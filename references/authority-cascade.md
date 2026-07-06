# Authority Cascade Building — 权威阶梯

系统性地通过从易到难的关鍵词排序来构建站点权威。不是简单地筛选低难度词，而是设计一个有意的级联架构，让每一阶段的胜利为下一阶段积累所需的权威信号。

---

## 1. 级联架构设计

### 核心机制
```
Phase 1 (KD < 15) → 快速获胜 → 积累主题权威 + 排名信号
    ↓ 70% Phase 1 进前10 → 触发 Phase 2
Phase 2 (KD 15-30) → 站内链接赋能 + 主题权威 → 进入中等难度
    ↓ 70% Phase 2 进前10 → 触发 Phase 3
Phase 3 (KD 30-50) → 外链支持 + 强主题权威 → 进入竞争区间
    ↓ 50% Phase 3 进前10 → 触发 Phase 4
Phase 4 (KD 50+) → 全站权威 + 高质量外链 → 头部词
```

### 实操案例：碳纤维制造商

目标终极词：`carbon fiber fabric` (KD 50, 搜索量 12,000/月)

**Phase 1 — 长尾铺底 (KD < 15)**
- `carbon fiber fabric 3k 200gsm twill` (KD 10, 量 200/月) → 产品规格页
- `what is carbon fiber fabric used for` (KD 12, 量 400/月) → 买家教育文章
- `carbon fiber fabric vs carbon fiber plate` (KD 14, 量 300/月) → 对比页
- `carbon fiber fabric for drone frames` (KD 12, 量 250/月) → 应用场景页
- `3k vs 12k carbon fiber fabric` (KD 8, 量 150/月) → 技术对比页

*目标：5-8 个 Phase 1 页面，3-6 个月内 70% 进前 10*

**Phase 2 — 中等难度 (KD 15-30)**
- `carbon fiber fabric specifications` (KD 25, 量 800/月)
- `carbon fiber fabric price per meter` (KD 22, 量 600/月)
- `custom carbon fiber fabric manufacturer` (KD 28, 量 500/月)
- `carbon fiber fabric mechanical properties` (KD 18, 量 350/月)

*Phase 1 页面内链指向 Phase 2 页面，用目标关键词做锚文本*

**Phase 3 — 竞争区间 (KD 30-50)**
- `carbon fiber fabric supplier` (KD 40, 量 2,500/月)
- `carbon fiber fabric china` (KD 38, 量 1,800/月)
- `buy carbon fiber fabric` (KD 35, 量 1,200/月)

*Phase 3 需要外链支持。此时 Phase 1-2 的累积权威 + 针对性外链建设。*

**Phase 4 — 头部词 (KD 50+)**
- `carbon fiber fabric` (KD 50, 量 12,000/月)

*全站权威、多簇内容、高质量外链缺一不可。不可跳过前面阶段直接打。*

---

## 2. 速度建模

### 经验法则
- **5-10 个页面在某一主题簇内排名前 10** → 该簇对 KD 高 15 分的词的权威门槛已具备
- **3-5 个页面排名前 3** → 主题权威信号很强，可以加速下一阶段
- **零页面排名前 50** → 不要在 Phase 2+ 投入资源，先解决 Phase 1

### 时间估算
| Phase | 新站 | 有一定基础的站 |
|-------|------|-------------|
| Phase 1 → 70% 进前10 | 3-6 个月 | 1-3 个月 |
| Phase 2 → 70% 进前10 | 6-12 个月（从启动计） | 3-6 个月 |
| Phase 3 → 50% 进前10 | 12-24 个月 | 8-18 个月 |
| Phase 4 | 24+ 个月 | 18+ 个月 |

---

## 3. 内链条级联设计

（本节是 `link-architecture.md` 在 KD 级联场景下的时序特化——什么时候链向哪一阶段的目标页。锚文本规则、密度上限、回填协议等通用规范以 `link-architecture.md` 为准。）

### 链接拓扑
```
Hub 页（主题支柱页）
  ├─ → Phase 1 Spoke 页 A（排名后，添加链向 Phase 2 目标页的链接）
  ├─ → Phase 1 Spoke 页 B（同上）
  ├─ → Phase 2 Target 页 X（接收来自多个 Phase 1 页面的链接）
  └─ → Phase 2 Target 页 Y
```

### 锚文本策略
- Phase 1 页 → Phase 2 页：用 Phase 2 页的目标关键词做锚文本
- 每篇 Phase 1 文章自然嵌入 1-2 个指向 Phase 2 目标页的链接
- 不堆砌：每 500-800 字最多 1 个指向同目标的链接

### 链接刷新
- 当 Phase 2 页面发布后，**回头更新已发布的 Phase 1 页面**，添加指向 Phase 2 的链接
- 当 Phase 1 页面获得排名后，其内链权重更高——立即在排名页中加链向 Phase 2

---

## 4. 阶段转换触发器

### 进入下一阶段的条件
- **Phase N → Phase N+1**：Phase N 中 ≥ 70% 的关键词进入前 10 且维持 ≥ 4 周
- **加速信号**：实际排名速度超过预期 → 将 Phase N+1 的启动提前 1-2 个月
- **减速信号**：Phase 1 中 < 30% 的关键词在 6 个月内进入前 50 → **不要进入 Phase 2**，先诊断根因

### 失败重评触发器
- Phase 1 6 个月后目标关键词仍未进入前 50 → 重新评估关键词选择（可能 KD 估计偏低、意图匹配错误、或内容质量不达标）
- Phase 2 12 个月后 < 30% 进前 10 → 主题权威积累不足或竞争环境变化
- 任一阶段的内容被 Google 核心更新打击 → 暂停级联，先修复内容质量

---

## 5. 与现有模式的集成

| 模式 | 级联集成方式 |
|------|-----------|
| **PLAN** | 级联架构是 90 天路线图的关键词战略主心骨 |
| **KEYWORD** | 新增输出维度：每个关键词标注 `cascade_phase: 1-4` |
| **WRITE** | Phase 1 内容优先生产；每个内容 brief 标注级联阶段 |
| **REVIEW** | 月度复盘检查阶段转换触发器是否满足 |
| **predictive-seo** | 难度分级和时间预估直接喂入级联速度模型 |

---

## 6. 不要做

- 不要因为头部词搜索量大就直接打 Phase 4 词——没有前三个阶段积累的权威，打不赢
- 不要给 Phase 1-2 页面做外链——它们靠内容质量和内链就能排名，针对页面的外链资源留到 Phase 3+（品牌级基础链接——目录/协会/认证——不受此限，见 `backlink-playbook.md` §一的启动闸门）
- 不要跳过阶段转换检查——"感觉差不多了"不是进入下一阶段的依据
- 不要在 Phase 1 页面还未排名时就大规模生产 Phase 2+ 内容——先验证 Phase 1 策略有效
- 不要把一个簇的级联照搬到另一个簇——不同主题簇的竞争格局不同，各自评估
