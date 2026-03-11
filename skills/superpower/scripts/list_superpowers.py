#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    registry_path = Path(__file__).resolve().parents[1] / "registry.json"
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    for item in payload.get("skills", []):
        name = str(item.get("name", "")).strip()
        status = str(item.get("status", "")).strip()
        reason = str(item.get("reason", "")).strip()
        if name:
            print(f"{name}\t{status}\t{reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
