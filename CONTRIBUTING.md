# Contribuer

## Mise en place

```bash
uv sync                           # crée .venv/ et installe le package + outils dev
git config core.hooksPath hooks   # active le hook pre-commit versionné
```

## Portes de qualité

Avant toute PR, les deux commandes doivent passer sans erreur (le hook
pre-commit et la CI les exécutent aussi) :

```bash
uv run ruff check .
uv run pytest -q
```

## Standards appliqués par l'outillage

- Complexité cyclomatique (McCabe) ≤ 8
- ≤ 30 instructions par fonction, ≤ 5 arguments
- Lignes ≤ 100 caractères
- ≤ 200 lignes par module, ≤ 20 par script — vérifié par `tests/unit/test_standards.py`

## Messages de commit

Les [Conventional Commits](https://www.conventionalcommits.org/fr/v1.0.0/)
sont obligatoires (`feat:`, `fix:`, `ci:`, `docs:`, `chore:`…) :
release-please s'en sert pour générer les versions et le CHANGELOG.
