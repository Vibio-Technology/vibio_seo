# JavaScript 渲染证据与 SPA 验证

最近核验 Google 官方资料：2026-07-11。易变行为以实时官方文档为准。

本文件解决一个边界问题：HTML 被解析不等于 JavaScript 已执行。HTTP 源码、静态构建文件和浏览器 DOM 能回答不同问题，三者不得互相冒充。

主要官方来源：

- JavaScript SEO 基础：https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics
- 排查 JavaScript 搜索问题：https://developers.google.com/search/docs/crawling-indexing/javascript/fix-search-javascript
- 可抓取链接：https://developers.google.com/search/docs/crawling-indexing/links-crawlable
- 动态渲染：https://developers.google.com/search/docs/crawling-indexing/javascript/dynamic-rendering
- Robots meta：https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag
- Canonical：https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls
- 技术最低要求：https://developers.google.com/search/docs/essentials/technical

资格与承诺边界同时遵守 `references/google-search-docs.md` 和 `references/evidence-policy.md`。

## 证据模式

| `evidence_mode` | 输入 | 可以证明 | 不能证明 |
|---|---|---|---|
| `http_source` | 内置有界抓取器获取的有限 HTTP 响应 | 本次响应的状态、headers、重定向链和响应源码 | JavaScript 执行后的 metadata、正文、链接、路由状态或 console/network 成功 |
| `static_build` | 本地构建的 `.html/.htm` 文件 | 构建产物中实际存在的字段、链接和文件关系 | 生产 HTTP、CDN/WAF/重写、浏览器执行 JavaScript后的 DOM |
| `browser_dom` | 外部真实浏览器导出的最终 DOM 文件/目录 | 有完整 provenance 时，证明指定 URL 与 DOM SHA-256、浏览器和采集时点已绑定 | 工具自行执行了 JavaScript、HTTP 状态/重定向、所有用户状态、History API 全流程或没有 JS 异常 |

`browser_dom` 表示输入声称来自浏览器，不自动等于已验证。只有同时提供 `--browser-provenance`，并让其中每个 URL 的 SHA-256 与导入 DOM 完全一致，报告才会设置 `client_side_dom_verified=true`。即使如此，也只能描述该快照。`scripts/seo_inspect.py --start-url` 的内置抓取器绝不执行 JavaScript；它只连接经 DNS 全量校验后的公网 IP，每次重定向重新校验，默认把 robots 自动发现的 sitemap 限于站点同源，并以 `Content-Length` 和实际读取双门禁限制单响应大小。`--site-dir` 也只解析静态构建文件。显式 `--sitemap` 可以授权跨源公网 sitemap，但不会授权本机、私网或链路本地目标。

未取得浏览器 DOM 时，把客户端 metadata、正文、canonical、结构化数据和内链写为“未经 JavaScript 渲染验证”。不要用“页面没有”替代“HTTP 源码/静态构建中没有”。

## 采集与对比

先保留输入 URL、采集时间、浏览器/设备、登录或 cookie 状态、是否禁用缓存、最终地址，以及 console/network 的失败记录。DOM 文件不携带这些上下文，必须在审计记录中补齐。

三种输入分别运行：

```bash
# 有限 HTTP 源码；不会执行 JavaScript
python scripts/seo_inspect.py --start-url https://example.com/ --max-pages 20 \
  --json-out .vibio/runs/http-source.json --markdown-out .vibio/runs/http-source.md

# 静态构建；不会启动浏览器
python scripts/seo_inspect.py --site-dir dist --base-url https://example.com/ \
  --json-out .vibio/runs/static-build.json --markdown-out .vibio/runs/static-build.md

# 浏览器导出的单页 DOM，配对初始源码快照与浏览器 provenance
python scripts/seo_inspect.py --rendered-dom .vibio/evidence/rendered.html \
  --source-input .vibio/evidence/source.html \
  --browser-provenance .vibio/evidence/browser-provenance.json \
  --base-url https://example.com/product/ \
  --json-out .vibio/runs/browser-dom.json --markdown-out .vibio/runs/browser-dom.md
```

目录输入应按 URL 路径镜像，例如 `index.html`、`products/index.html`。单文件输入映射到 `--base-url`。配对时两侧使用相同文件/路径布局；JSON 报告会保存每页源码与 DOM 的 SHA-256，以及 title、description、robots、canonical、内链、JSON-LD 类型、可见文字和结构计数差异。

provenance 文件使用以下最小结构。`documents` 必须覆盖本次导入的每个 URL；`sha256` 是对应 DOM 文件的原始字节摘要，`captured_at` 必须带 UTC offset。工具会拒绝重复 URL、缺页、摘要不一致、无时区时间或 `javascript_enabled=false`：

```json
{
  "schema_version": "1.0",
  "capture_method": "Playwright page.content()",
  "browser": "Chromium 140",
  "captured_at": "2026-07-11T10:00:00+08:00",
  "javascript_enabled": true,
  "documents": [
    {
      "url": "https://example.com/product/",
      "sha256": "<rendered.html 的 64 位 SHA-256>"
    }
  ]
}
```

