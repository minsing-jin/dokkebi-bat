#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <superpower-skill-name>" >&2
  exit 1
fi

NAME="$1"
SOURCE_ROOT="${HOME}/.codex/superpowers/skills_disabled"
TARGET_ROOT="${HOME}/.codex/skills"
SOURCE_DIR="${SOURCE_ROOT}/${NAME}"
TARGET_DIR="${TARGET_ROOT}/${NAME}"

if [ ! -d "$SOURCE_DIR" ]; then
  echo "[superpower] source skill not found: $SOURCE_DIR" >&2
  exit 1
fi

mkdir -p "$TARGET_ROOT"
rm -rf "$TARGET_DIR"
ln -s "$SOURCE_DIR" "$TARGET_DIR"

echo "[superpower] activated ${NAME} -> ${TARGET_DIR}"
