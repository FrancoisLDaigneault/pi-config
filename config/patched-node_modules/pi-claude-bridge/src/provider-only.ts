import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { activate } from "./index.js";

// Provider-only entry point: registers the claude-bridge model provider and
// all session lifecycle wiring, but never the AskClaude tool — regardless of
// askClaude.enabled in claude-bridge.json. Point a locked-down agent's
// `extensions:` list at this file to give it Claude models without a tool
// that can launch Claude Code with write and bash access.
export default function (pi: ExtensionAPI) {
	activate(pi, { askClaudeTool: false });
}
