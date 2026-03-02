# Codex Setup Templates (Manual Copy)

This directory provides templates only. It does not auto-create `.codex/` because some environments protect that path in sandbox mode.

## Where to copy
- Global config: `~/.codex/`
- Project config: `<repo>/.codex/` (create manually if needed)

## Files
- `config.toml.example`: profile examples for Ralph build/review loops
- `default.rules.example`: execpolicy rule examples

## Example application
```bash
mkdir -p ~/.codex
cp ralph/codex_setup/config.toml.example ~/.codex/config.toml
cp ralph/codex_setup/default.rules.example ~/.codex/default.rules
```

## Execpolicy check example
```bash
codex execpolicy check --rules ~/.codex/default.rules --command "rg --files"
codex execpolicy check --rules ~/.codex/default.rules --command "rm -rf build"
```
