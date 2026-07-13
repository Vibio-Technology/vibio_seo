import generatedKnowledge from "../generated/knowledge.json";

export const MAX_KNOWLEDGE_BYTES = 128 * 1024;
export const SUPPORTED_MODES = [
  "PLAN",
  "AUDIT",
  "FIX",
  "WRITE",
  "KEYWORD",
  "LINK",
  "REVIEW",
  "RECOVER",
] as const;

export type KnowledgeMode = (typeof SUPPORTED_MODES)[number];

export interface KnowledgeBundle {
  mode: KnowledgeMode;
  skillSource: string;
  referenceSources: string[];
  bytes: number;
  prompt: string;
}

interface GeneratedKnowledge {
  schemaVersion: number;
  maxKnowledgeBytes: number;
  modes: Record<KnowledgeMode, KnowledgeBundle>;
}

const knowledge = generatedKnowledge as unknown as GeneratedKnowledge;
const modeSet = new Set<string>(SUPPORTED_MODES);

export class KnowledgeError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "KnowledgeError";
  }
}

export function normalizeMode(value: string): KnowledgeMode {
  const mode = value.trim().toUpperCase();
  if (!modeSet.has(mode)) {
    throw new KnowledgeError(`未知模式。可选：${SUPPORTED_MODES.join("、")}。`);
  }
  return mode as KnowledgeMode;
}

export function loadModeKnowledge(modeValue: string): KnowledgeBundle {
  const mode = normalizeMode(modeValue);
  if (
    knowledge.schemaVersion !== 1 ||
    knowledge.maxKnowledgeBytes !== MAX_KNOWLEDGE_BYTES
  ) {
    throw new KnowledgeError("网页知识包版本无效；请重新生成。");
  }

  const bundle = knowledge.modes[mode];
  if (
    !bundle ||
    bundle.mode !== mode ||
    bundle.bytes > MAX_KNOWLEDGE_BYTES ||
    new TextEncoder().encode(bundle.prompt).byteLength !== bundle.bytes
  ) {
    throw new KnowledgeError(`${mode} 模式知识包无效；请重新生成。`);
  }

  return {
    ...bundle,
    referenceSources: [...bundle.referenceSources],
  };
}
