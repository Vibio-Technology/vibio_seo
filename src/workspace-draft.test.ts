import { afterEach, describe, expect, it, vi } from "vitest";

import { EMPTY_WORKSPACE_DRAFT } from "./data";
import {
  loadWorkspaceDraft,
  saveWorkspaceDraft,
  WORKSPACE_DRAFT_KEY,
} from "./storage";
import {
  buildAnalysisProject,
  buildWorkflowGatingProject,
  createEmptyWorkspaceDraft,
  migrateLegacyProject,
  normalizeWorkspaceDraft,
} from "./workspace-draft";

const LEGACY_KEY = "vibio:project:draft";

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

describe("workspace draft construction", () => {
  it("creates independent mode objects", () => {
    const first = createEmptyWorkspaceDraft();
    const second = createEmptyWorkspaceDraft();

    first.modes.audit.objective = "只修改第一份";

    expect(second.modes.audit.objective).toBe("");
    expect(first.modes.audit).not.toBe(first.modes.plan);
  });

  it("builds a flat analysis payload with primary-goal fallback and shared context", () => {
    const draft = createEmptyWorkspaceDraft();
    draft.profile = {
      ...draft.profile,
      projectName: "Vibio 德国站",
      market: "德国",
      language: "de-DE",
      conversion: "合格 RFQ",
      primaryGoal: "增加合格询盘",
    };
    draft.sharedContext = "CRM 暂未按落地页归因";
    draft.modes.audit = {
      objective: " ",
      details: "产品页曝光很少",
      scope: "/products/",
      timing: "近三个月",
    };

    const project = buildAnalysisProject(draft, "audit");

    expect(project.objective).toBe("增加合格询盘");
    expect(project.scope).toBe("/products/");
    expect(project.decisionWindow).toBe("近三个月");
    expect(project.details).toContain("产品页曝光很少");
    expect(project.details).toContain("CRM 暂未按落地页归因");
    expect(project.primaryGoal).toBe("增加合格询盘");
  });

  it("uses only recover and review task text for workflow gating", () => {
    const draft = createEmptyWorkspaceDraft();
    draft.modes.keyword.objective = "自然流量从 6 月开始骤降";
    draft.modes.recover.objective = "产品目录索引从 7 月开始下降";
    draft.modes.review.timing = "模板修复于 2026-07-01 上线";
    draft.sharedContext = "使用 GSC 导出对比";

    const projectText = JSON.stringify(buildWorkflowGatingProject(draft));

    expect(projectText).toContain("产品目录索引");
    expect(projectText).toContain("2026-07-01");
    expect(projectText).toContain("GSC 导出");
    expect(projectText).not.toContain("自然流量从 6 月开始骤降");
  });
});

describe("workspace draft migration", () => {
  it("moves legacy profile fields and preserves ambiguous task text as shared context", () => {
    const migrated = migrateLegacyProject({
      projectName: "Legacy",
      siteUrl: "https://example.com",
      market: "DE",
      language: "de-DE",
      conversion: "RFQ",
      audience: "Engineer",
      businessModel: "B2B",
      capacity: "SEO 1",
      objective: "找出增长瓶颈",
      scope: "/products/",
      details: "旧表单不记录当前模式",
      decisionWindow: "Q3",
      allowNetworkEvidence: false,
      allowStateDraft: true,
    });

    expect(migrated.profile).toMatchObject({
      projectName: "Legacy",
      siteUrl: "https://example.com",
      primaryGoal: "",
      allowNetworkEvidence: false,
    });
    expect(migrated.sharedContext).toContain("当前目标 / 问题：\n找出增长瓶颈");
    expect(migrated.sharedContext).toContain("分析范围：\n/products/");
    expect(migrated.sharedContext).toContain("旧版补充信息");
    expect(migrated.sharedContext).toContain("决策 / 观察窗口：\nQ3");
    expect(Object.values(migrated.modes).every((mode) => mode.objective === "")).toBe(true);
  });

  it("normalizes v2 fields by type and discards unknown data", () => {
    const normalized = normalizeWorkspaceDraft({
      schemaVersion: 2,
      profile: {
        projectName: "Vibio",
        market: 42,
        allowNetworkEvidence: false,
        unknown: "discard me",
      },
      modes: {
        audit: { objective: "审计产品页", details: 99, unknown: "discard me" },
        invented: { objective: "discard me" },
      },
      sharedContext: "共享背景",
      unknown: "discard me",
    });

    expect(normalized).not.toBeNull();
    expect(normalized?.profile.projectName).toBe("Vibio");
    expect(normalized?.profile.market).toBe("");
    expect(normalized?.profile.allowNetworkEvidence).toBe(false);
    expect(normalized?.modes.audit).toEqual({
      objective: "审计产品页",
      details: "",
      scope: "",
      timing: "",
    });
    expect(normalized?.modes.plan).toEqual({
      objective: "",
      details: "",
      scope: "",
      timing: "",
    });
    expect(normalized).not.toHaveProperty("unknown");
  });
});

describe("workspace draft storage", () => {
  it("prefers a valid v2 draft over the legacy key", () => {
    const v2 = createEmptyWorkspaceDraft();
    v2.profile.projectName = "V2";
    vi.stubGlobal("localStorage", memoryStorage({
      [WORKSPACE_DRAFT_KEY]: JSON.stringify(v2),
      [LEGACY_KEY]: JSON.stringify({ projectName: "Legacy" }),
    }));

    expect(loadWorkspaceDraft(EMPTY_WORKSPACE_DRAFT).profile.projectName).toBe("V2");
  });

  it("falls back to a legacy migration when v2 data is invalid", () => {
    vi.stubGlobal("localStorage", memoryStorage({
      [WORKSPACE_DRAFT_KEY]: JSON.stringify({ schemaVersion: 1 }),
      [LEGACY_KEY]: JSON.stringify({
        projectName: "Legacy",
        objective: "保留旧目标",
      }),
    }));

    const loaded = loadWorkspaceDraft(EMPTY_WORKSPACE_DRAFT);

    expect(loaded.profile.projectName).toBe("Legacy");
    expect(loaded.sharedContext).toContain("保留旧目标");
  });

  it("writes only the v2 key and leaves legacy data available for rollback", () => {
    const local = memoryStorage({ [LEGACY_KEY]: JSON.stringify({ projectName: "Legacy" }) });
    vi.stubGlobal("localStorage", local);
    const draft = createEmptyWorkspaceDraft();
    draft.profile.projectName = "Current";

    saveWorkspaceDraft(draft);

    expect(JSON.parse(local.getItem(WORKSPACE_DRAFT_KEY) ?? "{}").profile.projectName).toBe("Current");
    expect(local.getItem(LEGACY_KEY)).not.toBeNull();
  });
});
