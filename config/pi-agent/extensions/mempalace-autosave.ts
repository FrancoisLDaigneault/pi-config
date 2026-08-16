import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

/**
 * MemPalace autosave — bridges Pi lifecycle events to MemPalace's installed
 * hook handlers so memory checkpoints happen without manual MCP calls.
 *
 * Pi session JSONL is parseable by MemPalace's claude-code harness parser
 * (message.role / content[].text), so transcripts ingest as-is.
 *
 * Saves must never block or crash the session. The CLI reads its payload
 * exclusively from stdin, so handlers await the stdin flush (capped at 2 s)
 * to keep the payload from racing session teardown at shutdown; the spawned
 * process stays detached + unref'd and outlives the session.
 *
 * Subagent children (PI_SUBAGENT_CHILD=1) skip entirely — only the main
 * session persists memory, avoiding double ingestion.
 *
 * Escape hatch: launch with PI_MEMPALACE_AUTOSAVE=0 to disable for one session.
 */

const MEMPALACE_EXE = join(homedir(), ".local", "bin", "mempalace.exe");

// Cap on how long a handler may wait for the stdin flush. The promise always
// resolves — on flush, on error, or on timeout — never rejects, never hangs.
const STDIN_FLUSH_TIMEOUT_MS = 2000;

function runHook(
  hook: "stop" | "session-end" | "precompact",
  sessionId: string | undefined,
  transcriptPath: string | undefined,
): Promise<void> {
  return new Promise((resolve) => {
    let settled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const done = () => {
      if (settled) return;
      settled = true;
      if (timer) clearTimeout(timer);
      resolve();
    };
    try {
      // In-memory session — no transcript to ingest.
      if (!transcriptPath) return done();
      timer = setTimeout(done, STDIN_FLUSH_TIMEOUT_MS);
      const exe = existsSync(MEMPALACE_EXE) ? MEMPALACE_EXE : "mempalace";
      const child = spawn(
        exe,
        ["hook", "run", "--hook", hook, "--harness", "claude-code"],
        {
          stdio: ["pipe", "ignore", "ignore"],
          detached: true,
          windowsHide: true,
        },
      );
      // Swallow every failure mode and resolve: a memory save must never
      // break the session.
      child.on("error", done);
      const stdin = child.stdin;
      if (!stdin) {
        child.unref();
        return done();
      }
      stdin.on("error", done);
      // 'close' fires once the payload has flushed into the OS pipe buffer
      // and the fd is released — safe for Pi to exit after this.
      stdin.on("close", done);
      stdin.end(
        JSON.stringify({
          session_id: sessionId ?? "unknown",
          transcript_path: transcriptPath,
          stop_hook_active: false,
        }),
      );
      // Detached + unref: the save outlives session teardown without holding Pi open.
      child.unref();
    } catch {
      done();
    }
  });
}

export default function (pi: ExtensionAPI) {
  if (process.env.PI_SUBAGENT_CHILD === "1") return;
  if (process.env.PI_MEMPALACE_AUTOSAVE === "0") return;

  // Settled agent run → "stop": cheap no-op below MemPalace's save interval;
  // above it, checkpoints the diary and ingests the transcript.
  pi.on("agent_settled", async (_event, ctx) => {
    await runHook(
      "stop",
      ctx.sessionManager.getSessionId(),
      ctx.sessionManager.getSessionFile(),
    );
  });

  // Before compaction rewrites context → "precompact": ingest while intact.
  pi.on("session_before_compact", async (_event, ctx) => {
    await runHook(
      "precompact",
      ctx.sessionManager.getSessionId(),
      ctx.sessionManager.getSessionFile(),
    );
  });

  // Session teardown (quit/reload/new/resume/fork) → "session-end": final
  // flush. Awaiting the stdin flush here is what closes the shutdown race.
  pi.on("session_shutdown", async (_event, ctx) => {
    await runHook(
      "session-end",
      ctx.sessionManager.getSessionId(),
      ctx.sessionManager.getSessionFile(),
    );
  });
}
