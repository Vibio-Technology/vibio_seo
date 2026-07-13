import type { RunRecord } from "./types";

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function buildStandaloneReportHtml(
  record: RunRecord,
  overviewMarkup: string,
  reportMarkup: string,
): string {
  const title = `${record.projectName} - Vibio SEO 报告`;
  const generatedAt = new Date(record.createdAt).toLocaleString("zh-CN");
  const overview = overviewMarkup
    ? `<section class="export-section"><h2>确定性审计概览</h2>${overviewMarkup}</section>`
    : "";

  return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:">
  <title>${escapeHtml(title)}</title>
  <style>
    :root{color:#172033;background:#f7f9fc;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",sans-serif}
    *{box-sizing:border-box}body{margin:0;padding:40px 20px;line-height:1.65}.report{max-width:980px;margin:0 auto;background:#fff;border:1px solid #d9e2ec;border-radius:8px;padding:36px;box-shadow:0 16px 42px rgba(23,32,51,.08)}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
    header{padding-bottom:22px;border-bottom:1px solid #d9e2ec}h1{margin:4px 0 8px;font-size:32px}h2{margin:30px 0 14px;font-size:21px}h3{margin:22px 0 10px;font-size:16px}p,li{font-size:14px}.meta{display:flex;flex-wrap:wrap;gap:8px 18px;margin-top:12px;color:#627084;font-size:12px}.export-section{margin-top:26px;padding-top:4px;border-top:1px solid #d9e2ec}
    table{width:100%;border-collapse:collapse;margin:16px 0;font-size:12px}th,td{padding:9px 10px;border:1px solid #d9e2ec;text-align:left;vertical-align:top}th{background:#f9fbfd}blockquote{margin:16px 0;padding:10px 14px;border-left:3px solid #0f66e8;background:#eef6ff}code,pre{font-family:ui-monospace,SFMono-Regular,Consolas,monospace}code{padding:2px 4px;background:#fff1e9}pre{overflow:auto;padding:14px;border-radius:6px;color:#e7ebf2;background:#1d222a;white-space:pre-wrap}
    details{margin:10px 0;border:1px solid #d9e2ec;border-radius:8px;background:#fff}summary{padding:12px 14px;cursor:pointer;font-weight:700}details>div,details>ol,details>ul{padding:0 14px 14px}
    .audit-overview__header{display:grid;gap:7px;margin:0 0 20px}.audit-overview__eyebrow{color:#0b52bd;font:700 10px ui-monospace,SFMono-Regular,Consolas,monospace}.audit-overview__title{display:none}.audit-overview__intro{max-width:760px;margin:0;color:#627084;font-size:12px;line-height:1.7}
    .audit-overview__scope{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));margin:0 0 12px;border-top:1px solid #d9e2ec;border-bottom:1px solid #d9e2ec;background:#f9fbfd}.audit-overview__metric{padding:12px 14px}.audit-overview__metric+.audit-overview__metric{border-left:1px solid #d9e2ec}.audit-overview__metric-label{color:#627084;font-size:10px;font-weight:700}.audit-overview__metric-value{margin:3px 0 0;font-size:20px;font-weight:750}.audit-overview__scope-meta{display:flex;flex-wrap:wrap;gap:5px 18px;margin-bottom:22px;color:#627084;font-size:10px}.audit-overview__scope-meta span:first-child{overflow-wrap:anywhere;font-family:ui-monospace,SFMono-Regular,Consolas,monospace}
    .audit-overview__section-heading{display:flex;align-items:center;justify-content:space-between;gap:12px}.audit-overview__section-title{margin:0;font-size:15px}.audit-overview__section-count{color:#627084;font-size:10px}.audit-overview__severity,.audit-overview__group-section,.audit-overview__pages-section,.audit-overview__limitations{margin-top:24px}.audit-overview__severity-list{display:flex;flex-wrap:wrap;gap:7px;margin:10px 0 0;padding:0;list-style:none}.audit-overview__severity-item{display:inline-flex;align-items:center;gap:8px;min-height:27px;padding:2px 8px;border:1px solid #8293a8;border-radius:5px;background:#f2f4f7;color:#475467;font-size:11px}.audit-overview__severity-count{font-variant-numeric:tabular-nums}.audit-overview__severity-item--critical{border-color:#d92d20;background:#fef3f2;color:#b42318}.audit-overview__severity-item--high{border-color:#d65a21;background:#fff4ed;color:#b54708}.audit-overview__severity-item--medium{border-color:#b7791f;background:#fffaeb;color:#9a6700}.audit-overview__severity-item--low{border-color:#0f66e8;background:#eef6ff;color:#0b52bd}
    .audit-overview__groups{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:10px}.audit-overview__group{min-width:0;padding:14px;border:1px solid #d9e2ec;border-radius:8px;background:#fff;break-inside:avoid}.audit-overview__group-header{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:start;gap:10px}.audit-overview__group-icon{display:none}.audit-overview__group-title{margin:0;font-size:14px}.audit-overview__group-description{margin:4px 0 0;color:#627084;font-size:10px;line-height:1.55}.audit-overview__group-count{font-size:20px;font-variant-numeric:tabular-nums}.audit-overview__group-details{margin:13px 0 0;padding-top:10px;border:0;border-top:1px solid #d9e2ec;border-radius:0}.audit-overview__group-summary{display:flex;align-items:center;justify-content:space-between;min-height:30px;padding:0;color:#0b52bd;font-size:11px}.audit-overview__findings{display:grid;gap:8px;margin:9px 0 0;padding:0!important;list-style:none}
    .audit-overview__finding{padding:11px;border:1px solid #d9e2ec;border-left:3px solid #8293a8;background:#fff;break-inside:avoid}.audit-overview__finding--critical{border-left-color:#d92d20}.audit-overview__finding--high{border-left-color:#d65a21}.audit-overview__finding--medium{border-left-color:#b7791f}.audit-overview__finding--low{border-left-color:#0f66e8}.audit-overview__finding-header{display:flex;align-items:flex-start;gap:7px}.audit-overview__label{display:inline-flex;flex:0 0 auto;align-items:center;min-height:20px;padding:1px 6px;border:1px solid #8293a8;border-radius:4px;background:#f2f4f7;color:#475467;font-size:10px;font-weight:700}.audit-overview__label--critical{border-color:#d92d20;background:#fef3f2;color:#b42318}.audit-overview__label--high{border-color:#d65a21;background:#fff4ed;color:#b54708}.audit-overview__label--medium{border-color:#b7791f;background:#fffaeb;color:#9a6700}.audit-overview__label--low{border-color:#0f66e8;background:#eef6ff;color:#0b52bd}.audit-overview__observation{min-width:0;font-size:12px;line-height:1.55}.audit-overview__finding-meta{margin:7px 0 0;overflow-wrap:anywhere;color:#627084;font:10px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace}.audit-overview__finding-details{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px 14px;margin:10px 0 0;color:#344054;font-size:10px;line-height:1.6}.audit-overview__finding-field{min-width:0}.audit-overview__finding-field dt{font-weight:700;color:#172033}.audit-overview__finding-field dd{margin:3px 0 0;overflow-wrap:anywhere}.audit-overview__value-list{display:grid;gap:2px;margin:0;padding-left:17px}
    .audit-overview__pages{margin-top:10px;overflow-x:auto;border:1px solid #d9e2ec;border-radius:8px}.audit-overview__table{min-width:900px;margin:0}.audit-overview__table th,.audit-overview__table td{border-width:0 0 1px;padding:8px 9px}.audit-overview__table tr:last-child td{border-bottom:0}.audit-overview__limitations-list{display:grid;gap:7px;margin:10px 0 0;padding:0;list-style:none}.audit-overview__boundary{display:block;margin:0;padding:10px 12px;border:1px solid #d9e2ec;border-left:3px solid #0f66e8;border-radius:0 8px 8px 0;background:#f9fbfd;color:#475467;font-size:11px;line-height:1.65}.audit-overview__boundary--warning{border-color:#f3d19e;border-left-color:#b7791f;background:#fff7e6;color:#7a5b14}.audit-overview__empty{padding:10px 12px;border:1px solid #d9e2ec;border-radius:8px;background:#f9fbfd;color:#627084;font-size:11px}.export-section svg,.report-tabs,.report-actions,button{display:none!important}
    @media(max-width:720px){body{padding:0}.report{border:0;border-radius:0;padding:22px 16px}h1{font-size:26px}.audit-overview__scope,.audit-overview__groups{grid-template-columns:1fr}.audit-overview__metric+.audit-overview__metric{border-top:1px solid #d9e2ec;border-left:0}.audit-overview__finding-details{grid-template-columns:1fr}}
  </style>
</head>
<body>
  <main class="report">
    <header>
      <small>VIBIO SEO · ${escapeHtml(record.provider)} / ${escapeHtml(record.model)}</small>
      <h1>${escapeHtml(record.projectName)}</h1>
      <p>${escapeHtml(record.objective)}</p>
      <div class="meta"><span>${escapeHtml(record.market)}</span><span>${escapeHtml(record.language)}</span><span>${escapeHtml(record.siteUrl || "无公开 URL")}</span><time>${escapeHtml(generatedAt)}</time></div>
    </header>
    ${overview}
    <section class="export-section"><h2>分析报告</h2>${reportMarkup}</section>
  </main>
</body>
</html>`;
}
