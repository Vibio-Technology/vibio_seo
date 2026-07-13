import {
  ChartNoAxesCombined,
  ClipboardList,
  FilePenLine,
  KeyRound,
  LifeBuoy,
  Network,
  SearchCheck,
  Wrench,
} from "lucide-react";
import type { ComponentType } from "react";
import type { ModeDefinition, ModeId } from "../types";

const ICONS: Record<ModeId, ComponentType<{ size?: number; strokeWidth?: number }>> = {
  plan: ClipboardList,
  audit: SearchCheck,
  fix: Wrench,
  keyword: KeyRound,
  write: FilePenLine,
  link: Network,
  review: ChartNoAxesCombined,
  recover: LifeBuoy,
};

interface ModeRailProps {
  modes: ModeDefinition[];
  activeMode: ModeId;
  onChange: (mode: ModeId) => void;
  disabled?: boolean;
}

export function ModeRail({ modes, activeMode, onChange, disabled = false }: ModeRailProps) {
  return (
    <aside className="mode-rail" aria-label="SEO 工作模式">
      <div className="mode-rail__heading">
        <span>工作模式</span>
        <span className="mode-rail__count">8</span>
      </div>
      <div className="mode-rail__items">
        {modes.map((mode) => {
          const Icon = ICONS[mode.id];
          const active = activeMode === mode.id;
          return (
            <button
              className={`mode-button mode-button--${mode.accent}${active ? " is-active" : ""}`}
              type="button"
              key={mode.id}
              aria-pressed={active}
              onClick={() => onChange(mode.id)}
              disabled={disabled}
            >
              <span className="mode-button__icon" aria-hidden="true">
                <Icon size={17} strokeWidth={1.8} />
              </span>
              <span className="mode-button__label">
                <strong>{mode.label}</strong>
                <small>{mode.title}</small>
              </span>
              <span className="mode-button__code">{mode.code}</span>
            </button>
          );
        })}
      </div>
      <div className="mode-rail__footer">
        <span className="status-dot" />
        <span>证据优先 · 无虚构指标</span>
      </div>
    </aside>
  );
}
