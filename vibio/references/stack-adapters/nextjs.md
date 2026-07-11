# Next.js SEO 落地适配器

最近核验：2026-07-11。

`seo-fix-principles.md` 决定“正确结果是什么”，本文只说明如何在 Next.js 落地。示例以 App Router 为主；Pages Router 项目需映射到 `_app`、`_document`、`next/head` 或对应数据获取方式，不能照抄文件路径。

## 1. 先确认项目形态

检查：

- Next.js 版本、App/Pages Router 或混合模式。
- 静态导出、Node server、Edge、Vercel 或自托管。
- `next.config.*` 中 redirects、rewrites、headers、basePath、trailingSlash、i18n。
- 内容来源和动态路由的枚举方式。
- Metadata API、head helper、JSON-LD helper 是否已有单一事实源。

输出：`Stack / Router / Rendering / Edit mode / Adapter`。

## 2. 元数据

在根 layout 设置 canonical host，用页面 `metadata` 或 `generateMetadata` 生成准确、独特的 title、description、canonical 和社交预览。

```ts
// app/layout.tsx
import type { Metadata } from "next";

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL!),
  title: { default: "Brand", template: "%s | Brand" },
};
```

```ts
// app/products/[slug]/page.tsx
export async function generateMetadata({ params }): Promise<Metadata> {
  const product = await getProduct((await params).slug);
  if (!product) return {};
  const path = `/products/${product.slug}`;
  return {
    title: product.metaTitle ?? product.name,
    description: product.metaDescription ?? product.summary,
    alternates: { canonical: path },
    openGraph: {
      type: "website",
      url: path,
      title: product.metaTitle ?? product.name,
      description: product.metaDescription ?? product.summary,
      images: [{ url: product.ogImage, alt: product.name }],
    },
  };
}
```

Google 没有固定 title/description 字符上限。以简洁、准确、设备实际展示和用户判断为准。

## 3. 不存在页面与状态码

动态实体不存在时调用 `notFound()`，确保得到真实 404，而不是带错误文案的 200 soft-404。

```ts
import { notFound } from "next/navigation";

const product = await getProduct(slug);
if (!product) notFound();
```

永久迁移使用 `permanentRedirect()` 或 `next.config` 的 `permanent: true`；临时跳转使用正确临时状态。不要把所有旧 URL 重定向到首页。

## 4. Canonical host 与 URL 一致性

- `metadataBase`、环境变量、canonical、sitemap、robots host 和 hreflang 使用同一正式 origin。
- 通过 hosting/platform 或 `next.config` 把非首选 host、协议和路径变体重定向到首选 URL。
- Rewrites 不等于 redirects；确认搜索引擎最终看到的 URL/状态。
- 参数页、筛选页和分页策略需结合实际索引需求，不能一律 canonical 到第一页。

## 5. Robots 与 sitemap

```ts
// app/robots.ts
import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  const origin = process.env.NEXT_PUBLIC_SITE_URL!;
  return {
    rules: [{ userAgent: "*", allow: "/", disallow: ["/api/", "/admin/"] }],
    sitemap: `${origin}/sitemap.xml`,
    host: origin,
  };
}
```

```ts
// app/sitemap.ts
import type { MetadataRoute } from "next";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const products = await getAllProducts();
  return products.map((product) => ({
    url: absoluteUrl(`/products/${product.slug}`),
    lastModified: product.updatedAt,
  }));
}
```

Sitemap 应从页面真实数据源生成，只列 canonical、可索引 URL。`changeFrequency` 和 `priority` 不是排名杠杆，可省略；`lastModified` 必须真实。

普通页面不要调用 Google Indexing API。

## 6. JSON-LD

只添加当前支持、与可见内容一致的类型。首页可按官方说明使用 Organization/WebSite；产品、文章、面包屑、视频等按页面类型和 Search Gallery 当前资格使用。不要为 Google 富结果添加已停用的 FAQPage/HowTo。

```tsx
function JsonLd({ data }: { data: object }) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{
        __html: JSON.stringify(data).replace(/</g, "\\u003c"),
      }}
    />
  );
}
```

不要把未经验证的用户文本直接拼进 script。构建后解析 JSON-LD，并用当前 Rich Results Test/Schema validator 检查。

## 7. 渲染与内容可用性

Google 能处理 JavaScript，但服务器/静态渲染通常让关键内容更稳定地被用户、抓取器和分享工具获取。

- 产品名称、核心事实、正文、主导航和内部链接应在初始渲染结果中存在。
- 不要把主内容永久初始为 `opacity: 0`，或只有滚动/点击后才注入。
- Client component 只用于真实交互；能在 server component 获取和渲染的数据不要无理由推迟到客户端。
- Streaming/Suspense fallback 不能导致抓取时只留下无意义 loading shell。
- `generateStaticParams`、cache/revalidate 和动态数据策略要与内容更新频率一致。

## 8. 国际化

在 `alternates.languages` 输出每个真实、可索引的语言/地区 URL，并保证 reciprocity、canonical 和 locale 内容一致。按 Google 当前支持规则验证 hreflang：语言使用 ISO 639-1 两字母代码，地区使用 ISO 3166-1 Alpha-2，适用时脚本使用 ISO 15924；不要把任意 BCP 47 变体视为必然受支持。不要只翻译 metadata；正文、单位、标准、案例和转化路径也要本地化。

## 9. 图片、视频与性能

- 使用 `next/image` 时提供准确 alt、sizes 和适合的 priority/preload；不要把所有图片设为 priority。
- LCP 图不要 lazy-load；下方媒体按需延迟。
- OG 图片的声明尺寸与真实文件一致，URL 可公开访问。
- 第三方脚本、字体和视频 embed 需以 CrUX/RUM 与转化影响排序。
- 不因“SEO”删除所有动效；只修复导致主内容不可见、CLS、性能或无障碍问题的实现。

## 10. AI Search 边界

Google AI Overviews/AI Mode 仍依赖正常 Search 资格和质量系统。Next.js 不需要特殊 AI route、细碎 chunk 或 schema。

Google Search 忽略 `llms.txt`。只有目标平台官方说明支持、且项目批准实验时，才可从 sitemap/内容源生成可选文件；不能把它列为 Google 修复项。

`Google-Extended` 不控制内容是否在 AI Overviews/AI Mode 中出现、被链接或用于 grounding，也不影响 Google Search 收录/排名；它另用于限制相关模型训练用途。

## 11. 验证

按项目已有命令执行，不能假设一定使用 npm：

```bash
npm run lint
npx tsc --noEmit
npm run build
```

然后检查实际服务/构建产物：

- 代表性页面状态码、重定向与 canonical。
- 渲染 title、description、robots、hreflang、OG。
- JSON-LD 可解析且与可见内容一致。
- Sitemap/robots URL、内容与响应类型。
- 404、重定向、参数和多语言边界。
- 关键内容/内链在渲染结果中存在。

报告分为：`build/static verification passed`、`served artifact passed`、`GSC/crawl/search effect pending`。只有文件存在不能证明运行时正确。
