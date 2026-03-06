# Ralph Compatibility Wrappers

This directory is not the canonical Dokkebi Loop implementation.

Canonical runtime and skills live under:
- `skills/dokkebi-loop-codex/`

This directory exists only to preserve older entrypoints and shell-based workflows that still expect a top-level `ralph/` path.

## What stays here

- `ralph/loop.sh`
  - Compatibility shell loop for `plan`, `build`, and `review`.
- `ralph/tools/gate.sh`
  - Compatibility gate entrypoint.
- `ralph/state/IMPLEMENTATION_PLAN.md`
  - Compatibility state file for the shell loop.
- `ralph/logs/`
  - Runtime logs produced by compatibility wrappers and gate execution.

## When to use this directory

Use `ralph/` only when you intentionally want the shell wrapper surface:

```bash
./run-dokkebi-loop.sh build --max-iters 20
```

If you want the canonical artifact-first loop, run:

```bash
python3 skills/dokkebi-loop-codex/scripts/ralph_loop.py --repo . --loop --mode phase-config
```

That path is the source of truth for:
- strict PRD validation
- role-based phase execution
- context packs, evidence, lessons, and QA artifacts
- integrated permission policy checks
