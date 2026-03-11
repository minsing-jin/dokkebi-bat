#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$ROOT_DIR/skills/dokkebi-loop-codex"

install_codex() {
  local target="${HOME}/.codex"
  mkdir -p "$target"
  cp "$SKILL_DIR/ralph/codex_setup/config.toml.example" "$target/config.toml"
  cp "$SKILL_DIR/ralph/codex_setup/default.rules.example" "$target/default.rules"
  echo "[setup] Codex config installed to $target"
  install_codex_skills
}

link_skill_dir() {
  local source_dir="$1"
  local target_dir="$2"
  rm -rf "$target_dir"
  ln -s "$source_dir" "$target_dir"
}

install_codex_skills() {
  local skills_root="${HOME}/.codex/skills"
  local legacy_target="${skills_root}/ralph-loop-codex"
  local dokkebi_target="${skills_root}/dokkebi-loop-codex"
  local specify_target="${skills_root}/specify-gidometa-codex"
  local prdmd_target="${skills_root}/prd-md-to-json-codex"
  local clodex_target="${skills_root}/clodex"
  local superpower_target="${skills_root}/superpower"

  mkdir -p "$skills_root"
  rm -rf "$legacy_target"
  link_skill_dir "$SKILL_DIR" "$dokkebi_target"
  link_skill_dir "$ROOT_DIR/skills/specify-gidometa-codex" "$specify_target"
  link_skill_dir "$ROOT_DIR/skills/prd-md-to-json-codex" "$prdmd_target"
  link_skill_dir "$ROOT_DIR/skills/clodex" "$clodex_target"
  link_skill_dir "$ROOT_DIR/skills/superpower" "$superpower_target"
  echo "[setup] Codex skills linked to $skills_root (canonical: dokkebi-loop-codex)"
}

install_claude() {
  local skills_root="${HOME}/.claude/skills"
  local hooks_root="${HOME}/.claude/hooks"
  local legacy_target="${skills_root}/ralph-loop-codex"
  local dokkebi_target="${skills_root}/dokkebi-loop-codex"
  local specify_target="${skills_root}/specify-gidometa-codex"
  local prdmd_target="${skills_root}/prd-md-to-json-codex"
  local clodex_target="${skills_root}/clodex"
  local superpower_target="${skills_root}/superpower"
  mkdir -p "$skills_root"
  mkdir -p "$hooks_root"
  rm -rf "$legacy_target" "$dokkebi_target" "$specify_target" "$prdmd_target" "$clodex_target" "$superpower_target"
  cp -R "$SKILL_DIR" "$dokkebi_target"
  cp -R "$ROOT_DIR/skills/specify-gidometa-codex" "$specify_target"
  cp -R "$ROOT_DIR/skills/prd-md-to-json-codex" "$prdmd_target"
  cp -R "$ROOT_DIR/skills/clodex" "$clodex_target"
  cp -R "$ROOT_DIR/skills/superpower" "$superpower_target"
  cp "$SKILL_DIR/hooks/permission-gates.py" "$hooks_root/permission-gates.py"
  cp "$SKILL_DIR/hooks/permission-reviewer.py" "$hooks_root/permission-reviewer.py"
  cp "$SKILL_DIR/hooks/workflow-post.sh" "$hooks_root/workflow-post.sh"
  chmod +x "$hooks_root/permission-gates.py" "$hooks_root/permission-reviewer.py" "$hooks_root/workflow-post.sh"
  echo "[setup] Claude skills installed to $skills_root (canonical: dokkebi-loop-codex)"
  echo "[setup] Claude hooks installed to $hooks_root"
}

install_project_codex() {
  local target="$ROOT_DIR/.codex"
  mkdir -p "$target"
  cp "$SKILL_DIR/ralph/codex_setup/config.toml.example" "$target/config.toml"
  cp "$SKILL_DIR/ralph/codex_setup/default.rules.example" "$target/default.rules"
  echo "[setup] Project Codex config installed to $target"
}

MODE="${1:-all}"
case "$MODE" in
  migrate)
    python3 "$SKILL_DIR/scripts/tools/trash_migrate.py" --repo "$ROOT_DIR" "skills/ralph-loop-codex"
    ;;
  codex)
    install_codex
    ;;
  claude)
    install_claude
    ;;
  project)
    install_project_codex
    ;;
  all)
    install_project_codex
    install_codex
    install_claude
    ;;
  *)
    echo "Usage: $0 [all|codex|claude|project|migrate]" >&2
    exit 1
    ;;
esac

echo "[setup] done"
