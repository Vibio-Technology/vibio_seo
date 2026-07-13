import { expect, test, type Page } from "@playwright/test";
import { readFile } from "node:fs/promises";

import type {
  ModeDraft,
  ModeId,
  ProjectInput,
  ProjectProfile,
  RunRecord,
  WorkspaceDraftV2,
} from "../src/types";

const WORKSPACE_DRAFT_KEY = "vibio:workspace:draft:v2";
const LEGACY_PROJECT_KEY = "vibio:project:draft";
const MODEL_PREFERENCE_KEY = "vibio:model:preference";
const API_KEY_SESSION_KEY = "vibio:model:api-key";
const ACTIVE_WORKFLOW_KEY = "vibio:automation:active:v1";
const RUNS_KEY = "vibio:runs";

interface AnalyzeRequestBody {
  mode: ModeId;
  project: ProjectInput;
  workflow_context?: {
    schemaVersion?: string;
    completedReports?: Array<{
      mode: ModeId;
      artifactKind?: string;
      report: string;
    }>;
  };
}

const MODE_IDS: readonly ModeId[] = [
  "plan",
  "audit",
  "fix",
  "keyword",
  "write",
  "link",
  "review",
  "recover",
];

const providers = {
  providers: [
    {
      id: "deepseek",
      label: "DeepSeek",
      description: "DeepSeek V4，支持长上下文与思考模式",
      default_model: "deepseek-v4-flash",
      models: [
        { id: "deepseek-v4-flash", label: "DeepSeek V4 Flash" },
        { id: "deepseek-v4-pro", label: "DeepSeek V4 Pro" },
      ],
    },
  ],
};

function analyzeStreamBody(...events: Array<Record<string, unknown>>): string {
  return `${events.map((event) => JSON.stringify(event)).join("\n")}\n`;
}

async function mockSuccessfulAnalyses(
  page: Page,
  requestedBodies: AnalyzeRequestBody[],
): Promise<void> {
  await page.route("**/api/analyze/stream", async (route) => {
    const body = route.request().postDataJSON() as AnalyzeRequestBody;
    requestedBodies.push(body);
    await route.fulfill({
      contentType: "application/x-ndjson",
      body: analyzeStreamBody(
        {
          type: "accepted",
          provider: "deepseek",
          model: "deepseek-v4-flash",
          mode: body.mode.toUpperCase(),
        },
        { type: "heartbeat" },
        {
          type: "complete",
          result: {
            provider: "deepseek",
            model: "deepseek-v4-flash",
            mode: body.mode.toUpperCase(),
            report: `# ${body.mode.toUpperCase()} 阶段\n\n- ${body.mode} 已完成`,
            created_at: "2026-07-13T08:00:00Z",
          },
        },
      ),
    });
  });
}

const DEFAULT_PROFILE: ProjectProfile = {
  projectName: "Vibio 自动化测试",
  siteUrl: "https://example.com",
  market: "德国",
  language: "de-DE",
  conversion: "通过评审的 RFQ",
  primaryGoal: "建立可执行的 SEO 基线",
  audience: "工业采购与技术决策者",
  businessModel: "B2B 工业设备",
  capacity: "SEO 1 人，开发每周 2 天",
  allowNetworkEvidence: true,
  allowStateDraft: true,
};

const AUDIT_REPORT_FIXTURE: Record<string, unknown> = {
  schema_version: "seo-inspect-report.v1",
  analysis_kind: "bounded_seo_artifact_inspection",
  scope: {
    base_url: "https://example.com/",
    evidence_mode: "network",
    pages_parsed: 2,
    fetches: 4,
    sitemap_urls: 2,
  },
  findings: [
    {
      code: "canonical.mismatch",
      severity: "high",
      category: "url-signals",
      observation: "产品页 canonical 指向首页",
      evidence: ["HTML 中观察到首页 canonical"],
      urls: ["https://example.com/product"],
      impact_boundary: "仅证明当前响应中的规范信号冲突。",
      verification: "修复后重新抓取并核对响应 HTML。",
      confidence: "high",
    },
    {
      code: "headings.missing_h1",
      severity: "medium",
      category: "content-structure",
      observation: "首页没有 H1",
      evidence: ["解析结果 h1_count=0"],
      urls: ["https://example.com/"],
    },
  ],
  pages: [
    {
      url: "https://example.com/",
      status: 200,
      content_type: "text/html",
      titles: ["Example Domain"],
      canonicals: ["https://example.com/"],
      noindex: false,
      h1_count: 0,
      depth: 0,
      inbound_links_in_scope: 1,
      internal_link_count: 1,
    },
    {
      url: "https://example.com/product",
      status: 200,
      content_type: "text/html",
      titles: ["Product"],
      canonicals: ["https://example.com/"],
      noindex: false,
      h1_count: 1,
      depth: 1,
      inbound_links_in_scope: 1,
      internal_link_count: 0,
    },
  ],
  limitations: ["未使用搜索引擎索引数据，不能证明页面已收录。"],
};

