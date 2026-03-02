#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-.}"
cd "$ROOT"
mkdir -p ralph/logs
CMD_LOG="ralph/logs/gate.commands.txt"
: > "$CMD_LOG"

RESULT="skipped"
RAN_ANY=0

have_cmd() { command -v "$1" >/dev/null 2>&1; }

run_cmd() {
  local cmd="$1"
  echo "$cmd" | tee -a "$CMD_LOG"
  RAN_ANY=1
  if ! bash -lc "$cmd"; then
    RESULT="fail"
    echo "[gate] FAIL: $cmd" >&2
    exit 1
  fi
  RESULT="pass"
}

package_has_script() {
  local script="$1"
  [ -f package.json ] && grep -Eq "\"${script}\"[[:space:]]*:" package.json
}

if [ -f package.json ]; then
  PM="npm"
  if [ -f pnpm-lock.yaml ]; then
    PM="pnpm"
  elif [ -f yarn.lock ]; then
    PM="yarn"
  fi

  if package_has_script test; then
    case "$PM" in
      npm) run_cmd "npm run -s test" ;;
      pnpm) run_cmd "pnpm run -s test" ;;
      yarn) run_cmd "yarn -s test" ;;
    esac
  fi
  if package_has_script lint; then
    case "$PM" in
      npm) run_cmd "npm run -s lint" ;;
      pnpm) run_cmd "pnpm run -s lint" ;;
      yarn) run_cmd "yarn -s lint" ;;
    esac
  fi
  if package_has_script typecheck; then
    case "$PM" in
      npm) run_cmd "npm run -s typecheck" ;;
      pnpm) run_cmd "pnpm run -s typecheck" ;;
      yarn) run_cmd "yarn -s typecheck" ;;
    esac
  fi
fi

if [ -d tests ] || [ -f pytest.ini ] || [ -f setup.cfg ] || [ -f tox.ini ] || grep -qi pytest pyproject.toml 2>/dev/null; then
  if [ -x .venv/bin/python ]; then
    run_cmd ".venv/bin/python -m pytest -q"
  elif have_cmd python3; then
    run_cmd "python3 -m pytest -q"
  elif have_cmd python; then
    run_cmd "python -m pytest -q"
  fi
fi

if [ -f Cargo.toml ] && have_cmd cargo; then
  run_cmd "cargo test"
fi

if [ -f go.mod ] && have_cmd go; then
  run_cmd "go test ./..."
fi

if [ "$RAN_ANY" -eq 0 ]; then
  echo "[gate] skipped: no runnable test/lint/typecheck command detected"
  exit 0
fi

echo "[gate] pass"
