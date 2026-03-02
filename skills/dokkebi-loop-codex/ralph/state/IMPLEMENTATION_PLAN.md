# IMPLEMENTATION_PLAN

## Working Rules
- In one loop iteration, complete only one task.
- Keep each diff minimal and reversible.
- Run `./ralph/tools/gate.sh` before marking build task done.

## Stack Detection (initial)
- Node package manifest: not detected at bootstrap time
- Python project files: not detected at bootstrap time
- Rust (`Cargo.toml`): not detected at bootstrap time
- Go (`go.mod`): not detected at bootstrap time
- Existing tests directory: detected (`tests/`)

## Acceptance Criteria (global)
- [ ] Feature changes satisfy task acceptance criteria.
- [ ] Gate result is pass or explicitly skipped.
- [ ] Risks and follow-up items are tracked.

## Priority Task Queue
- [ ] P0: Confirm project-specific commands and update this plan.
  - Acceptance: plan has concrete build/test/lint/typecheck commands.

## Review Follow-up Tasks
- [ ] (none yet)
