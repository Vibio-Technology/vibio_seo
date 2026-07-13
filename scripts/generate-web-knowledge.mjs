import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const OUTPUT = resolve(ROOT, "src/lib/generated/knowledge.json");
const MAX_KNOWLEDGE_BYTES = 128 * 1024;

const MODE_SKILLS = {
  PLAN: "vibio-plan/SKILL.md",
  AUDIT: "vibio-audit/SKILL.md",
  FIX: "vibio-fix/SKILL.md",
  WRITE: "vibio-content/SKILL.md",
  KEYWORD: "vibio-keyword/SKILL.md",
  LINK: "vibio-link/SKILL.md",
  REVIEW: "vibio-review/SKILL.md",
  RECOVER: "vibio/SKILL.md",
};

const MODE_REFERENCES = {
  PLAN: [
    "evidence-policy.md",
    "capability-routing.md",
    "operating-system.md",
    "delivery-template.md",
    "roi-attribution.md",
    "seo-experimentation.md",
    "paid-search-intelligence.md",
    "state-templates.md",
  ],
  AUDIT: [
    "evidence-policy.md",
    "capability-routing.md",
    "google-search-docs.md",
    "javascript-rendering.md",
    "seo-fix-principles.md",
    "core-web-vitals.md",
    "faceted-navigation.md",
    "bing-webmaster-docs.md",
    "stack-detection.md",
    "paid-search-intelligence.md",
  ],
  FIX: [
    "evidence-policy.md",
    "capability-routing.md",
    "google-search-docs.md",
    "javascript-rendering.md",
    "seo-fix-principles.md",
    "core-web-vitals.md",
    "faceted-navigation.md",
    "bing-webmaster-docs.md",
    "stack-detection.md",
  ],
  WRITE: [
    "evidence-policy.md",
    "write-playbook.md",
    "competitor-teardown.md",
    "sourcing-and-eeat.md",
    "adversarial-review.md",
  ],
  KEYWORD: [
    "evidence-policy.md",
    "keyword-engine.md",
    "keyword-validation.md",
    "paid-search-intelligence.md",
    "authority-cascade.md",
  ],
  LINK: ["evidence-policy.md", "link-architecture.md", "backlink-playbook.md"],
  REVIEW: [
    "evidence-policy.md",
    "capability-routing.md",
    "google-search-docs.md",
    "core-web-vitals.md",
    "bing-webmaster-docs.md",
    "review-engine.md",
    "roi-attribution.md",
    "seo-experimentation.md",
    "state-templates.md",
  ],
  RECOVER: [
    "evidence-policy.md",
    "recovery-playbook.md",
    "review-engine.md",
    "migration-playbook.md",
  ],
};

function byteLength(value) {
  return Buffer.byteLength(value, "utf8");
}

async function readCanonical(relativePath) {
  const absolutePath = resolve(ROOT, relativePath);
  if (absolutePath !== ROOT && !absolutePath.startsWith(`${ROOT}${sep}`)) {
    throw new Error(`Knowledge path escapes the repository: ${relativePath}`);
  }

  const content = await readFile(absolutePath, "utf8");
  if (byteLength(content) > MAX_KNOWLEDGE_BYTES) {
    throw new Error(`Knowledge file exceeds ${MAX_KNOWLEDGE_BYTES} bytes: ${relativePath}`);
  }
  return content;
}

async function buildMode(mode) {
  const skillSource = MODE_SKILLS[mode];
  const referenceSources = MODE_REFERENCES[mode].map((name) => `references/${name}`);
  const parts = [
    `# 当前模式：${mode}`,
    "",
    `## Skill 指令（${skillSource}）`,
    "",
    await readCanonical(skillSource),
  ];

  for (const source of referenceSources) {
    parts.push("", `## 参考资料（${source}）`, "", await readCanonical(source));
  }

  const prompt = parts.join("\n");
  const bytes = byteLength(prompt);
  if (bytes > MAX_KNOWLEDGE_BYTES) {
    throw new Error(`${mode} knowledge bundle exceeds ${MAX_KNOWLEDGE_BYTES} bytes (${bytes}).`);
  }

  return { mode, skillSource, referenceSources, bytes, prompt };
}

const modes = {};
for (const mode of Object.keys(MODE_SKILLS)) {
  modes[mode] = await buildMode(mode);
}

const output = {
  schemaVersion: 1,
  maxKnowledgeBytes: MAX_KNOWLEDGE_BYTES,
  modes,
};

await mkdir(dirname(OUTPUT), { recursive: true });
await writeFile(OUTPUT, `${JSON.stringify(output, null, 2)}\n`, "utf8");

const summary = Object.values(modes)
  .map(({ mode, bytes }) => `${mode}=${bytes}`)
  .join(" ");
process.stdout.write(`Generated ${OUTPUT}\n${summary}\n`);
