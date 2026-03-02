from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CommandResult:
    command: str
    returncode: int
    stdout: str
    stderr: str


@dataclass
class StoryRuntime:
    raw: dict[str, Any]
    story_id: str
    title: str
    mode: str
    priority: int
    builder_commands: list[str] = field(default_factory=list)
    specify_commands: list[str] = field(default_factory=list)
    planner_commands: list[str] = field(default_factory=list)
    context_scribe_commands: list[str] = field(default_factory=list)
    verifier_commands: list[str] = field(default_factory=list)
    review_commands: list[str] = field(default_factory=list)
    testsmith_commands: list[str] = field(default_factory=list)
    show_me_hook_commands: list[str] = field(default_factory=list)
    issue_tiger_commands: list[str] = field(default_factory=list)
    tdd_red_command: str = ""
    tdd_green_command: str = ""
    qa_commands: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    non_goals: list[str] = field(default_factory=list)
    success_metrics: list[str] = field(default_factory=list)


@dataclass
class Paths:
    repo_dir: Path
    prd_path: Path
    state_path: Path
    progress_path: Path
    progress_jsonl_path: Path
    lessons_path: Path
    logs_dir: Path


@dataclass
class RunOptions:
    constraints: list[str]
    max_retries: int
    gate_command: str
    skip_gate: bool
    emit_context_pack: str
    lessons_mode: str
    mode: str


@dataclass
class RunContext:
    story: StoryRuntime
    attempt: int
    paths: Paths
    options: RunOptions
    git_before: dict[str, Any]
    events: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class PhaseResult:
    status: str
    phase: str
    command_results: list[CommandResult] = field(default_factory=list)
    summary: str = ""
