import { MAX_PROVIDER_RESPONSE_BYTES } from "./privacy";

export interface ChatMessage {
  role: "system" | "user";
  content: string;
}

interface Provider {
  id: string;
  label: string;
  description: string;
  endpoint: string;
  defaultModel: string;
  models: ReadonlyArray<{ id: string; label: string }>;
}

export interface PublicProvider {
  id: string;
  label: string;
  description: string;
  default_model: string;
  models: Array<{ id: string; label: string }>;
  model_editable: true;
}

export const PROVIDERS: Readonly<Record<string, Provider>> = {
  deepseek: {
    id: "deepseek",
    label: "DeepSeek",
    description: "DeepSeek V4 官方 OpenAI 兼容接口。",
    endpoint: "https://api.deepseek.com/chat/completions",
    defaultModel: "deepseek-v4-flash",
    models: [
      { id: "deepseek-v4-flash", label: "DeepSeek V4 Flash" },
      { id: "deepseek-v4-pro", label: "DeepSeek V4 Pro" },
    ],
  },
  mimo: {
    id: "mimo",
    label: "Xiaomi MiMo",
    description: "Xiaomi MiMo 官方 OpenAI 兼容接口。",
    endpoint: "https://api.xiaomimimo.com/v1/chat/completions",
    defaultModel: "mimo-v2-flash",
    models: [{ id: "mimo-v2-flash", label: "MiMo V2 Flash" }],
  },
  openai: {
    id: "openai",
    label: "OpenAI",
    description: "OpenAI Chat Completions 接口。",
    endpoint: "https://api.openai.com/v1/chat/completions",
    defaultModel: "gpt-4.1-mini",
    models: [
      { id: "gpt-4.1-mini", label: "GPT-4.1 mini" },
      { id: "gpt-4.1", label: "GPT-4.1" },
    ],
  },
  qwen: {
    id: "qwen",
    label: "Qwen",
    description: "阿里云 DashScope 千问 OpenAI 兼容接口。",
    endpoint: "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
    defaultModel: "qwen-plus",
    models: [
      { id: "qwen-plus", label: "Qwen Plus" },
      { id: "qwen-max", label: "Qwen Max" },
      { id: "qwen-turbo", label: "Qwen Turbo" },
    ],
  },
  moonshot: {
    id: "moonshot",
    label: "Moonshot AI",
    description: "Moonshot AI / Kimi 官方 OpenAI 兼容接口。",
    endpoint: "https://api.moonshot.cn/v1/chat/completions",
    defaultModel: "kimi-k2.5",
    models: [
      { id: "kimi-k2.5", label: "Kimi K2.5" },
      { id: "moonshot-v1-32k", label: "Moonshot V1 32K" },
    ],
  },
  zhipu: {
    id: "zhipu",
    label: "Zhipu AI",
    description: "智谱 BigModel GLM OpenAI 兼容接口。",
    endpoint: "https://open.bigmodel.cn/api/paas/v4/chat/completions",
    defaultModel: "glm-4.5",
    models: [
      { id: "glm-4.5", label: "GLM-4.5" },
      { id: "glm-4.5-air", label: "GLM-4.5 Air" },
    ],
  },
  siliconflow: {
    id: "siliconflow",
    label: "SiliconFlow",
    description: "SiliconFlow 多模型 OpenAI 兼容接口。",
    endpoint: "https://api.siliconflow.cn/v1/chat/completions",
    defaultModel: "deepseek-ai/DeepSeek-V3.2",
    models: [
      { id: "deepseek-ai/DeepSeek-V3.2", label: "DeepSeek V3.2" },
      { id: "Qwen/Qwen3-32B", label: "Qwen3 32B" },
    ],
  },
};

const MODEL_RE = /^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,159}$/;

export class ProviderError extends Error {
  constructor(
    public readonly detail: string,
    public readonly status = 502,
  ) {
    super(detail);
    this.name = "ProviderError";
  }
}

export function publicProviderCatalog(): PublicProvider[] {
  return Object.values(PROVIDERS).map((provider) => ({
    id: provider.id,
    label: provider.label,
    description: provider.description,
    default_model: provider.defaultModel,
    models: provider.models.map((model) => ({ ...model })),
    model_editable: true,
  }));
}

export function getProvider(providerId: string): Provider {
  const normalized = providerId.trim().toLowerCase();
  const provider = PROVIDERS[normalized];
  if (!provider) {
    throw new ProviderError(`未知模型服务商。可选：${Object.keys(PROVIDERS).join("、")}。`, 400);
  }
  return provider;
}

