import json
import subprocess
import sys
from pathlib import Path

def find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        candidate = parent / "skills" / "dokkebi-loop-codex" / "scripts" / "ralph_loop.py"
        if candidate.exists():
            return parent
    raise RuntimeError("could not locate repository root for ralph_loop.py")


REPO_ROOT = find_repo_root()
SCRIPT = REPO_ROOT / "skills" / "dokkebi-loop-codex" / "scripts" / "ralph_loop.py"


def run_loop(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(tmp_path), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def write_prd(tmp_path: Path, stories: list[dict]) -> None:
    normalized: list[dict] = []
    for idx, story in enumerate(stories, start=1):
        item = dict(story)
        item.setdefault("priority", idx)
        item.setdefault("acceptance_criteria", [f"{item.get('title', f'Story {idx}')} passes verifier commands"])
        item.setdefault("non_goals", [])
        item.setdefault("constraints", [])
        item.setdefault("dependencies", [])
        item.setdefault("risks", [])
        item.setdefault("success_metrics", [])
        normalized.append(item)
    (tmp_path / "prd.json").write_text(json.dumps({"stories": normalized}, indent=2), encoding="utf-8")


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


def test_default_constraint_is_applied_without_flag(tmp_path: Path) -> None:
    write_agents(tmp_path)
    write_prd(
        tmp_path,
        [
            {
                "id": "S-3B",
                "title": "default constraints",
                "status": "todo",
                "builder_commands": ["printf '%s' '{{constraints}}' > constraints.txt"],
                "verifier_commands": ["grep -q -- '--dangerously-skip-permissions' constraints.txt"],
            }
        ],
    )

    result = run_loop(tmp_path)

    assert result.returncode == 0, result.stderr
    constraints = (tmp_path / "constraints.txt").read_text(encoding="utf-8")
    assert "--dangerously-skip-permissions" in constraints


def test_default_constraints_include_git_push_permission(tmp_path: Path) -> None:
    write_agents(tmp_path)
    write_prd(
        tmp_path,
        [
            {
                "id": "S-3C",
                "title": "default constraints include push",
                "status": "todo",
                "builder_commands": ["printf '%s' '{{constraints}}' > constraints.txt"],
                "verifier_commands": ["grep -q -- '--allow-git-push' constraints.txt"],
            }
        ],
    )

    result = run_loop(tmp_path)

    assert result.returncode == 0, result.stderr
    constraints = (tmp_path / "constraints.txt").read_text(encoding="utf-8")
    assert "--allow-git-push" in constraints


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


def test_auto_creates_agents_md_by_default(tmp_path: Path) -> None:
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
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "AGENTS.md").exists()
    agents_text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "### implementer" in agents_text
    assert "### verifier" in agents_text
    assert "### planner" in agents_text
    assert "### issue tiger" in agents_text


def test_strict_agents_md_requires_existing_file(tmp_path: Path) -> None:
    write_prd(
        tmp_path,
        [
            {
                "id": "S-6B",
                "title": "strict agents check",
                "status": "todo",
                "builder_commands": ["true"],
                "verifier_commands": ["true"],
            }
        ],
    )
    result = run_loop(tmp_path, "--strict-agents-md")
    assert result.returncode == 1
    assert "AGENTS.md not found" in result.stderr


