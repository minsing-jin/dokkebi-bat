#!/usr/bin/env python3
"""Ralph loop runner for Codex repositories."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class CommandResult:
    command: str
    returncode: int
    stdout: str
    stderr: str


def normalize_argv(argv: list[str]) -> list[str]:
    normalized: list[str] = []
    idx = 0
    while idx < len(argv):
        token = argv[idx]
        if token == "--constraint" and idx + 1 < len(argv):
            value = argv[idx + 1]
            # Allow values that look like options, e.g. --dangerously-skip-permissions
            normalized.append(f"--constraint={value}")
            idx += 2
            continue
        normalized.append(token)
        idx += 1
    return normalized


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Ralph builder/verifier loop from prd.json")
    parser.add_argument("--repo", default=".", help="Repository directory containing prd.json")
    parser.add_argument("--prd-file", default="prd.json", help="PRD file path relative to repo")
    parser.add_argument("--state-file", default="ralph_state.json", help="State file path relative to repo")
    parser.add_argument("--progress-file", default="progress.md", help="Progress log file path relative to repo")
    parser.add_argument(
        "--constraint",
        action="append",
        default=[],
        help="Constraint token for commands (repeatable). Example: --constraint --dangerously-skip-permissions",
    )
    parser.add_argument("--loop", action="store_true", help="Run continuously until no todo story remains")
    parser.add_argument("--max-iterations", type=int, default=100, help="Safety guard for --loop mode")
    return parser.parse_args(normalize_argv(sys.argv[1:]))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        path.write_text(json.dumps(default, indent=2) + "\n", encoding="utf-8")
        return json.loads(json.dumps(default))
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def pick_story(prd: dict[str, Any]) -> dict[str, Any] | None:
    stories = prd.get("stories", [])
    for story in stories:
        if story.get("status", "todo") == "todo":
            return story
    return None


def interpolate(command: str, constraints: list[str]) -> str:
    rendered_constraints = " ".join(shlex.quote(flag) for flag in constraints)
    return command.replace("{{constraints}}", rendered_constraints)


def run_shell(command: str, repo_dir: Path) -> CommandResult:
    proc = subprocess.run(
        command,
        shell=True,
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    return CommandResult(command=command, returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)


def append_progress(progress_path: Path, line: str) -> None:
    with progress_path.open("a", encoding="utf-8") as handle:
        handle.write(line.rstrip() + "\n")


def run_story(
    repo_dir: Path,
    prd_path: Path,
    state_path: Path,
    progress_path: Path,
    story: dict[str, Any],
    constraints: list[str],
) -> bool:
    story_id = story.get("id", "unknown")
    title = story.get("title", "untitled")

    prd = load_json(prd_path, {"stories": []})
    live_story = next((s for s in prd.get("stories", []) if s.get("id") == story_id), story)
    live_story["status"] = "doing"
    save_json(prd_path, prd)

    state = load_json(state_path, {"failures": []})
    state["current_story_id"] = story_id
    state["last_run"] = utc_now()
    state["constraints"] = constraints
    save_json(state_path, state)

    print(f"[Picked story] {story_id} - {title}")
    append_progress(progress_path, f"- {utc_now()} start {story_id} {title}")

    builder_commands: list[str] = live_story.get("builder_commands", [])
    verifier_commands: list[str] = live_story.get("verifier_commands", [])

    if not builder_commands or not verifier_commands:
        append_progress(progress_path, f"- {utc_now()} fail {story_id} missing commands")
        live_story["status"] = "todo"
        save_json(prd_path, prd)
        return False

    print("[Builder plan]")
    for idx, raw in enumerate(builder_commands, start=1):
        print(f"{idx}. {raw}")

    command_results: list[CommandResult] = []
    for raw in builder_commands:
        cmd = interpolate(raw, constraints)
        result = run_shell(cmd, repo_dir)
        command_results.append(result)
        print(f"[Command] {cmd}")
        print(f"[Result] rc={result.returncode}")
        if result.stdout:
            print(result.stdout.rstrip())
        if result.stderr:
            print(result.stderr.rstrip(), file=sys.stderr)
        if result.returncode != 0:
            live_story["status"] = "todo"
            state.setdefault("failures", []).append(
                {
                    "story_id": story_id,
                    "phase": "builder",
                    "command": cmd,
                    "returncode": result.returncode,
                    "timestamp": utc_now(),
                }
            )
            save_json(prd_path, prd)
            save_json(state_path, state)
            append_progress(progress_path, f"- {utc_now()} fail {story_id} builder")
            print("[Verifier verdict] FAIL - builder command failed")
            return False

    for raw in verifier_commands:
        cmd = interpolate(raw, constraints)
        result = run_shell(cmd, repo_dir)
        command_results.append(result)
        print(f"[Command] {cmd}")
        print(f"[Result] rc={result.returncode}")
        if result.stdout:
            print(result.stdout.rstrip())
        if result.stderr:
            print(result.stderr.rstrip(), file=sys.stderr)
        if result.returncode != 0:
            live_story["status"] = "todo"
            state.setdefault("failures", []).append(
                {
                    "story_id": story_id,
                    "phase": "verifier",
                    "command": cmd,
                    "returncode": result.returncode,
                    "timestamp": utc_now(),
                }
            )
            save_json(prd_path, prd)
            save_json(state_path, state)
            append_progress(progress_path, f"- {utc_now()} fail {story_id} verifier")
            print("[Verifier verdict] FAIL - verifier command failed")
            return False

    live_story["status"] = "done"
    save_json(prd_path, prd)
    append_progress(progress_path, f"- {utc_now()} done {story_id}")
    print("[Verifier verdict] PASS")

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

    prd_path = repo_dir / args.prd_file
    state_path = repo_dir / args.state_file
    progress_path = repo_dir / args.progress_file

    load_json(prd_path, {"stories": []})
    load_json(state_path, {"failures": []})
    if not progress_path.exists():
        progress_path.write_text("# Ralph Progress\n\n", encoding="utf-8")

    iterations = 0
    while True:
        prd = load_json(prd_path, {"stories": []})
        story = pick_story(prd)
        if story is None:
            print("No todo stories left.")
            return 0

        ok = run_story(repo_dir, prd_path, state_path, progress_path, story, args.constraint)
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
