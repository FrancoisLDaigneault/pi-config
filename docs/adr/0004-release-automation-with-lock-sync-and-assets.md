# ADR-0004: Release automation with lock sync and signed assets

- Status: accepted
- Date: 2026-08-17

## Context

Releases must be reproducible and boring. `uv.lock` records the project
version and drifted after every release: release-please bumped
`pyproject.toml` but not the lock, costing a manual restore on every
subsequent run.

## Decision

release-please runs in manifest mode with its config under
`.github/release-please/` (relocated in PR #15). `uv.lock` is kept in sync by
a `toml` extra-files updater whose jsonpath uses the `.value` hop (an
internal of release-please's tagged TOML parser). A `release-assets` job,
gated on `release_created`, uploads wheel, sdist, SPDX SBOM (from the GitHub
dependency graph), SHA-256 checksums and a SLSA build-provenance attestation.
Guard: `uv sync --locked` in CI turns any silent updater failure into a loud
CI failure.

## Consequences

Lock bump proven live in four consecutive releases (v0.3.1 to v0.4.2); assets
verified end-to-end on v0.4.0 (`gh attestation verify` exit 0). Empirical
release semantics: `feat` = minor, `fix` and `docs` = patch (docs proven by
PR #14 / v0.4.1), `ci`/`chore`/`refactor`/`test` do not release by
themselves; the squash-merge subject decides the commit type. Re-verify the
jsonpath on any release-please-action major bump.
