# Dokkebi Bat

`dokkebi-bat` is a local skill bundle and runtime kit centered on Dokkebi Loop, a file-driven Ralph Loop workflow for Codex and Claude.

The repository is designed around one core idea:
- artifacts are the system memory
- execution must be evidence-gated
- interrupted work must resume from files, not chat

## What is in this repository

- `skills/dokkebi-loop-codex/`
  - Canonical Dokkebi Loop skill and runner.
- `skills/specify-gidometa-codex/`
  - Bootstraps or refines `prd.json` and story files from a rough idea.
- `skills/prd-md-to-json-codex/`
  - Converts `prd.md` into runnable `prd.json`.
- `skills/clodex/`
  - Claude-style planning and compressed handoff packet for Codex implementation.
- `setup-dokkebi-loop.sh`
  - Links or installs Dokkebi skills/config into Codex and Claude environments.
- `run-dokkebi-loop.sh`
  - Convenience wrapper for the compatibility loop shell entrypoint.
- `ralph/`
  - Thin compatibility wrappers only. Canonical implementation lives under `skills/dokkebi-loop-codex/`.
- `history/`
  - Development notes and archived runtime artifacts moved out of the project root.

## Core concepts

### Canonical artifacts

- `prd.json`
  - Story backlog with acceptance criteria, constraints, dependencies, risks, and execution commands.
- `stories/<id>/story.md`
  - Story definition.
- `stories/<id>/plan.md`
  - Implementation plan.
- `stories/<id>/context_pack.md`
  - Resume-safe compressed state.
- `stories/<id>/errors.md`
  - Failure reproduction and remediation instructions.
- `stories/<id>/evidence.md`
  - PASS evidence.
- `LESSONS.md`
  - Reusable playbook accumulated from failures.
- `PROGRESS.jsonl`
  - Append-only execution log.

### Loop principles

- Artifact-first
- Evidence-gated
- Context-pack memory
- Self-improvement

### Activation policy

Dokkebi Loop is explicit-only.

It does not run automatically for normal chat or small edits. Run it only when you explicitly invoke the skill or the loop command.

## Install

### One-time global setup for Codex

```bash
cd ~/Desktop/dokkebi-bat
./setup-dokkebi-loop.sh codex
```

This installs:
- `~/.codex/config.toml`
- `~/.codex/default.rules`
- `~/.codex/skills/dokkebi-loop-codex`
- `~/.codex/skills/specify-gidometa-codex`
- `~/.codex/skills/prd-md-to-json-codex`
- `~/.codex/skills/clodex`

### One-time global setup for Claude

```bash
cd ~/Desktop/dokkebi-bat
./setup-dokkebi-loop.sh claude
```

This installs:
- `~/.claude/skills/...`
- `~/.claude/hooks/permission-gates.py`
- `~/.claude/hooks/permission-reviewer.py`
- `~/.claude/hooks/workflow-post.sh`

### Project-local Codex config only

```bash
cd ~/Desktop/dokkebi-bat
./setup-dokkebi-loop.sh project
```

## Recommended workflow in a new project

Assume your target project is `~/Desktop/my-project`.

### 1. Enter the target project

```bash
cd ~/Desktop/my-project
```

### 2. Prepare PRD input

Option A: write `prd.md`, then convert it

```bash
python3 ~/.codex/skills/prd-md-to-json-codex/scripts/prd_md_to_json.py \
  --repo . \
  --input prd.md \
  --output prd.json \
  --mode phase-config
```

Option B: generate `prd.json` interactively

```bash
python3 ~/.codex/skills/specify-gidometa-codex/scripts/specify_gidometa.py \
  --repo . \
  --advanced
```

### 3. Run Dokkebi Loop

```bash
python3 ~/.codex/skills/dokkebi-loop-codex/scripts/ralph_loop.py \
  --repo . \
  --loop \
  --mode phase-config \
  --permission-profile balanced
```

Use `--deny-on-ask` if you want the loop to fail instead of proceeding on commands that are classified as `ask` by the permission policy.

## Clodex workflow

`clodex` is a planning-to-implementation bridge skill.

