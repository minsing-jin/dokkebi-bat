#!/usr/bin/env bash
set -euo pipefail

SKILLS_ROOT="${HOME}/.codex/skills"
BACKUP_ROOT="${HOME}/.codex/skills_disabled_dokkebi"

mkdir -p "$SKILLS_ROOT"
mkdir -p "$BACKUP_ROOT"

for path in "$SKILLS_ROOT"/*; do
  [ -e "$path" ] || continue
  name="$(basename "$path")"
  if [ "$name" = ".system" ] || [ "$name" = "superpower" ]; then
    continue
  fi
  rm -rf "$BACKUP_ROOT/$name"
  mv "$path" "$BACKUP_ROOT/$name"
  echo "[superpower-only] moved $name -> $BACKUP_ROOT/$name"
done

echo "[superpower-only] active skills:"
find "$SKILLS_ROOT" -maxdepth 1 -mindepth 1 | sort
