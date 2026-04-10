# CLAUDE.md — Master System Prompt

## Project Structure

```
ZaDeteto 2.0 Claude/
├── CLAUDE.md                  ← this file (master system prompt)
├── .env                       ← secrets (Supabase keys, future API keys)
├── .env.template              ← shows required vars, no real values
├── directives/                ← natural-language .md SOPs, zero code
│   ├── meta-website.md        ← umbrella: website-building workflows
│   ├── meta-agents.md         ← umbrella: agent/pipeline workflows
│   ├── scrape-google-maps.md
│   ├── enrich-providers.md
│   ├── crawl-website.md
│   ├── google-search-enrichment.md
│   └── run-pipeline.md
├── executions/                ← deterministic .py scripts
│   ├── scrape_google_maps.py
│   ├── enrich_providers.py
│   ├── crawl_website.py
│   ├── google_search_enrichment.py
│   └── run_pipeline.py
├── public_html/               ← 100% upload-safe for domain hosting
│   ├── *.html                 ← website pages
│   ├── js/                    ← browser JS modules
│   ├── video/                 ← hero videos
│   └── brand_assets/          ← logos, fonts, images
├── skills/                    ← reusable AI skill definitions
├── supabase/                  ← DB schema & migrations
├── tmp/                       ← agent scratchpad, checkpoints, test output
├── serve.mjs                  ← local dev server (localhost:3000)
├── screenshot.mjs             ← Puppeteer screenshot tool
└── .claude/agents/            ← sub-agent definitions
```

---

## Always Do First
- **Invoke the `frontend-design` skill** before writing any frontend code, every session, no exceptions.
- After you create or update any execution script (`executions/*.py`), you **must** follow the Sub-Agent Trigger Sequence below. No exceptions.

---

## DOE Framework (Directive-Orchestration-Execution)

| Layer | Location | Format | Rule |
|-------|----------|--------|------|
| **Directive** | `directives/` | `.md` files | Natural language only. Zero code. |
| **Orchestration** | Claude (you) | Conversational | Route decisions, call scripts, handle errors. Never write inline Python. |
| **Execution** | `executions/` | `.py` scripts | Deterministic. One script = one job. Same input = same output. |

- All temporary/checkpoint files go in `tmp/`
- All secrets live in `.env` — never hardcode in scripts
- See `directives/meta-agents.md` for the full script-to-directive mapping

---

## Sub-Agent Trigger Sequence

After creating or modifying any execution script (`*.py`), follow this sequence **automatically** without being asked:

1. **Invoke `script-reviewer`** — pass the directive path and script path. Review the report.
2. **Apply fixes** from any Critical or Important findings.
3. **Invoke `doc-sync`** — it reads the script and updates the matching directive in `directives/`, appending a changelog entry.

This is mandatory for every `.py` change. Do not skip steps. Do not batch multiple scripts.

---

## Self-Annealing Protocol

When an error occurs during script execution:

1. **Diagnose** — Read the full error output. Identify the root cause.
2. **Fix** — Attempt a targeted fix in the execution script.
3. **Re-run** — Verify the fix works.
4. **Update** — Trigger the Sub-Agent Trigger Sequence (reviewer + doc-sync).
5. **Escalate** — Only ask the user if you have exhausted all reasonable fix attempts.

Do not ask the user for help on the first error. Diagnose, fix, verify first.

---

## Frontend Rules

### Reference Images
- If a reference image is provided: match layout, spacing, typography, and color exactly. Swap in placeholder content (images via `https://placehold.co/`, generic copy). Do not improve or add to the design.
- If no reference image: design from scratch with high craft (see guardrails below).
- Screenshot your output, compare against reference, fix mismatches, re-screenshot. Do at least 2 comparison rounds. Stop only when no visible differences remain or user says so.

### Local Server
- **Always serve on localhost** — never screenshot a `file:///` URL.
- Start the dev server: `node serve.mjs` (serves the project root at `http://localhost:3000`)
- Website pages are at `http://localhost:3000/public_html/`
- `serve.mjs` lives in the project root. Start it in the background before taking any screenshots.
- If the server is already running, do not start a second instance.

### Screenshot Workflow
- Puppeteer is installed at `C:/Users/nateh/AppData/Local/Temp/puppeteer-test/`. Chrome cache is at `C:/Users/nateh/.cache/puppeteer/`.
- **Always screenshot from localhost:** `node screenshot.mjs http://localhost:3000/public_html/`
- Screenshots are saved automatically to `./temporary screenshots/screenshot-N.png` (auto-incremented, never overwritten).
- Optional label suffix: `node screenshot.mjs http://localhost:3000/public_html/ label` -> saves as `screenshot-N-label.png`
- `screenshot.mjs` lives in the project root. Use it as-is.
- After screenshotting, read the PNG from `temporary screenshots/` with the Read tool.
- When comparing, be specific: "heading is 32px but reference shows ~24px", "card gap is 16px but should be 24px"
- Check: spacing/padding, font size/weight/line-height, colors (exact hex), alignment, border-radius, shadows, image sizing

### Output Defaults
- Single HTML file, all styles inline, unless user says otherwise
- New website files go in `public_html/`
- Tailwind CSS via CDN: `<script src="https://cdn.tailwindcss.com"></script>`
- Placeholder images: `https://placehold.co/WIDTHxHEIGHT`
- Mobile-first responsive

### Brand Assets
- Always check `public_html/brand_assets/` before designing. It contains logos, fonts, and images.
- If assets exist there, use them. Do not use placeholders where real assets are available.
- If a logo is present, use it. If a color palette is defined, use those exact values — do not invent brand colors.

### Anti-Generic Guardrails
- **Colors:** Never use default Tailwind palette (indigo-500, blue-600, etc.). Pick a custom brand color and derive from it.
- **Shadows:** Never use flat `shadow-md`. Use layered, color-tinted shadows with low opacity.
- **Typography:** Never use the same font for headings and body. Pair a display/serif with a clean sans. Apply tight tracking (`-0.03em`) on large headings, generous line-height (`1.7`) on body.
- **Gradients:** Layer multiple radial gradients. Add grain/texture via SVG noise filter for depth.
- **Animations:** Only animate `transform` and `opacity`. Never `transition-all`. Use spring-style easing.
- **Interactive states:** Every clickable element needs hover, focus-visible, and active states. No exceptions.
- **Images:** Add a gradient overlay (`bg-gradient-to-t from-black/60`) and a color treatment layer with `mix-blend-multiply`.
- **Spacing:** Use intentional, consistent spacing tokens — not random Tailwind steps.
- **Depth:** Surfaces should have a layering system (base -> elevated -> floating), not all sit at the same z-plane.

---

## Ignored Folders
- `cards_insp/` and `docs/` — do not read, reference, or use these folders unless the user explicitly asks you to.

## Hard Rules
- Do not add sections, features, or content not in the reference
- Do not "improve" a reference design — match it
- Do not stop after one screenshot pass
- Do not use `transition-all`
- Do not use default Tailwind blue/indigo as primary color
- `public_html/` must never contain agent logic, .md directives, .py scripts, or .env files
- `directives/` must never contain code — natural language only
