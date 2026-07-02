# Stack Adapter: WordPress

Landing-method layer for WordPress. Target spec ("what correct looks like") is in `../seo-fix-principles.md`. WordPress almost always has an SEO plugin doing the heavy lifting — **work through the plugin, don't hand-write tags that the plugin will overwrite.**

## First: detect the SEO plugin

| Signal | Plugin | Where it lives |
|---|---|---|
| `<!-- This site is optimized with the Yoast SEO plugin -->` in HTML | Yoast SEO | `wp-content/plugins/wordpress-seo/` |
| `<!-- Search engine optimization by Rank Math -->` | Rank Math | `wp-content/plugins/seo-by-rank-math/` |
| `aioseo`/`_aioseo_` meta | All in One SEO | `wp-content/plugins/all-in-one-seo-pack/` |
| none | raw theme | `header.php` / `wp_head` hook |

The plugin owns title templates, meta description, canonical, OG/Twitter, and most JSON-LD. Edit per-post values in the post editor's SEO box, and global templates in the plugin's Search Appearance / Titles & Meta settings. Theme-level `functions.php` edits are the fallback when there's no plugin or for things the plugin doesn't cover.

## Edit mode

- **Full code/SFTP access** → edit `functions.php`, theme templates (`header.php`, `single.php`, `page.php`, `archive.php`), and `mu-plugins/`. You can add filters/hooks programmatically.
- **Admin-only (hosted WP.com, no theme editor)** → this is effectively CMS-paste: configure via the plugin UI and per-post SEO boxes. If a tag truly can't be set via UI, fall back to `url-only.md` guidance.

## Recipes

### Title & meta description
- Per-post: set in the Yoast/Rank Math box under each post/page.
- Global templates: Search Appearance (Yoast) / Titles & Meta (Rank Math). Pattern e.g. `%%title%% %%sep%% %%sitename%%`.
- Raw theme (no plugin): in `functions.php`, ensure `add_theme_support('title-tag')`; add description via a `wp_head` action echoing `<meta name="description">` from an excerpt/custom field.

### Canonical
Plugins emit self-referential canonicals automatically. Override per-post in the Advanced section of the SEO box only for genuine duplicates. Don't hand-add `<link rel="canonical">` in the theme if a plugin is active — you'll get duplicates.

### Structured data (Organization + WebSite + page types)
- Yoast/Rank Math emit a `@graph` with `Organization`/`WebSite`/`WebPage`/`BreadcrumbList` automatically — fill in Organization name (use the full legal name), logo, social profiles in the plugin's settings (Knowledge Graph / Local SEO).
- `Product` → use WooCommerce (emits Product/Offer schema) + the plugin.
- `FAQPage`/`HowTo` → Yoast/Rank Math blocks in the Gutenberg editor.
- Validate the rendered output with the `seo-schema` skill.

### OG / Twitter + brand site-name
- Set the Organization/Site name to the **full legal name** in the plugin's Knowledge Graph settings → this populates `og:site_name` and `WebSite` JSON-LD `name` (fixes the bare-domain SERP site-name).
- Social image: set the default OG image (Social settings) to a landscape 1200×630 image. Per-post override in the SEO box's Social tab.
- Put the full legal company name in the homepage meta description (and visible copy) for query highlighting.

### robots & sitemap
- Sitemap: Yoast → `/sitemap_index.xml`; Rank Math → `/sitemap_index.xml`. Don't also enable a second sitemap plugin.
- `robots.txt`: edit via the plugin's Tools → File editor, or a physical `robots.txt`. Ensure `/wp-admin/` disallowed (but `/wp-admin/admin-ajax.php` allowed), sitemap referenced.
- Indexability: the #1 WP gotcha is **Settings → Reading → "Discourage search engines"** being checked — it injects site-wide `noindex`. Check this first. Also check per-post "noindex" toggles in the SEO box.

### Images
- `alt` text is set in the Media Library / block editor per image. Bulk-fix with the plugin's tools or a dedicated alt-text plugin.
- Use a performance plugin (or theme support) for WebP + lazy-load.

### llms.txt
No native support. Add a physical `/llms.txt` at web root, or a tiny `mu-plugin` that hooks an `init` rewrite rule to serve it. Generate its content from the published pages/menu.

## Verification
Fetch the live URL and grep the rendered HTML (not PHP source — the plugin runs at render time):
```bash
curl -sL https://example.com/ | grep -oiE 'name="description"[^>]*|rel="canonical"[^>]*|property="og:site_name"[^>]*|"@type":"(Organization|WebSite)"'
curl -sL https://example.com/ | grep -i 'noindex'   # must be empty for indexable pages
```
Clear any caching plugin / CDN cache after changes, or you'll verify a stale page. SERP changes still wait on re-crawl.
