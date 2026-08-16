---
description: Maestro task contract — fill and dispatch to a subagent
argument-hint: "[task summary]"
---
Draft a task contract for this work, then dispatch it to the right subagent:

## Task Contract

**Goal** — one sentence: what outcome this task must produce.

**Context** — where to look first (files, prior decisions, NORTHSTAR.md KPIs affected).

**In scope** — the exact changes/deliverables expected.

**Out of scope** — what must NOT be touched. No drive-by cleanups, no unrelated refactors.

**Acceptance criteria** — verifiable, each one checkable by command or inspection:

- [ ] ...
- [ ] Existing tests pass; new behavior covered by a test.

**Rules in force** — Karpathy: think before coding (escalate ambiguity, don't guess), simplicity first (minimum code that solves the stated problem), surgical changes only, verify against the criteria above. YAGNI/KISS apply; a deliverable that does more than asked will be rejected.

**Verification** — commands the agent must run before reporting back, and evidence to return (diff summary, test output, risks).

Task: $ARGUMENTS
