# Next.js SEO Fix Playbook

Verified, code-level fixes for modern web stacks — Next.js App Router especially. Every recipe here was applied and verified (`npm run build` + `tsc --noEmit` + ESLint) on a real Vibio client project (a B2B carbon-fiber/fiberglass export site). Adapt the specifics; keep the principles.

**Golden rule:** after any change, run the project's build, type-check, and lint, then confirm the rendered HTML/`<head>` actually contains the intended tags before reporting done. SERP-facing changes only show up after Google re-crawls — tell the user to request indexing in Search Console.

## Fast codebase audit checklist

Run this before heavy crawls. It catches the high-frequency issues in minutes.

1. **Metadata coverage** — does every `page.tsx` export `metadata` or `generateMetadata`? (Redirect-only pages are exempt.)
   `for f in $(find app -name "page.tsx"); do grep -q "generateMetadata\|export const metadata" "$f" || echo "missing: $f"; done`
2. **Canonical** — is `alternates.canonical` set per page (usually via a shared `createPageMetadata` helper)?
3. **Structured data** — does the site emit `Organization` + `WebSite` site-wide, and `Product`/`Article`/`BreadcrumbList`/`FAQPage` where relevant? Validate with `seo-schema`.
4. **OG/Twitter** — is there a real OG image with correct declared dimensions? Is `og:site_name` the brand/legal name?
5. **robots + sitemap** — `app/robots.ts` and `app/sitemap.ts` present, sitemap referenced in robots, `/api` disallowed, host correct.
6. **H1 / heading order** — exactly one `<h1>` per page; no h1→h3 jumps. (Headings often live in referenced PageContent components.)
7. **Images** — all `next/image`/`<img>` have descriptive `alt`; no raw `<img>` where `next/image` should be used.
8. **Internal links** — footer covers all top pages; key landing pages link to each other with descriptive anchors; no orphan pages.
9. **llms.txt** — present for AI-search visibility?
10. **CSP / headers** — does the CSP block anything the app needs (e.g. dev `unsafe-eval`)? Are security headers set?

---

## Recipe: remove scroll-reveal animations (UX + accessibility)

**When:** content fades/slides in on scroll (GSAP ScrollTrigger, framer-motion `whileInView`, AOS, etc.). Visitors are there to read information, not watch motion; scroll-reveal also delays content paint, hurts perceived performance, and can fail for reduced-motion users and some crawlers/screenshotters.

**What to remove:**
- GSAP: `gsap.fromTo(..., { opacity: 0, y }, { scrollTrigger: {...} })` plus the `opacity-0` / `clip-hidden-*` initial-state classes the elements start with.
- framer-motion: `initial`/`whileInView`/`animate` opacity-translate combos and `variants` like `fadeUp`. Replace `<motion.div>` with `<div>` and drop the import.
- Scroll-triggered number counters: render the final value directly instead of animating from 0.

**Keep:** genuine interaction feedback that is *not* scroll-gated — hero carousel cross-fades, image-gallery swap fades, hover transitions. Removing those makes the UI feel broken.

**Method:**
1. Grep the surface: `grep -rln "whileInView\|framer-motion\|ScrollTrigger\|gsap\|opacity-0\|clip-hidden\|data-reveal" app components`.
2. For each hit, delete the animation hook/wrapper and the initial-hidden class so the element is visible by default.
3. If a component loses all client-side behavior, drop now-unused imports and consider removing `"use client"`.
4. Verify nothing else referenced the removed `data-*` attributes; run build/lint.

Net effect on the reference project: ~360 fewer lines, content visible immediately, no layout shift from reveal.

---

## Recipe: above-the-fold form / CTA visibility

**When:** a contact/inquiry page pushes the form and submit button below the fold; visitors must scroll to find "Send Inquiry". For a B2B site the inquiry form *is* the conversion — it must be visible on load.

