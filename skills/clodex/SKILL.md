---
name: clodex
description: Use when you want Claude-style collaborative planning, option generation, and context compression before Codex implementation.
---

# Clodex

Clodex is a bridge workflow that combines Claude-style planning with Codex implementation.

Use it only when the user explicitly asks for `clodex` or clearly wants:
- strong planning with multiple options
- a jointly refined implementation plan
- a compressed shared context packet that saves tokens
- a handoff from planning into implementation

## Core idea

One agent owns context compression.

That agent writes the canonical handoff files under `.clodex/`, and the implementation agent reads those files instead of rebuilding the full context from scratch.

## File contract

Clodex uses these files:

- `.clodex/context.md`
  - Canonical compressed project context.
- `.clodex/plan.md`
  - Final agreed plan with options, tradeoffs, and selected approach.
- `.clodex/implementation_packet.md`
  - Decision-complete build packet for Codex.
- `.clodex/status.md`
  - Current steward, current phase, next action, blockers, and handoff state.

Templates live in:
- `skills/clodex/templates/context.md`
- `skills/clodex/templates/plan.md`
- `skills/clodex/templates/implementation_packet.md`
- `skills/clodex/templates/status.md`

## Modes

### If invoked from Claude

Claude should:
- explore the repo or prompt context
- generate multiple implementation options
- compare tradeoffs
- ask high-value planning questions when needed
- converge on one selected design
- write `.clodex/context.md`
- write `.clodex/plan.md`
- write `.clodex/implementation_packet.md`
- write `.clodex/status.md` with `steward: Claude`, then mark handoff ready for Codex

Claude should not start broad implementation unless the user explicitly asks for it.

### If invoked from Codex

Codex should:
- read `.clodex/context.md`, `.clodex/plan.md`, and `.clodex/implementation_packet.md` first
- treat them as the primary working context
- implement according to the packet
- keep changes aligned with the selected approach
- update `.clodex/status.md` during implementation and verification
- only widen context gathering when the packet is incomplete or inconsistent with the repo

If the planning packet is missing, Codex should create it first in the same Clodex style before implementing.

## Required behavior

### Planning phase

- Offer at least 2 meaningful implementation options when tradeoffs exist.
- Make one recommendation and explain why.
- Resolve the chosen direction into a concrete plan.
- Keep the plan decision-complete before implementation starts.

### Context compression phase

- Summarize only what the implementation side needs.
- Remove chat noise and repeated exploration.
- Keep file references, interfaces, constraints, and risks.
- Prefer short, high-signal context over full transcript replay.

### Implementation handoff phase

The implementation packet must include:
- goal
- scope
- out-of-scope
- exact files or directories likely to change
- relevant interfaces or contracts
- step-by-step implementation sequence
- verification commands
- acceptance criteria
- unresolved risks or watchpoints

## Recommended workflow

### Start planning

If the user starts with an idea, create or update:
- `.clodex/context.md`
- `.clodex/plan.md`
- `.clodex/status.md`

### Lock implementation packet

Before coding, create:
- `.clodex/implementation_packet.md`

This file should be sufficient for a fresh Codex session to continue with minimal extra context.

### Implement

The implementation side reads the packet, executes, and updates:
- `.clodex/status.md`

When meaningful repo discoveries occur, roll the delta back into:
- `.clodex/context.md`

## Token discipline

Clodex exists to reduce re-explaining the same project state.

Rules:
- prefer reading `.clodex/*` first
- update the compressed files instead of restating long context in chat
- do not duplicate the same repository summary across turns
- keep one canonical context steward at a time

## Steward model

Set the active steward in `.clodex/status.md`.

Allowed values:
- `Claude`
- `Codex`

Whoever is the steward is responsible for keeping `.clodex/context.md` current.

## Handoff completion

Planning is complete when:
- `.clodex/plan.md` reflects the chosen option
- `.clodex/implementation_packet.md` is decision-complete
- `.clodex/status.md` says the next actor can implement without reopening planning

Implementation is complete when:
- requested code changes are done
- verification commands pass
- `.clodex/status.md` records completion or the next blocker
