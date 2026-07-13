import { describe, expect, it } from "vitest";

import {
  AUTOMATION_RECIPES,
  DEFAULT_AUTOMATION_CONFIG,
  buildAutomationGatingProject,
  buildAutomationPlan,
  buildAutomationProject,
  getAutomationEvidenceAvailability,
  getMissingAutomationEvidenceSources,
  normalizeAutomationConfig,
  resolveAutomationModes,
  selectAutomationEvidence,
} from "./automation";
import { EMPTY_PROJECT, EMPTY_WORKSPACE_DRAFT } from "./data";
import type { AutomationConfig } from "./automation";
import type { EvidenceFile, ProjectInput, WorkspaceDraftV2 } from "./types";

function project(overrides: Partial<ProjectInput> = {}): ProjectInput {
  return {
    ...EMPTY_PROJECT,
    projectName: "Vibio",
    market: "德国",
    language: "de-DE",
    conversion: "合格询盘",
    objective: "扩大自然搜索机会",
    ...overrides,
  };
}

function evidence(name: string, content: string, type = "text/csv"): EvidenceFile {
  return {
    id: name,
    name,
    type,
    size: content.length,
    content,
  };
}

function config(overrides: Partial<AutomationConfig> = {}): AutomationConfig {
  return {
    ...DEFAULT_AUTOMATION_CONFIG,
    selectedModes: [...DEFAULT_AUTOMATION_CONFIG.selectedModes],
    evidenceSources: [...DEFAULT_AUTOMATION_CONFIG.evidenceSources],
    ...overrides,
  };
}

describe("automation recipes and normalization", () => {
  it("defines the four supported recipes and a safe approval-first default", () => {
    expect(AUTOMATION_RECIPES.map((recipe) => recipe.id)).toEqual([
      "growth",
      "recovery",
      "technical",
      "content",
    ]);
    expect(DEFAULT_AUTOMATION_CONFIG).toMatchObject({
      schemaVersion: 1,
      recipe: "growth",
      advanceMode: "approval",
    });
  });

  it("deduplicates supported values and filters unknown values", () => {
    const normalized = normalizeAutomationConfig({
      schemaVersion: 99,
      objective: "  修复产品目录  ",
      recipe: "technical",
      selectedModes: ["fix", "fix", "review", "unknown"],
      evidenceSources: ["site", "site", "gsc", "unknown"],
      advanceMode: "continuous",
    });

    expect(normalized).toEqual({
      schemaVersion: 1,
      objective: "修复产品目录",
      recipe: "technical",
      selectedModes: ["fix", "review"],
      evidenceSources: ["site", "gsc"],
      advanceMode: "continuous",
    });
  });

  it("uses the selected recipe defaults when mode and evidence lists are omitted", () => {
    const normalized = normalizeAutomationConfig({ recipe: "recovery" });
    const recipe = AUTOMATION_RECIPES.find((item) => item.id === "recovery");

    expect(normalized.selectedModes).toEqual(recipe?.modes);
    expect(normalized.evidenceSources).toEqual(recipe?.evidenceSources);
  });
});

describe("resolveAutomationModes", () => {
  it("adds transitive dependencies and returns the canonical automation order", () => {
    expect(resolveAutomationModes(["write", "fix", "review"])).toEqual([
      "audit",
      "keyword",
      "fix",
      "write",
      "review",
    ]);
  });

  it("does not invent an implementation dependency for a standalone review", () => {
    expect(resolveAutomationModes(["review"])).toEqual(["review"]);
  });
});

describe("buildAutomationPlan", () => {
  it("filters to resolved modes, puts recovery first, and reuses recovery gating", () => {
    const steps = buildAutomationPlan(
      config({ selectedModes: ["recover", "fix"] }),
      project({ objective: "自然搜索点击从 7 月开始骤降" }),
    );

    expect(steps.map((step) => step.mode)).toEqual(["recover", "audit", "fix"]);
    expect(steps[0]).toEqual({ mode: "recover", status: "pending" });
  });

  it("keeps recovery skipped and review waiting when their existing gates have no evidence", () => {
    const steps = buildAutomationPlan(
      config({ selectedModes: ["recover", "review"] }),
      project(),
      [],
      project(),
    );

    expect(steps.map((step) => step.mode)).toEqual(["recover", "review"]);
    expect(steps.find((step) => step.mode === "recover")?.status).toBe("skipped");
    expect(steps.find((step) => step.mode === "review")?.status).toBe("waiting");
    expect(steps.find((step) => step.mode === "review")?.reason).toContain("等待已上线变更");
  });

  it("enables review when a deployed change is explicitly provided", () => {
    const steps = buildAutomationPlan(
      config({ selectedModes: ["review"] }),
      project(),
      [],
      project({ details: "模板修复已于 2026-07-01 上线" }),
    );

    expect(steps).toEqual([{ mode: "review", status: "pending" }]);
  });
});

