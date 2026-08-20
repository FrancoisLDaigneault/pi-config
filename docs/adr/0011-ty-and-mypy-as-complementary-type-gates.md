# ADR-0011: ty and mypy as complementary type gates

- Status: accepted
- Date: 2026-08-20
- Supersedes: ADR-0001

## Context

ADR-0001 chose ty as the sole type gate to keep configuration and execution
small. Ty and mypy use different implementations and diagnostic models, so
neither checker is a complete substitute for the other. Running both gives a
second independent signal while preserving the fast ty feedback path.

## Decision

Keep ty and add mypy as complementary blocking gates. Ty runs first with
warnings treated as errors; mypy then runs in strict mode. Both check `src`,
`scripts` and `tests` for Python 3.12 through the pre-commit framework,
`just check` and the CI `quality` job. Checker-specific suppressions must be
narrow and justified at the diagnostic site; no global ignore profile is
introduced.

## Consequences

Type checking takes longer and dependency installation includes mypy and its
runtime packages. In return, a diagnostic unique to either engine blocks the
same required `quality` context. Upgrades are reviewed against both outputs;
a finding is fixed or narrowly explained rather than silenced across the
project. The existing ty and pyright configuration remains unchanged.
