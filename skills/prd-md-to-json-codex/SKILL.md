---
name: prd-md-to-json-codex
description: Convert natural-language prd.md into runnable prd.json stories for Ralph Loop.
---

# PRD MD To JSON Codex

Purpose:
- Transform human-written `prd.md` into `prd.json`.

## Run
```bash
python3 skills/prd-md-to-json-codex/scripts/prd_md_to_json.py --repo . --input prd.md --output prd.json
```

## Mode
- `--mode phase-config` (default)
- `--mode basic`

## Merge
```bash
python3 skills/prd-md-to-json-codex/scripts/prd_md_to_json.py --repo . --input prd.md --output prd.json --merge
```
