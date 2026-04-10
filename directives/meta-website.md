# Metadirective: Website Building

## Scope
All tasks related to building, maintaining, and deploying the ZaDeteto public-facing marketing website.

## Key Rules
- All website assets live in `public_html/` — HTML, JS (`public_html/js/`), video (`public_html/video/`), brand assets (`public_html/brand_assets/`)
- `public_html/` must be 100% upload-safe for domain hosting — no agent logic, no .md directives, no .py scripts, no .env files
- Frontend design rules are defined in `CLAUDE.md` (root) — invoke the `frontend-design` skill before writing any frontend code
- Screenshot workflow uses `serve.mjs` (serves project root) and `screenshot.mjs` (Puppeteer)
- Supabase client is initialized in `public_html/js/supabase-init.js` (anon key, RLS-protected)
- Forms submit via `public_html/js/api-stub.js` (offline-first, falls back to localStorage)

## Website Pages
| Page | File | Purpose |
|------|------|---------|
| Homepage | `public_html/index.html` | Hero video, value proposition |
| Search | `public_html/search.html` | Provider search/listing |
| Listing detail | `public_html/listing.html` | Individual provider page |
| Business dashboard | `public_html/business-dashboard.html` | Business user panel |
| Business login | `public_html/business-login.html` | Business authentication |
| Contact | `public_html/contacts.html` | Contact form |
| Partners | `public_html/partners.html` | Partner application |
| Pricing | `public_html/pricing.html` | Plan pricing |
| Privacy | `public_html/privacy.html` | Privacy policy |
| Report | `public_html/report.html` | Report violation |
| Terms | `public_html/terms.html` | Terms of service |
| Cookies | `public_html/cookies.html` | Cookie policy |

## Shared JS Modules
| Script | Purpose |
|--------|---------|
| `js/nav-inject.js` | Global nav/footer injection |
| `js/cookie-banner.js` | GDPR consent banner |
| `js/analytics-loader.js` | Conditional analytics loading |
| `js/supabase-init.js` | Supabase client init |
| `js/api-stub.js` | Form submission API |

## Brand Assets
Located in `public_html/brand_assets/` — logos (SVG), fonts (Inter + PT Serif), hero poster, OG image. Always check this folder before designing; use real assets, never placeholders where brand files exist.

## Anti-Generic Design Guardrails
See `CLAUDE.md` for the full list. Key points: no default Tailwind palette, no flat shadows, pair display/serif with sans fonts, layered gradients with texture, animate only transform/opacity.

## Deployment
The `public_html/` folder can be uploaded directly to hosting. No build step required — all files are static HTML with inline styles and CDN dependencies (Tailwind, Supabase JS).