export function validateModelId(model: string): string {
  const value = model.trim();
  if (value !== model || !MODEL_RE.test(value)) {
    throw new ProviderError("模型 ID 格式无效。", 400);
  }
  return value;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function safeUpstreamMessage(payload: unknown, apiKey: string): string | null {
  if (!isRecord(payload)) return null;
  const error = payload.error;
  const message = isRecord(error) ? error.message : error;
  if (typeof message !== "string") return null;
  const cleaned = message.split(apiKey).join("[redacted]").replace(/\s+/g, " ").trim();
  return cleaned.length > 0 && cleaned.length <= 300 ? cleaned : null;
}

function providerHttpError(
  provider: Provider,
  status: number,
  payload: unknown,
  apiKey: string,
): ProviderError {
  if (status === 401 || status === 403) {
    return new ProviderError(`${provider.label} 拒绝了请求；请检查 API 密钥和模型权限。`, 401);
  }
  if (status === 429) {
    return new ProviderError(`${provider.label} 返回限流或额度不足。`, 429);
  }
  if (status >= 500) {
    return new ProviderError(`${provider.label} 服务暂时不可用（HTTP ${status}）。`, 502);
  }
  const upstream = safeUpstreamMessage(payload, apiKey);
  const suffix = upstream ? `：${upstream}` : "。";
  return new ProviderError(`${provider.label} 拒绝了请求（HTTP ${status}）${suffix}`, 502);
}

function messageContent(payload: unknown): string {
  if (!isRecord(payload) || !Array.isArray(payload.choices) || payload.choices.length === 0) {
    throw new ProviderError("模型服务商响应缺少 choices。");
  }
  const firstChoice = payload.choices[0];
  if (!isRecord(firstChoice) || !isRecord(firstChoice.message)) {
    throw new ProviderError("模型服务商响应缺少 message。");
  }
  const content = firstChoice.message.content;
  let result = "";
  if (typeof content === "string") {
    result = content.trim();
  } else if (Array.isArray(content)) {
    result = content
      .filter(isRecord)
      .map((item) => item.text)
      .filter((text): text is string => typeof text === "string")
      .join("\n")
      .trim();
  }
  if (!result) {
    throw new ProviderError("模型服务商未返回可用文本。");
  }
  return result;
}

async function readBoundedResponse(response: Response, provider: Provider): Promise<Uint8Array> {
  const declaredLength = response.headers.get("content-length");
  if (declaredLength !== null && /^\d+$/.test(declaredLength)) {
    const length = Number(declaredLength);
    if (Number.isSafeInteger(length) && length > MAX_PROVIDER_RESPONSE_BYTES) {
      throw new ProviderError(`${provider.label} 响应超过大小限制。`);
    }
  }

  if (!response.body) return new Uint8Array();
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    total += value.byteLength;
    if (total > MAX_PROVIDER_RESPONSE_BYTES) {
      await reader.cancel().catch(() => undefined);
      throw new ProviderError(`${provider.label} 响应超过大小限制。`);
    }
    chunks.push(value);
  }

  const combined = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    combined.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return combined;
}

function parseJson(bytes: Uint8Array, provider: Provider): unknown {
  try {
    const text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
    return JSON.parse(text) as unknown;
  } catch {
    throw new ProviderError(`${provider.label} 返回的不是有效 JSON。`);
  }
}

function tryParseJson(bytes: Uint8Array): unknown {
  try {
    const text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
    return JSON.parse(text) as unknown;
  } catch {
    return null;
  }
}

export async function chatCompletion(options: {
  providerId: string;
  apiKey: string;
  model: string;
  messages: ReadonlyArray<ChatMessage>;
  fetchImpl?: typeof fetch;
}): Promise<string> {
  const provider = getProvider(options.providerId);
  const model = validateModelId(options.model);
  const fetchImpl = options.fetchImpl ?? fetch;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 50_000);

  try {
    const response = await fetchImpl(provider.endpoint, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${options.apiKey}`,
        "Content-Type": "application/json",
        Accept: "application/json",
        "User-Agent": "VibioSEO-Web/1.0",
      },
      body: JSON.stringify({
        model,
        messages: options.messages.map((message) => ({ ...message })),
        stream: false,
        max_tokens: 4096,
      }),
      redirect: "manual",
      signal: controller.signal,
    });
    const responseBytes = await readBoundedResponse(response, provider);
    if (!response.ok) {
      throw providerHttpError(provider, response.status, tryParseJson(responseBytes), options.apiKey);
    }
    return messageContent(parseJson(responseBytes, provider));
  } catch (error) {
    if (error instanceof ProviderError) throw error;
    if (controller.signal.aborted) throw new ProviderError(`${provider.label} 请求超时。`, 504);
    throw new ProviderError(`无法连接 ${provider.label} 服务。`, 502);
  } finally {
    clearTimeout(timeout);
  }
}
