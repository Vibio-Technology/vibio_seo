import { describe, expect, it } from "vitest";

import { EMPTY_PROJECT } from "./data";
import type { EvidenceFile, ProjectInput, WorkflowStep } from "./types";
import {
  MAX_WORKFLOW_REPORT_JSON_BYTES,
  WORKFLOW_MODE_ORDER,
  aggregateWorkflowMarkdown,
  buildWorkflowContext,
  buildWorkflowPlan,
} from "./workflow";

function project(overrides: Partial<ProjectInput> = {}): ProjectInput {
  return {
    ...EMPTY_PROJECT,
    projectName: "Vibio 德国站",
    market: "德国",
    language: "de-DE",
    conversion: "合格 RFQ",
    objective: "建立 SEO 工作计划",
    ...overrides,
  };
}

function evidence(name: string, content = "", type = "text/plain"): EvidenceFile {
  return {
    id: name,
    name,
    type,
    size: content.length,
    content,
  };
}

describe("buildWorkflowPlan", () => {
  it("uses the fixed dependency order and gates recover and review when evidence is absent", () => {
    const steps = buildWorkflowPlan(project());

    expect(steps.map((step) => step.mode)).toEqual(WORKFLOW_MODE_ORDER);
    expect(steps.find((step) => step.mode === "recover")).toMatchObject({
      status: "skipped",
      reason: expect.stringContaining("下滑"),
    });
    expect(steps.find((step) => step.mode === "review")).toMatchObject({
      status: "skipped",
      reason: expect.stringContaining("等待已上线变更"),
    });
    expect(
      steps
        .filter((step) => !["recover", "review"].includes(step.mode))
        .every((step) => step.status === "pending"),
    ).toBe(true);
  });

  it.each([
    ["project", project({ objective: "GSC 点击和自然流量从 6 月开始骤降" }), []],
    ["evidence", project(), [evidence("index-note.md", "大量产品页出现索引异常")]],
  ])("enables recover for an explicit %s signal", (_source, inputProject, inputEvidence) => {
    const recover = buildWorkflowPlan(inputProject, inputEvidence).find(
      (step) => step.mode === "recover",
    );

    expect(recover).toEqual({ mode: "recover", status: "pending" });
  });

  it("does not treat a negated recovery incident as an active signal", () => {
    const recover = buildWorkflowPlan(
      project({ details: "检查完成，没有自然搜索流量下滑或索引异常。" }),
    ).find((step) => step.mode === "recover");

    expect(recover?.status).toBe("skipped");
  });

  it("does not treat prevention language as an observed recovery incident", () => {
    const recover = buildWorkflowPlan(
      project({ objective: "制定防止自然搜索流量下降的年度计划" }),
    ).find((step) => step.mode === "recover");

    expect(recover?.status).toBe("skipped");
  });

  it("does not treat a hypothetical decline question as an observed incident", () => {
    const recover = buildWorkflowPlan(
      project({ objective: "如果自然搜索流量下降，应该如何处理？" }),
    ).find((step) => step.mode === "recover");

    expect(recover?.status).toBe("skipped");
  });

  it("does not enable recovery from an empty incident-shaped file", () => {
    const recover = buildWorkflowPlan(project(), [evidence("organic-traffic-drop.csv")]).find(
      (step) => step.mode === "recover",
    );

    expect(recover?.status).toBe("skipped");
  });

  it.each([
    ["deployed change", project({ details: "模板修复已于 2026-07-01 上线" }), []],
    ["measurement evidence", project(), [evidence("gsc-before-after.csv", "page,clicks,impressions")]],
    ["experiment evidence", project(), [evidence("holdout-experiment.json", "{\"result\":\"ready\"}")]],
  ])("enables review when %s is available", (_source, inputProject, inputEvidence) => {
    const review = buildWorkflowPlan(inputProject, inputEvidence).find(
      (step) => step.mode === "review",
    );

    expect(review).toEqual({ mode: "review", status: "pending" });
  });

  it("does not enable review from an empty measurement-shaped file", () => {
    const review = buildWorkflowPlan(project(), [evidence("gsc-before-after.csv")]).find(
      (step) => step.mode === "review",
    );

    expect(review?.status).toBe("skipped");
  });

  it("does not enable review for a planned observation window without results", () => {
    const review = buildWorkflowPlan(
      project({ decisionWindow: "计划建立基线窗口和观察期" }),
    ).find((step) => step.mode === "review");

    expect(review?.status).toBe("skipped");
  });

  it.each([
    "计划下月上线模板修复并建立观察期",
    "计划接入 GSC 数据后做复盘",
  ])("does not enable review for future-only intent: %s", (details) => {
    const review = buildWorkflowPlan(project({ details })).find(
      (step) => step.mode === "review",
    );

    expect(review?.status).toBe("skipped");
  });
});

