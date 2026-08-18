#!/usr/bin/env bash
# Governance drift audit: compare repositories against governance/baseline.json.
#
# Usage: governance/audit.sh [--all | OWNER/REPO ...]
#
# --all enumerates every non-archived repository owned by the authenticated
# user. Each repository is checked with bootstrap.sh in dry-run mode; the
# result is a per-repo / per-control compliance matrix (OK / DRIFT / NA).
# Exit 1 when any control drifts anywhere - this is the drift detector that
# closes the hand-maintained docs/repo-settings.md gap when run regularly.
#
# Requirements: gh (authenticated, repo scope), python 3 on PATH.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

REPOS=()
if [[ "${1:-}" == "--all" ]]; then
  OWNER=$(gh api user --jq .login)
  while IFS= read -r repo; do
    REPOS+=("$repo")
  done < <(gh repo list "$OWNER" --limit 200 \
    --json nameWithOwner,isArchived \
    --jq '.[] | select(.isArchived | not) | .nameWithOwner' | sort)
elif [[ $# -ge 1 ]]; then
  REPOS=("$@")
else
  echo "usage: $0 [--all | OWNER/REPO ...]" >&2
  exit 2
fi

RESULTS=""
for repo in "${REPOS[@]}"; do
  echo "auditing $repo ..." >&2
  OUTPUT=$("$SCRIPT_DIR/bootstrap.sh" "$repo" 2>&1) || true
  while IFS= read -r line; do
    [[ "$line" == CTL\ * ]] && RESULTS+="$repo ${line#CTL }"$'\n'
  done <<< "$OUTPUT"
done

printf '%s' "$RESULTS" | python -c '
import sys

rows: dict[str, dict[str, str]] = {}
controls: list[str] = []
for line in sys.stdin:
    parts = line.split()
    if len(parts) != 3:
        continue
    repo, control, status = parts
    rows.setdefault(repo, {})[control] = status
    if control not in controls:
        controls.append(control)

if not rows:
    print("no results collected")
    sys.exit(2)

codes = {c: f"C{i + 1}" for i, c in enumerate(controls)}
mark = {"OK": "OK", "DRIFT": "DRIFT", "NA": "-"}
repo_w = max(len(r) for r in rows)
col_w = max(5, *(len(codes[c]) for c in controls))

print("legend: " + ", ".join(f"{codes[c]}={c}" for c in controls))
print("cells: OK = compliant, DRIFT = differs from baseline, - = not applicable")
print()
header = "repo".ljust(repo_w) + "  " + "  ".join(codes[c].ljust(col_w) for c in controls)
print(header)
print("-" * len(header))
drift = 0
for repo in sorted(rows):
    cells = []
    for c in controls:
        status = rows[repo].get(c, "?")
        drift += status == "DRIFT"
        cells.append(mark.get(status, status).ljust(col_w))
    print(repo.ljust(repo_w) + "  " + "  ".join(cells))
print()
print(f"total drift cells: {drift}")
sys.exit(1 if drift else 0)
'