interface WorkspaceDraftOverrides {
  profile?: Partial<ProjectProfile>;
  modes?: Partial<Record<ModeId, Partial<ModeDraft>>>;
  sharedContext?: string;
}

function createWorkspaceDraft(overrides: WorkspaceDraftOverrides = {}): WorkspaceDraftV2 {
  const modes = Object.fromEntries(
    MODE_IDS.map((mode) => [
      mode,
      {
        objective: "",
        details: "",
        scope: "",
        timing: "",
        ...overrides.modes?.[mode],
      },
    ]),
  ) as WorkspaceDraftV2["modes"];

  return {
    schemaVersion: 2,
    profile: { ...DEFAULT_PROFILE, ...overrides.profile },
    modes,
    sharedContext: overrides.sharedContext ?? "",
  };
}

const WORKFLOW_MODE_DRAFTS: Record<ModeId, ModeDraft> = {
  audit: {
    objective: "audit-objective：确认抓取与索引阻断",
    details: "audit-details：产品页长期无曝光",
    scope: "audit-scope：/products/",
    timing: "audit-timing：当前基线",
  },
  recover: {
    objective: "自然搜索流量最近骤降（recover-objective）",
    details: "recover-details：同期更换了模板",
    scope: "recover-scope：德国产品目录",
    timing: "recover-timing：2026-06-15 开始",
  },
  keyword: {
    objective: "keyword-objective：研究工业采购查询",
    details: "keyword-details：买家使用型号和规格词",
    scope: "keyword-scope：产品与方案页",
    timing: "keyword-timing：本季度",
  },
  plan: {
    objective: "plan-objective：排定下一阶段工作",
    details: "plan-details：开发每周可投入两天",
    scope: "plan-scope：德国站全站",
    timing: "plan-timing：未来六周",
  },
  fix: {
    objective: "fix-objective：修复已确认的 canonical 冲突",
    details: "fix-details：Next.js App Router",
    scope: "fix-scope：仅产品页模板",
    timing: "fix-timing：下次发布窗口",
  },
  write: {
    objective: "write-objective：改写产品详情页",
    details: "write-details：必须使用已验证的技术参数",
    scope: "write-scope：/de/products/example",
    timing: "write-timing：修复后发布",
  },
  link: {
    objective: "link-objective：支持德国产品页",
    details: "link-details：现有选型指南可做 donor",
    scope: "link-scope：先内链后外链",
    timing: "link-timing：内容发布后",
  },
  review: {
    objective: "模板修复已于 2026-07-01 上线（review-objective）",
    details: "review-details：已有 GSC 点击与曝光对比",
    scope: "review-scope：受影响产品页",
    timing: "review-timing：上线前后四周",
  },
};

function createWorkflowDraft(): WorkspaceDraftV2 {
  return createWorkspaceDraft({
    profile: { allowNetworkEvidence: false },
    modes: WORKFLOW_MODE_DRAFTS,
    sharedContext: "shared-context：不声称未提供的业务数据",
  });
}

async function injectWorkspace(
  page: Page,
  draft: WorkspaceDraftV2 = createWorkspaceDraft(),
  apiKey = "temporary-browser-key",
): Promise<void> {
  await page.addInitScript(
    ({ draftValue, key }) => {
      localStorage.setItem("vibio:workspace:draft:v2", JSON.stringify(draftValue));
      localStorage.setItem(
        "vibio:model:preference",
        JSON.stringify({ provider: "deepseek", model: "deepseek-v4-flash" }),
      );
      sessionStorage.setItem("vibio:model:api-key", key);
    },
    { draftValue: draft, key: apiKey },
  );
}

async function injectRun(page: Page, run: RunRecord): Promise<void> {
  await page.addInitScript(
    ({ key, value }) => localStorage.setItem(key, JSON.stringify([value])),
    { key: RUNS_KEY, value: run },
  );
}

