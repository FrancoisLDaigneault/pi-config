# ADR-0003: config/ is a byte-faithful snapshot, excluded from style gates

- Status: accepted
- Date: 2026-08-17

## Context

`config/` is not project code: it is the mirror of the live Pi configuration
produced by `sync.py` and replayed by `restore.py`. Its only required quality
is byte fidelity to the live machine. Style-fixing a mirror desyncs it from
reality, and the next sync reverts the fix - an infinite loop.

## Decision

Exclude `config/` from the style, type and language gates by configuration:
`extend-exclude` under `[tool.ruff]`, the `[tool.mypy]` files list, pytest
`testpaths`, and the language-gate file list. Security gates still apply in
full: gitleaks scans the complete history including `config/`, and `sync.py`
redacts secrets before any file enters the repo.

## Consequences

The workshop (src, scripts, tests - judged by every gate) and the showcase
(`config/` - judged on fidelity only) are now separated in configuration, not
just by convention. Empirical vindication: before the explicit ruff
exclusion, `ruff format` was silently scanning 11 scaffold-template files
inside `config/` (caught during PR #15); the exclusion turned an accidental
truth into a configured one.
