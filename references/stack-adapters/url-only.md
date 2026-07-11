# URL-Only / 无代码权限适配器

适用于只有线上 URL，或只有 Wix、Squarespace、Webflow、Framer、Carrd、托管 WordPress、Shopify 等有限 CMS UI 权限的场景。目标规范见 `../seo-fix-principles.md`。

URL-only 不等于只能给泛泛建议。必须完成“抓取现状 -> 逐项 diff -> 精确 handoff -> 应用后复验”。一旦获得模板或代码权限，立即切换到真实 stack adapter。

## 1. 明确权限

记录：

- 可访问 URL 与目标市场/页面类型。
- 是否有 CMS SEO 字段、custom code、redirect、robots/sitemap 或 analytics 权限。
- 是否能发布 preview、清缓存和查看 GSC。
- 最终执行人和可接受的交付格式。

## 2. 获取真实现状

按 `../javascript-rendering.md` 分开采集 HTTP 响应源码与外部浏览器 DOM；普通 HTTP 抓取器不执行 JavaScript。对首页和每类代表页面检查：

- 状态码、重定向链、canonical host。
- 渲染 title、description、robots、canonical、hreflang、OG。
- 可解析的 JSON-LD 与可见内容是否一致。
- H1/主内容、导航和上下文链接是否真实渲染。
- robots.txt、sitemap、404 和参数 URL。
- 移动端主任务、表单和关键媒体是否可用。

SPA 还要直接打开真实/不存在路由，检查 HTTP soft-404、History API 刷新与前进后退、初始 noindex/canonical、`<a href>`、匿名权限/API 回退和 console/network 异常。没有浏览器或无法导出 DOM 时，将客户端状态标为未验证。

被 WAF/CDN 拦截时使用正常浏览器 UA 或浏览器检查，并明确采集限制。不能从单页推断全站。

## 3. 每项修复的交付格式

```text
问题：引用当前响应/渲染 HTML 的原文
证据级别与官方来源：
影响页面：
目标状态：精确到最终渲染结果
操作位置：平台菜单/字段/模板/开发任务
可粘贴值或代码：
发布与缓存步骤：
复验方式：
搜索效果观察窗口：
```

不能确认平台菜单时，写成开发验收标准，不要编造 UI 路径。

## 4. Title 与 meta description

目标是每个重要页面有简洁、准确、互不重复的 title 和有帮助的 description。Google 没有固定字符上限，也可能重写 title/snippet。

常见位置：

- Wix：Page SEO / SEO Settings。
- Squarespace：Page Settings -> SEO。
- Webflow：Page Settings -> SEO settings。
- Framer：Page Settings -> SEO & Social。
- Carrd：站点/元素 metadata 能力取决于方案。
- WordPress：Yoast/Rank Math/AIOSEO 的页面编辑区。
- Shopify：资源的 Search engine listing。

如果系统只有一个全站字段，要求开发者把 title/description 建成页面级 CMS 字段并接入模板。

## 5. Canonical 与重定向

先确定首选 host、路径和参数策略。平台自动 canonical 不代表一定正确，要检查实际渲染值。

```html
<link rel="canonical" href="https://www.example.com/this-page/">
```

只对真正重复内容跨页 canonical。迁移页面使用服务端永久重定向；不要把大量旧 URL 全部重定向到首页。Self-canonical 是推荐做法，不把缺失本身自动判为 Critical；错误 canonical 风险更高。

## 6. 结构化数据

先确认平台或插件已输出什么，避免重复 graph。只添加 Google 当前支持、与可见内容真实一致的类型。

首页可按官方文档配置 Organization/WebSite；产品、文章、视频、面包屑等按页面与当前 Search Gallery 资格处理。不要全站重复注入首页实体 graph，也不要为 Google 富结果添加已停用的 FAQPage/HowTo。

若平台只有全站 custom code 而 schema 需要页面数据，交给开发者实现条件化模板，不能把某个产品事实硬编码到所有页面。

## 7. OG / 社交预览

配置准确的 `og:title`、`og:description`、`og:url`、`og:type` 和代表性 `og:image`。图片 URL 必须公开可访问，声明尺寸与真实文件一致。社交预览改善分发，不称为 Google 排名修复。

## 8. Robots 与 sitemap

- 先读平台默认行为，再做最小修改。
- Robots 不能用来 `noindex`，也不能阻断渲染所需资源。
- Sitemap 只列 canonical、可索引 URL；平台自动 sitemap 通过发布状态/页面设置控制时，不要求上传第二份。
- 普通页面不得使用 Google Indexing API。

平台不开放 robots 时，记录限制并优先使用页面级 index 设置、canonical、发布状态和内部链接。

## 9. AI Search

Google Search 忽略 `llms.txt`；缺少该文件不是 Google AI visibility 问题。不得建议为此购买插件、部署 proxy 或 CDN function。只有特定目标平台官方说明支持且已批准实验时，才交付可选实现。

## 10. 开发 handoff 示例

```md
### /products/example

- 当前：200，但 canonical 指向参数 URL；渲染 HTML 无产品主内容。
- 目标：canonical 指向无参数首选 URL；产品名称、规格与主要内链出现在初始渲染结果。
- 开发验收：状态/redirect/canonical 一致；JSON-LD 可解析且与页面可见价格/库存一致；build 通过。
- 复验：发布后重新抓取响应与渲染 HTML，记录 GSC URL Inspection；排名效果待后续抓取窗口。
```

## 11. 复验

用户或开发者应用修改后：

1. 清理平台/CDN 缓存或确认 preview URL。
2. 重新检查状态码、headers 与渲染 HTML。
3. 解析 schema、robots、sitemap、canonical 和 hreflang。
4. 在目标设备完成核心任务/表单。
5. 分开报告“产物已生效”和“Google 待重抓/重新评估”。

没有复验的 paste-ready 代码只能标为“待实施”，不能标为“已修复”。
