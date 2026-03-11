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


def test_superpower_bridge_exists_and_is_installed() -> None:
    skill_dir = REPO_ROOT / "skills" / "superpower"
    assert (skill_dir / "SKILL.md").exists()
    assert (skill_dir / "registry.json").exists()
    assert (skill_dir / "scripts" / "list_superpowers.py").exists()
    assert (skill_dir / "scripts" / "activate_superpower.sh").exists()

    setup = (REPO_ROOT / "setup-dokkebi-loop.sh").read_text(encoding="utf-8")
    assert 'superpower_target="${skills_root}/superpower"' in setup
    assert 'link_skill_dir "$ROOT_DIR/skills/superpower" "$superpower_target"' in setup
    assert 'cp -R "$ROOT_DIR/skills/superpower" "$superpower_target"' in setup


def test_superpower_only_script_exists() -> None:
    script = REPO_ROOT / "scripts" / "enable_superpower_only.sh"
    assert script.exists()
    text = script.read_text(encoding="utf-8")
    assert 'SKILLS_ROOT="${HOME}/.codex/skills"' in text
    assert '[ "$name" = ".system" ] || [ "$name" = "superpower" ]' in text
