# GEO Competitive Intelligence — 竞品 AI 可见性分析

监控竞品在 AI 搜索中的表现，找到他们的 GEO 弱点和你的机会窗口。

---

## 1. 竞品 GEO 评分卡

对每个主要竞品执行快速 GEO 审计（使用 `geo-audit.md` 协议的简化版），产出对比评分卡：

```
竞品 GEO 对比
                   你     竞品A   竞品B   竞品C
llms.txt           ✅      ❌      ✅      ❌
Organization schema ✅     ✅      ❌      ✅
FAQPage schema     ✅      ❌      ❌      ❌
Knowledge Panel    ❌      ✅      ✅      ❌
段落可摘引性(抽样)  72%     45%     80%     30%
GEO 总分          78      42      65      35
```

## 2. 竞品 GEO 信号采集

### 自动化检查（curl 可完成）

```bash
# 竞品 llms.txt
curl -sL https://competitor.com/llms.txt | head -20

# 竞品 schema 类型
curl -sL https://competitor.com/ | grep -oP '"@type":"[^"]+"' | sort | uniq -c

# 竞品 AI 爬虫屏蔽
curl -sL https://competitor.com/robots.txt | grep -iE "GPTBot|CCBot|Google-Extended|PerplexityBot"

# 竞品段落可摘引性（抽样产品页）
curl -sL https://competitor.com/product-page | grep -oP '<p>[^<]{40,150}</p>' | head -5
```

### 手动检查（浏览器）

| 信号 | 检查方法 |
|------|---------|
| Knowledge Panel | Google 搜索竞品品牌名 → 右侧是否有 Knowledge Panel？内容丰富度？ |
| AI Overviews 引用 | Google 搜索竞品核心关键词 → AI Overviews 是否引用竞品？引用哪句？ |
| ChatGPT 引用 | ChatGPT (web search) 问「what is [competitor's product]」→ 引用了竞品吗？ |
| Perplexity 来源 | Perplexity 搜索竞品核心关键词 → Sources 中是否出现竞品？排第几？ |
| 品牌 Wikipedia | 竞品是否有 Wikipedia 条目？条目质量？ |

## 3. GEO 缺口分析

从竞品对比中提取三类缺口：

### 你的 GEO 缺口（竞品有，你没有）
```
竞品A 有 Knowledge Panel，我们没有
  → 行动：补 Wikidata 条目 + 加强 Wikipedia 引用
竞品B llms.txt 更完整
  → 行动：对比竞品 llms.txt 结构，补全我们的
```

### 竞品的 GEO 缺口（你有，竞品没有）
```
我们有 FAQPage schema，竞品都没有
  → 这是 GEO 护城河，保持并扩大
我们有 answer-first 段落结构，竞品是传统叙事
  → AI 引用时我们的内容更容易被摘取
```

### 集体 GEO 空白（所有人都不做）
```
所有竞品都没有 HowTo schema
  → 如果我们加上，就是该品类 AI 搜索的独占入口
所有竞品都没有数据集/原创数据标记
  → 如果我们发布原创行业数据 + Dataset schema，建立不可复制的 GEO 优势
```

## 4. GEO 攻击手册

基于竞品分析的具体攻击动作：

### 攻击 1：抢占竞品缺少的 Schema 类型
如果竞品都没有 `FAQPage` → 在所有关键页面加 FAQPage schema + PAA 匹配的 FAQ 内容 → 独占该品类的 AI 问答引用。

### 攻击 2：用一手数据替代竞品的二手综述
如果竞品的 AI 引用来自二手行业报告 → 发布原创实测数据 + 注明「来自 [公司] 实验室测试」→ AI 偏好一手来源。

### 攻击 3：填补竞品 llms.txt 的内容空白
分析竞品 llms.txt 列了哪些页面 → 你的 llms.txt 列他们没列的页面（独家内容）→ AI 爬虫发现你的内容更独特。

### 攻击 4：在竞品 GEO 盲区建立实体权威
如果竞品都没有 Wikipedia/Wikidata → 你第一个建立 → Google Knowledge Graph 将你识别为该品类的权威实体。

### 攻击 5：复制竞品的 GEO 优势
竞品被 AI Overviews 频繁引用的内容 → 分析为什么（格式？数据？权威来源？）→ 用更好的版本替代。

## 5. GEO 监控节奏

| 频率 | 动作 |
|------|------|
| **周** | 检查自己+top 3竞品的核心关键词在 Google AI Overviews 中的引用 |
| **月** | 全量竞品 GEO 评分卡更新 |
| **季** | 深度分析：Wikipedia 变更、新 Schema 类型、竞品新内容策略 |
| **触发式** | 竞品上线新网站/大改版 → 48小时内执行完整 GEO 审计 |
