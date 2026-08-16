---
name: gauntlet-loop
description: Turn a goal into a concrete-reference quality loop, or run that loop with Pi's worker and fresh reviewer subagents. Use for "/gauntlet-loop", "gauntlet loop", "gauntlet this", "make a gauntlet prompt", or "loop until it beats X".
license: CC-BY-4.0
compatibility: Requires Pi with pi-subagents and the worker, reviewer, scout, and researcher agents.
metadata:
  source: https://github.com/robonuggets/gauntlet-loop
  technique: Matt Shumer's Gauntlet Loop
  adaptation: Modified for Pi and pi-subagents
---

# Gauntlet Loop for Pi

Turn the user's goal into a short prompt that forces comparison with a real quality bar. If the user asks to run it, keep the parent Pi session in charge and use Pi subagents.

## Choose the bar

If the user supplied a reference, verify that it is named, fetchable, and directly comparable. Otherwise offer 2 or 3 specific candidate bars with `ask_user_question`, then stop for their choice.

Prefer a demanding real artifact: a live page at matching viewports, a specific published piece, a named repository plus tests or benchmarks, a paper's methods section, or a real deck of similar scope. Add a measurable target when the goal has one. Never use a vague category or an inaccessible reference. Beware of a bar that is too easy: a weak reference lets the loop exit on round one having proven nothing.

## Return the prompt

After the bar is chosen, return one paste-ready block around 120–180 words, then one line: `I can run this here.` Adapt this template without adding architecture, file layout, stack choices, budgets, or round limits the user did not request:

```text
Build [GOAL].

The bar is [BAR]. Fetch the real artifact first and compare against it directly, not against a description.

Split the work into the smallest pieces that can be improved and judged independently. Use one builder for each change and a separate critic with fresh context. The critic inspects the actual output beside the bar under neutral A/B labels, picks the better one, and names the single biggest remaining gap. Scores and praise are not useful.

If ours loses, send that gap back to the builder and repeat. Stop only when ours wins the blind comparison or I stop the run.

Use Pi's worker as the sole writer and fresh reviewer agents as critics. Track progress with Pi's task list and FleetView.
```

## Run it in Pi

Load the `pi-subagents` skill before execution. The parent owns decomposition, winner decisions, iteration, and final verification. Children do not launch subagents.

1. Fetch and inspect the bar before building. If it cannot be fetched or compared, choose another bar.
2. Split the goal into judgeable pieces and track them with `todo`.
3. Use one `worker` as the sole writer in the active checkout. Do not run parallel writers unless each has an intentionally isolated worktree.
4. After each build pass, launch a `reviewer` with `context: "fresh"`. Give it the real output and bar, neutral A/B labels, and no builder history. Require exactly: winner, evidence, and biggest gap.
5. If ours loses, synthesize the gap and launch one fix `worker`. Search for sibling instances of the same failure class when applicable.
6. Repeat one observable round at a time. Do not encode an unbounded `while` loop or a fixed round cap; continue until ours wins or the user stops it.
7. Run the project's normal checks and inspect the final artifact before declaring success.

Use Pi's native `todo`, async run status, and FleetView instead of building a custom progress page.

## Model routing

Use the default configuration: the global default model and the `subagents.agentOverrides` in `~/.pi/agent/settings.json` decide which model each agent runs. Do not hardcode model IDs in prompts and do not set per-run model overrides for this skill.

If a configured model is unavailable or a different routing is needed, surface it to the user; an override file can be introduced at that point rather than pre-emptively.

## Non-negotiable failure checks

- The builder never judges its own work.
- Critics use fresh context and a binary A/B pick, not a score.
- The actual bar is fetched; descriptions are insufficient.
- No fixed number of rounds.
- No parallel writes to one checkout.
- Stop and ask the user when the loop reaches an unapproved product, architecture, budget, or authority decision.

## Attribution

Adapted from [RoboNuggets' Gauntlet Loop](https://github.com/robonuggets/gauntlet-loop), licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The Gauntlet Loop technique is credited by the source project to Matt Shumer and Claude of Duty. This version is modified for Pi and `pi-subagents`.
