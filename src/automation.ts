import type {
  EvidenceFile,
  ModeId,
  ProjectInput,
  WorkspaceDraftV2,
  WorkflowStep,
} from "./types";
import { buildWorkflowPlan } from "./workflow";
import { buildAnalysisProject } from "./workspace-draft";

export type AutomationRecipeId = "growth" | "recovery" | "technical" | "content";

export type AutomationAdvanceMode = "continuous" | "approval";

export type AutomationEvidenceSource =
  | "site"
  | "files"
  | "gsc"
  | "ga4"
  | "crm"
  | "deployment";

export interface AutomationConfig {
  schemaVersion: 1;
  objective: string;
  recipe: AutomationRecipeId;
  selectedModes: ModeId[];
  evidenceSources: AutomationEvidenceSource[];
  advanceMode: AutomationAdvanceMode;
}

export interface AutomationRecipe {
  id: AutomationRecipeId;
  label: string;
  description: string;
  modes: readonly ModeId[];
  evidenceSources: readonly AutomationEvidenceSource[];
}

export type AutomationEvidenceAvailability = Record<AutomationEvidenceSource, boolean>;

export const AUTOMATION_MODE_ORDER = [
  "recover",
  "audit",
  "keyword",
  "plan",
  "fix",
  "write",
  "link",
  "review",
] as const satisfies readonly ModeId[];

export const AUTOMATION_EVIDENCE_SOURCES = [
  "site",
  "files",
  "gsc",
  "ga4",
  "crm",
  "deployment",
] as const satisfies readonly AutomationEvidenceSource[];

export const AUTOMATION_ADVANCE_MODES = [
  "continuous",
  "approval",
] as const satisfies readonly AutomationAdvanceMode[];

export const AUTOMATION_RECIPES = [
  {
    id: "growth",
    label: "增长全链路",
    description: "从站点审计和需求验证开始，形成计划并准备执行与复盘。",
    modes: ["audit", "keyword", "plan", "fix", "write", "link", "review"],
    evidenceSources: ["site", "files", "gsc", "ga4", "crm", "deployment"],
  },
  {
    id: "recovery",
    label: "流量恢复",
    description: "先验证异常，再定位技术或业务机制并形成可逆修复与复盘。",
    modes: ["recover", "audit", "plan", "fix", "review"],
    evidenceSources: ["site", "files", "gsc", "ga4", "deployment"],
  },
  {
    id: "technical",
    label: "技术修复",
    description: "定位已验证的技术阻断，形成最小修复契约并安排复验。",
    modes: ["audit", "fix", "review"],
    evidenceSources: ["site", "files", "deployment"],
  },
  {
    id: "content",
    label: "内容增长",
    description: "验证查询与页面归属，规划、产出并支持可发布内容。",
    modes: ["audit", "keyword", "plan", "fix", "write", "link", "review"],
    evidenceSources: ["site", "files", "gsc", "ga4", "crm", "deployment"],
  },
] as const satisfies readonly AutomationRecipe[];

export const DEFAULT_AUTOMATION_CONFIG: AutomationConfig = {
  schemaVersion: 1,
  objective: "",
  recipe: "growth",
  selectedModes: [...AUTOMATION_RECIPES[0].modes],
  evidenceSources: ["site", "files"],
  advanceMode: "approval",
};

const MODE_SET = new Set<ModeId>(AUTOMATION_MODE_ORDER);
const EVIDENCE_SOURCE_SET = new Set<AutomationEvidenceSource>(AUTOMATION_EVIDENCE_SOURCES);
const ADVANCE_MODE_SET = new Set<AutomationAdvanceMode>(AUTOMATION_ADVANCE_MODES);
const RECIPE_SET = new Set<AutomationRecipeId>(AUTOMATION_RECIPES.map((recipe) => recipe.id));

const MODE_DEPENDENCIES: Partial<Record<ModeId, readonly ModeId[]>> = {
  keyword: ["audit"],
  plan: ["audit"],
  fix: ["audit"],
  write: ["keyword"],
  link: ["audit"],
};

