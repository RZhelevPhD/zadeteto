# Metadirective: Agent & Pipeline Workflows

## Scope
All tasks related to the lead generation pipeline, data enrichment, and agentic automation workflows for ZaDeteto.

## DOE Framework (Directive-Orchestration-Execution)

| Layer | Location | Format | Purpose |
|-------|----------|--------|---------|
| **Directive** | `directives/` | `.md` files, zero code | Natural language SOPs defining what to do and why |
| **Orchestration** | Claude (the AI agent) | Conversational | Routes decisions, calls scripts, handles errors |
| **Execution** | `executions/` | `.py` scripts | Deterministic code doing the actual work |

### Rules
- Directives contain **zero code** — only natural language instructions
- Execution scripts are **modular and deterministic** — one script, one job
- The orchestrator (Claude) never writes inline Python — it calls execution scripts
- All temporary/checkpoint files go in `tmp/`
- All secrets live in `.env` (root) — never hardcode in scripts

## Execution Scripts

### Scraping + enrichment (core pipeline)
| Script | Directive | Purpose |
|--------|-----------|---------|
| `executions/scrape_google_maps.py` | `directives/scrape-google-maps.md` | Scrape Google Maps for Bulgarian businesses (city-first flow with viewport fallback) |
| `executions/scrape_gmaps_by_url.py` | `directives/scrape-gmaps-by-url.md` | Re-scrape Google Maps detail pages from an existing URL list (Outscraper ingest stage 1) |
| `executions/enrich_providers.py` | `directives/enrich-providers.md` | Enrich scraped data with contacts/socials; Google Sheets or `--output-csv` |
| `executions/crawl_website.py` | `directives/crawl-website.md` | Extract contacts from a single website |
| `executions/google_search_enrichment.py` | `directives/google-search-enrichment.md` | Find social profiles via Google Search |
| `executions/run_pipeline.py` | `directives/run-pipeline.md` | Orchestrate full scrape-enrich pipeline |
| `executions/summarize_scrape.py` | `directives/summarize-scrape.md` | Summarize scraped CSVs into a markdown review file for human cross-check |

### City pipelines + image fetching
| Script | Directive | Purpose |
|--------|-----------|---------|
| `executions/run_city_pipeline.py` | `directives/run-city-pipeline.md` | End-to-end orchestrator for one target city: scrape → enrich → clean → images |
| `executions/run_3cities_batch.py` | — | Orchestrator for the Пловдив / Варна / Бургас 3-city batch (2026-04-21); resume-safe per-city |
| `executions/clean_enriched.py` | `directives/clean-enriched.md` | Drop viewport-spill rows (other BG cities) from an enriched CSV (`--target-city`) |
| `executions/fetch_business_images.py` | `directives/fetch-business-images.md` | Download logo + hero photo candidates per business (og:image + icon tags, Facebook fallback) |
| `executions/reconcile_curation.py` | `directives/reconcile-curation.md` | Propagate user deletions back into the manifest; stamp `legacy_id` on cleaned CSVs |
| `executions/dedupe_across_categories.py` | `directives/dedupe-across-categories.md` | Merge duplicate businesses across cleaned CSVs; union of granular `categories` |
| `executions/upload_images_to_supabase.py` | `directives/upload-images-to-supabase.md` | Ensure Storage buckets exist + upload logos/heros; write public URLs back to manifest |

### Supabase import
| Script | Directive | Purpose |
|--------|-----------|---------|
| `executions/extract_sofia_from_xlsx.py` | `directives/extract-sofia-from-xlsx.md` | Parse the Sofia multi-tab xlsx, aggregate categories per business across tabs, dedupe, emit import-ready CSV |
| `executions/sofia_tab_category_map.py` | — | Helper: Sofia xlsx tab-name → Bulgarian category mapping + specificity rank (consumed by extract_sofia_from_xlsx) |
| `executions/import_businesses_to_supabase.py` | `directives/import-businesses-to-supabase.md` | Upsert deduped CSV into `businesses` on `legacy_id`; dry-run by default; `--manifest` + `--import-batch` |
| `executions/backfill_google_ratings.py` | — | Backfill `google_rating` + `google_review_count` on `businesses` from deduped CSV |
| `executions/generate_claim_tokens.py` | `directives/generate-claim-tokens.md` | Generate one-time UUID claim tokens for every unowned business (outreach `/claim.html?token=…`) |

