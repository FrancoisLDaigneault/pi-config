# ADR-0007: Duplication kept over abstraction in the command modules

- Status: accepted
- Date: 2026-08-16

## Context

`sync`, `restore` and `backup` repeat a "check dir exists, warn, copy, count"
shape. An independent architecture review evaluated extracting a shared
helper and audited the whole module graph.

## Decision

Keep the duplication. A shared `copy_section` helper would need 4-5
parameters and would simplify no call site - duplication is cheaper than that
abstraction. The module graph stays a strict DAG: the three command modules
sit over the `fsops` helper, which sits over the stdlib-only leaves `paths`
and `secrets` (the command modules never import each other). The call-time
env-var seam in `paths.py` remains the single test seam serving unit,
integration and e2e tiers alike. No CLI framework, no config object.

## Consequences

The review's only actionable item was subtractive: the dead `is_excluded_file`
function and its test were removed. Two dormant findings are on record with
wake conditions: the `config/` subdirectory names are a sync/restore contract
guarded by the e2e round-trip test (centralize in `paths.py` only if a fourth
section is added or one is renamed), and `context_mode_version` stays in
`fsops` (every alternative home is worse).
