# Codex Setup Templates

These files are the template source for Codex configuration used by Dokkebi Loop.

In normal use, prefer the repository setup script:

```bash
./setup-dokkebi-loop.sh codex
```

Use manual copy only when you need to install or inspect the templates by hand.

## Files

- `config.toml.example`
  - Codex profile examples for build/review roles.
- `default.rules.example`
  - Execpolicy baseline aligned with Dokkebi Loop permission checks.

## Install manually

Global install:

```bash
mkdir -p ~/.codex
cp skills/dokkebi-loop-codex/ralph/codex_setup/config.toml.example ~/.codex/config.toml
cp skills/dokkebi-loop-codex/ralph/codex_setup/default.rules.example ~/.codex/default.rules
```

Project-local install:

```bash
mkdir -p .codex
cp skills/dokkebi-loop-codex/ralph/codex_setup/config.toml.example .codex/config.toml
cp skills/dokkebi-loop-codex/ralph/codex_setup/default.rules.example .codex/default.rules
```

## Validate rules

```bash
codex execpolicy check --rules ~/.codex/default.rules --command "rg --files"
codex execpolicy check --rules ~/.codex/default.rules --command "rm -rf build"
```
