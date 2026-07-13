import { Check, Clipboard, Code2, Download, FileText, RotateCcw, SearchCheck } from "lucide-react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { RunRecord } from "../types";

interface ReportViewProps {
  record: RunRecord;
  onReset: () => void;
}

function download(name: string, content: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  URL.revokeObjectURL(url);
}

function safeFileName(value: string): string {
  return value.trim().replace(/[^a-zA-Z0-9\u4e00-\u9fff_-]+/g, "-").slice(0, 48) || "vibio-report";
}

export function ReportView({ record, onReset }: ReportViewProps) {
  const [tab, setTab] = useState<"report" | "evidence">("report");
  const [copyStatus, setCopyStatus] = useState<"idle" | "copied" | "error">("idle");
  const baseName = `${safeFileName(record.projectName)}-${record.mode}-${record.createdAt.slice(0, 10)}`;

  const copyReport = async () => {
    try {
      await navigator.clipboard.writeText(record.report);
      setCopyStatus("copied");
    } catch {
      setCopyStatus("error");
    }
    window.setTimeout(() => setCopyStatus("idle"), 1600);
  };

  const jsonExport = JSON.stringify(
    {
      schema_version: "vibio-web.run.v1",
      ...record,
    },
    null,
    2,
  );

  return (
    <section className="report-view" aria-labelledby="report-title">
      <header className="report-header">
        <div>
          <span className="eyebrow">运行完成 · {record.provider} / {record.model}</span>
          <h1 id="report-title">{record.projectName}</h1>
          <p>{record.objective}</p>
        </div>
        <div className="report-actions">
          <button type="button" className="icon-button" onClick={copyReport} title="复制 Markdown">
            {copyStatus === "copied" ? <Check size={17} /> : <Clipboard size={17} />}
            <span>{copyStatus === "copied" ? "已复制" : copyStatus === "error" ? "复制失败" : "复制"}</span>
          </button>
          <button
            type="button"
            className="icon-button"
            onClick={() => download(`${baseName}.md`, record.report, "text/markdown;charset=utf-8")}
            title="下载 Markdown"
          >
            <Download size={17} />
            <span>Markdown</span>
          </button>
          <button
            type="button"
            className="icon-button"
            onClick={() => download(`${baseName}.json`, jsonExport, "application/json;charset=utf-8")}
            title="下载 JSON"
          >
            <Code2 size={17} />
            <span>JSON</span>
          </button>
          <button type="button" className="icon-button icon-button--primary" onClick={onReset}>
            <RotateCcw size={17} />
            <span>新建运行</span>
          </button>
        </div>
      </header>

      <div className="report-meta">
        <span>{record.market}</span>
        <span>{record.language}</span>
        <span>{record.siteUrl || "无公开 URL"}</span>
        <time dateTime={record.createdAt}>{new Date(record.createdAt).toLocaleString("zh-CN")}</time>
      </div>

      <div className="report-tabs" role="tablist" aria-label="报告视图">
        <button
          type="button"
          role="tab"
          aria-selected={tab === "report"}
          className={tab === "report" ? "is-active" : ""}
          onClick={() => setTab("report")}
        >
          <FileText size={16} />
          分析报告
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "evidence"}
          className={tab === "evidence" ? "is-active" : ""}
          onClick={() => setTab("evidence")}
        >
          <SearchCheck size={16} />
          证据清单
        </button>
      </div>

      {tab === "report" ? (
        <article className="markdown-report">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{record.report}</ReactMarkdown>
        </article>
      ) : (
        <div className="evidence-report">
          <div className="evidence-manifest">
            <h2>输入来源</h2>
            {record.siteUrl && (
              <div className="manifest-row">
                <GlobeManifestIcon />
                <div><strong>公开 URL</strong><span>{record.siteUrl}</span></div>
              </div>
            )}
            {record.evidence.map((file) => (
              <div className="manifest-row" key={file.name}>
                <FileText size={16} />
                <div><strong>{file.name}</strong><span>{Math.round(file.size / 1024)} KB · {file.type}</span></div>
              </div>
            ))}
            {!record.siteUrl && record.evidence.length === 0 && <p>本次运行没有附加外部证据。</p>}
          </div>
          {record.auditReport && (
            <details className="raw-evidence">
              <summary>查看确定性审计 JSON</summary>
              <pre>{JSON.stringify(record.auditReport, null, 2)}</pre>
            </details>
          )}
        </div>
      )}
    </section>
  );
}

function GlobeManifestIcon() {
  return <span className="manifest-globe" aria-hidden="true">URL</span>;
}
