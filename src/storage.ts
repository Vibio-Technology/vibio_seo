import type { ModelSettings, ProjectInput, RunRecord } from "./types";

const PROJECT_KEY = "vibio:project:draft";
const PROVIDER_KEY = "vibio:model:preference";
const API_KEY = "vibio:model:api-key";
const HISTORY_KEY = "vibio:runs";
const HISTORY_LIMIT = 12;

function readJson<T>(storage: Storage, key: string, fallback: T): T {
  try {
    const value = storage.getItem(key);
    return value ? (JSON.parse(value) as T) : fallback;
  } catch {
    return fallback;
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

export function saveRun(record: RunRecord): RunRecord[] {
  const next = [record, ...loadRuns().filter((item) => item.id !== record.id)].slice(
    0,
    HISTORY_LIMIT,
  );
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(next));
  } catch {
    // The returned in-memory history still includes the completed run.
  }
  return next;
}

export function clearRuns(): void {
  try {
    localStorage.removeItem(HISTORY_KEY);
  } catch {
    // Clearing the in-memory state is sufficient when storage is unavailable.
  }
}
