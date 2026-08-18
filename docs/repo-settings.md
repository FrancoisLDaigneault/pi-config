# Repository platform settings

Inventory of the GitHub settings that are NOT versioned as files in this
repository. If the repo ever has to be recreated, re-apply them with the
commands below.

> Maintained by hand. The documentation drift gate (`tests/unit/test_docs.py`)
> cannot verify this file: platform state is not reachable from pytest.
> Last verified: 2026-08-17.
>
> Machine-readable since 2026-08-18: `governance/baseline.json` captures these
> controls as desired state; `governance/audit.sh FrancoisLDaigneault/pi-config`
> verifies the live settings against it (see `governance/README.md`).

## Branch ruleset: main-protection (id 20945568)

Pull request required for every change to `main` (0 approving reviews -
single-maintainer repo, review happens in the orchestrated process);
force-push and branch deletion blocked; no bypass actors. Deliberately **no
required status checks**: release-please PRs created with `GITHUB_TOKEN`
carry no check runs (GitHub anti-recursion), so required checks would
deadlock every release PR (see ADR-0005). Check verification stays
procedural: watch PR checks before merge; post-merge CI on `main` is
authoritative. A `required_signatures` rule is **active** (since
2026-08-18): the signing key is registered on GitHub, so every PR branch
commit must carry a verified signature. Enabling it before key registration
blocks all worker PRs (empirically proven, see ADR-0010 and the
commit-signing section below).

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
`GITHUB_TOKEN` - since the draft flow it does so explicitly at draft-creation
time via `force-tag-creation`, see ADR-0009); no bypass actors. Empirically
verified at v0.4.3: creation succeeded under the ruleset and a tag-deletion
probe was rejected (GH013).

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

Immutability locks a release AT PUBLISH TIME. Releases are therefore created
as drafts (`"draft": true` in the release-please config), assets are uploaded
to the draft, and the workflow publishes it as the last step - GitHub's own
recommended flow for immutable releases (ADR-0009). Known permanent gap:
**v0.4.3 has no assets** - it was published (and locked) before this flow
existed and cannot be amended or deleted; its wheel/sdist stay reproducible
from the immutable tag (`uv build` at `v0.4.3`), and SBOM plus provenance
attestation resumed with the next release.

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

## Commit signing (ADR-0010)

Machine-side SSH commit signing is configured **repo-locally** in the
pi-config clone (not globally). Every local commit signs automatically; the
pre-commit hook runs unchanged. Key: `~/.ssh/id_ed25519_signing` (ed25519,
fingerprint `SHA256:p+fl2vQbPN4ltYMbDYIxdqBOiHLkxZqXZTNGt0cazHo`).

```bash
git config gpg.format ssh
git config user.signingkey ~/.ssh/id_ed25519_signing.pub
git config commit.gpgsign true
git config user.name "francois"
git config user.email "francois.ldaigneault@gmail.com"
git config gpg.ssh.allowedSignersFile ~/.ssh/allowed_signers
```

Commits on `main` are all GitHub-web-flow signed (squash merges and
release-please commits are created by GitHub); the 23 pre-ruleset direct
pushes predate signing and stay unverified - historical, not gated.

**Owner sequence — completed 2026-08-18.** The key is registered as a
Signing Key, previously pushed signed commits flipped retroactively to
`verified: true / valid`, and the `required_signatures` rule is re-enabled
on ruleset 20945568 (all four rules active). The steps below are kept for a
machine rebuild or key rotation.

Step 1 - register the signing key. Either:

```bash
gh auth refresh -h github.com -s admin:ssh_signing_key
gh ssh-key add ~/.ssh/id_ed25519_signing.pub --type signing \
  --title "pi-config commit signing"
```

or paste the content of `~/.ssh/id_ed25519_signing.pub` at
<https://github.com/settings/ssh/new> with key type **Signing Key**.

Step 2 - verify the retroactive flip (an already-pushed signed commit must
now show `verified: true`):

```bash
gh api repos/FrancoisLDaigneault/pi-config/commits/1e981bd \
  --jq '.commit.verification'
```

Step 3 - re-enable the `required_signatures` rule (gates every PR branch
commit from then on - do this only after step 2 succeeds):

```bash
gh api repos/FrancoisLDaigneault/pi-config/rulesets/20945568 -X PUT --input - <<'EOF'
{"name": "main-protection", "target": "branch", "enforcement": "active",
 "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
 "rules": [{"type": "pull_request", "parameters": {
    "required_approving_review_count": 0, "dismiss_stale_reviews_on_push": false,
    "require_code_owner_review": false, "require_last_push_approval": false,
    "required_review_thread_resolution": false}},
   {"type": "non_fast_forward"}, {"type": "deletion"},
   {"type": "required_signatures"}],
 "bypass_actors": []}
EOF
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
