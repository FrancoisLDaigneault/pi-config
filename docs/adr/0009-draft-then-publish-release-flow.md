# ADR-0009: Draft-then-publish release flow

- Status: accepted
- Date: 2026-08-17

## Context

Immutable releases (enabled in this repo, see `docs/repo-settings.md`) lock a
release and its tag at publish time. Our `release-assets` job uploaded assets
AFTER release-please published the release - so v0.4.3 failed with the
verbatim error `HTTP 422: Cannot upload assets to an immutable release.` and
is permanently assetless (immutability survives even disabling the setting).
GitHub's own guidance recommends the opposite order: "Create the release as a
draft. Attach all associated assets to the draft release. Publish the draft
release." (docs.github.com, immutable releases, Best practices section).

Verified before implementing (sources):

- release-please supports `"draft": true` in the manifest config, root-level
  or per-package (`schemas/config.json`: ReleaserConfigOptions.draft "Create
  the GitHub release in draft mode"; `docs/manifest-releaser.md`;
  `src/manifest.ts` v17.11.1: `pathConfig.draft ?? defaultConfig.draft`).
- The action outputs `release_created`, `tag_name`, `id` and `upload_url`
  fire for draft releases too: `outputReleases` in release-please-action
  `src/index.ts` (pinned commit 45996ed1) emits them for every release
  returned by `manifest.createReleases()`, with no draft filtering.
- GitHub does not create the Git tag for a draft release until publish
  ("lazy tag creation", release-please `docs/manifest-releaser.md`), which
  can make later release-please runs miss the previous release and corrupt
  changelogs if a draft gets stuck. Remedy documented there:
  `"force-tag-creation": true` makes release-please create the tag ref
  itself at draft-creation time (`git.createRef` in `src/github-api.ts`);
  the key is present in the dist bundled at our pinned action commit.
- `gh release upload` and `gh release edit` address drafts by their pending
  tag name: both call `shared.FetchRelease` (cli/cli
  `pkg/cmd/release/shared/fetch.go`), which falls back to a GraphQL draft
  lookup when `releases/tags/{tag}` returns nothing.
- Immutability applies at publication: "Once an immutable release is
  published, its associated Git tag is locked" (docs.github.com, immutable
  releases).

## Decision

Keep immutable releases enabled and switch to draft-then-publish:

- `release-please-config.json` gains `"draft": true` and
  `"force-tag-creation": true`.
- The `release-assets` job keeps its `release_created == 'true'` gate,
  uploads wheel + sdist + SPDX SBOM + SHA256SUMS to the draft (with the
  provenance attestation created before upload), then publishes as its final
  step: `gh release edit "$TAG" --draft=false`. No new permissions needed -
  releases are covered by `contents: write`.

## Consequences

The failure mode changes from an unrecoverable assetless immutable release
to a recoverable stuck draft: if any asset step fails, the release stays an
unpublished draft (visible to maintainers only) with its tag already created,
so subsequent release-please runs still find the previous release. Recovery:
re-run the failed `release-assets` job (uploads are idempotent via
`--clobber`), or manually `gh release upload vX.Y.Z <files> --clobber` and
`gh release edit vX.Y.Z --draft=false`. The end-to-end proof of the flow
arrives with the next releasable merge. v0.4.3 stays assetless forever; its
artifacts are reproducible from the immutable tag.
