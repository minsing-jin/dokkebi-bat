from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        path.write_text(json.dumps(default, indent=2) + "\n", encoding="utf-8")
        return json.loads(json.dumps(default))
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def append_progress(progress_path: Path, line: str) -> None:
    with progress_path.open("a", encoding="utf-8") as handle:
        handle.write(line.rstrip() + "\n")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def prepare_ralph_dirs(repo_dir: Path) -> Path:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    ralph_dir = repo_dir / ".ralph"
    logs_dir = ralph_dir / "logs"
    runs_dir = ralph_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    if logs_dir.exists() and any(logs_dir.iterdir()):
        archive_root = runs_dir / run_id
        archive_root.mkdir(parents=True, exist_ok=True)
        shutil.move(str(logs_dir), str(archive_root / "logs"))

    logs_dir.mkdir(parents=True, exist_ok=True)
    (repo_dir / "ERROR.md").unlink(missing_ok=True)
    return logs_dir


def log_command_output(log_path: Path, command: str, returncode: int, stdout: str, stderr: str) -> None:
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"$ {command}\n")
        handle.write(f"rc={returncode}\n")
        if stdout:
            handle.write(stdout)
            if not stdout.endswith("\n"):
                handle.write("\n")
        if stderr:
            handle.write("[stderr]\n")
            handle.write(stderr)
            if not stderr.endswith("\n"):
                handle.write("\n")
        handle.write("\n")
