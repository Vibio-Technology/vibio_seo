import { Clock3, FileClock, Trash2, X } from "lucide-react";
import { useEffect, useRef } from "react";
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
  const drawerRef = useRef<HTMLElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const onCloseRef = useRef(onClose);
  const restoreFocus = useRef(true);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!open) return;
    const previouslyFocused = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;
    restoreFocus.current = true;
    const frame = window.requestAnimationFrame(() => closeButtonRef.current?.focus());
    const handleKeyDown = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab" || !drawerRef.current) return;
      const focusable = [...drawerRef.current.querySelectorAll<HTMLElement>(
        "button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex='-1'])",
      )].filter((element) => element.getClientRects().length > 0);
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      window.cancelAnimationFrame(frame);
      document.removeEventListener("keydown", handleKeyDown);
      if (restoreFocus.current) previouslyFocused?.focus();
    };
  }, [open]);

  if (!open) return null;

  return (
    <div className="drawer-layer" role="presentation" onMouseDown={onClose}>
      <aside
        ref={drawerRef}
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
          <button ref={closeButtonRef} className="icon-button" type="button" onClick={onClose} aria-label="关闭运行记录" title="关闭">
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
              const workflow = run.mode === "workflow";
              const mode = workflow ? undefined : modes.find((item) => item.id === run.mode);
              return (
                <button
                  type="button"
                  className="history-item"
                  key={run.id}
                  onClick={() => {
                    restoreFocus.current = false;
                    onSelect(run);
                  }}
                >
                  <span className={`history-item__mode history-item__mode--${workflow ? "cyan" : (mode?.accent ?? "slate")}`}>
                    {workflow ? "AUTO" : (mode?.code ?? "--")}
                  </span>
                  <span className="history-item__body">
                    <strong>{run.projectName}</strong>
                    <span>{workflow ? "自动全流程" : mode?.label} · {run.objective}</span>
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
