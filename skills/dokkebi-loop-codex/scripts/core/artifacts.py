from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from core.files import utc_now


def ensure_story_contract(repo_dir: Path, story: dict[str, Any]) -> dict[str, Path]:
    story_id = str(story.get("id", "unknown"))
    story_dir = repo_dir / "stories" / story_id
    story_dir.mkdir(parents=True, exist_ok=True)

    story_md = story_dir / "story.md"
    plan_md = story_dir / "plan.md"
    context_md = story_dir / "context_pack.md"
    errors_md = story_dir / "errors.md"
    evidence_md = story_dir / "evidence.md"

    if not story_md.exists():
        ac = "\n".join(f"- {x}" for x in story.get("acceptance_criteria", [])) or "- (to be defined)"
        non_goals = "\n".join(f"- {x}" for x in story.get("non_goals", [])) or "- (to be defined)"
        risks = "\n".join(f"- {x}" for x in story.get("risks", [])) or "- (to be defined)"
        story_md.write_text(
            "\n".join(
                [
                    f"# Story {story_id}: {story.get('title', 'untitled')}",
                    "",
                    "## Goal",
                    str(story.get("goal", story.get("title", "untitled"))),
                    "",
                    "## Acceptance Criteria",
                    ac,
                    "",
                    "## Non-goals",
                    non_goals,
                    "",
                    "## Risks",
                    risks,
                    "",
                ]
            ),
            encoding="utf-8",
        )

    if not plan_md.exists():
        plan_md.write_text(
            "\n".join(
                [
                    f"# Plan for {story_id}",
                    "",
                    "## Steps",
                    "- Implement minimal scope for this story.",
                    "- Add/adjust tests for acceptance criteria.",
                    "- Verify evidence-gated commands.",
                    "",
                    "## Rollback",
                    "- Revert this story's diff and rerun verifier.",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    if not context_md.exists():
        context_md.write_text(
            "\n".join(
                [
                    f"# Context Pack: {story_id}",
                    "",
                    "## Summary",
                    "- Initialized.",
                    "",
                    "## Reproduction",
                    "- (none)",
                    "",
                    "## Next TODO",
                    "- Run implementer phase.",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    return {
        "dir": story_dir,
        "story": story_md,
        "plan": plan_md,
        "context_pack": context_md,
        "errors": errors_md,
        "evidence": evidence_md,
    }


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def update_context_pack(path: Path, *, summary: str, reproduction: list[str], next_todo: list[str], refs: list[str]) -> None:
    content = "\n".join(
        [
            f"# Context Pack ({utc_now()})",
            "",
            "## Summary",
            f"- {summary}",
            "",
            "## Reproduction",
            *([f"- `{c}`" for c in reproduction] or ["- (none)"]),
            "",
            "## Next TODO",
            *([f"- {t}" for t in next_todo] or ["- (none)"]),
            "",
            "## Artifact Refs",
            *([f"- {r}" for r in refs] or ["- (none)"]),
            "",
        ]
    )
    path.write_text(content, encoding="utf-8")


def write_errors(path: Path, *, story_id: str, phase: str, command: str, returncode: int, stderr: str, stdout: str) -> str:
    repro = command.strip()
    content = "\n".join(
        [
            f"# Errors: {story_id}",
            "",
            f"- phase: `{phase}`",
            f"- returncode: `{returncode}`",
            "",
            "## Reproduction",
            f"```bash\n{repro}\n```",
            "",
            "## Observed",
            "```text",
            (stderr or stdout or "(no output)").rstrip(),
            "```",
            "",
            "## Fix Instructions",
            "- Identify root cause from command output and changed files.",
            "- Apply one minimal fix, then rerun verifier commands.",
            "",
        ]
    )
    path.write_text(content + "\n", encoding="utf-8")
    return repro


def write_evidence(
    path: Path,
    *,
    story_id: str,
    commands: list[dict[str, Any]],
    summary: str,
    extra_sections: dict[str, list[str]] | None = None,
) -> dict[str, str]:
    lines = [f"# Evidence: {story_id}", "", f"- summary: {summary}", "", "## Commands"]
    hashes: dict[str, str] = {}
    for idx, cmd in enumerate(commands, start=1):
        text = json.dumps(cmd, ensure_ascii=False, sort_keys=True)
        h = _hash_text(text)
        hashes[f"cmd_{idx}"] = h
        lines.append(f"- `{cmd.get('command', '')}` rc={cmd.get('returncode', '')} hash={h}")
    if extra_sections:
        for section, items in extra_sections.items():
            lines.extend(["", f"## {section}"])
            lines.extend([f"- {item}" for item in items] or ["- (none)"])
    lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return hashes


def append_lessons(path: Path, *, story_id: str, phase: str, pattern: str, remedy: str) -> None:
    if not path.exists():
        path.write_text("# LESSONS\n\n", encoding="utf-8")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(
            "\n".join(
                [
                    f"## {utc_now()} {story_id} {phase}",
                    f"- Pattern: {pattern}",
                    f"- Remedy: {remedy}",
                    "",
                ]
            )
        )


def load_lessons(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")
