---
name: ralph-loop-codex
description: Use when the user wants an autonomous builder/verifier loop from prd.json, including continuous iterations with command constraints such as --dangerously-skip-permissions.
---

# Ralph Loop Codex

Use `scripts/ralph_loop.py` to process one `todo` story at a time from `prd.json`.

## Required Files
- `prd.json`: `{ "stories": [...] }`
- Optional `ralph_state.json`: runner state and failures
- Optional `progress.md`: append-only run log

Each story should include:
- `id`, `title`, `status` (`todo|doing|done`)
- `builder_commands`: shell commands for implementation
- `verifier_commands`: shell commands for validation

## Run Once
```bash
python scripts/ralph_loop.py --repo .
```

## Run Continuously
```bash
python scripts/ralph_loop.py --repo . --loop
```

## Apply Constraints (e.g. Codex flags)
Add placeholder `{{constraints}}` in your commands, then pass repeatable constraints:

```json
{
  "id": "S-10",
  "title": "codex task",
  "status": "todo",
  "builder_commands": [
    "codex run {{constraints}} --task-file tasks/10.md"
  ],
  "verifier_commands": [
    "test -f output/10.done"
  ]
}
```

```bash
python scripts/ralph_loop.py --repo . --loop \
  --constraint --dangerously-skip-permissions
```

## Harness
Quick end-to-end smoke run:
```bash
bash skills/ralph-loop-codex/harness/run_harness.sh
```
