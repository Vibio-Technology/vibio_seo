# 用于 SEO 的付费搜索情报

付费搜索是 SEO 的受控研究渠道。相比等待自然排名，它能更快观察目标市场用语、搜索意图、信息表达反馈、落地页转化和额外需求信号；只有合格对照设计才能估计增量，而且广告不会影响自然排名位置。

## 官方来源

- Keyword Planner: https://support.google.com/google-ads/answer/7337243
- Search terms report: https://support.google.com/google-ads/answer/2472708
- Paid and organic report: https://support.google.com/google-ads/answer/3097241
- Custom experiments: https://support.google.com/google-ads/answer/6261395
- Offline/enhanced conversions for leads: https://support.google.com/google-ads/answer/2998031
- GA4 recommended lead events: https://developers.google.com/analytics/devguides/collection/ga4/reference/events

隐私阈值、报告和上传 API 会发生变化，因此实施前必须核验实时文档。

## 何时使用

当 SEO 决策因证据获取缓慢或证据含糊而受阻时，使用本工作流：

- 两个听起来都地道的关键词变体争夺同一页面。
- 搜索量工具对某个 B2B 规格术语意见不一或完全未收录。
- SERP 显示商业意图，但页面转化承诺是否有效仍不确定。
- 新市场没有 GSC 历史数据。
- 标题/价值主张或落地页变体需要更快验证。
- 品牌词付费搜索可能蚕食或保护整体搜索需求。

若没有转化测量、目标市场控制和决策规则，不得启动付费验证。

## 闭环流程

### 1. 建立候选集

综合 RFQ、CRM 用语、GSC 查询、本地语言竞争对手术语、Keyword Planner 和 SERP 观察。明确市场、语言、页面、转化主张和买家阶段。

Keyword Planner 的历史指标是按其定义聚合的需求估算，不是自然搜索难度；forecast 是广告情景预测，会受地区、预算、出价、定向和广告质量等输入影响，极低量或敏感词可能不可发现/预测。Search terms report 是另一份实际触发查询报告，受隐私和查询活动不足的隐藏边界影响。三者不可混为同一口径。

### 2. 定义决策

写下一个可证伪的问题，例如：

```text
For German procurement engineers, does "X" or "Y" produce more qualified RFQs for the same product page and offer?
```

上线前选定主要结果指标。优先采用有效线索、销售接收线索、商机或成交收入，而非点击率或原始表单数量。

### 3. 开展有边界的实验

使用准确的目标地区/语言、受控查询主题、清晰的否定关键词、一致的转化跟踪，以及范围有限的落地页/信息表达对比。在支持的场景中，可使用 Google Ads 自定义实验拆分流量，进行受控比较。

如果目标是获得因果结论，不得同时改变出价、受众、信息表达和落地页。

### 4. 查看真实搜索词

搜索词报告显示曾触发广告的搜索。用它来：

- 确认或否定买家用语。
- 发现修饰词、应用、标准、问题和竞品对比。
- 识别学生、招聘、DIY、免费、消费者或无关需求。
- 改进 SEO 页面内容简报、面向用户的 FAQ 和内链锚文本。

低搜索量词可能因隐私原因被隐藏，因此未出现不代表需求为零。

### 5. 关联业务质量

对于 B2B，采集并回传 `generate_lead`、`qualify_lead`、`working_lead`、`close_convert_lead` 和 `disqualify_lead` 等生命周期阶段。在转交 CRM 的全过程中保留广告系列/查询主题和落地页上下文。

若能获得线索质量或收入数据，就不得仅按线索数量确定 SEO 优先级。

### 6. 回馈 SEO 决策

更新：

- 关键词验证结论和目标市场用语。
- 意图族与页面映射。
- 页面标题/价值主张和内容缺口。
- 不应为其创建页面的否定/无效受众。
- 基于有效需求的商业页面优先级。
- 预测假设和置信度。

记录实验周期、支出、定向、查询覆盖限制、样本量、有效结果及据此做出的精确决策。

## 付费与自然搜索分析

Google Ads 与 Search Console 关联后，可使用付费与自然搜索报告观察同一查询下 Search campaign 文字广告、自然结果和组合指标。它适合描述覆盖重叠，并形成蚕食、增量或品牌防御假设；观察性共现不能单独证明反事实。需要因果结论时，预先设计广告开关、地域/时间 holdout 或其他合格对照，并控制同期变化。广告不会改善自然排名。

## 停止条件

如果转化跟踪失效、地区/语言泄漏显著、查询不匹配目标买家、落地页无法兑现承诺，或样本无法回答既定问题，就停止或重新设计测试。绝不得仅为收集更多数据而建议无期限投入预算。
