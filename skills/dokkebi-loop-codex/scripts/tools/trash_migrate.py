#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Move files/directories to Trash with manifest")
    p.add_argument("paths", nargs="+", help="Paths to move")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--repo", default=".")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).resolve()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target_root = Path.home() / ".Trash" / "ralph-loop" / stamp
    manifest: list[dict[str, str]] = []

    for item in args.paths:
        src = (repo / item).resolve()
        if not src.exists():
            continue
        dst = target_root / src.name
        manifest.append({"src": str(src), "dst": str(dst)})
        if not args.dry_run:
            target_root.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                if dst.is_dir():
                    shutil.rmtree(dst)
                else:
                    dst.unlink()
            shutil.move(str(src), str(dst))

    if not args.dry_run:
        (target_root / "moved.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"dry_run": args.dry_run, "moves": manifest}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
