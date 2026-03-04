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
- [x] P0: Codex setup script links local skills for auto-sync.
  - Acceptance: `setup-dokkebi-loop.sh codex` installs config and symlinks skills into `~/.codex/skills`.
- [x] P1: Strict PRD validation enforced before any loop execution.
  - Acceptance: missing required story fields fail run and write `PRD_VALIDATION_ERRORS.md`.
- [x] P2: Root Ralph artifacts reduced to wrappers; implementation stays under skills.
  - Acceptance: root `ralph/` keeps wrapper entrypoints only, duplicate prompts/schema/scripts removed.
- [x] P3: PRD generators emit strict-compatible non-empty defaults.
  - Acceptance: `prd-md-to-json` and `specify-gidometa` output non-empty required lists and phase implementer/verifier commands.
- [x] P4: PRD generation switched to context-driven inference (no placeholder defaults).
  - Acceptance: generated stories fill required fields from `prd.md`/context heuristics and avoid `:` placeholder commands.
- [x] P5: QA dr.strange hardened with auto-checks, failure mapping, and retry loop handoff.
  - Acceptance: failing QA checks can map to story IDs, auto-write errors/context/lessons, and requeue stories to `todo`.
- [x] P6: QA failure no longer hard-stops loop when requeue candidates exist.
  - Acceptance: with `--loop`, qa failure can requeue mapped stories and continue iterations until QA passes or max-iterations reached.
- [x] P7: Enforce runnable phase contract and expose full execution trace in loop output.
  - Acceptance: phase-config requires implementer/testsmith/verifier/qa commands; runtime output prints phase commands/results beyond implementer.
- [x] P8: Root declutter and history segregation.
  - Acceptance: root runtime/history artifacts moved under `history/development` and `history/logs`.
- [x] P9: Loop no longer hard-stops on first failed story in `--loop` mode.
  - Acceptance: failed story is deferred and loop continues with remaining todo stories until completion or max-iterations.
- [x] P10: Prevent repeated blocking prompts by isolating chronic failures.
  - Acceptance: in loop mode, failed story remains current retry target until resolved; subsequent stories run only after recovery.
- [ ] P11: Confirm project-specific commands and update this plan.
  - Acceptance: plan has concrete build/test/lint/typecheck commands.

## Review Follow-up Tasks
- [ ] (none yet)

- [x] Migration: consolidated Ralph Loop into skills/dokkebi-loop-codex with root setup/run wrappers.
- Gate baseline captured
- [x] Ralph Loop v2 artifacts/evidence/context/lessons/progress pipeline implemented with legacy compatibility.
- [x] Role-based independent agent contracts and phase execution (specify/planner/context-scribe/show-me-the-hook/issue-tiger) wired as default template + runtime phases.
