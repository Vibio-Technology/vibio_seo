import { createHash } from "node:crypto";
import { lookup as systemLookup } from "node:dns/promises";
import { request as httpRequest, type IncomingHttpHeaders } from "node:http";
import { request as httpsRequest } from "node:https";
import { isIP, type LookupFunction } from "node:net";

import { load } from "cheerio";
import { XMLParser } from "fast-xml-parser";

const USER_AGENT = "VibioSEOInspect/2.0 (+bounded source audit)";
const RESPONSE_LIMIT_BYTES = 2 * 1024 * 1024;
const REQUEST_TIMEOUT_MS = 8_000;
const AUDIT_TIMEOUT_MS = 50_000;
const MAX_REDIRECTS = 5;
const MAX_SITEMAPS = 3;
const MAX_SITEMAP_URLS = 1_000;
const MAX_REPORTED_URLS = 20;
const MAX_PAGE_LINKS = 250;
const MAX_PAGE_IMAGES = 200;
const MAX_TEXT_EVIDENCE = 500;
const TRACKING_PARAMETERS = new Set(["gclid", "dclid", "fbclid", "msclkid", "yclid", "_gl"]);
const SAFE_RESPONSE_HEADERS = new Set([
  "cache-control",
  "content-language",
  "content-length",
  "content-encoding",
  "content-type",
  "link",
  "location",
  "x-robots-tag",
]);

export type Severity = "critical" | "high" | "medium" | "low" | "info";
export type Confidence = "high" | "medium" | "low";

export interface SeoInspectInput {
  url: string;
  max_pages?: number;
  production?: boolean;
}

export interface DnsAddress {
  address: string;
  family: 4 | 6;
}

export type DnsResolver = (hostname: string) => Promise<readonly DnsAddress[]>;

export interface ResolvedTarget {
  url: URL;
  hostname: string;
  origin: string;
  addresses: DnsAddress[];
}

export interface HeadingEvidence {
  level: number;
  text: string;
}

export interface HreflangEvidence {
  lang: string;
  url: string;
}

export interface LinkEvidence {
  source: string;
  target: string;
  anchor: string;
  rel: string[];
}

export interface ImageEvidence {
  src: string;
  alt_present: boolean;
  alt: string;
  width_present: boolean;
  height_present: boolean;
  loading: string;
}

export interface ImageResourceEvidence {
  element: "img" | "source";
  attribute: string;
  raw: string;
  url: string;
}

export interface ParsedHtmlDocument {
  document_base_url: string;
  html_sha256: string;
  visible_text_sha256: string;
  visible_text_length: number;
  titles: string[];
  descriptions: string[];
  canonicals: string[];
  robots: string[];
  hreflang: HreflangEvidence[];
  headings: HeadingEvidence[];
  internal_links: string[];
  external_links: string[];
  link_edges: LinkEvidence[];
  images: ImageEvidence[];
  image_resources: ImageResourceEvidence[];
  json_ld_types: string[];
  json_ld_errors: string[];
  html_lang: string;
  h1_count: number;
  main_count: number;
  anchor_count: number;
  anchors_without_href: string[];
  non_anchor_link_controls: string[];
  noindex: boolean;
}

export interface InspectFinding {
  code: string;
  severity: Severity;
  category: string;
  observation: string;
  urls: string[];
  evidence: string[];
  impact_boundary: string;
  verification: string;
  confidence: Confidence;
}

export interface InspectPage extends ParsedHtmlDocument {
  url: string;
  source: string;
  evidence_mode: "http_source";
  requested_url: string;
  status: number;
  final_url: string;
  content_type: string;
  response_headers: Record<string, string[]>;
  redirect_chain: Array<{ url: string; status: number; location: string }>;
  depth: number | null;
  inbound_links_in_scope: number;
  is_html: boolean;
}

export interface InspectReport {
  schema_version: "1.3";
  analysis_kind: "bounded_seo_artifact_inspection";
  tool: "vibio-seo-inspect";
  version: string;
  generated_at: string;
  scope: Record<string, unknown>;
  summary: Record<string, unknown>;
  limitations: string[];
  findings: InspectFinding[];
  pages: InspectPage[];
  rendering_comparison: null;
  robots: Record<string, unknown> | null;
  sitemap: Record<string, unknown>;
}

export class SeoInspectError extends Error {
  readonly status: number;

  constructor(message: string, status = 400) {
    super(message);
    this.name = "SeoInspectError";
    this.status = status;
  }
}

class NetworkInspectError extends SeoInspectError {
  constructor(message = "无法读取目标站点的公开 HTTP 源码。") {
    super(message, 502);
    this.name = "NetworkInspectError";
  }
}

class ResponseLimitError extends NetworkInspectError {
  constructor() {
    super("目标站点响应超过 2 MiB 的单次读取上限。");
    this.name = "ResponseLimitError";
  }
}

interface RawResponse {
  status: number;
  headers: Record<string, string[]>;
  body: Buffer;
}

interface FetchResult extends RawResponse {
  requestedUrl: string;
  finalUrl: string;
  redirectChain: Array<{ url: string; status: number; location: string }>;
  requests: number;
}

interface RobotsRule {
  allow: boolean;
  pattern: string;
}

interface RobotsGroup {
  agents: string[];
  rules: RobotsRule[];
}

interface RobotsDocument {
  source: string;
  status: number;
  groups: RobotsGroup[];
  sitemaps: string[];
  raw_sha256: string;
}

interface SitemapParseResult {
  pageUrls: string[];
  sitemapUrls: string[];
}

interface CrawlQueueItem {
  url: string;
  depth: number | null;
}

const defaultResolver: DnsResolver = async (hostname) => {
  const addresses = await systemLookup(hostname, { all: true, verbatim: true });
  return addresses
    .filter((item): item is { address: string; family: 4 | 6 } => item.family === 4 || item.family === 6)
    .map((item) => ({ address: item.address, family: item.family }));
};

async function resolveWithTimeout(hostname: string, resolver: DnsResolver): Promise<readonly DnsAddress[]> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new NetworkInspectError("DNS 解析超过 8 秒。")), REQUEST_TIMEOUT_MS);
    resolver(hostname).then(
      (addresses) => {
        clearTimeout(timer);
        resolve(addresses);
      },
      () => {
        clearTimeout(timer);
        reject(new NetworkInspectError("无法解析目标站点的 DNS 地址。"));
      },
    );
  });
}