async function expectNoHorizontalOverflow(page: Page): Promise<void> {
  const overflow = await page.evaluate(() => {
    const offenders = Array.from(document.body.querySelectorAll<HTMLElement>("*"))
      .filter((element) => {
        if (element.tagName.toLowerCase().startsWith("nextjs-")) return false;
        const rect = element.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return false;
        let current: HTMLElement | null = element;
        let insideHorizontalScroller = false;
        while (current && current !== document.body) {
          const overflowX = getComputedStyle(current).overflowX;
          if (["auto", "scroll"].includes(overflowX) && current.scrollWidth > current.clientWidth) {
            insideHorizontalScroller = true;
            break;
          }
          current = current.parentElement;
        }
        if (insideHorizontalScroller) return false;
        return rect.left < -1 || rect.right > window.innerWidth + 1;
      })
      .slice(0, 10)
      .map((element) => ({
        tag: element.tagName.toLowerCase(),
        className: element.className,
        left: Math.round(element.getBoundingClientRect().left),
        right: Math.round(element.getBoundingClientRect().right),
      }));
    return {
      document: document.documentElement.scrollWidth - window.innerWidth,
      body: document.body.scrollWidth - window.innerWidth,
      offenders,
    };
  });
  expect(overflow.document).toBeLessThanOrEqual(1);
  expect(overflow.body).toBeLessThanOrEqual(1);
  expect(overflow.offenders).toEqual([]);
}

test.beforeEach(async ({ page }) => {
  await page.route("**/api/providers", async (route) => {
    await route.fulfill({ json: providers });
  });
});

for (const viewport of [
  { label: "mobile", width: 390, height: 844 },
  { label: "desktop", width: 1440, height: 1000 },
] as const) {
  test(`marketing homepage is usable without overflow on ${viewport.label}`, async ({ page }) => {
    await injectWorkspace(page);
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    const response = await page.goto("/");

    expect(response?.ok()).toBe(true);
    await expect(page.getByRole("heading", { level: 1, name: "Vibio SEO" })).toBeVisible();
    const cta = page.locator('main a[href="/workspace"]:visible').first();
    await expect(cta).toHaveText(/进入工作台/);
    await expectNoHorizontalOverflow(page);

    await cta.click();
    await expect(page).toHaveURL(/\/workspace$/);
    await expect(page.getByRole("heading", { name: "定位搜索阻断" })).toBeVisible();
  });
}

test("mobile navigation traps focus, restores scrolling, and closes at the desktop breakpoint", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");

  const toggleControl = page.locator('button[aria-controls="marketing-navigation"]');
  const navigation = page.getByRole("navigation", { name: "主导航" });
  const toggle = page.getByRole("button", { name: "打开导航" });
  await toggle.click();
  await expect(toggleControl).toHaveAttribute("aria-expanded", "true");
  await expect(navigation.getByRole("link", { name: "工作方式", exact: true })).toBeFocused();
  await expect.poll(() => page.evaluate(() => document.body.style.overflow)).toBe("hidden");

  await page.keyboard.press("Shift+Tab");
  await expect(page.getByRole("button", { name: "关闭导航" }).first()).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(navigation.getByRole("link", { name: "进入工作台", exact: true })).toBeFocused();

  await page.keyboard.press("Escape");
  await expect(page.getByRole("button", { name: "打开导航" })).toBeFocused();
  await expect(toggleControl).toHaveAttribute("aria-expanded", "false");
  await expect.poll(() => page.evaluate(() => document.body.style.overflow)).toBe("");

  await page.getByRole("button", { name: "打开导航" }).click();
  await page.setViewportSize({ width: 1200, height: 844 });
  await expect(toggleControl).toHaveAttribute("aria-expanded", "false");
  await expect.poll(() => page.evaluate(() => document.body.style.overflow)).toBe("");
});

for (const viewport of [
  { label: "mobile", width: 390, height: 844 },
  { label: "desktop", width: 1440, height: 1000 },
] as const) {
  test(`workspace opens directly without overflow on ${viewport.label}`, async ({ page }) => {
    await injectWorkspace(page);
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    const response = await page.goto("/workspace");

    expect(response?.ok()).toBe(true);
    await expect(page).toHaveURL(/\/workspace$/);
    await expect(page.getByText("Vibio SEO", { exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "定位搜索阻断" })).toBeVisible();
    await expect(page.getByRole("button", { name: /运行审计/ })).toBeVisible();
    expect(await page.locator('input[name="provider-api-key"]').evaluate(
      (element: HTMLInputElement) => element.form !== null,
    )).toBe(true);
    await expect(page.locator('meta[name="robots"]')).toHaveAttribute(
      "content",
      /noindex.*nofollow|nofollow.*noindex/,
    );
    await expectNoHorizontalOverflow(page);
    if (viewport.label === "desktop") {
      await page.screenshot({ path: "/tmp/vibio-seo-desktop.png", fullPage: true });
    }
  });
}

