import { Check, Globe2, LockKeyhole, Target } from "lucide-react";
import type { ModeDefinition, ProjectInput } from "../types";

interface ProjectFormProps {
  mode: ModeDefinition;
  project: ProjectInput;
  onChange: (project: ProjectInput) => void;
  disabled?: boolean;
}

export function ProjectForm({ mode, project, onChange, disabled = false }: ProjectFormProps) {
  const update = <K extends keyof ProjectInput>(key: K, value: ProjectInput[K]) => {
    onChange({ ...project, [key]: value });
  };

  return (
    <div className="project-form">
      <header className="mode-intro">
        <div className={`mode-intro__index mode-intro__index--${mode.accent}`}>{mode.code}</div>
        <div>
          <span className="eyebrow">{mode.label} / {mode.id.toUpperCase()}</span>
          <h1>{mode.title}</h1>
          <p>{mode.description}</p>
        </div>
      </header>

      <section className="form-section" aria-labelledby="project-basics">
        <div className="form-section__title">
          <Globe2 size={17} aria-hidden="true" />
          <h2 id="project-basics">项目坐标</h2>
          <span>01</span>
        </div>
        <div className="form-grid form-grid--two">
          <label className="field">
            <span>项目名称 *</span>
            <input
              value={project.projectName}
              onChange={(event) => update("projectName", event.target.value)}
              placeholder="例如：Vibio 德国站"
              disabled={disabled}
            />
          </label>
          <label className="field">
            <span>站点 URL</span>
            <input
              type="url"
              value={project.siteUrl}
              onChange={(event) => update("siteUrl", event.target.value)}
              placeholder="https://example.com"
              disabled={disabled}
            />
          </label>
          <label className="field">
            <span>目标国家 / 地区 *</span>
            <input
              value={project.market}
              onChange={(event) => update("market", event.target.value)}
              placeholder="例如：德国"
              disabled={disabled}
            />
          </label>
          <label className="field">
            <span>目标语言 *</span>
            <input
              value={project.language}
              onChange={(event) => update("language", event.target.value)}
              placeholder="例如：de-DE"
              disabled={disabled}
            />
          </label>
          <label className="field">
            <span>主要合格转化 *</span>
            <input
              value={project.conversion}
              onChange={(event) => update("conversion", event.target.value)}
              placeholder="例如：通过技术评审的 RFQ"
              disabled={disabled}
            />
          </label>
          <label className="field">
            <span>目标买家</span>
            <input
              value={project.audience}
              onChange={(event) => update("audience", event.target.value)}
              placeholder="角色、公司类型、采购阶段"
              disabled={disabled}
            />
          </label>
        </div>
        <div className="form-grid form-grid--two form-grid--secondary">
          <label className="field">
            <span>业务与产品</span>
            <input
              value={project.businessModel}
              onChange={(event) => update("businessModel", event.target.value)}
              placeholder="商业模式、核心产品或服务"
              disabled={disabled}
            />
          </label>
          <label className="field">
            <span>分析范围</span>
            <input
              value={project.scope}
              onChange={(event) => update("scope", event.target.value)}
              placeholder="全站、目录、模板组或单页"
              disabled={disabled}
            />
          </label>
        </div>
      </section>

      <section className="form-section" aria-labelledby="project-decision">
        <div className="form-section__title">
          <Target size={17} aria-hidden="true" />
          <h2 id="project-decision">本次决策</h2>
          <span>02</span>
        </div>
        <label className="field">
          <span>当前目标 / 问题 *</span>
          <textarea
            rows={3}
            value={project.objective}
            onChange={(event) => update("objective", event.target.value)}
            placeholder="这次运行完成后，你需要做出什么决定？"
            disabled={disabled}
          />
        </label>
        <label className="field">
          <span>{mode.detailLabel}</span>
          <textarea
            rows={5}
            value={project.details}
            onChange={(event) => update("details", event.target.value)}
            placeholder={mode.detailPlaceholder}
            disabled={disabled}
          />
        </label>
        <div className="form-grid form-grid--two form-grid--secondary">
          <label className="field">
            <span>执行产能 / 负责人</span>
            <input
              value={project.capacity}
              onChange={(event) => update("capacity", event.target.value)}
              placeholder="例如：SEO 1 人，开发每周 2 天"
              disabled={disabled}
            />
          </label>
          <label className="field">
            <span>决策 / 观察窗口</span>
            <input
              value={project.decisionWindow}
              onChange={(event) => update("decisionWindow", event.target.value)}
              placeholder="使用项目自身周期，不套固定天数"
              disabled={disabled}
            />
          </label>
        </div>
      </section>

      <section className="form-section form-section--permissions" aria-labelledby="permission-heading">
        <div className="form-section__title">
          <LockKeyhole size={17} aria-hidden="true" />
          <h2 id="permission-heading">授权边界</h2>
          <span>03</span>
        </div>
        <div className="permission-row">
          <label className="check-control">
            <input
              type="checkbox"
              checked={project.allowNetworkEvidence}
              onChange={(event) => update("allowNetworkEvidence", event.target.checked)}
              disabled={disabled}
            />
            <span className="check-control__box"><Check size={13} /></span>
            <span>读取公开 URL 证据</span>
          </label>
          <label className="check-control">
            <input
              type="checkbox"
              checked={project.allowStateDraft}
              onChange={(event) => update("allowStateDraft", event.target.checked)}
              disabled={disabled}
            />
            <span className="check-control__box"><Check size={13} /></span>
            <span>生成项目状态草稿</span>
          </label>
          <span className="permission-boundary">不含部署、发信、CMS 或广告操作</span>
        </div>
      </section>
    </div>
  );
}
