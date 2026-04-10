# CHATGPT.md — Master System Prompt

## Project Structure

```
ZaDeteto 2.0 Claude/
├── directives/                ← natural-language .md SOPs, zero code
│   ├── meta-website.md        ← umbrella: website-building workflows
│   ├── meta-agents.md         ← umbrella: agent/pipeline workflows
│   └── *.md                   ← individual task directives
├── executions/                ← deterministic .py scripts
├── public_html/               ← 100% upload-safe for domain hosting
│   ├── *.html                 ← website pages
│   ├── js/                    ← browser JS modules
│   ├── video/                 ← hero videos
│   └── brand_assets/          ← logos, fonts, images
├── skills/                    ← reusable AI skill definitions
├── supabase/                  ← DB schema & migrations
├── tmp/                       ← scratchpad, checkpoints, test output
├── serve.mjs                  ← local dev server (localhost:3000)
└── screenshot.mjs             ← Puppeteer screenshot tool
```

---

## Always Do First
- **Invoke the `frontend-design` skill** before writing any frontend code, every session, no exceptions.

---

## DOE Framework (Directive-Orchestration-Execution)

| Layer | Location | Format | Rule |
|-------|----------|--------|------|
| **Directive** | `directives/` | `.md` files | Natural language only. Zero code. |
| **Orchestration** | You (the AI) | Conversational | Route decisions, call scripts, handle errors. |
| **Execution** | `executions/` | `.py` scripts | Deterministic. One script = one job. |

- All temporary/checkpoint files go in `tmp/`
- All secrets live in `.env` — never hardcode in scripts
- After modifying any execution script, update the matching directive in `directives/`

---

## Frontend Rules

### Reference Images
- If a reference image is provided: match layout, spacing, typography, and color exactly. Swap in placeholder content (images via `https://placehold.co/`, generic copy). Do not improve or add to the design.
- If no reference image: design from scratch with high craft (see guardrails below).
- Screenshot your output, compare against reference, fix mismatches, re-screenshot. Do at least 2 comparison rounds.

### Local Server
- **Always serve on localhost** — never screenshot a `file:///` URL.
- Start the dev server: `node serve.mjs` (serves the project root at `http://localhost:3000`)
- Website pages are at `http://localhost:3000/public_html/`

### Output Defaults
- Single HTML file, all styles inline, unless user says otherwise
- New website files go in `public_html/`
- Tailwind CSS via CDN: `<script src="https://cdn.tailwindcss.com"></script>`
- Placeholder images: `https://placehold.co/WIDTHxHEIGHT`
- Mobile-first responsive

### Brand Assets
- Always check `public_html/brand_assets/` before designing. It contains logos, fonts, and images.
- If assets exist there, use them. Do not use placeholders where real assets are available.
- If a logo is present, use it. If a color palette is defined, use those exact values.

### Anti-Generic Guardrails
- **Colors:** Never use default Tailwind palette (indigo-500, blue-600, etc.). Pick a custom brand color and derive from it.
- **Shadows:** Never use flat `shadow-md`. Use layered, color-tinted shadows with low opacity.
- **Typography:** Never use the same font for headings and body. Pair a display/serif with a clean sans.
- **Gradients:** Layer multiple radial gradients. Add grain/texture via SVG noise filter for depth.
- **Animations:** Only animate `transform` and `opacity`. Never `transition-all`. Use spring-style easing.
- **Interactive states:** Every clickable element needs hover, focus-visible, and active states.
- **Images:** Add a gradient overlay and a color treatment layer with `mix-blend-multiply`.
- **Spacing:** Use intentional, consistent spacing tokens.
- **Depth:** Surfaces should have a layering system (base -> elevated -> floating).

---

## Ignored Folders
- `cards_insp/` and `docs/` — do not read, reference, or use unless the user explicitly asks.

## Hard Rules
- Do not add sections, features, or content not in the reference
- Do not "improve" a reference design — match it
- Do not stop after one screenshot pass
- Do not use `transition-all`
- Do not use default Tailwind blue/indigo as primary color
- `public_html/` must never contain agent logic, .md directives, .py scripts, or .env files
- `directives/` must never contain code — natural language only
