from __future__ import annotations

from pathlib import Path

from core.files import log_command_output
from core.models import CommandResult
from core.runtime import interpolate, run_shell


def run_commands(phase: str, commands: list[str], constraints: list[str], repo_dir: Path, log_path: Path) -> tuple[bool, list[CommandResult], CommandResult | None]:
    results: list[CommandResult] = []
    for raw in commands:
        cmd = interpolate(raw, constraints)
        result = run_shell(cmd, repo_dir)
        results.append(result)
        log_command_output(log_path, result.command, result.returncode, result.stdout, result.stderr)
        if result.returncode != 0:
            return False, results, result
    return True, results, None


def run_single_expect_fail(command: str, constraints: list[str], repo_dir: Path, log_path: Path) -> tuple[bool, CommandResult]:
    cmd = interpolate(command, constraints)
    result = run_shell(cmd, repo_dir)
    log_command_output(log_path, result.command, result.returncode, result.stdout, result.stderr)
    return result.returncode != 0, result


def run_single_expect_pass(command: str, constraints: list[str], repo_dir: Path, log_path: Path) -> tuple[bool, CommandResult]:
    cmd = interpolate(command, constraints)
    result = run_shell(cmd, repo_dir)
    log_command_output(log_path, result.command, result.returncode, result.stdout, result.stderr)
    return result.returncode == 0, result
