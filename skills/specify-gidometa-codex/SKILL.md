---
name: specify-gidometa-codex
description: Use when you need to bootstrap or refine prd.json and stories/<id>/story.md from a vague idea into executable story artifacts.
---

# Specify Gidometa Codex

Purpose:
- Convert a rough idea into concrete PRD stories and story docs.
- Generate/merge `prd.json` and `stories/<id>/story.md`.

## Inputs
- Optional structured JSON file (`--input-json`)
- Or interactive answers in terminal

## Outputs
- `prd.json` (story list merged by story id)
- `stories/<id>/story.md`

## Run (interactive)
```bash
python3 skills/specify-gidometa-codex/scripts/specify_gidometa.py --repo .
```

## Run (advanced tech-stack mode)
```bash
python3 skills/specify-gidometa-codex/scripts/specify_gidometa.py \
  --repo . \
  --advanced \
  --emit-arch \
  --emit-conventions \
  --emit-adr
```

## Run (from JSON)
```bash
python3 skills/specify-gidometa-codex/scripts/specify_gidometa.py \
  --repo . \
  --input-json idea.json
```

## Input JSON shape
```json
{
  "project": {"title": "My Product", "goal": "..."},
  "stories": [
    {
      "id": "S-001",
      "title": "...",
      "priority": 1,
      "acceptance_criteria": ["..."],
      "non_goals": [],
      "constraints": [],
      "dependencies": [],
      "risks": [],
      "success_metrics": []
    }
  ]
}
```

## Notes
- New stories are written in `phase-config` mode template.
- Existing story IDs in `prd.json` are replaced by incoming story definitions.
- `--socratic` adds structured requirement prompts (non-goal/constraint/risk/success metric) per story.
