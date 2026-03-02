import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "skills" / "specify-gidometa-codex" / "scripts" / "specify_gidometa.py"


def run_specify(tmp_path: Path, input_payload: dict) -> subprocess.CompletedProcess[str]:
    input_file = tmp_path / "input.json"
    input_file.write_text(json.dumps(input_payload, ensure_ascii=False), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(tmp_path), "--input-json", str(input_file)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_generates_prd_and_story_docs(tmp_path: Path) -> None:
    payload = {
        "project": {"title": "My Product", "goal": "Ship MVP"},
        "stories": [
            {
                "id": "S-001",
                "title": "Auth",
                "priority": 1,
                "acceptance_criteria": ["login works"],
                "non_goals": [],
                "constraints": [],
                "dependencies": [],
                "risks": [],
                "success_metrics": [],
            }
        ],
    }
    result = run_specify(tmp_path, payload)
    assert result.returncode == 0, result.stderr

    prd = json.loads((tmp_path / "prd.json").read_text(encoding="utf-8"))
    assert prd["stories"][0]["id"] == "S-001"
    assert prd["stories"][0]["mode"] == "phase-config"
    assert prd["stories"][0]["phase_config"]["implementer_commands"]
    assert prd["stories"][0]["phase_config"]["verifier_commands"]
    assert prd["stories"][0]["phase_config"]["specify_commands"][0] != ":"
    assert prd["stories"][0]["non_goals"]
    assert prd["stories"][0]["constraints"]
    assert prd["stories"][0]["dependencies"]
    assert prd["stories"][0]["risks"]
    assert prd["stories"][0]["success_metrics"]
    assert (tmp_path / "stories" / "S-001" / "story.md").exists()


def test_merges_by_story_id(tmp_path: Path) -> None:
    (tmp_path / "prd.json").write_text(
        json.dumps(
            {
                "stories": [
                    {
                        "id": "S-001",
                        "title": "Old",
                        "status": "todo",
                        "priority": 9,
                        "builder_commands": ["true"],
                        "verifier_commands": ["true"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    payload = {
        "project": {"title": "My Product", "goal": "Ship MVP"},
        "stories": [
            {
                "id": "S-001",
                "title": "New",
                "priority": 1,
                "acceptance_criteria": ["new"],
                "non_goals": [],
                "constraints": [],
                "dependencies": [],
                "risks": [],
                "success_metrics": [],
            }
        ],
    }
    result = run_specify(tmp_path, payload)
    assert result.returncode == 0, result.stderr

    prd = json.loads((tmp_path / "prd.json").read_text(encoding="utf-8"))
    assert len(prd["stories"]) == 1
    assert prd["stories"][0]["title"] == "New"
    assert prd["stories"][0]["priority"] == 1


def test_generates_arch_conventions_and_adr_when_requested(tmp_path: Path) -> None:
    payload = {
        "project": {"title": "Advanced Product", "goal": "Ship robust platform"},
        "tech_stack": {
            "framework": "FastAPI",
            "database": "PostgreSQL",
            "infrastructure": "AWS",
            "deployment": "container",
            "test_strategy": "unit+integration+e2e",
        },
        "generate": {"arch": True, "conventions": True, "adr": True},
        "stories": [
            {
                "id": "S-010",
                "title": "Core API",
                "priority": 1,
                "acceptance_criteria": ["core endpoint works"],
            }
        ],
    }
    result = run_specify(tmp_path, payload)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "ARCH.md").exists()
    assert (tmp_path / "CONVENTIONS.md").exists()
    assert (tmp_path / "ADR" / "0001-tech-stack.md").exists()
