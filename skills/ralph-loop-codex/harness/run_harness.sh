#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
TMP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

cp "$ROOT_DIR/skills/ralph-loop-codex/examples/prd.json" "$TMP_DIR/prd.json"
cat > "$TMP_DIR/AGENTS.md" <<'EOF2'
# Agents
Use repository conventions.
EOF2

python3 "$ROOT_DIR/scripts/ralph_loop.py" \
  --repo "$TMP_DIR" \
  --loop \
  --max-retries 3 \
  --constraint "--dangerously-skip-permissions"

python3 - "$TMP_DIR/prd.json" <<'PY'
import json
import sys
from pathlib import Path

prd_path = Path(sys.argv[1])
payload = json.loads(prd_path.read_text(encoding="utf-8"))
statuses = [story["status"] for story in payload["stories"]]
if statuses != ["done", "done"]:
    raise SystemExit(f"unexpected statuses: {statuses}")
print("Harness check: all stories marked done")
PY

echo "Harness completed successfully in $TMP_DIR"
