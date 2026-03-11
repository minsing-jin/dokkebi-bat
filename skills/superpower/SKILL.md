---
name: superpower
description: Use when you want to inspect, register, or selectively activate external superpower skills without enabling them all by default.
---

# Superpower

This skill is a bridge for managing external `super-*` skills from the local Codex superpowers repository.

It exists to keep superpowers visible inside `dokkebi-bat` without enabling all of them globally by default.

## Activation policy

- Default state: disabled
- Do not auto-enable all `super-*` skills
- Activate a specific superpower only when explicitly requested

## Why this exists

Some superpower skills overlap with:
- `clodex`
- `dokkebi-loop-codex`
- `specify-gidometa-codex`

Enabling every superpower globally can create workflow ambiguity and skill selection conflicts.

This bridge keeps the catalog in one place and allows selective activation.

## Registry

Available external superpowers are tracked in:
- `skills/superpower/registry.json`

## Activation

To activate one superpower into global Codex skills:

```bash
bash skills/superpower/scripts/activate_superpower.sh super-writing-plans
```

To inspect the catalog:

```bash
python3 skills/superpower/scripts/list_superpowers.py
```

## Notes

- Source repository: `~/.codex/superpowers`
- Disabled source directory: `~/.codex/superpowers/skills_disabled`
- Target activation directory: `~/.codex/skills`

This bridge does not modify Dokkebi Loop behavior.
