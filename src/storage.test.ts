import { afterEach, describe, expect, it, vi } from "vitest";

import { EMPTY_WORKSPACE_DRAFT } from "./data";
import type { AutomationConfig } from "./automation";
import {
  ACTIVE_WORKFLOW_KEY,
  AUTOMATION_CONFIG_KEY,
  clearActiveWorkflow,
  loadActiveWorkflow,
  loadAutomationConfig,
  loadModelSettings,
  loadWorkspaceDraft,
  saveAutomationConfig,
  saveActiveWorkflow,
  saveRun,
  saveWorkspaceDraft,
  WORKSPACE_DRAFT_KEY,
} from "./storage";
import type { RunRecord, WorkflowExecutionSnapshot } from "./types";
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

describe("automation config storage", () => {
  it("normalizes and persists automation settings under their own key", () => {
    const workspaceValue = JSON.stringify({ sentinel: "workspace stays untouched" });
    const local = memoryStorage({ [WORKSPACE_DRAFT_KEY]: workspaceValue });
    vi.stubGlobal("localStorage", local);

    saveAutomationConfig({
      schemaVersion: 1,
      objective: "  修复产品目录  ",
      recipe: "technical",
      selectedModes: ["fix", "fix", "review"],
      evidenceSources: ["site", "site", "deployment"],
      advanceMode: "continuous",
    });

    expect(JSON.parse(local.getItem(AUTOMATION_CONFIG_KEY) ?? "{}")).toEqual({
      schemaVersion: 1,
      objective: "修复产品目录",
      recipe: "technical",
      selectedModes: ["fix", "review"],
      evidenceSources: ["site", "deployment"],
      advanceMode: "continuous",
    });
    expect(loadAutomationConfig()).toEqual({
      schemaVersion: 1,
      objective: "修复产品目录",
      recipe: "technical",
      selectedModes: ["fix", "review"],
      evidenceSources: ["site", "deployment"],
      advanceMode: "continuous",
    });
    expect(local.getItem(WORKSPACE_DRAFT_KEY)).toBe(workspaceValue);
  });

  it("does not persist API keys or integration secrets from an untrusted config object", () => {
    const local = memoryStorage();
    vi.stubGlobal("localStorage", local);
    const untrustedConfig: AutomationConfig & {
      apiKey: string;
      integrationTokens: Record<string, string>;
    } = {
      schemaVersion: 1,
      objective: "运行自动审计",
      recipe: "growth",
      selectedModes: ["audit", "fix"],
      evidenceSources: ["site", "gsc"],
      advanceMode: "approval",
      apiKey: "sk-should-not-be-saved",
      integrationTokens: { gsc: "oauth-secret" },
    };

    saveAutomationConfig(untrustedConfig);

    const persisted = local.getItem(AUTOMATION_CONFIG_KEY) ?? "";
    expect(persisted).not.toContain("sk-should-not-be-saved");
    expect(persisted).not.toContain("oauth-secret");
    expect(JSON.parse(persisted)).toEqual({
      schemaVersion: 1,
      objective: "运行自动审计",
      recipe: "growth",
      selectedModes: ["audit", "fix"],
      evidenceSources: ["site", "gsc"],
      advanceMode: "approval",
    });
  });
});

describe("active workflow session storage", () => {
  it("restores a validated stage snapshot without persisting credentials", () => {
    const session = memoryStorage();
    vi.stubGlobal("sessionStorage", session);
    const snapshot: WorkflowExecutionSnapshot & { apiKey: string } = {
      schemaVersion: 1,
      signature: "full-signature",
      coreSignature: "core-signature",
      startedAt: "2026-07-13T08:00:00Z",
      inspectionComplete: true,
      maxPages: 6,
      auditReport: { evidence_status: "available" },
      steps: [
        { mode: "audit", status: "complete", report: "# Audit" },
        { mode: "fix", status: "pending", inputModes: ["audit"] },
      ],
      apiKey: "sk-must-not-persist",
    };

    saveActiveWorkflow(snapshot);

    const persisted = session.getItem(ACTIVE_WORKFLOW_KEY) ?? "";
    expect(persisted).not.toContain("sk-must-not-persist");
    expect(loadActiveWorkflow()).toEqual({
      schemaVersion: 1,
      signature: "full-signature",
      coreSignature: "core-signature",
      startedAt: "2026-07-13T08:00:00Z",
      inspectionComplete: true,
      maxPages: 6,
      auditReport: { evidence_status: "available" },
      steps: [
        { mode: "audit", status: "complete", report: "# Audit" },
        { mode: "fix", status: "pending", inputModes: ["audit"] },
      ],
    });

    clearActiveWorkflow();
    expect(loadActiveWorkflow()).toBeNull();
  });

  it("rejects malformed workflow snapshots", () => {
    vi.stubGlobal("sessionStorage", memoryStorage({
      [ACTIVE_WORKFLOW_KEY]: JSON.stringify({
        schemaVersion: 1,
        signature: "x",
        coreSignature: "y",
        startedAt: "invalid",
        inspectionComplete: true,
        maxPages: 999,
        steps: [{ mode: "unknown", status: "complete" }],
      }),
    }));

    expect(loadActiveWorkflow()).toBeNull();
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
