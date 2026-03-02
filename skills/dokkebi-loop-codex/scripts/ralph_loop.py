#!/usr/bin/env python3
"""Ralph Loop runner (artifact-first + evidence-gated, basic and phase-config compatible)."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.artifacts import (
    append_lessons,
    ensure_story_contract,
    load_lessons,
    update_context_pack,
    write_errors,
    write_evidence,
)
from core.files import append_jsonl, append_progress, load_json, prepare_ralph_dirs, save_json, utc_now
from core.basic_adapter import pick_story, validate_prd_contract
from core.models import Paths, RunOptions
from core.role_agents import (
    apply_show_me_hook,
    run_context_scribe_builtin,
    run_issue_tiger_builtin,
    run_planner_builtin,
    run_qa_dr_strange,
    run_specify_builtin,
)
from core.runtime import capture_git_snapshot, command_result_as_dict
from phases.command_phase import run_commands, run_single_expect_fail, run_single_expect_pass


DEFAULT_CONSTRAINTS = ["--dangerously-skip-permissions", "--allow-git-push"]
DEFAULT_AGENTS_TEMPLATE = """# AGENTS

## Ralph Loop Principles
- Artifact-first: persistent memory lives in files, not chat.
- Evidence-gated: PASS requires executable evidence.
- Context-pack memory: update `stories/<id>/context_pack.md` every loop.
- Self-improvement: append reusable lessons to `LESSONS.md`.

## Role Contracts
### specify-gidometa
- Input: user idea + repo context
- Output: `prd.json`, `stories/<id>/story.md`

### planner
- Input: `prd.json`, `stories/<id>/story.md`
- Output: `stories/<id>/plan.md`

### context-scribe
- Input: diff + logs + story artifacts
- Output: `stories/<id>/context_pack.md`, `LESSONS.md` (when needed)

### implementer
- Input: `story.md`, `plan.md`, `context_pack.md`, `errors.md`
- Output: code changes

### testsmith
- Input: story context + current code
- Output: fail-first and regression tests

### verifier
- Input: code + plan + context pack + logs
- Output PASS: `stories/<id>/evidence.md`
- Output FAIL: `stories/<id>/errors.md`

### reviewer
- Input: current diff + tests
- Output: actionable review notes (commands or checks)

### show-me-the-hook
- Input: updated user directives + current PRD
- Output: patched `prd.json`/`story.md`/`plan.md`

### qa dr.strange
- Input: full PRD + runnable system
- Output: E2E evidence

### issue tiger
- Input: issue metadata
- Output: branch/PR automation artifacts

