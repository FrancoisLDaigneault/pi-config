#!/usr/bin/env bash
# Apply the governance baseline (governance/baseline.json) to one repository.
#
# Usage: governance/bootstrap.sh OWNER/REPO [--apply]
#
# Dry-run by default: prints one status line per control (OK / DRIFT / NA)
# plus the desired-vs-live diff for every drift, and exits 1 if any control
# drifts. With --apply, corrective API calls are executed and each control is
# re-checked afterwards (APPLIED / FAIL). Re-running on a compliant repo makes
# zero changes and exits 0 (idempotent). The script is additive/corrective
# only: it never disables anything outside the baseline scope.
#
# Requirements: gh (authenticated, repo scope), python 3 on PATH.
# Machine-readable output: lines starting with "CTL " (used by audit.sh).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASELINE="$SCRIPT_DIR/baseline.json"

REPO="${1:-}"
[[ -z "$REPO" || "$REPO" == --* ]] && {
  echo "usage: $0 OWNER/REPO [--apply]" >&2
  exit 2
}
APPLY=false
[[ "${2:-}" == "--apply" ]] && APPLY=true

# Canonical JSON (sorted keys, compact) so projections compare as strings.
# tr strips the CR that Python text-mode stdout emits on Windows.
canon() {
  python -c 'import json,sys
raw = sys.stdin.read().strip()
print(json.dumps(json.loads(raw) if raw else None, sort_keys=True, separators=(",", ":")))' \
    | tr -d '\r'
}

# Print the manifest of one control, one field per line (fields never contain
# newlines: projections are single-line jq filters, payloads compact JSON).
manifest() {
  CID="$1" python -c '
import json, os, sys
cid = os.environ["CID"]
with open(sys.argv[1], encoding="utf-8") as fh:
    controls = json.load(fh)["controls"]
c = next(c for c in controls if c["id"] == cid)
dump = lambda v: json.dumps(v, sort_keys=True, separators=(",", ":"))
print(c["kind"])
print(c["applicability"])
print(c.get("read_endpoint", "-"))
print(c.get("projection", "-"))
print(c.get("ruleset_name", "-"))
print(c["apply_method"])
print(c["apply_endpoint"])
print(dump(c["apply_payload"]) if "apply_payload" in c else "-")
print(dump(c["desired"]))
' "$BASELINE" | tr -d '\r'
}

control_ids() {
  python -c '
import json, sys
with open(sys.argv[1], encoding="utf-8") as fh:
    print("\n".join(c["id"] for c in json.load(fh)["controls"]))
' "$BASELINE" | tr -d '\r'
}

# Read the live projected state of a control. Sets LIVE (canonical JSON) and,
# for rulesets, RULESET_ID (empty when the ruleset does not exist yet).
read_live() {
  RULESET_ID=""
  case "$KIND" in
    ruleset)
      RULESET_ID=$(gh api "${READ_EP/\{repo\}/$REPO}" \
        --jq "[.[] | select(.name==\"$RS_NAME\")][0].id // empty")
      if [[ -z "$RULESET_ID" ]]; then
        LIVE='"absent"'
      else
        LIVE=$(gh api "repos/$REPO/rulesets/$RULESET_ID" --jq "$PROJECTION" | canon)
      fi
      ;;
    status204)
      if gh api "${READ_EP/\{repo\}/$REPO}" >/dev/null 2>&1; then
        LIVE='{"enabled":true}'
      else
        LIVE='{"enabled":false}'
      fi
      ;;
    json)
      if ! LIVE=$(gh api "${READ_EP/\{repo\}/$REPO}" --jq "$PROJECTION" 2>&1); then
        LIVE="\"read-error: $(echo "$LIVE" | head -1)\""
        return 0
      fi
      LIVE=$(printf '%s' "$LIVE" | canon)
      ;;
  esac
}

# Run the corrective call for a control (assumes read_live ran before).
apply_control() {
  local method="$METHOD" endpoint="${APPLY_EP/\{repo\}/$REPO}"
  if [[ "$KIND" == "ruleset" && -n "$RULESET_ID" ]]; then
    method="PUT"
    endpoint="repos/$REPO/rulesets/$RULESET_ID"
  fi
  if [[ "$PAYLOAD" == "-" ]]; then
    gh api -X "$method" "$endpoint" >/dev/null
  else
    printf '%s' "$PAYLOAD" | gh api -X "$method" "$endpoint" --input - >/dev/null
  fi
}

VISIBILITY=$(gh repo view "$REPO" --json visibility --jq '.visibility | ascii_downcase')
IS_ARCHIVED=$(gh repo view "$REPO" --json isArchived --jq '.isArchived')
if [[ "$IS_ARCHIVED" == "true" ]]; then
  echo "WARN: $REPO is archived (read-only) - nothing to do"
  exit 0
fi

MODE="dry-run"
$APPLY && MODE="apply"
echo "== governance bootstrap: $REPO (visibility: $VISIBILITY, mode: $MODE) =="

DRIFT_COUNT=0
FAIL_COUNT=0
for CID in $(control_ids); do
  {
    read -r KIND
    read -r APPLICABILITY
    read -r READ_EP
    read -r PROJECTION
    read -r RS_NAME
    read -r METHOD
    read -r APPLY_EP
    read -r PAYLOAD
    read -r DESIRED
  } < <(manifest "$CID")

  if [[ "$APPLICABILITY" == "public" && "$VISIBILITY" != "public" ]]; then
    echo "CTL $CID NA"
    echo "     skipped: public-only control on a $VISIBILITY repo (needs a paid plan)"
    continue
  fi

  read_live
  if [[ "$LIVE" == "$DESIRED" ]]; then
    echo "CTL $CID OK"
    continue
  fi

  if ! $APPLY; then
    echo "CTL $CID DRIFT"
    echo "     desired: $DESIRED"
    echo "     live:    $LIVE"
    DRIFT_COUNT=$((DRIFT_COUNT + 1))
    continue
  fi

  if ERR=$(apply_control 2>&1); then
    read_live
    if [[ "$LIVE" == "$DESIRED" ]]; then
      echo "CTL $CID APPLIED"
    else
      echo "CTL $CID FAIL"
      echo "     applied but live state still differs"
      echo "     desired: $DESIRED"
      echo "     live:    $LIVE"
      FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
  else
    echo "CTL $CID FAIL"
    echo "     apply error: $(echo "$ERR" | head -2 | tr '\n' ' ')"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
done

if $APPLY; then
  echo "== done: $FAIL_COUNT failure(s) =="
  [[ "$FAIL_COUNT" -eq 0 ]] || exit 1
else
  echo "== done: $DRIFT_COUNT drift(s) =="
  [[ "$DRIFT_COUNT" -eq 0 ]] || exit 1
fi
