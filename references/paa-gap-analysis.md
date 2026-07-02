# PAA & AI Overview Gap Analysis — SERP 问题级缺口分析

从 SERP 的 People Also Ask 和 AI Overviews 引用中手术式提取高意图、零竞争的内容机会。不是泛泛的关键词研究——而是直接从搜索结果中找出你的内容可以占领的未被回答的问题空间。

---

## 1. PAA 提取方法

### 捕获初始 PAA 集合
对每个目标关键词：
1. 用 `seo-dataforseo` SERP API 拉 SERP 数据 → 提取 `people_also_ask` 字段里的所有问题
2. 或 `WebFetch` Google SERP → 提取页面中 PAA 区块的问题文本
3. 初始集合通常 4-6 个问题

### 二级扩展（解锁更多机会）
对初始 PAA 中的每个问题：
1. 点击该问题 → SERP 动态加载新的相关问题
2. 捕获新出现的问题
3. 对新的问题再展开一次 → 三级扩展

每次展开产出 3-5 个新问题。2-3 级展开后，一个关键词可以产出 **15-30 个唯一问题**。

### 去重与聚类
- 同义问题合并（"what is carbon fiber prepreg" = "carbon fiber prepreg definition"）
- 按子主题聚类：规格类、应用类、对比类、采购类 → 便于后续分配到对应页面

---

## 2. AI Overview 引用映射

### 当 AI Overviews 出现时
1. 记下 AI Overview 回答中引用了哪些域名
2. 对于每个被引用的页面，检查：该页面被引用的具体段落是什么？什么格式？
3. 识别 AI Overview 回答中提到的、但**没有任何被引用页面完整覆盖**的子问题

### AI Overview 缺口评分
AI Overview 主动回答了但没人被引用 → 这是最高的内容机会（+2 优先级加成）：
- AI 引擎**已经在回答这个问题** → 搜索需求确实存在
- 但**没有优质来源可以引用** → 你的内容如果覆盖了，被引用的概率极高
- 这是最快的 GEO 获胜路径

---

## 3. 缺口矩阵构建

```
目标词: carbon fiber fabric
PAA问题                                     | 我的站 | 竞品A | 竞品B | 竞品C | 缺口判定
-------------------------------------------|--------|--------|--------|--------|----------
What is carbon fiber fabric?                |   ✓    |   ✓   |   ✓   |   ✓   | 已饱和，简洁带过
Carbon fiber fabric vs fiberglass?          |   ✗    |   ✓   |   ✓   |   ✗   | ★ 你的缺口
How strong is carbon fiber fabric?          |   ✗    |   ✗   |   ✗   |   ✗   | ★★ 集体留白
Carbon fiber fabric weight per square meter?|   ✗    |   ✗   |   ✗   |   ✗   | ★★ 集体留白
Can carbon fiber fabric be cut at home?     |   ✗    |   ✓   |   ✗   |   ✗   | ★ 你的缺口
How much does carbon fiber fabric cost?     |   ✗    |   ✗   |   ✗   |   ✗   | ★★ 集体留白(AI答案但无引用)

AI Overview 引用:
- 竞品A 被引用 (回答 "what is" 定义段)
- AI Overview 回答了 "cost per square meter" 但未引用任何页面 ★★★ 最高机会
```

---

## 4. 机会评分

每个缺口按以下维度评分：

| 维度 | 评分规则 |
|------|---------|
| 缺口类型 | 集体留白(3分) > 你的缺口(2分) > AI Overview未引用(额外+2) > 已饱和(0分) |
| 商业价值 | 含价格/规格/供应商信号 +2，纯信息型 0 |
| 可回答性 | 你有一手数据能答 +2，可从竞品/公开数据推导 0 |
| 搜索量估算 | 被多次 PAA 扩展触发 + (高频率出现 = 高需求) |

**优先生产顺序：** 集体留白 + AI Overview 缺口 + 高商业价值 → 立即排入 WRITE 队列

---

## 5. 内容注入策略

### 对已有页面：FAQ 段注入
- 选 3-5 个顶级缺口问题 → 在目标页末尾添加 FAQ 段
- 每个问题做 H3，第一句直接回答（40-60 字），之后展开 1-2 句
- 添加 FAQPage schema

### 对新页面：把缺口作为大纲骨架
- 缺口问题 → 页面 H2/H3 的标题
- 按买家旅程排序：认知问题 → 评估问题 → 决策问题
- 确保每个 H2 首句是完整的独立答案

### 格式匹配
观察该问题在 PAA 中的答案格式 → 匹配：
- PAA 显示段落答案 → 你的答案也要用段落
- PAA 显示列表 → 你用 `<ol>` + 完整句子
- PAA 显示表格 → 你用 `<table>` + 对比维度

---

## 6. WRITE 管线集成

在 **WRITE 模式 Step 2（关键词内核）之后、Step 3（SERP 侦察）之前** 插入本步骤：

1. 对目标关键词运行 PAA 2-3 级扩展 → 产出 15-30 个问题
2. 构建缺口矩阵 → 标记每个问题的竞争状态
3. 选出 3-5 个最高机会缺口 → 写入内容简报（Step 5）作为必须覆盖的 FAQ/H2 小节
4. 对于已有页面更新：同上，但注入到现有页面的 FAQ 段

---

## 7. 追踪

| 指标 | 数据源 | 频率 |
|------|--------|------|
| PAA 问题是否出现在 GSC 查询中 | GSC → 按查询过滤 | 月 |
| PAA 片段是否引用你的页面 | `seo-dataforseo` SERP 检查或手动抽查 | 月 |
| FAQ 段落的 AI Overview 引用 | 手动搜目标问题 | 月 |
| 新缺口出现 | 重新跑 PAA 扩展 | 季度 |

记录到 `.vibio/changelog.md`：`PAA GAP WIN: [问题] — 已出现在 PAA/GSC 查询中`
