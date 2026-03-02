import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "skills" / "prd-md-to-json-codex" / "scripts" / "prd_md_to_json.py"


def run_convert(tmp_path: Path, md_text: str, *args: str) -> subprocess.CompletedProcess[str]:
    md = tmp_path / "prd.md"
    md.write_text(md_text, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(tmp_path), "--input", "prd.md", "--output", "prd.json", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_converts_story_sections_to_prd_json(tmp_path: Path) -> None:
    md = """
# Product PRD

## Story: Auth Login
id: S-001
priority: 1
Acceptance Criteria:
- user can login
- session persists
Constraints:
- must use existing db
Risks:
- auth regression
"""
    result = run_convert(tmp_path, md)
    assert result.returncode == 0, result.stderr
    prd = json.loads((tmp_path / "prd.json").read_text(encoding="utf-8"))
    s = prd["stories"][0]
    assert s["id"] == "S-001"
    assert s["mode"] == "phase-config"
    assert "user can login" in s["acceptance_criteria"]
    assert s["phase_config"]["implementer_commands"]
    assert s["phase_config"]["verifier_commands"]
    assert s["phase_config"]["qa_commands"]
    assert s["phase_config"]["specify_commands"][0] != ":"
    assert s["non_goals"]
    assert s["constraints"]
    assert s["dependencies"]
    assert s["risks"]
    assert s["success_metrics"]


def test_basic_mode_emits_builder_verifier_keys(tmp_path: Path) -> None:
    md = "## Story: One\npriority: 1\n"
    result = run_convert(tmp_path, md, "--mode", "basic")
    assert result.returncode == 0, result.stderr
    prd = json.loads((tmp_path / "prd.json").read_text(encoding="utf-8"))
    s = prd["stories"][0]
    assert "builder_commands" in s
    assert "verifier_commands" in s
    assert s["builder_commands"]
    assert s["verifier_commands"]


def test_merge_replaces_same_story_id(tmp_path: Path) -> None:
    (tmp_path / "prd.json").write_text(
        json.dumps({"stories": [{"id": "S-001", "title": "Old", "status": "todo", "priority": 9}]}),
        encoding="utf-8",
    )
    md = "## Story: New Title\nid: S-001\npriority: 1\n"
    result = run_convert(tmp_path, md, "--merge")
    assert result.returncode == 0, result.stderr
    prd = json.loads((tmp_path / "prd.json").read_text(encoding="utf-8"))
    assert len(prd["stories"]) == 1
    assert prd["stories"][0]["title"] == "New Title"


def test_phase_config_uses_explicit_command_sections_when_present(tmp_path: Path) -> None:
    md = """
## Story: Command Story
id: S-777
priority: 1
Implementer Commands:
- echo impl > impl.txt
Verifier Commands:
- test -f impl.txt
"""
    result = run_convert(tmp_path, md, "--mode", "phase-config")
    assert result.returncode == 0, result.stderr
    prd = json.loads((tmp_path / "prd.json").read_text(encoding="utf-8"))
    phase = prd["stories"][0]["phase_config"]
    assert phase["implementer_commands"] == ["echo impl > impl.txt"]
    assert phase["verifier_commands"] == ["test -f impl.txt"]
