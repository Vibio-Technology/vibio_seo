import type {
  ModeId,
  ModelSettings,
  ProjectInput,
  RunRecord,
  WorkflowExecutionSnapshot,
  WorkflowStep,
  WorkflowStepStatus,
  WorkspaceDraftV2,
} from "./types";
import {
  DEFAULT_AUTOMATION_CONFIG,
  normalizeAutomationConfig,
  type AutomationConfig,
} from "./automation";
import {
  migrateLegacyProject,
  MODE_IDS,
  normalizeWorkspaceDraft,
} from "./workspace-draft";

const PROJECT_KEY = "vibio:project:draft";
export const WORKSPACE_DRAFT_KEY = "vibio:workspace:draft:v2";
const PROVIDER_KEY = "vibio:model:preference";
const API_KEY = "vibio:model:api-key";
const HISTORY_KEY = "vibio:runs";
export const AUTOMATION_CONFIG_KEY = "vibio:automation:config:v1";
export const ACTIVE_WORKFLOW_KEY = "vibio:automation:active:v1";
const HISTORY_LIMIT = 12;

const DEPRECATED_DEEPSEEK_MODELS = new Set(["deepseek-chat", "deepseek-reasoner"]);
const MODE_ID_SET = new Set<ModeId>(MODE_IDS);
const WORKFLOW_STATUS_SET = new Set<WorkflowStepStatus>([
  "pending",
  "running",
  "complete",
  "waiting",
  "skipped",
  "error",
]);

export interface SaveRunResult {
  runs: RunRecord[];
  persisted: boolean;
}

function readJson<T>(storage: Storage, key: string, fallback: T): T {
  try {
    const value = storage.getItem(key);
    return value ? (JSON.parse(value) as T) : fallback;
  } catch {
    return fallback;
  }
}

