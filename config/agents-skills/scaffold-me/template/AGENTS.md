# Agent rules

These rules apply to every automated agent and every change in this repository.

## Project direction

Read:

- [README.md](README.md) for the project’s **Purpose** and **Vision**;
- [NORTHSTAR.md](NORTHSTAR.md) for the dimensions we continuously improve.

Every change must preserve or advance that direction. Do not optimize one
North Star dimension by silently degrading another.

## Required guidance

Apply the documents relevant to the changed area:

| Guidance | Document | Read when |
|---|---|---|
| Architecture | [architecture.md](docs/architecture.md) | Changing boundaries, dependencies, persistence, APIs or integrations |
| Engineering standards | [standards.md](docs/engineering/standards.md) | Changing code, configuration or documentation |
| Testing | [testing.md](docs/engineering/testing.md) | Changing behavior or fixing a defect |
| Tooling and gates | [tooling.md](docs/engineering/tooling.md) | Changing dependencies, tooling or CI, and before completion |
| DevSecOps | [devsecops.md](docs/engineering/devsecops.md) | Changing inputs, secrets, dependencies, infrastructure, CI or releases |
| Commits and releases | [CONTRIBUTING.md](CONTRIBUTING.md) | Making commits or releases |

If applicable instructions conflict or cannot be followed, stop and surface the
conflict. Do not choose silently.

## Karpathy rules

### 1. Think before coding

Inspect the relevant implementation, callers and tests. State assumptions,
uncertainty and material tradeoffs. Ask when missing information would
materially change the result.

### 2. Simplicity first

Implement the smallest complete solution. Avoid speculative features,
abstractions and configuration.

### 3. Surgical changes

Change only what the requested outcome requires. Preserve unrelated working
code and user changes.

### 4. Goal-driven execution

Define observable acceptance criteria, prove the required behavior and
continue until the applicable checks pass.

## Scope discipline

> Implement for the approved contract and credible failure modes—not every
> imaginable future, integration, platform, configuration or impossible state.

- Solve the approved problem completely and stop.
- Do not design for hypothetical future requirements.
- Handle an edge case only when it is required, reachable, operationally
  credible, or necessary to prevent security failures, data loss or corruption.
- Do not handle states already made impossible by types, validation or domain
  invariants.
- Do not add unused configuration, extension points, fallbacks or compatibility
  layers.
- State intentionally unsupported boundaries instead of implementing them.
- Prefer deleting unnecessary code over preserving or explaining it.

## Meaningful verification

Every test must protect meaningful project-owned behavior, a contract, an
invariant, a credible failure mode or a previously observed regression.

- Do not write tests solely to increase coverage.
- Do not test language, framework or dependency behavior that the project does
  not own.
- Do not test trivial getters, setters, field storage or constant values.
- Test a DTO or schema only when the project owns relevant validation,
  normalization, defaults, transformation, serialization, compatibility or
  security behavior.
- Test through public behavior and stable boundaries.
- Do not mock internal implementation details.
- Use fakes only at real external boundaries and only when they preserve the
  contract relevant to the test.
- Do not assert call order or call counts unless they are part of the required
  behavior.
- Avoid repeating the same assertion at several test layers unless each layer
  protects a distinct risk.
- Use integration tests when a boundary cannot be proven meaningfully with a
  unit test.
- Prefer fewer high-signal tests over large quantities of low-signal tests.
- Coverage is a required floor, never a substitute for meaningful assertions.

A useful test should answer: **what credible defect would this test catch?**

## Non-negotiable rules

- Preserve documented architecture, contracts and project invariants.
- Never bypass validation, authorization, transaction or security boundaries.
- Never weaken tests, coverage thresholds or security gates merely to pass CI.
- Never commit secrets or realistic secret-shaped examples.
- Preserve unrelated working-tree changes.
- Do not add speculative abstractions, compatibility shims or dead code.
- Do not retain commented-out implementations.
- Do not modify generated files directly.
- Do not place plans, reviewer conversations or agent transcripts in source
  files.
- Review the final diff for accidental files, secrets and unrelated changes.

## Definition of done

A change is complete only when:

- it satisfies the approved requirements;
- it supports the project’s Purpose and Vision;
- it does not silently regress a North Star dimension;
- it follows the applicable architecture and engineering guidance;
- meaningful tests prove the required behavior and important boundaries;
- code, tests, configuration and documentation agree;
- every applicable quality and DevSecOps gate passes;
- no secret, unrelated change or unresolved in-scope defect remains;
- every claimed verification command was actually executed successfully.
