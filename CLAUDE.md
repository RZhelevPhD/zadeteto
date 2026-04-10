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
- After you create or update any HTML, CSS, or JS file in `public_html/`, you **must** follow the Frontend Review Trigger below. No exceptions.

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

## Frontend Review Trigger

After creating or modifying any frontend file (`*.html`, `*.css`, or `*.js`) inside `public_html/`, follow this sequence **automatically** without being asked:

1. **Invoke `frontend-reviewer`** — pass the path(s) to the changed file(s). Review the report.
2. **Apply fixes** from any Critical or Important findings.
3. **Re-invoke `frontend-reviewer`** if Critical findings were fixed, to verify they are resolved.

This is mandatory for every frontend file change in `public_html/`. Do not skip steps.

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

### Screenshot Workflow (Chrome Headless — THE way to take screenshots)

**Node.js is NOT installed on this machine.** Do not try `node serve.mjs` or `node screenshot.mjs` — they will fail with "node: command not found". Use Chrome headless directly instead. It reads `file://` URLs fine (no local server needed) and works out of the box.

**Chrome executable path:** `/c/Program Files/Google/Chrome/Application/chrome.exe`

**Screenshots output folder:** `/c/tmp/` (the project `temporary screenshots/` folder has a space in its path which Chrome's `--screenshot` flag rejects, so use `/c/tmp/` instead and read PNGs from there).

**Desktop screenshot (1920x1080):**
```bash
"/c/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --disable-gpu --hide-scrollbars \
  --window-size=1920,1080 \
  --screenshot="C:/tmp/desktop-index.png" \
  "file:///J:/My%20Drive/%21WIP%20VS%20Code%20%26%20Antigravity%20-10.4.2026/ZaDeteto%202.0%20Claude/public_html/index.html"
```

**Mobile screenshot (iPhone 12 Pro = 390x844):**
```bash
"/c/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --disable-gpu --hide-scrollbars \
  --window-size=390,844 \
  --screenshot="C:/tmp/mobile-index.png" \
  "file:///J:/My%20Drive/%21WIP%20VS%20Code%20%26%20Antigravity%20-10.4.2026/ZaDeteto%202.0%20Claude/public_html/index.html"
```

**URL encoding:** the project path contains spaces, `!`, and `&` which MUST be percent-encoded in the `file://` URL — otherwise Chrome silently fails. Use `%20` for spaces, `%21` for `!`, `%26` for `&`.

**Reading the screenshot:** use the `Read` tool on `C:/tmp/<filename>.png` (NOT relative path — absolute path required).

**Ignore these Chrome stderr messages** — they're benign and don't prevent the screenshot:
- `ERROR:chrome\browser\extensions\external_registry_loader_win.cc:161 ...`

**Known limitation:** `file://` URLs cannot load Supabase data (CORS), so mobile search cards will appear empty. That's expected — verify structure and nav, not data.

**Always screenshot before pushing frontend changes.** The deployed site has bitten us multiple times when I didn't verify locally first.

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
