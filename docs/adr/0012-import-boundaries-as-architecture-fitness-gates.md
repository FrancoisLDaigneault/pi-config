# ADR-0012: Import boundaries as architecture fitness gates

- Status: accepted
- Date: 2026-08-20

## Context

The command modules serve different workflows and should change for different
reasons. The secret-redaction policy is also independent of filesystem paths,
copy mechanics and command orchestration. Those seams were documented in
ADR-0007 but were not executable, so a future import could silently couple
them.

Patch-copy operations were mixed into `fsops` even though they change with the
set of locally patched packages rather than with generic file-copy behavior.

## Decision

Move `copy_patched` and `context_mode_version` mechanically into `patched`.
Keep `backup`, `restore` and `sync` mutually independent with an Import Linter
contract. Keep `secrets` from importing `paths`, `fsops`, `patched` or any
command module with a second contract. Ruff TID251 prevents production modules
from importing `tests` or the thin `scripts` wrappers. Deptry continues to
check undeclared external dependencies.

Run these checks through `just check`, pre-commit and the CI quality job. Do not
add a global layers contract: the package has no stable layer hierarchy that
would justify one.

This supersedes only ADR-0007's module-graph description and its placement of
`context_mode_version`; its decision to keep command-level duplication remains
accepted.

## Consequences

Architectural drift now fails before merge. Import Linter is a development-only
locked dependency; the runtime package remains stdlib-only. The extraction adds
no behavior, class, interface or factory. A future boundary change must update
the contract deliberately rather than bypassing the gate.
