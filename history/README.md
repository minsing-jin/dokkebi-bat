# History Layout

This folder keeps non-canonical history artifacts out of the project root so the active workspace stays focused on the current loop runtime.

## Directories

- `history/development/`
  - Past implementation plans, migration notes, and design writeups.
- `history/logs/`
  - Seed logs, snapshots, and archived runtime artifacts that should not live at the root.

## What belongs here

- one-off migration notes
- archived seed PRDs or progress files
- development history worth keeping for reference

## What should not live here

- active `prd.json`
- active story artifacts under `stories/<id>/`
- current `.ralph/logs/` for an in-progress run

If a file is part of the live artifact contract, keep it in the project root or under `stories/`. If it is historical context, move it under `history/`.
