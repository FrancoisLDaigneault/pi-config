# ADR-0005: Branch protection without required status checks

- Status: accepted
- Date: 2026-08-17

## Context

`main` must only change through pull requests. But release-please PRs created
with `GITHUB_TOKEN` carry no check runs (GitHub anti-recursion: workflows do
not trigger on events caused by the default token), so requiring status
checks in the ruleset would deadlock every release PR forever.

## Decision

Ruleset `main-protection`: pull request required (0 approving reviews -
single-maintainer repo, review happens in the orchestrated agent process
before merge), force-push and branch deletion blocked, no bypass actors -
and deliberately NO required status checks.

## Consequences

Check verification is procedural: PR checks are watched before every merge,
and post-merge CI on `main` is authoritative. The trade-off and the re-apply
command live in `docs/repo-settings.md`. Empirically verified: a direct push
to `main` is rejected by the ruleset (GH013). Revisit if GitHub ever lets
required checks exempt release-please PRs cleanly.
