---
description: Scaffold NORTHSTAR.md for this project (4 measurable KPI axes)
argument-hint: "[project context]"
---
Create (or update) `NORTHSTAR.md` at the project root. Dispatch a scout first if the current state of the project is unknown. The file must follow this structure — every KPI needs a current value, a target, and an automated measurement method (CI job, script, or command). A KPI nobody measures is decoration.

```markdown
# North Star — <project name>

> Automate the guardrails to deliver faster, with higher quality, and more securely.

## KPIs

| Axis | KPI | Current | Target | Measured by |
|------|-----|---------|--------|-------------|
| Speed | e.g. lead time commit→prod, CI duration | ? | ? | CI job / command |
| Security | e.g. critical vulns open, % gates automated | ? | ? | audit / scanner in CI |
| Maintainability | e.g. coverage on critical paths, complexity ceiling | ? | ? | coverage / lint gate |
| Scalability | e.g. p95 latency at target load, cost per request | ? | ? | bench / monitoring |

## Guardrails automated

- [ ] Lint + typecheck gate in CI
- [ ] Tests gate in CI
- [ ] Secret scanning
- [ ] Dependency audit

## Review cadence

KPIs reviewed every <N> weeks. Always-green targets are too easy; always-red targets are fantasy.
```

Pick ONE primary KPI per axis (not a laundry list). Ground current values in real measurements — dispatch an agent to measure, never guess.

Project context: $ARGUMENTS