function normalizeSpace(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

function sha256(value: string | Buffer): string {
  return createHash("sha256").update(value).digest("hex");
}

function stripIpv6Brackets(hostname: string): string {
  return hostname.startsWith("[") && hostname.endsWith("]") ? hostname.slice(1, -1) : hostname;
}

function effectivePort(url: URL): string {
  if (url.port) return url.port;
  return url.protocol === "https:" ? "443" : "80";
}

export function originKey(url: URL): string {
  return `${url.protocol}//${stripIpv6Brackets(url.hostname).toLowerCase().replace(/\.$/, "")}:${effectivePort(url)}`;
}

export function validateAuditUrl(raw: string): URL {
  if (typeof raw !== "string" || raw.length < 8 || raw.length > 2_048 || raw !== raw.trim()) {
    throw new SeoInspectError("URL 必须是 8 到 2048 个字符的 HTTP(S) 地址。");
  }
  if ([...raw].some((character) => {
    const code = character.charCodeAt(0);
    return code < 32 || code === 127;
  })) {
    throw new SeoInspectError("URL 包含不允许的控制字符。");
  }

  let url: URL;
  try {
    url = new URL(raw);
  } catch {
    throw new SeoInspectError("URL 格式无效。");
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new SeoInspectError("URL 必须使用 HTTP 或 HTTPS。");
  }
  if (!url.hostname) throw new SeoInspectError("URL 必须包含主机名。");
  if (url.username || url.password) throw new SeoInspectError("URL 不得包含用户名或密码。");
  const expectedPort = url.protocol === "https:" ? "443" : "80";
  if (url.port && url.port !== expectedPort) {
    throw new SeoInspectError("URL 审计只允许标准 HTTP 80 或 HTTPS 443 端口。");
  }
  const hostname = stripIpv6Brackets(url.hostname).toLowerCase().replace(/\.$/, "");
  if (hostname === "localhost" || hostname.endsWith(".localhost")) {
    throw new SeoInspectError("不允许审计本机或私有网络地址。");
  }
  url.hash = "";
  return url;
}

function parseIpv4(address: string): number[] | null {
  const parts = address.split(".");
  if (parts.length !== 4) return null;
  const octets = parts.map((part) => Number(part));
  if (octets.some((part, index) => !/^\d{1,3}$/.test(parts[index]) || !Number.isInteger(part) || part < 0 || part > 255)) {
    return null;
  }
  return octets;
}

function ipv6ToBigInt(address: string): bigint | null {
  const zoneIndex = address.indexOf("%");
  if (zoneIndex !== -1) return null;
  let normalized = address.toLowerCase();
  if (normalized.includes(".")) {
    const lastColon = normalized.lastIndexOf(":");
    if (lastColon === -1) return null;
    const ipv4 = parseIpv4(normalized.slice(lastColon + 1));
    if (!ipv4) return null;
    const high = ((ipv4[0] << 8) | ipv4[1]).toString(16);
    const low = ((ipv4[2] << 8) | ipv4[3]).toString(16);
    normalized = `${normalized.slice(0, lastColon)}:${high}:${low}`;
  }
  if ((normalized.match(/::/g) ?? []).length > 1) return null;
  const [leftRaw, rightRaw] = normalized.split("::");
  const left = leftRaw ? leftRaw.split(":") : [];
  const right = rightRaw ? rightRaw.split(":") : [];
  const missing = 8 - left.length - right.length;
  if ((normalized.includes("::") && missing < 1) || (!normalized.includes("::") && missing !== 0)) return null;
  const groups = normalized.includes("::") ? [...left, ...Array(missing).fill("0"), ...right] : left;
  if (groups.length !== 8 || groups.some((group) => !/^[0-9a-f]{1,4}$/.test(group))) return null;
  return groups.reduce((value, group) => (value << 16n) + BigInt(`0x${group}`), 0n);
}

function ipv6InPrefix(value: bigint, prefix: bigint, bits: number): boolean {
  const shift = BigInt(128 - bits);
  return value >> shift === prefix >> shift;
}

export function isPublicIpAddress(address: string): boolean {
  const family = isIP(address);
  if (family === 4) {
    const octets = parseIpv4(address);
    if (!octets) return false;
    const [a, b, c] = octets;
    if (a === 0 || a === 10 || a === 127 || a >= 224) return false;
    if (a === 100 && b >= 64 && b <= 127) return false;
    if (a === 169 && b === 254) return false;
    if (a === 172 && b >= 16 && b <= 31) return false;
    if (a === 192 && b === 0 && c === 0) return false;
    if (a === 192 && b === 0 && c === 2) return false;
    if (a === 192 && b === 88 && c === 99) return false;
    if (a === 192 && b === 168) return false;
    if (a === 198 && (b === 18 || b === 19)) return false;
    if (a === 198 && b === 51 && c === 100) return false;
    if (a === 203 && b === 0 && c === 113) return false;
    return true;
  }
  if (family === 6) {
    const value = ipv6ToBigInt(address);
    if (value === null) return false;
    const globalStart = 0x20000000000000000000000000000000n;
    if (!ipv6InPrefix(value, globalStart, 3)) return false;
    if (ipv6InPrefix(value, 0x20010000000000000000000000000000n, 23)) return false;
    if (ipv6InPrefix(value, 0x20010db8000000000000000000000000n, 32)) return false;
    if (ipv6InPrefix(value, 0x3fff0000000000000000000000000000n, 20)) return false;
    return true;
  }
  return false;
}

export function assertPublicAddressSet(hostname: string, addresses: readonly DnsAddress[]): DnsAddress[] {
  if (!addresses.length) throw new NetworkInspectError("目标主机没有可用的 DNS 地址。");
  const normalized = addresses.map((item) => ({ address: item.address, family: item.family }));
  const hasInvalid = normalized.some(
    (item) => (item.family !== 4 && item.family !== 6) || isIP(item.address) !== item.family || !isPublicIpAddress(item.address),
  );
  if (hasInvalid) {
    throw new SeoInspectError(`目标主机 ${hostname} 的 DNS 结果包含非公网地址，已拒绝请求。`);
  }
  return normalized.filter(
    (item, index, values) => values.findIndex((candidate) => candidate.address === item.address && candidate.family === item.family) === index,
  );
}

export async function resolvePublicTarget(
  raw: string | URL,
  allowedOrigin?: string,
  resolver: DnsResolver = defaultResolver,
): Promise<ResolvedTarget> {
  const url = validateAuditUrl(raw instanceof URL ? raw.toString() : raw);
  const targetOrigin = originKey(url);
  if (allowedOrigin && targetOrigin !== allowedOrigin) {
    throw new SeoInspectError("抓取目标必须与起始 URL 同源。");
  }
  const hostname = stripIpv6Brackets(url.hostname).toLowerCase().replace(/\.$/, "");
  let addresses: readonly DnsAddress[];
  const literalFamily = isIP(hostname);
  if (literalFamily === 4 || literalFamily === 6) {
    addresses = [{ address: hostname, family: literalFamily }];
  } else {
    addresses = await resolveWithTimeout(hostname, resolver);
  }
  return {
    url,
    hostname,
    origin: targetOrigin,
    addresses: assertPublicAddressSet(hostname, addresses),
  };
}

export function createPinnedLookup(expectedHostname: string, pinned: DnsAddress): LookupFunction {
  return (hostname, options, callback) => {
    const actual = stripIpv6Brackets(hostname).toLowerCase().replace(/\.$/, "");
    if (actual !== expectedHostname) {
      const error = new Error("Pinned DNS hostname mismatch") as NodeJS.ErrnoException;
      error.code = "EPERM";
      if (options.all) {
        callback(error, []);
      } else {
        callback(error, "", 0);
      }
      return;
    }
    if (options.all) {
      callback(null, [{ address: pinned.address, family: pinned.family }]);
    } else {
      callback(null, pinned.address, pinned.family);
    }
  };
}

function normalizeHeaders(headers: IncomingHttpHeaders): Record<string, string[]> {
  const normalized: Record<string, string[]> = {};
  for (const [rawName, rawValue] of Object.entries(headers)) {
    const name = rawName.toLowerCase();
    if (!SAFE_RESPONSE_HEADERS.has(name) || rawValue === undefined) continue;
    normalized[name] = (Array.isArray(rawValue) ? rawValue : [rawValue]).map(String);
  }
  return normalized;
}

function firstHeader(headers: Record<string, string[]>, name: string): string {
  return headers[name.toLowerCase()]?.[0] ?? "";
}

function isRedirect(status: number): boolean {
  return status === 301 || status === 302 || status === 303 || status === 307 || status === 308;
}

async function requestPinned(target: ResolvedTarget, pinned: DnsAddress, timeoutMs: number): Promise<RawResponse> {
  const requester = target.url.protocol === "https:" ? httpsRequest : httpRequest;
  return new Promise((resolve, reject) => {
    let settled = false;
    const finish = (callback: () => void) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      callback();
    };
    const req = requester(
      target.url,
      {
        method: "GET",
        headers: {
          accept: "text/html,application/xhtml+xml,application/xml,text/xml,text/plain;q=0.8,*/*;q=0.1",
          "accept-encoding": "identity",
          "user-agent": USER_AGENT,
        },
        lookup: createPinnedLookup(target.hostname, pinned),
        servername: target.url.protocol === "https:" ? target.hostname : undefined,
      },
      (response) => {
        const status = response.statusCode ?? 0;
        const headers = normalizeHeaders(response.headers);
        if (isRedirect(status) && firstHeader(headers, "location")) {
          response.destroy();
          finish(() => resolve({ status, headers, body: Buffer.alloc(0) }));
          return;
        }
        const declaredLength = Number(firstHeader(headers, "content-length"));
        if (Number.isFinite(declaredLength) && declaredLength > RESPONSE_LIMIT_BYTES) {
          response.destroy();
          finish(() => reject(new ResponseLimitError()));
          return;
        }
        const encoding = firstHeader(headers, "content-encoding").toLowerCase();
        if (encoding && encoding !== "identity") {
          response.destroy();
          finish(() => reject(new NetworkInspectError("目标站点忽略 identity 请求并返回了压缩响应。")));
          return;
        }
        const chunks: Buffer[] = [];
        let bytes = 0;
        response.on("data", (chunk: Buffer | string) => {
          const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
          bytes += buffer.length;
          if (bytes > RESPONSE_LIMIT_BYTES) {
            response.destroy();
            finish(() => reject(new ResponseLimitError()));
            return;
          }
          chunks.push(buffer);
        });
        response.on("end", () => finish(() => resolve({ status, headers, body: Buffer.concat(chunks, bytes) })));
        response.on("error", () => finish(() => reject(new NetworkInspectError())));
      },
    );
    const timer = setTimeout(() => req.destroy(new NetworkInspectError("读取目标站点超过 8 秒。")), timeoutMs);
    req.on("error", (error) => finish(() => reject(error instanceof SeoInspectError ? error : new NetworkInspectError())));
    req.end();
  });
}

