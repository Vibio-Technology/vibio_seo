import { expect, test, type Page } from "@playwright/test";

import type {
  ModeDraft,
  ModeId,
  ProjectInput,
  ProjectProfile,
  WorkspaceDraftV2,
} from "../src/types";

const WORKSPACE_DRAFT_KEY = "vibio:workspace:draft:v2";
const LEGACY_PROJECT_KEY = "vibio:project:draft";
const MODEL_PREFERENCE_KEY = "vibio:model:preference";
const API_KEY_SESSION_KEY = "vibio:model:api-key";
const RUNS_KEY = "vibio:runs";

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

async function expectNoHorizontalOverflow(page: Page): Promise<void> {
  const overflow = await page.evaluate(() => ({
    document: document.documentElement.scrollWidth - window.innerWidth,
    body: document.body.scrollWidth - window.innerWidth,
  }));
  expect(overflow.document).toBeLessThanOrEqual(1);
  expect(overflow.body).toBeLessThanOrEqual(1);
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

test("automatic workflow uses each mode draft and resumes only with the same inputs", async ({ page }) => {
  const workflowDraft = createWorkflowDraft();
  const requestedBodies: Array<{
    mode: ModeId;
    project: ProjectInput;
    workflow_context?: { completedReports?: Array<{ mode: ModeId }> };
  }> = [];
  let keywordAttempts = 0;

  await injectWorkspace(page, workflowDraft);
  await page.route("**/api/analyze", async (route) => {
    const body = route.request().postDataJSON() as (typeof requestedBodies)[number];
    requestedBodies.push(body);
    if (body.mode === "keyword") {
      keywordAttempts += 1;
      if (keywordAttempts === 1) {
        await route.fulfill({ status: 503, json: { detail: "模型服务临时限流。" } });
        return;
      }
    }
    await route.fulfill({
      json: {
        provider: "deepseek",
        model: "deepseek-v4-flash",
        mode: body.mode.toUpperCase(),
        report: `# ${body.mode.toUpperCase()} 阶段\n\n- 已完成`,
        created_at: "2026-07-13T08:00:00Z",
      },
    });
  });

  await page.goto("/workspace");
  await page.getByRole("button", { name: "自动跑全流程" }).click();
  await expect(page.locator(".error-banner")).toContainText("关键词阶段失败");
  await expect(page.getByRole("button", { name: "从关键词继续" })).toBeVisible();
  expect(requestedBodies.map(({ mode }) => mode)).toEqual(["audit", "recover", "keyword"]);

  const auditObjective = page.getByLabel("这次最想确认什么？");
  await auditObjective.fill(`${workflowDraft.modes.audit.objective}（已修改）`);
  await expect(page.getByRole("button", { name: "重新运行全流程" })).toBeVisible();
  await auditObjective.fill(workflowDraft.modes.audit.objective);
  await expect(page.getByRole("button", { name: "从关键词继续" })).toBeVisible();

  await page.getByRole("button", { name: "从关键词继续" }).click();
  await expect(page.getByRole("heading", {
    level: 1,
    name: "Vibio 自动化测试 SEO 全流程报告",
  })).toBeVisible();
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeLessThanOrEqual(1);

  expect(requestedBodies.map(({ mode }) => mode)).toEqual([
    "audit",
    "recover",
    "keyword",
    "keyword",
    "plan",
    "fix",
    "write",
    "link",
    "review",
  ]);
  for (const body of requestedBodies) {
    const expectedDraft = workflowDraft.modes[body.mode];
    expect(body.project.objective).toBe(expectedDraft.objective);
    expect(body.project.scope).toBe(expectedDraft.scope);
    expect(body.project.decisionWindow).toBe(expectedDraft.timing);
    expect(body.project.details).toBe(
      `本模式补充信息：\n${expectedDraft.details}\n\n共享项目背景：\n${workflowDraft.sharedContext}`,
    );
    for (const otherMode of MODE_IDS.filter((mode) => mode !== body.mode)) {
      expect(body.project.details).not.toContain(workflowDraft.modes[otherMode].details);
    }
  }

  const stored = await page.evaluate((key) => localStorage.getItem(key), RUNS_KEY);
  expect(stored).not.toContain("temporary-browser-key");
  const runs = JSON.parse(stored ?? "[]") as Array<{
    mode?: string;
    objective?: string;
    workflow?: { steps?: unknown[] };
  }>;
  expect(runs).toHaveLength(1);
  expect(runs[0]).toMatchObject({
    mode: "workflow",
    objective: workflowDraft.profile.primaryGoal,
  });
  expect(runs[0].workflow?.steps).toHaveLength(8);
  expect(await page.evaluate((key) => sessionStorage.getItem(key), API_KEY_SESSION_KEY)).toBe(
    "temporary-browser-key",
  );
  expect(await page.evaluate((key) => localStorage.getItem(key), MODEL_PREFERENCE_KEY)).toContain(
    "deepseek-v4-flash",
  );
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