test("first-time project setup collects the shared profile once and opens the workspace", async ({ page }) => {
  await page.goto("/workspace");

  await expect(page.getByRole("heading", { name: "建立项目档案" })).toBeVisible();
  await expect(page.getByRole("button", { name: "保存并进入工作台" })).toBeVisible();
  await page.getByLabel("项目名称 *").fill("首次设置项目");
  await page.getByLabel("站点 URL").fill("https://first.example.com");
  await page.getByLabel("目标国家 / 地区 *").fill("德国");
  await page.getByLabel("目标语言 *").fill("de-DE");
  await page.getByLabel("主要合格转化 *").fill("通过评审的 RFQ");
  await page.getByLabel("项目主要目标 *").fill("找到阻碍询盘增长的 SEO 瓶颈");
  await expect(page.getByRole("heading", { name: "建立项目档案" })).toBeVisible();
  await page.getByRole("button", { name: "保存并进入工作台" }).click();

  await expect(page.getByRole("heading", { name: "定位搜索阻断" })).toBeVisible();
  await expect(page.getByText("首次设置项目", { exact: true })).toBeVisible();
  await expect.poll(() => page.evaluate(
    (key) => localStorage.getItem(key),
    WORKSPACE_DRAFT_KEY,
  )).toContain("找到阻碍询盘增长的 SEO 瓶颈");
});

test("mode-specific drafts remain isolated while switching modes", async ({ page }) => {
  await injectWorkspace(page, createWorkspaceDraft());
  await page.goto("/workspace");

  const auditObjective = page.getByLabel("这次最想确认什么？");
  await auditObjective.fill("只属于审计的任务");
  await page.getByRole("button", { name: /^关键词/ }).click();
  const keywordObjective = page.getByLabel("要研究哪个产品或主题？");
  await expect(keywordObjective).toHaveValue("");
  await keywordObjective.fill("只属于关键词的任务");

  await page.getByRole("button", { name: /^审计/ }).click();
  await expect(auditObjective).toHaveValue("只属于审计的任务");
  await expect.poll(() => page.evaluate((key) => {
    const stored = JSON.parse(localStorage.getItem(key) ?? "null") as WorkspaceDraftV2 | null;
    return stored
      ? [stored.modes.audit.objective, stored.modes.keyword.objective]
      : [];
  }, WORKSPACE_DRAFT_KEY)).toEqual([
    "只属于审计的任务",
    "只属于关键词的任务",
  ]);
});

test("legacy project storage migrates into the shared project context", async ({ page }) => {
  const legacyProject = {
    projectName: "旧版 Vibio 项目",
    siteUrl: "https://legacy.example.com",
    market: "德国",
    language: "de-DE",
    conversion: "旧版 RFQ",
    audience: "工业采购",
    businessModel: "B2B",
    capacity: "SEO 1 人",
    objective: "旧版目标",
    scope: "旧版分析范围",
    details: "旧版补充信息",
    decisionWindow: "旧版观察窗口",
    allowNetworkEvidence: false,
    allowStateDraft: true,
  };
  await page.addInitScript((value) => {
    localStorage.setItem("vibio:project:draft", JSON.stringify(value));
  }, legacyProject);
  await page.goto("/workspace");

  await expect(page.getByRole("heading", { name: "建立项目档案" })).toBeVisible();
  await expect(page.getByLabel("项目名称 *")).toHaveValue("旧版 Vibio 项目");
  await page.getByText("更多项目设置", { exact: true }).click();
  await expect(page.getByLabel("所有任务共享的背景")).toHaveValue(
    /当前目标 \/ 问题：\n旧版目标[\s\S]*分析范围：\n旧版分析范围[\s\S]*旧版补充信息：\n旧版补充信息[\s\S]*决策 \/ 观察窗口：\n旧版观察窗口/,
  );
  await expect.poll(() => page.evaluate(
    (key) => localStorage.getItem(key),
    WORKSPACE_DRAFT_KEY,
  )).toContain("旧版目标");
  expect(await page.evaluate((key) => localStorage.getItem(key), LEGACY_PROJECT_KEY)).toContain(
    "旧版目标",
  );
});

