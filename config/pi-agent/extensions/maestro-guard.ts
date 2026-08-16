import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

/**
 * Maestro guard — hard enforcement of "Maestro orchestrates, never executes".
 *
 * Three-tier guard evaluated at tool_call, in the MAIN agent session only:
 *  1. ALLOWED — orchestration and read-only orientation tools (exact names).
 *     Special case: the `mcp` gateway is allowed only for discovery calls (no `tool`
 *     argument) or MemPalace tools — Maestro's memory protocol.
 *  2. BLOCKED — known execution/research tools, kept for their pedagogical messages
 *     that redirect to the right subagent.
 *  3. DEFAULT — any tool not in either map is blocked (fail-closed): a future
 *     extension's tool can never silently slip past the guard.
 *
 * Subagent children (spawned by pi-subagents with PI_SUBAGENT_CHILD=1)
 * keep full tool access, so delegated work is unaffected.
 *
 * Escape hatch: launch with PI_MAESTRO_GUARD=0 to disable for one session.
 */

// Orchestration + read-only orientation. Unknown tools are blocked by default,
// so a legitimate new orchestration tool must be added here (then restart Pi).
const ALLOWED = new Set<string>([
 // Delegation — Maestro's hands
 "subagent",
 "subagent_wait",
 "subagent_supervisor",
 "intercom",
 // Built-in read-only orientation
 "read",
 "ls",
 "grep",
 "find",
 "glob",
 // pi-lens read-only navigation/diagnostics
 "ast_grep_search",
 "module_report",
 "project_report",
 "symbol_search",
 "read_symbol",
 "read_enclosing",
 "lsp_diagnostics",
 "lens_diagnostics",
 "pi_lens_activate_tools",
 "get_search_content",
 // context-mode read-only (search/stats/diagnostics — not execution)
 "ctx_search",
 "ctx_stats",
 "ctx_doctor",
 // Interaction/tracking
 "ask_user_question",
 // rpiv-todo registers exactly one tool named "todo" (tool/types.ts TOOL_NAME)
 "todo",
]);

// Known execution/research tools. The default tier already blocks everything
// unknown; this map only exists for its messages that name the right subagent.
const BLOCKED: Record<string, string> = {
 // Built-in execution tools
 edit: "editing files",
 write: "writing files",
 bash: "running shell commands",
 interactive_shell: "running interactive terminal work",
 // Sandboxed code execution (context-mode)
 ctx_execute: "executing code",
 ctx_execute_file: "processing files with code",
 ctx_batch_execute: "running command batches",
 // MCP scripting (pi-mcp-adapter) — arbitrary JavaScript, not an isolation boundary
 mcpScript: "executing arbitrary JavaScript",
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
 // Couplage: pi-subagents (nicobailon) définit PI_SUBAGENT_CHILD=1; un autre
 // runner (ex: avtc-pi-subagent) ne le définit pas -> les enfants seraient
 // bloqués (fail-closed, bypass PI_MAESTRO_GUARD=0).
 if (process.env.PI_SUBAGENT_CHILD === "1") return;
 if (process.env.PI_MAESTRO_GUARD === "0") return;

 pi.on("tool_call", (event) => {
  // Tier 1 special case: `mcp` gateway. Allowed only for discovery calls
  // (`tool` absent or empty string) or MemPalace memory tools; anything else —
  // including a present non-string target — is blocked (fail-closed), because
  // any other target would proxy execution through a future MCP server.
  if (event.toolName === "mcp") {
   const target = ((event.input ?? {}) as Record<string, unknown>).tool;
   if (
    target === undefined ||
    target === "" ||
    (typeof target === "string" && target.startsWith("mempalace_"))
   ) {
    return undefined;
   }
   return {
    block: true,
    reason:
     `Maestro orchestrates, never executes. The 'mcp' gateway is reserved for MemPalace ` +
     `(memory protocol) in this session; '${String(target)}' must go through a subagent instead.`,
   };
  }

  // Tier 1: orchestration and orientation tools pass through.
  if (ALLOWED.has(event.toolName)) {
   return undefined;
  }

  // Tier 2: known execution tools get a message naming the right subagent.
  // Object.hasOwn guards against prototype-chain hits (e.g. "constructor").
  if (Object.hasOwn(BLOCKED, event.toolName)) {
   return {
    block: true,
    reason:
     `Maestro orchestrates, never executes. '${event.toolName}' (${BLOCKED[event.toolName]}) is reserved for subagents. ` +
     `Dispatch one instead: workers for code, scouts/researchers for research, reviewers for audits.`,
   };
  }

  // Tier 3: fail-closed default — unknown tools never slip past the guard.
  return {
   block: true,
   reason:
    `Outil inconnu du guard Maestro. Si c'est un outil d'orchestration légitime, ` +
    `ajoute-le à ALLOWED dans maestro-guard.ts puis redémarre Pi; sinon dispatch un subagent.`,
  };
 });
}
