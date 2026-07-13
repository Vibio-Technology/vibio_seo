import {
  ArrowRight,
  Braces,
  ChartNoAxesCombined,
  Check,
  CircleDot,
  ClipboardCheck,
  FileCode2,
  FilePenLine,
  Fingerprint,
  KeyRound,
  LifeBuoy,
  LockKeyhole,
  Network,
  Route,
  SearchCheck,
  ShieldCheck,
  Sparkles,
  Target,
  Wrench,
} from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { MarketingNav } from "@/components/marketing/MarketingNav";
import styles from "./marketing.module.css";

const capabilityGroups = [
  {
    number: "01",
    label: "发现",
    title: "先确认问题是否真实",
    description: "从访问、源码与异常范围开始，区分观察事实、官方规则和待验证假设。",
    modes: [
      { label: "审计", Icon: SearchCheck },
      { label: "恢复", Icon: LifeBuoy },
    ],
  },
  {
    number: "02",
    label: "决策",
    title: "把资源放到主导约束上",
    description: "验证目标市场的买家任务，再按依赖、产能、指标和停止条件安排工作。",
    modes: [
      { label: "关键词", Icon: KeyRound },
      { label: "计划", Icon: Route },
    ],
  },
  {
    number: "03",
    label: "形成产物",
    title: "从建议推进到可审阅交付",
    description: "形成修复契约、目标市场页面成稿，以及基于真实资产的链接行动。",
    modes: [
      { label: "修复", Icon: Wrench },
      { label: "内容", Icon: FilePenLine },
      { label: "链接", Icon: Network },
    ],
  },
  {
    number: "04",
    label: "验证",
    title: "改动存在，才讨论结果",
    description: "分开验证产物、抓取与索引、搜索表现和业务结果，不把相关变化写成因果。",
    modes: [{ label: "复盘", Icon: ChartNoAxesCombined }],
  },
] as const;

const workflowSteps = [
  ["01", "审计", "读取当前证据"],
  ["02", "恢复", "有异常信号时进入"],
  ["03", "关键词", "验证需求与页面"],
  ["04", "计划", "排序依赖与行动"],
  ["05", "修复", "形成最小修复契约"],
  ["06", "内容", "产出目标市场页面"],
  ["07", "链接", "改善发现与权威"],
  ["08", "复盘", "证据成熟后进入"],
] as const;

const providers = [
  "DeepSeek",
  "Xiaomi MiMo",
  "OpenAI",
  "Qwen",
  "Kimi",
  "Zhipu AI",
  "SiliconFlow",
] as const;

const faqs = [
  {
    question: "Vibio 会直接修改或发布我的网站吗？",
    answer:
      "当前网页版生成可审阅的修复契约、内容和行动建议，不会自动部署代码、修改 CMS、发送外联、操作 GSC 或启动广告。任何外部副作用都应由你单独授权和执行。",
  },
  {
    question: "开始前必须接入 GSC、GA4 或 CRM 吗？",
    answer:
      "不需要。填写项目名称、目标市场、语言、主要合格转化与本次目标即可开始；公开 URL 和上传证据可按任务补充。你可以上传脱敏的聚合导出提高判断上限；没有第一方数据时，Vibio 会说明哪些结论当前无法得出。",
  },
  {
    question: "我的 API Key 会保存在哪里？",
    answer:
      "Key 仅保留在当前浏览器会话，并随单次请求转发给所选模型服务商。它不会写入项目草稿或运行历史。你可以随时清空输入，关闭当前浏览器会话也会结束会话存储。",
  },
  {
    question: "报告和项目会跨设备同步吗？",
    answer:
      "不会。当前版本的项目草稿和最近运行记录保存在当前浏览器的本地存储中，不提供账号系统或云同步。报告可以复制，或导出为 Markdown 和 JSON。",
  },
  {
    question: "公开 URL 审计能看到什么？",
    answer:
      "它在有界范围内读取匿名 HTTP 源码、robots.txt、sitemap、状态码、canonical、robots 指令、标题和链接等信号。它不执行 JavaScript，也不能证明搜索引擎已经抓取、收录或选择了相同 canonical。",
  },
  {
    question: "Vibio 能保证排名、流量或收入增长吗？",
    answer:
      "不能。Vibio 保证的是证据分级、明确决策、可验证产物、停止条件和复盘闭环。排名、流量、AI 展示和业务结果必须在适合项目的观察窗口里，用第一方数据验证。",
  },
] as const;

