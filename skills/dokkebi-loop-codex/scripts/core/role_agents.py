from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from core.artifacts import update_context_pack
from core.files import utc_now
from core.models import CommandResult


def run_specify_builtin(repo_dir: Path, story: dict[str, Any]) -> CommandResult:
    sid = str(story.get("id", "unknown"))
    sdir = repo_dir / "stories" / sid
    sdir.mkdir(parents=True, exist_ok=True)
    story_md = sdir / "story.md"
    if not story_md.exists():
        story_md.write_text(
            "\n".join(
                [
                    f"# Story {sid}: {story.get('title', 'untitled')}",
                    "",
                    "## Goal",
                    str(story.get("title", "untitled")),
                    "",
                    "## Acceptance Criteria",
                    *(f"- {x}" for x in story.get("acceptance_criteria", []) or ["(to be defined)"]),
                    "",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
    return CommandResult(
        command="builtin:specify-gidometa",
        returncode=0,
        stdout=f"story doc ensured: {story_md}\n",
        stderr="",
    )


def run_planner_builtin(repo_dir: Path, story: dict[str, Any]) -> CommandResult:
    sid = str(story.get("id", "unknown"))
    sdir = repo_dir / "stories" / sid
    sdir.mkdir(parents=True, exist_ok=True)
    plan_md = sdir / "plan.md"

    implementer = story.get("phase_config", {}).get("implementer_commands", story.get("builder_commands", []))
    verifier = story.get("phase_config", {}).get("verifier_commands", story.get("verifier_commands", []))
    tests = story.get("phase_config", {}).get("testsmith_commands", story.get("testsmith_commands", []))

    lines = [
        f"# Plan for {sid}",
        "",
        "## Steps",
        "- Specify story scope and constraints.",
        "- Break into file/module changes with small commits.",
        "- Implement minimal change set.",
        "- Add adversarial/regression tests (fail-first).",
        "- Verify and record evidence.",
        "",
        "## Files",
        "- stories/<id>/story.md",
        "- stories/<id>/plan.md",
        "- stories/<id>/context_pack.md",
        "",
        "## Implementer Commands",
        *([f"- `{c}`" for c in implementer] or ["- (none)"]),
        "",
        "## Test Plan",
        *([f"- `{c}`" for c in tests] or ["- (none)"]),
        "",
        "## Verifier Commands",
        *([f"- `{c}`" for c in verifier] or ["- (none)"]),
        "",
        "## Rollback",
        "- Revert story diff and rerun verifier commands.",
        "",
        "## Risks",
        *([f"- {r}" for r in story.get("risks", [])] or ["- (to be defined)"]),
        "",
    ]
    plan_md.write_text("\n".join(lines), encoding="utf-8")
    adr_topic = story.get("adr_topic", "")
    options = story.get("tech_stack_options", [])
    if adr_topic or options:
        adr_dir = repo_dir / "stories" / sid / "ADR"
        adr_dir.mkdir(parents=True, exist_ok=True)
        adr_file = adr_dir / "0001-stack-choice.md"
        adr_lines = [
            f"# ADR: {adr_topic or 'Stack Choice'}",
            "",
            "## Options Considered",
            *([f"- {o}" for o in options] or ["- current stack"]),
            "",
            "## Decision",
            f"- selected: {story.get('selected_stack', 'current stack')}",
            "",
            "## Rationale",
            "- Prefer simpler operational burden and existing team familiarity.",
            "",
        ]
        adr_file.write_text("\n".join(adr_lines), encoding="utf-8")
    return CommandResult(
        command="builtin:planner",
        returncode=0,
        stdout=f"plan generated: {plan_md}\n",
        stderr="",
    )


def run_context_scribe_builtin(
    repo_dir: Path,
    story: dict[str, Any],
    *,
    summary: str,
    reproduction: list[str],
    next_todo: list[str],
    refs: list[str],
) -> CommandResult:
    sid = str(story.get("id", "unknown"))
    context_path = repo_dir / "stories" / sid / "context_pack.md"
    update_context_pack(
        context_path,
        summary=summary,
        reproduction=reproduction,
        next_todo=next_todo,
        refs=refs,
    )
    return CommandResult(
        command="builtin:context-scribe",
        returncode=0,
        stdout=f"context pack updated: {context_path}\n",
        stderr="",
    )


def apply_show_me_hook(repo_dir: Path, prd: dict[str, Any]) -> tuple[bool, str]:
    """Apply optional request file and return (changed, summary)."""
    req_path = repo_dir / ".ralph" / "hook_requests.json"
    if not req_path.exists():
        return False, "no hook request"

    payload = json.loads(req_path.read_text(encoding="utf-8"))
    changed = False
    applied: list[str] = []
    for req in payload.get("requests", []):
        action = req.get("action")
        if action == "add_story":
            prd.setdefault("stories", []).append(req["story"])
            changed = True
            applied.append("add_story")
        elif action == "update_priority":
            sid = str(req.get("id", ""))
            for story in prd.get("stories", []):
                if str(story.get("id")) == sid:
                    story["priority"] = int(req.get("priority", story.get("priority", 9999)))
                    changed = True
                    applied.append(f"update_priority:{sid}")
                    break
        elif action == "update_acceptance_criteria":
            sid = str(req.get("id", ""))
            for story in prd.get("stories", []):
                if str(story.get("id")) == sid:
                    story["acceptance_criteria"] = list(req.get("acceptance_criteria", []))
                    changed = True
                    applied.append(f"update_ac:{sid}")
                    break
        elif action == "set_status":
            sid = str(req.get("id", ""))
            status = str(req.get("status", "todo"))
            for story in prd.get("stories", []):
                if str(story.get("id")) == sid:
                    story["status"] = status
                    changed = True
                    applied.append(f"set_status:{sid}:{status}")
                    break
        elif action == "remove_story":
            sid = str(req.get("id", ""))
            before = len(prd.get("stories", []))
            prd["stories"] = [s for s in prd.get("stories", []) if str(s.get("id")) != sid]
            if len(prd["stories"]) != before:
                changed = True
                applied.append(f"remove_story:{sid}")
        elif action == "update_story_field":
            sid = str(req.get("id", ""))
            field = str(req.get("field", ""))
            value = req.get("value")
            for story in prd.get("stories", []):
                if str(story.get("id")) == sid and field:
                    story[field] = value
                    changed = True
                    applied.append(f"update_field:{sid}:{field}")
                    break

    archive = repo_dir / ".ralph" / "hook_applied"
    archive.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().replace(":", "-")
    archived_req = archive / f"hook_requests.{stamp}.json"
    req_path.rename(archived_req)
    change_log = archive / f"hook_changes.{stamp}.md"
    change_log.write_text(
        "\n".join(
            [
                "# Show Me The Hook Change Log",
                "",
                f"- changed: {changed}",
                *[f"- {entry}" for entry in applied],
                f"- request_file: {archived_req}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return changed, "hook request applied"


def run_issue_tiger_builtin(repo_dir: Path, story: dict[str, Any]) -> CommandResult:
    sid = str(story.get("id", "unknown"))
    issues_dir = repo_dir / "issues"
    if not issues_dir.exists():
        return CommandResult(command="builtin:issue-tiger", returncode=0, stdout="no issues directory\n", stderr="")

    issue_file = issues_dir / f"{sid}.json"
    if not issue_file.exists():
        return CommandResult(command="builtin:issue-tiger", returncode=0, stdout=f"no issue file for {sid}\n", stderr="")

    issue = json.loads(issue_file.read_text(encoding="utf-8"))
    out_dir = repo_dir / ".ralph" / "issue_tiger"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{sid}.md"
    branch = issue.get("branch", f"feature/{sid.lower()}")
    pr_title = issue.get("pr_title", f"[{sid}] {story.get('title', sid)}")
    lines = [
        f"# Issue Tiger Plan: {sid}",
        "",
        f"- branch: `{branch}`",
        f"- pr_title: {pr_title}",
        "",
        "## Checklist",
        "- [ ] Create/update branch",
        "- [ ] Apply story changes",
        "- [ ] Run verifier + gate",
        "- [ ] Open PR with evidence links",
        "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")
    commands = issue.get("commands", [])
    if isinstance(commands, list) and commands:
        exec_log = out_dir / f"{sid}.commands.log"
        with exec_log.open("w", encoding="utf-8") as handle:
            for command in commands:
                proc = subprocess.run(
                    command,
                    shell=True,
                    cwd=repo_dir,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                handle.write(f"$ {command}\nrc={proc.returncode}\n")
                if proc.stdout:
                    handle.write(proc.stdout)
                    if not proc.stdout.endswith("\n"):
                        handle.write("\n")
                if proc.stderr:
                    handle.write("[stderr]\n")
                    handle.write(proc.stderr)
                    if not proc.stderr.endswith("\n"):
                        handle.write("\n")
                handle.write("\n")
                if proc.returncode != 0:
                    return CommandResult(
                        command="builtin:issue-tiger",
                        returncode=proc.returncode,
                        stdout=f"issue plan created: {out}\n",
                        stderr=f"issue command failed: {command}",
                    )
    return CommandResult(command="builtin:issue-tiger", returncode=0, stdout=f"issue plan created: {out}\n", stderr="")


def run_qa_dr_strange(repo_dir: Path, prd: dict[str, Any]) -> CommandResult:
    def run_check(name: str, command: str, *, story_id: str, phase: str) -> dict[str, Any]:
        proc = subprocess.run(command, shell=True, cwd=repo_dir, capture_output=True, text=True, check=False)
        return {
            "name": name,
            "command": command,
            "story_id": story_id,
            "phase": phase,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }

    def discover_checks() -> list[dict[str, Any]]:
        checks: list[dict[str, Any]] = []
        package_json = repo_dir / "package.json"
        if package_json.exists():
            try:
                package = json.loads(package_json.read_text(encoding="utf-8"))
            except Exception:
                package = {}
            scripts = package.get("scripts", {}) if isinstance(package.get("scripts", {}), dict) else {}
            if "test" in scripts:
                checks.append({"name": "discover:test", "command": "npm run -s test", "story_id": "", "phase": "discover"})
            if "lint" in scripts:
                checks.append({"name": "discover:lint", "command": "npm run -s lint", "story_id": "", "phase": "discover"})
            if "typecheck" in scripts:
                checks.append({"name": "discover:typecheck", "command": "npm run -s typecheck", "story_id": "", "phase": "discover"})
        if (repo_dir / "tests").exists() or (repo_dir / "pytest.ini").exists() or (repo_dir / "pyproject.toml").exists():
            py = ".venv/bin/python -m pytest -q" if (repo_dir / ".venv" / "bin" / "python").exists() else "python3 -m pytest -q"
            checks.append({"name": "discover:pytest", "command": py, "story_id": "", "phase": "discover"})
        if (repo_dir / "Cargo.toml").exists():
            checks.append({"name": "discover:cargo-test", "command": "cargo test", "story_id": "", "phase": "discover"})
        if (repo_dir / "go.mod").exists():
            checks.append({"name": "discover:go-test", "command": "go test ./...", "story_id": "", "phase": "discover"})
        return checks

    stories = prd.get("stories", [])
    done = [s for s in stories if s.get("status") == "done"]
    todo = [s for s in stories if s.get("status") != "done"]
    evidence_lines = [
        "# E2E Evidence",
        "",
        f"- total_stories: {len(stories)}",
        f"- done: {len(done)}",
        f"- pending: {len(todo)}",
        "",
        "## Story Evidence",
    ]
    for story in stories:
        sid = str(story.get("id", "unknown"))
        ev = repo_dir / "stories" / sid / "evidence.md"
        evidence_lines.append(f"- {sid}: {'present' if ev.exists() else 'missing'}")
    evidence_lines.append("")

    qa_cfg = prd.get("qa", {}) if isinstance(prd.get("qa", {}), dict) else {}
    scenarios = qa_cfg.get("scenarios", [])
    auto_checks = qa_cfg.get("auto_checks", [])
    discover = bool(qa_cfg.get("discover_checks", True))
    failed_story = ""
    check_results: list[dict[str, Any]] = []

    if discover:
        evidence_lines.extend(["", "## Discovered Checks"])
        for check in discover_checks():
            result = run_check(
                str(check.get("name", "discover")),
                str(check.get("command", "true")),
                story_id=str(check.get("story_id", "")),
                phase=str(check.get("phase", "discover")),
            )
            check_results.append(result)
            evidence_lines.append(f"- {result['name']}: rc={result['returncode']} cmd=`{result['command']}`")

    if isinstance(auto_checks, list) and auto_checks:
        evidence_lines.extend(["", "## Auto Checks"])
        for check in auto_checks:
            if not isinstance(check, dict):
                continue
            result = run_check(
                str(check.get("name", "auto-check")),
                str(check.get("command", "true")),
                story_id=str(check.get("story_id", "")),
                phase="auto-check",
            )
            check_results.append(result)
            evidence_lines.append(f"- {result['name']}: rc={result['returncode']} cmd=`{result['command']}`")
            if result["returncode"] != 0 and not failed_story and result.get("story_id"):
                failed_story = str(result["story_id"])

    if isinstance(scenarios, list):
        evidence_lines.extend(["", "## Scenarios"])
        for scenario in scenarios:
            name = str(scenario.get("name", "unnamed"))
            command = str(scenario.get("command", "true"))
            story_id = str(scenario.get("story_id", ""))
            result = run_check(name, command, story_id=story_id, phase="scenario")
            check_results.append(result)
            evidence_lines.append(f"- {name}: rc={result['returncode']} cmd=`{command}`")
            if result["returncode"] != 0 and not failed_story:
                failed_story = story_id

    out = repo_dir / "E2E_EVIDENCE.md"
    out.write_text("\n".join(evidence_lines), encoding="utf-8")
    failing_checks = [r for r in check_results if int(r.get("returncode", 1)) != 0]
    failed_story_ids = sorted({str(r.get("story_id", "")).strip() for r in failing_checks if str(r.get("story_id", "")).strip()})
    rc = 0 if len(todo) == 0 and not failing_checks else 1
    stderr = ""
    if len(todo) != 0:
        stderr = "pending stories remain"
    if failed_story:
        stderr = f"{stderr}; failing scenario mapped to story {failed_story}".strip("; ")
    if failing_checks and not failed_story:
        stderr = f"{stderr}; one or more QA checks failed".strip("; ")

    result_path = repo_dir / ".ralph" / "qa_dr_strange_result.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        json.dumps(
            {
                "returncode": rc,
                "failed_story_ids": failed_story_ids,
                "failing_checks": failing_checks,
                "pending_story_ids": [str(s.get("id", "")) for s in todo],
                "total_checks": len(check_results),
                "evidence_file": str(out),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return CommandResult(
        command="builtin:qa-dr-strange",
        returncode=rc,
        stdout=f"e2e evidence written: {out}\nqa result: {result_path}\n",
        stderr=stderr,
    )