### Prospects (outreach segmentation)
| Script | Directive | Purpose |
|--------|-----------|---------|
| `executions/clean_segment_prospects.py` | `directives/clean-segment-prospects.md` | Take raw Outscraper output, dedupe, clean fields, classify each prospect into niches |
| `executions/enrich_and_reclassify_prospects.py` | `directives/enrich-and-reclassify-prospects.md` | Upgrade niche classification by fetching actual website text (fixes ~35% `other` tagging) |

### QA pillars (on-demand site audit)
| Script | Directive | Purpose |
|--------|-----------|---------|
| `executions/qa_run.py` | `directives/qa-run.md` | Umbrella runner for the five deterministic QA pillars; writes `tmp/qa-reports/<ts>/run-summary.json` |
| `executions/qa_links.py` | `directives/qa-links.md` | Link & asset integrity: every href / src / link / OG meta / JSON-LD / JS-string asset across `public_html/` |
| `executions/qa_forms_inventory.py` | `directives/qa-forms.md` | Form audit: missing labels, missing required, autocomplete misuse, novalidate without JS replacement, missing error containers |
| `executions/qa_roles_probe.py` | `directives/qa-roles.md` | Role-gated UI: `js/nav-inject.js` role-detection contract + protected-page client-side auth gates |
| `executions/qa_a11y_static.py` | `directives/qa-craft.md` | Static a11y scan: alt, label-for, h1 hygiene, landmarks, skip-link, focus-visible, focusable-inside-aria-hidden, onclick-without-role |
| `executions/qa_data_integrity.py` | `directives/qa-data.md` | Read-only Supabase invariants: slug uniqueness, FK orphans, tier enum, expired tokens, audit-submission consistency |

The QA umbrella is `directives/meta-qa.md`. Always invoke through the `qa` orchestrator (`.claude/agents/qa.md`), not the scripts directly.

### Content pipelines (memes + content intelligence)
| Script | Directive | Purpose |
|--------|-----------|---------|
| `executions/validate_bg_writing.py` | `directives/validate-bg-writing.md` | Translationese + brand-vocab audit for Bulgarian content CSVs |
| `executions/audit_meme_templates.py` | `directives/audit-meme-templates.md` | Meme pipeline Step 1 — list template images, write skeleton registry CSV |
| `executions/meme_create_master_sheet.py` | `directives/meme-create-master-sheet.md` | Generate / regenerate `meme-master-sheet.xlsx` — the master input for the Meme Machine pipeline |
| `executions/inject_brand_vocab.py` | `directives/inject-brand-vocab.md` | Meme pipeline Step 4 — flag Top 3 variations missing brand vocab, suggest injections |
| `executions/export_designer_brief.py` | `directives/export-designer-brief.md` | Meme pipeline Step 5 — filter Top 3, export designer-ready CSV |
| `executions/run_meme_pipeline.py` | `directives/run-meme-pipeline.md` | Umbrella orchestrator for the 5-step meme content pipeline |
| `executions/fetch_social_data.py` | `directives/content-intelligence.md` | Fetch social posts from Apify |
| `executions/analyze_outliers.py` | `directives/content-intelligence.md` | Detect engagement outliers |
| `executions/research_trends.py` | `directives/content-intelligence.md` | Research why content is trending |
| `executions/generate_content_report.py` | `directives/content-intelligence.md` | Generate PDF report with graphs |
| `executions/run_content_intelligence.py` | `directives/content-intelligence.md` | Orchestrate full content intel pipeline |

### Funny library + punchup stack
| Script | Directive | Purpose |
|--------|-----------|---------|
| `executions/reorganize_funny_library.py` | `directives/reorganize-funny-library.md` | One-time relocation of `BRANDING/Funny Marketing 2.0/` into 9 numbered buckets under `BRANDING/funny/` with kebab-case slugs + companion grouping + audit ledger |
| `executions/index_funny_library.py` | `directives/index-funny-library.md` | Indexer that regenerates `docs/funny-reference-index.md` with the bucket → subagent routing table + per-bucket asset listings |

