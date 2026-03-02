#!/usr/bin/env bash
set -euo pipefail

MODE=""
MAX_ITERS=20
TIMEOUT="30m"
CONTINUE_ON_HUMAN=0
SKIP_GIT_REPO_CHECK=0

usage() {
  cat <<USAGE
Usage:
  ./ralph/loop.sh [mode] [options]

Modes:
  plan | build | review

Options:
  --mode <plan|build|review>
  --max-iters <N>
  --timeout <30m>
  --continue-on-human
  --skip-git-repo-check
  -h, --help
USAGE
}

if [ "${1:-}" = "plan" ] || [ "${1:-}" = "build" ] || [ "${1:-}" = "review" ]; then
  MODE="$1"
  shift
fi

while [ "$#" -gt 0 ]; do
  case "$1" in
    --mode) MODE="$2"; shift 2 ;;
    --max-iters) MAX_ITERS="$2"; shift 2 ;;
    --timeout) TIMEOUT="$2"; shift 2 ;;
    --continue-on-human) CONTINUE_ON_HUMAN=1; shift ;;
    --skip-git-repo-check) SKIP_GIT_REPO_CHECK=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 1 ;;
  esac
done

if [ -z "$MODE" ]; then
  MODE="build"
fi

case "$MODE" in
  plan|build|review) ;;
  *) echo "Invalid mode: $MODE" >&2; exit 1 ;;
esac

if [ "$SKIP_GIT_REPO_CHECK" -ne 1 ]; then
  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "[loop] Not inside a git repository. Use --skip-git-repo-check to bypass." >&2
    exit 1
  fi
fi

mkdir -p ralph/logs
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCHEMA="$SCRIPT_DIR/schema/loop_output.schema.json"
PROMPT="$SCRIPT_DIR/prompts/$(printf '%s' "$MODE" | tr '[:lower:]' '[:upper:]').md"

if [ ! -f "$SCHEMA" ] || [ ! -f "$PROMPT" ]; then
  echo "[loop] Missing schema or prompt file." >&2
  exit 1
fi

parse_json_field() {
  local file="$1"
  local expr="$2"
  if command -v jq >/dev/null 2>&1; then
    jq -r "$expr" "$file"
  elif command -v python3 >/dev/null 2>&1; then
    python3 - "$file" "$expr" <<'PY'
import json, sys
path, expr = sys.argv[1], sys.argv[2]
with open(path, encoding='utf-8') as f:
    data = json.load(f)
if expr == '.status':
    print(data.get('status', ''))
elif expr == '.notes[]':
    for n in data.get('notes', []):
        print(n)
else:
    print('')
PY
  else
    echo ""
  fi
}

ITER=1
while [ "$ITER" -le "$MAX_ITERS" ]; do
  OUT_JSON="ralph/logs/out.${MODE}.${ITER}.json"
  EVENTS_JSONL="ralph/logs/events.${MODE}.${ITER}.jsonl"

  echo "[loop] mode=$MODE iter=$ITER"
  cat "$PROMPT" | codex exec \
    --output-schema "$SCHEMA" \
    --timeout "$TIMEOUT" \
    -o "$OUT_JSON" \
    --json - 2>&1 | tee "$EVENTS_JSONL"

  if [ ! -f "$OUT_JSON" ]; then
    echo "[loop] Missing output file: $OUT_JSON" >&2
    exit 1
  fi

  STATUS="$(parse_json_field "$OUT_JSON" '.status')"

  if [ "$STATUS" = "LOOP_COMPLETE" ]; then
    echo "[loop] LOOP_COMPLETE"
    exit 0
  fi

  if [ "$STATUS" = "NEEDS_HUMAN" ]; then
    echo "[loop] NEEDS_HUMAN"
    parse_json_field "$OUT_JSON" '.notes[]' | sed 's/^/- /'
    if [ "$CONTINUE_ON_HUMAN" -eq 1 ]; then
      ITER=$((ITER + 1))
      continue
    fi
    exit 0
  fi

  if [ "$STATUS" != "CONTINUE" ]; then
    echo "[loop] Unknown status: $STATUS" >&2
    exit 1
  fi

  ITER=$((ITER + 1))
done

echo "[loop] Reached max iterations: $MAX_ITERS"
exit 0
