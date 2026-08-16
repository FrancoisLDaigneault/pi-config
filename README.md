# pi-config

Dépôt officiel de la configuration Pi (persona Maestro, extensions, prompts, skills, settings). Objectif : ne jamais perdre la configuration, même après un update de Pi ou une réinstallation de la machine.

## Prérequis

- [uv](https://docs.astral.sh/uv/) installé
- Python 3.12+ (uv le télécharge automatiquement si absent, via `.python-version`)

## Setup

```bash
cd pi-config
uv venv          # cree .venv/ dans le repo avec Python 3.12+
```

## Les trois scripts

Tous en Python stdlib pur (aucune dépendance), lancés avec `uv run` :

| Script | Rôle |
| --- | --- |
| `uv run scripts/sync.py` | Copie la config **vive** (`~/.pi/agent`, `~/.agents/skills`, patch context-mode) vers `config/` dans le repo. À lancer avant chaque commit. |
| `uv run scripts/restore.py` | Chemin inverse : `config/` → emplacements vifs. **Simulation par défaut** ; ajouter `--apply` pour exécuter. Ne touche jamais `auth.json`. |
| `uv run scripts/backup.py` | Sauvegarde complète **locale** (config + patch + MemPalace + skills) dans un dossier horodaté sous `~/pi-backups/`. Option `--destination`. Code de sortie 1 si une section échoue. |

## Workflow recommandé avant chaque update de Pi

```bash
uv run scripts/backup.py     # filet de securite local complet (fermer Pi d'abord pour MemPalace)
uv run scripts/sync.py       # met a jour config/ dans le repo
git add -A
git commit -m "chore: sync Pi config before update"
git push
```

Après un `npm update` de context-mode : le fichier patché `config/patched-node_modules/context-mode/build/adapters/pi/extension.js` est écrasé côté vif — le restaurer avec `uv run scripts/restore.py --apply` (voir `config/patched-node_modules/README.md`).

## ⚠️ Ce qui n'est PAS dans le repo

- **`auth.json`** — identifiants et secrets. Jamais versionné (exclu par `sync.py` **et** par `.gitignore`).
- **Données MemPalace** (`~/.mempalace`) — mémoire personnelle de l'agent, volumineuse et privée.

Ces deux éléments sont couverts par `backup.py` **en local uniquement**. Ne jamais uploader un dossier `pi-backups/` en clair.

## Secrets caviardés

`sync.py` audite chaque JSON de config avant inclusion (clés `apiKey`, `token`, `secret`, etc. et valeurs `sk-…`, `ghp_…`, `Bearer …`). Toute valeur suspecte est remplacée par `<REDACTED>` et signalée en sortie. Pour restaurer un fichier caviardé : récupérer la vraie valeur depuis la machine source (ou le backup local) et la remettre à la main après `restore.py --apply`.