The punchup umbrella is `directives/meta-punchup.md`. Always invoke through the `punchup` orchestrator (`.claude/agents/punchup.md`), not the audit subagents directly.

## Sub-Agents

| Agent | Location | Trigger | Purpose |
|-------|----------|---------|---------|
| `script-reviewer` | `~/.claude/agents/script-reviewer.md` | After any .py is created/modified | Audit for correctness, error handling, logic, safety |
| `doc-sync` | `.claude/agents/doc-sync.md` | After script-reviewer passes | Update directives to match script changes |
| `ahdm` | `.claude/agents/ahdm.md` | When improving marketing/copy/offers | AHDM Orchestrator — routes to domain subagents, synthesizes Bulgarian improvement plan |
| `ahdm-offers` | `.claude/agents/ahdm-offers.md` | Called by AHDM orchestrator | Offer construction, pricing, Value Equation, Grand Slam Offer |
| `ahdm-leads` | `.claude/agents/ahdm-leads.md` | Called by AHDM orchestrator | Lead generation, Core Four, lead magnets, nurture |
| `ahdm-ads` | `.claude/agents/ahdm-ads.md` | Called by AHDM orchestrator | Ad copy, hooks, attention mechanics, Marketing Machine |
| `ahdm-closing` | `.claude/agents/ahdm-closing.md` | Called by AHDM orchestrator | Sales closing, Blame Framework, objection handling |
| `ahdm-proof` | `.claude/agents/ahdm-proof.md` | Called by AHDM orchestrator | Social proof, testimonials, retention, 5 Horsemen |
| `ahdm-brand` | `.claude/agents/ahdm-brand.md` | Called by AHDM orchestrator | StoryBrand SB7, brand narrative, positioning |
| `ahdm-launch` | `.claude/agents/ahdm-launch.md` | Called by AHDM orchestrator | Funnel architecture, VSL scripts, launch sequences |
| `ahdm-ops` | `.claude/agents/ahdm-ops.md` | Called by AHDM orchestrator | Scaling SOPs, Leila's 5 Frameworks |
| `bg-writing` | `.claude/agents/bg-writing.md` | Called by AHDM Step 6.5, BD Step 6.5, or main thread for any Bulgarian artifact >3 sentences; also by `run_meme_pipeline.py` implicitly via `validate_bg_writing.py` | Bulgarian language quality gate — checks positive (skill) and negative (banned patterns) layers; optionally runs `validate_bg_writing.py`; returns verdict + rewrite. See `directives/bg-writing-review.md`. |
| `qa` | `.claude/agents/qa.md` | When user asks for a QA pass / link check / journey check / role audit / form audit / a11y check / data-integrity check on the site | QA Orchestrator — routes to six pillar subagents, synthesises consolidated report under `tmp/qa-reports/<ts>/`. See `directives/meta-qa.md`. |
| `qa-links` | `.claude/agents/qa-links.md` | Called by QA orchestrator | Link & asset integrity. Backed by `executions/qa_links.py`. |
| `qa-journeys` | `.claude/agents/qa-journeys.md` | Called by QA orchestrator | Parent + partner walkthroughs via Chrome headless. No backing script. |
| `qa-roles` | `.claude/agents/qa-roles.md` | Called by QA orchestrator | Role-gated UI + access control. Backed by `executions/qa_roles_probe.py`. |
| `qa-forms` | `.claude/agents/qa-forms.md` | Called by QA orchestrator | Form audit. Backed by `executions/qa_forms_inventory.py`. |
| `qa-craft` | `.claude/agents/qa-craft.md` | Called by QA orchestrator | Static a11y + responsive screenshot loop. Backed by `executions/qa_a11y_static.py` + Chrome headless. |
| `qa-data` | `.claude/agents/qa-data.md` | Called by QA orchestrator | Read-only Supabase data-integrity probe. Backed by `executions/qa_data_integrity.py`. |
| `punchup` | `.claude/agents/punchup.md` | When the user asks for a punch-up / "make this funnier" / "add humour" / a specific reel-format or device by name; also via the soft Punch-up Suggestion Trigger after an ad / VSL / landing page / email body / long social post is created | punchup Orchestrator — runs `punchup-truth` first, fans out the relevant audit subagents, runs `punchup-safety` last, hands the bundle to `punchup-writer`, gates BG. See `directives/meta-punchup.md`. |
| `punchup-truth` | `.claude/agents/punchup-truth.md` | Called by punchup orchestrator (always, first) | Relatable Truth specialist. Reads `BRANDING/funny/01-core/` + `05-audience/` + Twelve Types of Relatable Truth. Returns Audience Profile + Top Truths + Slot Map. |
| `punchup-toolkit` | `.claude/agents/punchup-toolkit.md` | Called by punchup orchestrator (long-form + general slots) | 6-tool comedic toolkit specialist (Bracketed Asides, Joke Thirds, Lists, Misdirection, Comic Comparisons, Parody). Maps slot shape to device. |
| `punchup-jokes` | `.claude/agents/punchup-jokes.md` | Called by punchup orchestrator (short-form video / reel / caption) | 12 reel-format joke templates + joke-writing fundamentals. Matches asset to template + cites the template's `.txt` recipe for Framework Fidelity. |
| `punchup-ads` | `.claude/agents/punchup-ads.md` | Called by punchup orchestrator (paid ad copy) | Ad-type specialist (Problem-Solution / Testimonial / Origin Story) + FB Ads + Mini VSLs + PAS. |
| `punchup-copy` | `.claude/agents/punchup-copy.md` | Called by punchup orchestrator (landing pages / sales pages / emails / lead magnets / webinar slides / VSL past the hook) | Long-copy framework specialist. AIDA / PAS / FAB / OCPB / Selling-With-Story punch-up. |
| `punchup-platform` | `.claude/agents/punchup-platform.md` | Called by punchup orchestrator (channel + amplifier-aware) | Platform delivery (UGC + monthly sessions) + reach amplifiers (giveaways, engagement campaigns, win-the-comments). |
| `punchup-safety` | `.claude/agents/punchup-safety.md` | Called by punchup orchestrator (last in audit fan-out) | Golden / Silver Rule check from `skills/funny-marketing.md`. DROP / RISKY / SAFE per opportunity. |
| `punchup-writer` | `.claude/agents/punchup-writer.md` | Called by punchup orchestrator (after audit + safety) | The only punchup subagent that produces finished variants. Folds in the legacy jts-01-comedy-creative Framework Fidelity Rule + 4-phase joke creation process. |

