# GEO Content Patterns — AI 优先的内容结构

AI 引擎摘引内容有特定的格式偏好。本文档提供经过验证的内容模板，最大化在 Google AI Overviews、ChatGPT、Perplexity、Bing Copilot 中的引用概率。

---

## 核心原则：可摘引原子

每个"可摘引原子"是一个**脱离上下文也能被 AI 完整引用**的内容单元。一篇文章由多个可摘引原子组成。

可摘引原子的结构：
```
[触发问题] → H2/H3 标题（匹配真实查询措辞）
[直接答案] → 40-60 字完整陈述（第一句）
[展开说明] → 2-3 句补充
[证据锚点] → 数据 + 可点击来源 + 年份
```

---

## Pattern 1：定义型段落（AI Overviews / ChatGPT 最常引用）

**触发查询：** "what is X", "X definition", "define X"

**模板：**
```html
<h2>What is [Entity]?</h2>
<p>[Entity] is a [category] that [primary function], commonly used in [application domain] for [key benefit]. Unlike [alternative], [entity] offers [differentiator].</p>
<p>[2-3 sentences expanding on mechanism, history, or variants.]</p>

<!-- AI Overviews typically pulls the first <p> verbatim -->
```

**为什么有效：** Google AI Overviews 的段落型 Featured Snippet 直接摘取定义型 `<p>`。第一句必须是语法完整的独立陈述——AI 不会拼接多个句子来形成定义。

**检查：** 删除 `<h2>` 后，第一句读起来是否像一条完整的百科词条定义？

## Pattern 2：对比型表格（Perplexity / ChatGPT 最常引用）

**触发查询：** "X vs Y", "X compared to Y", "difference between X and Y"

**模板：**
```html
<h2>[Entity A] vs [Entity B]: Key Differences</h2>
<p>[Entity A] and [Entity B] differ primarily in [key differentiator 1], [key differentiator 2], and [key differentiator 3].</p>

<table>
  <thead>
    <tr><th>Dimension</th><th>[Entity A]</th><th>[Entity B]</th></tr>
  </thead>
  <tbody>
    <tr><td>[Dimension 1]</td><td>[Value A1]</td><td>[Value B1]</td></tr>
    <tr><td>[Dimension 2]</td><td>[Value A2]</td><td>[Value B2]</td></tr>
    <tr><td>[Dimension 3]</td><td>[Value A3]</td><td>[Value B3]</td></tr>
    <tr><td>[Dimension 4]</td><td>[Value A4]</td><td>[Value B4]</td></tr>
    <tr><td>Best for</td><td>[Use case A]</td><td>[Use case B]</td></tr>
  </tbody>
</table>
```

**为什么有效：** Perplexity 偏好结构化对比数据。`<table>` 比 CSS 模拟的表格更容易被 AI 解析。每个单元格的值必须是具体、可量化的——AI 忽略「好」「较好」「一般」这种模糊词。

**检查：** 每个单元格的值是否具体到可以被 AI 直接引用（数字、是/否、具体描述）？

## Pattern 3：步骤型列表（Bing Copilot / AI Overviews 最常引用）

**触发查询：** "how to X", "steps to X", "X process"

**模板：**
```html
<h2>How to [Achieve Outcome]: Step-by-Step</h2>
<p>Follow these [N] steps to [achieve outcome]. The entire process typically takes [timeframe] and requires [prerequisites].</p>

<ol>
  <li><strong>[Step Name]:</strong> [1-2 sentences explaining the action]. [Expected result or common pitfall].</li>
  <li><strong>[Step Name]:</strong> [1-2 sentences explaining the action]. [Expected result or common pitfall].</li>
  <li><strong>[Step Name]:</strong> [1-2 sentences explaining the action]. [Expected result or common pitfall].</li>
</ol>

<p><strong>Pro tip:</strong> [expert insight not obvious to beginners].</p>
```

**为什么有效：** Bing Copilot 偏好结构化步骤。`<ol>` 的语义告诉 AI 这是有序步骤。每个 `<li>` 必须是一个完整句子——AI 摘引时不会拼接 `<strong>` 和后续文本。

**Schema 配对：** 添加 `HowTo` schema（`step` 数组，每步含 `name` + `text`）。

## Pattern 4：FAQ 原子阵列（全平台通用）

**触发查询：** People Also Ask 问题、长尾问题查询

**模板：**
```html
<h2>Frequently Asked Questions About [Topic]</h2>

<h3>Q: [Exact PAA question phrasing]?</h3>
<p>[Direct answer in 1-3 sentences, max 150 characters]. <a href="[source]">[Source, Year]</a></p>

<h3>Q: [Exact PAA question phrasing]?</h3>
<p>[Direct answer in 1-3 sentences, max 150 characters]. <a href="[source]">[Source, Year]</a></p>
```

**为什么有效：** Google PAA 的答案长度限制约 150 字符。超过这个长度的答案会被截断。每个 Q&A 是一个独立原子——AI 可以为不同查询摘引不同 Q&A，互不干扰。

**Schema 配对：** 必须添加 `FAQPage` schema，`mainEntity` 中包含所有 Q&A。