test("single-step plan hands off to audit and audit hands off to fix without overwriting the fix draft", async ({ page }) => {
  const workflowDraft = createWorkflowDraft();
  workflowDraft.profile.allowNetworkEvidence = true;
  workflowDraft.modes.fix.objective = "";
  const originalFixDraft = { ...workflowDraft.modes.fix };
  const requestedBodies: AnalyzeRequestBody[] = [];
  let inspectionAttempts = 0;

  await injectWorkspace(page, workflowDraft);
  await mockSuccessfulAnalyses(page, requestedBodies);
  await page.route("**/api/inspect", async (route) => {
    inspectionAttempts += 1;
    if (inspectionAttempts === 1) {
      await route.fulfill({ status: 502, json: { detail: "站点证据暂时不可用" } });
      return;
    }
    await route.fulfill({ json: { report: AUDIT_REPORT_FIXTURE } });
  });

  await page.goto("/workspace");
  await page.getByRole("button", { name: /^计划/ }).click();
  await page.getByRole("button", { name: "运行计划" }).click();
  await expect(page.getByRole("button", { name: "按此计划开始审计" })).toBeVisible();

  await page.getByRole("button", { name: "按此计划开始审计" }).click();
  await expect(page.getByRole("heading", { name: "定位搜索阻断" })).toBeVisible();
  await expect(page.locator(".handoff-banner")).toContainText("自动继承计划");
  await page.getByRole("button", { name: "运行审计" }).click();
  await expect(page.getByRole("button", { name: "根据审计生成修复" })).toBeVisible();

  await page.getByRole("button", { name: "根据审计生成修复" }).click();
  await expect(page.getByRole("heading", { name: "形成最小修复契约" })).toBeVisible();
  await expect(page.locator(".handoff-banner")).toContainText("计划、审计");
  await expect(page.getByLabel("要修复的已确认问题")).toHaveValue("");
  await page.getByRole("button", { name: "运行修复" }).click();
  await expect.poll(() => requestedBodies.map(({ mode }) => mode)).toEqual(["plan", "audit", "fix"]);
  expect(inspectionAttempts).toBe(2);

  const auditBody = requestedBodies.find(({ mode }) => mode === "audit");
  expect(auditBody?.workflow_context?.completedReports?.map(({ mode }) => mode)).toEqual(["plan"]);
  const fixBody = requestedBodies.find(({ mode }) => mode === "fix");
  expect(fixBody?.workflow_context).toMatchObject({
    schemaVersion: "vibio-web.workflow-context.v1",
    completedReports: [
      { mode: "plan", artifactKind: "execution_plan" },
      { mode: "audit", artifactKind: "audit_findings" },
    ],
  });
  expect(fixBody?.workflow_context?.completedReports?.[0].report).toContain("PLAN 阶段");
  expect(fixBody?.workflow_context?.completedReports?.[1].report).toContain("AUDIT 阶段");

  const storedFixDraft = await page.evaluate((key) => {
    const stored = JSON.parse(localStorage.getItem(key) ?? "null") as WorkspaceDraftV2 | null;
    return stored?.modes.fix;
  }, WORKSPACE_DRAFT_KEY);
  expect(storedFixDraft).toEqual(originalFixDraft);
});

test("approval automation runs a selected technical subset and leaves review waiting for evidence", async ({ page }) => {
  const draft = createWorkspaceDraft({
    profile: { allowNetworkEvidence: false },
    modes: {
      audit: { objective: "检查产品页规范信号" },
      fix: { objective: "修复已确认的 canonical 冲突" },
    },
  });
  const requestedBodies: AnalyzeRequestBody[] = [];
  await injectWorkspace(page, draft);
  await mockSuccessfulAnalyses(page, requestedBodies);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/workspace");

  await page.getByRole("button", { name: "自动流程" }).click();
  await expect(page.getByRole("heading", { name: "编排 SEO 能力链" })).toBeVisible();
  await page.getByRole("radio", { name: /^技术修复/ }).click();
  await expect(page.locator(".automation-route-node", { hasText: "关键词" }).getByRole("checkbox")).not.toBeChecked();
  await expect(page.locator(".automation-route-node", { hasText: "审计" }).getByRole("checkbox")).toBeChecked();
  await expect(page.locator(".automation-route-node", { hasText: "修复" }).getByRole("checkbox")).toBeChecked();
  await expect(page.locator(".automation-route-node", { hasText: "复盘" }).getByRole("checkbox")).toBeChecked();
  await expectNoHorizontalOverflow(page);
  await page.screenshot({ path: "/tmp/vibio-automation-desktop.png", fullPage: true });

  await page.getByRole("button", { name: "确认路线并开始审计" }).click();
  await expect.poll(() => requestedBodies.map(({ mode }) => mode)).toEqual(["audit"]);
  await expect(page.getByRole("button", { name: "继续到修复" })).toBeVisible();
  await expect(page.locator(".automation-latest-output")).toContainText("AUDIT 阶段");

  await page.getByRole("button", { name: "继续到修复" }).click();
  await expect.poll(() => requestedBodies.map(({ mode }) => mode)).toEqual(["audit", "fix"]);
  await expect(page.getByRole("tab", { name: "流程轨迹" })).toBeVisible();
  await page.getByRole("tab", { name: "流程轨迹" }).click();
  await expect(page.locator(".workflow-step--waiting")).toContainText("复盘");
  await expect(page.locator(".workflow-step--waiting")).toContainText("等待材料");

  const runs = await page.evaluate((key) => JSON.parse(localStorage.getItem(key) ?? "[]"), RUNS_KEY) as Array<{
    mode?: string;
    workflow?: { status?: string; steps?: Array<{ mode?: string; status?: string }> };
  }>;
  expect(runs).toHaveLength(1);
  expect(runs[0]).toMatchObject({
    mode: "workflow",
    workflow: {
      status: "partial",
      steps: [
        { mode: "audit", status: "complete" },
        { mode: "fix", status: "complete" },
        { mode: "review", status: "waiting" },
      ],
    },
  });

  await expect(page.getByRole("button", { name: "等待复盘材料" })).toBeDisabled();
  await page.locator('.evidence-panel input[type="file"]').setInputFiles({
    name: "gsc-before-after.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("page,clicks,impressions\n/products,12,140"),
  });
  const continueReview = page.getByRole("button", { name: "继续到复盘" });
  await expect(continueReview).toBeEnabled();
  await continueReview.click();
  await expect.poll(() => requestedBodies.map(({ mode }) => mode)).toEqual([
    "audit",
    "fix",
    "review",
  ]);

  const resumedRuns = await page.evaluate(
    (key) => JSON.parse(localStorage.getItem(key) ?? "[]"),
    RUNS_KEY,
  ) as Array<{ workflow?: { status?: string } }>;
  expect(resumedRuns).toHaveLength(1);
  expect(resumedRuns[0].workflow?.status).toBe("complete");
  expect(await page.evaluate((key) => sessionStorage.getItem(key), ACTIVE_WORKFLOW_KEY)).toBeNull();
});

