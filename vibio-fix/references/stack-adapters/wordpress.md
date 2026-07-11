# 技术栈适配器：WordPress

这是面向 WordPress 的落地实施层。目标规范（“正确结果应是什么样”）见 `../seo-fix-principles.md`。WordPress 几乎总是由 SEO 插件承担主要工作，**应通过插件完成配置，不要手写随后会被插件覆盖的标签。**

## 第一步：识别 SEO 插件

| 识别信号 | 插件 | 所在路径 |
|---|---|---|
| HTML 中出现 `<!-- This site is optimized with the Yoast SEO plugin -->` | Yoast SEO | `wp-content/plugins/wordpress-seo/` |
| `<!-- Search engine optimization by Rank Math -->` | Rank Math | `wp-content/plugins/seo-by-rank-math/` |
| `aioseo`/`_aioseo_` meta | All in One SEO | `wp-content/plugins/all-in-one-seo-pack/` |
| 未发现上述信号 | 原始主题 | `header.php` / `wp_head` hook |

标题模板、meta description、canonical、OG / Twitter 以及大多数 JSON-LD 均由插件管理。在文章编辑器的 SEO 设置框中编辑单篇内容的值，在插件的 Search Appearance / Titles & Meta 设置中编辑全局模板。只有没有插件，或插件无法覆盖所需功能时，才回退到主题级 `functions.php` 修改。

## 编辑模式

- **拥有完整代码 / SFTP 权限** → 编辑 `functions.php`、主题模板（`header.php`、`single.php`、`page.php`、`archive.php`）和 `mu-plugins/`。可以通过代码添加 filter / hook。
- **仅有管理员权限（托管版 WP.com，无主题编辑器）** → 实际按 CMS 粘贴模式处理：通过插件 UI 和单篇内容的 SEO 设置框完成配置。若某个标签确实无法通过 UI 设置，则回退到 `url-only.md` 指引。

## 实施配方

### 标题与 meta description
- 单篇内容：在每篇文章或页面下方的 Yoast / Rank Math 设置框中配置。
- 全局模板：在 Search Appearance（Yoast）或 Titles & Meta（Rank Math）中配置，例如 `%%title%% %%sep%% %%sitename%%`。
- 原始主题（无插件）：在 `functions.php` 中确保已调用 `add_theme_support('title-tag')`；再通过 `wp_head` action，从摘要或自定义字段输出 `<meta name="description">`。

### Canonical
插件会自动输出自指 canonical。只有页面确属重复内容时，才在 SEO 设置框的 Advanced 部分按篇覆盖。启用插件时不要在主题中手动添加 `<link rel="canonical">`，否则会产生重复标签。

### 结构化数据
- Yoast / Rank Math 通常会输出包含 `Organization` / `WebSite` / `WebPage` / `BreadcrumbList` 的 `@graph`。先准确配置组织和站点信息，再检查首页及代表性页面类型；不要额外手写重复图谱。
- `Product` → 只有价格、库存状态、评价和 offer 数据与可见内容一致时，才使用 WooCommerce 或插件输出。
- Google FAQPage 和 HowTo 富媒体搜索结果均已退役。可以为用户保留问答和步骤区块，但不要为了宣称能改善 Google 排名、富媒体搜索结果或 AI 引用而启用或添加相应 schema。
- 使用 `seo-schema` 和 Google 当前在线功能文档验证现阶段支持的输出。

### OG / Twitter 与品牌站点名
- 准确配置 Organization 信息，但 Site / WebSite 名称应使用用户普遍熟悉的简洁品牌名。若完整法定实体名称不同，应将其用于 Organization 和必要的法律信息场景，而不是自动写入 `og:site_name` 或 `WebSite.name`。
- 社交分享图片：在 Social 设置中将默认 OG 图片设为 1200×630 的横版图片，并可在 SEO 设置框的 Social 标签页中按篇覆盖。
- 首页可见文案和 meta description 应面向用户，准确说明实际产品或服务；不要仅为追求查询词高亮而插入法定名称。

### robots 与 sitemap
- Sitemap：Yoast → `/sitemap_index.xml`；Rank Math → `/sitemap_index.xml`。不要同时启用第二个 sitemap 插件。
- `robots.txt`：通过插件的 Tools → File editor 编辑，或编辑实体 `robots.txt` 文件。确保禁止抓取 `/wp-admin/`，但允许 `/wp-admin/admin-ajax.php`，并引用 sitemap。
- 可索引性：WordPress 最常见的问题是勾选了 **Settings → Reading → "Discourage search engines"**，这会在全站注入 `noindex`。应首先检查此项，同时检查 SEO 设置框中单篇内容的 `noindex` 开关。

### 图片
- 每张图片的 `alt` 文本在 Media Library 或区块编辑器中设置。批量修复时可使用插件工具或专用 alt-text 插件。装饰性图片应使用空 `alt=""`。
- 使用性能插件或主题支持来提供 WebP 和 lazy-load。

### AI 搜索
Google Search 会忽略 `llms.txt`；不要为了改善 Google 可见性而安装相关插件或添加 rewrite。只有目标平台已有支持文档且实验获得批准时，才考虑使用该文件。

## 验证
抓取最终线上响应，而不是 PHP 源码，因为插件在渲染时运行。解析 DOM，检查 title、canonical、OG 和 JSON-LD 的实际值；验证可索引性时，应解析最终生效的 `<meta name="robots">` 指令，以及重定向链中每一跳的 `X-Robots-Tag` 响应头：
```bash
curl -sL https://example.com/ | grep -oiE 'name="description"[^>]*|rel="canonical"[^>]*|property="og:site_name"[^>]*|"@type":"(Organization|WebSite)"'
curl -sSIL https://example.com/ | grep -i '^x-robots-tag:'
```
不能因为 JSON、脚本、注释或文档中任意出现了 `noindex` 字符串，就判定页面不可索引。修改后应清除缓存插件和 CDN 缓存，否则验证到的可能是旧页面。SERP 变化仍需等待搜索引擎重新抓取。
