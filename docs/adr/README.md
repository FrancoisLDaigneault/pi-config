# Architecture Decision Records

Significant technical decisions for pi-config, recorded as short ADRs
(context / decision / consequences). The "why" behind the tooling lives here
so it does not have to be re-litigated; the "what" is enforced by the gates
themselves.

| ADR | Title | Status |
| --- | --- | --- |
| [0001](0001-mypy-strict-as-sole-type-gate.md) | mypy --strict as the sole type gate | accepted |
| [0002](0002-english-only-accent-heuristic-gate.md) | English-only content with an accent-heuristic gate | accepted |
| [0003](0003-config-snapshot-excluded-from-style-gates.md) | config/ is a byte-faithful snapshot, excluded from style gates | accepted |
| [0004](0004-release-automation-with-lock-sync-and-assets.md) | Release automation with lock sync and signed assets | accepted |
| [0005](0005-branch-protection-without-required-checks.md) | Branch protection without required status checks | accepted |
| [0006](0006-branch-coverage-floor-on-pytest-addopts.md) | 90% branch-coverage floor riding pytest addopts | accepted |
| [0007](0007-duplication-kept-over-abstraction.md) | Duplication kept over abstraction in the command modules | accepted |
| [0008](0008-documentation-drift-gate.md) | Documentation drift gate | accepted |
| [0009](0009-draft-then-publish-release-flow.md) | Draft-then-publish release flow for immutable releases | accepted |
| [0010](0010-signed-commits.md) | Signed commits on main with repo-local SSH signing | accepted |

Conventions: MADR-lite, numbered, immutable once accepted (supersede with a
new ADR instead of editing history). New significant decisions get the next
number.