test("continuous automation completes the selected technical route in one run", async ({ page }) => {
  const requestedBodies: AnalyzeRequestBody[] = [];
  await injectWorkspace(page, createWorkflowDraft());
  await mockSuccessfulAnalyses(page, requestedBodies);
  await page.goto("/workspace");

  await page.getByRole("button", { name: "自动流程" }).click();
  await page.getByRole("radio", { name: /^技术修复/ }).click();
  await page.getByRole("radio", { name: /^连续分析/ }).click();
  await page.getByRole("button", { name: "启动连续分析" }).click();

  await expect.poll(() => requestedBodies.map(({ mode }) => mode)).toEqual([
    "audit",
    "fix",
    "review",
  ]);
  await expect(page.getByRole("tab", { name: "流程轨迹" })).toBeVisible();
  expect(requestedBodies[1].workflow_context?.completedReports?.map(({ mode }) => mode)).toEqual([
    "audit",
  ]);
  expect(requestedBodies[2].workflow_context?.completedReports?.map(({ mode }) => mode)).toEqual([
    "fix",
  ]);

  const stored = await page.evaluate((key) => localStorage.getItem(key), RUNS_KEY);
  expect(stored).not.toContain("temporary-browser-key");
  const runs = JSON.parse(stored ?? "[]") as Array<{
    mode?: string;
    workflow?: { status?: string; steps?: Array<{ status?: string }> };
  }>;
  expect(runs).toHaveLength(1);
  expect(runs[0]).toMatchObject({ mode: "workflow", workflow: { status: "complete" } });
  expect(runs[0].workflow?.steps?.every(({ status }) => status === "complete")).toBe(true);
  expect(await page.evaluate((key) => sessionStorage.getItem(key), API_KEY_SESSION_KEY)).toBe(
    "temporary-browser-key",
  );
  expect(await page.evaluate((key) => sessionStorage.getItem(key), ACTIVE_WORKFLOW_KEY)).toBeNull();
  expect(await page.evaluate((key) => localStorage.getItem(key), MODEL_PREFERENCE_KEY)).toContain(
    "deepseek-v4-flash",
  );
});

test("approval automation restores completed stages after a page refresh", async ({ page }) => {
  const requestedBodies: AnalyzeRequestBody[] = [];
  await injectWorkspace(page, createWorkflowDraft());
  await mockSuccessfulAnalyses(page, requestedBodies);
  await page.goto("/workspace");

  await page.getByRole("button", { name: "自动流程" }).click();
  await page.getByRole("radio", { name: /^技术修复/ }).click();
  await page.getByRole("button", { name: "确认路线并开始审计" }).click();
  await expect.poll(() => requestedBodies.map(({ mode }) => mode)).toEqual(["audit"]);
  await expect(page.getByRole("button", { name: "继续到修复" })).toBeVisible();
  expect(await page.evaluate((key) => sessionStorage.getItem(key), ACTIVE_WORKFLOW_KEY))
    .not.toContain("temporary-browser-key");

  await page.reload();
  const continueFix = page.getByRole("button", { name: "继续到修复" });
  await expect(continueFix).toBeVisible();
  await expect(page.locator(".workflow-step--complete", { hasText: "审计" })).toBeVisible();
  await continueFix.click();
  await expect.poll(() => requestedBodies.map(({ mode }) => mode)).toEqual(["audit", "fix"]);
});

