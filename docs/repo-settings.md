# Repository platform settings

Inventory of the GitHub settings that are NOT versioned as files in this
repository. If the repo ever has to be recreated, re-apply them with the
commands below.

> Maintained by hand. The documentation drift gate (`tests/unit/test_docs.py`)
> cannot verify this file: platform state is not reachable from pytest.
> Last verified: 2026-08-17.

## Branch ruleset: main-protection (id 20945568)

Pull request required for every change to `main` (0 approving reviews -
single-maintainer repo, review happens in the orchestrated process);
force-push and branch deletion blocked; no bypass actors. Deliberately **no
required status checks**: release-please PRs created with `GITHUB_TOKEN`
carry no check runs (GitHub anti-recursion), so required checks would
deadlock every release PR (see ADR-0005). Check verification stays
procedural: watch PR checks before merge; post-merge CI on `main` is
authoritative.

```bash
gh api repos/FrancoisLDaigneault/pi-config/rulesets -X POST --input - <<'EOF'
{"name": "main-protection", "target": "branch", "enforcement": "active",
 "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
 "rules": [{"type": "pull_request", "parameters": {
    "required_approving_review_count": 0, "dismiss_stale_reviews_on_push": false,
    "require_code_owner_review": false, "require_last_push_approval": false,
    "required_review_thread_resolution": false}},
   {"type": "non_fast_forward"}, {"type": "deletion"}],
 "bypass_actors": []}
EOF
```

## Tag ruleset: release-tags (id 20957165)

Applies to `refs/tags/v*`: tag deletion, update and force-update blocked; tag
**creation stays allowed** (release-please creates the release tags with
`GITHUB_TOKEN`); no bypass actors. Residual risk tracked: verify at the next
release that tag creation still succeeds.

```bash
gh api repos/FrancoisLDaigneault/pi-config/rulesets -X POST --input - <<'EOF'
{"name": "release-tags", "target": "tag", "enforcement": "active",
 "conditions": {"ref_name": {"include": ["refs/tags/v*"], "exclude": []}},
 "rules": [{"type": "deletion"}, {"type": "update"}, {"type": "non_fast_forward"}],
 "bypass_actors": []}
EOF
```

## Immutable releases

Enabled (`{"enabled": true}`): published releases and their assets can no
longer be modified or deleted, closing the trust chain that checksums and
provenance attestations point at.

```bash
gh api repos/FrancoisLDaigneault/pi-config/immutable-releases -X PUT
```

## CodeQL code scanning (default setup)

State `configured`, query suite `default`, schedule `weekly`; languages
detected: actions, javascript-typescript, python. Config is GitHub-managed
(no workflow file in the repo).

```bash
gh api repos/FrancoisLDaigneault/pi-config/code-scanning/default-setup \
  -X PATCH -f state=configured
```

## Dependabot

Alerts enabled (endpoint returns 204) and security updates enabled. Version
updates are configured in-repo via `.github/dependabot.yml` (weekly,
github-actions + uv ecosystems).

```bash
gh api repos/FrancoisLDaigneault/pi-config/vulnerability-alerts -X PUT
gh api repos/FrancoisLDaigneault/pi-config/automated-security-fixes -X PUT
```

## Secret scanning and push protection

Both enabled (non-provider patterns and validity checks stay off).

```bash
gh api repos/FrancoisLDaigneault/pi-config -X PATCH \
  -f 'security_and_analysis[secret_scanning][status]=enabled' \
  -f 'security_and_analysis[secret_scanning_push_protection][status]=enabled'
```

## Private vulnerability reporting

Enabled (`{"enabled": true}`) - the reporting path documented in SECURITY.md.

```bash
gh api repos/FrancoisLDaigneault/pi-config/private-vulnerability-reporting -X PUT
```

## Actions workflow permissions

Default workflow permissions `read`; `can_approve_pull_request_reviews` is
`true` - required so release-please (running with `GITHUB_TOKEN`) may create
its release PRs. Do not flip it back to `false`: that reintroduces the
"GitHub Actions is not permitted to create or approve pull requests" failure.

```bash
gh api repos/FrancoisLDaigneault/pi-config/actions/permissions/workflow \
  -X PUT -f default_workflow_permissions=read \
  -F can_approve_pull_request_reviews=true
```
