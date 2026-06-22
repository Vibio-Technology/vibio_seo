---
name: vibio-fix
description: |
  当用户说「优化这个页面的 SEO」「加 schema / 结构化数据」「修 OG 图 / 社交分享图」「让公司名在 Google 搜索结果里显示 / 高亮」「加 llms.txt」「修 canonical / 重定向」「修 robots / sitemap」，或直接「给个网址帮我把 SEO 改好」时，应使用本 skill。栈无关：先识别站点用什么搭建（Next.js / WordPress / Shopify / 静态站 / 未知），载入对应适配器，套用通用目标规格直接动手改；没有代码权限时给出精确目标规格 + 可粘贴片段。改完在渲染产物里验证，并提醒面向 SERP 的改动需等搜索引擎重新抓取。
  不应触发：要的是执行计划（用 vibio-plan）、要的是先全面诊断找问题（用 vibio-audit）、要的是写文章/正文成稿（用 vibio-content，本 skill 只做技术标记与落地，不写内容）、纯概念问答。
  Use for any concrete code- or CMS-level SEO fix on any stack (Next.js, WordPress, Shopify, static/Astro, or a hosted platform), or when given just a URL to fix. Detects the stack, loads the right adapter, applies the stack-agnostic spec, and verifies in rendered output.
---

# Vibio SEO — FIX 引擎（栈无关）

默认动手修，不只描述。所有 SEO 问题都暴露在**渲染出来的 HTML + HTTP 响应**里，跟用什么语言/框架生成无关。所以修复永远分两层：

1. **目标规格（栈无关）** = `references/seo-fix-principles.md`：正确的 `<head>` / JSON-LD / robots / sitemap / 状态码应该长什么样。
2. **落地方式（栈相关）** = `references/stack-adapters/<栈>.md`：在具体栈里怎么把它改成真的。

先用原则层定义「要达成什么」，再开对应适配器看「在这个栈里怎么做」。

**黄金法则**：每条 SEO 事实都要在*渲染产物*里可验证，不只是源码。改完抓取/构建出 HTML，确认目标标签真的在；面向 SERP 的改动只有搜索引擎重新抓取后才显现——提醒用户去 Search Console 请求索引。

---

## 修复流程

### Step 0：确定输入与栈
两种入口：
- **有代码库** → 用 `references/stack-detection.md` 从配置文件识别栈。
- **只有一个 URL** → 先抓取（路由给 `seo-page` / `seo-firecrawl` / `seo-technical`，或 `WebFetch`/`curl`），再用 `stack-detection.md` 的「从 URL 指纹识别」判断栈 + 能不能改代码。

如果是 `vibio-audit` 转过来的，栈信息应已带下来，不必重新识别。

输出一句话定位：**「栈：X。编辑模式：改代码 / 改模板 / CMS 粘贴。载入适配器：Y。」**

### Step 1：定义目标
对每个要修的项，从 `references/seo-fix-principles.md` 取出目标规格（标题/描述、canonical、可索引性、JSON-LD、OG、标题层级、图片、内链、sitemap/robots、hreflang、llms.txt、品牌 SERP）。按**影响排序**修，不按文件顺序：先排查可索引性阻断（误加 noindex、robots 封禁、错 canonical、软 404），再标题描述，再结构化数据，再 OG，再优化层。

### Step 2：按适配器落地
打开对应 `references/stack-adapters/<栈>.md`：
- `nextjs.md` — 最完整，全部真实验证过的代码级配方（App Router）
- `wordpress.md` — 通过 SEO 插件（Yoast/Rank Math）+ 主题落地
- `shopify.md` — 通过 Liquid 模板 + 主题设置 + metafields
- `static-astro.md` — Astro/Hugo/Jekyll/纯 HTML，直接改模板，最接近原则本身
- `url-only.md` — 没代码权限时的降级：给精确目标规格 + 可粘贴片段 + 在用户平台里贴哪

