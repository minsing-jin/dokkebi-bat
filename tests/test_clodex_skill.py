from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_clodex_skill_exists_with_templates() -> None:
    skill_dir = REPO_ROOT / "skills" / "clodex"
    assert (skill_dir / "SKILL.md").exists()
    assert (skill_dir / "templates" / "context.md").exists()
    assert (skill_dir / "templates" / "plan.md").exists()
    assert (skill_dir / "templates" / "implementation_packet.md").exists()
    assert (skill_dir / "templates" / "status.md").exists()


def test_setup_script_installs_clodex() -> None:
    setup = (REPO_ROOT / "setup-dokkebi-loop.sh").read_text(encoding="utf-8")
    assert 'clodex_target="${skills_root}/clodex"' in setup
    assert 'link_skill_dir "$ROOT_DIR/skills/clodex" "$clodex_target"' in setup
    assert 'cp -R "$ROOT_DIR/skills/clodex" "$clodex_target"' in setup
