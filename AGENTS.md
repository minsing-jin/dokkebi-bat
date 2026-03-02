# AGENTS

## Ralph Loop Principles
- Artifact-first: files are the system memory.
- Evidence-gated: PASS requires executable evidence.
- Context-pack memory: refresh `stories/<id>/context_pack.md` each loop.
- Self-improvement: append reusable rules to `LESSONS.md`.

## Role Contracts
### specify-gidometa
- Input: user idea + repo context
- Output: `prd.json`, `stories/<id>/story.md`

### planner
- Input: `prd.json`, `stories/<id>/story.md`
- Output: `stories/<id>/plan.md`

### context-scribe
- Input: logs + diffs + story artifacts
- Output: `stories/<id>/context_pack.md`, optional `LESSONS.md` append

### implementer
- Input: `story.md`, `plan.md`, `context_pack.md`, `errors.md`
- Output: code changes and rerunnable workspace state

### testsmith
- Input: story context + current code + previous failures
- Output: fail-first/regression tests

### verifier
- Input: code + plan + context pack + test logs
- Output PASS: `stories/<id>/evidence.md`
- Output FAIL: `stories/<id>/errors.md`

### reviewer
- Input: diff + test evidence
- Output: concrete risk/quality feedback commands

### show-me-the-hook
- Input: new user directives + current PRD
- Output: updates to `prd.json`, `story.md`, `plan.md`

### qa dr.strange
- Input: full PRD + runnable system
- Output: end-to-end release evidence

### issue tiger
- Input: issue metadata
- Output: issue->branch/PR automation artifacts

## Loop Sequence
specify-gidometa -> planner -> context-scribe -> implementer -> testsmith -> verifier
FAIL -> context-scribe update -> implementer retry
ALL PASS -> qa dr.strange
