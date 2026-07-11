# 技术栈与编辑模式检测

FIX 或代码级 AUDIT 开始前，先识别技术栈、渲染层、部署形态和权限。目标规范始终来自 `seo-fix-principles.md`，adapter 只决定落地位置。

## 检测顺序

1. 本地代码/配置/依赖。
2. 构建与部署配置。
3. 线上 headers、HTML 指纹和资源路径。
4. CMS/后台/模板权限。
5. 无法确认时标记 Unknown，不凭一个弱信号猜测。

## 本地代码指纹

| Stack | 主要信号 | Adapter / 验证 |
|---|---|---|
| Next.js App Router | `next.config.*`、`app/**/page.*`、`layout.*`、package `next` | `stack-adapters/nextjs.md`；build/type/lint/render |
| Next.js Pages Router | `pages/_app.*`、`pages/_document.*`、`next.config.*` | Next adapter，需映射 Pages Router API |
| WordPress | `wp-config.php`、`wp-content/`、theme/plugin | `wordpress.md`；PHP/CMS/plugin 输出 |
| Shopify theme | `layout/theme.liquid`、`config/settings_schema.json`、Liquid templates | `shopify.md`；theme preview/live render |
| Astro | `astro.config.*`、`.astro` pages/layouts | `static-astro.md`；build + dist |
| Hugo | `hugo.toml`/config、`layouts/` | `static-astro.md`；hugo build |
| Jekyll | `_config.yml`、`_layouts/`、`_includes/` | `static-astro.md`；jekyll build |
| Nuxt | `nuxt.config.*`、`.vue` pages、package `nuxt` | 以 `seo-fix-principles.md` 定目标，按 Nuxt head/route API 落地 |
| SvelteKit | `svelte.config.*`、`src/routes/**/+page.*` | 按 SvelteKit SSR/head/adapter 验证 |
| Remix/React Router | `app/routes`、`entry.server.*`、相关 package | 按 route meta/server render 验证 |
| Gatsby | `gatsby-config.*`、`gatsby-node.*` | 检查 SSR/static HTML 与插件重复输出 |
| Vite/React SPA | `vite.config.*`、client routes、无 SSR | 重点验证 prerender/SSR、真实状态码与初始 HTML |
| Plain/static HTML | `index.html`，无框架配置 | `static-astro.md`，直接检查输出 |

没有专用 adapter 时，仍按目标规范执行；不能把它硬套成 Next.js。

## Headless CMS

Contentful、Sanity、Strapi、WordPress headless、Shopify Hydrogen 等只说明内容来源。真正负责 `<head>`、状态码、canonical、schema、sitemap 和渲染的是前端/hosting 层。

输出应同时记录：

```text
Content source: [CMS]
Rendering stack: [framework]
Hosting/runtime: [platform]
Edit mode: [code/template/CMS/URL-only]
```

## 线上指纹

组合使用，不能只凭一个信号：

- WordPress：`/wp-content/`、generator、Yoast/Rank Math/AIOSEO 注释或 graph。
- Shopify：`cdn.shopify.com`、Shopify scripts/headers、`myshopify.com` 关联。
- Next.js：`/_next/` assets、`__NEXT_DATA__`（仅部分版本/Router）。
- Nuxt：`/_nuxt/`、`__NUXT__`。
- Webflow：`data-wf-*`、webflow assets。
- Wix：Wix static/Thunderbolt 指纹。
- Squarespace：Squarespace static scripts/blocks。
- Framer：Framer 生成器/资源。
- Cloudflare/Vercel/Netlify headers 只说明边缘/hosting，不一定说明应用框架。

检查响应 headers、redirect chain、script/style URL、generator、HTML comments 和 JSON payload。CDN 可能隐藏 origin，浏览器扩展/代理也可能注入标记。

## SEO 插件检测

WordPress/Shopify 等平台先识别是谁拥有 metadata/schema/sitemap：

- Yoast、Rank Math、AIOSEO、SEOPress。
- Shopify theme 自带、SEO app、feed app。
- 多插件/主题同时输出时优先消除重复所有权，不能继续叠标签。

## 编辑模式

```text
有本地代码与部署权限？
├─ 是：code mode -> 改源码，运行项目验证命令和渲染检查
└─ 否：有模板/theme 权限？
   ├─ 是：template mode -> preview/publish 后验证
   └─ 否：有 CMS SEO/custom-code 权限？
      ├─ 是：CMS mode -> 使用现有字段/插件，避免重复输出
      └─ 否：URL-only -> Fetch、Diff、精确 handoff、应用后复验
```

Wix、Squarespace、Webflow、Framer、Carrd 不必自动判为完全锁定；先确认套餐和实际 UI 权限。

## 必须输出的检测结果

```text
Stack:
Router/rendering:
Content source:
Hosting/runtime:
SEO owner/plugin:
Edit mode:
Selected adapter:
Confidence and evidence:
Unverified assumptions:
```

AUDIT 交给 FIX 时必须带上这份结果，避免下一阶段重新猜栈。