## Loop Sequence
specify-gidometa -> planner -> context-scribe -> implementer -> testsmith -> verifier
FAIL => context-scribe update -> implementer retry
ALL PASS => qa dr.strange
"""
REQUIRED_AGENT_MARKERS = [
    "### specify-gidometa",
    "### planner",
    "### context-scribe",
    "### implementer",
    "### testsmith",
    "### verifier",
    "### reviewer",
    "### show-me-the-hook",
    "### qa dr.strange",
    "### issue tiger",
]


def normalize_argv(argv: list[str]) -> list[str]:
    normalized: list[str] = []
    idx = 0
    while idx < len(argv):
        token = argv[idx]
        if token == "--constraint" and idx + 1 < len(argv):
            normalized.append(f"--constraint={argv[idx + 1]}")
            idx += 2
            continue
        if token == "--mode" and idx + 1 < len(argv):
            mode = argv[idx + 1]
            if mode == "legacy":
                mode = "basic"
            if mode == "v2":
                mode = "phase-config"
            normalized.append(f"--mode={mode}")
            idx += 2
            continue
        if token.startswith("--mode="):
            mode = token.split("=", 1)[1]
            if mode == "legacy":
                mode = "basic"
            if mode == "v2":
                mode = "phase-config"
            normalized.append(f"--mode={mode}")
            idx += 1
            continue
        normalized.append(token)
        idx += 1
    return normalized


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Ralph loop from prd.json")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--prd-file", default="prd.json")
    parser.add_argument("--state-file", default="ralph_state.json")
    parser.add_argument("--progress-file", default="progress.md")
    parser.add_argument("--progress-jsonl", default="PROGRESS.jsonl")
    parser.add_argument("--lessons-file", default="LESSONS.md")
    parser.add_argument("--constraint", action="append", default=list(DEFAULT_CONSTRAINTS))
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--max-iterations", type=int, default=100)
    parser.add_argument("--gate-command", default="./ralph/tools/gate.sh")
    parser.add_argument("--skip-gate", action="store_true")
    parser.add_argument("--allow-missing-agents-md", action="store_true")
    parser.add_argument("--strict-agents-md", action="store_true")
    parser.add_argument("--story-id", default="")
    parser.add_argument("--mode", choices=["auto", "basic", "phase-config"], default="auto")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--emit-context-pack", choices=["always", "on-fail", "on-pass"], default="always")
    parser.add_argument("--lessons-mode", choices=["off", "append", "append-and-inject"], default="append-and-inject")
    parser.add_argument("--trash-on-migrate", action="store_true")
    parser.add_argument("--bootstrap-prd", action="store_true", help="Bootstrap prd.json via specify-gidometa when missing/empty")
    parser.add_argument("--bootstrap-input-json", default="", help="Input JSON file for PRD bootstrap")
    parser.add_argument("--bootstrap-overwrite", action="store_true", help="Overwrite existing stories/<id>/story.md during bootstrap")
    return parser.parse_args(normalize_argv(sys.argv[1:]))


def _maybe_trash_old_skill_dir(repo_dir: Path) -> None:
    src = repo_dir / "skills" / "ralph-loop-codex"
    if not src.exists():
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dst_root = Path.home() / ".Trash" / "ralph-loop" / stamp
    dst_root.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst_root / src.name))


def _ensure_files(paths: Paths) -> None:
    load_json(paths.prd_path, {"stories": []})
    load_json(paths.state_path, {"failures": []})
    if not paths.progress_path.exists():
        paths.progress_path.write_text("# Ralph Progress\n\n", encoding="utf-8")
    if not paths.progress_jsonl_path.exists():
        paths.progress_jsonl_path.write_text("", encoding="utf-8")
    if not paths.lessons_path.exists():
        paths.lessons_path.write_text("# LESSONS\n\n", encoding="utf-8")


def _bootstrap_prd_if_needed(args: argparse.Namespace, paths: Paths) -> int:
    if not args.bootstrap_prd:
        return 0

    prd = load_json(paths.prd_path, {"stories": []})
    stories = prd.get("stories", [])
    if isinstance(stories, list) and len(stories) > 0:
        return 0

    script = Path(__file__).resolve().parents[2] / "specify-gidometa-codex" / "scripts" / "specify_gidometa.py"
    if not script.exists():
        print(f"bootstrap script not found: {script}", file=sys.stderr)
        return 1

    cmd = [sys.executable, str(script), "--repo", str(paths.repo_dir)]
    if args.bootstrap_input_json:
        cmd.extend(["--input-json", args.bootstrap_input_json])
    if args.bootstrap_overwrite:
        cmd.append("--overwrite")

    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.stdout.strip():
        print(proc.stdout.strip())
    if proc.returncode != 0:
        if proc.stderr.strip():
            print(proc.stderr.strip(), file=sys.stderr)
        return proc.returncode
    return 0


def _ensure_agents_md(repo_dir: Path, *, strict: bool) -> bool:
    agents = repo_dir / "AGENTS.md"
    if agents.exists():
        return True
    if strict:
        return False
    agents.write_text(DEFAULT_AGENTS_TEMPLATE, encoding="utf-8")
    return True


def _ensure_agents_contract(repo_dir: Path) -> None:
    agents = repo_dir / "AGENTS.md"
    if not agents.exists():
        return
    text = agents.read_text(encoding="utf-8")
    missing = [m for m in REQUIRED_AGENT_MARKERS if m not in text]
    if not missing:
        return
    appendix = ["", "## Ralph Loop Contract Addendum (auto-appended)"]
    for marker in missing:
        role = marker.replace("### ", "")
        appendix.append(f"{marker}")
        appendix.append(f"- Contract missing in existing AGENTS.md; define input/output for `{role}`.")
        appendix.append("")
    agents.write_text(text.rstrip() + "\n" + "\n".join(appendix), encoding="utf-8")


def _flatten_trace_commands(trace: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for key in ["specify", "planner", "context_scribe", "show_me_hook", "builder", "testsmith", "verifier", "review", "issue_tiger"]:
        result.extend(list(trace.get(key, [])))
    tdd = trace.get("tdd", {})
    if isinstance(tdd, dict):
        if tdd.get("red"):
            result.append(dict(tdd["red"]))
        if tdd.get("green"):
            result.append(dict(tdd["green"]))
    if trace.get("gate"):
        result.append(dict(trace["gate"]))
    for item in trace.get("qa", []) or []:
        result.append(dict(item))
    return result


def _write_attempt_trace(logs_dir: Path, story_id: str, attempt: int, trace: dict[str, Any]) -> None:
    (logs_dir / f"{story_id}-attempt-{attempt}.json").write_text(json.dumps(trace, indent=2) + "\n", encoding="utf-8")


def _write_debug_bundle(logs_dir: Path, story_id: str, attempt: int, phase: str, command: str, returncode: int, repo_dir: Path) -> None:
    git = capture_git_snapshot(repo_dir)
    lines = [
        f"# Debug Bundle: {story_id} attempt {attempt}",
        "",
        f"- phase: `{phase}`",
        f"- command: `{command}`",
        f"- returncode: `{returncode}`",
        "",
        "## Root-Cause Checklist",
        "- Reproduce the failure command exactly once from logs.",
        "- Compare with prior successful evidence/context pack.",
        "- Apply one minimal fix then rerun verifier.",
        "",
        "## Git Snapshot",
        f"- head: `{git.get('head', '')}`",
        "",
        "```",
        str(git.get("status_short", "")),
        "```",
        "",
        "```",
        str(git.get("diff_stat", "")),
        "```",
        "",
    ]
    (logs_dir / f"{story_id}-attempt-{attempt}-debug.md").write_text("\n".join(lines), encoding="utf-8")


def _update_story_status(prd: dict[str, Any], story_id: str, status: str) -> None:
    for s in prd.get("stories", []):
        if str(s.get("id")) == story_id:
            s["status"] = status
            return


def _should_run_gate(repo_dir: Path, gate_command: str, skip_gate: bool) -> bool:
    if skip_gate or not gate_command.strip():
        return False
    default_gate = gate_command.strip() == "./ralph/tools/gate.sh"
    if not default_gate:
        return True
    return (repo_dir / "ralph" / "tools" / "gate.sh").exists()


def _record_progress(
    paths: Paths,
    *,
    story_id: str,
    phase: str,
    status: str,
    summary: str,
    commands: list[dict[str, Any]],
    artifact_hashes: dict[str, str],
) -> None:
    git = capture_git_snapshot(paths.repo_dir)
    append_jsonl(
        paths.progress_jsonl_path,
        {
            "timestamp": utc_now(),
            "story_id": story_id,
            "phase": phase,
            "status": status,
            "commands": commands,
            "git_head": git.get("head", ""),
            "summary": summary,
            "artifact_hashes": artifact_hashes,
        },
    )


def _build_verifier_feedback(story_obj: Any, trace: dict[str, Any]) -> dict[str, list[str]]:
    # Lightweight soft gate scoring to keep evidence actionable.
    test_count = len(trace.get("testsmith", [])) + (1 if trace.get("tdd", {}).get("green") else 0)
    review_count = len(trace.get("review", []))
    qa_count = len(trace.get("qa", []))
    complexity_score = max(1, 10 - len(trace.get("builder", [])))
    coverage_score = min(10, 4 + test_count + qa_count)
    maintainability_score = min(10, 5 + review_count)
    security_score = 7 if review_count > 0 else 5
    performance_score = 7 if qa_count > 0 else 6

    options = story_obj.raw.get("tech_stack_options", [])
    selected = story_obj.raw.get("selected_stack", "current stack")
    devil_points: list[str] = []
    if options:
        devil_points.append(f"selected stack: {selected}")
        alternatives = [o for o in options if o != selected]
        if alternatives:
            devil_points.append(f"alternatives considered: {', '.join(alternatives)}")
            devil_points.append("question: can a simpler option reduce operational risk?")
        else:
            devil_points.append("no explicit alternatives provided")
    else:
        devil_points.append("no tech_stack_options provided; devil's-advocate comparison skipped")

    return {
        "Soft Gate Scores": [
            f"coverage: {coverage_score}/10",
            f"complexity: {complexity_score}/10",
            f"maintainability: {maintainability_score}/10",
            f"security: {security_score}/10",
            f"performance: {performance_score}/10",
        ],
        "Devils Advocate": devil_points,
    }


def run_story(paths: Paths, prd: dict[str, Any], state: dict[str, Any], story_obj: Any, options: RunOptions) -> bool:
    story_id = story_obj.story_id
    title = story_obj.title
    _update_story_status(prd, story_id, "doing")
    save_json(paths.prd_path, prd)

    contract = ensure_story_contract(paths.repo_dir, story_obj.raw)

    state["current_story_id"] = story_id
    state["last_run"] = utc_now()
    state["constraints"] = options.constraints
    save_json(paths.state_path, state)

    print(f"[Picked story] {story_id} - {title}")
    print("[Builder plan]")
    for idx, cmd in enumerate(story_obj.builder_commands, start=1):
        print(f"{idx}. {cmd}")
    append_progress(paths.progress_path, f"- {utc_now()} start {story_id} {title}")

    if not story_obj.builder_commands or not story_obj.verifier_commands:
        append_progress(paths.progress_path, f"- {utc_now()} fail {story_id} missing commands")
        _update_story_status(prd, story_id, "todo")
        save_json(paths.prd_path, prd)
        return False

    lessons_text = load_lessons(paths.lessons_path) if options.lessons_mode == "append-and-inject" else ""
    if lessons_text:
        append_progress(paths.progress_path, f"- {utc_now()} lessons injected lines={len(lessons_text.splitlines())}")

    error_md = paths.repo_dir / "ERROR.md"

    for attempt in range(1, options.max_retries + 1):
        print(f"[Attempt] {attempt}/{options.max_retries}")
        append_progress(paths.progress_path, f"- {utc_now()} attempt {story_id} {attempt}/{options.max_retries}")

        trace: dict[str, Any] = {
            "timestamp": utc_now(),
            "story_id": story_id,
            "title": title,
            "attempt": attempt,
            "constraints": options.constraints,
            "specify": [],
            "planner": [],
            "context_scribe": [],
            "show_me_hook": [],
            "builder": [],
            "testsmith": [],
            "verifier": [],
            "review": [],
            "issue_tiger": [],
            "qa": [],
            "tdd": {"red": None, "green": None},
            "gate": None,
            "outcome": "in_progress",
            "git_before": capture_git_snapshot(paths.repo_dir),
        }

        specify_log = paths.logs_dir / f"{story_id}-specify-{attempt}.log"
        planner_log = paths.logs_dir / f"{story_id}-planner-{attempt}.log"
        context_scribe_log = paths.logs_dir / f"{story_id}-context-scribe-{attempt}.log"
        hook_log = paths.logs_dir / f"{story_id}-show-me-hook-{attempt}.log"
        builder_log = paths.logs_dir / f"{story_id}-build-{attempt}.log"
        testsmith_log = paths.logs_dir / f"{story_id}-testsmith-{attempt}.log"
        verifier_log = paths.logs_dir / f"{story_id}-verify-{attempt}.log"
        review_log = paths.logs_dir / f"{story_id}-review-{attempt}.log"
        issue_tiger_log = paths.logs_dir / f"{story_id}-issue-tiger-{attempt}.log"
        tdd_log = paths.logs_dir / f"{story_id}-tdd-{attempt}.log"
        gate_log = paths.logs_dir / f"{story_id}-gate-{attempt}.log"
        qa_log = paths.logs_dir / f"{story_id}-qa-{attempt}.log"

        def fail(phase: str, failed_command: str, rc: int, stdout: str, stderr: str, summary: str) -> bool:
            state.setdefault("failures", []).append(
                {
                    "story_id": story_id,
                    "attempt": attempt,
                    "phase": phase,
                    "command": failed_command,
                    "returncode": rc,
                    "timestamp": utc_now(),
                }
            )
            trace["outcome"] = f"{phase}_failed"
            trace["failure"] = {"phase": phase, "command": failed_command, "returncode": rc}
            trace["git_after"] = capture_git_snapshot(paths.repo_dir)
            _write_attempt_trace(paths.logs_dir, story_id, attempt, trace)
            _write_debug_bundle(paths.logs_dir, story_id, attempt, phase, failed_command, rc, paths.repo_dir)
            repro = write_errors(
                contract["errors"],
                story_id=story_id,
                phase=phase,
                command=failed_command,
                returncode=rc,
                stderr=stderr,
                stdout=stdout,
            )
            if options.emit_context_pack in {"always", "on-fail"}:
                update_context_pack(
                    contract["context_pack"],
                    summary=summary,
                    reproduction=[repro],
                    next_todo=["Read errors.md", "Apply minimal fix", "Rerun verifier commands"],
                    refs=[str(contract["errors"])],
                )
            if options.lessons_mode in {"append", "append-and-inject"}:
                append_lessons(
                    paths.lessons_path,
                    story_id=story_id,
                    phase=phase,
                    pattern=f"{phase} failed with rc={rc}",
                    remedy="Capture minimal repro, then patch and rerun evidence gate.",
                )
            _record_progress(
                paths,
                story_id=story_id,
                phase=phase,
                status="FAIL",
                summary=summary,
                commands=_flatten_trace_commands(trace),
                artifact_hashes={},
            )
            append_progress(paths.progress_path, f"- {utc_now()} fail {story_id} {phase} attempt={attempt}")
            save_json(paths.state_path, state)
            if not error_md.exists():
                error_md.write_text(f"# Error\n\n{phase} failed for {story_id} on attempt {attempt}.\n", encoding="utf-8")
            if attempt == options.max_retries:
                _update_story_status(prd, story_id, "todo")
                save_json(paths.prd_path, prd)
                append_progress(paths.progress_path, f"- {utc_now()} exhausted {story_id}")
                print(f"[Verifier verdict] FAIL - {phase} exhausted retries")
                return False
            return True

        def run_phase_or_fail(phase: str, commands: list[str], log_path: Path, summary: str) -> str:
            ok, results, failed = run_commands(phase, commands, options.constraints, paths.repo_dir, log_path)
            trace[phase] = [command_result_as_dict(x) for x in results]
            if not ok and failed is not None:
                if fail(phase, failed.command, failed.returncode, failed.stdout, failed.stderr, summary):
                    return "retry"
                return "abort"
            return "ok"

        def record_builtin(phase: str, result: Any, log_path: Path) -> str:
            from core.files import log_command_output

            log_command_output(log_path, result.command, result.returncode, result.stdout, result.stderr)
            trace[phase].append(command_result_as_dict(result))
            if result.returncode != 0:
                if fail(phase, result.command, result.returncode, result.stdout, result.stderr, f"{phase} builtin failed"):
                    return "retry"
                return "abort"
            return "ok"

        # Built-in specify/planner/context-scribe always run so role contracts are active by default.
        phase_result = record_builtin("specify", run_specify_builtin(paths.repo_dir, story_obj.raw), specify_log)
        if phase_result == "retry":
            continue
        if phase_result == "abort":
            return False

        phase_result = record_builtin("planner", run_planner_builtin(paths.repo_dir, story_obj.raw), planner_log)
        if phase_result == "retry":
            continue
        if phase_result == "abort":
            return False

        phase_result = record_builtin(
            "context_scribe",
            run_context_scribe_builtin(
                paths.repo_dir,
                story_obj.raw,
                summary="Initial context pack update before implementation",
                reproduction=[],
                next_todo=["Run implementer commands", "Run testsmith and verifier"],
                refs=[str(contract["story"]), str(contract["plan"])],
            ),
            context_scribe_log,
        )
        if phase_result == "retry":
            continue
        if phase_result == "abort":
            return False

        if story_obj.specify_commands:
            phase_result = run_phase_or_fail("specify", story_obj.specify_commands, specify_log, "Specify phase failed")
            if phase_result == "retry":
                continue
            if phase_result == "abort":
                return False

        if story_obj.planner_commands:
            phase_result = run_phase_or_fail("planner", story_obj.planner_commands, planner_log, "Planner phase failed")
            if phase_result == "retry":
                continue
            if phase_result == "abort":
                return False

        if story_obj.context_scribe_commands:
            phase_result = run_phase_or_fail(
                "context_scribe",
                story_obj.context_scribe_commands,
                context_scribe_log,
                "Context-scribe phase failed",
            )
            if phase_result == "retry":
                continue
            if phase_result == "abort":
                return False

        if story_obj.show_me_hook_commands:
            phase_result = run_phase_or_fail(
                "show_me_hook",
                story_obj.show_me_hook_commands,
                hook_log,
                "Show-me-the-hook phase failed",
            )
            if phase_result == "retry":
                continue
            if phase_result == "abort":
                return False

        if story_obj.tdd_red_command:
            ok, result = run_single_expect_fail(story_obj.tdd_red_command, options.constraints, paths.repo_dir, tdd_log)
            trace["tdd"]["red"] = command_result_as_dict(result)
            if not ok:
                if fail("tdd_red", result.command, result.returncode, result.stdout, result.stderr, "TDD red command unexpectedly passed"):
                    continue
                return False

        ok, results, failed = run_commands("builder", story_obj.builder_commands, options.constraints, paths.repo_dir, builder_log)
        trace["builder"] = [command_result_as_dict(x) for x in results]
        for x in results:
            print(f"[Command] {x.command}")
            print(f"[Result] rc={x.returncode}")
            if x.stdout:
                print(x.stdout.rstrip())
            if x.stderr:
                print(x.stderr.rstrip(), file=sys.stderr)
        if not ok and failed is not None:
            if fail("builder", failed.command, failed.returncode, failed.stdout, failed.stderr, "Implementer commands failed"):
                continue
            return False

        ok, results, failed = run_commands("testsmith", story_obj.testsmith_commands, options.constraints, paths.repo_dir, testsmith_log)
        trace["testsmith"] = [command_result_as_dict(x) for x in results]
        if not ok and failed is not None:
            if fail("testsmith", failed.command, failed.returncode, failed.stdout, failed.stderr, "Testsmith commands failed"):
                continue
            return False

        error_md.unlink(missing_ok=True)
        ok, results, failed = run_commands("verifier", story_obj.verifier_commands, options.constraints, paths.repo_dir, verifier_log)
        trace["verifier"] = [command_result_as_dict(x) for x in results]
        for x in results:
            print(f"[Command] {x.command}")
            print(f"[Result] rc={x.returncode}")
            if x.stdout:
                print(x.stdout.rstrip())
            if x.stderr:
                print(x.stderr.rstrip(), file=sys.stderr)
        if (not ok and failed is not None) or error_md.exists():
            failed_cmd = failed.command if failed is not None else "ERROR.md signal"
            failed_rc = failed.returncode if failed is not None else 1
            failed_stdout = failed.stdout if failed is not None else ""
            failed_stderr = failed.stderr if failed is not None else "ERROR.md present"
            if fail("verifier", failed_cmd, failed_rc, failed_stdout, failed_stderr, "Verifier evidence gate failed"):
                continue
            return False

        if story_obj.tdd_green_command:
            ok, result = run_single_expect_pass(story_obj.tdd_green_command, options.constraints, paths.repo_dir, tdd_log)
            trace["tdd"]["green"] = command_result_as_dict(result)
            if not ok:
                if fail("tdd_green", result.command, result.returncode, result.stdout, result.stderr, "TDD green command failed"):
                    continue
                return False

        ok, results, failed = run_commands("review", story_obj.review_commands, options.constraints, paths.repo_dir, review_log)
        trace["review"] = [command_result_as_dict(x) for x in results]
        if not ok and failed is not None:
            if fail("review", failed.command, failed.returncode, failed.stdout, failed.stderr, "Review commands failed"):
                continue
            return False

        ok, results, failed = run_commands(
            "issue_tiger",
            story_obj.issue_tiger_commands,
            options.constraints,
            paths.repo_dir,
            issue_tiger_log,
        )
        trace["issue_tiger"] = [command_result_as_dict(x) for x in results]
        if not ok and failed is not None:
            if fail("issue_tiger", failed.command, failed.returncode, failed.stdout, failed.stderr, "Issue tiger phase failed"):
                continue
            return False

        phase_result = record_builtin("issue_tiger", run_issue_tiger_builtin(paths.repo_dir, story_obj.raw), issue_tiger_log)
        if phase_result == "retry":
            continue
        if phase_result == "abort":
            return False

        if _should_run_gate(paths.repo_dir, options.gate_command, options.skip_gate):
            ok, result = run_single_expect_pass(options.gate_command, options.constraints, paths.repo_dir, gate_log)
            trace["gate"] = command_result_as_dict(result)
            if not ok:
                if fail("gate", result.command, result.returncode, result.stdout, result.stderr, "Gate command failed"):
                    continue
                return False

        ok, results, failed = run_commands("qa", story_obj.qa_commands, options.constraints, paths.repo_dir, qa_log)
        trace["qa"] = [command_result_as_dict(x) for x in results]
        if not ok and failed is not None:
            if fail("qa", failed.command, failed.returncode, failed.stdout, failed.stderr, "QA stage failed"):
                continue
            return False

        _update_story_status(prd, story_id, "done")
        save_json(paths.prd_path, prd)
        trace["outcome"] = "pass"
        trace["git_after"] = capture_git_snapshot(paths.repo_dir)
        _write_attempt_trace(paths.logs_dir, story_id, attempt, trace)

        evidence_hashes = write_evidence(
            contract["evidence"],
            story_id=story_id,
            commands=_flatten_trace_commands(trace),
            summary="Evidence gate passed",
            extra_sections=_build_verifier_feedback(story_obj, trace),
        )
        if options.emit_context_pack in {"always", "on-pass"}:
            next_todo = ["Run next highest-priority story"]
            if story_obj.qa_commands:
                next_todo = ["Review QA outputs and proceed to next story"]
            phase_result = record_builtin(
                "context_scribe",
                run_context_scribe_builtin(
                    paths.repo_dir,
                    story_obj.raw,
                    summary="Story passed evidence gate",
                    reproduction=[],
                    next_todo=next_todo,
                    refs=[str(contract["evidence"])],
                ),
                context_scribe_log,
            )
            if phase_result == "retry":
                continue
            if phase_result == "abort":
                return False

        _record_progress(
            paths,
            story_id=story_id,
            phase="verifier",
            status="PASS",
            summary="Story completed with evidence",
            commands=_flatten_trace_commands(trace),
            artifact_hashes=evidence_hashes,
        )
        append_progress(paths.progress_path, f"- {utc_now()} done {story_id} attempts={attempt}")
        save_json(paths.state_path, state)
        error_md.unlink(missing_ok=True)
        print("[Verifier verdict] PASS")
        break

    remaining = [s for s in prd.get("stories", []) if s.get("status") == "todo"]
    if remaining:
        print(f"[Next suggested story] {remaining[0].get('id', 'unknown')}")
    else:
        print("[Next suggested story] none")
    return True


def main() -> int:
    args = parse_args()
    repo_dir = Path(args.repo).resolve()
    repo_dir.mkdir(parents=True, exist_ok=True)

    if args.trash_on_migrate:
        _maybe_trash_old_skill_dir(repo_dir)

    strict_agents = bool(args.strict_agents_md and not args.allow_missing_agents_md)
    if not _ensure_agents_md(repo_dir, strict=strict_agents):
        print("AGENTS.md not found in repo root. Create it first (or disable --strict-agents-md).", file=sys.stderr)
        return 1
    _ensure_agents_contract(repo_dir)

    logs_dir = prepare_ralph_dirs(repo_dir)
    paths = Paths(
        repo_dir=repo_dir,
        prd_path=repo_dir / args.prd_file,
        state_path=repo_dir / args.state_file,
        progress_path=repo_dir / args.progress_file,
        progress_jsonl_path=repo_dir / args.progress_jsonl,
        lessons_path=repo_dir / args.lessons_file,
        logs_dir=logs_dir,
    )

    _ensure_files(paths)
    bootstrap_rc = _bootstrap_prd_if_needed(args, paths)
    if bootstrap_rc != 0:
        return bootstrap_rc

    options = RunOptions(
        constraints=args.constraint,
        max_retries=args.max_retries,
        gate_command=args.gate_command,
        skip_gate=args.skip_gate,
        emit_context_pack=args.emit_context_pack,
        lessons_mode=args.lessons_mode,
        mode=args.mode,
    )

    iterations = 0
    while True:
        prd = load_json(paths.prd_path, {"stories": []})
        state = load_json(paths.state_path, {"failures": []})
        hook_changed, hook_summary = apply_show_me_hook(paths.repo_dir, prd)
        if hook_changed:
            save_json(paths.prd_path, prd)
            append_progress(paths.progress_path, f"- {utc_now()} show-me-the-hook {hook_summary}")
        validation_errors = validate_prd_contract(prd, args.mode, args.story_id or None)
        if validation_errors:
            validation_path = paths.repo_dir / "PRD_VALIDATION_ERRORS.md"
            lines = [
                "# PRD Validation Errors",
                "",
                "Ralph Loop strict validation failed. Fill missing PRD fields before rerun.",
                "",
                "## Errors",
            ]
            lines.extend([f"- {msg}" for msg in validation_errors])
            lines.extend(["", "## Required Action", "- Update `prd.json` to satisfy the story contract."])
            validation_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            append_progress(paths.progress_path, f"- {utc_now()} fail prd-validation count={len(validation_errors)}")
            append_jsonl(
                paths.progress_jsonl_path,
                {
                    "timestamp": utc_now(),
                    "story_id": args.story_id or "PRD",
                    "phase": "prd-validation",
                    "status": "FAIL",
                    "commands": [],
                    "git_head": capture_git_snapshot(paths.repo_dir).get("head", ""),
                    "summary": f"strict prd validation failed ({len(validation_errors)} errors)",
                    "artifact_hashes": {},
                },
            )
            print(f"Strict PRD validation failed. See {validation_path}", file=sys.stderr)
            for msg in validation_errors:
                print(f"- {msg}", file=sys.stderr)
            return 1
        story_obj = pick_story(prd, args.mode, args.story_id or None)
        if story_obj is None:
            qa_result = run_qa_dr_strange(paths.repo_dir, prd)
            qa_detail_path = paths.repo_dir / ".ralph" / "qa_dr_strange_result.json"
            qa_details: dict[str, Any] = {}
            if qa_detail_path.exists():
                try:
                    qa_details = json.loads(qa_detail_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    qa_details = {}
            if qa_result.returncode != 0 and qa_details:
                failed_story_ids = [sid for sid in qa_details.get("failed_story_ids", []) if sid]
                failing_checks = qa_details.get("failing_checks", [])
                for sid in failed_story_ids:
                    for story in prd.get("stories", []):
                        if str(story.get("id")) != sid:
                            continue
                        story["status"] = "todo"
                        contract = ensure_story_contract(paths.repo_dir, story)
                        check = next((c for c in failing_checks if str(c.get("story_id", "")) == sid), None)
                        failed_cmd = str(check.get("command", "qa scenario failed")) if isinstance(check, dict) else "qa scenario failed"
                        failed_stdout = str(check.get("stdout", "")) if isinstance(check, dict) else ""
                        failed_stderr = str(check.get("stderr", "")) if isinstance(check, dict) else qa_result.stderr
                        repro = write_errors(
                            contract["errors"],
                            story_id=sid,
                            phase="qa-dr-strange",
                            command=failed_cmd,
                            returncode=1,
                            stderr=failed_stderr,
                            stdout=failed_stdout,
                        )
                        update_context_pack(
                            contract["context_pack"],
                            summary="QA dr.strange detected a failing end-to-end check",
                            reproduction=[repro],
                            next_todo=["Fix failing scenario", "Rerun verifier and QA"],
                            refs=[str(paths.repo_dir / "E2E_EVIDENCE.md"), str(contract["errors"])],
                        )
                        append_lessons(
                            paths.lessons_path,
                            story_id=sid,
                            phase="qa-dr-strange",
                            pattern="QA scenario/check failure after all stories marked done",
                            remedy="Map failing check to story, revert status to todo, fix and rerun full QA gate.",
                        )
                        break
                if failed_story_ids:
                    save_json(paths.prd_path, prd)
            append_progress(paths.progress_path, f"- {utc_now()} qa-dr-strange rc={qa_result.returncode}")
            append_jsonl(
                paths.progress_jsonl_path,
                {
                    "timestamp": utc_now(),
                    "story_id": "ALL",
                    "phase": "qa-dr-strange",
                    "status": "PASS" if qa_result.returncode == 0 else "FAIL",
                    "commands": [command_result_as_dict(qa_result)],
                    "git_head": capture_git_snapshot(paths.repo_dir).get("head", ""),
                    "summary": qa_result.stdout.strip() or qa_result.stderr.strip(),
                    "artifact_hashes": {},
                },
            )
            print("No todo stories left.")
            return 0 if qa_result.returncode == 0 else 1

        ok = run_story(paths, prd, state, story_obj, options)
        iterations += 1

        if not ok:
            return 1
        if not args.loop:
            return 0
        if iterations >= args.max_iterations:
            print("Reached max iterations.", file=sys.stderr)
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
