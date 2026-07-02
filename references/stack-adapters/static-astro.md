# Stack Adapter: Static sites (Astro / Hugo / Jekyll / plain HTML)

Landing-method layer for static-site generators and hand-written HTML. Target spec is in `../seo-fix-principles.md`. This is the adapter **closest to the principles themselves** — you edit templates/layouts that produce HTML directly, with no plugin or platform in between. The pattern is the same across generators; only the templating syntax differs.

## Where the `<head>` lives

| Generator | Layout / head file | Per-page front-matter |
|---|---|---|
| Astro | `src/layouts/*.astro`, a `<BaseHead>` component | frontmatter in `.astro` / `.md` |
| Hugo | `layouts/_default/baseof.html`, `layouts/partials/head.html` | front matter in `content/**` |
| Jekyll | `_layouts/default.html`, `_includes/head.html` | YAML front matter in pages/posts |
| 11ty | `_includes/layouts/base.njk` | front matter |
| Plain HTML | each file's `<head>` (or a shared include if using SSI/build) | inline |

General approach: make the layout accept per-page `title`/`description`/`image`/`canonical` variables with sensible site-wide defaults, so every page gets correct tags without per-page boilerplate.

## Recipes

### Title & meta description
Drive from front matter with a fallback:
- Astro: `<title>{title ?? site.title}</title>`, `<meta name="description" content={description ?? site.description}>`.
- Hugo: `<title>{{ .Title }} | {{ .Site.Title }}</title>`, `<meta name="description" content="{{ .Description | default .Site.Params.description }}">`.
- Jekyll: `{{ page.title | default: site.title }}`, `{{ page.description | default: site.description }}`.

### Canonical
Build an absolute canonical from the site base URL + page path in the head partial:
- Astro: `<link rel="canonical" href={new URL(Astro.url.pathname, site.url)}>`.
- Hugo: `<link rel="canonical" href="{{ .Permalink }}">`.
- Jekyll: `<link rel="canonical" href="{{ page.url | absolute_url }}">`.
Set the site base URL correctly (`site` in astro.config / `baseURL` in Hugo / `url` in Jekyll `_config.yml`) — a wrong base URL breaks every canonical and OG URL.

### Structured data
Add `Organization` + `WebSite` JSON-LD once in the base layout (interpolate site config: legal name, logo, url). Add `Article`/`BlogPosting` + `BreadcrumbList` in the post layout from front matter (title, date, author, image). Keep the logo square for `Organization.logo`. Validate with `seo-schema`.

### OG / Twitter + brand site-name
In the head partial, emit `og:title/description/url/type/image` and `og:site_name` = the full legal/brand name from site config. Default OG image = a landscape 1200×630 asset; per-page override from front matter. Set `twitter:card` = `summary_large_image`.

### robots.txt & sitemap
- Sitemap: Astro `@astrojs/sitemap` integration; Hugo emits `sitemap.xml` natively; Jekyll `jekyll-sitemap` plugin. Ensure it's generated and referenced in `robots.txt`.
- `robots.txt`: a static file in `public/` (Astro) / `static/` (Hugo) / root (Jekyll). Allow `/`, reference the sitemap, set host.

### Indexability
Static sites rarely emit accidental `noindex` — but check the base layout for a leftover `<meta name="robots" content="noindex">` (common in a "coming soon" template that shipped to prod). Check hosting (Netlify/Vercel/Cloudflare Pages) isn't password-protecting or `noindex`-ing preview deploys that became prod.

### Images
Use the generator's image pipeline (Astro `<Image>`, Hugo image processing) for WebP + dimensions. Ensure every `<img>`/component has descriptive `alt` from front matter or content. Use `seo-images` for depth.

### llms.txt
Easiest stack for this — add a static `/llms.txt` in `public/`/`static/`, or template it from the content collection so it lists all pages (Astro: an endpoint `src/pages/llms.txt.ts`; Hugo: a custom output format). Follow the llmstxt.org structure.

## Verification
Build, then grep the output dir (no server needed):
```bash
# Astro: npm run build → dist/ ; Hugo: hugo → public/ ; Jekyll: jekyll build → _site/
grep -roiE 'property="og:site_name"[^>]*|"@type":"(Organization|WebSite)"|rel="canonical"[^>]*' <output-dir>/index.html
grep -rli 'noindex' <output-dir> || echo "no stray noindex — good"
```
Then deploy and re-fetch the live URL to confirm the host serves what you built. SERP changes wait on re-crawl.
