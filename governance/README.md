# Governance baseline as code

This directory turns the hand-maintained platform-settings inventory
(`docs/repo-settings.md`) into an executable desired-state baseline for
every repository owned by the account.

| File | Role |
| --- | --- |
| `baseline.json` | Machine-readable desired state: 10 controls, each with its read endpoint, a jq projection, the desired value and the corrective API call. Every desired value equals the verified live state of the reference repo (pi-config). |
| `bootstrap.sh` | Applies the baseline to one repository. Dry-run by default; `--apply` executes. Idempotent: re-running on a compliant repo changes nothing and exits 0. |
| `audit.sh` | Compliance matrix across repositories (`--all` = every non-archived repo you own). Exit 1 on any drift. |

## Usage

```bash
# See what a repo would need (no changes made):
governance/bootstrap.sh OWNER/REPO

# Apply the baseline to a repo:
governance/bootstrap.sh OWNER/REPO --apply

# Audit the whole fleet (or specific repos):
governance/audit.sh --all
governance/audit.sh OWNER/REPO1 OWNER/REPO2
```

Requirements: `gh` authenticated with the `repo` scope, Python 3 on PATH,
Git Bash or any bash. A fleet audit takes roughly 20-30 seconds per repo
(a dozen API calls each).

## Controls

`ruleset-main-protection`, `ruleset-release-tags`, `immutable-releases`,
`codeql-default-setup`, `dependabot-alerts`, `dependabot-security-updates`,
`secret-scanning`, `secret-scanning-push-protection`,
`private-vulnerability-reporting`, `actions-workflow-permissions`.

Public-only controls (rulesets, CodeQL, secret scanning, push protection,
private vulnerability reporting) are skipped with `NA` on private repos:
a free personal plan only gets them on public repositories. Machine-local
commit-signing configuration is out of scope (not a platform setting; see
the commit-signing section of `docs/repo-settings.md`).

Comparison is projection-based: only the fields the baseline governs are
compared (canonical JSON), so server-added defaults never produce false
drift. `bootstrap.sh` is additive/corrective only - it never disables
anything outside the baseline scope.

## Drift detection for pi-config itself

Running `governance/audit.sh FrancoisLDaigneault/pi-config` verifies that
the live platform settings still match `docs/repo-settings.md` (the baseline
was extracted from it). Run it after any settings change, or on a schedule.

## Scheduled audit (documented, not enabled)

A weekly GitHub Actions job could run `audit.sh --all` and fail on drift.
It is NOT enabled because the workflow `GITHUB_TOKEN` is scoped to its own
repository and cannot read sibling repos. Enabling it requires an owner
action: create a fine-grained PAT (read-only: Administration, Code scanning,
Secret scanning, Dependabot alerts on the governed repos), store it as a
repository secret (for example `GOVERNANCE_AUDIT_TOKEN`), and add a small
scheduled workflow that checks out this repo and runs the audit with
`GH_TOKEN=${{ secrets.GOVERNANCE_AUDIT_TOKEN }}`. Prefer a GitHub App
installation for durable automation.

## Org-migration note

This baseline is Step 1 of the multi-repo enforcement path. On a personal
account it is a continuously *audited* desired state, not platform-enforced:
repository settings can still drift between audits. Under a GitHub Team
organization, the same content becomes actual enforcement objects:
organization rulesets targeting all repos (the two ruleset controls),
a default/enforced security configuration (the security controls), and an
organization Actions policy (the workflow-permissions control). At migration
time, `audit.sh --all` is the acceptance test that the org objects reproduce
this baseline.

## Permanent test bed

`governance-canary` (public scratch repo under the owner) exists to exercise
bootstrap/audit changes end to end without touching real repos. Keep it, or
delete it and recreate it with `gh repo create governance-canary --public
--add-readme` (plus one committed Python file so CodeQL default setup has a
supported language) next time a live proof is needed.
