"use client";

import {
  Check,
  CircleDashed,
  FileInput,
  Globe2,
  PencilLine,
  PlugZap,
  RotateCcw,
  Route,
  ShieldCheck,
  Workflow,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  AUTOMATION_EVIDENCE_SOURCES,
  AUTOMATION_MODE_ORDER,
  AUTOMATION_RECIPES,
  resolveAutomationModes,
  type AutomationConfig,
  type AutomationEvidenceAvailability,
  type AutomationEvidenceSource,
  type AutomationRecipeId,
} from "../automation";
import { MODES } from "../data";
import type { ModeId, ProjectProfile, WorkflowStep } from "../types";
import { buildWorkflowContextForMode } from "../workflow";
import { WorkflowProgress } from "./WorkflowProgress";

interface AutomationWorkspaceProps {
  profile: ProjectProfile;
  config: AutomationConfig;
  onChange: (config: AutomationConfig) => void;
  previewSteps: WorkflowStep[];
  steps: WorkflowStep[];
  evidenceAvailability: AutomationEvidenceAvailability;
  onEditProject: () => void;
  onResetFlow: () => void;
  disabled?: boolean;
}

const EVIDENCE_META: Record<AutomationEvidenceSource, {
  label: string;
  description: string;
}> = {
  site: { label: "公开站点", description: "HTTP 源码、robots 与 sitemap" },
  files: { label: "上传材料", description: "HTML、CSV、JSON 与说明文件" },
  gsc: { label: "GSC / Bing", description: "查询、页面、点击与曝光导出" },
  ga4: { label: "GA4", description: "落地页与聚合站内行为" },
  crm: { label: "CRM", description: "脱敏后的合格转化与商机汇总" },
  deployment: { label: "发布记录", description: "上线日期、变更范围与版本说明" },
};

function modeLabel(mode: ModeId): string {
  return MODES.find((item) => item.id === mode)?.label ?? mode;
}

