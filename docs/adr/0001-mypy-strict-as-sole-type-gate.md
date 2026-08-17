# ADR-0001: mypy --strict as the sole type gate

- Status: accepted
- Date: 2026-08-16

## Context

pi-config is a ~600-line stdlib-only tool with a behavioral test suite above
90% branch coverage. Static typing was initially skipped (YAGNI: small
surface, tests as the safety net). Going public with an all-gates-automated
policy made the typing blind spot the one unjustified exception, and the cost
of adopting strict typing was minimal while the codebase was small.

## Decision

Adopt `mypy --strict` as the only type gate: dev dependency in the uv group,
`[tool.mypy]` with `strict = true` over `src`, `scripts` and `tests`. Zero
per-module overrides, zero `type: ignore`. Rejected: pyright as a gate (adds
a Node runtime; mypy is tracked by Dependabot via the uv ecosystem) and ty
(preview at decision time). The `[tool.pyright]` section in pyproject.toml is
editor wiring only - it points pyright-family checkers embedded in editors at
the project venv; it is not a gate.

## Consequences

The initial run surfaced 93 errors, all fixed by annotations alone (shipped
with release v0.2.0). The gate rides the pre-commit hook, the CI quality job
and `just check`. A future mypy major may add new strict errors; that is the
gate working as intended.