async function requestResolvedTarget(target: ResolvedTarget, deadline: number): Promise<RawResponse> {
  let lastError: unknown;
  const requestDeadline = Math.min(deadline, Date.now() + REQUEST_TIMEOUT_MS);
  for (const address of target.addresses) {
    const remaining = requestDeadline - Date.now();
    if (remaining <= 0) throw new NetworkInspectError("站点审计超过总时间上限。");
    try {
      return await requestPinned(target, address, remaining);
    } catch (error) {
      if (error instanceof ResponseLimitError) throw error;
      lastError = error;
    }
  }
  throw lastError instanceof SeoInspectError ? lastError : new NetworkInspectError();
}

async function fetchWithRedirects(raw: string, allowedOrigin: string, deadline: number): Promise<FetchResult> {
  const requestedUrl = canonicalizeUrl(validateAuditUrl(raw)).toString();
  let current = requestedUrl;
  const redirectChain: Array<{ url: string; status: number; location: string }> = [];
  let requests = 0;
  for (let redirect = 0; redirect <= MAX_REDIRECTS; redirect += 1) {
    const target = await resolvePublicTarget(current, allowedOrigin);
    const response = await requestResolvedTarget(target, deadline);
    requests += 1;
    const location = firstHeader(response.headers, "location");
    if (!isRedirect(response.status) || !location) {
      return {
        ...response,
        requestedUrl,
        finalUrl: canonicalizeUrl(target.url).toString(),
        redirectChain,
        requests,
      };
    }
    if (redirect === MAX_REDIRECTS) throw new NetworkInspectError("目标站点重定向次数超过上限。");
    let next: URL;
    try {
      next = validateAuditUrl(new URL(location, target.url).toString());
    } catch {
      throw new NetworkInspectError("目标站点返回了不安全的重定向地址。");
    }
    if (originKey(next) !== allowedOrigin) throw new NetworkInspectError("目标站点重定向到了不同源地址，已停止抓取。");
    const normalizedNext = canonicalizeUrl(next).toString();
    redirectChain.push({ url: current, status: response.status, location: normalizedNext });
    current = normalizedNext;
  }
  throw new NetworkInspectError("目标站点重定向次数超过上限。");
}

export function canonicalizeUrl(input: URL | string): URL {
  const url = input instanceof URL ? new URL(input.toString()) : new URL(input);
  url.hash = "";
  for (const key of [...url.searchParams.keys()]) {
    const lowered = key.toLowerCase();
    if (lowered.startsWith("utm_") || TRACKING_PARAMETERS.has(lowered)) url.searchParams.delete(key);
  }
  return url;
}

function resolveDocumentUrl(raw: string, base: URL): URL | null {
  const value = raw.trim();
  if (!value || value.startsWith("#")) return null;
  try {
    const resolved = new URL(value, base);
    if (resolved.protocol !== "http:" && resolved.protocol !== "https:") return null;
    if (resolved.username || resolved.password || resolved.toString().length > 2_048) return null;
    return canonicalizeUrl(resolved);
  } catch {
    return null;
  }
}

function directiveTokens(values: readonly string[]): string[] {
  const tokens = new Set<string>();
  for (const value of values) {
    let scope: string | null = null;
    for (const rawItem of value.toLowerCase().split(/[,;]/)) {
      let item = rawItem.trim();
      if (!item) continue;
      const scoped = item.match(/^([a-z0-9_-]+)\s*:\s*(.+)$/);
      if (scoped && !new Set(["max-image-preview", "max-snippet", "max-video-preview", "unavailable_after"]).has(scoped[1])) {
        scope = scoped[1];
        item = scoped[2].trim();
      }
      const token = item.split(":", 1)[0].trim();
      if (token && (scope === null || scope === "googlebot")) {
        tokens.add(token);
        if (token === "none") {
          tokens.add("noindex");
          tokens.add("nofollow");
        }
      }
    }
  }
  return [...tokens].sort();
}

function collectJsonLdTypes(value: unknown, output: Set<string>): void {
  if (Array.isArray(value)) {
    value.forEach((item) => collectJsonLdTypes(item, output));
    return;
  }
  if (!value || typeof value !== "object") return;
  const record = value as Record<string, unknown>;
  const type = record["@type"];
  if (typeof type === "string") output.add(type);
  if (Array.isArray(type)) type.filter((item): item is string => typeof item === "string").forEach((item) => output.add(item));
  Object.entries(record).forEach(([key, item]) => {
    if (key !== "@type") collectJsonLdTypes(item, output);
  });
}

function parseSrcset(value: string): string[] {
  return value
    .split(/,(?=\s*[^\s,]+(?:\s|$))/)
    .map((candidate) => candidate.trim().split(/\s+/, 1)[0])
    .filter(Boolean);
}