describe("buildAutomationGatingProject", () => {
  it("uses the single automation objective when deciding whether recovery is relevant", () => {
    const input: WorkspaceDraftV2 = {
      ...EMPTY_WORKSPACE_DRAFT,
      profile: { ...EMPTY_WORKSPACE_DRAFT.profile },
      modes: Object.fromEntries(
        Object.entries(EMPTY_WORKSPACE_DRAFT.modes).map(([mode, value]) => [mode, { ...value }]),
      ) as WorkspaceDraftV2["modes"],
    };
    const automationConfig = config({
      objective: "GSC 点击和自然流量从 7 月开始骤降",
      selectedModes: ["recover"],
    });

    expect(buildAutomationPlan(
      automationConfig,
      buildAutomationGatingProject(input, automationConfig),
    )).toEqual([{ mode: "recover", status: "pending" }]);
  });

  it("does not let hidden review text trigger the recovery gate", () => {
    const input: WorkspaceDraftV2 = {
      ...EMPTY_WORKSPACE_DRAFT,
      profile: { ...EMPTY_WORKSPACE_DRAFT.profile, primaryGoal: "建立增长基线" },
      modes: Object.fromEntries(
        Object.entries(EMPTY_WORKSPACE_DRAFT.modes).map(([mode, value]) => [mode, { ...value }]),
      ) as WorkspaceDraftV2["modes"],
    };
    input.modes.review.objective = "复盘上个月的自然流量骤降";
    const automationConfig = config({ objective: "", selectedModes: ["recover"] });

    expect(buildAutomationPlan(
      automationConfig,
      buildAutomationGatingProject(input, automationConfig),
    )[0].status).toBe("skipped");
  });
});

describe("automation evidence sources", () => {
  it("detects site access, populated files, specialized exports, and deployment records", () => {
    const inputEvidence = [
      evidence("gsc-export.csv", "page,clicks,impressions\n/products,10,100"),
      evidence("ga4-landing.csv", "landing_page,sessions,conversions\n/products,12,2"),
      evidence("crm-cohort.csv", "landing_page,qualified_leads,revenue\n/products,2,100"),
      evidence("changelog.md", "修复已于 2026-07-01 上线", "text/markdown"),
    ];
    const availability = getAutomationEvidenceAvailability(
      project({ siteUrl: "https://example.com", allowNetworkEvidence: true }),
      inputEvidence,
    );

    expect(availability).toEqual({
      site: true,
      files: true,
      gsc: true,
      ga4: true,
      crm: true,
      deployment: true,
    });
  });

  it("reports selected sources that are not currently available", () => {
    const missing = getMissingAutomationEvidenceSources(
      config({ evidenceSources: ["site", "files", "gsc"] }),
      project({ siteUrl: "https://example.com", allowNetworkEvidence: false }),
      [evidence("empty.csv", "")],
    );

    expect(missing).toEqual(["site", "files", "gsc"]);
  });

  it("only sends files from evidence sources selected for the workflow", () => {
    const inputEvidence = [
      evidence("gsc-export.csv", "page,clicks,impressions\n/products,10,100"),
      evidence("ga4-landing.csv", "landing_page,sessions,conversions\n/products,12,2"),
      evidence("crm-cohort.csv", "landing_page,qualified_leads\n/products,2"),
      evidence("research-notes.md", "Verified product facts", "text/markdown"),
    ];

    expect(selectAutomationEvidence(
      config({ evidenceSources: ["site", "gsc", "crm"] }),
      inputEvidence,
    ).map((file) => file.name)).toEqual(["gsc-export.csv", "crm-cohort.csv"]);
    expect(selectAutomationEvidence(
      config({ evidenceSources: ["files"] }),
      inputEvidence,
    ).map((file) => file.name)).toEqual(inputEvidence.map((file) => file.name));
    expect(selectAutomationEvidence(
      config({ evidenceSources: ["site"] }),
      inputEvidence,
    )).toEqual([]);
  });
});

describe("buildAutomationProject", () => {
  function draft(): WorkspaceDraftV2 {
    return {
      ...EMPTY_WORKSPACE_DRAFT,
      profile: {
        ...EMPTY_WORKSPACE_DRAFT.profile,
        projectName: "Vibio",
        market: "德国",
        language: "de-DE",
        conversion: "合格询盘",
        primaryGoal: "项目资料中的目标",
      },
      modes: Object.fromEntries(
        Object.entries(EMPTY_WORKSPACE_DRAFT.modes).map(([mode, value]) => [mode, { ...value }]),
      ) as WorkspaceDraftV2["modes"],
    };
  }

  it("prefers mode-specific fields over the automation objective", () => {
    const input = draft();
    input.modes.audit = {
      objective: "确认产品页索引问题",
      details: "最近曝光下降",
      scope: "/products/",
      timing: "本周",
    };

    expect(buildAutomationProject(input, "audit", config({ objective: "自动化总目标" }))).toMatchObject({
      objective: "确认产品页索引问题",
      details: "本模式补充信息：\n最近曝光下降",
      scope: "/products/",
      decisionWindow: "本周",
    });
  });

  it("falls back to the automation objective before the project primary goal", () => {
    const input = draft();

    expect(buildAutomationProject(input, "audit", config({ objective: "自动化总目标" })).objective)
      .toBe("自动化总目标");
    expect(buildAutomationProject(input, "audit", config({ objective: "" })).objective)
      .toBe("项目资料中的目标");
  });
});
