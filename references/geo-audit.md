# GEO Audit Protocol — AI 搜索就绪度审查

对任意站点执行 GEO 专项审计，产出 0-100 分评分和优先级修复清单。可独立运行，也可作为 AUDIT 模式的 GEO 子项。

---

## 审计流程

### Phase 0：爬取与发现

```bash
# 1. 检查 llms.txt
curl -sL https://example.com/llms.txt | head -50

# 2. 检查 AI 爬虫可访问性
curl -sL https://example.com/robots.txt | grep -iE "GPTBot|CCBot|Google-Extended|anthropic|PerplexityBot"

# 3. 无 JS 渲染检查（AI 爬虫通常不执行 JS）
curl -sL https://example.com/ | grep -c "<h1"  # 应有输出
curl -sL https://example.com/product-page | grep -c "<h1"  # 关键页面也应有输出

# 4. 结构化数据检查
curl -sL https://example.com/ | grep -o '"@type"[^,}]*' | sort | uniq -c

# 5. 抽样页面段落可摘引性
curl -sL https://example.com/key-page | grep -oP '<(h[1-3]|p)>[^<]{20,150}</\1>' | head -20
```

### Phase 1：可爬取性审查（25 分）

| 检查项 | 分值 | 判定方法 |
|--------|------|---------|
| llms.txt 存在 | 8 | `curl /llms.txt` → 200 OK |
| llms.txt 格式正确 | 5 | H1 标题 + blockquote 摘要 + 分段链接列表含描述 |
| llms.txt 内容更新（≤30 天） | 2 | 检查描述中的产品/页面是否为当前版本 |
| GPTBot 未被屏蔽 | 2 | `robots.txt` 中无 `Disallow: /` for GPTBot |
| Google-Extended 未被屏蔽 | 2 | 关键：AI Overviews 数据源 |
| CCBot 未被屏蔽 | 1 | Common Crawl，被多个 AI 引擎使用 |
| PerplexityBot 未被屏蔽 | 1 | |
| anthropic-ai 未被屏蔽 | 1 | Claude |
| 关键内容在无 JS 环境下可读 | 3 | `curl \| grep` 验证 H1/H2/正文存在 |

### Phase 2：结构化数据审查（25 分）

| 检查项 | 分值 | 判定方法 |
|--------|------|---------|
| Organization schema 存在 | 5 | `grep '"@type":"Organization"'` |
| Organization.name 为全称 | 2 | 非简称/域名 |
| Organization.sameAs ≥ 5 个权威链接 | 3 | LinkedIn + Wikipedia/Wikidata + YouTube + 行业平台 |
| Organization.logo 正确 | 1 | 正方形图，URL 可达 |
| WebSite schema 存在 | 3 | `grep '"@type":"WebSite"'` |
| WebSite.name 与 Organization 一致 | 1 | |
| 页面级 schema 正确（Article/Product/FAQ 等） | 5 | 抽样 5 个页面检查，每个 1 分 |
| dateModified 真实更新 | 2 | 文章/产品页的 dateModified 是否为近期 |
| author 字段非空壳 | 1 | Article schema 的 author 链到真实作者页 |
| Schema 通过 Rich Results Test | 2 | 抽样验证 |

### Phase 3：可摘引性审查（25 分）

抽样 5 个高价值页面（首页 + 2 产品页 + 2 文章页），逐页检查：

| 检查项 | 分值 | 判定方法 |
|--------|------|---------|
| H1 后 100 字内含直接答案/定义 | 5 | 第一个 `<p>` 是否为 40-60 字完整陈述 |
| 每个 H2 首句 = 该节核心答案 | 5 | 检查 ≥3 个 H2，首句是否独立完整 |
| 无跨段依赖 | 3 | 无「如上所述」「前面提到」「见下文」 |
| 关键数据在表格/列表中 | 3 | 规格/对比/参数是否结构化 |
| 术语首次出现有定义 | 2 | 专业术语、缩写首次出现时是否解释 |
| FAQ 段存在且有 FAQPage schema | 3 | 主要产品/文章是否有 FAQ 段 |
| 段落短（2-4 句为主） | 2 | 是否有 5+ 句的长段落 |
| 无内容在付费墙/登录墙后 | 2 | 被引用的关键信息是否可公开访问 |

