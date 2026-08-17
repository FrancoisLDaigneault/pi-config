# ADR-0010: Signed commits on main with repo-local SSH signing

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

## Decision

- Add the `required_signatures` rule to the `main-protection` ruleset
  (id 20945568), alongside the existing pull_request / non_fast_forward /
  deletion rules, no bypass actors.
- Configure repo-local SSH commit signing in the working clone (ed25519 key,
  `gpg.format ssh`, `commit.gpgsign true`, identity set repo-locally - this
  also ends the per-command identity dance workers used before). Local
  verification via `gpg.ssh.allowedSignersFile` reports a good signature.
- Rely on GitHub web-flow signing for everything that lands on `main`
  (squash merges, release-please release commits).

## Consequences

- `main` only accepts verified-signed commits; the PR-only flow satisfies the
  rule by construction. The first squash merge under the active rule (this
  ADR's own PR) is the empirical proof.
- Rebase merges would land author-signed commits (GitHub does not re-sign
  them); unsigned ones would be rejected. The established procedure is
  squash-only, so this is a non-issue - but do not switch to rebase merges.
- Branch/worker commits sign locally, but show as Unverified on GitHub until
  the owner registers the public key as a **signing key** (requires the
  `admin:ssh_signing_key` scope - interactive auth the automation cannot
  perform; exact commands in `docs/repo-settings.md`). Cosmetic: branch
  commits are squashed away and never reach `main`.
- External contributors without signing setup are unaffected: they cannot
  push to `main` directly (pull_request rule), and their PRs land through
  GitHub-signed squash commits.
