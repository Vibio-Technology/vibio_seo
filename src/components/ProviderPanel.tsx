import { Cpu, Eye, EyeOff, KeyRound, ShieldCheck } from "lucide-react";
import { useId, useMemo, useState } from "react";
import type { ModelSettings, ProviderDefinition } from "../types";

interface ProviderPanelProps {
  providers: ProviderDefinition[];
  settings: ModelSettings;
  onChange: (settings: ModelSettings) => void;
  loading?: boolean;
}

export function ProviderPanel({
  providers,
  settings,
  onChange,
  loading = false,
}: ProviderPanelProps) {
  const [showKey, setShowKey] = useState(false);
  const modelListId = useId();
  const provider = useMemo(
    () => providers.find((item) => item.id === settings.provider) ?? providers[0],
    [providers, settings.provider],
  );

  const changeProvider = (providerId: string) => {
    const next = providers.find((item) => item.id === providerId);
    if (!next) return;
    onChange({ ...settings, provider: providerId, model: next.default_model });
  };

  return (
    <form
      className="side-section provider-panel"
      aria-labelledby="provider-heading"
      autoComplete="off"
      onSubmit={(event) => event.preventDefault()}
    >
      <div className="side-section__heading">
        <div>
          <span className="eyebrow">模型内核</span>
          <h2 id="provider-heading">BYOK 连接</h2>
        </div>
        <Cpu size={18} aria-hidden="true" />
      </div>

      <label className="field field--compact">
        <span>提供商</span>
        <select
          value={settings.provider}
          onChange={(event) => changeProvider(event.target.value)}
          disabled={loading}
        >
          {providers.map((item) => (
            <option key={item.id} value={item.id}>
              {item.label}
            </option>
          ))}
        </select>
      </label>

      <label className="field field--compact">
        <span>模型 ID</span>
        <input
          list={modelListId}
          value={settings.model}
          onChange={(event) => onChange({ ...settings, model: event.target.value })}
          placeholder="输入接口支持的模型 ID"
          autoComplete="off"
          disabled={loading}
        />
        <datalist id={modelListId}>
          {provider?.models.map((model) => (
            <option key={model.id} value={model.id}>
              {model.label}
            </option>
          ))}
        </datalist>
      </label>

      <label className="field field--compact">
        <span>API Key</span>
        <div className="secret-input">
          <KeyRound size={15} aria-hidden="true" />
          <input
            type={showKey ? "text" : "password"}
            value={settings.apiKey}
            onChange={(event) => onChange({ ...settings, apiKey: event.target.value })}
            placeholder="输入当前提供商的 Key"
            autoComplete="new-password"
            name="provider-api-key"
            spellCheck={false}
            disabled={loading}
          />
          <button
            type="button"
            className="icon-button icon-button--bare"
            onClick={() => setShowKey((value) => !value)}
            title={showKey ? "隐藏 API Key" : "显示 API Key"}
            aria-label={showKey ? "隐藏 API Key" : "显示 API Key"}
          >
            {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>
      </label>

      <div className="security-note">
        <ShieldCheck size={15} aria-hidden="true" />
        <span>Key 仅保留在当前浏览器会话，不写入项目历史。</span>
      </div>
      <div className={`provider-state${settings.apiKey ? " is-ready" : ""}`}>
        <span className="status-dot" />
        <span>{settings.apiKey ? `${provider?.label ?? "模型"} 已就绪` : "等待 API Key"}</span>
      </div>
    </form>
  );
}
