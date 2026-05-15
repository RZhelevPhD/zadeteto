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
├── docs/
│   ├── reference-index.md     ← AHDM library catalog (domain tags, frameworks, routing)
│   ├── cheatsheets/           ← extracted framework summaries (gitignored)
│   └── AH+DM reference docs/ ← private source PDFs/DOCX (gitignored, never publish)
├── skills/                    ← reusable AI skill definitions
├── supabase/                  ← DB schema & migrations
├── tmp/                       ← agent scratchpad, checkpoints, test output
├── serve.mjs                  ← local dev server (localhost:3000)
├── screenshot.mjs             ← Puppeteer screenshot tool
└── .claude/agents/            ← sub-agent definitions
    ├── ahdm.md                ← AHDM orchestrator (routes to domain subagents)
    ├── ahdm-{domain}.md       ← 8 domain subagents (offers, leads, ads, closing, proof, brand, launch, ops)
    ├── doc-sync.md
    ├── script-reviewer.md
    └── frontend-reviewer.md
```

---

## Always Do First
- **Invoke the `frontend-design` skill** before writing any frontend code, every session, no exceptions.
- **Load `skills/bulgarian-writing.md`** BEFORE drafting any Bulgarian-language output. See Bulgarian Copy Rules below, no exceptions.
- After you create or update any execution script (`executions/*.py`), you **must** follow the Sub-Agent Trigger Sequence below. No exceptions.
- After you create or update any HTML, CSS, or JS file in `public_html/`, you **must** follow the Frontend Review Trigger below. No exceptions.
- After you generate Bulgarian copy longer than ~3 sentences destined for a file (HTML, CSV, Markdown, email draft) or for a user-facing plan, you **must** follow the Bulgarian Copy Gate below. No exceptions.

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

## QA Trigger

When the user asks for any of:
- A QA pass, link check, journey check, role-gate verification, form audit, accessibility/responsive check, or Supabase data-integrity check
- "How does the partner journey look?", "Is anything broken on the parent flow?", "Did anything regress?"

invoke the `qa` orchestrator (`.claude/agents/qa.md`). It:
1. Confirms scope (full pass vs subset).
2. Invokes `executions/qa_run.py` for the deterministic pillars (links, forms, roles, craft, data) into a timestamped report directory under `tmp/qa-reports/<ts>/`.
3. Routes journey walkthroughs to the `qa-journeys` subagent (Chrome-headless screenshots).
4. Synthesises one consolidated `index.md` with severity-ranked findings.
5. Routes the synthesis through the `bg-writing` gate if it contains >3 sentences of Bulgarian.

The full pillar list and routing table is in `directives/meta-qa.md`. The QA stack is read-only — it reports findings, never auto-fixes. Do not invoke individual `qa_*.py` scripts ad-hoc; go through the orchestrator so a single timestamped report directory is produced.

---

## cbstory Trigger

When the user asks for any of:

- A signature / origin / founder story; a video script; a webinar or talk outline; a lead magnet (guide, checklist, mini-course); offer-page copy; a moment-of-pitch transition; an offer name
- "Conversion story" / "infusion" / "bulletproof offer" / "offer transition" by name
- EN+BG creative copy that pulls from the personal stories vault (`BRANDING/stories-vault/`)

invoke the `cbstory` orchestrator (`.claude/agents/cbstory.md`). It:

1. Loads `docs/zd-context.md` and `skills/bulgarian-writing.md`.
2. Routes to one or more framework subagents (`cbstory-conversion`, `cbstory-infusion`, `cbstory-offer`, `cbstory-script`) per the routing table in `docs/cb-reference-index.md`.
3. Pulls the right personal story via `cbstory-vault` (which uses `docs/stories-vault-index.md`, regenerated by `executions/index_stories_vault.py` when stale).
4. Hands the bundle to `cbstory-writer`, which produces the actual EN+BG deliverable plus a Delivery sheet for video scripts (pacing, pause/emphasis marks, BG-accent EN pronunciation, BG stress marks).
5. Routes the BG section through the `bg-writing` gate.
6. Returns one artifact, structured as defined in `directives/meta-cbstory.md`.

Unlike AHDM (which audits) and BD (which coaches), `cbstory` *produces*. The orchestrator ends with a deliverable file, not a plan.

**Isolation rule (v1):** `cbstory` does NOT call `ahdm-*` or `bd-*` subagents, and AHDM / BD do NOT call `cbstory-*`. If a job needs both audit and production, the user invokes them sequentially. Both orchestrators independently call the shared `bg-writing` gate.

---

## punchup Trigger

When the user asks for any of:

- "Punch up", "make this funnier", "add humour", "comedy copy", "make it funny", "разчупи го", "по-забавно"
- "Funny is Money" / "Social Success Machine" by name
- A specific reel-format request: "trying to explain X to your parents", "POV", "teaching an alien", "5 signs you're", "X 10 years ago vs now", etc.
- A specific device request: "joke thirds", "bracketed aside", "comic comparison", "misdirection", "parody"

invoke the `punchup` orchestrator (`.claude/agents/punchup.md`). It:

1. Loads `docs/zd-context.md`, `skills/funny-marketing.md`, and `skills/bulgarian-writing.md` (if BG is in scope).
2. Routes to one or more audit subagents (`punchup-truth`, `punchup-toolkit`, `punchup-jokes`, `punchup-ads`, `punchup-copy`, `punchup-platform`) per the routing table in `docs/funny-reference-index.md`. `punchup-truth` runs first; the rest fan out in parallel.
3. Runs `punchup-safety` last to apply Golden / Silver Rule verdicts (DROP / RISKY / SAFE).
4. Hands the ranked opportunity stack to `punchup-writer`, which produces 2-3 punched-up variants per opportunity (EN+BG side-by-side when both are requested), applying Framework Fidelity (the writer folds in the legacy jts-01-comedy-creative rule + 4-phase joke creation process).
5. Routes BG variants through the `bg-writing` gate.
6. Returns one artifact, structured as defined in `directives/meta-punchup.md`.

Like `cbstory`, `punchup` *produces* — it ends with finished punched-up variants the user can ship, not a plan.

**Isolation rule (v1):** `punchup` does NOT call `ahdm-*`, `bd-*`, or `cbstory-*` subagents, and the other three orchestrators do NOT call `punchup-*`. If a job needs both audit (AHDM) and punch-up, OR both narrative production (`cbstory`) and punch-up, the user invokes them sequentially. All four orchestrators independently call the shared `bg-writing` gate.

---

## Punch-up Suggestion Trigger

After any of the following is created or substantially modified, **before marking the task complete**, ask the user one question — "Искаш ли да пусна punch-up минаване?" (or "Want me to run a punch-up pass?" if the user has been chatting in English) — and only proceed once they answer yes/no:

- An ad / ad copy block (FB, IG, LinkedIn, Google).
- A VSL or video script (any length).
- A landing-page hero, body section, or full landing page in `public_html/`.
- An email body for a campaign or sequence.
- A long-form social post (>3 sentences) destined for a file or a publish queue.
- A lead-magnet body, sales-page section, or webinar slide-deck copy.
- An image / meme caption longer than ~10 words.
- Any cbstory deliverable that is one of the shapes above (fired automatically at the end of the cbstory turn — main thread asks once cbstory hands the artifact back).

If yes → invoke the `punchup` orchestrator with the file path or pasted copy.
If no → continue without further mention.

**Do NOT fire** on: nav labels, button microcopy ≤5 words, error messages, log lines, internal docs, README content, code comments, plan files, audit plans (AHDM / BD output), trust-critical / legal copy, or anything in `directives/` / `tmp/`. The list of zones the punch-up itself refuses to enter (CTA, guarantee, proof, offer stack, legal) is in `directives/meta-punchup.md` under "Never-Punch Zones".

This is a soft trigger — it asks rather than auto-runs. The asking is itself part of the workflow: the user gets to decide every time whether the asset earns a punch-up pass.

---

## Bulgarian Copy Rules

Failure mode this addresses: the `bulgarian-writing` skill sometimes did not fire and Claude produced translationese (stiff, English-syntax Bulgarian with em-dashes, corporate filler, „не X. Y." drama formulas, reversed word order). The rules below make the skill fire and add a deterministic review pass.

### Positive layer — load the skill BEFORE drafting

Before producing any Bulgarian text — including orchestrator plans (AHDM, BD), page copy in `public_html/`, CSV columns, email drafts, captions, headings, ad lines, UI strings — read `skills/bulgarian-writing.md` in full if it is not already in the current context window. This is not optional. The skill must be in context AT GENERATION TIME, not only at review time.

Hold these negative prompts in mind while drafting (full list in the skill):

- Never use em-dash (`—`). Ever. Use comma, period, colon, or parentheses.
- Never use corporate filler: „в днешния динамичен свят", „широка гама", „иновативни решения", „с цел да", „по отношение на", „в рамките на", „с оглед на", „предоставяме", „водещ доставчик", „високо качество на услугата".
- Never use reversed word order („Разходи прозрачни" is English-syntax; the BG order is „Прозрачни разходи").
- Never use explicit подлог Аз/Ние/Вие + aux verb at sentence start unless you need contrast. BG is pro-drop.
- Never mix „ти" and „Вие" in the same artifact.
- Never use the „не X. Y." drama formula where „не X, а Y" in one sentence reads naturally.
- Never translate English idioms literally.
- Prefer verbs over abstract nouns („Получаваш достъп" > „Получаване на достъп").

### Negative layer — run the `bg-writing` subagent AFTER drafting

The `bg-writing` subagent at `.claude/agents/bg-writing.md` is a Bulgarian language-quality reviewer. It reads `skills/bulgarian-writing.md`, scans for all banned patterns, optionally runs the deterministic `executions/validate_bg_writing.py` linter, and returns a verdict plus rewrite.

**Bulgarian Copy Gate** — invoke `bg-writing` automatically, without being asked, in these cases:

1. AHDM or BD orchestrator finished drafting a Bulgarian plan / copy (the orchestrators handle this in their own Step 6.5 — no action from the main thread).
2. Main thread is writing Bulgarian copy to `public_html/*.html` with a diff that adds >3 sentences of Bulgarian.
3. Main thread is writing or modifying any Bulgarian text column in a CSV. For CSVs, ALSO run:
   ```bash
   python executions/validate_bg_writing.py <path.csv> --column "<bg-col>" --output tmp/bg_gate_<artifact>.md
   ```
   and fold the linter flags into the review.
4. Main thread is generating >3 sentences of Bulgarian for a user-facing chat reply: the skill must be loaded, but the subagent pass is skipped to keep chat latency low.

Apply the subagent's rewrite before committing to file or presenting to the user. FAIL verdicts block the ship; escalate to the user rather than ship translationese.

Full spec: `directives/bg-writing-review.md`.

---

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

**Map prototype `file://` limitation:** `map-lab.html` and `map-lab-embed.html` (and the legacy `map-embed.html`) will NOT render Mapbox tiles when opened via `file://`. The public Mapbox access token in those files is URL-restricted to `localhost`, `zadeteto.com`, and `www.zadeteto.com`, so a `file://` origin gets a silent 401/403 from the tile API and the canvas stays blank. For map testing specifically, run a local server (`python -m http.server 8000` from `public_html/`) and open `http://localhost:8000/map-lab.html`. Other pages (search, index, about) still work fine via `file://` because they do not call Mapbox.

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
- Do not add `Co-Authored-By` lines to git commit messages
- Do not add sections, features, or content not in the reference
- Do not "improve" a reference design — match it
- Do not stop after one screenshot pass
- Do not use `transition-all`
- Do not use default Tailwind blue/indigo as primary color
- `public_html/` must never contain agent logic, .md directives, .py scripts, or .env files
- `directives/` must never contain code — natural language only