export function AutomationWorkspace({
  profile,
  config,
  onChange,
  previewSteps,
  steps,
  evidenceAvailability,
  onEditProject,
  onResetFlow,
  disabled = false,
}: AutomationWorkspaceProps) {
  const resolvedModes = resolveAutomationModes(config.selectedModes);
  const latestStep = [...steps].reverse().find(
    (step) => step.status === "complete" && step.report?.trim(),
  );
  const nextStep = steps.find((step) => step.status === "error" || step.status === "pending");
  const nextContext = nextStep ? buildWorkflowContextForMode(steps, nextStep.mode) : null;
  const locked = steps.length > 0;

  const update = (patch: Partial<AutomationConfig>) => onChange({ ...config, ...patch });
  const selectRecipe = (recipeId: AutomationRecipeId) => {
    const recipe = AUTOMATION_RECIPES.find((item) => item.id === recipeId) ?? AUTOMATION_RECIPES[0];
    update({
      recipe: recipe.id,
      selectedModes: [...recipe.modes],
      evidenceSources: [...recipe.evidenceSources],
    });
  };
  const toggleMode = (mode: ModeId) => {
    const selected = new Set(config.selectedModes);
    if (selected.has(mode)) selected.delete(mode);
    else selected.add(mode);
    update({ selectedModes: AUTOMATION_MODE_ORDER.filter((item) => selected.has(item)) });
  };
  const toggleEvidence = (source: AutomationEvidenceSource) => {
    const selected = new Set(config.evidenceSources);
    if (selected.has(source)) selected.delete(source);
    else selected.add(source);
    update({
      evidenceSources: AUTOMATION_EVIDENCE_SOURCES.filter((item) => selected.has(item)),
    });
  };

  return (
    <div className="project-form automation-workspace">
      <section className="project-summary" aria-label="当前项目">
        <div className="project-summary__identity">
          <Globe2 size={18} aria-hidden="true" />
          <div>
            <span className="eyebrow">当前项目</span>
            <strong>{profile.projectName || "未命名项目"}</strong>
            {profile.siteUrl && <span>{profile.siteUrl}</span>}
          </div>
        </div>
        <dl className="project-summary__facts">
          <div><dt>市场</dt><dd>{profile.market || "待设置"}</dd></div>
          <div><dt>语言</dt><dd>{profile.language || "待设置"}</dd></div>
          <div><dt>合格转化</dt><dd>{profile.conversion || "待设置"}</dd></div>
        </dl>
        <button
          type="button"
          className="icon-button project-summary__edit"
          onClick={onEditProject}
          disabled={disabled}
        >
          <PencilLine size={16} aria-hidden="true" />
          <span>编辑项目</span>
        </button>
      </section>

      <header className="automation-intro">
        <span className="automation-intro__icon" aria-hidden="true"><Workflow size={21} /></span>
        <div>
          <span className="eyebrow">AUTO / ORCHESTRATION</span>
          <h1>编排 SEO 能力链</h1>
          <p>先定义任务和证据边界，再让每一步把结果交给真正依赖它的下一步。</p>
        </div>
        {locked && (
          <button type="button" className="text-button" onClick={onResetFlow} disabled={disabled}>
            <RotateCcw size={15} aria-hidden="true" />
            重新编排
          </button>
        )}
      </header>

      {locked ? (
        <section className="automation-console" aria-labelledby="automation-console-title">
          <div className="automation-section-heading">
            <div>
              <span className="eyebrow">LIVE WORKFLOW</span>
              <h2 id="automation-console-title">当前能力链</h2>
            </div>
            <span className="automation-recipe-tag">
              {AUTOMATION_RECIPES.find((item) => item.id === config.recipe)?.label}
            </span>
          </div>
          <WorkflowProgress steps={steps} compact />

          {latestStep && (
            <article className="automation-latest-output" aria-labelledby="automation-latest-title">
              <header>
                <div>
                  <span className="eyebrow">最近完成 · {modeLabel(latestStep.mode)}</span>
                  <h3 id="automation-latest-title">阶段结果</h3>
                </div>
                <span className="tag tag--ready"><Check size={12} />已进入上下文</span>
              </header>
              <div className="automation-markdown">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{latestStep.report}</ReactMarkdown>
              </div>
            </article>
          )}

          {nextStep && (
            <div className="automation-handoff">
              <Route size={17} aria-hidden="true" />
              <div>
                <span>下一步 · {modeLabel(nextStep.mode)}</span>
                <strong>
                  {nextContext && nextContext.completedReports.length > 0
                    ? `自动带入 ${nextContext.completedReports.map((item) => modeLabel(item.mode)).join("、")}`
                    : "使用项目档案与当前证据开始"}
                </strong>
              </div>
            </div>
          )}
        </section>
      ) : (
        <>
          <section className="automation-section" aria-labelledby="automation-objective-title">
            <div className="automation-section-heading">
              <div>
                <span className="automation-section-number">01</span>
                <h2 id="automation-objective-title">任务定义</h2>
              </div>
              <span>唯一必需的流程输入</span>
            </div>
            <label className="field automation-objective">
              <span>这次要推进什么结果？</span>
              <textarea
                rows={3}
                value={config.objective}
                onChange={(event) => update({ objective: event.target.value })}
                placeholder={profile.primaryGoal ? `默认：${profile.primaryGoal}` : "例如：定位产品目录阻断并形成可上线修复"}
                disabled={disabled}
              />
            </label>
          </section>

          <section className="automation-section" aria-labelledby="automation-recipe-title">
            <div className="automation-section-heading">
              <div>
                <span className="automation-section-number">02</span>
                <h2 id="automation-recipe-title">路线模板</h2>
              </div>
              <span>选择判断起点，可继续微调</span>
            </div>
            <div className="automation-recipes" role="radiogroup" aria-label="自动流程路线">
              {AUTOMATION_RECIPES.map((recipe) => (
                <button
                  type="button"
                  role="radio"
                  aria-checked={config.recipe === recipe.id}
                  className={config.recipe === recipe.id ? "is-active" : ""}
                  onClick={() => selectRecipe(recipe.id)}
                  disabled={disabled}
                  key={recipe.id}
                >
                  <span>{recipe.label}</span>
                  <small>{recipe.description}</small>
                </button>
              ))}
            </div>
          </section>

          <section className="automation-section" aria-labelledby="automation-route-title">
            <div className="automation-section-heading">
              <div>
                <span className="automation-section-number">03</span>
                <h2 id="automation-route-title">运行阶段</h2>
              </div>
              <span>依赖阶段会自动补入并排序</span>
            </div>
            <div className="automation-route-editor">
              {AUTOMATION_MODE_ORDER.map((modeId, index) => {
                const definition = MODES.find((item) => item.id === modeId);
                const direct = config.selectedModes.includes(modeId);
                const resolved = resolvedModes.includes(modeId);
                const dependencyOnly = resolved && !direct;
                const gatedStep = previewSteps.find((step) => step.mode === modeId);
                return (
                  <label className={`automation-route-node${resolved ? " is-selected" : ""}`} key={modeId}>
                    <input
                      type="checkbox"
                      checked={resolved}
                      onChange={() => toggleMode(modeId)}
                      disabled={disabled || dependencyOnly}
                    />
                    <span className="automation-route-node__index">{String(index + 1).padStart(2, "0")}</span>
                    <span>
                      <strong>{definition?.label ?? modeId}</strong>
                      <small>{definition?.title}</small>
                    </span>
                    <em>
                      {gatedStep?.status === "waiting"
                        ? "等待"
                        : gatedStep?.status === "skipped"
                          ? "条件"
                          : dependencyOnly
                            ? "依赖"
                            : direct ? "运行" : "关闭"}
                    </em>
                  </label>
                );
              })}
            </div>
          </section>

          <section className="automation-section" aria-labelledby="automation-evidence-title">
            <div className="automation-section-heading">
              <div>
                <span className="automation-section-number">04</span>
                <h2 id="automation-evidence-title">证据接入</h2>
              </div>
              <span>未检测到的导出可在右侧上传</span>
            </div>
            <div className="automation-evidence-grid">
              {AUTOMATION_EVIDENCE_SOURCES.map((source) => {
                const selected = config.evidenceSources.includes(source);
                const available = evidenceAvailability[source];
                const meta = EVIDENCE_META[source];
                return (
                  <label className={`automation-evidence-item${selected ? " is-selected" : ""}`} key={source}>
                    <input
                      type="checkbox"
                      checked={selected}
                      onChange={() => toggleEvidence(source)}
                      disabled={disabled}
                    />
                    <span className="automation-evidence-item__icon" aria-hidden="true">
                      {source === "site" ? <Globe2 size={16} /> : source === "files" ? <FileInput size={16} /> : <PlugZap size={16} />}
                    </span>
                    <span>
                      <strong>{meta.label}</strong>
                      <small>{meta.description}</small>
                    </span>
                    <em className={available ? "is-ready" : ""}>
                      {available ? <><Check size={12} />可用</> : <><CircleDashed size={12} />待上传</>}
                    </em>
                  </label>
                );
              })}
            </div>
          </section>

          <section className="automation-section automation-policy" aria-labelledby="automation-policy-title">
            <div className="automation-section-heading">
              <div>
                <span className="automation-section-number">05</span>
                <h2 id="automation-policy-title">推进方式</h2>
              </div>
              <span>所有生产动作仍需显式授权</span>
            </div>
            <div className="automation-policy-options" role="radiogroup" aria-label="流程推进方式">
              <button
                type="button"
                role="radio"
                aria-checked={config.advanceMode === "approval"}
                className={config.advanceMode === "approval" ? "is-active" : ""}
                onClick={() => update({ advanceMode: "approval" })}
                disabled={disabled}
              >
                <ShieldCheck size={17} aria-hidden="true" />
                <span><strong>逐步确认</strong><small>每个阶段完成后查看结果，再进入下一步</small></span>
              </button>
              <button
                type="button"
                role="radio"
                aria-checked={config.advanceMode === "continuous"}
                className={config.advanceMode === "continuous" ? "is-active" : ""}
                onClick={() => update({ advanceMode: "continuous" })}
                disabled={disabled}
              >
                <Workflow size={17} aria-hidden="true" />
                <span><strong>连续分析</strong><small>分析与草稿自动推进，发布、部署和外联不会执行</small></span>
              </button>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
