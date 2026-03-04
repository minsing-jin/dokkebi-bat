#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Convert PRD markdown to prd.json")
    p.add_argument("--repo", default=".")
    p.add_argument("--input", default="prd.md")
    p.add_argument("--output", default="prd.json")
    p.add_argument("--mode", choices=["basic", "phase-config"], default="phase-config")
    p.add_argument("--merge", action="store_true", help="merge into existing prd.json by story id")
    return p.parse_args()


def _extract_story_blocks(text: str) -> list[tuple[str, str]]:
    # Only treat explicitly tagged story headings as individual stories.
    # This prevents random section headers from becoming fake stories.
    pattern = re.compile(r"^##\s*(?:Story|스토리)[:\-\s]+(?P<title>.+?)\s*$", re.MULTILINE)
    matches = list(pattern.finditer(text))
    if not matches:
        return [("Default Story", text.strip())]
    blocks: list[tuple[str, str]] = []
    for idx, m in enumerate(matches):
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        blocks.append((m.group("title").strip(), text[start:end].strip()))
    return blocks


def _extract_list(block: str, keys: list[str]) -> list[str]:
    lines = block.splitlines()
    active = False
    out: list[str] = []
    for line in lines:
        raw = line.strip()
        if any(raw.lower().startswith(k.lower()) for k in keys):
            active = True
            # inline value support: "AC: a, b"
            if ":" in raw:
                tail = raw.split(":", 1)[1].strip()
                if tail:
                    out.extend([x.strip() for x in tail.split(",") if x.strip()])
            continue
        if active:
            if raw.startswith("##"):
                break
            if raw.startswith("-"):
                item = raw.lstrip("-").strip()
                if item:
                    out.append(item)
            elif raw == "":
                continue
            else:
                # stop at plain paragraph after list section
                if out:
                    break
    return out


