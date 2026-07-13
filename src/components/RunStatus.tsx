import { Check, CircleDashed, LoaderCircle, SearchCheck, Sparkles } from "lucide-react";
import type { RunStage } from "../types";

const STEPS: Array<{ id: Exclude<RunStage, "idle" | "error">; label: string }> = [
  { id: "validating", label: "校验输入" },
  { id: "collecting", label: "收集证据" },
  { id: "analyzing", label: "模型分析" },
  { id: "complete", label: "生成报告" },
];

const ORDER: Record<RunStage, number> = {
  idle: -1,
  validating: 0,
  collecting: 1,
  analyzing: 2,
  complete: 3,
  error: -1,
};

const ACTIVE_ICONS = [CircleDashed, SearchCheck, Sparkles, Check];

interface RunStatusProps {
  stage: RunStage;
  analysisLabel?: string;
}

export function RunStatus({ stage, analysisLabel }: RunStatusProps) {
  if (stage === "idle") return null;
  const activeIndex = ORDER[stage];

  return (
    <div className={`run-status${stage === "error" ? " is-error" : ""}`} aria-live="polite">
      {stage === "error" ? (
        <span>运行未完成，请检查下方错误后重试。</span>
      ) : (
        STEPS.map((step, index) => {
          const finished = index < activeIndex || stage === "complete";
          const active = index === activeIndex && stage !== "complete";
          const Icon = active ? LoaderCircle : finished ? Check : ACTIVE_ICONS[index];
          const label = step.id === "analyzing" && analysisLabel ? analysisLabel : step.label;
          return (
            <div
              key={step.id}
              className={`run-status__step${active ? " is-active" : ""}${finished ? " is-finished" : ""}`}
            >
              <span><Icon size={14} className={active ? "spin" : ""} /></span>
              <strong>{label}</strong>
            </div>
          );
        })
      )}
    </div>
  );
}
