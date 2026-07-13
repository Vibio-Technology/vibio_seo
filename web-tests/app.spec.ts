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

  await page.getByRole("button", { name: /关键词验证真实买家需求/ }).click();
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
  await page.getByRole("button", { name: /内容产出可发布页面/ }).click();
  await expect(page.getByRole("heading", { name: "产出可发布页面" })).toBeVisible();

  const layout = await page.evaluate(() => {
    const overflowing = [...document.querySelectorAll<HTMLElement>("body *")]
      .filter((element) => {
        const style = getComputedStyle(element);
        if (style.position === "fixed") return false;
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
