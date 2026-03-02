# Ralph Loop Kit for Codex

This kit provides an external loop runner around `codex exec` with a strict output schema.

## Concept
- `plan`: update `ralph/state/IMPLEMENTATION_PLAN.md` from repo context
- `build`: execute only one highest-priority task from the plan
- `review`: inspect current changes and add follow-up tasks when risks are found

The loop contract is schema-driven via `ralph/schema/loop_output.schema.json`.

## Quick Start
```bash
./ralph/loop.sh build --max-iters 20
```

## Mode Examples
```bash
./ralph/loop.sh --mode plan --max-iters 3
./ralph/loop.sh --mode build --max-iters 20 --timeout 30m
./ralph/loop.sh --mode review --max-iters 5
```

## Notes on Git/Sandbox
- Some sandboxed environments make `.git/` partially read-only.
- If commit/push is blocked, keep loop iterations for code changes + verification, then commit manually in a writable environment.
- `ralph/loop.sh` performs a git-repo check by default. Use `--skip-git-repo-check` only when intentionally running outside git.

## Logs
- Structured output JSON: `ralph/logs/out.<mode>.<iter>.json`
- Event stream JSONL: `ralph/logs/events.<mode>.<iter>.jsonl`
