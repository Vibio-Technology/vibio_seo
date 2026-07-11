# 分面导航、参数与抓取空间治理

最后核验：2026-07-11。本协议适用于筛选、排序、分页、规格组合和其他可能扩张 URL 空间的导航系统。

## 官方来源

- Google 分面导航抓取管理：https://developers.google.com/search/docs/crawling-indexing/crawling-managing-faceted-navigation
- Google URL 结构建议：https://developers.google.com/search/docs/crawling-indexing/url-structure
- Robots.txt：https://developers.google.com/search/docs/crawling-indexing/robots/intro
- Canonical：https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls
- HTTP 状态码：https://developers.google.com/search/docs/crawling-indexing/http-network-errors

## 先决定哪些分面值得被发现

不要先给所有筛选 URL 加 canonical 或 `noindex`，再猜 Google 会如何处理。先按真实需求、独立内容、稳定库存和商业路径定义两类 URL：

- **索引目标**：存在已验证的独立搜索任务，页面能提供稳定、实质不同的商品/内容集合，有唯一标题与正文，并获得明确内链。
- **交互状态**：只帮助当前用户排序或缩小结果，没有独立搜索价值，或组合空间过大、重复、稀疏、不稳定。

默认只开放有限、可解释的索引目标。筛选控件可继续服务用户，但不代表每个状态都应成为可抓取、可索引 URL。

## 不需要索引的分面

若分面 URL 不需要出现在 Google 产品中，优先从 URL 生成和链接图源头收敛：

1. 为筛选参数建立 allowlist/denylist，禁止会话、视图、排序、跟踪和任意组合进入可索引 URL 集。
2. 内链、sitemap 和导航只暴露规范列表页及获批分面；不要让模板持续生成无限组合。
3. 对明确的参数模式使用范围最小且经过测试的 `robots.txt` 抓取规则，保留商品详情、规范列表、CSS/JS 和其他必要资源。
4. 若产品允许仅在客户端表达状态，可使用 URL fragment；Google 通常不使用 fragment 抓取和索引其中状态，因此它也不能作为独立搜索落地页。

`robots.txt` 管抓取，不是移除或 `noindex` 工具。被 robots 阻断的 URL 仍可能因外链而被发现，且爬虫无法读取页面上的 `noindex` 或 canonical。对已经索引的参数 URL，应先规划可抓取的 301、404/410、`noindex` 或规范化阶段，再决定何时阻断抓取。

Canonical 和链接上的 `rel="nofollow"` 可能减少部分重复抓取，但 Google 官方指出它们长期通常不如直接抓取控制有效。Canonical 还是信号而非命令，不能补救无限 URL 生成。

## 需要抓取/索引的分面 URL 合同

对获批分面执行确定性 URL 合同：

- 查询参数使用标准的 `?` 与 `&` 分隔，不用逗号、分号或括号模拟参数边界。
- 若把筛选编码在路径中，筛选维度的逻辑顺序必须稳定；同一组合不得因点击顺序产生多个 URL。
- 参数名、值、大小写、编码、顺序和默认值采用唯一规范形式；内部链接永远输出该形式，重复形式 301 到唯一 URL 或返回正确错误状态。
- 禁止重复筛选、互斥/无意义组合、空值、任意键、无限排序、无限日历和无界分页进入链接图。
- Sitemap 只包含获批的 canonical、可索引 URL；canonical、重定向、内链和分页信号保持一致。
- 每个索引目标返回真实 `200`，具备独立可见内容，并能在没有脚本失败或登录状态的情况下完成核心任务。

## 空结果与错误组合

Google 官方分面指南要求，无结果筛选、重复筛选、无意义组合和不存在的分页 URL 返回该 URL 下真实 HTTP `404`。不要把它们 `200` soft-404，也不要全部重定向到首页、父类目或统一错误 URL。

SPA 也应尽量通过边缘层/服务器为 deep link 返回正确状态。若架构暂时做不到，至少让渲染内容明确不可用、阻止继续生成链接，并把服务器状态修复列为技术债；客户端“未找到”文字不能证明 HTTP 404。

## 抓取控制变更的验证

上线前：

- 枚举参数排列、重复值、空值、非法值、无结果、超界分页和编码变体；
- 用真实 robots 解析规则检查允许/禁止样本，避免通配符误伤业务查询参数；
- 抓取一个代表性目录，比较唯一内容 URL、参数 URL 数量、深度、canonical 目标和内部入链；
- 检查 HTTP 源码与浏览器 DOM，确认客户端不会重新生成被治理的 URL。

上线后结合服务器日志、Bing/Google 站长工具、抓取统计和索引报告观察。记录抓取量、发现速度、索引 URL 形态和服务器资源，但不要把抓取下降自动等同于排名提升。

## 决策记录

```text
Facet/parameter:
User purpose:
Search-demand evidence:
Index policy: approved | interaction-only | blocked | retired
Canonical URL form:
Internal-link rule:
Robots rule (if any):
Invalid/empty behavior:
Representative test URLs:
Pre/post crawl evidence:
Index observation:
Business/search outcome:
```