### Phase 4：品牌实体信号审查（15 分）

| 检查项 | 分值 | 判定方法 |
|--------|------|---------|
| Knowledge Panel 出现（搜品牌名） | 4 | Google 搜索品牌名 → 右侧有 Knowledge Panel |
| Wikipedia 条目存在 | 3 | 独立条目 > 被提及 > 无 |
| Wikidata 条目存在 | 2 | `wikidata.org/wiki/Q...` |
| 过去 12 个月被权威媒体/行业报告引用 ≥2 次 | 3 | 搜索 `"品牌名" + 行业关键词` |
| NAP 一致性（多平台） | 2 | 官网 vs LinkedIn vs Google Maps 企业名/地址一致 |
| 品牌搜索量趋势正向（GSC） | 1 | 品牌名搜索量月环比增长 |

### Phase 5：引用质量审查（10 分）

| 检查项 | 分值 | 判定方法 |
|--------|------|---------|
| 引用页面加载 < 1 秒 | 3 | PageSpeed Insights / `curl -o /dev/null -s -w '%{time_total}'` |
| 引用页无大量广告/弹窗 | 2 | 首屏广告密度 < 30% |
| Canonical 正确 | 2 | 被引用页的 canonical 指向自身 |
| 多源数据一致 | 3 | 同一数据在网站不同位置的表述一致 |

---

## 评分汇总

```
GEO 总分 = Phase1(25) + Phase2(25) + Phase3(25) + Phase4(15) + Phase5(10) = 100
```

| 分数 | 等级 | 动作 |
|------|------|------|
| 90-100 | **AI 统治级** | 维护即可，月度复查 |
| 75-89 | **强可发现** | 补齐 1-2 个短板 |
| 55-74 | **部分可见** | 系统性修复，优先 Phase 1+2 |
| 35-54 | **弱可见** | 从 Phase 1 开始重建 GEO 基线 |
| 0-34 | **AI 隐形** | 紧急：先做 llms.txt + 结构化数据 |

---

## 审计交付格式

```md
# GEO Audit Report — [Site Name]

## Score: XX/100 — [等级]

### Phase 1: Crawlability — XX/25
- [PASS/FAIL] llms.txt: [details]
- [PASS/FAIL] AI crawler access: [details]
- ...

### Phase 2: Structured Data — XX/25
- [PASS/FAIL] Organization schema: [details]
- ...

### Phase 3: Citability — XX/25
- Page 1 (/url): XX/25 — [gaps]
- Page 2 (/url): XX/25 — [gaps]
- ...

### Phase 4: Brand Entity — XX/15
- [PASS/FAIL] Knowledge Panel: [details]
- ...

### Phase 5: Citation Quality — XX/10
- [PASS/FAIL] Page speed: [details]
- ...

## Priority Fixes (ordered by impact)
1. [CRITICAL] [fix] — [expected GEO score gain: +X]
2. [HIGH] [fix] — [expected GEO score gain: +Y]
3. ...

## Next 3 Actions
1. ...
2. ...
3. ...
```

---

## 审计工具路由

| 检查 | 工具 |
|------|------|
| llms.txt | curl + manual |
| AI 爬虫屏蔽 | curl robots.txt |
| 无 JS 渲染 | curl + grep |
| Schema 验证 | `seo-schema` |
| 段落可摘引性 | `seo-geo` |
| Knowledge Panel | 手动 Google 搜索 |
| Wikipedia/Wikidata | `WebSearch` 或手动 |
| 页面速度 | `seo-google` (PageSpeed) 或 `seo-performance` |
| Canonical | curl + grep |