**Method:**
1. Shrink the top hero padding (e.g. `pt-36` → `pt-28`) and the heading size (`text-4xl` → `text-3xl`).
2. Cut secondary descriptive paragraphs in the header; keep one tight value line.
3. Tighten form internals: container padding `p-8` → `p-6`, field gaps `mt-4` → `mt-3`, textarea `rows={5}` → `4`, button `mt-6` → `mt-5`.
4. Goal: the whole form + submit button fits one viewport on a typical laptop without scrolling.

Pair with: link the address in the contact card to Google Maps in English — `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}&hl=en` (the `hl=en` forces the English UI for international buyers).

---

## Recipe: footer redesign + social/marketplace links

**When:** a light-gray footer with thin contrast, or missing the channels B2B buyers actually use.

**Method:**
1. Dark theme for weight and contrast: `bg-neutral-900`, white headings, `text-neutral-400` links hover→white, `border-white/10` dividers.
2. Make section group titles (e.g. "Carbon Fiber", "Glass Fiber") clickable links to the division landing pages — free internal links to core pages.
3. Add the company column's missing pages (e.g. Services).
4. Social/marketplace links as `aria-label`led icon anchors with `target="_blank" rel="noopener noreferrer"`. For export manufacturers, wire the channels that matter: WhatsApp, LinkedIn, the relevant B2B marketplace (e.g. Made-in-China company page), YouTube, plus email/phone. Use real SVG brand paths, not placeholders.

These changes double as internal-linking improvements — they feed link equity to landing pages and help discovery.

---

## Recipe: correct OG / social share image

**When:** `og:image` points at a square logo (e.g. 2000×2000) but the metadata declares `1200×630`. Share cards then render a mislabeled square logo — unprofessional and dimension-mismatched.

**Principles:**
- OG images should be landscape, ~1.91:1 (1200×630 ideal). A representative photo (factory, product, R&D) beats a bare logo for click-through.
- Declared `width`/`height` must match the actual file.
- For per-page images that vary in size (product/article images), **omit** width/height and let platforms read them, rather than forcing one wrong size.

**Method:**
1. Pick a representative landscape image already in the project (e.g. a hero banner) or generate one with `seo-image-gen`.
2. Centralize in the SEO config: `ogImage`, `ogImageWidth`, `ogImageHeight`.
3. In the shared metadata helper, declare dimensions **only** when using the default image:
   ```ts
   const isDefaultImage = image === siteConfig.ogImage;
   const ogImage = isDefaultImage
     ? { url, width: siteConfig.ogImageWidth, height: siteConfig.ogImageHeight, alt }
     : { url, alt };
   ```
4. Update any hardcoded `1200×630` in the root `layout.tsx` OG block to the config values.
5. Keep the square logo for `Organization.logo` in JSON-LD — that one *should* be square.
6. Verify: grep the prerendered HTML for `og:image` + `og:image:width`. Tell the user to re-scrape via the platform debuggers (Facebook Sharing Debugger, LinkedIn Post Inspector, Twitter Card Validator) since they cache.

---

## Recipe: llms.txt for AI-search visibility (GEO)

**When:** the site has no `llms.txt`. AI answer engines (ChatGPT, Perplexity, etc.) use it to understand site structure and surface citable content. High-leverage for B2B where buyers increasingly ask LLMs.

**Method:** generate it dynamically from the same data sources as the sitemap so it never drifts. Next.js route handler at `app/llms.txt/route.ts`:

```ts
import { absoluteUrl, siteConfig } from "@/lib/seo";
import { contactInfo } from "@/lib/contact";
import { allCarbonFiberCategories } from "@/data/carbon-fiber";
// ...other data sources
export const dynamic = "force-static";

export function GET() {
  const body = `# ${siteConfig.name}

> ${siteConfig.description} Operated by ${contactInfo.company}, a manufacturer ... since ${contactInfo.foundingDate}.

## Carbon Fiber
${allCarbonFiberCategories.map(c => `- [${c.name}](${absoluteUrl(`/carbon-fiber/products/${c.slug}`)}): ${c.description}`).join("\n")}

## Company
- [About](${absoluteUrl("/about")})
- [Contact](${absoluteUrl("/contact")}): ${contactInfo.emails[0]}
`;
  return new Response(body, {
    headers: { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "public, max-age=3600, s-maxage=86400" },
  });
}
```

