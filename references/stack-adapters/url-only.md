# Stack Adapter: URL-Only (no code access)

Landing-method layer for when you can't edit source code — no repo, no SFTP, no CMS admin. You can only inspect the live URL and hand the user or their developer precise instructions. Target spec is in `../seo-fix-principles.md`.

This adapter is the most common real-world path for agencies working on client sites hosted on locked platforms (Wix, Squarespace, managed WordPress, custom CMS with no dev access).

## What "URL-only" means

You have: the live URL and `curl` / browser devtools.
You don't have: source code, template files, CMS admin, deployment access.
Your output: exact target HTML + paste-ready snippets + WHERE to paste + what to tell the developer.

## Output format for every fix

For each issue found, provide:
1. **What's wrong** — quoted from the current rendered HTML
2. **What it should be** — the exact HTML that should appear in the rendered output
3. **How to fix it** — platform-specific paste location or developer instruction
4. **How to verify** — the `curl | grep` command to confirm after the fix

## Recipe templates for common fixes

### Title & meta description
**Problem:** `<title>` is the site name on every page; no unique meta description.
**Fix snippet:**
```html
<title>Primary Keyword — What This Page Offers | Brand Name</title>
<meta name="description" content="150-160 character description with primary keyword, benefit statement, and soft call to action.">
```
**Paste location:**
- Wix: SEO Settings → SEO Basics → "Title tag" and "Meta description" fields per page
- Squarespace: Page Settings → SEO → "SEO Title" and "SEO Description"
- WordPress (no code): Yoast/Rank Math SEO box per page → "SEO Title" and "Meta description"
- Custom CMS: ask developer to add to `<head>` per page template, driven by a CMS field

### Canonical
**Problem:** missing self-referential canonical.
**Fix snippet:**
```html
<link rel="canonical" href="https://www.example.com/this-page-path/">
```
**Paste location:**
- Wix: auto-generated, check SEO Settings → Advanced → "Canonical URL"
- Squarespace: auto-generated from page URL
- Custom: ask developer to add to `<head>`, generated from the page's canonical URL

### Structured data (Organization + WebSite)
**Problem:** no Organization or WebSite JSON-LD (brand name won't show in SERP).
**Fix snippet:**
```html
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Organization",
 "name":"Full Legal Company Name Ltd.",
 "alternateName":"ShortBrand",
 "url":"https://www.example.com",
 "logo":"https://www.example.com/logo.png"}
</script>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"WebSite",
 "name":"Full Legal Company Name Ltd.",
 "alternateName":"ShortBrand",
 "url":"https://www.example.com"}
</script>
```
**Paste location:**
- Wix: Settings → Custom Code → Add → "Head" section, paste in the "HTML / embed code" field
- Squarespace: Settings → Advanced → Code Injection → "Header"
- WordPress: Appearance → Theme File Editor → `header.php` (before `</head>`), or plugin's custom code field
- Custom: ask developer to add to site-wide `<head>`

### OG tags
**Problem:** `og:image` is a square logo but declared as 1200×630.
**Fix snippet:**
```html
<meta property="og:site_name" content="Full Legal Company Name Ltd.">
<meta property="og:image" content="https://www.example.com/og-image-1200x630.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
```
**Paste location:** same as structured data above (site-wide `<head>`)

### robots.txt
**Problem:** no sitemap reference, or blocking critical paths.
**Fix snippet:**
```
User-agent: *
Allow: /
Disallow: /api/
Disallow: /admin/
Sitemap: https://www.example.com/sitemap.xml
```
**Paste location:**
- Wix: auto-generated, limited editing
- Squarespace: auto-generated
- Custom hosting: upload to web root as `robots.txt`
- Ask developer to place at site root, served as `text/plain`

### llms.txt
**Problem:** no llms.txt for AI crawler discovery.
**Fix snippet — save as `/llms.txt`:**
```
# Brand Name

> One-line description of the business and what it offers.

## Products
- [Product Category A](https://www.example.com/category-a): Description of product category.
- [Product Category B](https://www.example.com/category-b): Description.

## Company
- [About](https://www.example.com/about)
- [Contact](https://www.example.com/contact): email@example.com
```
**Paste location:** upload to web root. If locked platform prevents file upload, ask developer or use a reverse proxy / CDN edge function.

## Platform-specific paste locations

| Platform | Title/Meta | OG/Social | Structured Data | robots.txt |
|---|---|---|---|---|
| Wix | SEO Settings per page | Settings → Custom Code → Head | Settings → Custom Code → Head | Auto (limited) |
| Squarespace | Page Settings → SEO | Settings → Code Injection → Header | Settings → Code Injection → Header | Auto |
| WordPress (admin) | Yoast/Rank Math per page | Plugin Social settings | Plugin + Custom Code | Plugin Tools → File Editor |
| Shopify (admin) | Per-product "Search engine listing" | theme.liquid | theme.liquid | templates/robots.txt.liquid |
| Webflow | Page Settings → SEO | Site Settings → Custom Code → Head | Site Settings → Custom Code → Head | Project Settings → SEO |
| Custom CMS | CMS field → developer wires to template | Ask developer for `<head>` access | Ask developer for `<head>` access | Ask developer for web root |

## Verification
After the user/developer applies the change, re-fetch and grep:
```bash
curl -sL https://example.com/ | grep -oiE 'property="og:site_name"[^>]*|"@type":"(Organization|WebSite)"|rel="canonical"[^>]*|name="description"[^>]*'
```
Confirm the intended tags appear. If not, the change wasn't applied correctly or the platform is caching — clear cache and re-check.