describe("buildWorkflowContext", () => {
  it("keeps only the three most recent completed reports and marks truncation", () => {
    const oversized = "💡".repeat(MAX_WORKFLOW_REPORT_JSON_BYTES);
    const steps: WorkflowStep[] = [
      { mode: "audit", status: "complete", report: "audit report" },
      { mode: "recover", status: "skipped", report: "must not be included" },
      { mode: "keyword", status: "complete", report: "keyword report" },
      { mode: "plan", status: "error", report: "must not be included" },
      { mode: "fix", status: "complete", report: "fix report" },
      { mode: "write", status: "running", report: "must not be included" },
      { mode: "link", status: "complete", report: oversized, createdAt: "2026-07-13T10:00:00Z" },
    ];

    const context = buildWorkflowContext(steps);

    expect(context.schemaVersion).toBe("vibio-web.workflow-context.v1");
    expect(context.completedReports.map((item) => item.mode)).toEqual(["keyword", "fix", "link"]);
    expect(context.completedReports[0]).toMatchObject({ truncated: false, report: "keyword report" });
    expect(context.completedReports[2]).toMatchObject({
      truncated: true,
      createdAt: "2026-07-13T10:00:00Z",
    });
    expect(
      new TextEncoder().encode(JSON.stringify(context.completedReports[2].report)).byteLength,
    ).toBeLessThanOrEqual(MAX_WORKFLOW_REPORT_JSON_BYTES);
    expect(new TextEncoder().encode(JSON.stringify(context)).byteLength).toBeLessThan(192 * 1024);
    expect(JSON.stringify(context)).not.toContain("must not be included");
    expect(JSON.stringify(context)).not.toContain("audit report");
  });

  it("keeps three multi-byte reports below the server context byte limit", () => {
    const report = "💡\n".repeat(MAX_WORKFLOW_REPORT_JSON_BYTES);
    const context = buildWorkflowContext([
      { mode: "audit", status: "complete", report },
      { mode: "keyword", status: "complete", report },
      { mode: "plan", status: "complete", report },
    ]);

    expect(context.completedReports).toHaveLength(3);
    expect(context.completedReports.every((item) => item.truncated)).toBe(true);
    expect(new TextEncoder().encode(JSON.stringify(context)).byteLength).toBeLessThan(192 * 1024);
  });
});

describe("aggregateWorkflowMarkdown", () => {
  it("combines reports, statuses, reasons, and project metadata into one document", () => {
    const markdown = aggregateWorkflowMarkdown(
      project({ siteUrl: "https://example.com" }),
      [
        {
          mode: "audit",
          status: "complete",
          report: "## 审计结论\n\n发现 canonical 冲突。",
          createdAt: "2026-07-13T09:00:00Z",
        },
        { mode: "recover", status: "skipped", reason: "没有下滑信号。" },
        { mode: "keyword", status: "running" },
        { mode: "plan", status: "pending" },
        { mode: "fix", status: "error", reason: "模型服务暂不可用。" },
      ],
    );

    expect(markdown).toContain("# Vibio 德国站 SEO 全流程报告");
    expect(markdown).toContain("- 站点：https://example.com");
    expect(markdown).toContain("- 已完成：1");
    expect(markdown).toContain("- 运行中：1");
    expect(markdown).toContain("- 待运行：1");
    expect(markdown).toContain("- 已跳过：1");
    expect(markdown).toContain("- 失败：1");
    expect(markdown).toContain("### 01 审计（AUDIT）");
    expect(markdown).toContain("发现 canonical 冲突。");
    expect(markdown).toContain("- 说明：没有下滑信号。");
    expect(markdown).toContain("- 说明：模型服务暂不可用。");
    expect(markdown).toContain("- 完成时间：2026-07-13T09:00:00Z");
  });
});
