---
name: dokkebi-loop-codex
description: Use when you want an autonomous builder/verifier loop from prd.json with one-task-per-iteration execution and gate verification.
---

# Dokkebi Loop Codex

Use `skills/dokkebi-loop-codex/scripts/ralph_loop.py` to process one `todo` story at a time from `prd.json`.

## Required Files
- `AGENTS.md`: auto-created with role contracts (`specify/planner/context-scribe/implementer/testsmith/verifier/reviewer/show-me-the-hook/qa/issue-tiger`) if missing (use `--strict-agents-md` to enforce manual creation)
- `prd.json`: `{ "stories": [...] }`
- Optional `ralph_state.json`: runner state and failures
- Optional `progress.md`: append-only run log

PRD validation is strict and always-on:
- Missing required story fields fail immediately before execution.
- Failure report is written to `PRD_VALIDATION_ERRORS.md`.

Each story should include:
- `id`, `title`, `status` (`todo|doing|done`)
- `priority` (integer)
- `acceptance_criteria` (non-empty list)
- `non_goals`, `constraints`, `dependencies`, `risks`, `success_metrics` (lists)
- `builder_commands`: shell commands for implementation
- `verifier_commands`: shell commands for validation
- `review_commands` (optional): post-verify quality checks; failure returns story to `todo`
- `tdd_red_command` (optional): must fail before build phase
- `tdd_green_command` (optional): must pass after verify phase
- `phase_config` (optional, phase-config): `specify_commands`, `planner_commands`, `context_scribe_commands`, `show_me_hook_commands`, `implementer_commands`, `testsmith_commands`, `verifier_commands`, `review_commands`, `issue_tiger_commands`, `qa_commands`

## Run Once
```bash
python3 skills/dokkebi-loop-codex/scripts/ralph_loop.py --repo .
```

## Bootstrap PRD Then Run
```bash
python3 skills/dokkebi-loop-codex/scripts/ralph_loop.py \
  --repo . \
  --bootstrap-prd \
  --bootstrap-input-json idea.json \
  --loop
```

## Run Continuously
```bash
python3 skills/dokkebi-loop-codex/scripts/ralph_loop.py --repo . --loop
```

## Phase-Config Mode
```bash
python3 skills/dokkebi-loop-codex/scripts/ralph_loop.py --repo . --mode phase-config --loop
```

## Story Selection
```bash
python3 skills/dokkebi-loop-codex/scripts/ralph_loop.py --repo . --story-id PC-001
```

## Mode Names
- `basic`: `builder_commands` + `verifier_commands`
- `phase-config`: `phase_config.*` role-based commands
- compatibility aliases are accepted: `legacy -> basic`, `v2 -> phase-config`

## Ralph Plan/Build/Review Loop
```bash
bash skills/dokkebi-loop-codex/ralph/loop.sh build --max-iters 20
```

## Retries + ERROR.md Protocol
- Use `--max-retries` to retry the same story before failing.
- Before each verifier attempt, stale `ERROR.md` is removed.
- If verifier fails and no `ERROR.md` exists, runner writes one automatically.
- `ERROR.md` presence after verifier phase is treated as FAIL.

## Quality Phases
When configured, a story executes in this order:
1. `specify_commands`
2. `planner_commands`
3. `context_scribe_commands`
4. `show_me_hook_commands`
5. `tdd_red_command` (expected fail)
6. `builder_commands` (implementer)
7. `testsmith_commands`
8. `verifier_commands`
9. `tdd_green_command` (expected pass)
10. `review_commands`
11. `issue_tiger_commands`
12. `gate` (`./ralph/tools/gate.sh` by default, unless `--skip-gate`)
13. `qa_commands`

Built-in role agents also run by default (even without custom commands):
- `specify-gidometa`: ensures `stories/<id>/story.md`
- `planner`: ensures `stories/<id>/plan.md` (+ story-level ADR draft when stack options are provided)
- `context-scribe`: updates `stories/<id>/context_pack.md`
- `issue-tiger`: emits issue execution artifacts when `issues/<id>.json` exists
- `qa dr.strange`: writes `E2E_EVIDENCE.md` when all stories are processed

## Apply Constraints (e.g. Codex flags)
Add placeholder `{{constraints}}` in your commands, then pass repeatable constraints.

- Default constraints are already enabled: `--dangerously-skip-permissions`, `--allow-git-push`
- Add more constraints with additional `--constraint` flags.

```bash
python3 skills/dokkebi-loop-codex/scripts/ralph_loop.py --repo . --loop \
  --constraint --dangerously-skip-permissions
```

## Run-State Hygiene
- Startup archives stale `.ralph/logs` into `.ralph/runs/<run_id>/logs`.
- New run starts with fresh `.ralph/logs` and cleared `ERROR.md`.

## Compatibility Flag
If you need to run without `AGENTS.md`:
```bash
python3 skills/dokkebi-loop-codex/scripts/ralph_loop.py --repo . --allow-missing-agents-md
```

## Harness
Quick end-to-end smoke run:
```bash
bash skills/dokkebi-loop-codex/harness/run_harness.sh
```

## Setup
Project root convenience scripts:
```bash
./setup-dokkebi-loop.sh
./run-dokkebi-loop.sh build --max-iters 20
```

## Debug Logs
Each attempt writes detailed logs for replay/debugging:
- `.ralph/logs/<story>-build-<attempt>.log`
- `.ralph/logs/<story>-verify-<attempt>.log`
- `.ralph/logs/<story>-review-<attempt>.log`
- `.ralph/logs/<story>-tdd-<attempt>.log`
- `.ralph/logs/<story>-gate-<attempt>.log`
- `.ralph/logs/<story>-attempt-<attempt>.json` (commands, outputs, outcome, git snapshot)
- `.ralph/logs/<story>-attempt-<attempt>-debug.md` (failure root-cause checklist + context)

## Artifact Contract
For each story run, the loop guarantees:
- `stories/<id>/story.md`
- `stories/<id>/plan.md`
- `stories/<id>/context_pack.md`
- `stories/<id>/errors.md` (on FAIL)
- `stories/<id>/evidence.md` (on PASS)
- `PROGRESS.jsonl` append-only events
- `LESSONS.md` accumulated failure playbook
- `E2E_EVIDENCE.md` written by QA stage
