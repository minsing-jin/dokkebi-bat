import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1] / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.policy import evaluate_command_policy, load_permission_policy


def policy_path() -> Path:
    return Path(__file__).resolve().parents[1] / "policy" / "permission_policy.json"


def test_balanced_denies_env_access() -> None:
    policy = load_permission_policy(policy_path(), "balanced")
    decision = evaluate_command_policy("cat .env", policy)
    assert decision.decision == "deny"


def test_balanced_allows_psql_select() -> None:
    policy = load_permission_policy(policy_path(), "balanced")
    decision = evaluate_command_policy("psql -c \"SELECT 1\"", policy)
    assert decision.decision == "allow"


def test_balanced_denies_psql_drop() -> None:
    policy = load_permission_policy(policy_path(), "balanced")
    decision = evaluate_command_policy("psql -c \"DROP TABLE users\"", policy)
    assert decision.decision == "deny"


def test_balanced_denies_direct_push_to_main() -> None:
    policy = load_permission_policy(policy_path(), "balanced")
    decision = evaluate_command_policy("git push origin main", policy)
    assert decision.decision == "deny"


def test_invalid_profile_raises_value_error(tmp_path: Path) -> None:
    data = {"profiles": {"balanced": {"deny_patterns": [], "ask_patterns": [], "allow_patterns": []}}}
    p = tmp_path / "policy.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    try:
        load_permission_policy(p, "strict")
    except ValueError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("expected ValueError for missing profile")