### Trigger Sequence (mandatory, no exceptions)
1. Create or modify any execution script (`.py`)
2. Invoke `script-reviewer` sub-agent — provide the directive path and script path
3. Apply any fixes from the reviewer's report
4. Invoke `doc-sync` sub-agent — it reads the script and updates the matching directive

## Self-Annealing Protocol
When an error occurs during script execution:
1. **Diagnose** — Read the error, identify the root cause
2. **Fix** — Attempt a targeted fix in the execution script
3. **Update** — Update the directive to reflect the change
4. **Verify** — Re-run the script to confirm the fix works
5. **Escalate** — Only ask the user if all fix attempts are exhausted

## Checkpoint Files
- `tmp/scrape_checkpoint.json` — completed keyword/city pairs
- `tmp/enrichment_progress.json` — completed enrichment rows
- Never delete these during or between runs
- Use `--resume` flag to skip completed work

## Dependencies
```bash
pip install playwright pandas requests beautifulsoup4 googlesearch-python \
            gspread google-auth-oauthlib google-auth python-dotenv openpyxl xlrd
playwright install chromium
```

## External Credentials
- `credentials.json` — Google OAuth (download from Google Cloud Console, place in project root)
- `token.json` — Auto-generated after first Google OAuth consent
- `.env` — Supabase URL, publishable key (`sb_publishable_...`), and secret key (`sb_secret_...`); source of truth for all API config
