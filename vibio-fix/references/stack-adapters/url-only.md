# Stack Adapter: URL-only (no code access)

The fallback when you can't edit code or templates — hosted platforms (Wix, Squarespace, Webflow without code export, WP.com free, Shopify without theme access), a marketing team that only has CMS login, or the user just gave you a URL. You **diagnose from the rendered page and hand back a precise, paste-ready spec** instead of editing.

Target spec ("what correct looks like") is in `../seo-fix-principles.md`. This adapter is about *delivery format* when you can't touch the build.

## Workflow

1. **Fetch the rendered page** (via `seo-page` / `seo-firecrawl` / `seo-technical`, or `WebFetch`/`curl`). Extract the current state of each item in the target spec: title, description, canonical, robots meta, JSON-LD, OG/Twitter, H1/heading order, images/alt, hreflang, llms.txt, sitemap, robots.txt.
2. **Diff against the spec.** For each gap, produce a concrete fix the user can apply *in their platform's UI*.
3. **Hand off in this format** — per finding:
   - **What's wrong** (quote the current rendered value).
   - **Target** (the exact corrected value/snippet).
   - **Where to put it** in their platform (be specific per platform — see below).
   - **How to verify** (what to re-check after they save/publish).

## Platform paste-points (where users actually set these)

| Platform | Title/desc | OG image | JSON-LD / custom head | robots/sitemap |
|---|---|---|---|---|
| Wix | Page → SEO Basics | Social Share | SEO → Advanced → Custom code (header) | auto sitemap; robots editable in SEO tools |
| Squarespace | Page Settings → SEO | Page Settings → Social Image | Settings → Advanced → Code Injection (header) | auto |
| Webflow | Page Settings → SEO | Open Graph | Page/Site Settings → Custom Code (head) | auto + editable |
| WP.com (no editor) | Yoast/Jetpack SEO box | Social settings | limited; plugin-dependent | plugin |
| Framer / Carrd / etc. | page SEO panel | page social panel | site head/embed if exposed | platform-managed |

If the platform exposes a "custom head code" box, you can paste JSON-LD and meta tags there directly. If it doesn't, note the limitation honestly — some tags simply can't be set on some platforms.

## Paste-ready snippets

Give literal, copy-paste blocks. Example for brand SERP site-name (the most common request):

```html
<!-- Paste into the site-wide custom <head> code box -->
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"WebSite",
 "name":"Full Legal Company Name Co., Ltd.",
 "alternateName":"ShortBrand",
 "url":"https://example.com/"}
</script>
<meta property="og:site_name" content="Full Legal Company Name Co., Ltd.">
```

And tell them to also put the full legal name in the homepage SEO description field (for query bold-highlighting). Both only show after the engine re-crawls — they should submit the homepage in Search Console.

## Verification (you can still verify)
You don't have the code, but you can re-fetch the live URL after they publish:
```bash
curl -sL https://example.com/ | grep -oiE 'property="og:site_name"[^>]*|"@type":"WebSite"|name="description"[^>]*'
```
Confirm the served HTML now contains the target, then hand off the re-crawl/Search-Console step. If the platform caches, tell them to clear it.

## When to escalate
If the user actually *can* get code/template access (e.g. Shopify theme editor, Webflow code export, WordPress via SFTP), point them to it and switch to the real adapter — code-level fixes are more robust than CMS-paste and survive theme updates better.
