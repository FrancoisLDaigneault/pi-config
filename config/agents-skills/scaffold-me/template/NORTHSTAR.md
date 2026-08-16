# North Star

> Defined standards let us automate with confidence—delivering faster while
> becoming more reliable, maintainable, secure, and consistently higher
> quality. The North Star is never reached; we measure our progress, pursue it
> continuously, and keep raising the bar.

## Purpose

The North Star guides engineering decisions and continuous improvement. It is
not a finish line, a backlog or a collection of vanity metrics.

We improve four connected dimensions:

1. security;
2. delivery speed;
3. maintainability;
4. quality and reliability.

Speed means shortening the path from an approved change to trustworthy
feedback and safe delivery. It never means bypassing engineering or security
controls.

## Dimensions

| Dimension | We pursue | Useful evidence |
|---|---|---|
| Security | Reduced exposure, stronger controls and faster remediation | Verified secrets, known vulnerabilities, control failures, remediation time and security incidents |
| Delivery speed | Faster trustworthy feedback and safe delivery | Local-check duration, CI duration, lead time, deployment frequency and recovery time |
| Maintainability | Changes that remain understandable, isolated and economical | Architecture violations, static-analysis debt, dependency health, change complexity and ownership clarity |
| Quality and reliability | Correct behavior and dependable operation | Escaped defects, change-failure rate, flaky tests, meaningful behavior coverage, service objectives and regressions |

Runtime performance is measured separately when latency, throughput, memory or
resource usage is part of the Vision.

## Measurement principles

- Establish a baseline before claiming improvement.
- Define each adopted measure, its evidence source and its review cadence.
- Prefer automated evidence from established tools and platforms.
- Measure outcomes where possible and use engineering gates as leading signals.
- Use trends together with thresholds; a single number rarely tells the whole
  story.
- Do not create instrumentation whose maintenance cost exceeds its decision
  value.
- Do not game coverage, complexity, velocity or defect metrics.
- Never improve delivery speed by weakening security, testing or reliability.
- Never improve a metric by moving work or failures outside its measurement.
- Surface material tradeoffs instead of hiding them.
- Raise standards when evidence shows the project can sustain the higher bar.
- Do not lower a standard merely to make a failing build pass.
- Remove or replace measures that no longer predict meaningful outcomes.

## Project measures

The project’s selected measures and enforced thresholds are documented in:

- [testing.md](docs/engineering/testing.md) for behavioral evidence and
  coverage;
- [tooling.md](docs/engineering/tooling.md) for automated quality gates;
- [devsecops.md](docs/engineering/devsecops.md) for security and supply-chain
  evidence;
- [architecture.md](docs/architecture.md) for reliability, scale and
  performance requirements.

Not every project needs every possible measure. Adopt a measure when it informs
a real decision, protects an important boundary or demonstrates progress
toward the Vision.