export default function HomePage() {
  return (
    <div className={styles.siteShell}>
      <MarketingNav />

      <main>
        <section className={styles.hero} aria-labelledby="hero-title">
          <Image
            className={styles.heroImage}
            src="/vibio-workspace-preview.webp"
            alt="Vibio SEO 工作台的真实界面预览"
            fill
            priority
            sizes="100vw"
          />
          <div className={styles.heroShade} aria-hidden="true" />
          <div className={styles.heroInner}>
            <div className={styles.heroCopy}>
              <span className={styles.heroEyebrow}>
                <Sparkles size={15} aria-hidden="true" />
                证据驱动的搜索优化工作流
              </span>
              <h1 id="hero-title">Vibio SEO</h1>
              <p className={styles.heroLead}>把 SEO 从一堆建议，变成有证据、能执行、可复盘的工作流。</p>
              <p className={styles.heroBody}>
                站点、市场、语言和主要转化只填一次。每项能力只补问当前决策必须知道的信息，然后给出可审阅的行动与报告。
              </p>
              <div className={styles.heroActions}>
                <Link className={styles.primaryButton} href="/workspace">
                  进入工作台
                  <ArrowRight size={18} aria-hidden="true" />
                </Link>
                <a className={styles.secondaryButton} href="#how-it-works">
                  查看工作方式
                </a>
              </div>
              <p className={styles.heroNote}>
                <Check size={14} aria-hidden="true" />
                无需注册·使用你自己的模型 API Key
              </p>
            </div>

            <dl className={styles.heroFacts} aria-label="产品概览">
              <div>
                <dt>一份</dt>
                <dd>项目档案</dd>
              </div>
              <div>
                <dt>8 种</dt>
                <dd>专项能力</dd>
              </div>
              <div>
                <dt>7 家</dt>
                <dd>BYOK 模型</dd>
              </div>
              <div>
                <dt>2 种</dt>
                <dd>报告导出格式</dd>
              </div>
            </dl>
          </div>
        </section>

        <section className={styles.promiseBand} aria-label="Vibio 的方法">
          <div className={styles.sectionInner}>
            <p>
              <CircleDot size={16} aria-hidden="true" />
              不编搜索量、KD、排名或收入
            </p>
            <p>
              <ShieldCheck size={16} aria-hidden="true" />
              不把源码观察写成收录事实
            </p>
            <p>
              <ClipboardCheck size={16} aria-hidden="true" />
              每次交付都包含限制与下一步
            </p>
          </div>
        </section>

        <section className={styles.projectSection} id="how-it-works" aria-labelledby="project-title">
          <div className={styles.sectionInner}>
            <header className={styles.sectionHeader}>
              <span className={styles.sectionKicker}>ONE PROJECT BRIEF</span>
              <h2 id="project-title">项目信息，只填一次</h2>
              <p>
                站点、目标市场、语言和合格转化属于项目，不属于某一次分析。建立项目后，你只需补充当前任务的最少信息。
              </p>
            </header>

            <ol className={styles.briefSteps}>
              <li>
                <span className={styles.stepNumber}>01</span>
                <Target size={22} aria-hidden="true" />
                <h3>建立项目坐标</h3>
                <p>一次填写站点、市场、语言、业务与主要合格转化。</p>
              </li>
              <li>
                <span className={styles.stepNumber}>02</span>
                <Fingerprint size={22} aria-hidden="true" />
                <h3>只补充任务差异</h3>
                <p>审计补范围，关键词补买家任务，内容补企业事实，复盘补变更与窗口。</p>
              </li>
              <li>
                <span className={styles.stepNumber}>03</span>
                <ClipboardCheck size={22} aria-hidden="true" />
                <h3>获得可复验交付</h3>
                <p>报告明确证据、影响边界、优先级、复验方式、停止条件和下三项行动。</p>
              </li>
            </ol>
          </div>
        </section>

        <section className={styles.workflowSection} id="workflow" aria-labelledby="workflow-title">
          <div className={styles.sectionInner}>
            <div className={styles.workflowIntro}>
              <span className={styles.sectionKickerLight}>AUTOMATIC CAPABILITY CHAIN</span>
              <h2 id="workflow-title">从一个问题开始，不必先学会八种模式</h2>
              <p>
                单独运行某项能力，或让自动流程按依赖顺序推进。恢复与复盘只在证据条件满足时进入；运行失败后可从失败阶段继续。
              </p>
            </div>

            <ol className={styles.workflowTrack}>
              {workflowSteps.map(([number, label, description], index) => (
                <li key={label}>
                  <span className={styles.workflowIndex}>{number}</span>
                  <div>
                    <strong>{label}</strong>
                    <span>{description}</span>
                  </div>
                  {index < workflowSteps.length - 1 && (
                    <ArrowRight className={styles.workflowArrow} size={16} aria-hidden="true" />
                  )}
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className={styles.capabilitiesSection} id="capabilities" aria-labelledby="capabilities-title">
          <div className={styles.sectionInner}>
            <header className={styles.sectionHeader}>
              <span className={styles.sectionKicker}>EIGHT SPECIALISTS, ONE METHOD</span>
              <h2 id="capabilities-title">不是八个独立工具，是一条决策链</h2>
              <p>
                每项能力关注不同阶段，但共享同一套证据等级、权限边界和交付契约。
              </p>
            </header>

            <div className={styles.capabilityList}>
              {capabilityGroups.map((group) => (
                <article key={group.number} className={styles.capabilityRow}>
                  <div className={styles.capabilityLabel}>
                    <span>{group.number}</span>
                    <strong>{group.label}</strong>
                  </div>
                  <div className={styles.capabilityCopy}>
                    <h3>{group.title}</h3>
                    <p>{group.description}</p>
                  </div>
                  <div className={styles.modeList} aria-label={`${group.label}阶段能力`}>
                    {group.modes.map(({ label, Icon }) => (
                      <span key={label}>
                        <Icon size={16} aria-hidden="true" />
                        {label}
                      </span>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className={styles.evidenceSection} id="evidence" aria-labelledby="evidence-title">
          <div className={`${styles.sectionInner} ${styles.evidenceGrid}`}>
            <div className={styles.evidenceCopy}>
              <span className={styles.sectionKicker}>EVIDENCE BEFORE OPINION</span>
              <h2 id="evidence-title">不是健康分，是可复验的证据</h2>
              <p>
                Vibio 从公开 URL 和你提供的脱敏材料开始。它会说清自己看到了什么、证明了什么，以及当前还不能知道什么。
              </p>
              <ul className={styles.evidencePoints}>
                <li><SearchCheck size={18} />读取有界的 HTTP 源码、robots.txt 与 sitemap</li>
                <li><FileCode2 size={18} />支持 CSV、JSON、HTML、XML、Markdown 与 TXT 证据</li>
                <li><Braces size={18} />报告可复制，并导出 Markdown 和 JSON</li>
              </ul>
            </div>

            <figure className={styles.evidenceLedger}>
              <figcaption>
                <span>VIBIO / EVIDENCE NOTE</span>
                <span>HTTP SOURCE</span>
              </figcaption>
              <div className={styles.ledgerStatus}>
                <SearchCheck size={28} aria-hidden="true" />
                <div>
                  <strong>已观察</strong>
                  <span>当前匿名 HTTP 响应源码</span>
                </div>
              </div>
              <dl>
                <div>
                  <dt>可验证</dt>
                  <dd>状态码、canonical、robots 指令、标题与链接</dd>
                </div>
                <div>
                  <dt>不外推</dt>
                  <dd>JavaScript 执行后的 DOM、真实收录、排名与转化</dd>
                </div>
                <div>
                  <dt>复验</dt>
                  <dd>在同一证据范围内重新请求与比较产物</dd>
                </div>
              </dl>
              <p><LockKeyhole size={14} />限制会和发现一起出现，不放在小字里。</p>
            </figure>
          </div>
        </section>

        <section className={styles.modelsSection} id="models" aria-labelledby="models-title">
          <div className={styles.sectionInner}>
            <div className={styles.modelsHeading}>
              <div>
                <span className={styles.sectionKicker}>BRING YOUR OWN KEY</span>
                <h2 id="models-title">模型可选，方法一致</h2>
              </div>
              <p>
                选择你已有的模型服务。Vibio 不为不同模型换一套 SEO 逻辑：八种能力共享同一套证据政策与知识边界。
              </p>
            </div>
            <div className={styles.providerLine} aria-label="支持的模型服务商">
              {providers.map((provider, index) => (
                <span key={provider}>
                  {provider}
                  {index < providers.length - 1 && <i aria-hidden="true" />}
                </span>
              ))}
            </div>
          </div>
        </section>

        <section className={styles.trustSection} id="security" aria-labelledby="trust-title">
          <div className={styles.sectionInner}>
            <header className={styles.sectionHeader}>
              <span className={styles.sectionKicker}>CLEAR OPERATING BOUNDARIES</span>
              <h2 id="trust-title">数据如何走，产品就如何说</h2>
              <p>
                当前版本不用“已连接”包装尚未实现的能力。你能清楚看到模型、证据、存储与外部操作的边界。
              </p>
            </header>

            <div className={styles.trustGrid}>
              <article>
                <KeyRound size={22} aria-hidden="true" />
                <h3>Key 只属于当前会话</h3>
                <p>API Key 不写入项目或运行历史，只随单次请求转发给你选择的模型。</p>
              </article>
              <article>
                <Fingerprint size={22} aria-hidden="true" />
                <h3>历史仅存当前浏览器</h3>
                <p>项目草稿与运行记录使用本地存储，当前没有账号系统、云端项目或跨设备同步。</p>
              </article>
              <article>
                <ShieldCheck size={22} aria-hidden="true" />
                <h3>外部动作留给人审核</h3>
                <p>不自动部署、不修改 CMS、不发外联、不操作 GSC 或广告账户。</p>
              </article>
            </div>

            <Link className={styles.inlineLink} href="/privacy">
              查看完整的隐私与数据处理说明
              <ArrowRight size={16} aria-hidden="true" />
            </Link>
          </div>
        </section>

        <section className={styles.faqSection} id="faq" aria-labelledby="faq-title">
          <div className={styles.sectionInner}>
            <header className={styles.sectionHeaderCompact}>
              <span className={styles.sectionKicker}>QUESTIONS, ANSWERED PLAINLY</span>
              <h2 id="faq-title">开始前需要知道的事</h2>
            </header>
            <div className={styles.faqList}>
              {faqs.map((faq, index) => (
                <details key={faq.question}>
                  <summary>
                    <span>{String(index + 1).padStart(2, "0")}</span>
                    <strong>{faq.question}</strong>
                    <span className={styles.faqMark} aria-hidden="true">+</span>
                  </summary>
                  <p>{faq.answer}</p>
                </details>
              ))}
            </div>
          </div>
        </section>

        <section className={styles.finalCta} aria-labelledby="cta-title">
          <div className={styles.sectionInner}>
            <div>
              <span className={styles.finalKicker}>START WITH A REAL QUESTION</span>
              <h2 id="cta-title">从一个真实问题开始</h2>
              <p>建立项目坐标，选择单项能力，或让 Vibio 自动走完适用的流程。</p>
            </div>
            <Link className={styles.ctaButton} href="/workspace">
              进入工作台
              <ArrowRight size={19} aria-hidden="true" />
            </Link>
          </div>
        </section>
      </main>

      <footer className={styles.footer}>
        <div className={styles.sectionInner}>
          <div className={styles.footerBrand}>
            <Image src="/vibio-logo.png" alt="" width={34} height={34} />
            <div>
              <strong>Vibio SEO</strong>
              <span>Evidence-led search operations</span>
            </div>
          </div>
          <nav aria-label="页脚导航">
            <a href="#how-it-works">工作方式</a>
            <a href="#capabilities">产品能力</a>
            <Link href="/privacy">隐私与数据</Link>
            <Link href="/workspace">工作台</Link>
          </nav>
          <span className={styles.footerVersion}>V5.0</span>
        </div>
      </footer>
    </div>
  );
}
