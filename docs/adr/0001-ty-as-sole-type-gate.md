# ADR-0001: Astral ty as the sole type gate

- Status: accepted
- Date: 2026-08-20

## Context

pi-config is a small stdlib-only tool with a behavioral test suite above 90%
branch coverage. Going public with an all-gates-automated policy made static
typing necessary, while keeping the checker fast and its configuration small.

## Decision

Adopt Astral ty as the only type gate. The locked development dependency runs
`ty check --error-on-warning src scripts tests`, with Python 3.12 selected in
`[tool.ty.environment]`. Defaults remain authoritative, warnings block the
gate, and there are no global diagnostic ignores. The `[tool.pyright]` section
in pyproject.toml remains editor wiring only; it is not a quality gate.

## Consequences

The gate checks source, scripts and tests through the pre-commit framework, the
CI `quality` job and `just check`. The migration baseline and the first ty run
both passed without diagnostics. Future checker releases may add findings;
that is the gate working as intended.