Follows the https://llmstxt.org format: H1 title, blockquote summary, sectioned link lists with short descriptions. Verify it prerenders as a static route and the body is correct. Then deepen with the `seo-geo` skill (citability, brand-mention signals).

---

## Recipe: brand name in the SERP (site name + search highlighting)

This solves two distinct things people confuse. **Both require Google to re-crawl before they show.**

**Problem A — the site-name line under the title shows the bare domain** (e.g. "zysfiber.com") instead of the company name.
Google derives the SERP site name from `WebSite` structured data `name` + `og:site_name`. If neither states the full name, Google falls back to the domain.

Fix:
1. Add a `WebSite` JSON-LD on the homepage (site-wide layout) with the full legal name and the short brand as `alternateName`:
   ```ts
   export function websiteJsonLd() {
     return { "@context": "https://schema.org", "@type": "WebSite",
       name: siteConfig.legalName,            // "Jiangsu Zeyusen Carbon Fiber Technology Co., Ltd."
       alternateName: siteConfig.name,        // "ZeYuSen Fiber"
       url: absoluteUrl("/") };
   }
   ```
2. Set `openGraph.siteName` to the legal name in both the root `layout.tsx` and the shared metadata helper.
3. Add `alternateName` to the existing `Organization` JSON-LD too.
4. Keep the `<title>` template short (`%s | ShortBrand`) — don't bloat every tab/title with the full legal name.

**Problem B — searching the company name doesn't bold-match (highlight) on your result, but does on an older site.**
The red/bold text in a SERP snippet is Google highlighting the searched query where it appears in the page's meta description / indexed copy. If the full company name never appears in your description, there's nothing to match.

Fix: include the full legal name naturally in the homepage `meta description` (and ideally visible body copy):
> "Jiangsu Zeyusen Carbon Fiber Technology Co., Ltd. manufactures carbon fiber mats, fiberglass fabrics, ... "

Verify (A+B): grep the prerendered homepage HTML for `"@type":"WebSite"`, `og:site_name`, and the legal name inside `name="description"`. Then have the user submit the homepage for indexing in Search Console — new sites especially are slow to reflect this.

---

## Recipe: CSP `unsafe-eval` for dev only

**When:** dev console shows `eval() is not supported ... make sure 'unsafe-eval' is included` because a strict `Content-Security-Policy` `script-src` blocks what React/Turbopack need in development. Production doesn't need it and shouldn't have it.

**Method** in `next.config.ts`:
```ts
const isDev = process.env.NODE_ENV === "development";
// in script-src:
`script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""} https://...`,
```
Restart the dev server (config changes don't hot-reload). Production CSP stays strict.

---

## Recipe: canonical host / www redirect & metadata hygiene

- Enforce one canonical host. Redirect non-www → www (or vice versa) with a `permanent` redirect in `next.config.ts` `redirects()` keyed on the `host`. Pick the host that matches `NEXT_PUBLIC_SITE_URL` and the canonical tags.
- `metadataBase` set to the canonical site URL so all relative OG/canonical URLs resolve absolutely.
- Per-page `canonical` via a shared `createPageMetadata({ title, description, path, image? })` helper — keeps canonical/OG/Twitter consistent across the whole app.
- `robots.ts`: allow `/`, disallow `/api/`, reference the sitemap, set `host`.
- `sitemap.ts`: generate from the same data sources as pages (categories, products, blog, applications) so it never goes stale; set sensible `changeFrequency`/`priority`.

---

## Verification ritual (every fix)

```bash
npx tsc --noEmit          # types
npx eslint <changed files> # lint
npm run build              # full build + static generation
# then confirm intent in output, e.g.:
grep -oE 'property="og:site_name" content="[^"]*"' .next/server/app/index.html
```
Clean up temp files. Report exactly what passed and what couldn't be verified (e.g. live SERP changes pending Google re-crawl). Commit only when asked; if asked to commit without attribution, omit any AI co-author trailer.


