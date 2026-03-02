from __future__ import annotations

from typing import Any

from core.models import StoryRuntime


def _safe_int(value: Any, default: int = 9999) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def infer_mode(story: dict[str, Any], requested_mode: str) -> str:
    if requested_mode in {"legacy", "basic"}:
        return "basic"
    if requested_mode in {"v2", "phase-config"}:
        return "phase-config"
    story_mode = str(story.get("mode", ""))
    if story_mode in {"legacy", "basic"}:
        return "basic"
    if story_mode in {"v2", "phase-config"}:
        return "phase-config"
    if "phase_config" in story:
        return "phase-config"
    return "basic"


def normalize_story(story: dict[str, Any], requested_mode: str) -> StoryRuntime:
    mode = infer_mode(story, requested_mode)
    phase_config = story.get("phase_config", {}) if isinstance(story.get("phase_config"), dict) else {}

    builder_commands = list(story.get("builder_commands", []))
    specify_commands = list(story.get("specify_commands", []))
    planner_commands = list(story.get("planner_commands", []))
    context_scribe_commands = list(story.get("context_scribe_commands", []))
    verifier_commands = list(story.get("verifier_commands", []))
    review_commands = list(story.get("review_commands", []))
    testsmith_commands = list(story.get("testsmith_commands", []))
    show_me_hook_commands = list(story.get("show_me_hook_commands", []))
    issue_tiger_commands = list(story.get("issue_tiger_commands", []))
    qa_commands = list(story.get("qa_commands", []))

    if mode == "phase-config":
        specify_cfg = phase_config.get("specify_commands", [])
        planner_cfg = phase_config.get("planner_commands", [])
        context_scribe_cfg = phase_config.get("context_scribe_commands", [])
        implementer_cfg = phase_config.get("implementer_commands", [])
        verifier_cfg = phase_config.get("verifier_commands", [])
        testsmith_cfg = phase_config.get("testsmith_commands", [])
        review_cfg = phase_config.get("review_commands", [])
        hook_cfg = phase_config.get("show_me_hook_commands", [])
        issue_cfg = phase_config.get("issue_tiger_commands", [])
        qa_cfg = phase_config.get("qa_commands", [])
        if specify_cfg:
            specify_commands = list(specify_cfg)
        if planner_cfg:
            planner_commands = list(planner_cfg)
        if context_scribe_cfg:
            context_scribe_commands = list(context_scribe_cfg)
        if implementer_cfg:
            builder_commands = list(implementer_cfg)
        if verifier_cfg:
            verifier_commands = list(verifier_cfg)
        if testsmith_cfg:
            testsmith_commands = list(testsmith_cfg)
        if review_cfg:
            review_commands = list(review_cfg)
        if hook_cfg:
            show_me_hook_commands = list(hook_cfg)
        if issue_cfg:
            issue_tiger_commands = list(issue_cfg)
        if qa_cfg:
            qa_commands = list(qa_cfg)

    return StoryRuntime(
        raw=story,
        story_id=str(story.get("id", "unknown")),
        title=str(story.get("title", "untitled")),
        mode=mode,
        priority=_safe_int(story.get("priority", 9999)),
        specify_commands=specify_commands,
        planner_commands=planner_commands,
        context_scribe_commands=context_scribe_commands,
        builder_commands=builder_commands,
        verifier_commands=verifier_commands,
        review_commands=review_commands,
        testsmith_commands=testsmith_commands,
        show_me_hook_commands=show_me_hook_commands,
        issue_tiger_commands=issue_tiger_commands,
        tdd_red_command=str(story.get("tdd_red_command", "")).strip(),
        tdd_green_command=str(story.get("tdd_green_command", "")).strip(),
        qa_commands=qa_commands,
        acceptance_criteria=list(story.get("acceptance_criteria", [])),
        constraints=list(story.get("constraints", [])),
        dependencies=list(story.get("dependencies", [])),
        risks=list(story.get("risks", [])),
        non_goals=list(story.get("non_goals", [])),
        success_metrics=list(story.get("success_metrics", [])),
    )


