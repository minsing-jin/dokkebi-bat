from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1] / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.runtime import interpolate


def test_interpolate_replaces_placeholder() -> None:
    cmd = interpolate("codex exec {{constraints}} --json", ["--dangerously-skip-permissions"])
    assert "--dangerously-skip-permissions" in cmd
    assert "{{constraints}}" not in cmd


def test_interpolate_auto_injects_constraints_for_codex_command() -> None:
    cmd = interpolate("codex exec --json", ["--dangerously-skip-permissions", "--allow-git-push"])
    assert "--dangerously-skip-permissions" in cmd
    assert "--allow-git-push" in cmd