function readUnknownJson(storage: Storage, key: string): unknown | undefined {
  try {
    const value = storage.getItem(key);
    return value === null ? undefined : JSON.parse(value);
  } catch {
    return undefined;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function normalizeWorkflowStep(value: unknown): WorkflowStep | null {
  if (!isRecord(value) || !MODE_ID_SET.has(value.mode as ModeId)) return null;
  if (!WORKFLOW_STATUS_SET.has(value.status as WorkflowStepStatus)) return null;
  const inputModes = Array.isArray(value.inputModes)
    ? value.inputModes.filter(
        (mode): mode is ModeId => typeof mode === "string" && MODE_ID_SET.has(mode as ModeId),
      )
    : undefined;
  return {
    mode: value.mode as ModeId,
    status: value.status as WorkflowStepStatus,
    ...(typeof value.report === "string" ? { report: value.report } : {}),
    ...(typeof value.reason === "string" ? { reason: value.reason } : {}),
    ...(typeof value.createdAt === "string" ? { createdAt: value.createdAt } : {}),
    ...(inputModes?.length ? { inputModes } : {}),
  };
}

function normalizeActiveWorkflow(value: unknown): WorkflowExecutionSnapshot | null {
  if (
    !isRecord(value) ||
    value.schemaVersion !== 1 ||
    typeof value.signature !== "string" ||
    typeof value.coreSignature !== "string" ||
    typeof value.startedAt !== "string" ||
    typeof value.inspectionComplete !== "boolean" ||
    typeof value.maxPages !== "number" ||
    !Number.isInteger(value.maxPages) ||
    value.maxPages < 1 ||
    value.maxPages > 10 ||
    !Array.isArray(value.steps)
  ) return null;
  const steps = value.steps.map(normalizeWorkflowStep);
  if (steps.some((step) => step === null)) return null;
  return {
    schemaVersion: 1,
    signature: value.signature,
    coreSignature: value.coreSignature,
    startedAt: value.startedAt,
    inspectionComplete: value.inspectionComplete,
    maxPages: value.maxPages,
    ...(isRecord(value.auditReport) ? { auditReport: value.auditReport } : {}),
    steps: steps as WorkflowStep[],
    ...(typeof value.recordId === "string" ? { recordId: value.recordId } : {}),
  };
}

export function loadWorkspaceDraft(fallback: WorkspaceDraftV2): WorkspaceDraftV2 {
  try {
    const stored = normalizeWorkspaceDraft(
      readUnknownJson(localStorage, WORKSPACE_DRAFT_KEY),
      fallback,
    );
    if (stored) return stored;

    return migrateLegacyProject(readUnknownJson(localStorage, PROJECT_KEY), fallback);
  } catch {
    return migrateLegacyProject(undefined, fallback);
  }
}

export function saveWorkspaceDraft(draft: WorkspaceDraftV2): void {
  try {
    localStorage.setItem(WORKSPACE_DRAFT_KEY, JSON.stringify(draft));
  } catch {
    // Browser storage is optional; the active in-memory workspace remains usable.
  }
}

export function loadAutomationConfig(): AutomationConfig {
  try {
    return normalizeAutomationConfig(readUnknownJson(localStorage, AUTOMATION_CONFIG_KEY));
  } catch {
    return normalizeAutomationConfig(DEFAULT_AUTOMATION_CONFIG);
  }
}

export function saveAutomationConfig(config: AutomationConfig): void {
  try {
    localStorage.setItem(AUTOMATION_CONFIG_KEY, JSON.stringify(normalizeAutomationConfig(config)));
  } catch {
    // The active in-memory automation configuration remains usable.
  }
}

export function loadActiveWorkflow(): WorkflowExecutionSnapshot | null {
  try {
    return normalizeActiveWorkflow(readUnknownJson(sessionStorage, ACTIVE_WORKFLOW_KEY));
  } catch {
    return null;
  }
}

export function saveActiveWorkflow(snapshot: WorkflowExecutionSnapshot): void {
  try {
    const normalized = normalizeActiveWorkflow(snapshot);
    if (!normalized) return;
    sessionStorage.setItem(ACTIVE_WORKFLOW_KEY, JSON.stringify(normalized));
  } catch {
    // Workflow execution remains available in memory when session storage is unavailable.
  }
}

export function clearActiveWorkflow(): void {
  try {
    sessionStorage.removeItem(ACTIVE_WORKFLOW_KEY);
  } catch {
    // Clearing the in-memory execution is sufficient when session storage is unavailable.
  }
}

export function loadProject(fallback: ProjectInput): ProjectInput {
  try {
    return { ...fallback, ...readJson<Partial<ProjectInput>>(localStorage, PROJECT_KEY, {}) };
  } catch {
    return fallback;
  }
}

export function saveProject(project: ProjectInput): void {
  try {
    localStorage.setItem(PROJECT_KEY, JSON.stringify(project));
  } catch {
    // Browser storage is optional; the active in-memory project remains usable.
  }
}

export function loadModelSettings(defaults: ModelSettings): ModelSettings {
  try {
    const preference = readJson<Partial<ModelSettings>>(localStorage, PROVIDER_KEY, {});
    const provider = preference.provider ?? defaults.provider;
    const storedModel = preference.model ?? defaults.model;
    const model = provider === "deepseek" && DEPRECATED_DEEPSEEK_MODELS.has(storedModel)
      ? "deepseek-v4-flash"
      : storedModel;
    return {
      ...defaults,
      ...preference,
      provider,
      model,
      apiKey: sessionStorage.getItem(API_KEY) ?? "",
    };
  } catch {
    return defaults;
  }
}

export function saveModelSettings(settings: ModelSettings): void {
  try {
    localStorage.setItem(
      PROVIDER_KEY,
      JSON.stringify({ provider: settings.provider, model: settings.model }),
    );
    if (settings.apiKey) {
      sessionStorage.setItem(API_KEY, settings.apiKey);
    } else {
      sessionStorage.removeItem(API_KEY);
    }
  } catch {
    // Keep the key in React state when browser storage is unavailable.
  }
}

export function loadRuns(): RunRecord[] {
  try {
    return readJson<RunRecord[]>(localStorage, HISTORY_KEY, []);
  } catch {
    return [];
  }
}

export function saveRun(record: RunRecord): SaveRunResult {
  const next = [record, ...loadRuns().filter((item) => item.id !== record.id)].slice(
    0,
    HISTORY_LIMIT,
  );
  let candidate = next;
  while (candidate.length > 0) {
    try {
      localStorage.setItem(HISTORY_KEY, JSON.stringify(candidate));
      return { runs: candidate, persisted: true };
    } catch {
      if (candidate.length === 1) break;
      candidate = candidate.slice(0, -1);
    }
  }
  return { runs: next, persisted: false };
}

export function clearRuns(): void {
  try {
    localStorage.removeItem(HISTORY_KEY);
  } catch {
    // Clearing the in-memory state is sufficient when storage is unavailable.
  }
}
