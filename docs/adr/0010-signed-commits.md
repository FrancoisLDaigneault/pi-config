# ADR-0010: Signed commits - repo-local SSH signing, rule deferred to key registration

- Status: accepted
- Date: 2026-08-17

## Context

Release artifacts carry cryptographically verified SLSA provenance
attestations (ADR-0004), but nothing authenticated the commits that produce
them - anyone holding a token could commit "as" the maintainer. Closing that
asymmetry is the last unauthenticated link in the supply chain.

Verified before implementing (GitHub commits API, `verification` field): every
`main` commit since the PR-only flow began is `verified: true` with reason
`valid` - squash-merge and release-please commits are created by GitHub
itself and signed with its web-flow key. The 23 older unverified commits are
pre-ruleset direct pushes: historical, and not gated by ruleset rules (which
apply to new pushes only). Requiring signatures on `main` therefore costs
nothing in the established flow.

## Empirical discovery (the load-bearing fact)

The `required_signatures` ruleset rule gates **every commit on the PR
branch**, not just the squash commit that lands on `main`. Proven live: with
the rule active, this ADR's own PR (#23) - whose single branch commit was
signed locally but `verified: false` / `reason: unknown_key` on GitHub
(signing key not yet registered) - reported `mergeStateStatus: BLOCKED` and
gh refused the squash merge ("To have the pull request merged after all the
requirements have been met, add the --auto flag."). Removing the rule
flipped the same PR to `CLEAN` with no other change. Verification is
retroactive: registering the key flips existing `unknown_key` commits to
`verified: true` (the signature is present; only the key is unknown).

## Decision

- Configure repo-local SSH commit signing in the working clone (ed25519 key,
  `gpg.format ssh`, `commit.gpgsign true`, identity set repo-locally - this
  also ends the per-command identity dance workers used before). Local
  verification via `gpg.ssh.allowedSignersFile` reports a good signature.
- **Defer** the `required_signatures` rule on `main-protection`: enabling it
  before the signing key is registered blocks every worker PR (empirically
  proven above) while the registration needs interactive auth
  (`admin:ssh_signing_key` scope) that automation cannot perform.
- Correct enablement order, documented as a copy-paste sequence in
  `docs/repo-settings.md`: (1) register the signing key, (2) verify a branch
  commit flips to `verified: true`, (3) re-enable the rule.

## Consequences

- Until the rule is re-enabled, `main` integrity rests on what is already
  proven: the PR-only flow (no direct pushes) and the fact that every `main`
  commit since that flow began is GitHub-web-flow signed (22/22 verified).
- Worker commits sign automatically from now on; they show Unverified on
  GitHub only until the key registration (cosmetic in the interval, and
  retroactively fixed by it).
- Once the rule is re-enabled: release-please PRs stay unaffected (bot
  commits are web-flow signed); any PR from a machine without a registered
  signing key will be blocked at merge - by design at that point.
- Rebase merges would land author-signed commits (GitHub does not re-sign
  them); the established procedure is squash-only - do not switch to rebase
  merges.