const SOURCE_PATTERNS: Record<Exclude<AutomationEvidenceSource, "site" | "files">, RegExp[]> = {
  gsc: [
    /(?:^|[._\-/\s])gsc(?:[._\-/\s]|$)/i,
    /search[ _-]?console/i,
    /(?:query|page).{0,40}(?:clicks?|impressions?|ctr|position)/i,
  ],
  ga4: [
    /(?:^|[._\-/\s])ga4(?:[._\-/\s]|$)/i,
    /google[ _-]?analytics/i,
    /(?:landing[ _-]?page|sessions?|users?).{0,40}(?:conversions?|events?)/i,
  ],
  crm: [
    /(?:^|[._\-/\s])crm(?:[._\-/\s]|$)/i,
    /(?:qualified[ _-]?leads?|opportunit(?:y|ies)|revenue|合格线索|商机|收入)/i,
  ],
  deployment: [
    /(?:^|[._\-/\s])(?:deploy|deployment|release|changelog)(?:[._\-/\s]|$)/i,
    /(?:已|已经|刚刚|已完成).{0,24}(?:上线|发布|部署|改版|修复|迁移|变更)/i,
    /\b(?:deployed|released|launched|rolled out|went live)\b/i,
  ],
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function uniqueAllowed<T extends string>(
  value: unknown,
  allowed: ReadonlySet<T>,
): T[] {
  if (!Array.isArray(value)) return [];
  const result: T[] = [];
  const seen = new Set<T>();
  for (const item of value) {
    if (typeof item !== "string" || !allowed.has(item as T) || seen.has(item as T)) continue;
    seen.add(item as T);
    result.push(item as T);
  }
  return result;
}

function recipeById(id: AutomationRecipeId): AutomationRecipe {
  return AUTOMATION_RECIPES.find((recipe) => recipe.id === id) ?? AUTOMATION_RECIPES[0];
}

export function normalizeAutomationConfig(value: unknown): AutomationConfig {
  if (!isRecord(value)) {
    return {
      ...DEFAULT_AUTOMATION_CONFIG,
      selectedModes: [...DEFAULT_AUTOMATION_CONFIG.selectedModes],
      evidenceSources: [...DEFAULT_AUTOMATION_CONFIG.evidenceSources],
    };
  }

  const recipe = typeof value.recipe === "string" && RECIPE_SET.has(value.recipe as AutomationRecipeId)
    ? value.recipe as AutomationRecipeId
    : DEFAULT_AUTOMATION_CONFIG.recipe;
  const recipeDefaults = recipeById(recipe);
  const selectedModes = Array.isArray(value.selectedModes)
    ? uniqueAllowed(value.selectedModes, MODE_SET)
    : [...recipeDefaults.modes];
  const evidenceSources = Array.isArray(value.evidenceSources)
    ? uniqueAllowed(value.evidenceSources, EVIDENCE_SOURCE_SET)
    : [...recipeDefaults.evidenceSources];
  const advanceMode = typeof value.advanceMode === "string" &&
    ADVANCE_MODE_SET.has(value.advanceMode as AutomationAdvanceMode)
    ? value.advanceMode as AutomationAdvanceMode
    : DEFAULT_AUTOMATION_CONFIG.advanceMode;

  return {
    schemaVersion: 1,
    objective: typeof value.objective === "string" ? value.objective.trim() : "",
    recipe,
    selectedModes,
    evidenceSources,
    advanceMode,
  };
}

export function resolveAutomationModes(selectedModes: readonly ModeId[]): ModeId[] {
  const resolved = new Set<ModeId>();

  const include = (mode: ModeId) => {
    if (resolved.has(mode)) return;
    for (const dependency of MODE_DEPENDENCIES[mode] ?? []) include(dependency);
    resolved.add(mode);
  };

  for (const mode of selectedModes) include(mode);
  return AUTOMATION_MODE_ORDER.filter((mode) => resolved.has(mode));
}

export function buildAutomationPlan(
  config: AutomationConfig,
  gatingProject: ProjectInput,
  evidence: readonly EvidenceFile[] = [],
  reviewProject: ProjectInput = gatingProject,
): WorkflowStep[] {
  const selected = new Set(resolveAutomationModes(config.selectedModes));
  const gatedSteps = buildWorkflowPlan(gatingProject, evidence, reviewProject);
  const byMode = new Map(gatedSteps.map((step) => [step.mode, step]));

  return AUTOMATION_MODE_ORDER.flatMap((mode) => {
    if (!selected.has(mode)) return [];
    const step = byMode.get(mode);
    return step ? [{ ...step }] : [];
  });
}

function projectEvidenceText(project: ProjectInput): string {
  return Object.values(project)
    .filter((value): value is string => typeof value === "string" && value.trim().length > 0)
    .join("\n");
}

function populatedEvidence(evidence: readonly EvidenceFile[]): EvidenceFile[] {
  return evidence.filter((file) => file.size > 0 && file.content.trim().length > 0);
}

function matchesEvidenceSource(
  file: EvidenceFile,
  source: Exclude<AutomationEvidenceSource, "site" | "files">,
): boolean {
  if (file.size <= 0 || !file.content.trim()) return false;
  const value = `${file.name}\n${file.type}\n${file.content}`;
  return SOURCE_PATTERNS[source].some((pattern) => pattern.test(value));
}

export function selectAutomationEvidence(
  config: AutomationConfig,
  evidence: readonly EvidenceFile[] = [],
): EvidenceFile[] {
  const files = populatedEvidence(evidence);
  if (config.evidenceSources.includes("files")) return files;

  const selectedSources = config.evidenceSources.filter(
    (source): source is Exclude<AutomationEvidenceSource, "site" | "files"> =>
      source !== "site" && source !== "files",
  );
  return files.filter((file) =>
    selectedSources.some((source) => matchesEvidenceSource(file, source)),
  );
}

export function getAutomationEvidenceAvailability(
  project: ProjectInput,
  evidence: readonly EvidenceFile[] = [],
): AutomationEvidenceAvailability {
  const files = populatedEvidence(evidence);
  const fileText = files.map((file) => `${file.name}\n${file.type}\n${file.content}`).join("\n");
  const deploymentText = `${projectEvidenceText(project)}\n${fileText}`;

  return {
    site: Boolean(project.allowNetworkEvidence && project.siteUrl.trim()),
    files: files.length > 0,
    gsc: files.some((file) => matchesEvidenceSource(file, "gsc")),
    ga4: files.some((file) => matchesEvidenceSource(file, "ga4")),
    crm: files.some((file) => matchesEvidenceSource(file, "crm")),
    deployment: SOURCE_PATTERNS.deployment.some((pattern) => pattern.test(deploymentText)),
  };
}

export function getMissingAutomationEvidenceSources(
  config: AutomationConfig,
  project: ProjectInput,
  evidence: readonly EvidenceFile[] = [],
): AutomationEvidenceSource[] {
  const availability = getAutomationEvidenceAvailability(project, evidence);
  return config.evidenceSources.filter((source) => !availability[source]);
}

export function buildAutomationProject(
  draft: WorkspaceDraftV2,
  mode: ModeId,
  config: AutomationConfig,
): ProjectInput {
  const project = buildAnalysisProject(draft, mode);
  return {
    ...project,
    objective:
      draft.modes[mode].objective.trim() ||
      config.objective.trim() ||
      draft.profile.primaryGoal.trim(),
  };
}

export function buildAutomationGatingProject(
  draft: WorkspaceDraftV2,
  config: AutomationConfig,
): ProjectInput {
  const project = buildAnalysisProject(draft, "recover");
  const objectives = [
    config.objective.trim(),
    draft.modes.recover.objective.trim(),
    draft.profile.primaryGoal.trim(),
  ].filter((value, index, values) => value && values.indexOf(value) === index);
  return {
    ...project,
    objective: objectives.join("\n\n"),
  };
}
