---
name: vibio-memory
description: |
  Vibio 项目记忆的格式规范与读写约定。当用户说「这个项目之前做到哪了」「继续上次的 SEO」「上次审查/改了什么」「记录一下这次的发现」时可直接触发本 skill 来读写记忆；更多时候它是 vibio-plan / vibio-audit / vibio-fix / vibio-review 内联遵循的约定——那些 skill 自己用 Read/Write 操作项目根的 .vibio/，格式以本 skill 的 references/state-templates.md 为准。
  .vibio/ 存：诊断结论、主瓶颈、90 天进度、内容/关键词/外链三张追踪表、每次改动日志。让 vibio 系列从「每次重新认识项目的咨询师」变成「记得上次干了什么的操作系统」。
  不应触发：用户要的是一次性问答、没有具体项目、纯概念解释。
  Defines the .vibio/ memory format and read/write conventions. Sibling skills read/write .vibio/ directly (with Read/Write) following references/state-templates.md; can also be invoked directly to recall or record project state.
---

# Vibio SEO — 项目记忆（格式规范 + 读写约定）

SEO 是长周期的事：要追踪决策历史、要复盘见效。没有持久状态，每次 PLAN 都从零 kickoff、每次 AUDIT 都重读、改完 FIX 就断线。本 skill 定义每个项目那份落盘记忆的**格式和读写规矩**。

**重要——执行方式**：skill 之间不能互相函数调用。所谓「让 vibio-memory 读写」其实是：**plan/audit/fix/review 自己用 `Read`/`Write`/`Edit` 工具直接操作项目根的 `.vibio/`**，按本 skill `references/state-templates.md` 的格式来。本 skill 是那套格式和约定的单一事实来源；用户也可直接触发它来"回忆/记录"。

**核心约定：任何 vibio 子 skill 开工前先读 `.vibio/`，收工后写回。**

---

## 存储位置

被操作的**项目根目录**下的 `.vibio/`（不是 skill 目录、不是 home）。结构：

```
<项目根>/.vibio/
├── project.md            # 项目档案 + 当前状态（单一事实来源）
├── trackers/
│   ├── content.md        # 内容追踪表
│   ├── keywords.md       # 关键词追踪表
│   └── outreach.md       # 外链追踪表（权重工作启动后才建）
└── changelog.md          # 每次 AUDIT/FIX 的改动日志（追加，不覆写）
```

只有 URL、没有本地项目时：在当前工作目录建 `.vibio/`，在 `project.md` 里记下目标 URL 和"无代码访问"。提醒用户把 `.vibio/` 加进 `.gitignore` 还是提交由他们定（提交便于团队共享决策历史，推荐提交）。

---

## 读流程（任何子 skill 开工前，用 `Read` 工具直接读）

1. 看项目根有没有 `.vibio/project.md`（`Read` 或 `Glob`）。
2. **有** → 用 `Read` 读 `project.md` + 相关 tracker + `changelog.md` 末尾几条。据此判断：当前阶段、已完成项、上次的主瓶颈、已知的栈、待办。把这些带入当前任务，**不要重启**（呼应 operating-system.md 的延续规则：只输出下一段操作切片）。
3. **没有** → 这是新项目，照常 kickoff，并在收工时用 `Write` **新建** `.vibio/`。

读完用一句话向用户确认定位：「读到记忆：这是 Shopify 站，上次（<日期>）诊断主瓶颈是内容系统，已发布 4 个商业页，待办是内链。继续。」

---

## 写流程（任何子 skill 收工后，用 `Write`/`Edit` 直接写）

只记会改变下一步决策的东西，不记流水账：
- **vibio-plan** 写/更新 `project.md` 的诊断、主瓶颈、90 天目标、路线图阶段、节奏；用 `Write` 建 tracker 骨架。
- **vibio-audit** 用 `Edit` 把发现追加到 `changelog.md`（带日期、优先级、是否已修），把新确认的栈/状态更新进 `project.md`。
- **vibio-fix** 把每次改动追加到 `changelog.md`（改了什么、哪个文件/位置、验证结果、是否面向 SERP 待重抓）。
- **vibio-review** 更新 `trackers/keywords.md` 的排名/趋势，把复盘结论追加到 `changelog.md`（Type: REVIEW）。

写时机：完成一个有意义的动作就追加，别等会话结束。changelog 永远追加（用 `Edit` 在顶部插入，不覆写整文件）。

---

## 文件格式

参考 `references/state-templates.md` 里的标准模板（project.md / 三张 tracker / changelog 各一份），保持字段一致，方便下次机读。tracker 字段对齐 operating-system.md 的追踪系统定义（内容：标题/URL/页型/关键词族/意图/状态/发布日/更新日/负责人；关键词：词/意图/归属页/优先级/难度/当前vs上次排名/趋势；外链：目标站/渠道/类型/推广页/日期/状态/结果）。

---

## 不要做

- 不把记忆写到项目外（skill 目录、home）——除非是 URL-only 无本地项目。
- 不覆写 `changelog.md`，只追加。
- 不记不影响决策的流水账（"读了首页"这种）。
- 读到记忆后不重启整个流程，只续上次的下一步。
- 不在没确认项目根的情况下乱建 `.vibio/`。
