/**
 * pi-skill-parity — renders the <available_skills> catalog for providers whose
 * prompt builder omits it.
 *
 * THE BUG
 * -------
 * Pi resolves an agent's skills into `event.systemPromptOptions.skills` the same
 * way for every provider, then renders the prompt through a provider-specific
 * path. Only the `claude-bridge` path emits an <available_skills> section. An
 * agent routed to `openai-codex` gets its skills resolved and then silently
 * dropped.
 *
 * Measured at before_agent_start (same task, three agents):
 *
 *   scout    provider=openai-codex   spo.skills=array:4  -> rendered 0 skills
 *   reviewer provider=claude-bridge  spo.skills=array:4  -> rendered 4 skills
 *   delegate provider=claude-bridge  spo.skills=array:4  -> rendered 4 skills
 *
 * Same resolved input, different rendered output. Pi core ships compiled and
 * cannot be patched locally, but `before_agent_start` can write systemPrompt,
 * and that hook does reach codex agents.
 *
 * WHY NOT KEY OFF PROMPT CONTENT
 * ------------------------------
 * `promptHasCatalog` is false for BOTH providers at hook time — claude-bridge
 * appends its catalog downstream of this hook. Testing the prompt for an
 * existing catalog therefore double-injects on the claude path (observed:
 * reviewer reported 110 skills across 2 catalogs). The provider is the only
 * reliable discriminator here.
 *
 * MODES
 * -----
 *   "parity" (default) — render exactly the skills Pi resolved for this agent.
 *                        Restores provider parity; changes nothing else.
 *   "full"             — render every SKILL.md discoverable on disk. This is a
 *                        preference change, not a bug fix: it gives codex agents
 *                        MORE than claude agents get. ~106 skills / ~12k tokens.
 *
 * Config (optional) in ~/.pi/agent/settings.json:
 *
 *   "skillParity": {
 *     "enabled": true,
 *     "mode": "parity",              // or "full"
 *     "rendersCatalog": ["claude-bridge"],  // providers to leave alone
 *     "exclude": ["bigpowers"],      // full mode only: substring match
 *     "maxSkills": 0                 // full mode only: 0 = uncapped
 *   }
 */

import fs from "node:fs";
import path from "node:path";
import os from "node:os";

const HOME = process.env.USERPROFILE || process.env.HOME || os.homedir();
const AGENT_DIR = path.join(HOME, ".pi", "agent");

/** Providers whose own prompt builder already emits <available_skills>. */
const DEFAULT_RENDERS_CATALOG = ["claude-bridge"];

function skillRoots() {
  const roots = [];
  const nm = path.join(AGENT_DIR, "npm", "node_modules");
  const addPkg = (dir) => {
    roots.push(path.join(dir, "skills"));
    roots.push(path.join(dir, ".pi", "skills"));
  };

  let entries = [];
  try {
    entries = fs.readdirSync(nm, { withFileTypes: true });
  } catch {
    entries = [];
  }
  for (const e of entries) {
    if (!e.isDirectory()) continue;
    if (e.name.startsWith("@")) {
      let scoped = [];
      try {
        scoped = fs.readdirSync(path.join(nm, e.name), { withFileTypes: true });
      } catch {
        scoped = [];
      }
      for (const s of scoped) {
        if (s.isDirectory()) addPkg(path.join(nm, e.name, s.name));
      }
    } else {
      addPkg(path.join(nm, e.name));
    }
  }
  roots.push(path.join(AGENT_DIR, "skills"));
  roots.push(path.join(HOME, ".agents", "skills"));
  return roots;
}

/** Minimal frontmatter reader; folds indented continuation lines. */
function parseFrontmatter(text) {
  if (!text.startsWith("---")) return null;
  const end = text.indexOf("\n---", 3);
  if (end < 0) return null;
  const body = text.slice(text.indexOf("\n") + 1, end);

  const out = {};
  let key = null;
  for (const raw of body.split("\n")) {
    const m = raw.match(/^([A-Za-z_][\w-]*):\s?(.*)$/);
    if (m) {
      key = m[1];
      out[key] = m[2] ?? "";
    } else if (key && raw.trim()) {
      out[key] += " " + raw.trim();
    }
  }
  return out;
}

let DISK_CACHE = null;

