# Ralph Compatibility Loop

This directory contains the shell-based compatibility loop that wraps `codex exec`.

It is not the main Dokkebi Loop runtime. The canonical artifact-first runner is:

```bash
python3 skills/dokkebi-loop-codex/scripts/ralph_loop.py --repo . --loop --mode phase-config
```

Use the shell loop only when you explicitly want the older `plan/build/review` surface.

## Modes

- `plan`
  - Refresh `ralph/state/IMPLEMENTATION_PLAN.md` from repo context.
- `build`
  - Execute the next unit of work from the plan.
- `review`
  - Inspect current changes and write follow-up work when risks are found.

The shell loop contract is schema-driven via:
- `ralph/schema/loop_output.schema.json`

## Quick start

```bash
./ralph/loop.sh build --max-iters 20
```

## Examples

```bash
./ralph/loop.sh --mode plan --max-iters 3
./ralph/loop.sh --mode build --max-iters 20 --timeout 30m
./ralph/loop.sh --mode review --max-iters 5
```

## Behavior notes

- `ralph/loop.sh` checks that you are inside a git repository by default.
- Use `--skip-git-repo-check` only when you intentionally run outside git.
- The shell loop does not replace the `prd.json`-driven Dokkebi Loop. It exists for compatibility and narrower iterative flows.

## Logs

- `ralph/logs/out.<mode>.<iter>.json`
  - Structured result per iteration.
- `ralph/logs/events.<mode>.<iter>.jsonl`
  - Raw event stream emitted by `codex exec`.
