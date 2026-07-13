import { FileJson2, FileSpreadsheet, FileText, Globe2, Trash2, Upload } from "lucide-react";
import { useRef, useState } from "react";
import {
  ACCEPTED_EVIDENCE,
  MAX_EVIDENCE_BYTES,
  MAX_EVIDENCE_FILES,
  MAX_EVIDENCE_TOTAL_BYTES,
} from "../data";
import type { EvidenceFile, ModeDefinition } from "../types";

interface EvidencePanelProps {
  mode: ModeDefinition;
  files: EvidenceFile[];
  onChange: (files: EvidenceFile[]) => void;
  siteUrl: string;
  networkEnabled: boolean;
  maxPages: number;
  onMaxPagesChange: (value: number) => void;
  onError: (message: string) => void;
  disabled?: boolean;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}

function fileIcon(name: string) {
  if (name.endsWith(".csv")) return FileSpreadsheet;
  if (name.endsWith(".json")) return FileJson2;
  return FileText;
}

export function EvidencePanel({
  mode,
  files,
  onChange,
  siteUrl,
  networkEnabled,
  maxPages,
  onMaxPagesChange,
  onError,
  disabled = false,
}: EvidencePanelProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const addFiles = async (list: FileList | File[]) => {
    const incoming = Array.from(list);
    if (files.length + incoming.length > MAX_EVIDENCE_FILES) {
      onError(`单次最多添加 ${MAX_EVIDENCE_FILES} 份证据文件。`);
      return;
    }
    const totalBytes = files.reduce((sum, file) => sum + file.size, 0)
      + incoming.reduce((sum, file) => sum + file.size, 0);
    if (totalBytes > MAX_EVIDENCE_TOTAL_BYTES) {
      onError("模型证据包总大小不能超过 90 KB。");
      return;
    }

    const next: EvidenceFile[] = [];
    for (const file of incoming) {
      if (file.size > MAX_EVIDENCE_BYTES) {
        onError(`${file.name} 超过 ${MAX_EVIDENCE_BYTES / 1024} KB 上限。`);
        return;
      }
      const extension = `.${file.name.split(".").pop()?.toLowerCase() ?? ""}`;
      if (!ACCEPTED_EVIDENCE.split(",").includes(extension)) {
        onError(`${file.name} 不是支持的文本证据格式。`);
        return;
      }
      const content = await file.text();
      next.push({
        id: crypto.randomUUID(),
        name: file.name,
        type: file.type || extension.slice(1),
        size: file.size,
        content,
      });
    }
    onChange([...files, ...next]);
  };

  return (
    <section className="side-section evidence-panel" aria-labelledby="evidence-heading">
      <div className="side-section__heading">
        <div>
          <span className="eyebrow">输入材料</span>
          <h2 id="evidence-heading">证据包</h2>
        </div>
        <span className="evidence-count">{files.length}/{MAX_EVIDENCE_FILES}</span>
      </div>

      {siteUrl && networkEnabled ? (
        <div className="url-evidence">
          <div className="url-evidence__main">
            <Globe2 size={16} aria-hidden="true" />
            <div>
              <strong>HTTP 源码审计</strong>
              <span>{siteUrl}</span>
            </div>
            <span className="tag tag--ready">已授权</span>
          </div>
          <label className="stepper-control">
            <span>抓取页数</span>
            <input
              type="number"
              min={1}
              max={10}
              value={maxPages}
              onChange={(event) =>
                onMaxPagesChange(Math.min(10, Math.max(1, Number(event.target.value) || 1)))
              }
              disabled={disabled}
            />
          </label>
        </div>
      ) : (
        <div className="url-evidence url-evidence--muted">
          <Globe2 size={16} aria-hidden="true" />
          <span>{siteUrl ? "公开 URL 读取未授权" : "未提供公开站点 URL"}</span>
        </div>
      )}

      <button
        type="button"
        className={`dropzone${dragging ? " is-dragging" : ""}`}
        onClick={() => inputRef.current?.click()}
        onDragEnter={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          void addFiles(event.dataTransfer.files);
        }}
        disabled={disabled}
      >
        <Upload size={18} aria-hidden="true" />
        <strong>添加证据文件</strong>
        <span>CSV · JSON · HTML · XML · MD · TXT</span>
      </button>
      <input
        ref={inputRef}
        className="sr-only"
        type="file"
        accept={ACCEPTED_EVIDENCE}
        multiple
        onChange={(event) => {
          if (event.target.files) void addFiles(event.target.files);
          event.target.value = "";
        }}
      />

      {files.length > 0 && (
        <div className="file-list" aria-label="已添加证据">
          {files.map((file) => {
            const Icon = fileIcon(file.name.toLowerCase());
            return (
              <div className="file-item" key={file.id}>
                <Icon size={16} aria-hidden="true" />
                <div>
                  <strong>{file.name}</strong>
                  <span>{formatBytes(file.size)}</span>
                </div>
                <button
                  type="button"
                  className="icon-button icon-button--bare"
                  onClick={() => onChange(files.filter((item) => item.id !== file.id))}
                  aria-label={`移除 ${file.name}`}
                  title="移除文件"
                  disabled={disabled}
                >
                  <Trash2 size={15} />
                </button>
              </div>
            );
          })}
        </div>
      )}

      <p className="evidence-hint">{mode.evidenceHint}</p>
      <p className="privacy-boundary">请仅上传聚合、脱敏资料；Key、Cookie、联系人和 CRM 原始行会被拒绝。</p>
    </section>
  );
}
