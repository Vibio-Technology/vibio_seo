# Stack Detection

Before any FIX or code-level AUDIT, determine the stack and edit mode. The fix target is always the same (→ `seo-fix-principles.md`), but the landing method differs radically by stack. This file tells you which adapter to load.

## Detection by codebase (local project)

### Next.js (App Router)
- `next.config.ts` or `next.config.mjs` or `next.config.js` exists
- `app/` directory with `page.tsx` / `layout.tsx`
- `package.json` has `next` dependency
- **Adapter:** `stack-adapters/nextjs.md`
- **Edit mode:** code (TypeScript/TSX, build verification)

### Next.js (Pages Router)
- `pages/` directory with `_app.tsx` / `index.tsx`
- `next.config.js` exists
- **Adapter:** `stack-adapters/nextjs.md` (App Router recipes adapt; principles same)

### WordPress
- `wp-config.php` exists
- `wp-content/` directory
- **Adapter:** `stack-adapters/wordpress.md`
- **Edit mode:** template (PHP theme files) or CMS-paste (plugin UI + per-post SEO boxes)
- **Plugin detection:** check rendered HTML for `<!-- This site is optimized with the Yoast SEO plugin -->` (Yoast) or `<!-- Search engine optimization by Rank Math -->` (Rank Math) or `aioseo` meta (All in One SEO). No plugin signal = raw theme.

### Shopify
- `layout/theme.liquid` exists
- `templates/` directory with `.liquid` files
- `config/settings_schema.json`
- **Adapter:** `stack-adapters/shopify.md`
- **Edit mode:** template (Liquid, Online Store → Themes → Edit code)

### Astro
- `astro.config.mjs` exists
- `src/layouts/` or `src/pages/` with `.astro` files
- **Adapter:** `stack-adapters/static-astro.md`
- **Edit mode:** code (Astro components, build verification)

### Hugo
- `config.toml` or `config.yaml` or `hugo.toml`
- `layouts/` directory
- **Adapter:** `stack-adapters/static-astro.md`
- **Edit mode:** code (Go templates, build verification)

### Jekyll
- `_config.yml` exists
- `_layouts/` or `_includes/` directories
- **Adapter:** `stack-adapters/static-astro.md`
- **Edit mode:** code (Liquid templates, build verification)

### Plain HTML / unknown static
- `index.html` files, no framework config
- **Adapter:** `stack-adapters/static-astro.md`
- **Edit mode:** code (direct HTML editing)

## Detection by live URL (no code access)

### Signal: WordPress
- `/wp-content/` paths in page source
- `/wp-admin/` accessible (redirects to login)
- Generator meta: `<meta name="generator" content="WordPress ...">`
- **Edit mode:** CMS-paste if client has WP admin; otherwise URL-only

### Signal: Shopify
- `myshopify.com` in domain or source
- Shopify CDN URLs (`cdn.shopify.com`)
- **Edit mode:** template if client has theme access; otherwise URL-only

### Signal: Wix / Squarespace / Webflow
- Wix: `wix.com` or `_wix` in source
- Squarespace: `squarespace.com` in source
- Webflow: `webflow.io` in source, `data-wf-` attributes
- **Edit mode:** URL-only (locked platforms — paste-ready snippets for available fields)

### Signal: Next.js
- `__NEXT_DATA__` JSON in page source
- `.next` in asset URLs

### Signal: No framework detected
- Generic HTML, no CMS signals
- **Edit mode:** URL-only
- **Adapter:** `stack-adapters/url-only.md`

## Edit mode decision tree

```
Have local codebase?
├─ YES → code mode (use stack adapter, edit source, run build/lint)
└─ NO → live URL only
    ├─ Client has admin access (WP admin, Shopify admin)?
    │   ├─ YES → CMS-paste mode (guide through plugin UI / theme settings)
    │   └─ NO → URL-only mode (provide paste-ready snippets + exact paste location)
    └─ Locked platform (Wix / Squarespace / hosted WP without code)?
        └─ URL-only mode
```

When in URL-only mode: provide exact HTML snippets the user can paste into the limited fields they have access to (meta description box, header code injection, etc.), with clear instructions on WHERE to paste.
