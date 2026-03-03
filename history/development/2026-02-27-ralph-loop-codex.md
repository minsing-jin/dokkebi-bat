# Ralph Loop Codex Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 저장소 내부에 Codex용 Ralph Loop 스킬, Python 루프 실행기, 자동 검증 하네스를 구축한다.

**Architecture:** `scripts/ralph_loop.py`가 `prd.json`/`ralph_state.json`/`progress.md`를 관리하며 builder/verifier 명령을 실행한다. `--loop`로 연속 반복 실행을 지원하고 `--constraint`로 `--dangerously-skip-permissions` 같은 플래그를 명령 템플릿에 주입한다.

**Tech Stack:** Python 3 표준 라이브러리, pytest, shell harness

---

### Task 1: RED 테스트 작성
- Create: `tests/test_ralph_loop.py`
- Add failing tests for: single-step success transition, failure retention, constraint interpolation, loop mode completion.

### Task 2: GREEN 구현
- Create: `scripts/ralph_loop.py`
- Implement CLI, story selection, command execution, status updates, progress/state persistence.

### Task 3: 스킬/예제/하네스
- Create: `skills/ralph-loop-codex/SKILL.md`
- Create: `skills/ralph-loop-codex/examples/prd.json`
- Create: `skills/ralph-loop-codex/harness/run_harness.sh`

### Task 4: 검증
- Run: `pytest -q`
- Run: `bash skills/ralph-loop-codex/harness/run_harness.sh`

### Task 5: 커밋/푸시
- Commit all files and push to `origin/main`.
