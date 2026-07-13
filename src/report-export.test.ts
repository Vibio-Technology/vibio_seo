import { describe, expect, it } from "vitest";

import { buildStandaloneReportHtml } from "./report-export";
import type { RunRecord } from "./types";

const record: RunRecord = {
  id: "run-1",
  mode: "audit",
  projectName: "Vibio <测试>",
  siteUrl: "https://example.com?a=1&b=2",
  market: "德国",
  language: "de-DE",
  objective: "验证 <canonical>",
  provider: "deepseek",
  model: "deepseek-v4-pro",
  report: "# 报告",
  evidence: [],
  createdAt: "2026-07-13T08:00:00Z",
};

describe("buildStandaloneReportHtml", () => {
  it("exports a self-contained report with escaped record metadata", () => {
    const html = buildStandaloneReportHtml(
      record,
      '<div class="audit-overview">审计概览</div>',
      "<h1>模型报告</h1>",
    );

    expect(html).toContain("<!doctype html>");
    expect(html).toContain("Vibio &lt;测试&gt;");
    expect(html).toContain("验证 &lt;canonical&gt;");
    expect(html).toContain("https://example.com?a=1&amp;b=2");
    expect(html).toContain("审计概览");
    expect(html).toContain("<h1>模型报告</h1>");
    expect(html).toContain("Content-Security-Policy");
  });

  it("omits the overview section when deterministic evidence is unavailable", () => {
    const html = buildStandaloneReportHtml(record, "", "<p>报告</p>");

    expect(html).not.toContain("确定性审计概览</h2>");
    expect(html).toContain("<p>报告</p>");
  });
});
