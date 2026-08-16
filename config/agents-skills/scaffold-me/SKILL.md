---
name: scaffold-me
description: Guide, generate, and verify lean greenfield project scaffolds. Use when a user asks to scaffold, initialize, bootstrap, or start a new software project and wants recommendations for languages, tooling, linting, tests, and CI before any domain code is written.
---

# Scaffold Me

Create a minimal, verified foundation for a new project. Never use this skill
to retrofit an existing repository.

## Interview

Ask one question at a time and ask no more than five scaffold questions. Skip
anything the user already answered.

1. Obtain the project name and parent directory.
2. Capture the project **Purpose** in one sentence.
3. Capture the expected **Vision** in one or two concrete sentences.
4. Read [references/baselines.md](references/baselines.md), recommend one
   technology profile with its baseline tools and CI, and offer at most two
   alternatives. Let the user accept, replace, or skip any recommendation.
5. Recommend MIT licensing, then require an explicit choice between `MIT` and
   `UNLICENSED`. For MIT, capture the copyright holder and year in the same
   question. Capture an optional GitHub owner only when the user wants
   `CODEOWNERS`. Do not silently select a license or substitute one the
   template does not support.

Ask additional questions only when the user explicitly requests deeper
scaffolding. Do not ask about databases, deployment, containers, APIs,
frontends, or observability unless they are required by the final target.

## Approval gate

Present a compact Scaffold Contract containing:

- project name and destination;
- Purpose and Vision;
- selected profile and baseline;
- license choice and, for MIT, the exact copyright notice;
- whether `CODEOWNERS` will be generated and for which GitHub owner;
- exact files and verification commands.

Stop and request explicit approval. Do not create directories, files,
dependencies, or repositories before approval.

## Build

After approval:

1. Check the destination with the host's native filesystem tools. If it exists,
   stop. Copier merges by default, so never invoke it for an existing path.
2. Run Copier directly from the skill directory with the approved values:

   ```text
   uvx --from copier==9.17.1 copier copy --defaults --data profile=<profile> --data project_name=<name> --data purpose=<purpose> --data vision=<vision> --data license=<license> [MIT copyright data] [GitHub owner] <skill-directory> <destination>
   ```

   Never pass `--force`, `--overwrite`, `--trust`, or `--UNSAFE`. Do not use a
   wrapper or generate into an existing directory.
3. Initialize the selected package manager and lockfile using the commands in
   [references/baselines.md](references/baselines.md).
4. Run the profile's complete verification commands.
5. Initialize Git only if the user accepted it in the baseline.

Generate only the approved source skeleton, meaningful initial contract test,
documentation, native tool configuration, quality gates, hooks, command catalog,
and CI workflow. Generate no domain behavior, speculative directories, empty
test layers, custom quality tooling, or hypothetical architecture components.
The architecture document always describes the real repository; include a
Mermaid system diagram only when multiple approved components make it useful.

## Handoff gate

Report the generated files and verification results, then stop. Ask whether the
user wants to begin planning the first implementation. Do not start planning
automatically.

If the user agrees, follow the planning gate written into the generated
`AGENTS.md`: ground the plan in README **Purpose** and **Vision**, ask one
question at a time, present the complete plan, and stop again for explicit
execution approval. Never chain scaffold, planning, and implementation.
