# ADR-0006: 90% branch-coverage floor riding pytest addopts

- Status: accepted
- Date: 2026-08-17

## Context

A coverage gate should ride existing mechanisms instead of adding steps, and
branch-aware measurement is the honest metric for a codebase whose value is
concentrated in error paths (failing backup sections, unreadable JSON,
refusing to restore auth.json).

## Decision

`[tool.coverage.run] branch = true` and `--cov-fail-under=90` in pytest
`addopts` (PR #11, release v0.4.0). Because the floor lives in the pytest
config, the pre-commit hook, the CI quality job and `just check` inherit it
automatically - zero new steps anywhere. The floor was set only after
measuring reality: 92.84% branch coverage at introduction, with zero tests
written to inflate the number and zero pragmas.

## Consequences

Subset runs need `--no-cov` (the floor is meant for the full suite). CI
publishes `coverage.xml` plus JUnit results as a run artifact and prints the
percentage in the run summary, with the floor value derived from
pyproject.toml rather than hardcoded.
