import { afterEach, describe, expect, it, vi } from "vitest";

import { EMPTY_WORKSPACE_DRAFT } from "./data";
import {
  loadModelSettings,
  loadWorkspaceDraft,
  saveRun,
  saveWorkspaceDraft,
  WORKSPACE_DRAFT_KEY,
} from "./storage";
import type { RunRecord } from "./types";
import { createEmptyWorkspaceDraft } from "./workspace-draft";

const LEGACY_PROJECT_KEY = "vibio:project:draft";

function run(id: string): RunRecord {
  return {
    id,
    mode: "audit",
    projectName: "Vibio",
    siteUrl: "https://example.com",
    market: "DE",
    language: "de-DE",
    objective: "Audit",
    provider: "deepseek",
    model: "deepseek-v4-flash",
    report: `# ${id}`,
    evidence: [],
    createdAt: "2026-07-13T08:00:00Z",
  };
}

function storage(initialRuns: RunRecord[], write: (value: string) => void): Storage {
  let value = JSON.stringify(initialRuns);
  return {
    get length() { return value ? 1 : 0; },
    clear() { value = ""; },
    getItem(key) { return key === "vibio:runs" ? value : null; },
    key(index) { return index === 0 && value ? "vibio:runs" : null; },
    removeItem(key) { if (key === "vibio:runs") value = ""; },
    setItem(key, next) {
      if (key !== "vibio:runs") return;
      write(next);
      value = next;
    },
  };
}

function memoryStorage(initial: Record<string, string> = {}): Storage {
  const values = new Map(Object.entries(initial));
  return {
    get length() { return values.size; },
    clear() { values.clear(); },
    getItem(key) { return values.get(key) ?? null; },
    key(index) { return [...values.keys()][index] ?? null; },
    removeItem(key) { values.delete(key); },
    setItem(key, value) { values.set(key, value); },
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("saveRun", () => {
  it("evicts the oldest history entries until the browser accepts the write", () => {
    const local = storage([run("old-1"), run("old-2"), run("old-3")], (value) => {
      if ((JSON.parse(value) as unknown[]).length > 2) throw new DOMException("quota");
    });
    vi.stubGlobal("localStorage", local);

    const result = saveRun(run("new"));

    expect(result.persisted).toBe(true);
    expect(result.runs.map((item) => item.id)).toEqual(["new", "old-1"]);
  });

  it("reports when even the current record cannot be persisted", () => {
    vi.stubGlobal("localStorage", storage([], () => { throw new DOMException("quota"); }));

    const result = saveRun(run("new"));

    expect(result.persisted).toBe(false);
    expect(result.runs.map((item) => item.id)).toEqual(["new"]);
  });
});

describe("workspace draft storage", () => {
  it("prefers a valid v2 workspace over the legacy project", () => {
    const current = createEmptyWorkspaceDraft();
    current.profile.projectName = "V2 workspace";
    const local = memoryStorage({
      [WORKSPACE_DRAFT_KEY]: JSON.stringify(current),
      [LEGACY_PROJECT_KEY]: JSON.stringify({ projectName: "Legacy project" }),
    });
    vi.stubGlobal("localStorage", local);

    const loaded = loadWorkspaceDraft(EMPTY_WORKSPACE_DRAFT);

    expect(loaded.profile.projectName).toBe("V2 workspace");
    expect(loaded.sharedContext).toBe("");
  });

  it.each([
    ["malformed JSON", "{not-json"],
    ["invalid schema", JSON.stringify({ schemaVersion: 1, profile: {}, modes: {} })],
  ])("falls back to and migrates the legacy project for %s", (_case, invalidV2) => {
    const local = memoryStorage({
      [WORKSPACE_DRAFT_KEY]: invalidV2,
      [LEGACY_PROJECT_KEY]: JSON.stringify({
        projectName: "Legacy project",
        objective: "找出当前增长瓶颈",
        details: "旧表单没有保存所属模式",
      }),
    });
    vi.stubGlobal("localStorage", local);

    const loaded = loadWorkspaceDraft(EMPTY_WORKSPACE_DRAFT);

    expect(loaded.profile.projectName).toBe("Legacy project");
    expect(loaded.sharedContext).toContain("当前目标 / 问题：\n找出当前增长瓶颈");
    expect(loaded.sharedContext).toContain("旧版补充信息：\n旧表单没有保存所属模式");
    expect(Object.values(loaded.modes).every((mode) => mode.objective === "")).toBe(true);
  });

  it("writes only the v2 key and leaves the legacy project untouched", () => {
    const legacyValue = JSON.stringify({ projectName: "Legacy project" });
    const local = memoryStorage({ [LEGACY_PROJECT_KEY]: legacyValue });
    vi.stubGlobal("localStorage", local);
    const current = createEmptyWorkspaceDraft();
    current.profile.projectName = "Current workspace";

    saveWorkspaceDraft(current);

    expect(JSON.parse(local.getItem(WORKSPACE_DRAFT_KEY) ?? "{}").profile.projectName).toBe(
      "Current workspace",
    );
    expect(local.getItem(LEGACY_PROJECT_KEY)).toBe(legacyValue);
  });
});

describe("model settings storage", () => {
  it.each(["deepseek-chat", "deepseek-reasoner"])(
    "migrates deprecated DeepSeek model %s to V4 Flash",
    (deprecatedModel) => {
      vi.stubGlobal("localStorage", memoryStorage({
        "vibio:model:preference": JSON.stringify({
          provider: "deepseek",
          model: deprecatedModel,
        }),
      }));
      vi.stubGlobal("sessionStorage", memoryStorage());

      expect(loadModelSettings({
        provider: "deepseek",
        model: "deepseek-v4-flash",
        apiKey: "",
      })).toMatchObject({
        provider: "deepseek",
        model: "deepseek-v4-flash",
      });
    },
  );
});