**关键约束：**
- H3 必须使用真实查询措辞（从 seo-dataforseo 的 question keywords 或 SERP 的 PAA 中提取）
- 答案不能包含营销语言（PAA 过滤推销性内容）
- 每个答案必须自包含，不依赖其他 Q&A

## Pattern 5：规格/参数表（B2B 专用，Perplexity 高偏好）

**触发查询：** "X specifications", "X technical data", "X properties"

**模板：**
```html
<h2>[Product/Material] Technical Specifications</h2>
<p>The table below summarizes the key technical parameters of [product/material] based on [testing standard, e.g., ASTM D3039]. All values are from [source type: manufacturer data / independent testing].</p>

<table>
  <thead>
    <tr><th>Property</th><th>Value</th><th>Test Standard</th></tr>
  </thead>
  <tbody>
    <tr><td>Tensile Strength</td><td>3,500 MPa</td><td>ASTM D3039</td></tr>
    <tr><td>Tensile Modulus</td><td>230 GPa</td><td>ASTM D3039</td></tr>
    <tr><td>Density</td><td>1.6 g/cm³</td><td>ASTM D792</td></tr>
    <tr><td>Glass Transition (Tg)</td><td>120°C</td><td>DSC</td></tr>
  </tbody>
</table>
```

**为什么有效：** Perplexity 的「Sources」功能将规格表视为高价值信息。添加测试标准列将来源锚定到可验证的第三方标准——这直接提升 Perplexity 来源评分。

## Pattern 6：数据-洞察段落（ChatGPT / Perplexity 高偏好）

**触发查询：** "X statistics", "X data", "X trends"

**模板：**
```html
<h2>[Specific Finding]: The Data Behind [Topic]</h2>
<p>According to <a href="[source URL]">[Source Name] ([Year])</a>, [specific statistic] — which means [one-sentence insight on what this implies].</p>
<p>[2-3 sentences contextualizing the data: comparison to previous years, industry average, regional breakdown.]</p>
```

**为什么有效：** ChatGPT 偏好引用包含「数据 + 解读」的内容。单纯的数字罗列不如「数字 + 这意味着什么」更容易被引用。将来源名称和年份内联到句子中——AI 引用时会带上这些信息。

**检查：** 每个数据点后面是否跟了「这意味着」的解读，而不只是数字？

## Pattern 7：对比决策框架（全平台，B2B 高价值）

**触发查询：** "how to choose X", "X selection guide", "which X is right for me"

**模板：**
```html
<h2>How to Choose the Right [Product Type]: Decision Framework</h2>
<p>Your choice depends primarily on [factor 1], [factor 2], and [factor 3]. Use the table below to match your requirements to the right option.</p>

<table>
  <thead>
    <tr><th>If you need...</th><th>Choose...</th><th>Because...</th></tr>
  </thead>
  <tbody>
    <tr><td>[Scenario A]</td><td>[Option X]</td><td>[Specific reason tied to a property]</td></tr>
    <tr><td>[Scenario B]</td><td>[Option Y]</td><td>[Specific reason tied to a property]</td></tr>
    <tr><td>[Scenario C]</td><td>[Option Z]</td><td>[Specific reason tied to a property]</td></tr>
  </tbody>
</table>
```

**为什么有效：** 「If X → choose Y → because Z」是 AI 引擎摘引的最高价值结构——它直接回答决策问题，不需要 AI 自己做推理。

---

## 跨平台差异速查

| 特性 | Google AI Overviews | ChatGPT | Perplexity | Bing Copilot |
|------|-------------------|---------|------------|-------------|
| 引用长度偏好 | 40-60 字段落 | 100-200 字段落 | 按来源卡片分组 | 结构化数据优先 |
| 格式偏好 | `<p>` > `<table>` > `<ol>` | 长文深度 > 短定义 | `<table>` + 数据源标注 | `<ol>` 步骤 + Schema |
| 权威来源权重 | 极高（gov/edu/知名品牌） | 高（Bing索引权威） | 极高（学术/行业） | 高（Bing索引权威） |
| JS 渲染 | 部分支持 | 有限 | 有限 | 部分支持 |
| llms.txt 权重 | 中（辅助信号） | 高（入口地图） | 低 | 中 |
| Schema 权重 | 高 | 中 | 中 | 高 |

---

## 内容上线前 GEO 检查清单

每篇文章/产品页发布前：

- [ ] 开头 100 字是否有独立可摘引的直接答案？
- [ ] 每个 H2 首句是否是语法完整的独立陈述？
- [ ] 对比/规格/参数是否在 `<table>` 中（非 div 模拟）？
- [ ] FAQ 段是否存在 + FAQPage schema 已添加？
- [ ] 关键术语首次出现时是否定义了？
- [ ] 所有数据点是否有内联可点击来源（含年份）？
- [ ] 是否有跨段依赖（「如上所述」「前面提到」「见下文」）→ 全部消除？
- [ ] 无 JS 环境下 curl 是否能读到关键内容？
- [ ] Article schema 的 `dateModified` 是否更新了？
- [ ] 页面加载是否 < 1 秒？
