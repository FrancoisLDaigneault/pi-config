# Governance

pi-config is a single-maintainer project. This file states how decisions are
made - honestly, without invented committees.

## Roles

- **Maintainer** (final say on everything): [@FrancoisLDaigneault](https://github.com/FrancoisLDaigneault).
- **AI agents** execute day-to-day changes under the maintainer's
  orchestration. Every change that lands on `main` goes through a pull
  request, the automated gates, and an independent review before merge -
  nobody pushes directly to `main`.

## Decisions

Significant technical decisions are recorded as ADRs in
[`docs/adr/`](docs/adr/README.md) (context, decision, consequences). Accepted
ADRs are superseded by new ones, not rewritten.

## Contributions, releases, security

- Contribution path and quality gates: [`CONTRIBUTING.md`](CONTRIBUTING.md).
- Releases are automated: release-please opens a release PR from the
  Conventional Commits on `main`; merging it publishes the tag, changelog and
  signed release assets.
- Security reports: [`SECURITY.md`](SECURITY.md).
