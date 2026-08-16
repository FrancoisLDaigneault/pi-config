import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

/**
 * Maestro guard — hard enforcement of "Maestro orchestrates, never executes".
 *
 * Blocks execution and research tools in the MAIN agent session only.
 * Subagent children (spawned by pi-subagents with PI_SUBAGENT_CHILD=1)
 * keep full tool access, so delegated work is unaffected.
 *
 * Escape hatch: launch with PI_MAESTRO_GUARD=0 to disable for one session.
 */

// Deny-list is open by construction: tools registered by future extensions are not covered — review this map whenever a new package is installed.
const BLOCKED: Record<string, string> = {
 // Built-in execution tools
 edit: "editing files",
 write: "writing files",
 bash: "running shell commands",
 // NOTE: grep/find are deliberately ALLOWED — local orientation (knowing where
 // things live) makes task contracts sharper. Deep research stays delegated.
 // Sandboxed code execution (context-mode)
 ctx_execute: "executing code",
 ctx_execute_file: "processing files with code",
 ctx_batch_execute: "running command batches",
 // Web research
 web_search: "web research",
 fetch_content: "fetching web content",
 source_check: "fact-checking research",
 ctx_fetch_and_index: "fetching web content",
 // Structural rewrite (pi-lens); ast_grep_search stays allowed as read-only orientation
 ast_grep_replace: "structural code rewrite",
};

export default function (pi: ExtensionAPI) {
 // Subagent children execute freely — the guard applies to Maestro only.
 if (process.env.PI_SUBAGENT_CHILD === "1") return;
 if (process.env.PI_MAESTRO_GUARD === "0") return;

 pi.on("tool_call", (event) => {
  // Object.hasOwn guards against prototype-chain hits (e.g. "constructor").
  const activity = Object.hasOwn(BLOCKED, event.toolName)
   ? BLOCKED[event.toolName]
   : undefined;
  if (activity) {
   return {
    block: true,
    reason:
     `Maestro orchestrates, never executes. '${event.toolName}' (${activity}) is reserved for subagents. ` +
     `Dispatch one instead: workers for code, scouts/researchers for research, reviewers for audits.`,
   };
  }
  return undefined;
 });
}