export function parseHtmlDocument(
  html: string,
  documentUrl: string,
  responseHeaders: Record<string, string[]> = {},
): ParsedHtmlDocument {
  const sourceUrl = validateAuditUrl(documentUrl);
  const sourceOrigin = originKey(sourceUrl);
  const $ = load(html);
  let baseUrl = sourceUrl;
  const rawBase = $("base[href]").first().attr("href");
  if (rawBase) baseUrl = resolveDocumentUrl(rawBase, sourceUrl) ?? sourceUrl;

  const titles = $("title")
    .map((_index, element) => normalizeSpace($(element).text()).slice(0, MAX_TEXT_EVIDENCE))
    .get()
    .filter(Boolean)
    .slice(0, 10);
  const descriptions = $("meta[name]")
    .filter((_index, element) => ($(element).attr("name") ?? "").trim().toLowerCase() === "description")
    .map((_index, element) => normalizeSpace($(element).attr("content") ?? "").slice(0, MAX_TEXT_EVIDENCE))
    .get()
    .filter(Boolean)
    .slice(0, 10);
  const metaRobotValues = $("meta[name]")
    .filter((_index, element) => ["robots", "googlebot"].includes(($(element).attr("name") ?? "").trim().toLowerCase()))
    .map((_index, element) => $(element).attr("content") ?? "")
    .get();
  const robots = directiveTokens([...metaRobotValues, ...(responseHeaders["x-robots-tag"] ?? [])]);

  const canonicals = $("link[href]")
    .filter((_index, element) => ($(element).attr("rel") ?? "").toLowerCase().split(/\s+/).includes("canonical"))
    .map((_index, element) => resolveDocumentUrl($(element).attr("href") ?? "", baseUrl)?.toString() ?? "")
    .get()
    .filter(Boolean)
    .slice(0, 10);
  const hreflang: HreflangEvidence[] = [];
  $("link[href][hreflang]").each((_index, element) => {
    const rel = ($(element).attr("rel") ?? "").toLowerCase().split(/\s+/);
    const lang = ($(element).attr("hreflang") ?? "").trim();
    const url = resolveDocumentUrl($(element).attr("href") ?? "", baseUrl);
    if (rel.includes("alternate") && lang && url && hreflang.length < 100) {
      hreflang.push({ lang: lang.slice(0, 100), url: url.toString() });
    }
  });

  const headings: HeadingEvidence[] = $("h1,h2,h3,h4,h5,h6")
    .map((_index, element) => ({
      level: Number(element.tagName.slice(1)),
      text: normalizeSpace($(element).text()).slice(0, MAX_TEXT_EVIDENCE),
    }))
    .get()
    .slice(0, 200);

  const internal = new Set<string>();
  const external = new Set<string>();
  const linkEdges: LinkEvidence[] = [];
  const anchorsWithoutHref: string[] = [];
  $("a").each((_index, element) => {
    const href = $(element).attr("href");
    const anchor = normalizeSpace($(element).text()).slice(0, 300);
    if (href === undefined || !href.trim()) {
      if (anchor && anchorsWithoutHref.length < 100) anchorsWithoutHref.push(anchor);
      return;
    }
    const target = resolveDocumentUrl(href, baseUrl);
    if (!target) return;
    const rel = ($(element).attr("rel") ?? "")
      .toLowerCase()
      .split(/\s+/)
      .filter(Boolean);
    const normalized = target.toString();
    if (originKey(target) === sourceOrigin) {
      if (internal.size < MAX_PAGE_LINKS) internal.add(normalized);
    } else if (external.size < MAX_PAGE_LINKS) {
      external.add(normalized);
    }
    if (linkEdges.length < MAX_PAGE_LINKS) {
      linkEdges.push({ source: canonicalizeUrl(sourceUrl).toString(), target: normalized, anchor, rel: rel.slice(0, 20) });
    }
  });

  const images: ImageEvidence[] = [];
  const imageResources: ImageResourceEvidence[] = [];
  const imageAttributes = ["src", "data-src", "data-lazy-src", "data-original", "data-flickity-lazyload", "data-echo"];
  const srcsetAttributes = ["srcset", "data-srcset", "data-lazy-srcset", "data-original-srcset"];
  $("img").each((_index, element) => {
    if (images.length >= MAX_PAGE_IMAGES) return;
    const alt = $(element).attr("alt");
    const primaryRaw = imageAttributes.map((attribute) => $(element).attr(attribute)).find(Boolean) ?? "";
    const primary = resolveDocumentUrl(primaryRaw, baseUrl);
    images.push({
      src: primary?.toString() ?? primaryRaw,
      alt_present: alt !== undefined,
      alt: (alt ?? "").slice(0, MAX_TEXT_EVIDENCE),
      width_present: $(element).attr("width") !== undefined,
      height_present: $(element).attr("height") !== undefined,
      loading: ($(element).attr("loading") ?? "").trim().toLowerCase(),
    });
  });
  $("img,source").each((_index, element) => {
    if (imageResources.length >= MAX_PAGE_IMAGES * 2) return;
    const elementName = element.tagName === "source" ? "source" : "img";
    for (const attribute of imageAttributes) {
      if (elementName === "source" && attribute !== "src") continue;
      const raw = $(element).attr(attribute);
      const url = raw ? resolveDocumentUrl(raw, baseUrl) : null;
      if (raw && url && imageResources.length < MAX_PAGE_IMAGES * 2) {
        imageResources.push({ element: elementName, attribute, raw: raw.slice(0, 2_048), url: url.toString() });
      }
    }
    for (const attribute of srcsetAttributes) {
      const raw = $(element).attr(attribute);
      if (!raw) continue;
      for (const candidate of parseSrcset(raw)) {
        const url = resolveDocumentUrl(candidate, baseUrl);
        if (url && imageResources.length < MAX_PAGE_IMAGES * 2) {
          imageResources.push({ element: elementName, attribute, raw: candidate, url: url.toString() });
        }
      }
    }
  });

  const jsonLdTypes = new Set<string>();
  const jsonLdErrors: string[] = [];
  $('script[type="application/ld+json" i]').each((index, element) => {
    const value = $(element).text().trim();
    if (!value) return;
    try {
      collectJsonLdTypes(JSON.parse(value), jsonLdTypes);
    } catch {
      if (jsonLdErrors.length < 20) jsonLdErrors.push(`JSON-LD script ${index + 1} is not valid JSON`);
    }
  });

  const body = $("body").clone();
  body.find("script,style,noscript,template").remove();
  const visibleText = normalizeSpace(body.text());
  const nonAnchorLinkControls = $('[role="link"]')
    .filter((_index, element) => element.tagName !== "a")
    .map((_index, element) => element.tagName)
    .get();

  return {
    document_base_url: canonicalizeUrl(baseUrl).toString(),
    html_sha256: sha256(html),
    visible_text_sha256: sha256(visibleText),
    visible_text_length: visibleText.length,
    titles,
    descriptions,
    canonicals: [...new Set(canonicals)],
    robots,
    hreflang,
    headings,
    internal_links: [...internal].sort(),
    external_links: [...external].sort(),
    link_edges: linkEdges,
    images,
    image_resources: imageResources,
    json_ld_types: [...jsonLdTypes].map((value) => value.slice(0, 200)).sort().slice(0, 100),
    json_ld_errors: jsonLdErrors,
    html_lang: ($("html").attr("lang") ?? "").trim(),
    h1_count: headings.filter((heading) => heading.level === 1).length,
    main_count: $("main").length,
    anchor_count: $("a").length,
    anchors_without_href: anchorsWithoutHref,
    non_anchor_link_controls: nonAnchorLinkControls,
    noindex: robots.includes("noindex"),
  };
}

export function parseRobotsDocument(text: string, source: string, status = 200): RobotsDocument {
  const groups: RobotsGroup[] = [];
  const sitemaps: string[] = [];
  let current: RobotsGroup | null = null;
  let hasRules = false;
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.replace(/#.*$/, "").trim();
    if (!line) continue;
    const separator = line.indexOf(":");
    if (separator === -1) continue;
    const field = line.slice(0, separator).trim().toLowerCase();
    const value = line.slice(separator + 1).trim();
    if (field === "sitemap" && value) {
      if (sitemaps.length < 20) sitemaps.push(value);
      continue;
    }
    if (field === "user-agent") {
      if (!current || hasRules) {
        current = { agents: [], rules: [] };
        groups.push(current);
        hasRules = false;
      }
      if (value) current.agents.push(value.toLowerCase());
      continue;
    }
    if ((field === "allow" || field === "disallow") && current) {
      hasRules = true;
      if (value && value.length <= 2_048 && (value.match(/\*/g) ?? []).length <= 32 && current.rules.length < 5_000) {
        current.rules.push({ allow: field === "allow", pattern: value });
      }
    }
  }
  return { source, status, groups, sitemaps, raw_sha256: sha256(text) };
}