test("automatic workflow stays partial when site evidence fails and can retry it", async ({ page }) => {
  const draft = createWorkflowDraft();
  draft.profile.allowNetworkEvidence = true;
  const requestedBodies: AnalyzeRequestBody[] = [];
  let inspectionAttempts = 0;
  await injectWorkspace(page, draft);
  await mockSuccessfulAnalyses(page, requestedBodies);
  await page.route("**/api/inspect", async (route) => {
    inspectionAttempts += 1;
    if (inspectionAttempts === 1) {
      await route.fulfill({ status: 502, json: { detail: "公开站点暂时不可用" } });
      return;
    }
    await route.fulfill({ json: { report: AUDIT_REPORT_FIXTURE } });
  });
  await page.goto("/workspace");

  await page.getByRole("button", { name: "自动流程" }).click();
  await page.getByRole("radio", { name: /^技术修复/ }).click();
  await page.getByRole("radio", { name: /^连续分析/ }).click();
  await page.getByRole("button", { name: "启动连续分析" }).click();

  const retryEvidence = page.getByRole("button", { name: "重试站点证据" });
  await expect(retryEvidence).toBeVisible();
  expect(inspectionAttempts).toBe(1);
  expect(requestedBodies.map(({ mode }) => mode)).toEqual(["audit", "fix", "review"]);

  await retryEvidence.click();
  await expect.poll(() => inspectionAttempts).toBe(2);
  await expect.poll(() => requestedBodies.map(({ mode }) => mode)).toEqual([
    "audit",
    "fix",
    "review",
    "audit",
    "fix",
    "review",
  ]);
  await expect(page.getByRole("button", { name: "重试站点证据" })).toBeHidden();

  const runs = await page.evaluate(
    (key) => JSON.parse(localStorage.getItem(key) ?? "[]"),
    RUNS_KEY,
  ) as Array<{ workflow?: { status?: string } }>;
  expect(runs).toHaveLength(1);
  expect(runs[0].workflow?.status).toBe("complete");
});

test("automatic workflow builder has no horizontal overflow at 390px", async ({ page }) => {
  await injectWorkspace(page, createWorkflowDraft());
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/workspace");

  await page.getByRole("button", { name: "自动流程" }).click();
  await expect(page.getByRole("heading", { name: "编排 SEO 能力链" })).toBeVisible();
  await expectNoHorizontalOverflow(page);
  await page.screenshot({ path: "/tmp/vibio-automation-mobile.png", fullPage: true });
});

test("analysis connection closure keeps inputs and shows a recoverable error", async ({ page }) => {
  const draft = createWorkspaceDraft({
    profile: { allowNetworkEvidence: false },
    modes: { audit: { objective: "保留这次审计输入" } },
  });
  await injectWorkspace(page, draft);
  await page.route("**/api/analyze/stream", async (route) => {
    await route.abort("connectionclosed");
  });
  await page.goto("/workspace");

  await page.getByRole("button", { name: "运行审计" }).click();

  await expect(page.locator(".error-banner")).toContainText("分析连接中断，服务端未确认是否完成");
  await expect(page.locator(".error-banner")).toContainText("重复提交可能再次计费");
  await expect(page.getByLabel("这次最想确认什么？")).toHaveValue("保留这次审计输入");
  await expect(page.getByRole("button", { name: "运行审计" })).toBeEnabled();
});

test("stream timeout keeps inputs and explains the five-minute boundary", async ({ page }) => {
  const draft = createWorkspaceDraft({
    profile: { allowNetworkEvidence: false },
    modes: { audit: { objective: "保留超时审计输入" } },
  });
  await injectWorkspace(page, draft);
  await page.route("**/api/analyze/stream", async (route) => {
    await route.fulfill({
      contentType: "application/x-ndjson",
      body: analyzeStreamBody(
        {
          type: "accepted",
          provider: "deepseek",
          model: "deepseek-v4-pro",
          mode: "AUDIT",
        },
        { type: "heartbeat" },
        { type: "error", status: 504, detail: "DeepSeek 请求超时。" },
      ),
    });
  });
  await page.goto("/workspace");

  await page.getByRole("button", { name: "运行审计" }).click();

  await expect(page.locator(".error-banner")).toContainText("约 5 分钟的运行窗口内未完成");
  await expect(page.getByLabel("这次最想确认什么？")).toHaveValue("保留超时审计输入");
  await expect(page.getByRole("button", { name: "运行审计" })).toBeEnabled();
});

