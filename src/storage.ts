import type { ModelSettings, ProjectInput, RunRecord, WorkspaceDraftV2 } from "./types";
import {
  migrateLegacyProject,
  normalizeWorkspaceDraft,
} from "./workspace-draft";

const PROJECT_KEY = "vibio:project:draft";
export const WORKSPACE_DRAFT_KEY = "vibio:workspace:draft:v2";
const PROVIDER_KEY = "vibio:model:preference";
const API_KEY = "vibio:model:api-key";
const HISTORY_KEY = "vibio:runs";
const HISTORY_LIMIT = 12;

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
    return {
      ...defaults,
      ...preference,
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