function robotsRuleMatches(pattern: string, path: string): boolean {
  const anchored = pattern.endsWith("$");
  const source = (anchored ? pattern.slice(0, -1) : pattern)
    .split("*")
    .map((part) => part.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
    .join(".*");
  try {
    return new RegExp(`^${source}${anchored ? "$" : ""}`).test(path);
  } catch {
    return false;
  }
}

export function isAllowedByRobots(url: URL, robots: RobotsDocument | null): boolean {
  if (!robots) return true;
  const productToken = "vibioseoinspect";
  const candidates = robots.groups
    .map((group) => ({
      group,
      specificity: Math.max(
        ...group.agents.map((agent) => {
          const token = agent.replace(/[^a-z0-9_-]/g, "");
          return agent === "*" ? 0 : token && productToken.startsWith(token) ? token.length : -1;
        }),
        -1,
      ),
    }))
    .filter((item) => item.specificity >= 0);
  if (!candidates.length) return true;
  const bestSpecificity = Math.max(...candidates.map((item) => item.specificity));
  const rules = candidates.filter((item) => item.specificity === bestSpecificity).flatMap((item) => item.group.rules);
  const path = `${url.pathname}${url.search}`;
  const matches = rules.filter((rule) => robotsRuleMatches(rule.pattern, path));
  if (!matches.length) return true;
  const longest = Math.max(...matches.map((rule) => rule.pattern.replace(/\$$/, "").length));
  return matches.some((rule) => rule.allow && rule.pattern.replace(/\$$/, "").length === longest);
}

export function parseSitemapXml(xml: string): SitemapParseResult {
  if (/<!\s*(?:DOCTYPE|ENTITY)\b/i.test(xml)) return { pageUrls: [], sitemapUrls: [] };
  let document: unknown;
  try {
    document = new XMLParser({ ignoreAttributes: true, removeNSPrefix: true, trimValues: true, parseTagValue: false }).parse(xml);
  } catch {
    return { pageUrls: [], sitemapUrls: [] };
  }
  const record = document && typeof document === "object" ? (document as Record<string, unknown>) : {};
  const asArray = (value: unknown): unknown[] => (Array.isArray(value) ? value : value === undefined ? [] : [value]);
  const locValues = (value: unknown): string[] =>
    asArray(value)
      .map((item) => (item && typeof item === "object" ? (item as Record<string, unknown>).loc : undefined))
      .filter((item): item is string => typeof item === "string" && item.length > 0);
  const urlset = record.urlset && typeof record.urlset === "object" ? (record.urlset as Record<string, unknown>) : {};
  const sitemapindex =
    record.sitemapindex && typeof record.sitemapindex === "object" ? (record.sitemapindex as Record<string, unknown>) : {};
  return { pageUrls: locValues(urlset.url), sitemapUrls: locValues(sitemapindex.sitemap) };
}

function isHtmlContent(contentType: string, body: Buffer): boolean {
  const mediaType = contentType.split(";", 1)[0].trim().toLowerCase();
  if (mediaType === "text/html" || mediaType === "application/xhtml+xml") return true;
  if (mediaType && mediaType !== "text/plain") return false;
  const prefix = body.subarray(0, 512).toString("utf8").trimStart().toLowerCase();
  return prefix.startsWith("<!doctype html") || prefix.startsWith("<html") || prefix.includes("<head");
}

function emptyParsedDocument(body: Buffer, documentUrl: string): ParsedHtmlDocument {
  const digest = sha256(body);
  return {
    document_base_url: documentUrl,
    html_sha256: digest,
    visible_text_sha256: sha256(""),
    visible_text_length: 0,
    titles: [],
    descriptions: [],
    canonicals: [],
    robots: [],
    hreflang: [],
    headings: [],
    internal_links: [],
    external_links: [],
    link_edges: [],
    images: [],
    image_resources: [],
    json_ld_types: [],
    json_ld_errors: [],
    html_lang: "",
    h1_count: 0,
    main_count: 0,
    anchor_count: 0,
    anchors_without_href: [],
    non_anchor_link_controls: [],
    noindex: false,
  };
}

function addFinding(findings: InspectFinding[], finding: Omit<InspectFinding, "confidence"> & { confidence?: Confidence }): void {
  findings.push({ ...finding, confidence: finding.confidence ?? "high" });
}

function buildFindings(
  pages: InspectPage[],
  startUrl: string,
  production: boolean,
  robots: RobotsDocument | null,
  sitemapUrls: Set<string>,
): InspectFinding[] {
  const findings: InspectFinding[] = [];
  const healthyHtmlPages = pages.filter((page) => page.is_html && page.status >= 200 && page.status < 400);
  const status5xx = pages.filter((page) => page.status >= 500);
  const status4xx = pages.filter((page) => page.status >= 400 && page.status < 500);
  if (status5xx.length) {
    addFinding(findings, {
      code: "http.server-error",
      severity: production ? "critical" : "high",
      category: "http",
      observation: `${status5xx.length} 个已请求 URL 返回 5xx。`,
      urls: status5xx.map((page) => page.url).slice(0, MAX_REPORTED_URLS),
      evidence: status5xx.map((page) => `status=${page.status}`).slice(0, MAX_REPORTED_URLS),
      impact_boundary: "这里只证明本次匿名源码请求收到服务器错误，不证明所有用户或搜索爬虫持续遇到相同响应。",
      verification: "从相同网络位置重试，并核对源站、CDN 和应用日志。",
    });
  }
  if (status4xx.length) {
    addFinding(findings, {
      code: "http.client-error",
      severity: "high",
      category: "http",
      observation: `${status4xx.length} 个已请求 URL 返回 4xx。`,
      urls: status4xx.map((page) => page.url).slice(0, MAX_REPORTED_URLS),
      evidence: status4xx.map((page) => `status=${page.status}`).slice(0, MAX_REPORTED_URLS),
      impact_boundary: "范围仅覆盖本次有界抓取实际请求的 URL。",
      verification: "确认 URL 是否应存在；修复后直接请求并复验站内链接和 sitemap。",
    });
  }

  const noTitle = healthyHtmlPages.filter((page) => page.titles.length === 0);
  if (noTitle.length) {
    addFinding(findings, {
      code: "metadata.title-missing",
      severity: "high",
      category: "metadata",
      observation: `${noTitle.length} 个成功 HTML 响应没有可见的 title 元素。`,
      urls: noTitle.map((page) => page.url).slice(0, MAX_REPORTED_URLS),
      evidence: ["HTTP 源码中 title_count=0"],
      impact_boundary: "未执行 JavaScript；客户端后置生成的 title 不在本证据范围内。",
      verification: "直接查看生产响应源码，确保每个目标页面在初始 HTML 中输出准确 title。",
    });
  }
  const multipleTitles = healthyHtmlPages.filter((page) => page.titles.length > 1);
  if (multipleTitles.length) {
    addFinding(findings, {
      code: "metadata.title-multiple",
      severity: "medium",
      category: "metadata",
      observation: `${multipleTitles.length} 个页面的源码包含多个 title 元素。`,
      urls: multipleTitles.map((page) => page.url).slice(0, MAX_REPORTED_URLS),
      evidence: multipleTitles.map((page) => `title_count=${page.titles.length}`).slice(0, MAX_REPORTED_URLS),
      impact_boundary: "多个元素会造成信号歧义，但本检查不推断搜索引擎最终采用哪一个。",
      verification: "让服务端源码只输出一个与页面意图一致的 title。",
    });
  }
  const missingDescription = healthyHtmlPages.filter((page) => page.descriptions.length === 0);
  if (missingDescription.length) {
    addFinding(findings, {
      code: "metadata.description-missing",
      severity: "low",
      category: "metadata",
      observation: `${missingDescription.length} 个成功 HTML 响应没有 meta description。`,
      urls: missingDescription.map((page) => page.url).slice(0, MAX_REPORTED_URLS),
      evidence: ["HTTP 源码中 description_count=0"],
      impact_boundary: "缺失不等于排名损失，搜索系统也可能改写摘要。",
      verification: "为需要搜索摘要控制的页面提供独特且与正文一致的 description。",
    });
  }
  const missingCanonical = healthyHtmlPages.filter((page) => page.canonicals.length === 0);
  if (missingCanonical.length) {
    addFinding(findings, {
      code: "canonical.missing",
      severity: "medium",
      category: "url-signals",
      observation: `${missingCanonical.length} 个成功 HTML 响应没有 canonical link。`,
      urls: missingCanonical.map((page) => page.url).slice(0, MAX_REPORTED_URLS),
      evidence: ["HTTP 源码中 canonical_count=0"],
      impact_boundary: "canonical 是提示而非指令；缺失本身不证明重复页面已被错误合并。",
      verification: "确认规范 URL 策略，并在初始 HTML、重定向、站内链接与 sitemap 中保持一致。",
    });
  }
  const multipleCanonical = healthyHtmlPages.filter((page) => page.canonicals.length > 1);
  if (multipleCanonical.length) {
    addFinding(findings, {
      code: "canonical.multiple",
      severity: "high",
      category: "url-signals",
      observation: `${multipleCanonical.length} 个页面声明了多个 canonical URL。`,
      urls: multipleCanonical.map((page) => page.url).slice(0, MAX_REPORTED_URLS),
      evidence: multipleCanonical.map((page) => page.canonicals.join(" | ")).slice(0, MAX_REPORTED_URLS),
      impact_boundary: "只验证源码声明冲突，不推断搜索系统最终选择。",
      verification: "每个页面只保留一个绝对 canonical，并与目标 URL 状态和内容一致。",
    });
  }
  const crossOriginCanonical = healthyHtmlPages.filter(
    (page) => page.canonicals.length === 1 && originKey(new URL(page.canonicals[0])) !== originKey(new URL(page.url)),
  );
  if (crossOriginCanonical.length) {
    addFinding(findings, {
      code: "canonical.cross-origin",
      severity: "medium",
      category: "url-signals",
      observation: `${crossOriginCanonical.length} 个页面将 canonical 指向其他 origin。`,
      urls: crossOriginCanonical.map((page) => page.url).slice(0, MAX_REPORTED_URLS),
      evidence: crossOriginCanonical.map((page) => `canonical=${page.canonicals[0]}`).slice(0, MAX_REPORTED_URLS),
      impact_boundary: "跨域 canonical 可能是有意的内容联合；本检查只标记需要核实的事实。",
      verification: "确认跨域归属意图，并核对目标页面可访问、内容等价且允许索引。",
      confidence: "medium",
    });
  }
  const noindexPages = healthyHtmlPages.filter((page) => page.noindex);
  if (noindexPages.length) {
    addFinding(findings, {
      code: "indexing.noindex",
      severity: "high",
      category: "indexing",
      observation: `${noindexPages.length} 个成功 HTML 响应声明 noindex。`,
      urls: noindexPages.map((page) => page.url).slice(0, MAX_REPORTED_URLS),
      evidence: noindexPages.map((page) => `robots=${page.robots.join(",")}`).slice(0, MAX_REPORTED_URLS),
      impact_boundary: "noindex 可能是有意配置；本检查不声称这些 URL 当前已被收录或已移除。",
      verification: "按页面意图核对 meta robots 与 X-Robots-Tag，修改后请求实时源码复验。",
    });
  }
  const missingH1 = healthyHtmlPages.filter((page) => page.h1_count === 0);
  if (missingH1.length) {
    addFinding(findings, {
      code: "headings.h1-missing",
      severity: "medium",
      category: "content-structure",
      observation: `${missingH1.length} 个成功 HTML 响应没有 h1。`,
      urls: missingH1.map((page) => page.url).slice(0, MAX_REPORTED_URLS),
      evidence: ["HTTP 源码中 h1_count=0"],
      impact_boundary: "标题层级是内容结构证据，不是独立排名保证。",
      verification: "确认页面主主题在初始 HTML 中有清晰、可见的主标题。",
    });
  }
  const invalidJsonLd = healthyHtmlPages.filter((page) => page.json_ld_errors.length > 0);
  if (invalidJsonLd.length) {
    addFinding(findings, {
      code: "structured-data.invalid-json",
      severity: "medium",
      category: "structured-data",
      observation: `${invalidJsonLd.length} 个页面包含无法解析的 JSON-LD。`,
      urls: invalidJsonLd.map((page) => page.url).slice(0, MAX_REPORTED_URLS),
      evidence: invalidJsonLd.map((page) => page.json_ld_errors.join("; ")).slice(0, MAX_REPORTED_URLS),
      impact_boundary: "这里只验证 JSON 语法和类型提取，不验证富结果资格或搜索展示。",
      verification: "修复 JSON 后使用对应搜索引擎的结构化数据测试工具复验完整对象。",
    });
  }
  const imagesMissingAlt = healthyHtmlPages.filter((page) => page.images.some((image) => !image.alt_present));
  if (imagesMissingAlt.length) {
    addFinding(findings, {
      code: "images.alt-attribute-missing",
      severity: "low",
      category: "images",
      observation: `${imagesMissingAlt.length} 个页面有 img 元素缺少 alt 属性。`,
      urls: imagesMissingAlt.map((page) => page.url).slice(0, MAX_REPORTED_URLS),
      evidence: imagesMissingAlt
        .map((page) => `missing_alt=${page.images.filter((image) => !image.alt_present).length}`)
        .slice(0, MAX_REPORTED_URLS),
      impact_boundary: "装饰图可以使用空 alt，但缺少 alt 属性与明确空值不是同一事实。",
      verification: "为信息图提供准确替代文本，为纯装饰图显式使用空 alt。",
    });
  }
  const missingLang = healthyHtmlPages.filter((page) => !page.html_lang);
  if (missingLang.length) {
    addFinding(findings, {
      code: "language.html-lang-missing",
      severity: "low",
      category: "international",
      observation: `${missingLang.length} 个成功 HTML 响应没有 html lang。`,
      urls: missingLang.map((page) => page.url).slice(0, MAX_REPORTED_URLS),
      evidence: ["HTTP 源码中 html_lang 为空"],
      impact_boundary: "lang 主要帮助语言与可访问性解释；本检查不推断区域排名。",
      verification: "在服务端输出与页面主要语言一致的有效 BCP 47 语言标签。",
    });
  }

  const titleGroups = new Map<string, InspectPage[]>();
  for (const page of healthyHtmlPages) {
    const title = page.titles[0]?.toLowerCase();
    if (!title) continue;
    titleGroups.set(title, [...(titleGroups.get(title) ?? []), page]);
  }
  const duplicateTitles = [...titleGroups.values()].filter((group) => group.length > 1);
  if (duplicateTitles.length) {
    const duplicatePages = duplicateTitles.flat();
    addFinding(findings, {
      code: "metadata.title-duplicate",
      severity: "medium",
      category: "metadata",
      observation: `${duplicatePages.length} 个范围内页面共享 title。`,
      urls: duplicatePages.map((page) => page.url).slice(0, MAX_REPORTED_URLS),
      evidence: duplicateTitles.map((group) => `title=${group[0].titles[0]} | pages=${group.length}`).slice(0, MAX_REPORTED_URLS),
      impact_boundary: "重复 title 只在本次抓取范围内成立，不证明页面内容重复或造成流量损失。",
      verification: "核对页面搜索意图，必要时让 title 清楚区分各 URL。",
    });
  }

  const start = new URL(startUrl);
  if (robots && !isAllowedByRobots(start, robots)) {
    addFinding(findings, {
      code: "robots.blocks-start-url",
      severity: production ? "critical" : "high",
      category: "crawl-control",
      observation: "robots.txt 的适用规则阻止本审计用户代理抓取起始 URL。",
      urls: [startUrl],
      evidence: [`robots_source=${robots.source}`],
      impact_boundary: "不同搜索爬虫可能匹配不同 user-agent 组；robots 阻止抓取不等同于 noindex。",
      verification: "按目标搜索爬虫复核适用规则，并在修改后实时请求 robots.txt。",
    });
  }
  const sitemapNoindex = healthyHtmlPages.filter((page) => sitemapUrls.has(page.url) && page.noindex);
  if (sitemapNoindex.length) {
    addFinding(findings, {
      code: "sitemap.noindex-url",
      severity: "high",
      category: "url-signals",
      observation: `${sitemapNoindex.length} 个 sitemap URL 同时声明 noindex。`,
      urls: sitemapNoindex.map((page) => page.url).slice(0, MAX_REPORTED_URLS),
      evidence: ["sitemap inclusion + HTTP source noindex"],
      impact_boundary: "只覆盖成功解析且位于本次有界范围的 sitemap URL。",
      verification: "让 sitemap 只包含希望索引的规范 URL，并同步页面 robots 指令。",
    });
  }

  const fetchedByUrl = new Map(pages.map((page) => [page.url, page]));
  const brokenEdges = healthyHtmlPages.flatMap((page) =>
    page.internal_links
      .map((target) => ({ source: page.url, target, result: fetchedByUrl.get(target) }))
      .filter((edge) => edge.result && edge.result.status >= 400),
  );
  if (brokenEdges.length) {
    addFinding(findings, {
      code: "links.internal-http-error",
      severity: "high",
      category: "internal-links",
      observation: `${brokenEdges.length} 条已验证站内链接指向 4xx/5xx 响应。`,
      urls: [...new Set(brokenEdges.map((edge) => edge.target))].slice(0, MAX_REPORTED_URLS),
      evidence: brokenEdges
        .map((edge) => `${edge.source} -> ${edge.target} status=${edge.result?.status}`)
        .slice(0, MAX_REPORTED_URLS),
      impact_boundary: "只报告目标也在本次抓取范围内并实际返回错误的链接。",
      verification: "修复链接目标或重定向，并从源页面重新点击和请求目标。",
    });
  }

  const severityOrder: Record<Severity, number> = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };
  return findings.sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity] || a.code.localeCompare(b.code));
}

