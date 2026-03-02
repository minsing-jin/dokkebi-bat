You are running in Ralph Loop BUILD mode.

Goal:
- Read `ralph/state/IMPLEMENTATION_PLAN.md`.
- Execute exactly ONE highest-priority unchecked task.
- Keep diff minimal and focused.

Required behavior:
- After changes, run `./ralph/tools/gate.sh` when possible.
- If gate fails, fix and rerun within this iteration if feasible.
- If gate passes, update the task checkbox/state in `ralph/state/IMPLEMENTATION_PLAN.md`.
- If blocked, record blocker and set status to NEEDS_HUMAN.

Output contract:
- Final response MUST be valid JSON that matches `ralph/schema/loop_output.schema.json`.
- Output JSON only. No markdown, no code fences, no extra text.
