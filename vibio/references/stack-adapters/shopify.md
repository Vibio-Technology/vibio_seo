# 技术栈适配器：Shopify

这是 Shopify 的落地实施层，目标规格见 `../seo-fix-principles.md`。Shopify 会自动生成 canonical、sitemap 和基础 metadata，但具体表现受主题、应用和资源配置影响；定制主要位于 **Liquid 主题模板**、**主题设置**与**资源级 metafield**。

## 编辑模式

- **可编辑主题代码**（Online Store -> Themes -> Edit code）：修改 `layout/`、`templates/`、`sections/`、`snippets/` 中的 `.liquid` 文件，这是主要路径。
- **无主题权限/只能用应用**：按 CMS 模式使用后台 SEO 字段（Online Store -> Preferences，以及产品/集合的 Search engine listing）和现有 SEO 应用；界面未暴露的能力按 `url-only.md` 降级。

## Shopify 自动生成的内容（修改前先验证）
- Shopify 会输出 canonical，但集合、产品变体、筛选器、应用和主题都可能改变最终目标。检查代表性页面的渲染值并确认目标正确；不要手工再加第二个标签。
- `sitemap.xml`：自动生成在 `/sitemap.xml` 并引用子 sitemap，不能直接编辑；通过产品、集合和页面的发布状态控制纳入范围。
- `robots.txt`：通过 `templates/robots.txt.liquid` 定制。

## 实施方法

### Title 与 meta description
- 全局：`layout/theme.liquid` 的 `<head>` 通常包含 `<title>{{ page_title }}{% ... %}</title>` 和 `{% if page_description %}<meta name="description" content="{{ page_description }}">{% endif %}`。
- 资源级：产品、集合、页面和博客文章的 Search engine listing 设置 `page_title` 与 `page_description`。
- 在 `theme.liquid` 修正薄弱模板，例如品牌名是否作为后缀由页面可读性与站点惯例决定，不套固定字符规则。

### 结构化数据
- Shopify 主题差异很大，许多主题通过 `{{ product | structured_data }}` 或自定义 section 输出基础 `Product` JSON-LD。验证实际渲染标记、防止重复 Product graph；只有可见数据真实支持时才添加 `Offer`/`AggregateRating`。
- 若主题尚未提供有效的企业/站点名标记，仅在首页按 Google 当前文档添加 `Organization` 与 `WebSite`，不要全站重复输出：
  ```liquid
  <script type="application/ld+json">
  {"@context":"https://schema.org","@type":"Organization",
   "name":{{ shop.name | json }},
   "url":{{ shop.url | json }},
   "logo":{{ 'logo.png' | asset_url | prepend: 'https:' | json }}}
  </script>
  <script type="application/ld+json">
  {"@context":"https://schema.org","@type":"WebSite",
   "name":{{ settings.site_name | default: shop.name | json }},
   "alternateName":{{ shop.name | json }},
   "url":{{ shop.url | json }}}
  </script>
  ```
- 使用 `seo-schema` 验证；需要 Shopping/商城深度时使用 `seo-ecommerce`。

### OG / Twitter 与品牌站点名
- 在 `theme.liquid` 的 `<head>` 检查 `og:title`、`og:description`、`og:url`、`og:type`、`og:image` 和 `og:site_name`。使用用户熟悉的简洁品牌/站点名，通常是 `shop.name` 或可编辑的 `settings.site_name`；若法定主体名不同，仅放在 `Organization` 或必要法律披露中。
- 许多主题会使用产品/集合主图作为 OG 图片；首页默认图应是可代表业务的横版真实资产，常见社交预览规格为 1200x630，但应核验目标平台当前要求。

### robots.txt
只有已验证的抓取/索引问题确实需要时才定制。通过当前 `robots.default_groups` 对象保留 Shopify 默认规则，再追加范围最小的定向规则；不要用 `content_for_header` 或已过时的 `robots.default_rules` 替换默认内容。

```liquid
{% for group in robots.default_groups %}
  {{- group.user_agent -}}
  {% for rule in group.rules %}
    {{- rule -}}
  {% endfor %}
  {% if group.user_agent.value == '*' %}
    {{- 'Disallow: /example-private-path' -}}
  {% endif %}
  {% if group.sitemap != blank %}
    {{ group.sitemap }}
  {% endif %}
{% endfor %}
```

部署前将输出与线上默认规则对比，并验证产品、集合、媒体、CSS 和 JS 资源仍可抓取。官方参考：https://shopify.dev/docs/storefronts/themes/seo/robots-txt.md

### 分面与重复 URL
集合筛选/排序 URL 可能制造大量重复空间，但部分分面也可能承接独立且已验证的需求。先定义分面导航策略：决定哪些组合值得稳定、可抓取页面和内链，哪些不应成为索引目标。canonical 只是信号，要验证渲染目标和内链行为，并用抓取/索引证据判断，不假设 Shopify 默认设置能解决所有情况。大型目录使用 `seo-ecommerce` + `seo-technical` 评估索引膨胀。

### 图片
在后台为图片设置 `alt`，或在 Liquid 中使用 `{{ image.alt }}`。Shopify 的 `image_url` 可通过 `width:` 输出响应式资源；模板应传入合理尺寸。信息性图片写准确 alt，装饰图使用空 alt。

### AI 搜索
Google Search 会忽略 `llms.txt`；不要为了 Google 可见性添加应用、代理或 CDN 路由。只有明确目标平台有文档支持，且实验价值足以覆盖维护成本时，才考虑可选文件。

## 验证
抓取线上店铺 URL 并检查 HTTP 响应源码；发布前通过主题预览 URL 验证。以下 `curl` 不执行 JavaScript，不能证明客户端应用或脚本改写后的 DOM：
```bash
curl -sL https://shop.example.com/ | grep -oiE 'property="og:site_name"[^>]*|"@type":"(Organization|WebSite|Product)"|rel="canonical"[^>]*'
```
未发布主题的改动不会出现在正式 URL。完成预览或发布后的产物验证后，SERP 变化仍需等待重新抓取，不能把部署成功称为排名生效。

若主题 app extension 或客户端脚本会改 metadata、canonical、JSON-LD、正文或链接，按 `../javascript-rendering.md` 另采集浏览器 DOM，并检查源码与 DOM 冲突、匿名权限、失败 network 请求和 console 异常。
