# Dokkebi Loop Codex Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ralph Loop 자산을 `skills/dokkebi-loop-codex`로 통합하고 루트 `.sh` 기반 설치/실행 진입점을 제공한다.

**Architecture:** 실제 구현 파일은 모두 `skills/dokkebi-loop-codex`에 위치시킨다. 기존 경로(`ralph/*`, `scripts/ralph_loop.py`)는 thin wrapper로 유지해 깨짐 없이 새 위치로 위임한다. 루트 셸 스크립트는 Codex/Claude Code 설정 복사와 루프 실행 진입점 역할만 담당한다.

**Tech Stack:** bash, Python 3, 기존 Ralph Loop 스크립트/스키마/프롬프트

---

### Task 1: 스킬 디렉터리 구조 통합

**Files:**
- Create: `skills/dokkebi-loop-codex/`
- Create: `skills/dokkebi-loop-codex/ralph/`
- Create: `skills/dokkebi-loop-codex/scripts/`
- Create: `skills/dokkebi-loop-codex/tests/`
- Move/Copy from existing `ralph/`, `scripts/ralph_loop.py`, `tests/test_ralph_loop.py`, `skills/ralph-loop-codex/*`

**Step 1: 대상 디렉터리 생성**
Run: `mkdir -p skills/dokkebi-loop-codex/{ralph,scripts,tests,examples,harness,codex_setup}`
Expected: 디렉터리 생성 성공

**Step 2: 기존 자산을 새 위치로 이동/복제**
Run: shell move/copy commands
Expected: 새 경로에 동일 기능 자산 배치 완료

### Task 2: 스킬 문서 및 하네스 경로 정렬

**Files:**
- Modify: `skills/dokkebi-loop-codex/SKILL.md`
- Modify: `skills/dokkebi-loop-codex/harness/run_harness.sh`

**Step 1: 문서의 실행 경로를 새 구조 기준으로 갱신**
Run: edit file
Expected: 모든 명령 예시가 `skills/dokkebi-loop-codex` 기준으로 일관

**Step 2: 하네스가 새 위치의 runner를 사용하도록 수정**
Run: edit file
Expected: `python3 skills/dokkebi-loop-codex/scripts/ralph_loop.py ...`

### Task 3: 호환 래퍼 제공

**Files:**
- Modify/Create: `ralph/loop.sh`
- Modify/Create: `ralph/tools/gate.sh`
- Modify/Create: `scripts/ralph_loop.py`

**Step 1: 래퍼 스크립트로 위임 구현**
Run: edit file
Expected: 기존 명령이 새 스킬 경로의 실행 파일을 호출

### Task 4: 루트 설치/실행 스크립트 추가

**Files:**
- Create: `setup-dokkebi-loop.sh`
- Create: `run-dokkebi-loop.sh`
- Create: `SKILLS.md` (선택적 안내 문서)

**Step 1: 설치 스크립트 구현**
Run: add file
Expected: `~/.codex` 또는 `<repo>/.codex`로 템플릿 복사 가능

**Step 2: 실행 진입점 구현**
Run: add file
Expected: `./run-dokkebi-loop.sh build --max-iters 20` 형태로 실행 가능

### Task 5: 테스트/검증 정렬

**Files:**
- Modify: `tests/test_ralph_loop.py` (import/경로 갱신)

**Step 1: 테스트가 새 runner 위치를 바라보도록 수정**
Run: edit file
Expected: 테스트가 통과 가능한 경로 참조

**Step 2: 게이트 및 하네스 실행**
Run: `./ralph/tools/gate.sh`, `bash skills/dokkebi-loop-codex/harness/run_harness.sh`
Expected: gate pass 또는 skipped, harness 성공
