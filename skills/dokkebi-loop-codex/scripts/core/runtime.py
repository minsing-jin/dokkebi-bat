from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from core.models import CommandResult


def interpolate(command: str, constraints: list[str]) -> str:
    unique_constraints = list(dict.fromkeys(constraints))
    rendered_constraints = " ".join(shlex.quote(flag) for flag in unique_constraints)
    if "{{constraints}}" in command:
        return command.replace("{{constraints}}", rendered_constraints)
    stripped = command.lstrip()
    # Auto-inject constraints for codex execution commands when placeholder is omitted.
    if rendered_constraints and (stripped.startswith("codex ") or stripped.startswith("codex\n")):
        return f"{command} {rendered_constraints}"
    return command


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


def command_result_as_dict(result: CommandResult) -> dict[str, object]:
    return {
        "command": result.command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def run_git_capture(repo_dir: Path, args: list[str]) -> str:
    proc = subprocess.run(["git", *args], cwd=repo_dir, capture_output=True, text=True, check=False)
    return (proc.stdout or proc.stderr or "").strip()


def capture_git_snapshot(repo_dir: Path) -> dict[str, object]:
    inside = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    if inside.returncode != 0:
        return {"is_git_repo": False}
    return {
        "is_git_repo": True,
        "status_short": run_git_capture(repo_dir, ["status", "--short"]),
        "diff_stat": run_git_capture(repo_dir, ["diff", "--stat"]),
        "head": run_git_capture(repo_dir, ["rev-parse", "--short", "HEAD"]),
    }
