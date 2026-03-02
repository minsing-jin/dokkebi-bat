# Dokkebi Loop Codex Design

## Goal
Ralph Loop 관련 모든 자산을 `skills/dokkebi-loop-codex` 아래로 통합하고, 루트의 간단한 셸 스크립트만으로 Codex/Claude Code 환경에서 설치 및 실행 가능하게 만든다.

## Scope
- `ralph/` 디렉터리의 실행/프롬프트/스키마/게이트/셋업 템플릿을 `skills/dokkebi-loop-codex/ralph/`로 이동
- `scripts/ralph_loop.py`를 `skills/dokkebi-loop-codex/scripts/ralph_loop.py`로 이동
- 스킬 문서/예제/하네스를 `skills/dokkebi-loop-codex/` 구조로 정리
- 루트에 직관적 진입점 제공:
  - `setup-dokkebi-loop.sh` (Codex/Claude Code 설정 파일 설치)
  - `run-dokkebi-loop.sh` (plan/build/review 실행)
- 기존 호출과의 호환을 위해 최소 래퍼 유지:
  - `ralph/loop.sh`, `ralph/tools/gate.sh`, `scripts/ralph_loop.py`는 새 경로로 위임

## Non-goals
- Ralph 실행 로직 자체 변경
- PRD 스토리 내용 변경

## Architecture
- 단일 소스 오브 트루스는 `skills/dokkebi-loop-codex/`로 고정한다.
- 루트 래퍼는 경로 위임만 수행하여 유지보수 비용을 최소화한다.
- 설치 스크립트는 `~/.codex` 및 프로젝트 `.codex`에 템플릿을 복사하는 기능을 제공한다.

## Compatibility
- 기존 `./ralph/tools/gate.sh`, `./ralph/loop.sh`, `python scripts/ralph_loop.py`는 동작을 유지한다.
- 신규 권장 경로는 `skills/dokkebi-loop-codex/*` 및 루트 진입 스크립트다.
