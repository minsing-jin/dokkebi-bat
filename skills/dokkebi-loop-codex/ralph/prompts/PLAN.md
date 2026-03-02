You are running in Ralph Loop PLAN mode.

Goal:
- Do not modify product code.
- Read repository structure/spec/docs/tests.
- Update only `ralph/state/IMPLEMENTATION_PLAN.md` with an actionable plan.

Rules:
- Keep plan concise and prioritized.
- One iteration must target one actionable task.
- Include acceptance criteria and verification command ideas.
- If required context is missing, ask for human input via notes.

Output contract:
- Final response MUST be valid JSON that matches `ralph/schema/loop_output.schema.json`.
- Output JSON only. No markdown, no code fences, no extra text.
