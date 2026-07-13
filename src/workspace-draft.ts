import {
  EMPTY_MODE_DRAFT,
  EMPTY_PROJECT_PROFILE,
  EMPTY_WORKSPACE_DRAFT,
} from "./data";
import type {
  ModeDraft,
  ModeDrafts,
  ModeId,
  ProjectInput,
  ProjectProfile,
  WorkspaceDraftV2,
} from "./types";

export const MODE_IDS: readonly ModeId[] = [
  "plan",
  "audit",
  "fix",
  "keyword",
  "write",
  "link",
  "review",
  "recover",
];

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function stringValue(value: unknown, fallback: string): string {
  return typeof value === "string" ? value : fallback;
}

function booleanValue(value: unknown, fallback: boolean): boolean {
  return typeof value === "boolean" ? value : fallback;
}

function normalizeModeDraft(value: unknown, fallback: ModeDraft): ModeDraft {
  const record = isRecord(value) ? value : {};
  return {
    objective: stringValue(record.objective, fallback.objective),
    details: stringValue(record.details, fallback.details),
    scope: stringValue(record.scope, fallback.scope),
    timing: stringValue(record.timing, fallback.timing),
  };
}

function normalizeProjectProfile(value: unknown, fallback: ProjectProfile): ProjectProfile {
  const record = isRecord(value) ? value : {};
  return {
    projectName: stringValue(record.projectName, fallback.projectName),
    siteUrl: stringValue(record.siteUrl, fallback.siteUrl),
    market: stringValue(record.market, fallback.market),
    language: stringValue(record.language, fallback.language),
    conversion: stringValue(record.conversion, fallback.conversion),
    primaryGoal: stringValue(record.primaryGoal, fallback.primaryGoal),
    audience: stringValue(record.audience, fallback.audience),
    businessModel: stringValue(record.businessModel, fallback.businessModel),
    capacity: stringValue(record.capacity, fallback.capacity),
    allowNetworkEvidence: booleanValue(
      record.allowNetworkEvidence,
      fallback.allowNetworkEvidence,
    ),
    allowStateDraft: booleanValue(record.allowStateDraft, fallback.allowStateDraft),
  };
}

export function createEmptyModeDrafts(): ModeDrafts {
  return Object.fromEntries(
    MODE_IDS.map((mode) => [mode, { ...EMPTY_MODE_DRAFT }]),
  ) as ModeDrafts;
}

export function createEmptyWorkspaceDraft(): WorkspaceDraftV2 {
  return {
    schemaVersion: 2,
    profile: { ...EMPTY_PROJECT_PROFILE },
    modes: createEmptyModeDrafts(),
    sharedContext: "",
  };
}

function cloneWorkspaceDraft(draft: WorkspaceDraftV2): WorkspaceDraftV2 {
  return {
    schemaVersion: 2,
    profile: { ...draft.profile },
    modes: Object.fromEntries(
      MODE_IDS.map((mode) => [mode, { ...draft.modes[mode] }]),
    ) as ModeDrafts,
    sharedContext: draft.sharedContext,
  };
}

export function normalizeWorkspaceDraft(
  value: unknown,
  fallback: WorkspaceDraftV2 = EMPTY_WORKSPACE_DRAFT,
): WorkspaceDraftV2 | null {
  if (
    !isRecord(value) ||
    value.schemaVersion !== 2 ||
    !isRecord(value.profile) ||
    !isRecord(value.modes)
  ) {
    return null;
  }

  const fallbackDraft = cloneWorkspaceDraft(fallback);
  const storedModes = value.modes;
  return {
    schemaVersion: 2,
    profile: normalizeProjectProfile(value.profile, fallbackDraft.profile),
    modes: Object.fromEntries(
      MODE_IDS.map((mode) => [
        mode,
        normalizeModeDraft(storedModes[mode], fallbackDraft.modes[mode]),
      ]),
    ) as ModeDrafts,
    sharedContext: stringValue(value.sharedContext, fallbackDraft.sharedContext),
  };
}

const LEGACY_CONTEXT_FIELDS = [
  ["objective", "当前目标 / 问题"],
  ["scope", "分析范围"],
  ["details", "旧版补充信息"],
  ["decisionWindow", "决策 / 观察窗口"],
] as const;

function legacySharedContext(value: Record<string, unknown>): string {
  return LEGACY_CONTEXT_FIELDS.flatMap(([field, label]) => {
    const content = stringValue(value[field], "").trim();
    return content ? [`${label}：\n${content}`] : [];
  }).join("\n\n");
}

export function migrateLegacyProject(
  value: unknown,
  fallback: WorkspaceDraftV2 = EMPTY_WORKSPACE_DRAFT,
): WorkspaceDraftV2 {
  const fallbackDraft = cloneWorkspaceDraft(fallback);
  if (!isRecord(value)) return fallbackDraft;

  return {
    schemaVersion: 2,
    profile: {
      projectName: stringValue(value.projectName, fallbackDraft.profile.projectName),
      siteUrl: stringValue(value.siteUrl, fallbackDraft.profile.siteUrl),
      market: stringValue(value.market, fallbackDraft.profile.market),
      language: stringValue(value.language, fallbackDraft.profile.language),
      conversion: stringValue(value.conversion, fallbackDraft.profile.conversion),
      primaryGoal: fallbackDraft.profile.primaryGoal,
      audience: stringValue(value.audience, fallbackDraft.profile.audience),
      businessModel: stringValue(value.businessModel, fallbackDraft.profile.businessModel),
      capacity: stringValue(value.capacity, fallbackDraft.profile.capacity),
      allowNetworkEvidence: booleanValue(
        value.allowNetworkEvidence,
        fallbackDraft.profile.allowNetworkEvidence,
      ),
      allowStateDraft: booleanValue(
        value.allowStateDraft,
        fallbackDraft.profile.allowStateDraft,
      ),
    },
    modes: createEmptyModeDrafts(),
    sharedContext: legacySharedContext(value),
  };
}

function joinedSections(sections: Array<[label: string, value: string]>): string {
  return sections.flatMap(([label, value]) => {
    const content = value.trim();
    return content ? [`${label}：\n${content}`] : [];
  }).join("\n\n");
}

export function buildAnalysisProject(draft: WorkspaceDraftV2, mode: ModeId): ProjectInput {
  const task = draft.modes[mode];
  const objective = task.objective.trim() || draft.profile.primaryGoal.trim();
  const details = joinedSections([
    ["本模式补充信息", task.details],
    ["共享项目背景", draft.sharedContext],
  ]);

  return {
    ...draft.profile,
    objective,
    scope: task.scope.trim(),
    details,
    decisionWindow: task.timing.trim(),
  };
}

export function buildWorkflowGatingProject(draft: WorkspaceDraftV2): ProjectInput {
  const recovery = draft.modes.recover;
  const review = draft.modes.review;
  return {
    ...draft.profile,
    objective: joinedSections([
      ["恢复任务", recovery.objective],
      ["复盘任务", review.objective],
      ["项目主要目标", draft.profile.primaryGoal],
    ]),
    scope: joinedSections([
      ["恢复影响范围", recovery.scope],
      ["复盘影响范围", review.scope],
    ]),
    details: joinedSections([
      ["恢复同期背景", recovery.details],
      ["复盘测量背景", review.details],
      ["共享项目背景", draft.sharedContext],
    ]),
    decisionWindow: joinedSections([
      ["异常开始时间", recovery.timing],
      ["变更与比较窗口", review.timing],
    ]),
  };
}

export const buildWorkflowSignalProject = buildWorkflowGatingProject;
