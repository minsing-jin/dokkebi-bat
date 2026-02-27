import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "ralph_loop.py"


def run_loop(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(tmp_path), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def write_prd(tmp_path: Path, stories: list[dict]) -> None:
    (tmp_path / "prd.json").write_text(json.dumps({"stories": stories}, indent=2), encoding="utf-8")


def read_prd(tmp_path: Path) -> dict:
    return json.loads((tmp_path / "prd.json").read_text(encoding="utf-8"))


def test_single_story_success_marks_done(tmp_path: Path) -> None:
    write_prd(
        tmp_path,
        [
            {
                "id": "S-1",
                "title": "echo",
                "status": "todo",
                "builder_commands": ["echo build > built.txt"],
                "verifier_commands": ["test -f built.txt"],
            }
        ],
    )

    result = run_loop(tmp_path)

    assert result.returncode == 0, result.stderr
    story = read_prd(tmp_path)["stories"][0]
    assert story["status"] == "done"
    assert (tmp_path / "built.txt").exists()


def test_verifier_failure_keeps_story_todo(tmp_path: Path) -> None:
    write_prd(
        tmp_path,
        [
            {
                "id": "S-2",
                "title": "fail verify",
                "status": "todo",
                "builder_commands": ["echo x > out.txt"],
                "verifier_commands": ["test -f missing.txt"],
            }
        ],
    )

    result = run_loop(tmp_path)

    assert result.returncode == 1
    story = read_prd(tmp_path)["stories"][0]
    assert story["status"] == "todo"


def test_constraint_placeholder_is_interpolated(tmp_path: Path) -> None:
    write_prd(
        tmp_path,
        [
            {
                "id": "S-3",
                "title": "constraints",
                "status": "todo",
                "builder_commands": ["printf '%s' '{{constraints}}' > constraints.txt"],
                "verifier_commands": ["grep -q -- '--dangerously-skip-permissions' constraints.txt"],
            }
        ],
    )

    result = run_loop(tmp_path, "--constraint", "--dangerously-skip-permissions")

    assert result.returncode == 0, result.stderr
    constraints = (tmp_path / "constraints.txt").read_text(encoding="utf-8")
    assert "--dangerously-skip-permissions" in constraints


def test_loop_mode_processes_all_todo_stories(tmp_path: Path) -> None:
    write_prd(
        tmp_path,
        [
            {
                "id": "S-4",
                "title": "one",
                "status": "todo",
                "builder_commands": ["echo one >> done.log"],
                "verifier_commands": ["grep -q one done.log"],
            },
            {
                "id": "S-5",
                "title": "two",
                "status": "todo",
                "builder_commands": ["echo two >> done.log"],
                "verifier_commands": ["grep -q two done.log"],
            },
        ],
    )

    result = run_loop(tmp_path, "--loop")

    assert result.returncode == 0, result.stderr
    statuses = [story["status"] for story in read_prd(tmp_path)["stories"]]
    assert statuses == ["done", "done"]
