# Stack Detection

<!-- SYNCED COPY. Authoritative source: vibio-fix/references/stack-detection.md.
     vibio-audit uses this only to identify the stack and pass it to vibio-fix;
     the adapters it mentions (url-only.md, stack-adapters/*) live in vibio-fix.
     If you edit detection logic, update both copies. -->

Before fixing, identify what built the site so you load the right adapter. Detection works from a codebase or from a served URL. Pick the adapter; if nothing matches, use `url-only.md` (URL) or the generic principles + framework docs (unknown code).

## From a codebase

Fast signals, in order:

| Signal | Stack | Adapter |
|---|---|---|
| `next.config.{js,ts,mjs}`, `app/` or `pages/` dir, `.next/` | Next.js | `stack-adapters/nextjs.md` |
| `wp-config.php`, `wp-content/`, theme `functions.php` | WordPress | `stack-adapters/wordpress.md` |
| `*.liquid`, `config/settings_schema.json`, `templates/*.liquid` | Shopify (theme) | `stack-adapters/shopify.md` |
| `astro.config.*`, `.astro` files | Astro | `stack-adapters/static-astro.md` |
| `config.toml`+`content/`+`layouts/` (Hugo), `_config.yml`+`_layouts/` (Jekyll), plain `.html` | Static site | `stack-adapters/static-astro.md` |
| `nuxt.config.*`, `gatsby-config.*`, `svelte.config.*`, `vite.config.*` | Other JS framework | generic principles + that framework's metadata API |

When multiple match (e.g. a headless WP + Next.js frontend), the **rendering layer** owns the `<head>` — fix where the HTML is actually emitted (the Next.js frontend here), and treat the CMS as a data source.

## From a served URL

When you only have a URL, fingerprint the response (route this through `seo-technical` / `seo-firecrawl`, or a quick `curl -sIL` + `curl -sL | head`):

| Fingerprint | Likely stack |
|---|---|
| `x-powered-by: Next.js`, `/_next/static/` asset paths | Next.js |
| `<meta name="generator" content="WordPress …">`, `/wp-content/`, `/wp-json/` | WordPress |
| `x-shopify-stage` / `x-sorting-hat` headers, `cdn.shopify.com` assets, `/cdn/shop/` | Shopify |
| `<meta name="generator" content="Astro/Hugo/Jekyll …">` | Static site |
| `x-powered-by: Express/PHP`, framework cookies | server-rendered app |
| no clear signal | unknown → URL-only mode |

Also note from the URL: does it have a build/deploy you can touch, or is it a hosted platform where you can only edit via the CMS/theme UI? That decides **code-edit vs paste-spec**:
- You can edit code/templates → use the matching adapter.
- You can only edit through a CMS admin (hosted WP.com, Shopify without theme access, Wix/Squarespace, unknown) → use `url-only.md`: give the exact target spec + paste-ready snippet and where to put it.

## Output of this step

State plainly: **"Stack: X. Edit mode: code / template / CMS-paste. Loading adapter: Y."** Then proceed. `vibio-audit` should pass this down so `vibio-fix` doesn't re-detect.
