# NORTHSTAR - pi-config

Steering KPIs for this repository (personal backup/restore tool for the Pi configuration).
One KPI per axis, measurable, with a real current value. Updated whenever a measurement changes category.

## Speed

| KPI | Current | Target | Measurement |
| --- | --- | --- | --- |
| Fresh-machine restore | 8-step documented procedure | < 30 min wall clock | Follow `README.md` "Restoring on a fresh machine" |
| Test suite duration | 0.8 s (29 tests) | < 5 s | `uv run pytest -q` (CI gate) |

## Security

| KPI | Current | Target | Measurement |
| --- | --- | --- | --- |
| Secrets in the repo | 0 (history audited) | 0, always | `sync.py` audit at each sync + gitleaks job in CI |
| `auth.json` tracked by git | never | never | `sync.py` exclusion + `.gitignore` + e2e test |

## Maintainability

| KPI | Current | Target | Measurement |
| --- | --- | --- | --- |
| Ruff violations (C901=8, PLR0915=30, PLR0913=5) | 0 | 0 | `uv run ruff check .` (pre-commit hook + CI) |
| src module / script size | max 142 / 8 lines | <= 200 / <= 20 | `tests/unit/test_standards.py` (the limit is a test) |
| Green tests | 29 (15 unit / 12 integration / 2 e2e) | 100% green, 3 levels | `uv run pytest` (hook + CI) |

## Scalability

(For this tool, scalability means the sync/restore workflow keeps holding as the config grows.)

| KPI | Current | Target | Measurement |
| --- | --- | --- | --- |
| sync -> restore fresh-machine parity | proven (e2e, identical files) | stays proven at every commit | `tests/e2e/test_full_cycle.py` in CI |
| `config/` snapshot freshness | synced on 2026-08-16 | sync before every Pi update | README `sync -> commit -> push` workflow |

A KPI that is always green effortlessly should be tightened; a KPI that is always red should be fixed or dropped.
