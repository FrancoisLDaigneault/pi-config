# ADR-0008: Documentation drift gate

- Status: accepted
- Date: 2026-08-17

## Context

Docs repeatedly drifted from tooling reality: gate lists missed commands two
passes in a row, test counts went stale, and a release-semantics claim was
disproven the day it shipped. Manual truth passes fix drift once; only a gate
prevents recurrence.

## Decision

`tests/unit/test_docs.py` asserts machine-checkable doc claims against their
sources of truth: test counts versus collected test functions, hook commands
quoted verbatim in README/CONTRIBUTING/AGENTS and present in ci.yml, size
caps versus `test_standards` constants, the coverage floor versus pyproject
addopts, and the Python version versus `requires-python`. Anchored patterns
only: prose can be rephrased freely while numbers cannot silently rot.

## Consequences

Proven at introduction (PR #15): the gate failed on stale test counts in its
own PR and forced the fix in the same commit; it also forced the CI reports
change to use `PYTEST_ADDOPTS` env rather than editing the verbatim gate
line. Platform-side facts (rulesets, CodeQL state) stay outside the gate -
pytest cannot reach them; `docs/repo-settings.md` is hand-maintained instead.
