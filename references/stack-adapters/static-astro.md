# 技术栈适配器：静态站（Astro / Hugo / Jekyll / 纯 HTML）

这是面向静态站点生成器和手写 HTML 的落地实施层。目标规范见 `../seo-fix-principles.md`。该适配器**最贴近原则本身**：直接编辑生成 HTML 的模板或布局，中间没有插件或平台介入。不同生成器采用相同模式，只有模板语法不同。

## `<head>` 位于何处

| 生成器 | 布局 / head 文件 | 页面级 front matter |
|---|---|---|
| Astro | `src/layouts/*.astro`、`<BaseHead>` 组件 | `.astro` / `.md` 中的 front matter |
| Hugo | `layouts/_default/baseof.html`、`layouts/partials/head.html` | `content/**` 中的 front matter |
| Jekyll | `_layouts/default.html`、`_includes/head.html` | 页面或文章中的 YAML front matter |
| 11ty | `_includes/layouts/base.njk` | front matter |
| 纯 HTML | 每个文件的 `<head>`（使用 SSI 或构建流程时也可能是共享 include） | 直接写在文件中 |

通用做法：让布局接收页面级 `title` / `description` / `image` / `canonical` 变量，并配置合理的全站默认值，使每个页面都能获得正确标签，而不必重复编写样板代码。

## 实施配方

### 标题与 meta description
从 front matter 读取，并设置回退值：
- Astro：`<title>{title ?? site.title}</title>`，`<meta name="description" content={description ?? site.description}>`。
- Hugo：`<title>{{ .Title }} | {{ .Site.Title }}</title>`，`<meta name="description" content="{{ .Description | default .Site.Params.description }}">`。
- Jekyll：`{{ page.title | default: site.title }}`，`{{ page.description | default: site.description }}`。

### Canonical
在 head partial 中，用站点基础 URL 与页面路径生成绝对 canonical URL：
- Astro：`<link rel="canonical" href={new URL(Astro.url.pathname, site.url)}>`。
- Hugo：`<link rel="canonical" href="{{ .Permalink }}">`。
- Jekyll：`<link rel="canonical" href="{{ page.url | absolute_url }}">`。
正确配置站点基础 URL（astro.config 中的 `site`、Hugo 中的 `baseURL`、Jekyll `_config.yml` 中的 `url`）。基础 URL 一旦出错，所有 canonical 和 OG URL 都会出错。

### 结构化数据
先确认没有插件或组件输出同一份图谱，然后仅在首页渲染首页级 `Organization` 和 `WebSite` JSON-LD。共享基础布局可以包含首页条件判断，但不得在每个 URL 上重复首页实体标记。只有当可见页面类型匹配且 front matter 真实准确时，才添加 `Article` / `BlogPosting` 和 `BreadcrumbList`。使用 `seo-schema` 和当前功能文档验证结果。

### OG / Twitter 与品牌站点名
在 head partial 中输出 `og:title/description/url/type/image` 和 `og:site_name`，站点名使用用户熟悉的简洁品牌名或常用站名。若法定实体名称不同，应将其保留在 Organization 和法律信息场景中，不要强行用作站点名。默认 OG 图片应采用有代表性的横版素材，并允许通过 front matter 按页面覆盖。将 `twitter:card` 设为 `summary_large_image`。

### robots.txt 与 sitemap
- Sitemap：Astro 使用 `@astrojs/sitemap` 集成；Hugo 原生输出 `sitemap.xml`；Jekyll 使用 `jekyll-sitemap` 插件。确保 sitemap 已生成，并在 `robots.txt` 中引用。
- `robots.txt`：静态文件分别放在 `public/`（Astro）、`static/`（Hugo）或根目录（Jekyll）。允许抓取 `/`，引用 sitemap，并设置 host。

### 可索引性
静态站很少意外输出 `noindex`，但仍需检查基础布局中是否残留 `<meta name="robots" content="noindex">`。这种情况常见于将“即将上线”模板直接发布到生产环境。还要检查托管平台（Netlify / Vercel / Cloudflare Pages）是否对已转为生产环境的预览部署保留了密码保护或 `noindex`。

### 图片
使用生成器的图片管线（Astro `<Image>`、Hugo 图片处理）生成现代格式并提供稳定尺寸。信息型图片应使用简洁的 alt 文本说明其用途；装饰性图片使用空 `alt=""`，且不应重复邻近文本。需要深入处理时使用 `seo-images`。

### AI 搜索
Google Search 会忽略 `llms.txt`；不要把创建该文件当作改善 Google 排名或 AI 可见性的修复手段。只有当另一个明确针对的平台已有支持文档且实验获得批准时，才可选用该文件，并应从同一内容源生成，避免内容漂移。

## 验证
完成构建后，在输出目录中检索结果，无需启动服务器；这只能记为 `static_build`，不能证明生产 HTTP 或浏览器 JavaScript：
```bash
# Astro：npm run build → dist/；Hugo：hugo → public/；Jekyll：jekyll build → _site/
grep -roiE 'property="og:site_name"[^>]*|"@type":"(Organization|WebSite)"|rel="canonical"[^>]*' <output-dir>/index.html
# 解析代表性页面最终生效的 meta robots 指令，并检查线上 X-Robots-Tag 响应头。
```
不要因为 JSON、脚本、注释或文档中任意出现了 `noindex` 字符串，就判定页面不可索引。随后部署并重新抓取线上 URL，确认托管平台实际提供的是本次构建结果；存在客户端 hydration/路由时再按 `../javascript-rendering.md` 采集浏览器 DOM。SERP 变化仍需等待搜索引擎重新抓取。
