# Skills Catalog

## dokkebi-loop-codex
- Path: `skills/dokkebi-loop-codex`
- Purpose: PRD 기반 builder/verifier 자동 루프를 Codex/Claude Code에서 재사용 가능한 스킬로 제공

### Quick Start
```bash
./setup-dokkebi-loop.sh all
./run-dokkebi-loop.sh build --max-iters 20
```

`./setup-dokkebi-loop.sh codex` 실행 시 Codex 설정 + `~/.codex/skills` 심볼릭 링크 동기화가 함께 적용됩니다.
이때 과거 이름 `~/.codex/skills/ralph-loop-codex`는 자동 정리되고 `dokkebi-loop-codex`만 canonical로 유지됩니다.

### Direct Commands
```bash
python3 skills/dokkebi-loop-codex/scripts/ralph_loop.py --repo . --loop
python3 skills/dokkebi-loop-codex/scripts/ralph_loop.py --repo . --mode phase-config --story-id V2-001
bash skills/dokkebi-loop-codex/harness/run_harness.sh
```

## specify-gidometa-codex
- Path: `skills/specify-gidometa-codex`
- Purpose: 아이디어를 `prd.json` + `stories/<id>/story.md`로 부트스트랩

### Quick Start
```bash
python3 skills/specify-gidometa-codex/scripts/specify_gidometa.py --repo .
python3 skills/dokkebi-loop-codex/scripts/ralph_loop.py --repo . --bootstrap-prd --bootstrap-input-json idea.json --loop
```

## prd-md-to-json-codex
- Path: `skills/prd-md-to-json-codex`
- Purpose: 자연어 `prd.md`를 Ralph Loop용 `prd.json`으로 변환

### Quick Start
```bash
python3 skills/prd-md-to-json-codex/scripts/prd_md_to_json.py --repo . --input prd.md --output prd.json
```

## clodex
- Path: `skills/clodex`
- Purpose: Claude-style planning, option comparison, context compression, and Codex implementation handoff를 하나의 워크플로로 제공

### Quick Start
```bash
mkdir -p .clodex
cp skills/clodex/templates/context.md .clodex/context.md
cp skills/clodex/templates/plan.md .clodex/plan.md
cp skills/clodex/templates/implementation_packet.md .clodex/implementation_packet.md
cp skills/clodex/templates/status.md .clodex/status.md
```

`clodex`는 planning 전용 컨텍스트를 `.clodex/` 아래에 압축해서 유지하고, 그 결과를 바탕으로 Codex가 구현하도록 handoff하는 skill이다.
