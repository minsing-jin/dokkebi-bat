#!/usr/bin/env bash
# PostToolUse hook: append lightweight workflow audit lines.
set -euo pipefail

ROOT="${DOKKEBI_HOOK_ROOT:-$HOME}"
AUDIT_DIR="$ROOT/.ralph/hooks"
AUDIT_LOG="$AUDIT_DIR/post-tool-audit.log"

INPUT=$(cat || true)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null || true)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null || true)

[[ "$TOOL_NAME" == "Bash" ]] || exit 0
[[ -n "$COMMAND" ]] || exit 0

mkdir -p "$AUDIT_DIR"
{
  printf '%s ' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  printf 'tool=%s ' "$TOOL_NAME"
  printf 'cmd=%q\n' "$COMMAND"
} >> "$AUDIT_LOG"
