# Dokkebi Loop Robustness Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** superpowers 워크플로우 원칙(verification, debugging, TDD, review)을 Ralph Loop 실행기에 내장해 강건성을 높인다.

**Architecture:** `skills/dokkebi-loop-codex/scripts/ralph_loop.py`에 gate/review/tdd 단계를 명시적 phase로 추가하고, 시도별 trace JSON에 각 phase 결과를 기록한다.

**Tech Stack:** Python 3 stdlib, pytest tests, shell commands

---

### Task 1: RED 테스트 추가
- gate 단계 자동 검증, review_commands, tdd red/green, trace 확장 테스트 추가

### Task 2: GREEN 구현
- CLI 옵션: `--gate-command`, `--skip-gate`
- Story 확장 필드: `review_commands`, `tdd_red_command`, `tdd_green_command`
- 실패 시 디버그 번들 생성
- trace JSON phase 확장

### Task 3: 문서 업데이트
- SKILL.md에 새 필드/실행 단계 문서화

### Task 4: 검증
- gate/harness 실행