不要把任意下载的 HTML 手工标成已验证 `browser_dom`，也不要在 DOM 修改后复用旧摘要。没有 provenance 时工具仍可做有限字段解析和源码差异，但会把客户端状态列为未验证。浏览器不可用时继续做 `http_source` 或 `static_build` 检查。

## SPA 与客户端渲染检查

### 1. HTTP、deep link 与 soft 404

- 直接请求每类真实路由和一个确定不存在的路由，记录每一跳与最终 HTTP 状态；浏览器 DOM 文件无法提供这一证据。
- 不存在内容应返回真实 404/410，或按 Google 的 JavaScript 站点建议跳转到服务器返回 404 的 URL。不要让所有未知路径都返回 `200` 加“未找到”文案。
- 对受保护页面分别测试匿名、过期会话和正常权限。Googlebot 不登录、不开会员权限，也不会通过点击解锁主内容。
- API 失败、超时或被 robots/CORS/WAF 拒绝时，页面应保留有意义的 HTTP/HTML 回退；不能永久停在空壳或 loading 状态。

Soft 404 需要“HTTP + 最终可见内容”共同判断。只有 DOM 或只有字符串命中都不足以断言。

### 2. 路由与 History API

- 为每份可索引内容提供稳定、可直接打开的 HTTP(S) URL；不要把 `#/product` 片段当作新页面发现机制。
- 使用 History API 时，测试 `pushState/replaceState` 后的地址、刷新、直接打开、前进/后退，以及分享该 URL 后的服务器回退。
- 每次路由切换后核对 title、canonical、robots、主内容和内部链接是否与地址一致，并检查旧页面信号是否残留。
- DOM 快照只能证明一个路由状态。未实际执行导航序列时，将 History API 行为标为未验证。

### 3. 初始 noindex

Google 明确警告：不要在初始源码中放 `noindex` 再依赖 JavaScript 移除，因为 Google 看到 `noindex` 后可能跳过渲染。希望索引的 URL 应在初始 HTTP HTML 和最终 DOM 中都没有 `noindex`；同时检查 `X-Robots-Tag`。

工具在配对源码与浏览器 DOM 时会报告 `rendering.initial-noindex-removed`。该 finding 证明两个快照不同，不证明 Google 已采用任一状态。

### 4. Canonical 与 metadata

- 初始源码和最终 DOM 应由单一所有者输出一致的 title、robots 和 canonical。
- Google 可以处理 JavaScript 注入的 canonical，但不要在源码放一个值后用客户端改成另一个值；框架、插件和标签管理器也不能重复输出。
- 将源码与 DOM 的变化记录为差异，不把 HTTP 源码的值称为“最终渲染值”。有 GSC 时再核对 Google-selected canonical。

### 5. 可抓取链接

Google 通常可靠抓取带可解析 URL 的 `<a href="...">`。重要导航和上下文入口不要只使用 `onclick`、`<div role="link">`、按钮状态或无法解析的 JavaScript URL。

在初始源码和最终 DOM 分别检查：

- `href` 是否为真实 HTTP(S) 或可解析相对 URL；
- 锚文本是否说明目标；
- 客户端新增链接是否在错误、匿名和直接打开状态下仍存在；
- sitemap 不能替代正常内部链接。

`links.non-crawlable-control` 只说明当前 HTML 证据中存在链接式控件，不证明所有目标都不可发现。

### 6. 主内容、权限与失败回退

- 产品事实、正文、主导航和核心转化不应只在滚动、点击、同意弹层或登录后才注入。
- 用匿名/无 cookie 浏览器复测，并检查关键 API、JS bundle、CSS 和图片是否可被抓取与正常返回。
- 对 JS 禁用、bundle 404、API 5xx/403、慢响应和 hydration 失败测试有意义的回退；至少不能错误返回“成功且空白”的页面。
- 不因浏览器能在一个登录会话中看到内容，就断言 Googlebot 或普通匿名用户可见。

### 7. JavaScript 异常

保存 console error、unhandled rejection、失败 network 请求、CSP/CORS 错误和被扩展注入的异常。区分站点自身错误与浏览器扩展/代理噪声。重新加载和客户端导航都要检查；一次 DOM 导出可能在异常发生前或缓存命中后看似正常。

## 验收结论

分别给出：

```text
HTTP source/status: passed | failed | unverified
Static build: passed | failed | not applicable
Browser DOM sample: passed | failed | unverified
Source-vs-rendered consistency: passed | failed | not compared
SPA routes / soft-404 / permissions / JS console: passed | failed | unverified
Google crawl/index/search effect: pending evidence
```

动态渲染是 Google 文档中的 workaround，不是长期首选方案。优先服务端渲染、静态渲染或 hydration，使用户与抓取器获得一致内容；任何产物通过都不能证明已抓取、已索引、排名或收入提升。