Use it when you want:
- stronger planning with multiple options
- one compressed shared context instead of repeated long chat context
- a clean handoff from planning into implementation

Clodex uses `.clodex/` as the shared packet directory:
- `.clodex/context.md`
- `.clodex/plan.md`
- `.clodex/implementation_packet.md`
- `.clodex/status.md`

Initialize the packet directory with:

```bash
mkdir -p .clodex
cp ~/.codex/skills/clodex/templates/context.md .clodex/context.md
cp ~/.codex/skills/clodex/templates/plan.md .clodex/plan.md
cp ~/.codex/skills/clodex/templates/implementation_packet.md .clodex/implementation_packet.md
cp ~/.codex/skills/clodex/templates/status.md .clodex/status.md
```

Recommended use:

1. Use `clodex` to explore, compare options, and lock the plan.
2. Write the final implementation packet under `.clodex/`.
3. Let Codex implement from `.clodex/implementation_packet.md`.
4. Keep `.clodex/context.md` as the canonical compressed context to save tokens.

Rules:
- `clodex` is explicit-only, like Dokkebi Loop.
- One side is the active steward for `.clodex/context.md`.
- The implementation side should read `.clodex/*` first before re-exploring the whole repo.

## Primary entrypoints

### File-driven loop runner

This is the main runtime:

```bash
python3 skills/dokkebi-loop-codex/scripts/ralph_loop.py --repo . --loop --mode phase-config
```

Use this when you want strict PRD validation, role-phase execution, story artifacts, policy checks, evidence, and QA behavior.

### Compatibility shell wrapper

```bash
./run-dokkebi-loop.sh build --max-iters 20
```

This calls the compatibility wrapper in `skills/dokkebi-loop-codex/ralph/loop.sh`.

Use this only when you specifically want the `plan/build/review` shell loop surface. The canonical artifact-first loop is `scripts/ralph_loop.py`.

## Permission policy

Jeffrey-inspired permission handling is integrated as an additive layer without changing Dokkebi Loop's artifact contract.

Current profiles:
- `balanced`
- `strict`
- `fast`

Default policy file:
- `skills/dokkebi-loop-codex/policy/permission_policy.json`

The loop evaluates each command before execution and writes policy traces under:
- `.ralph/logs/<story>-policy-<attempt>.json`

Examples of guarded behavior:
- deny `.env` access
- classify `psql` read vs write
- block or flag risky `git push` and destructive commands

## What the loop creates

When a story runs successfully or fails, Dokkebi Loop manages these outputs automatically:

- `stories/<id>/story.md`
- `stories/<id>/plan.md`
- `stories/<id>/context_pack.md`
- `stories/<id>/errors.md`
- `stories/<id>/evidence.md`
- `PROGRESS.jsonl`
- `LESSONS.md`
- `.ralph/logs/*`
- `E2E_EVIDENCE.md`

## Testing

Run the full test suite from this repository root:

```bash
pytest -q
```

## Troubleshooting

### Strict PRD validation failed

The loop writes:
- `PRD_VALIDATION_ERRORS.md`

Fix the listed fields in `prd.json` and rerun.

### Gate says no runnable command detected

Default gate discovery only runs when the project exposes recognizable test/lint/typecheck commands.

Check:
- `package.json` scripts
- Python test environment
- `Cargo.toml`
- `go.mod`

### Loop stops after failures

Read:
- `stories/<id>/errors.md`
- `stories/<id>/context_pack.md`
- `.ralph/logs/<story>-attempt-<n>-debug.md`

### Codex or Claude does not see the skills

Rerun setup:

```bash
./setup-dokkebi-loop.sh codex
./setup-dokkebi-loop.sh claude
```

## Repository map

```text
.
├── AGENTS.md
├── README.md
├── history/
├── ralph/
├── run-dokkebi-loop.sh
├── setup-dokkebi-loop.sh
├── skills/
│   ├── clodex/
│   ├── dokkebi-loop-codex/
│   ├── prd-md-to-json-codex/
│   └── specify-gidometa-codex/
└── tests/
```