def test_prd_validation_fails_when_required_fields_missing(tmp_path: Path) -> None:
    write_agents(tmp_path)
    (tmp_path / "prd.json").write_text(
        json.dumps(
            {
                "stories": [
                    {
                        "id": "S-VAL-1",
                        "title": "invalid",
                        "status": "todo",
                        "builder_commands": ["true"],
                        "verifier_commands": ["true"],
                    }
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    result = run_loop(tmp_path)
    assert result.returncode == 1
    assert "Strict PRD validation failed" in result.stderr
    assert (tmp_path / "PRD_VALIDATION_ERRORS.md").exists()


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


def test_attempt_trace_log_contains_story_status_and_commands(tmp_path: Path) -> None:
    write_agents(tmp_path)
    write_prd(
        tmp_path,
        [
            {
                "id": "S-12",
                "title": "trace log",
                "status": "todo",
                "builder_commands": ["echo build > build.txt"],
                "verifier_commands": ["test -f build.txt"],
            }
        ],
    )

    result = run_loop(tmp_path)
    assert result.returncode == 0, result.stderr

    trace_files = list((tmp_path / ".ralph" / "logs").glob("S-12-attempt-1.json"))
    assert trace_files
    trace = json.loads(trace_files[0].read_text(encoding="utf-8"))
    assert trace["story_id"] == "S-12"
    assert trace["attempt"] == 1
    assert trace["outcome"] == "pass"
    assert trace["builder"][0]["command"] == "echo build > build.txt"
    assert trace["verifier"][0]["returncode"] == 0


def test_review_commands_failure_keeps_story_todo(tmp_path: Path) -> None:
    write_agents(tmp_path)
    write_prd(
        tmp_path,
        [
            {
                "id": "S-13",
                "title": "review fail",
                "status": "todo",
                "builder_commands": ["true"],
                "verifier_commands": ["true"],
                "review_commands": ["false"],
            }
        ],
    )

    result = run_loop(tmp_path, "--skip-gate")
    assert result.returncode == 1
    story = read_prd(tmp_path)["stories"][0]
    assert story["status"] == "todo"


def test_tdd_cycle_runs_red_then_green(tmp_path: Path) -> None:
    write_agents(tmp_path)
    write_prd(
        tmp_path,
        [
            {
                "id": "S-14",
                "title": "tdd cycle",
                "status": "todo",
                "tdd_red_command": "test -f out.txt",
                "builder_commands": ["echo ok > out.txt"],
                "verifier_commands": ["test -f out.txt"],
                "tdd_green_command": "test -f out.txt",
            }
        ],
    )

    result = run_loop(tmp_path, "--skip-gate")
    assert result.returncode == 0, result.stderr
    story = read_prd(tmp_path)["stories"][0]
    assert story["status"] == "done"


def test_gate_command_runs_and_is_logged(tmp_path: Path) -> None:
    write_agents(tmp_path)
    write_prd(
        tmp_path,
        [
            {
                "id": "S-15",
                "title": "gate log",
                "status": "todo",
                "builder_commands": ["true"],
                "verifier_commands": ["true"],
            }
        ],
    )

    result = run_loop(tmp_path, "--gate-command", "echo gate-ok > gate.txt")
    assert result.returncode == 0, result.stderr
    trace = json.loads((tmp_path / ".ralph" / "logs" / "S-15-attempt-1.json").read_text(encoding="utf-8"))
    assert trace["gate"]["command"] == "echo gate-ok > gate.txt"
    assert trace["gate"]["returncode"] == 0


def test_phase_config_artifact_contract_and_progress_jsonl(tmp_path: Path) -> None:
    write_agents(tmp_path)
    write_prd(
        tmp_path,
        [
            {
                "id": "V2-1",
                "title": "phase-config pass",
                "mode": "phase-config",
                "status": "todo",
                "phase_config": {
                    "implementer_commands": ["echo phase > out.txt"],
                    "verifier_commands": ["test -f out.txt"],
                },
            }
        ],
    )
    result = run_loop(tmp_path, "--mode", "phase-config", "--skip-gate")
    assert result.returncode == 0, result.stderr
    story_dir = tmp_path / "stories" / "V2-1"
    assert (story_dir / "story.md").exists()
    assert (story_dir / "plan.md").exists()
    assert (story_dir / "context_pack.md").exists()
    assert (story_dir / "evidence.md").exists()
    events = (tmp_path / "PROGRESS.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert events
    last = json.loads(events[-1])
    assert last["status"] == "PASS"
    assert last["story_id"] == "V2-1"


def test_phase_config_extra_roles_are_executed(tmp_path: Path) -> None:
    write_agents(tmp_path)
    write_prd(
        tmp_path,
        [
            {
                "id": "PX-1",
                "title": "extra roles",
                "mode": "phase-config",
                "status": "todo",
                "phase_config": {
                    "specify_commands": ["echo s > specify.txt"],
                    "planner_commands": ["echo p > planner.txt"],
                    "context_scribe_commands": ["echo c > context.txt"],
                    "show_me_hook_commands": ["echo h > hook.txt"],
                    "implementer_commands": ["echo i > impl.txt"],
                    "testsmith_commands": ["grep -q i impl.txt"],
                    "verifier_commands": ["test -f impl.txt"],
                    "review_commands": ["grep -q i impl.txt"],
                    "issue_tiger_commands": ["echo t > issue.txt"],
                    "qa_commands": ["test -f issue.txt"]
                },
            }
        ],
    )
    result = run_loop(tmp_path, "--mode", "phase-config", "--skip-gate")
    assert result.returncode == 0, result.stderr
    for name in ["specify.txt", "planner.txt", "context.txt", "hook.txt", "impl.txt", "issue.txt"]:
        assert (tmp_path / name).exists()
    trace = json.loads((tmp_path / ".ralph" / "logs" / "PX-1-attempt-1.json").read_text(encoding="utf-8"))
    assert trace["specify"][0]["returncode"] == 0
    assert trace["planner"][0]["returncode"] == 0
    assert trace["context_scribe"][0]["returncode"] == 0
    assert trace["show_me_hook"][0]["returncode"] == 0
    assert trace["issue_tiger"][0]["returncode"] == 0


def test_failure_writes_errors_and_lessons(tmp_path: Path) -> None:
    write_agents(tmp_path)
    write_prd(
        tmp_path,
        [
            {
                "id": "V2-2",
                "title": "phase-config fail",
                "mode": "phase-config",
                "status": "todo",
                "phase_config": {
                    "implementer_commands": ["true"],
                    "verifier_commands": ["false"],
                },
            }
        ],
    )
    result = run_loop(tmp_path, "--mode", "phase-config", "--skip-gate", "--max-retries", "1")
    assert result.returncode == 1
    story_dir = tmp_path / "stories" / "V2-2"
    assert (story_dir / "errors.md").exists()
    lessons = (tmp_path / "LESSONS.md").read_text(encoding="utf-8")
    assert "V2-2" in lessons


def test_story_id_selects_single_story(tmp_path: Path) -> None:
    write_agents(tmp_path)
    write_prd(
        tmp_path,
        [
            {
                "id": "A",
                "title": "a",
                "status": "todo",
                "builder_commands": ["echo a > a.txt"],
                "verifier_commands": ["test -f a.txt"],
            },
            {
                "id": "B",
                "title": "b",
                "status": "todo",
                "builder_commands": ["echo b > b.txt"],
                "verifier_commands": ["test -f b.txt"],
            },
        ],
    )
    result = run_loop(tmp_path, "--story-id", "B", "--skip-gate")
    assert result.returncode == 0, result.stderr
    payload = read_prd(tmp_path)["stories"]
    statuses = {s["id"]: s["status"] for s in payload}
    assert statuses["A"] == "todo"
    assert statuses["B"] == "done"


def test_bootstrap_prd_then_runs_story(tmp_path: Path) -> None:
    input_json = tmp_path / "idea.json"
    input_json.write_text(
        json.dumps(
            {
                "project": {"title": "Boot", "goal": "Boot goal"},
                "stories": [
                    {
                        "id": "B-001",
                        "title": "boot story",
                        "priority": 1,
                        "acceptance_criteria": ["creates file"],
                        "phase_config": {
                            "implementer_commands": ["echo boot > boot.txt"],
                            "verifier_commands": ["test -f boot.txt"],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    result = run_loop(
        tmp_path,
        "--bootstrap-prd",
        "--bootstrap-input-json",
        str(input_json),
        "--mode",
        "phase-config",
        "--skip-gate",
    )
    assert result.returncode == 0, result.stderr
    prd = read_prd(tmp_path)
    assert prd["stories"][0]["id"] == "B-001"
    assert prd["stories"][0]["status"] == "done"
    assert (tmp_path / "boot.txt").exists()


def test_show_me_hook_updates_priority_before_pick(tmp_path: Path) -> None:
    write_agents(tmp_path)
    write_prd(
        tmp_path,
        [
            {
                "id": "A",
                "title": "a",
                "status": "todo",
                "priority": 1,
                "builder_commands": ["echo a > a.txt"],
                "verifier_commands": ["test -f a.txt"],
            },
            {
                "id": "B",
                "title": "b",
                "status": "todo",
                "priority": 2,
                "builder_commands": ["echo b > b.txt"],
                "verifier_commands": ["test -f b.txt"],
            },
        ],
    )
    hook_dir = tmp_path / ".ralph"
    hook_dir.mkdir(parents=True, exist_ok=True)
    (hook_dir / "hook_requests.json").write_text(
        json.dumps(
            {
                "requests": [
                    {"action": "update_priority", "id": "B", "priority": 0},
                ]
            }
        ),
        encoding="utf-8",
    )
    result = run_loop(tmp_path, "--skip-gate")
    assert result.returncode == 0, result.stderr
    payload = read_prd(tmp_path)["stories"]
    statuses = {s["id"]: s["status"] for s in payload}
    assert statuses["B"] == "done"


def test_issue_tiger_builtin_writes_plan(tmp_path: Path) -> None:
    write_agents(tmp_path)
    write_prd(
        tmp_path,
        [
            {
                "id": "I-1",
                "title": "issue tiger",
                "status": "todo",
                "builder_commands": ["true"],
                "verifier_commands": ["true"],
            }
        ],
    )
    issues_dir = tmp_path / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)
    (issues_dir / "I-1.json").write_text(json.dumps({"branch": "feature/i-1", "pr_title": "I-1 PR"}), encoding="utf-8")
    result = run_loop(tmp_path, "--skip-gate")
    assert result.returncode == 0, result.stderr
    assert (tmp_path / ".ralph" / "issue_tiger" / "I-1.md").exists()


def test_issue_tiger_runs_issue_commands(tmp_path: Path) -> None:
    write_agents(tmp_path)
    write_prd(
        tmp_path,
        [
            {
                "id": "I-2",
                "title": "issue command",
                "status": "todo",
                "builder_commands": ["true"],
                "verifier_commands": ["true"],
            }
        ],
    )
    issues_dir = tmp_path / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)
    (issues_dir / "I-2.json").write_text(
        json.dumps({"commands": ["echo issue-run > issue-run.txt"]}),
        encoding="utf-8",
    )
    result = run_loop(tmp_path, "--skip-gate")
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "issue-run.txt").exists()


def test_qa_dr_strange_writes_e2e_evidence(tmp_path: Path) -> None:
    write_agents(tmp_path)
    write_prd(
        tmp_path,
        [
            {
                "id": "Q-1",
                "title": "qa",
                "status": "todo",
                "builder_commands": ["true"],
                "verifier_commands": ["true"],
            }
        ],
    )
    result = run_loop(tmp_path, "--loop", "--skip-gate")
    assert result.returncode == 0, result.stderr
    evidence = tmp_path / "E2E_EVIDENCE.md"
    assert evidence.exists()
    assert "total_stories" in evidence.read_text(encoding="utf-8")


def test_qa_dr_strange_fails_on_scenario_failure(tmp_path: Path) -> None:
    write_agents(tmp_path)
    (tmp_path / "prd.json").write_text(
        json.dumps(
            {
                "stories": [
                    {"id": "QX", "title": "already done", "status": "done", "priority": 1}
                ],
                "qa": {
                    "scenarios": [
                        {"name": "broken", "command": "false", "story_id": "QX"}
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    result = run_loop(tmp_path, "--loop", "--skip-gate")
    assert result.returncode == 1
    content = (tmp_path / "E2E_EVIDENCE.md").read_text(encoding="utf-8")
    assert "broken" in content


def test_qa_dr_strange_requeues_failed_story_and_writes_errors(tmp_path: Path) -> None:
    write_agents(tmp_path)
    (tmp_path / "prd.json").write_text(
        json.dumps(
            {
                "stories": [
                    {"id": "Q-RETRY-1", "title": "done story", "status": "done", "priority": 1}
                ],
                "qa": {
                    "discover_checks": False,
                    "auto_checks": [
                        {"name": "mapped fail", "command": "false", "story_id": "Q-RETRY-1"}
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    result = run_loop(tmp_path, "--loop", "--skip-gate")
    assert result.returncode == 1
    prd = read_prd(tmp_path)
    assert prd["stories"][0]["status"] == "todo"
    assert (tmp_path / "stories" / "Q-RETRY-1" / "errors.md").exists()
    assert (tmp_path / ".ralph" / "qa_dr_strange_result.json").exists()
    lessons = (tmp_path / "LESSONS.md").read_text(encoding="utf-8")
    assert "qa-dr-strange" in lessons


def test_planner_builtin_creates_adr_when_options_provided(tmp_path: Path) -> None:
    write_agents(tmp_path)
    write_prd(
        tmp_path,
        [
            {
                "id": "P-1",
                "title": "planner adr",
                "status": "todo",
                "builder_commands": ["true"],
                "verifier_commands": ["true"],
                "tech_stack_options": ["A", "B"],
                "selected_stack": "A",
                "adr_topic": "Stack Decision",
            }
        ],
    )
    result = run_loop(tmp_path, "--skip-gate")
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "stories" / "P-1" / "ADR" / "0001-stack-choice.md").exists()


def test_evidence_contains_soft_gate_and_devils_advocate(tmp_path: Path) -> None:
    write_agents(tmp_path)
    write_prd(
        tmp_path,
        [
            {
                "id": "V-1",
                "title": "feedback",
                "status": "todo",
                "builder_commands": ["echo x > x.txt"],
                "testsmith_commands": ["grep -q x x.txt"],
                "verifier_commands": ["test -f x.txt"],
                "review_commands": ["grep -q x x.txt"],
                "tech_stack_options": ["A", "B"],
                "selected_stack": "A",
            }
        ],
    )
    result = run_loop(tmp_path, "--skip-gate")
    assert result.returncode == 0, result.stderr
    evidence = (tmp_path / "stories" / "V-1" / "evidence.md").read_text(encoding="utf-8")
    assert "Soft Gate Scores" in evidence
    assert "Devils Advocate" in evidence
