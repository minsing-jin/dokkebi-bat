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


def write_agents(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")


def test_single_story_success_marks_done(tmp_path: Path) -> None:
    write_agents(tmp_path)
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
    write_agents(tmp_path)
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
    write_agents(tmp_path)
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
    write_agents(tmp_path)
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


def test_requires_agents_md_by_default(tmp_path: Path) -> None:
    write_prd(
        tmp_path,
        [
            {
                "id": "S-6",
                "title": "agents check",
                "status": "todo",
                "builder_commands": ["true"],
                "verifier_commands": ["true"],
            }
        ],
    )
    result = run_loop(tmp_path)
    assert result.returncode == 1
    assert "AGENTS.md not found" in result.stderr


def test_priority_order_uses_lowest_number_first(tmp_path: Path) -> None:
    write_agents(tmp_path)
    write_prd(
        tmp_path,
        [
            {
                "id": "S-7",
                "title": "low priority",
                "status": "todo",
                "priority": 5,
                "builder_commands": ["echo S7 >> order.log"],
                "verifier_commands": ["grep -q S7 order.log"],
            },
            {
                "id": "S-8",
                "title": "high priority",
                "status": "todo",
                "priority": 1,
                "builder_commands": ["echo S8 >> order.log"],
                "verifier_commands": ["grep -q S8 order.log"],
            },
        ],
    )
    result = run_loop(tmp_path, "--loop")
    assert result.returncode == 0, result.stderr
    lines = (tmp_path / "order.log").read_text(encoding="utf-8").strip().splitlines()
    assert lines[0] == "S8"


def test_retry_then_passes_with_error_md_signal(tmp_path: Path) -> None:
    write_agents(tmp_path)
    write_prd(
        tmp_path,
        [
            {
                "id": "S-9",
                "title": "retry pass",
                "status": "todo",
                "builder_commands": [
                    "count=0; [ -f .count ] && count=$(cat .count); count=$((count+1)); echo $count > .count"
                ],
                "verifier_commands": [
                    "if [ \"$(cat .count)\" -lt 2 ]; then echo '# Error' > ERROR.md; false; else rm -f ERROR.md; true; fi"
                ],
            }
        ],
    )
    result = run_loop(tmp_path, "--max-retries", "3")
    assert result.returncode == 0, result.stderr
    assert read_prd(tmp_path)["stories"][0]["status"] == "done"


def test_exhausted_retries_returns_nonzero(tmp_path: Path) -> None:
    write_agents(tmp_path)
    write_prd(
        tmp_path,
        [
            {
                "id": "S-10",
                "title": "retry fail",
                "status": "todo",
                "builder_commands": ["true"],
                "verifier_commands": ["echo '# Error' > ERROR.md; false"],
            }
        ],
    )
    result = run_loop(tmp_path, "--max-retries", "2")
    assert result.returncode == 1
    assert read_prd(tmp_path)["stories"][0]["status"] == "todo"


def test_archives_previous_logs_on_startup(tmp_path: Path) -> None:
    write_agents(tmp_path)
    stale_dir = tmp_path / ".ralph" / "logs"
    stale_dir.mkdir(parents=True)
    (stale_dir / "old.log").write_text("stale\n", encoding="utf-8")

    write_prd(
        tmp_path,
        [
            {
                "id": "S-11",
                "title": "archive logs",
                "status": "todo",
                "builder_commands": ["true"],
                "verifier_commands": ["true"],
            }
        ],
    )
    result = run_loop(tmp_path)
    assert result.returncode == 0, result.stderr
    runs = list((tmp_path / ".ralph" / "runs").glob("*/logs/old.log"))
    assert runs, "old logs should be archived under .ralph/runs/<run_id>/logs"
