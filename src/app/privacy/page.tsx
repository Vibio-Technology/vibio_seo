import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { MarketingNav } from "@/components/marketing/MarketingNav";
import styles from "../marketing.module.css";

export const metadata: Metadata = {
  title: "隐私与数据处理",
  description: "了解 Vibio SEO 如何处理 API Key、项目草稿、运行历史、上传证据、公开 URL 与第三方模型请求。",
  alternates: {
    canonical: "/privacy",
  },
};

const sections = [
  ["overview", "处理概览"],
  ["key", "API Key"],
  ["browser", "浏览器存储"],
  ["evidence", "证据与 URL"],
  ["providers", "第三方模型"],
  ["delete", "删除数据"],
] as const;

export default function PrivacyPage() {
  return (
    <div className={`${styles.siteShell} ${styles.privacyPage}`}>
      <MarketingNav />
      <main id="main-content">
        <header className={styles.privacyHero}>
          <div className={styles.sectionInner}>
            <span className={styles.sectionKicker}>PRIVACY &amp; DATA HANDLING</span>
            <h1>隐私与数据处理</h1>
            <p>
              这里说明 Vibio SEO 网页版在当前版本中如何处理你输入的 Key、项目信息、证据文件、公开 URL 与运行报告。我们尽量用产品的实际行为来描述边界。
            </p>
            <div className={styles.privacyMeta}>
              <span>VIBIO SEO V5.0</span>
              <span>更新日期：2026-07-13</span>
            </div>
          </div>
        </header>

        <div className={`${styles.sectionInner} ${styles.privacyContent}`}>
          <aside className={styles.privacyToc} aria-label="本页目录">
            <span>ON THIS PAGE</span>
            {sections.map(([id, label]) => (
              <a href={`#${id}`} key={id}>{label}</a>
            ))}
          </aside>

          <article className={styles.privacyArticle}>
            <p className={styles.privacyIntro}>
              Vibio SEO 当前没有账号系统或云端项目库。项目草稿和运行历史保存在当前浏览器；模型分析时，本次任务的项目信息与证据会发送到你选择的模型服务商。
            </p>

            <section className={styles.privacySection} id="overview">
              <h2>1. 处理概览</h2>
              <p>Vibio SEO 的网页版会处理以下几类数据：</p>
              <div className={styles.privacyBoundary}>
                <div>
                  <strong>项目信息</strong>
                  <span>站点、目标市场、语言、业务、主要转化与当前任务。</span>
                </div>
                <div>
                  <strong>模型设置</strong>
                  <span>你选择的服务商、模型 ID 与当前会话中的 API Key。</span>
                </div>
                <div>
                  <strong>任务证据</strong>
                  <span>你上传的文本文件、公开 URL 抓取结果与流程上下文。</span>
                </div>
                <div>
                  <strong>运行结果</strong>
                  <span>模型返回的报告、完成时间和证据文件的名称、类型、大小。</span>
                </div>
              </div>
            </section>

            <section className={styles.privacySection} id="key">
              <h2>2. API Key 如何处理</h2>
              <p>
                你输入的 API Key 保存在当前标签页的 <code>sessionStorage</code> 中，用于同一浏览器会话内的后续请求。当浏览器存储不可用时，Key 只保留在页面当前的内存状态中。
              </p>
              <p>
                运行分析时，Key 通过单次请求发给 Vibio 的服务端路由，再用于请求你选择的模型服务商官方接口。Vibio 的应用代码不会把 Key 写入项目草稿、运行历史或服务端持久化存储。
              </p>
              <p>请使用限额、可撤销的 Key，并在对应模型平台中定期检查用量与权限。</p>
            </section>

            <section className={styles.privacySection} id="browser">
              <h2>3. 当前浏览器中的存储</h2>
              <h3>项目草稿</h3>
              <p>
                项目表单保存在 <code>localStorage</code> 中，让你在同一浏览器中不必重复输入。所选模型服务商与模型 ID 也保存在当前浏览器，但 API Key 不会进入这份本地偏好。
              </p>
              <h3>运行历史</h3>
              <p>
                最近的运行记录保存在 <code>localStorage</code> 中。记录包含项目摘要、模型、报告、公开 URL 审计结果，以及上传文件的名称、类型和大小。运行历史不保存 API Key，也不保存上传文件的原始内容。
              </p>
              <p>这些数据不会自动跨设备同步，也不会自动进入 Vibio 的云端项目库。</p>
            </section>

            <section className={styles.privacySection} id="evidence">
              <h2>4. 上传证据与公开 URL</h2>
              <h3>上传文件</h3>
              <p>
                支持的证据是 CSV、JSON、HTML、XML、Markdown 和 TXT 等文本格式。文件内容会在浏览器中读取，并作为当次分析请求的一部分发送到 Vibio 服务端和你选择的模型服务商。
              </p>
              <p>
                请只上传完成当前任务所需的聚合、脱敏资料。应用会拒绝常见的密钥、Cookie、密码、邮箱、电话、身份证号码和稳定个人标识等敏感内容，但这不代表自动检测能发现所有敏感数据。
              </p>
              <h3>公开 URL</h3>
              <p>
                当你授权读取公开 URL 时，Vibio 会在服务端请求该站点的匿名 HTTP 源码、robots.txt、sitemap 与同源页面。抓取范围有页数、响应大小和超时上限；抓取器拒绝本机、私网、链路本地、凭据 URL 和混合公网/私网 DNS 结果。
              </p>
              <p>当前 URL 审计不执行 JavaScript，不登录站点，也不能证明搜索引擎的真实抓取、收录、canonical 选择或排名状态。</p>
            </section>

            <section className={styles.privacySection} id="providers">
              <h2>5. 第三方模型服务</h2>
              <p>
                Vibio SEO 当前支持你使用自己的 Key 请求 DeepSeek、Xiaomi MiMo、OpenAI、Qwen、Kimi、Zhipu AI 和 SiliconFlow。运行任务时，你选择的提供商会收到为本次分析组装的提示、项目信息、证据和流程上下文。
              </p>
              <p>
                第三方服务如何处理、保留或用于改进你提交的内容，由你与对应服务商之间的账号、套餐、设置与条款决定。在运行前，请检查所选服务商的隐私政策、数据保留选项和区域要求。
              </p>
            </section>

            <section className={styles.privacySection} id="delete">
              <h2>6. 查看、导出与删除</h2>
              <p>当前版本的数据操作都在你正在使用的浏览器中完成：</p>
              <ol className={styles.privacyActions}>
                <li>
                  <strong>清除 API Key</strong>
                  <span>在工作台中清空 Key 输入，或关闭当前标签页/浏览器会话。</span>
                </li>
                <li>
                  <strong>删除运行历史</strong>
                  <span>打开工作台的“运行记录”，使用清空功能删除当前浏览器中的记录。</span>
                </li>
                <li>
                  <strong>删除项目草稿</strong>
                  <span>清空项目字段，或在浏览器设置中删除本站的站点数据。</span>
                </li>
                <li>
                  <strong>导出报告</strong>
                  <span>在报告页中复制 Markdown，或下载 Markdown、JSON 和独立 HTML 文件。</span>
                </li>
              </ol>
              <p>清除本地数据不会自动删除第三方模型服务商已经处理的请求。这部分需要按对应服务商的账号设置和政策处理。</p>
            </section>

            <Link className={styles.inlineLink} href="/">
              <ArrowLeft size={16} aria-hidden="true" />
              返回 Vibio SEO 首页
            </Link>
          </article>
        </div>
      </main>
    </div>
  );
}