def pick_story(prd: dict[str, Any], requested_mode: str, story_id: str | None) -> StoryRuntime | None:
    stories = [s for s in prd.get("stories", []) if s.get("status", "todo") == "todo"]
    if story_id:
        stories = [s for s in stories if str(s.get("id")) == story_id]
    if not stories:
        return None
    stories.sort(key=lambda s: (_safe_int(s.get("priority", 9999)), str(s.get("id", ""))))
    return normalize_story(stories[0], requested_mode)


def _is_nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_string_list(story: dict[str, Any], key: str, *, non_empty: bool) -> list[str]:
    errors: list[str] = []
    if key not in story:
        return [f"missing field `{key}`"]
    value = story.get(key)
    if not isinstance(value, list):
        return [f"`{key}` must be a list"]
    if non_empty and len(value) == 0:
        errors.append(f"`{key}` must contain at least one item")
    for idx, item in enumerate(value):
        if not _is_nonempty_str(item):
            errors.append(f"`{key}[{idx}]` must be a non-empty string")
    return errors


def validate_prd_contract(prd: dict[str, Any], requested_mode: str, story_id: str | None = None) -> list[str]:
    errors: list[str] = []
    stories = prd.get("stories")
    if not isinstance(stories, list) or len(stories) == 0:
        return ["`stories` must be a non-empty list"]

    selected_count = 0
    for idx, story in enumerate(stories):
        if not isinstance(story, dict):
            errors.append(f"stories[{idx}] must be an object")
            continue
        sid = str(story.get("id", "")).strip()
        if story_id and sid != story_id:
            continue
        status = str(story.get("status", "todo"))
        if not story_id and status == "done":
            continue
        selected_count += 1
        prefix = f"stories[{idx}]"

        if not _is_nonempty_str(story.get("id")):
            errors.append(f"{prefix}: missing/invalid `id`")
        if not _is_nonempty_str(story.get("title")):
            errors.append(f"{prefix}: missing/invalid `title`")
        if status not in {"todo", "doing", "done"}:
            errors.append(f"{prefix}: `status` must be one of todo|doing|done")
        if "priority" not in story:
            errors.append(f"{prefix}: missing field `priority`")
        else:
            try:
                int(story.get("priority"))
            except (TypeError, ValueError):
                errors.append(f"{prefix}: `priority` must be an integer")

        for key, non_empty in [
            ("acceptance_criteria", True),
            ("non_goals", False),
            ("constraints", False),
            ("dependencies", False),
            ("risks", False),
            ("success_metrics", False),
        ]:
            for err in _validate_string_list(story, key, non_empty=non_empty):
                errors.append(f"{prefix}: {err}")

        mode = infer_mode(story, requested_mode)
        if mode == "phase-config":
            phase_config = story.get("phase_config")
            if not isinstance(phase_config, dict):
                errors.append(f"{prefix}: missing/invalid `phase_config` object")
                continue
            for key in ["implementer_commands", "verifier_commands"]:
                value = phase_config.get(key)
                if not isinstance(value, list) or len(value) == 0:
                    errors.append(f"{prefix}: `phase_config.{key}` must be a non-empty list")
                    continue
                for cmd_idx, cmd in enumerate(value):
                    if not _is_nonempty_str(cmd):
                        errors.append(f"{prefix}: `phase_config.{key}[{cmd_idx}]` must be a non-empty string")
        else:
            for key in ["builder_commands", "verifier_commands"]:
                value = story.get(key)
                if not isinstance(value, list) or len(value) == 0:
                    errors.append(f"{prefix}: `{key}` must be a non-empty list")
                    continue
                for cmd_idx, cmd in enumerate(value):
                    if not _is_nonempty_str(cmd):
                        errors.append(f"{prefix}: `{key}[{cmd_idx}]` must be a non-empty string")

    if story_id and selected_count == 0:
        errors.append(f"story `{story_id}` not found in prd.json")
    return errors
