from __future__ import annotations

import json
import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class PolicyDecision:
    decision: str  # allow | ask | deny
    reason: str
    matched_rule: str = ""


@dataclass
class PermissionPolicy:
    profile: str
    deny_patterns: list[dict[str, str]]
    ask_patterns: list[dict[str, str]]
    allow_patterns: list[dict[str, str]]
    secret_path_regex: str
    psql_write_keywords: list[str]
    psql_deny_keywords: list[str]
    psql_read_starts: list[str]


def _as_rule_list(raw: Any) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        pattern = str(item.get("pattern", "")).strip()
        if not pattern:
            continue
        out.append(
            {
                "pattern": pattern,
                "reason": str(item.get("reason", "")).strip() or "matched policy rule",
            }
        )
    return out


def load_permission_policy(path: Path, profile: str) -> PermissionPolicy:
    payload = json.loads(path.read_text(encoding="utf-8"))
    profiles = payload.get("profiles", {})
    if not isinstance(profiles, dict):
        raise ValueError("permission policy `profiles` must be an object")
    selected = profiles.get(profile)
    if not isinstance(selected, dict):
        available = ", ".join(sorted(str(k) for k in profiles.keys()))
        raise ValueError(f"permission profile `{profile}` not found (available: {available})")

    psql = selected.get("psql", {})
    if not isinstance(psql, dict):
        psql = {}

    return PermissionPolicy(
        profile=profile,
        deny_patterns=_as_rule_list(selected.get("deny_patterns")),
        ask_patterns=_as_rule_list(selected.get("ask_patterns")),
        allow_patterns=_as_rule_list(selected.get("allow_patterns")),
        secret_path_regex=str(selected.get("secret_path_regex", r"(^|[ \t\"'/])\\.env(\\.[^ \t\"'/]+)?($|[ \t\"'/])")),
        psql_write_keywords=[str(x).lower() for x in psql.get("write_keywords", []) if str(x).strip()],
        psql_deny_keywords=[str(x).lower() for x in psql.get("deny_keywords", []) if str(x).strip()],
        psql_read_starts=[str(x).lower() for x in psql.get("read_starts", []) if str(x).strip()],
    )


def _split_tokens(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except Exception:
        return command.split()


def _contains_secret_path(command: str, policy: PermissionPolicy) -> bool:
    return bool(re.search(policy.secret_path_regex, command))


def _find_psql_index(tokens: list[str]) -> int | None:
    idx = 0
    while idx < len(tokens) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=.*$", tokens[idx]):
        idx += 1
    if idx < len(tokens):
        tok = tokens[idx]
        if tok == "psql" or tok.endswith("/psql") or tok.endswith("\\psql.exe"):
            return idx
    return None


def _extract_psql_sql(tokens: list[str], psql_idx: int) -> str | None:
    idx = psql_idx + 1
    while idx < len(tokens):
        token = tokens[idx]
        if token in ("-c", "--command"):
            return tokens[idx + 1] if idx + 1 < len(tokens) else ""
        if token.startswith("--command="):
            return token.split("=", 1)[1]
        if token in ("-f", "--file"):
            return None
        idx += 1
    return None


def _classify_psql_sql(sql: str, policy: PermissionPolicy) -> PolicyDecision:
    text = (sql or "").strip()
    low = text.lower()

    for kw in policy.psql_deny_keywords:
        if re.search(rf"\b{re.escape(kw)}\b", low):
            return PolicyDecision("deny", f"psql statement contains denied keyword `{kw}`", f"psql.deny.{kw}")

    starts_read = any(re.match(rf"^{re.escape(prefix)}\b", low) for prefix in policy.psql_read_starts)
    has_into = bool(re.search(r"\binto\b", low))
    has_write = any(re.search(rf"\b{re.escape(kw)}\b", low) for kw in policy.psql_write_keywords)
    if starts_read and not has_into and not has_write:
        return PolicyDecision("allow", "psql read-only query", "psql.read")

    return PolicyDecision("ask", "psql non-read query requires confirmation", "psql.ask")


def evaluate_command_policy(command: str, policy: PermissionPolicy) -> PolicyDecision:
    if _contains_secret_path(command, policy):
        return PolicyDecision("deny", "sensitive .env path access denied", "secret_path")

    tokens = _split_tokens(command)
    psql_idx = _find_psql_index(tokens)
    if psql_idx is not None:
        sql = _extract_psql_sql(tokens, psql_idx)
        if sql is None:
            return PolicyDecision("ask", "psql interactive/file execution requires confirmation", "psql.file_or_interactive")
        return _classify_psql_sql(sql, policy)

    for rule in policy.deny_patterns:
        if re.search(rule["pattern"], command):
            return PolicyDecision("deny", rule["reason"], rule["pattern"])
    for rule in policy.ask_patterns:
        if re.search(rule["pattern"], command):
            return PolicyDecision("ask", rule["reason"], rule["pattern"])
    for rule in policy.allow_patterns:
        if re.search(rule["pattern"], command):
            return PolicyDecision("allow", rule["reason"], rule["pattern"])
    return PolicyDecision("allow", "no matching deny/ask rule; allow by default", "default_allow")

