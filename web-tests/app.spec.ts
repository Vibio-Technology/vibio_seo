import { expect, test } from "@playwright/test";

const providers = {
  providers: [
    {
      id: "deepseek",
      label: "DeepSeek",
      description: "适合中文分析与长文推理",
      default_model: "deepseek-chat",
      models: [
        { id: "deepseek-chat", label: "DeepSeek Chat" },
        { id: "deepseek-reasoner", label: "DeepSeek Reasoner" },
      ],
    },
  ],
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/providers", async (route) => {
    await route.fulfill({ json: providers });
  });
});

test("desktop workspace exposes the full audit flow without overflow", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");

  await expect(page.getByText("Vibio SEO", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "定位搜索阻断" })).toBeVisible();
  await expect(page.getByRole("button", { name: /运行审计/ })).toBeVisible();
  await expect(page.getByText("DeepSeek 已就绪")).not.toBeVisible();

  await page.getByRole("button", { name: /^关键词/ }).click();
  await expect(page.getByRole("heading", { name: "验证真实买家需求" })).toBeVisible();

  const overflow = await page.evaluate(() => ({
    document: document.documentElement.scrollWidth - window.innerWidth,
    body: document.body.scrollWidth - window.innerWidth,
  }));
  expect(overflow.document).toBeLessThanOrEqual(1);
  expect(overflow.body).toBeLessThanOrEqual(1);

  await page.screenshot({ path: "/tmp/vibio-seo-desktop.png", fullPage: true });
});

test("mobile workspace remains usable and text stays within the viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "定位搜索阻断" })).toBeVisible();
  await page.getByRole("button", { name: /^内容(?:\s|$)/ }).click();
  await expect(page.getByRole("heading", { name: "产出可发布页面" })).toBeVisible();

  const layout = await page.evaluate(() => {
    const isInsideHorizontalScroller = (element: HTMLElement) => {
      let parent = element.parentElement;
      while (parent && parent !== document.body) {
        const style = getComputedStyle(parent);
        if (
          ["auto", "scroll"].includes(style.overflowX) &&
          parent.scrollWidth > parent.clientWidth
        ) {
          return true;
        }
        parent = parent.parentElement;
      }
      return false;
    };
    const overflowing = [...document.querySelectorAll<HTMLElement>("body *")]
      .filter((element) => {
        const style = getComputedStyle(element);
        if (style.position === "fixed" || isInsideHorizontalScroller(element)) return false;
        const rect = element.getBoundingClientRect();
        return rect.right > window.innerWidth + 1 || rect.left < -1;
      })
      .map((element) => element.className)
      .slice(0, 10);
    return {
      pageOverflow: document.documentElement.scrollWidth - window.innerWidth,
      overflowing,
    };
  });
  expect(layout.pageOverflow).toBeLessThanOrEqual(1);
  expect(layout.overflowing).toEqual([]);

  await page.screenshot({ path: "/tmp/vibio-seo-mobile.png", fullPage: true });
});

test("automatic workflow resumes from a failed step and stores one safe aggregate run", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const requestedModes: string[] = [];
  let inspectCalls = 0;
  let keywordAttempts = 0;

  await page.route("**/api/inspect", async (route) => {
    inspectCalls += 1;
    if (inspectCalls === 1) {
      await route.fulfill({ status: 429, json: { detail: "站点审计临时限流。" } });
      return;
    }
    await route.fulfill({
      json: {
        report: {
          analysis_kind: "bounded_seo_artifact_inspection",
          summary: { pages: 1 },
          findings: [],
          pages: [],
        },
        markdown: "# 审计证据",
      },
    });
  });

  await page.route("**/api/analyze", async (route) => {
    const body = route.request().postDataJSON() as {
      mode: string;
      workflow_context?: { completedReports?: Array<{ mode: string }> };
    };
    requestedModes.push(body.mode);
    if (body.mode === "keyword") {
      keywordAttempts += 1;
      if (keywordAttempts === 1) {
        await route.fulfill({ status: 503, json: { detail: "模型服务临时限流。" } });
        return;
      }
    }
    if (body.mode !== "audit") {
      expect(body.workflow_context?.completedReports?.length).toBeGreaterThan(0);
    }
    await route.fulfill({
      json: {
        provider: "deepseek",
        model: "deepseek-chat",
        mode: body.mode.toUpperCase(),
        report: `# ${body.mode.toUpperCase()} 阶段\n\n- 已完成`,
        created_at: "2026-07-13T08:00:00Z",
      },
    });
  });

  await page.goto("/");
  await page.getByLabel("项目名称 *").fill("Vibio 自动化测试");
  await page.getByLabel("站点 URL").fill("https://example.com");
  await page.getByLabel("目标国家 / 地区 *").fill("德国");
  await page.getByLabel("目标语言 *").fill("de-DE");
  await page.getByLabel("主要合格转化 *").fill("通过评审的 RFQ");
  await page.getByLabel("当前目标 / 问题 *").fill("建立可执行的 SEO 基线。");
  await page.getByPlaceholder("输入当前提供商的 Key").fill("temporary-browser-key");

  await page.getByRole("button", { name: "自动跑全流程" }).click();
  await expect(page.locator(".error-banner")).toContainText("关键词阶段失败");
  await expect(page.getByRole("button", { name: "重试证据并继续" })).toBeVisible();
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeLessThanOrEqual(1);
  expect(inspectCalls).toBe(1);
  expect(requestedModes).toEqual(["audit", "keyword"]);

  await page.getByLabel("项目名称 *").fill("Vibio 自动化测试更新");
  await expect(page.getByRole("button", { name: "重新运行全流程" })).toBeVisible();
  await page.getByLabel("项目名称 *").fill("Vibio 自动化测试");
  await expect(page.getByRole("button", { name: "重试证据并继续" })).toBeVisible();
  await page.getByRole("button", { name: "重试证据并继续" }).click();
  await expect(page.getByText("Vibio 自动化测试 SEO 全流程报告")).toBeVisible();
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeLessThanOrEqual(1);

  expect(inspectCalls).toBe(2);
  expect(requestedModes).toEqual([
    "audit",
    "keyword",
    "audit",
    "keyword",
    "plan",
    "fix",
    "write",
    "link",
  ]);

  const stored = await page.evaluate(() => localStorage.getItem("vibio:runs"));
  expect(stored).not.toContain("temporary-browser-key");
  const runs = JSON.parse(stored ?? "[]") as Array<{ mode?: string; workflow?: { steps?: unknown[] } }>;
  expect(runs).toHaveLength(1);
  expect(runs[0].mode).toBe("workflow");
  expect(runs[0].workflow?.steps).toHaveLength(8);

  const reportTab = page.getByRole("tab", { name: "分析报告" });
  await reportTab.focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("tab", { name: "流程轨迹" })).toHaveAttribute("aria-selected", "true");
  await expect(page.getByRole("heading", { name: "能力链进度" })).toBeVisible();
  await page.keyboard.press("End");
  await expect(page.getByRole("tab", { name: "证据清单" })).toHaveAttribute("aria-selected", "true");

  await page.screenshot({ path: "/tmp/vibio-seo-workflow.png" });
});

test("history drawer traps focus, closes with Escape, and restores the opener", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");

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