小且可逆的改动直接做；较大的先说思路再做。匹配项目现有写法。

### Step 3：在渲染产物里验证
验证永远针对渲染输出（适配器各有对应命令）：
```bash
# 线上 URL（被 WAF/CDN 挡时加浏览器 UA：-A "Mozilla/5.0 ... Chrome/126.0 Safari/537.36"）
curl -sL https://example.com/ | grep -oiE '<title>[^<]*|name="description"|rel="canonical"|property="og:site_name"|"@type":"(Organization|WebSite|Product|Article)"'
curl -sL https://example.com/ | grep -i 'noindex'   # 可索引页必须为空
# 或构建产物目录（Next .next/server、Astro dist、Hugo public…）
```
验 JSON-LD 是否生效时，别只 grep `@type`——结构化数据常嵌套，要把 `<script type="application/ld+json">` 完整解析成对象再确认目标类型和必填字段在。有代码的栈还要先跑该栈的 build/lint。明确报告什么通过了、什么还没法验证（线上 SERP 变化要等重抓）。清理临时文件，只在用户要求时提交。

### Step 4：写回记忆
用 `Edit` 把这次改动追加到项目根 `.vibio/changelog.md`（在顶部插入，append-only，不覆写）：改了什么、哪个文件/模板/CMS 位置、验证结果（build/lint 或 grep 渲染 HTML）、是否面向 SERP 待重抓、引用的官方规则（如有）。格式见 `vibio-memory` 的 `references/state-templates.md`。每完成一个修复就记一条——这样下次审查/复盘能看到改动历史，不重复修。开工前若项目根已有 `.vibio/`，先用 `Read` 看一眼上次改了什么。

---

## 内置修复经验（适配器里的真实配方）

`stack-adapters/nextjs.md` 是金子——来自真实 Vibio 客户项目（B2B 碳纤维/玻纤外贸站）并通过 build + tsc + ESLint 验证：去除滚动渐显动效、表单首屏可见、Footer 深色化+社媒/B2B 平台链接、OG 图修正、llms.txt 动态路由、WebSite+Organization 结构化数据、完整公司名成为 SERP 站点名+搜索高亮、CSP 仅开发放开、canonical/www 重定向。其它栈的适配器把这些「应该达成什么」翻译成各自的落地方式。

---

## 下一步路由（修复完成后）

| 触发条件 | 推荐 |
|---------|------|
| 面向 SERP 的改动（站点名、schema、meta、OG）| 「已改完并验证。这些变化要等搜索引擎重新抓取才显现，去 Search Console 提交相关页请求索引。社交图改动还要在 Facebook/LinkedIn/Twitter 调试器里重新抓取（有缓存）。已记进 changelog，建议 2-6 周后跑 `vibio-review` 复测见效。」 |
| 改的是 CMS/托管平台（url-only）| 「片段和位置已给出。你在平台里粘好并发布后，我可以重新抓取这个 URL 帮你确认生效。」 |
| 还有未修的问题需要排期 | 「这批已修。剩余项建议跑 `vibio-plan` 排进路线图。」 |
| 不确定还有哪些问题 | 「修复已完成。想系统排查其余隐患就跑 `vibio-audit` 做完整审查。」 |
| 生成 OG/hero 图时没有合适横图 | 「项目里没有合适横图，用 `seo-image-gen` 生成一张再接回 OG 配置。」 |

---

## 不要做

- 不在没验证渲染产物的情况下声称修复有效（有代码的栈还要跑 build/lint）。
- 不假装通用：识别不出栈、又没代码权限时，老实走 url-only 给规格，别瞎改。
- 不在 WordPress/Shopify 里手写会被插件/平台覆盖的标签（如插件已发 canonical 就别再手加）。
- 不移除真正的交互反馈，只移除滚动门控的渐显（见 nextjs 适配器）。
- 生产环境 CSP 不放开 unsafe-eval。
- 不承诺改完立刻在 SERP 生效。
