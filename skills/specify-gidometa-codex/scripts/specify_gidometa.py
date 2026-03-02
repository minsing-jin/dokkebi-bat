#!/usr/bin/env python3
"""Bootstrap PRD and story artifacts from structured input or interactive prompts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate prd.json + stories/<id>/story.md")
    p.add_argument("--repo", default=".", help="target repository root")
    p.add_argument("--input-json", default="", help="path to JSON spec file")
    p.add_argument("--overwrite", action="store_true", help="overwrite existing story markdown files")
    p.add_argument("--advanced", action="store_true", help="enable advanced tech stack questionnaire")
    p.add_argument("--emit-arch", action="store_true", help="write ARCH.md")
    p.add_argument("--emit-conventions", action="store_true", help="write CONVENTIONS.md")
    p.add_argument("--emit-adr", action="store_true", help="write ADR draft")
    p.add_argument(
        "--socratic-mode",
        choices=["off", "human", "auto"],
        default="auto",
        help="off: skip socratic prompts, human: ask user, auto: agent-derived answers from context",
    )
    p.add_argument("--prd-md", default="", help="optional PRD markdown path used as context for auto socratic mode")
    return p.parse_args()


def _heuristic_list(text: str, *, label: str, fallback: list[str]) -> list[str]:
    lowered = text.lower()
    if label == "constraints":
        out: list[str] = []
        for token in ["must", "deadline", "budget", "compliance", "security", "latency", "cost"]:
            if token in lowered:
                out.append(f"Respect {token}-related requirement from PRD context")
        return out or fallback
    if label == "risks":
        out = []
        for token in ["risk", "unclear", "dependency", "integration", "regression", "performance", "security"]:
            if token in lowered:
                out.append(f"Potential {token} risk inferred from PRD context")
        return out or fallback
    if label == "non_goals":
        out = []
        if "mvp" in lowered:
            out.append("Exclude post-MVP enhancements in this story")
        if "prototype" in lowered:
            out.append("Avoid production-hardening beyond stated scope")
        return out or fallback
    if label == "success_metrics":
        out = []
        if "latency" in lowered:
            out.append("Latency target is satisfied")
        if "coverage" in lowered or "test" in lowered:
            out.append("Automated tests pass for acceptance criteria")
        return out or fallback
    return fallback


def _auto_socratic_fill(
    story: dict[str, Any],
    *,
    project_title: str,
    project_goal: str,
    prd_md_text: str,
    existing_prd: dict[str, Any],
) -> tuple[list[str], list[str], list[str], list[str]]:
    context = "\n".join(
        [
            project_title,
            project_goal,
            prd_md_text,
            json.dumps(existing_prd, ensure_ascii=False),
            story.get("title", ""),
            " ".join(story.get("acceptance_criteria", [])),
        ]
    )
    non_goals = story.get("non_goals", []) or _heuristic_list(
        context,
        label="non_goals",
        fallback=[f"Keep scope strictly to '{story.get('title', 'this story')}'"],
    )
    constraints = story.get("constraints", []) or _heuristic_list(
        context,
        label="constraints",
        fallback=["Keep changes minimal and verifiable with executable commands"],
    )
    risks = story.get("risks", []) or _heuristic_list(
        context,
        label="risks",
        fallback=["Ambiguous requirement interpretation can cause rework"],
    )
    success_metrics = story.get("success_metrics", []) or _heuristic_list(
        context,
        label="success_metrics",
        fallback=["All acceptance criteria map to passing verifier commands"],
    )
    return non_goals, constraints, risks, success_metrics


def _infer_from_context(title: str, ac: list[str], context: str, *, kind: str) -> list[str]:
    text = " ".join([title, *ac, context]).lower()
    if kind == "non_goals":
        if "mvp" in text or "prototype" in text:
            return [f"Limit scope to MVP behavior for: {title}"]
        return [f"Exclude work beyond acceptance criteria for: {title}"]
    if kind == "constraints":
        if "security" in text or "compliance" in text:
            return [f"Honor security/compliance constraints for: {title}"]
        return [f"Implement with minimal safe changes for: {title}"]
    if kind == "dependencies":
        if "database" in text or "api" in text or "integration" in text:
            return [f"Coordinate with existing integration dependencies for: {title}"]
        return [f"Use existing repository modules only for: {title}"]
    if kind == "risks":
        if "performance" in text or "latency" in text:
            return [f"Performance regression risk exists for: {title}"]
        return [f"Requirement drift risk exists for: {title}"]
    if "test" in text or "coverage" in text:
        return [f"Automated verification passes for: {title}"]
    return [f"Acceptance criteria are satisfied for: {title}"]


def _default_phase_config(story_id: str) -> dict[str, list[str]]:
    safe_id = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in story_id)
    done_file = f".ralph/artifacts/{safe_id}.done"
    plan_file = f".ralph/artifacts/{safe_id}.plan.txt"
    implementer = [f"mkdir -p .ralph/artifacts", f"printf '%s\\n' '{safe_id}' > {done_file}"]
    verifier = [f"test -f {done_file}"]
    return {
        "specify_commands": [f"mkdir -p .ralph/artifacts && printf '%s\\n' 'specify:{safe_id}' > {plan_file}"],
        "planner_commands": [f"grep -q '{safe_id}' {plan_file}"],
        "context_scribe_commands": [f"test -f {plan_file}"],
        "show_me_hook_commands": [f"test -f {plan_file}"],
        "implementer_commands": implementer,
        "testsmith_commands": verifier,
        "verifier_commands": verifier,
        "review_commands": verifier,
        "issue_tiger_commands": [f"test -f {done_file}"],
        "qa_commands": [f"test -f {done_file}"],
    }


def _load_payload(args: argparse.Namespace, repo: Path) -> dict[str, Any]:
    if args.input_json:
        return json.loads(Path(args.input_json).read_text(encoding="utf-8"))

    project_title = input("Project title: ").strip() or "Untitled Project"
    project_goal = input("Project goal: ").strip() or project_title
    story_count = int((input("Number of stories [1]: ").strip() or "1"))
    tech_stack: dict[str, str] = {}
    if args.advanced:
        print("Advanced Tech Stack Mode")
        tech_stack["framework"] = input("Framework [FastAPI/Next.js/Django/etc]: ").strip() or "unspecified"
        tech_stack["database"] = input("Database [PostgreSQL/MySQL/SQLite/etc]: ").strip() or "unspecified"
        tech_stack["infrastructure"] = input("Infrastructure [AWS/GCP/Azure/local]: ").strip() or "unspecified"
        tech_stack["deployment"] = input("Deployment strategy [container/serverless/vm]: ").strip() or "unspecified"
        tech_stack["test_strategy"] = input("Test strategy [unit+integration+e2e]: ").strip() or "unit+integration"

    stories: list[dict[str, Any]] = []
    for idx in range(1, story_count + 1):
        sid = input(f"Story {idx} id [S-{idx:03d}]: ").strip() or f"S-{idx:03d}"
        title = input(f"Story {idx} title: ").strip() or sid
        ac_raw = input(f"Story {idx} acceptance criteria (comma-separated): ").strip()
        acceptance_criteria = [x.strip() for x in ac_raw.split(",") if x.strip()] or [f"{title} is complete"]
        priority = int((input(f"Story {idx} priority [1]: ").strip() or "1"))
        non_goals: list[str] = []
        constraints: list[str] = []
        risks: list[str] = []
        success_metrics: list[str] = []
        if args.socratic_mode == "human":
            print("Socratic prompts (short answers, comma-separated where relevant):")
            ng = input("What is explicitly out-of-scope?: ").strip()
            cs = input("What hard constraints exist (time/budget/compliance)?: ").strip()
            rk = input("Top failure risks?: ").strip()
            sm = input("How do we measure success?: ").strip()
            non_goals = [x.strip() for x in ng.split(",") if x.strip()]
            constraints = [x.strip() for x in cs.split(",") if x.strip()]
            risks = [x.strip() for x in rk.split(",") if x.strip()]
            success_metrics = [x.strip() for x in sm.split(",") if x.strip()]
        stories.append(
            {
                "id": sid,
                "title": title,
                "status": "todo",
                "priority": priority,
                "mode": "phase-config",
                "acceptance_criteria": acceptance_criteria,
                "non_goals": non_goals or _infer_from_context(title, acceptance_criteria, project_goal, kind="non_goals"),
                "constraints": constraints or _infer_from_context(title, acceptance_criteria, project_goal, kind="constraints"),
                "dependencies": _infer_from_context(title, acceptance_criteria, project_goal, kind="dependencies"),
                "risks": risks or _infer_from_context(title, acceptance_criteria, project_goal, kind="risks"),
                "success_metrics": success_metrics or _infer_from_context(title, acceptance_criteria, project_goal, kind="success_metrics"),
                "phase_config": _default_phase_config(sid),
            }
        )

    return {
        "project": {"title": project_title, "goal": project_goal},
        "tech_stack": tech_stack,
        "generate": {
            "arch": args.emit_arch,
            "conventions": args.emit_conventions,
            "adr": args.emit_adr,
        },
        "stories": stories,
    }


def _story_markdown(project_title: str, project_goal: str, story: dict[str, Any]) -> str:
    def bullets(items: list[str], fallback: str) -> str:
        if not items:
            return f"- {fallback}"
        return "\n".join(f"- {item}" for item in items)

    return "\n".join(
        [
            f"# Story {story['id']}: {story['title']}",
            "",
            "## Project Context",
            f"- project: {project_title}",
            f"- goal: {project_goal}",
            "",
            "## Goal",
            story["title"],
            "",
            "## Acceptance Criteria",
            bullets(story.get("acceptance_criteria", []), "(to be defined)"),
            "",
            "## Non-goals",
            bullets(story.get("non_goals", []), "(to be defined)"),
            "",
            "## Constraints",
            bullets(story.get("constraints", []), "(to be defined)"),
            "",
            "## Dependencies",
            bullets(story.get("dependencies", []), "(none)"),
            "",
            "## Risks",
            bullets(story.get("risks", []), "(to be defined)"),
            "",
            "## Success Metrics",
            bullets(story.get("success_metrics", []), "(to be defined)"),
            "",
        ]
    ) + "\n"


def _merge_stories(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for story in existing:
        by_id[str(story.get("id", ""))] = story
    for story in incoming:
        by_id[str(story.get("id", ""))] = story

    merged = list(by_id.values())
    merged.sort(key=lambda s: (int(s.get("priority", 9999)), str(s.get("id", ""))))
    return merged


def _normalize_story(story: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(story)
    sid = str(normalized.get("id", "S-000"))
    title = str(normalized.get("title", sid))
    ac = [x for x in normalized.get("acceptance_criteria", []) if isinstance(x, str) and x.strip()]
    ac = ac or [f"{title} is complete"]
    context_blob = f"{title} {' '.join(ac)}"
    normalized.setdefault("status", "todo")
    normalized.setdefault("priority", 1)
    normalized.setdefault("mode", "phase-config")
    normalized["acceptance_criteria"] = ac
    normalized["non_goals"] = [x for x in normalized.get("non_goals", []) if isinstance(x, str) and x.strip()] or _infer_from_context(title, ac, context_blob, kind="non_goals")
    normalized["constraints"] = [x for x in normalized.get("constraints", []) if isinstance(x, str) and x.strip()] or _infer_from_context(title, ac, context_blob, kind="constraints")
    normalized["dependencies"] = [x for x in normalized.get("dependencies", []) if isinstance(x, str) and x.strip()] or _infer_from_context(title, ac, context_blob, kind="dependencies")
    normalized["risks"] = [x for x in normalized.get("risks", []) if isinstance(x, str) and x.strip()] or _infer_from_context(title, ac, context_blob, kind="risks")
    normalized["success_metrics"] = [x for x in normalized.get("success_metrics", []) if isinstance(x, str) and x.strip()] or _infer_from_context(title, ac, context_blob, kind="success_metrics")
    phase = normalized.get("phase_config")
    defaults = _default_phase_config(sid)
    if not isinstance(phase, dict):
        normalized["phase_config"] = defaults
    else:
        merged: dict[str, list[str]] = {}
        for key, default_value in defaults.items():
            current = phase.get(key)
            if isinstance(current, list):
                cleaned = [x for x in current if isinstance(x, str) and x.strip()]
                merged[key] = cleaned or default_value
            else:
                merged[key] = default_value
        if not phase.get("testsmith_commands"):
            merged["testsmith_commands"] = list(merged["verifier_commands"])
        if not phase.get("review_commands"):
            merged["review_commands"] = list(merged["verifier_commands"])
        if not phase.get("qa_commands"):
            merged["qa_commands"] = list(merged["verifier_commands"])
        if not phase.get("issue_tiger_commands"):
            merged["issue_tiger_commands"] = list(merged["verifier_commands"])
        normalized["phase_config"] = merged
    return normalized


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).resolve()
    repo.mkdir(parents=True, exist_ok=True)

    payload = _load_payload(args, repo)
    project = payload.get("project", {})
    project_title = str(project.get("title", "Untitled Project"))
    project_goal = str(project.get("goal", project_title))
    tech_stack = payload.get("tech_stack", {})
    generate = payload.get("generate", {})
    stories = [_normalize_story(s) for s in payload.get("stories", [])]

    prd_path = repo / "prd.json"
    if prd_path.exists():
        current = json.loads(prd_path.read_text(encoding="utf-8"))
    else:
        current = {"stories": []}

    prd_md_text = ""
    if args.prd_md:
        prd_md_text = Path(args.prd_md).read_text(encoding="utf-8")

    socratic_log_lines: list[str] = []
    if args.socratic_mode == "auto":
        for story in stories:
            non_goals, constraints, risks, success_metrics = _auto_socratic_fill(
                story,
                project_title=project_title,
                project_goal=project_goal,
                prd_md_text=prd_md_text,
                existing_prd=current,
            )
            story["non_goals"] = non_goals
            story["constraints"] = constraints
            story["risks"] = risks
            story["success_metrics"] = success_metrics
            socratic_log_lines.extend(
                [
                    f"## {story.get('id')}",
                    "- mode: auto",
                    f"- non_goals: {', '.join(non_goals)}",
                    f"- constraints: {', '.join(constraints)}",
                    f"- risks: {', '.join(risks)}",
                    f"- success_metrics: {', '.join(success_metrics)}",
                    "",
                ]
            )

    merged_stories = _merge_stories(current.get("stories", []), stories)
    prd_path.write_text(json.dumps({"stories": merged_stories}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    stories_dir = repo / "stories"
    stories_dir.mkdir(parents=True, exist_ok=True)

    written: list[str] = []
    for story in stories:
        sid = str(story.get("id", "unknown"))
        sdir = stories_dir / sid
        sdir.mkdir(parents=True, exist_ok=True)
        story_md = sdir / "story.md"
        if story_md.exists() and not args.overwrite:
            continue
        story_md.write_text(_story_markdown(project_title, project_goal, story), encoding="utf-8")
        written.append(str(story_md))

    if args.socratic_mode in {"auto", "human"}:
        soc_dir = repo / ".ralph" / "socratic"
        soc_dir.mkdir(parents=True, exist_ok=True)
        soc_path = soc_dir / f"specify.{project_title.replace(' ', '_')}.md"
        if args.socratic_mode == "human":
            soc_path.write_text("# Socratic Log\n\n- mode: human\n- responses collected interactively\n", encoding="utf-8")
        else:
            soc_path.write_text("# Socratic Log\n\n" + "\n".join(socratic_log_lines), encoding="utf-8")

    if generate.get("arch"):
        (repo / "ARCH.md").write_text(
            "\n".join(
                [
                    f"# Architecture: {project_title}",
                    "",
                    f"- Goal: {project_goal}",
                    f"- Framework: {tech_stack.get('framework', 'unspecified')}",
                    f"- Database: {tech_stack.get('database', 'unspecified')}",
                    f"- Infrastructure: {tech_stack.get('infrastructure', 'unspecified')}",
                    f"- Deployment: {tech_stack.get('deployment', 'unspecified')}",
                    "",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
    if generate.get("conventions"):
        (repo / "CONVENTIONS.md").write_text(
            "\n".join(
                [
                    "# Engineering Conventions",
                    "",
                    "- Keep changes minimal and story-scoped.",
                    "- Require evidence commands before marking PASS.",
                    "- Maintain context_pack and lessons after each iteration.",
                    "",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
    if generate.get("adr"):
        adr_dir = repo / "ADR"
        adr_dir.mkdir(parents=True, exist_ok=True)
        (adr_dir / "0001-tech-stack.md").write_text(
            "\n".join(
                [
                    "# ADR 0001: Initial Tech Stack",
                    "",
                    "## Context",
                    f"- project: {project_title}",
                    "",
                    "## Decision",
                    f"- framework: {tech_stack.get('framework', 'unspecified')}",
                    f"- database: {tech_stack.get('database', 'unspecified')}",
                    f"- infrastructure: {tech_stack.get('infrastructure', 'unspecified')}",
                    f"- deployment: {tech_stack.get('deployment', 'unspecified')}",
                    "",
                    "## Consequences",
                    "- Revisit after first end-to-end milestone.",
                    "",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    print(
        json.dumps(
            {
                "status": "ok",
                "project": project_title,
                "stories_added_or_updated": [s.get("id") for s in stories],
                "written_story_docs": written,
                "prd": str(prd_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