function reportMarkdown(report: InspectReport): string {
  const scope = report.scope as {
    base_url: string;
    pages_parsed: number;
    sitemap_urls: number;
    production_asserted: boolean;
  };
  const summary = report.summary as {
    finding_counts: Record<Severity, number>;
    noindex_pages: number;
    reachable_pages_from_root: number;
    max_observed_click_depth: number | null;
  };
  const counts = summary.finding_counts;
  const labels: Record<Severity, string> = { critical: "严重阻断", high: "高", medium: "中", low: "低", info: "信息" };
  const inlineCode = (value: unknown) => `\`${String(value).replace(/`/g, "\\`").replace(/[\r\n]+/g, " ")}\``;
  const lines = [
    "# Vibio SEO 源码审计",
    "",
    `- 生成时间：${report.generated_at}`,
    `- 基准 URL：${scope.base_url}`,
    `- 已解析页面：${scope.pages_parsed}`,
    `- sitemap URL：${scope.sitemap_urls}`,
    `- 生产目标确认：${scope.production_asserted ? "是" : "否"}`,
    `- 发现：严重阻断 ${counts.critical} / 高 ${counts.high} / 中 ${counts.medium} / 低 ${counts.low} / 信息 ${counts.info}`,
    "",
    "## 证据边界",
    "",
    ...report.limitations.map((item) => `- ${item}`),
    "",
    "## 发现",
    "",
  ];
  if (!report.findings.length) lines.push("当前有界范围没有命中内置规则；这不代表 SEO 完整、已收录或效果得到证明。", "");
  report.findings.forEach((finding, index) => {
    lines.push(
      `### ${index + 1}. [${labels[finding.severity]}] ${finding.observation}`,
      "",
      `- 代码：\`${finding.code}\``,
      `- 类别：${finding.category}`,
      `- 置信度：${finding.confidence}`,
    );
    if (finding.urls.length) lines.push(`- URL：${finding.urls.map(inlineCode).join("；")}`);
    if (finding.evidence.length) lines.push(`- 证据：${finding.evidence.map(inlineCode).join("；")}`);
    lines.push(`- 影响边界：${finding.impact_boundary}`, `- 复验：${finding.verification}`, "");
  });
  lines.push(
    "## 覆盖摘要",
    "",
    `- noindex 页面：${summary.noindex_pages}`,
    `- 从根页面可达：${summary.reachable_pages_from_root}`,
    `- 已观察最大点击深度：${summary.max_observed_click_depth ?? "未知"}`,
    "",
  );
  return lines.join("\n");
}

