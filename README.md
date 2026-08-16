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
| `uv run scripts/restore.py` | Chemin inverse : `config/` → emplacements vifs. **Simulation par défaut** ; ajouter `--apply` pour exécuter. Ne touche jamais `auth.json`. Le patch context-mode n'est restauré qu'avec `--patch` (voir plus bas). Additif : ne supprime jamais les fichiers vifs obsolètes. |
| `uv run scripts/backup.py` | Sauvegarde complète **locale** (config + patch + MemPalace + skills) dans un dossier horodaté sous `~/pi-backups/`. Option `--destination`. Code de sortie 1 si une section échoue. |

## Workflow recommandé avant chaque update de Pi

```bash
uv run scripts/backup.py     # filet de securite local complet (fermer Pi d'abord pour MemPalace)
uv run scripts/sync.py       # met a jour config/ dans le repo
git add -A
git commit -m "chore: sync Pi config before update"
git push
```

Après un `npm update` de context-mode : le fichier patché `config/patched-node_modules/context-mode/build/adapters/pi/extension.js` est écrasé côté vif — le restaurer avec `uv run scripts/restore.py --apply --patch` (voir `config/patched-node_modules/README.md`).

Si `sync.py` échoue en cours de route (JSON illisible, permission refusée), `config/` peut rester partiel : le récupérer avec `git restore config/`.

## Restauration sur machine neuve

L'ordre compte : le patch context-mode doit être recopié **après** l'installation npm, sinon l'installation l'écrase (c'est pour ça que `restore.py` ne le restaure qu'avec le flag explicite `--patch`).

1. **Installer Pi** (et `uv`) sur la nouvelle machine.
2. **Cloner ce repo** : `git clone <url> pi-config && cd pi-config && uv venv`.
3. **Restaurer la config Pi** (sans le patch) : `uv run scripts/restore.py` pour vérifier en simulation, puis `uv run scripts/restore.py --apply`. Cela remet en place `~/.pi/agent` (persona, extensions, prompts, skills, settings, `npm/package.json` + `package-lock.json`) et `~/.agents/skills`.
4. **Réinstaller les packages npm de Pi** : `cd ~/.pi/agent/npm && npm ci` (le lockfile restauré à l'étape 3 garantit les versions exactes).
5. **Réappliquer le patch context-mode** — maintenant que `node_modules` existe : `uv run scripts/restore.py --apply --patch` (depuis le repo).
6. **Restaurer `auth.json`** depuis un backup local `backup.py` (jamais dans le repo) : le copier à la main vers `~/.pi/agent/auth.json`.
7. **Restaurer `~/.mempalace`** depuis le même backup local, si souhaité (mémoire de l'agent).
8. Lancer Pi et vérifier que persona, extensions et skills sont bien chargés.

## ⚠️ Ce qui n'est PAS dans le repo

- **`auth.json`** — identifiants et secrets. Jamais versionné (exclu par `sync.py` **et** par `.gitignore`).
- **Données MemPalace** (`~/.mempalace`) — mémoire personnelle de l'agent, volumineuse et privée.

Ces deux éléments sont couverts par `backup.py` **en local uniquement**. Ne jamais uploader un dossier `pi-backups/` en clair.

## Secrets caviardés

`sync.py` audite chaque JSON de config avant inclusion (clés `apiKey`, `token`, `secret`, etc. et valeurs `sk-…`, `ghp_…`, `Bearer …`). Toute valeur suspecte est remplacée par `<REDACTED>` et signalée en sortie. Pour restaurer un fichier caviardé : récupérer la vraie valeur depuis la machine source (ou le backup local) et la remettre à la main après `restore.py --apply`.