/** All SKILL.md on disk, keyed by skill name. */
function scanDisk() {
  if (DISK_CACHE) return DISK_CACHE;
  const byName = new Map();
  for (const root of skillRoots()) {
    let dirs = [];
    try {
      dirs = fs.readdirSync(root, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const d of dirs) {
      if (!d.isDirectory()) continue;
      const file = path.join(root, d.name, "SKILL.md");
      let text;
      try {
        if (fs.statSync(file).size > 512_000) continue;
        text = fs.readFileSync(file, "utf8");
      } catch {
        continue;
      }
      const fm = parseFrontmatter(text);
      if (!fm) continue;
      const name = (fm.name || d.name).trim();
      const description = (fm.description || "").trim();
      if (!name || !description || byName.has(name)) continue;
      byName.set(name, { name, description, location: file });
    }
  }
  DISK_CACHE = byName;
  return DISK_CACHE;
}

/** Normalize whatever shape systemPromptOptions.skills uses into skill records. */
function resolveResolvedSkills(resolved) {
  const disk = scanDisk();
  const out = [];
  for (const entry of resolved) {
    if (!entry) continue;
    if (typeof entry === "string") {
      const hit = disk.get(entry);
      if (hit) out.push(hit);
      continue;
    }
    const name = entry.name || entry.id;
    if (!name) continue;
    const hit = disk.get(name);
    out.push({
      name,
      description: entry.description || (hit && hit.description) || "",
      location: entry.location || entry.path || (hit && hit.location) || "",
    });
  }
  return out.filter((s) => s.description);
}

function collectFull(cfg) {
  const exclude = Array.isArray(cfg.exclude) ? cfg.exclude : [];
  let all = [...scanDisk().values()];
  if (exclude.length) {
    all = all.filter(
      (s) => !exclude.some((p) => s.name.includes(p) || s.location.includes(p))
    );
  }
  all.sort((a, b) => a.name.localeCompare(b.name));
  const cap = Number(cfg.maxSkills) || 0;
  return cap > 0 ? all.slice(0, cap) : all;
}

function renderCatalog(skills) {
  const esc = (s) =>
    String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  const body = skills
    .map(
      (s) =>
        `  <skill>\n` +
        `    <name>${esc(s.name)}</name>\n` +
        `    <description>${esc(s.description)}</description>\n` +
        `    <location>${esc(s.location)}</location>\n` +
        `  </skill>`
    )
    .join("\n");

  return (
    "The following skills provide specialized instructions for specific tasks.\n" +
    "Use the read tool to load a skill's file when the task matches its description.\n" +
    "When a skill file references a relative path, resolve it against the skill " +
    "directory (parent of SKILL.md) and use that absolute path in tool commands.\n\n" +
    `<available_skills>\n${body}\n</available_skills>`
  );
}

function loadConfig() {
  try {
    const s = JSON.parse(
      fs.readFileSync(path.join(AGENT_DIR, "settings.json"), "utf8")
    );
    return s.skillParity && typeof s.skillParity === "object" ? s.skillParity : {};
  } catch {
    return {};
  }
}

export default function piSkillParity(pi) {
  const cfg = loadConfig();
  if (cfg.enabled === false) return;

  const rendersCatalog = Array.isArray(cfg.rendersCatalog)
    ? cfg.rendersCatalog
    : DEFAULT_RENDERS_CATALOG;
  const mode = cfg.mode === "full" ? "full" : "parity";

  pi.on("before_agent_start", (event, ctx) => {
    try {
      const provider = ctx?.model?.provider;
      // Provider renders its own catalog downstream of this hook — leave it alone.
      // Content-sniffing the prompt does NOT work here: the claude-bridge catalog
      // is appended after this point, so it always looks absent and we double-inject.
      if (!provider || rendersCatalog.includes(provider)) return;

      const resolved = event?.systemPromptOptions?.skills;
      const skills =
        mode === "full"
          ? collectFull(cfg)
          : Array.isArray(resolved)
            ? resolveResolvedSkills(resolved)
            : [];

      if (!skills.length) return;

      const existing = String(event?.systemPrompt ?? "");
      if (existing.includes("<available_skills>")) return; // belt and braces

      const block = renderCatalog(skills);
      return { systemPrompt: existing ? `${existing}\n\n${block}` : block };
    } catch {
      // Never break agent startup over a prompt section.
      return;
    }
  });
}
