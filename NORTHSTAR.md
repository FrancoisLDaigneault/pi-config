# NORTHSTAR - pi-config

Steering KPIs for this repository (personal backup/restore tool for the Pi configuration).
One North Star KPI per axis, plus supporting indicators. Every value is measured;
an unmeasured value is written as unmeasured, never invented. Updated whenever a
measurement changes category.

## Speed

North Star KPI:

| KPI | Current | Target | Measurement |
| --- | --- | --- | --- |
| Fresh-machine restore time | not yet measured | < 30 min wall clock | Time the `README.md` "Restoring on a fresh machine" procedure end to end |

Supporting indicators:

| Indicator | Current | Target | Measurement |
| --- | --- | --- | --- |
| Test suite duration | 2.8 s (53 tests) | < 5 s | `uv run pytest -q` (CI gate) |

Measurement cadence: CI runs on every push/PR to `main` and every Monday at
06:00 UTC - the weekly run catches bit-rot without anyone pushing.

## Security

North Star KPI:

| KPI | Current | Target | Measurement |
| --- | --- | --- | --- |
| Secrets in the repo | 0 (history audited) | 0, always | `sync.py` audit at each sync + gitleaks job in CI |

Supporting indicators:

| Indicator | Current | Target | Measurement |
| --- | --- | --- | --- |
| `auth.json` tracked by git | never | never | `sync.py` exclusion + `.gitignore` + e2e test |
| Release integrity (SBOM + provenance attestation) | v0.4.0 verified with `gh attestation verify` | every release verified | release assets + attestation check (see `SECURITY.md`) |
| Semgrep CE findings | 0 at adoption | 0 blocking | `uvx semgrep==1.173.0 scan --config p/python --metrics=off --error src scripts` in CI |
| Open vulnerability alerts / time-to-patch | baseline not yet recorded | record baseline, then 0 critical open | GitHub Security tab (CodeQL, `uv audit --locked`, Dependabot, secret scanning) |

## Maintainability

North Star KPI:

| KPI | Current | Target | Measurement |
| --- | --- | --- | --- |
| Branch coverage | 94.05% | >= 90% (enforced floor) | every full `uv run pytest` run (pre-commit framework + CI + `just check`) |

Supporting indicators:

| Indicator | Current | Target | Measurement |
| --- | --- | --- | --- |
| Ruff violations (C901=8, PLR0915=30, PLR0913=5) | 0 | 0 | `uv run ruff check .` (pre-commit framework + CI) |
| src module / script size | max 140 / 8 lines | <= 200 / <= 20 | `tests/unit/test_standards.py` (the limit is a test) |
| Green tests | 53 (32 unit / 19 integration / 2 e2e) | 100% green, 3 levels | `uv run pytest` (pre-commit framework + CI) |

## Scalability

(For this tool, scalability means the sync/restore workflow keeps holding as the config grows.)

North Star KPI:

| KPI | Current | Target | Measurement |
| --- | --- | --- | --- |
| sync -> restore fresh-machine parity | proven (e2e, identical files) | stays proven at every commit | `tests/e2e/test_full_cycle.py` in CI |

Supporting indicators:

| Indicator | Current | Target | Measurement |
| --- | --- | --- | --- |
| `config/` snapshot freshness | synced on 2026-08-18 | sync before every Pi update | README sync -> PR workflow |

A KPI that is always green effortlessly should be tightened; a KPI that is always red should be fixed or dropped.