def _extract_priority(block: str, default: int) -> int:
    m = re.search(r"priority\s*:\s*(\d+)", block, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return default


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned or "story"


def _extract_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    parts = re.split(r"(?<=[.!?])\s+", normalized)
    out: list[str] = []
    for part in parts:
        s = part.strip(" -\t")
        if len(s) >= 12:
            out.append(s)
    return out


def _infer_list(block: str, title: str, ac: list[str], *, label: str) -> list[str]:
    text = " ".join([title, *ac, block])
    sentences = _extract_sentences(text)
    keyword_map = {
        "non_goals": ["exclude", "out of scope", "won't", "later", "future", "mvp", "prototype"],
        "constraints": ["must", "should", "deadline", "budget", "security", "compliance", "latency", "cost"],
        "dependencies": ["depends", "dependency", "requires", "api", "service", "database", "integration"],
        "risks": ["risk", "failure", "regression", "unclear", "edge", "race", "performance", "security"],
        "success_metrics": ["measure", "metric", "success", "pass", "latency", "coverage", "accuracy", "throughput"],
    }
    keys = keyword_map[label]
    inferred = [s for s in sentences if any(k in s.lower() for k in keys)]
    if inferred:
        return inferred[:3]
    base = ac[0] if ac else title
    if label == "non_goals":
        return [f"Limit this story to: {base}"]
    if label == "constraints":
        return [f"Implement in a way that preserves requirement intent: {base}"]
    if label == "dependencies":
        return [f"No explicit dependency listed; validate within existing project boundaries for: {title}"]
    if label == "risks":
        return [f"Primary risk is mis-implementing acceptance criteria: {base}"]
    return [f"Success is verified by executable checks for: {base}"]


def _inferred_phase_commands(story_id: str, title: str, ac: list[str]) -> dict[str, list[str]]:
    safe_id = re.sub(r"[^A-Za-z0-9._-]+", "_", story_id)
    safe_title = title.replace("'", "")
    target = _slug(ac[0] if ac else title)
    done_file = f".ralph/artifacts/{safe_id}.{target}.done"
    note_file = f".ralph/artifacts/{safe_id}.plan.txt"
    implementer = [
        f"mkdir -p .ralph/artifacts",
        f"printf '%s\\n' '{safe_title}::{target}' > {done_file}",
    ]
    verifier = [
        f"test -f {done_file}",
        f"grep -q '{target}' {done_file}",
    ]
    return {
        "specify_commands": [f"mkdir -p .ralph/artifacts && printf '%s\\n' 'specify:{safe_id}:{target}' > {note_file}"],
        "planner_commands": [f"grep -q '{safe_id}' {note_file}"],
        "context_scribe_commands": [f"test -f {note_file}"],
        "show_me_hook_commands": [f"test -f {note_file}"],
        "implementer_commands": implementer,
        "testsmith_commands": verifier,
        "verifier_commands": verifier,
        "review_commands": [f"grep -q '{safe_title}' {done_file}"],
        "issue_tiger_commands": [f"test -f {done_file}"],
        "qa_commands": [f"test -f {done_file}"],
    }


def _story_json(title: str, block: str, idx: int, mode: str) -> dict[str, Any]:
    sid_match = re.search(r"\bid\s*:\s*([A-Za-z0-9\-_]+)", block, re.IGNORECASE)
    sid = sid_match.group(1) if sid_match else f"S-{idx:03d}"
    ac = _extract_list(block, ["acceptance criteria", "ac"])
    ac = ac or [f"{title} meets documented requirements"]
    non_goals = _extract_list(block, ["non-goals", "non goals"]) or _infer_list(block, title, ac, label="non_goals")
    constraints = _extract_list(block, ["constraints"]) or _infer_list(block, title, ac, label="constraints")
    dependencies = _extract_list(block, ["dependencies", "deps"]) or _infer_list(block, title, ac, label="dependencies")
    risks = _extract_list(block, ["risks", "risk"]) or _infer_list(block, title, ac, label="risks")
    success_metrics = _extract_list(block, ["success metrics", "metrics"]) or _infer_list(block, title, ac, label="success_metrics")
    priority = _extract_priority(block, idx)

    story: dict[str, Any] = {
        "id": sid,
        "title": title,
        "status": "todo",
        "priority": priority,
        "mode": mode,
        "acceptance_criteria": ac,
        "non_goals": non_goals,
        "constraints": constraints,
        "dependencies": dependencies,
        "risks": risks,
        "success_metrics": success_metrics,
    }

    phase_commands = _inferred_phase_commands(sid, title, ac)
    explicit_implementer = _extract_list(
        block,
        ["implementer commands", "builder commands", "implementation commands", "build commands"],
    )
    explicit_verifier = _extract_list(
        block,
        ["verifier commands", "verify commands", "validation commands", "test commands"],
    )
    explicit_testsmith = _extract_list(block, ["testsmith commands", "regression test commands", "adversarial test commands"])
    explicit_review = _extract_list(block, ["review commands", "quality review commands"])
    explicit_qa = _extract_list(block, ["qa commands", "run commands", "e2e commands"])
    if explicit_implementer:
        phase_commands["implementer_commands"] = explicit_implementer
    if explicit_verifier:
        phase_commands["verifier_commands"] = explicit_verifier
    if explicit_testsmith:
        phase_commands["testsmith_commands"] = explicit_testsmith
    if explicit_review:
        phase_commands["review_commands"] = explicit_review
    if explicit_qa:
        phase_commands["qa_commands"] = explicit_qa
    if mode == "basic":
        story["builder_commands"] = list(phase_commands["implementer_commands"])
        story["verifier_commands"] = list(phase_commands["verifier_commands"])
    else:
        story["phase_config"] = phase_commands
    return story


def _merge(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {str(s.get("id", "")): s for s in existing}
    for s in incoming:
        by_id[str(s.get("id", ""))] = s
    merged = list(by_id.values())
    merged.sort(key=lambda s: (int(s.get("priority", 9999)), str(s.get("id", ""))))
    return merged


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).resolve()
    inp = Path(args.input)
    if not inp.is_absolute():
        inp = repo / inp
    out = Path(args.output)
    if not out.is_absolute():
        out = repo / out

    text = inp.read_text(encoding="utf-8")
    blocks = _extract_story_blocks(text)
    stories = [_story_json(title, block, idx + 1, args.mode) for idx, (title, block) in enumerate(blocks)]

    if args.merge and out.exists():
        existing = json.loads(out.read_text(encoding="utf-8"))
        merged = _merge(existing.get("stories", []), stories)
    else:
        merged = stories

    out.write_text(json.dumps({"stories": merged}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "input": str(inp), "output": str(out), "stories": len(merged)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
