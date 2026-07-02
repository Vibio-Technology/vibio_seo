# Stack Adapter: Shopify

Landing-method layer for Shopify. Target spec is in `../seo-fix-principles.md`. Shopify auto-generates a lot (canonical, sitemap, basic meta) but the defaults are weak and the customization lives in **Liquid theme templates** + **theme settings** + **per-resource metafields**.

## Edit mode

- **Theme code access** (Online Store → Themes → Edit code) → edit `.liquid` files in `layout/`, `templates/`, `sections/`, `snippets/`. This is the main path.
- **No theme access / app-only** → CMS-paste: use the SEO fields in the admin (Online Store → Preferences, and per-product/collection "Search engine listing"), plus an SEO app. Fall back to `url-only.md` for anything not exposed.

## What Shopify does automatically (don't fight it)
- Canonical tags: auto, self-referential. Don't hand-add duplicates.
- `sitemap.xml`: auto at `/sitemap.xml` (+ child sitemaps). Can't edit directly; control inclusion via product/collection/page publish status.
- `robots.txt`: editable since 2021 via `templates/robots.txt.liquid`.

## Recipes

### Title & meta description
- Global: `layout/theme.liquid` `<head>` usually has `<title>{{ page_title }}{% ... %}</title>` and `{% if page_description %}<meta name="description" content="{{ page_description }}">{% endif %}`.
- Per-resource: the "Search engine listing" edit box on each product/collection/page/blog post sets `page_title` + `page_description`.
- Fix weak title template in `theme.liquid` (e.g. include shop name as suffix, not prefix).

### Structured data
- Shopify themes vary; many emit basic `Product` JSON-LD via `{{ product | structured_data }}` or hand-rolled in `sections/product-template.liquid`. Verify `Product` + `Offer` + `AggregateRating` render on product pages.
- Add site-wide `Organization` + `WebSite` JSON-LD in `theme.liquid` `<head>` (Shopify does NOT add these by default — this is the common gap):
  ```liquid
  <script type="application/ld+json">
  {"@context":"https://schema.org","@type":"Organization",
   "name":{{ shop.name | json }},
   "url":{{ shop.url | json }},
   "logo":{{ 'logo.png' | asset_url | prepend: 'https:' | json }}}
  </script>
  <script type="application/ld+json">
  {"@context":"https://schema.org","@type":"WebSite",
   "name":{{ settings.legal_name | default: shop.name | json }},
   "alternateName":{{ shop.name | json }},
   "url":{{ shop.url | json }}}
  </script>
  ```
- Validate with `seo-schema`. For Shopping/marketplace depth use `seo-ecommerce`.

### OG / Twitter + brand site-name
- In `theme.liquid` `<head>` ensure `og:title`, `og:description`, `og:url`, `og:type`, `og:image`, and `og:site_name` = full legal name (set a `settings.legal_name` in `settings_schema.json` so it's editable). Shopify's default `og:site_name` is just `shop.name`.
- OG image: many themes use the product/collection featured image; for the homepage set a landscape 1200×630 default in theme settings.

### robots.txt
Edit `templates/robots.txt.liquid` to add rules (e.g. disallow `/cart`, `/checkout`, internal search `/search`, tag filters) while keeping Shopify's defaults via `{% layout none %}{{ content_for_header }}{% endlayout %}`.

### Faceted/duplicate URLs
Collection filter/sort params create duplicates — rely on Shopify's auto-canonical, and avoid linking to parameterized URLs internally. For large catalogs, use `seo-ecommerce` + `seo-technical` to assess index bloat.

### Images
`alt` set per image in the admin or via `{{ image.alt }}` in Liquid. Shopify serves responsive `image_url` with `width:`; ensure templates pass sensible sizes.

### llms.txt
No native route. Adding `templates/llms.txt.liquid` won't work (Shopify only allows the robots template). Use an app, reverse-proxy/edge worker, or host `llms.txt` on the apex via CDN. If none possible, note the limitation.

## Verification
Fetch the live storefront URL and grep rendered HTML; preview themes via the theme preview URL before publishing:
```bash
curl -sL https://shop.example.com/ | grep -oiE 'property="og:site_name"[^>]*|"@type":"(Organization|WebSite|Product)"|rel="canonical"[^>]*'
```
Publish the theme (or use preview) — edits to an unpublished theme won't show on the live URL. SERP changes wait on re-crawl.
