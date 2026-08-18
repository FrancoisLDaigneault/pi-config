# Changelog

## [0.5.1](https://github.com/fld-forge/pi-config/compare/v0.5.0...v0.5.1) (2026-08-18)


### Bug Fixes

* enforce MCP tool exclusions and sync models ([fa44967](https://github.com/fld-forge/pi-config/commit/fa4496732c3e3381c2a766c1aaa4237583a43b66))

## [0.5.0](https://github.com/fld-forge/pi-config/compare/v0.4.7...v0.5.0) (2026-08-18)


### Features

* preserve every local node_modules patch, drop scaffold-me ([#34](https://github.com/fld-forge/pi-config/issues/34)) ([745d859](https://github.com/fld-forge/pi-config/commit/745d85933daa32c69f7b33977526c5e8191d5745))

## [0.4.7](https://github.com/fld-forge/pi-config/compare/v0.4.6...v0.4.7) (2026-08-18)


### Documentation

* point references at the new organization ([#30](https://github.com/fld-forge/pi-config/issues/30)) ([5060446](https://github.com/fld-forge/pi-config/commit/5060446686821a1d1d47a9e391f69a3f3fc8e9b8))

## [0.4.6](https://github.com/fld-forge/pi-config/compare/v0.4.5...v0.4.6) (2026-08-18)


### Documentation

* remove repository-settings material from the repository ([#28](https://github.com/fld-forge/pi-config/issues/28)) ([502e865](https://github.com/fld-forge/pi-config/commit/502e865c43d6893a82fec27597335c3e631177f8))

## [0.4.5](https://github.com/fld-forge/pi-config/compare/v0.4.4...v0.4.5) (2026-08-17)


### Documentation

* record signature rule activation ([#24](https://github.com/fld-forge/pi-config/issues/24)) ([fc6497d](https://github.com/fld-forge/pi-config/commit/fc6497d1d80a89cf1473bdf5192486bc1f581a74))

## [0.4.4](https://github.com/fld-forge/pi-config/compare/v0.4.3...v0.4.4) (2026-08-17)


### Bug Fixes

* report and redact top-level secret strings ([#21](https://github.com/fld-forge/pi-config/issues/21)) ([b9e8547](https://github.com/fld-forge/pi-config/commit/b9e85470833159111721398b00c36f7c06b8fd2c))

## [0.4.3](https://github.com/fld-forge/pi-config/compare/v0.4.2...v0.4.3) (2026-08-17)


### Documentation

* add ADRs, governance files, settings inventory and Scorecard ([#17](https://github.com/fld-forge/pi-config/issues/17)) ([277e5df](https://github.com/fld-forge/pi-config/commit/277e5dff968debfc39c75fa0fe96a5a0c32c183e))

## [0.4.2](https://github.com/fld-forge/pi-config/compare/v0.4.1...v0.4.2) (2026-08-17)


### Documentation

* add agent guide, doc-drift gate and CI coverage reports ([#15](https://github.com/fld-forge/pi-config/issues/15)) ([3297ead](https://github.com/fld-forge/pi-config/commit/3297ead6eaf1a5d6d87f52100e6410065d05a639))

## [0.4.1](https://github.com/fld-forge/pi-config/compare/v0.4.0...v0.4.1) (2026-08-17)


### Documentation

* align README, CONTRIBUTING, SECURITY and NORTHSTAR with current reality ([#13](https://github.com/fld-forge/pi-config/issues/13)) ([b3ae58e](https://github.com/fld-forge/pi-config/commit/b3ae58ec09966b97130b52c78bef124448814ac2))

## [0.4.0](https://github.com/fld-forge/pi-config/compare/v0.3.1...v0.4.0) (2026-08-17)


### Features

* repo hygiene, coverage gate and release assets ([#11](https://github.com/fld-forge/pi-config/issues/11)) ([c2d1c91](https://github.com/fld-forge/pi-config/commit/c2d1c91a544707d807cc1f30ae72769fe56ee9d4))

## [0.3.1](https://github.com/fld-forge/pi-config/compare/v0.3.0...v0.3.1) (2026-08-17)


### Bug Fixes

* keep uv.lock in sync with releases, enforce ruff format, fix pyright venv resolution ([#7](https://github.com/fld-forge/pi-config/issues/7)) ([44bfae3](https://github.com/fld-forge/pi-config/commit/44bfae38e1953785252473307fb61a42b4402ac2))

## [0.3.0](https://github.com/fld-forge/pi-config/compare/v0.2.0...v0.3.0) (2026-08-17)


### Features

* English-only codebase and docs with automated language gate ([#4](https://github.com/fld-forge/pi-config/issues/4)) ([70a913e](https://github.com/fld-forge/pi-config/commit/70a913e1fc9dde16c657594c262231730e00ecbd))

## 0.2.0 (2026-08-17)


### Features

* add supply-chain gates, release automation and governance docs ([c8d478c](https://github.com/fld-forge/pi-config/commit/c8d478cd113eb3ddd8dad74d9ff8dcf05f4ee34e))
* enforce strict static typing with mypy ([cc1533d](https://github.com/fld-forge/pi-config/commit/cc1533d69e8e4ce0e7b7fd390adbb1dc294204ad))
* initial Pi configuration snapshot with uv-based tooling ([147e632](https://github.com/fld-forge/pi-config/commit/147e6324a6ffbfdc3e5792c7797c9da773c93414))


### Bug Fixes

* gate context-mode patch behind --patch flag, document fresh-machine restore ([8b2e96b](https://github.com/fld-forge/pi-config/commit/8b2e96b2c140dd542f06b590d118346931c1d4da))
* per-section backup exclusions matching legacy behavior, robust error handling ([9559998](https://github.com/fld-forge/pi-config/commit/955999882a88900fa975d74d9758b7cfa87a683b))
* secret audit covers list values and every copied JSON ([ecc19c1](https://github.com/fld-forge/pi-config/commit/ecc19c1b733b6120b67522a490b3b90f7558015b))


### Documentation

* define north star KPIs per axis with measured baselines ([1213409](https://github.com/fld-forge/pi-config/commit/12134092f11dadf87c1e7a345df9351909d06373))
* document package structure, quality standards and test commands ([d0153a4](https://github.com/fld-forge/pi-config/commit/d0153a42753014f495d4ca11d6233040469c69dd))

## Changelog

Ce fichier est maintenu automatiquement par
[release-please](https://github.com/googleapis/release-please) à partir des
messages de commit (Conventional Commits). Ne pas l'éditer à la main.