test("leaving the workspace aborts an in-flight model request", async ({ page }) => {
  const draft = createWorkspaceDraft({
    profile: { allowNetworkEvidence: false },
    modes: { audit: { objective: "验证离开页面时取消请求" } },
  });
  await injectWorkspace(page, draft);
  await page.addInitScript(() => {
    const originalFetch = window.fetch.bind(window);
    window.fetch = (input, init) => {
      const url = input instanceof Request ? input.url : String(input);
      if (!url.includes("/api/analyze/stream")) return originalFetch(input, init);
      sessionStorage.setItem("vibio:test:analysis-started", "true");
      return new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () => {
          sessionStorage.setItem("vibio:test:analysis-aborted", "true");
          reject(new DOMException("Aborted", "AbortError"));
        }, { once: true });
      });
    };
  });
  await page.goto("/workspace");

  await page.getByRole("button", { name: "运行审计" }).click();
  await expect.poll(() => page.evaluate(
    () => sessionStorage.getItem("vibio:test:analysis-started"),
  )).toBe("true");
  await expect(page.getByRole("button", { name: "运行记录" })).toBeDisabled();
  await page.getByRole("link", { name: "返回 Vibio SEO 首页" }).click();

  await expect(page).toHaveURL(/\/$/);
  await expect.poll(() => page.evaluate(
    () => sessionStorage.getItem("vibio:test:analysis-aborted"),
  )).toBe("true");
});

test("deterministic audit opens as a structured overview and exports standalone HTML", async ({ page }) => {
  const run: RunRecord = {
    id: "structured-audit-run",
    mode: "audit",
    projectName: "结构化审计样例",
    siteUrl: "https://example.com",
    market: "德国",
    language: "de-DE",
    objective: "定位可核验的搜索阻断",
    provider: "deepseek",
    model: "deepseek-v4-pro",
    report: "# 分析报告\n\n## 三项行动\n\n1. 修复 canonical。",
    auditReport: AUDIT_REPORT_FIXTURE,
    evidence: [],
    createdAt: "2026-07-13T08:00:00Z",
  };
  await injectWorkspace(page);
  await injectRun(page, run);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/workspace");

  await page.getByRole("button", { name: /运行记录/ }).click();
  await page.getByRole("button", { name: /结构化审计样例/ }).click();

  const overviewTab = page.getByRole("tab", { name: "审计概览" });
  await expect(overviewTab).toHaveAttribute("aria-selected", "true");
  await expect(page.getByRole("heading", { name: "审计概览" })).toBeVisible();
  const canonicalFinding = page.locator(".audit-overview__observation", {
    hasText: "产品页 canonical 指向首页",
  });
  await expect(canonicalFinding).toBeHidden();
  await page.getByText("展开 1 条发现").first().click();
  await expect(canonicalFinding).toBeVisible();
  await expect(page.locator(".audit-overview__boundary", {
    hasText: "未使用搜索引擎索引数据，不能证明页面已收录。",
  })).toBeVisible();
  await expectNoHorizontalOverflow(page);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: "/tmp/vibio-audit-overview-mobile.png" });

  await page.setViewportSize({ width: 1440, height: 1000 });
  await expectNoHorizontalOverflow(page);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: "/tmp/vibio-audit-overview-desktop.png" });

  await overviewTab.focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("tab", { name: "分析报告" })).toHaveAttribute("aria-selected", "true");
  await expect(page.getByRole("heading", { name: "三项行动" })).toBeVisible();

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "下载独立 HTML 报告" }).click();
  const downloaded = await downloadPromise;
  expect(downloaded.suggestedFilename()).toBe("结构化审计样例-audit-2026-07-13.html");
  const downloadPath = await downloaded.path();
  expect(downloadPath).not.toBeNull();
  const html = await readFile(downloadPath as string, "utf8");
  expect(html).toContain("<!doctype html>");
  expect(html).toContain("产品页 canonical 指向首页");
  expect(html).toContain("修复 canonical");
  expect(html).not.toContain("<script");
});

test("history drawer traps focus, closes with Escape, and restores the opener", async ({ page }) => {
  await injectWorkspace(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/workspace");

  const opener = page.getByRole("button", { name: "运行记录" });
  await opener.click();
  const close = page.getByRole("button", { name: "关闭运行记录" });
  await expect(close).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(close).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog", { name: "运行记录" })).toBeHidden();
  await expect(opener).toBeFocused();
});

test("a historical report from another project cannot enter the current manual chain", async ({ page }) => {
  const historicalRun: RunRecord = {
    id: "other-project-audit",
    mode: "audit",
    projectName: "另一个项目",
    siteUrl: "https://other.example.com",
    market: "美国",
    language: "en-US",
    objective: "Audit another site",
    provider: "deepseek",
    model: "deepseek-v4-flash",
    report: "# Other project audit",
    auditReport: AUDIT_REPORT_FIXTURE,
    evidence: [],
    createdAt: "2026-07-13T08:00:00Z",
  };
  await injectWorkspace(page, createWorkspaceDraft());
  await injectRun(page, historicalRun);
  await page.goto("/workspace");

  await page.getByRole("button", { name: "运行记录" }).click();
  await page.getByRole("button", { name: /另一个项目/ }).click();
  await expect(page.getByRole("heading", { level: 1, name: "另一个项目" })).toBeVisible();
  await expect(page.getByRole("button", { name: "根据审计生成修复" })).toBeHidden();
});
