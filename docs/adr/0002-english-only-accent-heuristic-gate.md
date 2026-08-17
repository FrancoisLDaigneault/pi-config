# ADR-0002: English-only content with an accent-heuristic gate

- Status: accepted
- Date: 2026-08-17

## Context

The repository went public with mixed French/English content. A full FR-to-EN
translation of code, comments, CLI strings and docs landed in PR #4 (release
v0.3.0). A guardrail was needed so French could not silently return.

## Decision

`tests/unit/test_language.py` fails the suite when a scanned file contains
Latin accented code points (U+00C0-U+00FF minus the multiplication and
division signs, plus the OE ligatures). The scan covers a defined file set
(Python trees, root docs, workflows, templates); excluded by design:
`CHANGELOG.md` (generated), `config/` (live snapshot), `LICENSE` (author
name), `CODE_OF_CONDUCT.md` (canonical text). Rejected alternatives: NLP
language detection (false positives on short fragments), cspell (permanent
dictionary upkeep), LLM review (non-deterministic).

## Consequences

Accentless French is undetectable - an accepted trade-off (the heuristic
catches ~95%; PR review covers the rest, proven when review caught an
accent-free French pyproject description the gate cannot see). The explicit
file list is existence-checked, so a renamed target fails loudly instead of
silently shrinking the scan.
