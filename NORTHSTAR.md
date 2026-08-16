# NORTHSTAR — pi-config

KPIs de pilotage de ce depot (outil personnel de sauvegarde/restauration de la config Pi).
Un KPI par axe, mesurable, avec valeur actuelle reelle. Mis a jour quand une mesure change de categorie.

## Rapidite

| KPI | Actuel | Cible | Mesure |
| --- | --- | --- | --- |
| Restauration machine neuve | procedure 8 etapes documentee | < 30 min chrono | Suivre `README.md` § Restauration sur machine neuve |
| Duree de la suite de tests | 0.63 s (28 tests) | < 5 s | `uv run pytest -q` (gate CI) |

## Securite

| KPI | Actuel | Cible | Mesure |
| --- | --- | --- | --- |
| Secrets dans le repo | 0 (historique audite) | 0, toujours | Audit `sync.py` a chaque sync + job gitleaks en CI |
| `auth.json` suivi par git | jamais | jamais | Exclusion `sync.py` + `.gitignore` + test e2e |

## Maintenabilite

| KPI | Actuel | Cible | Mesure |
| --- | --- | --- | --- |
| Violations ruff (C901=8, PLR0915=30, PLR0913=5) | 0 | 0 | `uv run ruff check .` (hook pre-commit + CI) |
| Taille des modules src / scripts | max 142 / 8 lignes | <= 200 / <= 20 | `tests/unit/test_standards.py` (la limite est un test) |
| Tests verts | 28 (14 unit / 12 integration / 2 e2e) | 100 % verts, 3 niveaux | `uv run pytest` (hook + CI) |

## Durabilite (scalabilite pour cet outil)

| KPI | Actuel | Cible | Mesure |
| --- | --- | --- | --- |
| Parite sync -> restore machine neuve | prouvee (e2e, fichiers identiques) | reste prouvee a chaque commit | `tests/e2e/test_full_cycle.py` en CI |
| Fraicheur du snapshot `config/` | sync du 2026-08-16 | sync avant chaque update de Pi | Workflow `sync -> commit -> push` du README |

Un KPI toujours vert sans effort est a resserrer ; un KPI toujours rouge est a corriger ou a retirer.