export async function inspectSite(input: SeoInspectInput): Promise<{ report: InspectReport; markdown: string }> {
  const maxPages = input.max_pages ?? 5;
  const production = input.production ?? false;
  if (!Number.isInteger(maxPages) || maxPages < 1 || maxPages > 10) {
    throw new SeoInspectError("max_pages 必须是 1 到 10 的整数。");
  }
  if (typeof production !== "boolean") throw new SeoInspectError("production 必须是布尔值。");
  const start = canonicalizeUrl(validateAuditUrl(input.url));
  const allowedOrigin = originKey(start);
  await resolvePublicTarget(start, allowedOrigin);
  const deadline = Date.now() + AUDIT_TIMEOUT_MS;
  let fetches = 0;
  const notes: string[] = [];

  let robots: RobotsDocument | null = null;
  const robotsUrl = new URL("/robots.txt", start).toString();
  try {
    const response = await fetchWithRedirects(robotsUrl, allowedOrigin, deadline);
    fetches += response.requests;
    if (response.status >= 200 && response.status < 300) {
      robots = parseRobotsDocument(response.body.toString("utf8"), response.finalUrl, response.status);
    }
  } catch {
    notes.push("robots.txt 未能安全读取；报告不据此推断抓取规则为空。");
  }

  const sitemapPages = new Set<string>();
  const sitemapSources: string[] = [];
  const pendingSitemaps = [
    ...(robots?.sitemaps ?? []),
    new URL("/sitemap.xml", start).toString(),
  ];
  const seenSitemaps = new Set<string>();
  while (pendingSitemaps.length && seenSitemaps.size < MAX_SITEMAPS && Date.now() < deadline) {
    const candidate = pendingSitemaps.shift();
    if (!candidate) break;
    let sitemapUrl: URL;
    try {
      sitemapUrl = canonicalizeUrl(validateAuditUrl(new URL(candidate, start).toString()));
    } catch {
      continue;
    }
    if (originKey(sitemapUrl) !== allowedOrigin || seenSitemaps.has(sitemapUrl.toString())) continue;
    seenSitemaps.add(sitemapUrl.toString());
    try {
      const response = await fetchWithRedirects(sitemapUrl.toString(), allowedOrigin, deadline);
      fetches += response.requests;
      if (response.status < 200 || response.status >= 300) continue;
      sitemapSources.push(response.finalUrl);
      const parsed = parseSitemapXml(response.body.toString("utf8"));
      for (const rawPage of parsed.pageUrls) {
        if (sitemapPages.size >= MAX_SITEMAP_URLS) break;
        try {
          const pageUrl = canonicalizeUrl(validateAuditUrl(new URL(rawPage, start).toString()));
          if (originKey(pageUrl) === allowedOrigin) sitemapPages.add(pageUrl.toString());
        } catch {
          // Invalid or credential-bearing sitemap URLs are ignored and never fetched.
        }
      }
      for (const child of parsed.sitemapUrls) pendingSitemaps.push(child);
    } catch {
      if ((robots?.sitemaps ?? []).includes(candidate)) notes.push("robots.txt 声明的一个 sitemap 未能安全读取。");
    }
  }

  const queue: CrawlQueueItem[] = [{ url: start.toString(), depth: 0 }];
  const queued = new Set([start.toString()]);
  const pages = new Map<string, InspectPage>();
  let sitemapSeedsAdded = false;
  while (queue.length && pages.size < maxPages && Date.now() < deadline) {
    const item = queue.shift();
    if (!item) break;
    let itemUrl: URL;
    try {
      itemUrl = validateAuditUrl(item.url);
    } catch {
      continue;
    }
    if (item.url !== start.toString() && !isAllowedByRobots(itemUrl, robots)) continue;
    try {
      const response = await fetchWithRedirects(item.url, allowedOrigin, deadline);
      fetches += response.requests;
      const finalUrl = canonicalizeUrl(response.finalUrl).toString();
      if (pages.has(finalUrl)) continue;
      const contentType = firstHeader(response.headers, "content-type");
      const html = isHtmlContent(contentType, response.body);
      const parsed = html
        ? parseHtmlDocument(response.body.toString("utf8"), finalUrl, response.headers)
        : emptyParsedDocument(response.body, finalUrl);
      const page: InspectPage = {
        ...parsed,
        url: finalUrl,
        source: finalUrl,
        evidence_mode: "http_source",
        requested_url: response.requestedUrl,
        status: response.status,
        final_url: finalUrl,
        content_type: contentType,
        response_headers: response.headers,
        redirect_chain: response.redirectChain,
        depth: item.depth,
        inbound_links_in_scope: 0,
        is_html: html,
      };
      pages.set(finalUrl, page);
      queued.add(finalUrl);
      if (html) {
        for (const link of page.internal_links) {
          if (queued.has(link) || pages.size + queue.length >= maxPages * 3) continue;
          let linkUrl: URL;
          try {
            linkUrl = validateAuditUrl(link);
          } catch {
            continue;
          }
          if (originKey(linkUrl) !== allowedOrigin || !isAllowedByRobots(linkUrl, robots)) continue;
          queued.add(link);
          queue.push({ url: link, depth: item.depth === null ? null : item.depth + 1 });
        }
      }
      if (!sitemapSeedsAdded) {
        sitemapSeedsAdded = true;
        for (const sitemapUrl of sitemapPages) {
          if (queued.has(sitemapUrl) || !isAllowedByRobots(new URL(sitemapUrl), robots)) continue;
          queued.add(sitemapUrl);
          queue.push({ url: sitemapUrl, depth: null });
        }
      }
    } catch (error) {
      if (item.url === start.toString() && pages.size === 0) throw error;
      notes.push("一个范围内 URL 未能安全读取；未把失败推断为页面不存在。");
    }
  }
  if (Date.now() >= deadline) notes.push("达到 50 秒总时间上限，报告只覆盖截止前取得的证据。");

  const pageList = [...pages.values()].sort((a, b) => a.url.localeCompare(b.url));
  const inbound = new Map(pageList.map((page) => [page.url, 0]));
  for (const page of pageList) {
    for (const target of page.internal_links) {
      if (inbound.has(target)) inbound.set(target, (inbound.get(target) ?? 0) + 1);
    }
  }
  pageList.forEach((page) => {
    page.inbound_links_in_scope = inbound.get(page.url) ?? 0;
  });

  const findings = buildFindings(pageList, start.toString(), production, robots, sitemapPages);
  const findingCounts: Record<Severity, number> = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
  findings.forEach((finding) => {
    findingCounts[finding.severity] += 1;
  });
  const statusCounts: Record<string, number> = {};
  pageList.forEach((page) => {
    statusCounts[String(page.status)] = (statusCounts[String(page.status)] ?? 0) + 1;
  });
  const depths = pageList.map((page) => page.depth).filter((depth): depth is number => depth !== null);
  const limitations = [
    "本报告只验证当前匿名 HTTP 响应源码，不执行 JavaScript，也不声称客户端渲染后的 metadata、正文或链接相同。",
    "本次最多解析 10 个同源页面；robots.txt、sitemap 和页面响应均受 2 MiB 单响应上限与 8 秒请求上限约束。",
    "报告不生成健康分，不证明 Google 已抓取、已索引、选择相同 canonical、给予富结果或带来排名与流量变化。",
    "DNS 在连接前解析并校验，连接只使用已校验的固定公网 IP；任一私网、环回、本地链路或混合 DNS 结果都会被拒绝。",
    ...notes,
  ];
  const report: InspectReport = {
    schema_version: "1.3",
    analysis_kind: "bounded_seo_artifact_inspection",
    tool: "vibio-seo-inspect",
    version: "2.0.0",
    generated_at: new Date().toISOString(),
    scope: {
      mode: "remote",
      evidence_mode: "http_source",
      base_url: start.toString(),
      pages_parsed: pageList.length,
      known_assets: 0,
      fetches,
      sitemap_urls: sitemapPages.size,
      robots_source: robots?.source ?? null,
      production_asserted: production,
      fetch_mode: "raw-http-source",
      javascript_rendered: false,
      client_side_dom_verified: false,
      browser_provenance_verified: false,
      browser_provenance: null,
      http_response_verified: true,
      source_comparison_provided: false,
      javascript_runtime_executed_by_tool: false,
      sitemap_seeded_crawl: sitemapPages.size > 0,
      max_pages: maxPages,
      response_limit_bytes: RESPONSE_LIMIT_BYTES,
      request_timeout_ms: REQUEST_TIMEOUT_MS,
    },
    summary: {
      finding_counts: findingCounts,
      status_counts: statusCounts,
      noindex_pages: pageList.filter((page) => page.noindex).length,
      orphan_pages_in_scope: pageList.filter((page) => page.url !== start.toString() && page.inbound_links_in_scope === 0).length,
      reachable_pages_from_root: depths.length,
      max_observed_click_depth: depths.length ? Math.max(...depths) : null,
    },
    limitations,
    findings,
    pages: pageList,
    rendering_comparison: null,
    robots: robots
      ? {
          source: robots.source,
          status: robots.status,
          sha256: robots.raw_sha256,
          groups: robots.groups.length,
          sitemap_directives: robots.sitemaps,
        }
      : null,
    sitemap: {
      sources: sitemapSources,
      urls_discovered: sitemapPages.size,
      resources_fetched: seenSitemaps.size,
    },
  };
  return { report, markdown: reportMarkdown(report) };
}
