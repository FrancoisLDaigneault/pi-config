import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

/**
 * Skill router — makes the installed skill catalogue actually reachable.
 *
 * Pi puts every skill's name + description in the system prompt but loads the
 * body only when the model decides to; Pi's own docs concede "models don't
 * always do this". The result is a large catalogue that stays invisible unless
 * the user names a skill. bigpowers ships a session-start bootstrap for Claude
 * Code and Gemini (.gemini/extensions/bigpowers/hooks/session-start) but no Pi
 * extension at all, so on Pi nothing arms the router.
 *
 * This injects a short routing policy as a transient user-context message on
 * the first LLM call after a session starts and again after a compaction
 * rewrites the context. It is catalogue-wide (bigpowers, context-mode,
 * pi-lens, ponytail, pi-subagents, pi-mcp-adapter, user skills) and carries a
 * decision procedure rather than a list of skill names.
 *
 * One-shot by design: `context` fires before EVERY LLM call, including each
 * tool round-trip, so injecting unconditionally would repeat the policy dozens
 * of times per turn. A flag is armed on session_start / session_compact and
 * consumed by the next context event. The message is not persisted — the
 * handler receives a deep copy scoped to that one call.
 *
 * Subagent children (PI_SUBAGENT_CHILD=1) skip entirely: they run explicit
 * task contracts, so routing advice is noise and costs tokens.
 *
 * Escape hatch: launch with PI_SKILL_ROUTER=0 to disable for one session.
 */

// Injected verbatim. Kept short on purpose: it is re-sent after every
// compaction, and a long policy competes with the work it is meant to route.
const POLICY = `<EXTREMELY_IMPORTANT>
Skill routing policy (injected by the skill-router extension, not sent by the user).

Skills from several packages are installed. Their names and one-line descriptions
are already in your system prompt; their bodies are not. Loading one means
reading its SKILL.md with the \`read\` tool.

BEFORE answering a non-trivial request, decide whether a skill applies.
Under-triggering is the documented failure mode, so bias toward loading: if you
judge even a modest chance (~10%) that a skill fits, read it before acting. The
cost is one file read.

ESCAPE: for a trivial request — a direct factual question, a one-line edit, a
status check, a command you already know — answer directly and load nothing.
Ceremony on small work is a failure too.

Route by task shape:
- New feature or initiative -> survey-context, then scope-work -> slice-tasks -> plan-work
- Bug, breakage, failing test -> investigate-bug, then diagnose-root
- Reviewing code or a diff -> request-review
- Over-engineering or simplification -> ponytail (ponytail-review to audit a change)
- Large output: logs, builds, many files, document processing -> ctx_execute / ctx_batch_execute
- Searching code by structure -> pi-lens-ast-grep (ast_grep_search); definitions and
  references -> pi-lens-lsp-navigation
- Library or framework documentation -> mcp({server:"context7", tool:"query-docs", ...})
- Recalling past decisions or sessions -> mcp({server:"mempalace", tool:"mempalace_search", ...})
- Delegating parallel or isolated work -> pi-subagents

UNSURE which skill applies: read search-skills and let it route you.
NEVER load the whole catalogue — one or two skills, then act.
The user can always force a skill with /skill:name.
</EXTREMELY_IMPORTANT>`;

export default function (pi: ExtensionAPI) {
 if (process.env.PI_SUBAGENT_CHILD === "1") return;
 if (process.env.PI_SKILL_ROUTER === "0") return;

 // Armed by lifecycle events, consumed by the next LLM call.
 let armed = false;

 // Session started, loaded, resumed, or forked — the agent is about to act on
 // a fresh context.
 pi.on("session_start", () => {
  armed = true;
 });

 // Compaction rewrote the context, so an earlier injection is gone. Re-arm.
 pi.on("session_compact", () => {
  armed = true;
 });

 // Fires before every LLM call. Inject once per arming, then disarm.
 pi.on("context", (event) => {
  if (!armed) return;
  armed = false;
  return {
   messages: [
    ...event.messages,
    { role: "user" as const, content: POLICY, timestamp: Date.now() },
   ],
  };
 });
}
