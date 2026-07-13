import { Clock3, FileClock, Trash2, X } from "lucide-react";
import type { ModeDefinition, RunRecord } from "../types";

interface HistoryDrawerProps {
  open: boolean;
  runs: RunRecord[];
  modes: ModeDefinition[];
  onClose: () => void;
  onSelect: (run: RunRecord) => void;
  onClear: () => void;
}

export function HistoryDrawer({ open, runs, modes, onClose, onSelect, onClear }: HistoryDrawerProps) {
  if (!open) return null;

  return (
    <div className="drawer-layer" role="presentation" onMouseDown={onClose}>
      <aside
        className="history-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="history-heading"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header>
          <div>
            <span className="eyebrow">当前浏览器</span>
            <h2 id="history-heading">运行记录</h2>
          </div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="关闭运行记录" title="关闭">
            <X size={18} />
          </button>
        </header>

        <div className="history-list">
          {runs.length === 0 ? (
            <div className="history-empty">
              <FileClock size={24} />
              <p>还没有本地运行记录。</p>
            </div>
          ) : (
            runs.map((run) => {
              const mode = modes.find((item) => item.id === run.mode);
              return (
                <button type="button" className="history-item" key={run.id} onClick={() => onSelect(run)}>
                  <span className={`history-item__mode history-item__mode--${mode?.accent ?? "slate"}`}>
                    {mode?.code ?? "--"}
                  </span>
                  <span className="history-item__body">
                    <strong>{run.projectName}</strong>
                    <span>{mode?.label} · {run.objective}</span>
                    <small><Clock3 size={12} />{new Date(run.createdAt).toLocaleString("zh-CN")}</small>
                  </span>
                </button>
              );
            })
          )}
        </div>

        {runs.length > 0 && (
          <footer>
            <button type="button" className="text-button text-button--danger" onClick={onClear}>
              <Trash2 size={15} />
              清空本地记录
            </button>
          </footer>
        )}
      </aside>
    </div>
  );
}
