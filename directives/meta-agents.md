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

| Script | Directive | Purpose |
|--------|-----------|---------|
| `executions/scrape_google_maps.py` | `directives/scrape-google-maps.md` | Scrape Google Maps for Bulgarian businesses |
| `executions/enrich_providers.py` | `directives/enrich-providers.md` | Enrich scraped data with contacts/socials |
| `executions/crawl_website.py` | `directives/crawl-website.md` | Extract contacts from a single website |
| `executions/google_search_enrichment.py` | `directives/google-search-enrichment.md` | Find social profiles via Google Search |
| `executions/run_pipeline.py` | `directives/run-pipeline.md` | Orchestrate full scrape-enrich pipeline |
| `executions/fetch_social_data.py` | `directives/content-intelligence.md` | Fetch social posts from Apify |
| `executions/analyze_outliers.py` | `directives/content-intelligence.md` | Detect engagement outliers |
| `executions/research_trends.py` | `directives/content-intelligence.md` | Research why content is trending |
| `executions/generate_content_report.py` | `directives/content-intelligence.md` | Generate PDF report with graphs |
| `executions/run_content_intelligence.py` | `directives/content-intelligence.md` | Orchestrate full content intel pipeline |

## Sub-Agents

| Agent | Location | Trigger | Purpose |
|-------|----------|---------|---------|
| `script-reviewer` | `~/.claude/agents/script-reviewer.md` | After any .py is created/modified | Audit for correctness, error handling, logic, safety |
| `doc-sync` | `.claude/agents/doc-sync.md` | After script-reviewer passes | Update directives to match script changes |

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
- `.env` — Supabase URL and anon key (source of truth for all API config)
