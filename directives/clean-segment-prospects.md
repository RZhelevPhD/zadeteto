# Clean & Segment Prospects — Directive

## Purpose

Take raw Outscraper / Google Maps scrape output, dedupe it, clean fields, and classify each prospect into one or more niches (from most-specific to least-specific). Output a single clean CSV ready for outreach sequencing or import into a CRM.

## Inputs

- `tmp/outscraper.xlsx` — raw scrape (default input)
- Headers expected (Outscraper Google-Maps + enrichment standard):
  - `location_link`, `domain_x`, `domain_y`, `company_name`, `company_phone`, `company_phones`, `company_linkedin`, `company_facebook`, `company_instagram`, `company_x`, `company_youtube`, `full_name`, `first_name`, `last_name`, `title`, `email`, `contact_phone`, `contact_phones`, `contact_linkedin`, `contact_facebook`, `contact_instagram`, `contact_x`, `website_title`, `website_description`, `website_generator`, `website_has_gtm`, `website_has_fb_pixel`, `source`

If the header set differs, the script still runs but missing columns are treated as empty.

## Outputs

- `tmp/prospects_clean.csv` — deduped + cleaned + segmented, UTF-8 with BOM
- `tmp/prospects_clean_report.json` — run summary (counts per niche, dedupe stats)

## Deduplication rules

Two records are considered the same prospect if they share any of these identity keys:

1. **Normalized domain** — `domain_y` (or `domain_x` if `domain_y` is empty), lowercased, stripped of `www.` and trailing slash. Primary key.
2. **Normalized phone** — all `company_phone(s)` and `contact_phone(s)` collapsed to digits-only. If two records share any phone number → same prospect.
3. **Normalized email** — lowercased, stripped. If two records share an email → same prospect.

When records merge:
- Scalar fields: keep the first non-empty value in input order.
- Multi-value fields (`emails`, `phones`, `facebook`, `instagram`, `contact_names`): concatenate unique values, `; `-joined.
- Niches: union of niches from all merged rows (dedup preserved).
- Record a `merged_from` count for traceability.

Records with **no domain, no phone, no email** are dropped (unusable).

## Field cleaning

- **phones** — strip all non-digits, then normalize:
  - If starts with `359` and len == 12 → prepend `+`.
  - If starts with `0` and len == 10 → replace leading `0` with `+359`.
  - Otherwise keep digits-only form. Discard if fewer than 7 digits.
  - Output multiple phones `; `-joined, unique.
- **emails** — lowercase, strip, drop obvious junk (contains spaces, no `@`, double `@`). Dedup. `; `-joined.
- **domain** — lowercase, strip `https?://`, strip `www.`, strip trailing `/`. Empty string if missing.
- **social urls** — keep as-is but strip whitespace and trailing `/`. Dedup.
- **name_best** — pick the first non-empty of: `company_name`, `website_title` (trimmed of site-suffixes like `- My Site`, `| ...`, etc.), `full_name`.

## Niche taxonomy

Each niche has:
- `key` — machine id (snake_case)
- `label_bg` — Bulgarian display label
- `sphere` — maps to the 8 partner-form categories on the site (`Специалисти`, `Учене и умения`, `Игри и забавления`, `Култура`, `Спорт и движение`, `Тържества и събития`, `Стоки`, `Домашна грижа и помощ`)
- `priority` — integer, higher = more specific / listed first in multi-niche assignments
- `keywords` — list of Bulgarian + Latin substrings searched across `company_name + website_title + website_description + domain` (case-insensitive, lowercased, accent-agnostic)
- `negative_keywords` (optional) — if any match, the niche is rejected for that row

### Priority bands

- **10 (most specific, top priority):** the niche is unambiguous — company name or title literally contains a domain-defining term.
- **9:** specific sport / therapy / discipline that parents book directly.
- **8:** product categories and supporting services.
- **7:** generic learning / educational center / generic sport club (last-resort fallback before "other").
- **1:** `other` (nothing matched).

### Niches

Games & Entertainment — `Игри и забавления`
- `animators` (10) — `аниматор`, `парти агенция`, `клоун`, `шоу програм`, `magic show`, `фокусник`, `big bubble`, `балон шоу`, `dj за детско`, `party talent`
- `party_center` (10) — `парти център`, `детски парти център`, `детски център`, `детски клуб`, `парти зала`, `playground`, `kids land`, `детски кът`, `игротек`

Celebrations & Events — `Тържества и събития`
- `photographer` (10) — `фотограф`, `photograph`, `детска фотография`
- `party_decor` (9) — `балони`, `декорация`, `украса за`, `party decor`, `балонена къща`

Sport — `Спорт и движение`
- `martial_arts` (9) — `карате`, `айкидо`, `aikido`, `таекуондо`, `taekwondo`, `винг чун`, `wing chun`, `wing tsung`, `джу джицу`, `jiu jitsu`, `jiu-jitsu`, `jiujitsu`, `кикбокс`, `kickbox`, `муай тай`, `muay thai`, `капоейра`, `capoeira`, `джудо`, `judo`, `бойн`, `кунг фу`, `kung fu`, `бокс`, `самбо`, `фехтовк`, `тай чи`, `tai chi`, `хапкидо`, `кумдо`, `mma`, `fight club`, `доджо`, `додж`, `додо`, `борба`, `wrestling`
- `dance_ballet` (9) — `балет`, `ballet`, `танц`, `tanci`, `dance`, `школа по танц`, `zumba`, `зумба`, `хореограф`, `латино танц`, `tango`, `танго`, `народни танци`
- `football` (9) — `футбол`, `football`, `soccer`, `фк `, `fc `
- `swimming` (9) — `плуване`, `swim`, `басейн`, `аква`, `waterpolo`
- `basketball` (9) — `баскет`, `basket`
- `volleyball` (9) — `волейбол`, `volley`
- `tennis` (9) — `тенис`, `tennis`
- `ice_skating` (9) — `ледена пързалка`, `кънки`, `хокей`, `hockey`, `фигурно пързаляне`, `ice centre`, `ice center`
- `athletics` (9) — `лека атлетика`, `athletics`, `track and field`
- `gymnastics` (9) — `гимнастик`, `gymnastic`
- `climbing` (9) — `катерене`, `climbing`, `алпинизъм`, `boulder`
- `sport_general` (7) — `спортен клуб`, `sport club`, `спортен център`, `sport center`, `спортен комплекс`, `sport complex`, `спортна академия`, `fitness`, `фитнес`, `федерация по`, `sports federation` — fallback only

Learning & Skills — `Учене и умения`
- `kindergarten` (10) — `детска градина`, `детска ясла`, `чдг`, `чдя`, `kindergarten`, `nursery`, `daycare`, `montessori`, `edutainment`, `bilingual`, `multilingual children`
- `private_school` (10) — `частно училище`, `частен лицей`, `частно основно`, `частно средно`, `лицей`, `гимназия`, `соу`, `основно училище`, `средно училище`, `private school`, `primary school`, `secondary school`, `high school`, `international school` (bare `school` / `училище` removed — they falsely matched karate "schools", language schools, speech-therapy centers, etc.)
- `afterschool` (10) — `занималн`, `after school`, `brain academy`, `целодневна подготовка`, `афтършкул`, `ментална аритметика`, `smartykids`, `smarty kids`
- `language_school` (10) — `езиков`, `language`, `курсове по английски`, `курсове по немски`, `курсове по испански`, `курсове по френски`, `курсове по италиански`, `курсове по руски`, `english school`, `английски език`, `немски език`, `испански език`, `френски език`, `ielts`, `toefl`, `cambridge`, `cae`, `fce`, `cpe`
- `music_school` (10) — `музикална школа`, `music school`, `music center`, `music lab`, `музикален център`, `музикално студио`, `музикално обучителн`, `уроци по пиано`, `уроци по китара`, `уроци по цигулка`, `уроци по пеене`, `уроци по гайда`, `уроци по музик`, `уроци по барабани`, `уроци по барабан`, `solfege`, `солфеж`, `venera music`, `city music`, `music box`, `rhythm-academy`, `rhythm academy`, `drum cover`, `drum lessons`, `певчески`, `искам да пея`
- `art_school` (10) — `уроци по рисуване`, `art school`, `школа по рисуване`, `арт студио`, `керамика`, `drawing class`, `рисуване за`
- `driving_school` (10) — `автошкола`, `шофьорски курс`, `driving school`
- `private_lessons_subj` (8) — `частни уроци`, `уроци по математика`, `уроци по български`, `уроци по биология`, `уроци по химия`, `подготовка за нво`, `подготовка за матур`, `матура по`, `нво`, `кандидат-студент`, `учебен център` — fallback
- `educational_center` (7) — `учебен център`, `образователен център`, `center for learning`, `learning center`, `академия`, `academy`, `academi` — last-resort fallback

Specialists — `Специалисти`
- `speech_therapist` (10) — `логопед`, `speech therap`, `speechtherap`, `логопедичен`, `logoped`, `езиково-говорна`
- `child_psychologist` (10) — *Note:* all prospects in this dataset were scraped from the Google Maps query "детски психолог", so even generic psychology terms point to a practitioner who serves children or parents. Keywords: `детски психолог`, `детски психотерап`, `child psycholog`, `психомоторик`, `арт терапия`, `арттерапия`, `детско развитие`, `детска психология`, `детски коуч`, plus generic terms: `психолог`, `психотерапев`, `психотерапия`, `psycholog`, `psychotherap`, `психологическо консултиране`, `психологична помощ`, `психологично консултиране`, `психиатр`, `семейни констелации`, `фамилни констелации`, `хипнотерап`, `хипноза`
- `therapy_center` (9) — `терапевтичен център`, `ерготерапия`, `occupational therap`, `сензорна интеграция`, `сензорно-интегративна`, `център за детско развитие`, `развитие и игра`, `център за развитие`, `психологически кът`

Culture — `Култура`
- `theatre_opera` (9) — `опера`, `opera`, `театър`, `theatre`, `theater`, `филхармон`
- `museum` (9) — `музей`, `museum`
- `community_cultural_center` (9) — `читалище`

Goods — `Стоки`
- `kids_clothing_shoes` (8) — `детски дрехи`, `детски дрешки`, `бебешки дрехи`, `бебешки дрешки`, `детски обувки`, `бебешки обувки`, `детски магазин`, `kids shoes`, `kids clothes`, `baby clothes`, `bebeshki dreshki`, `боси обувки`, `боти`, `ботуши`, `маратонки за деца`
- `kids_toys` (8) — `детски играчки`, `играчк`, `toys`, `toy store`
- `baby_goods` (8) — `бебешки магазин`, `бебешки мебели`, `бебешки кошар`, `бебешки колич`, `кошара`, `креватче`, `бебешки стоки`, `baby shop`, `бебешки гнезд`
- `sports_gear` (8) — `спортна екипировка`, `екипировка за`, `танцова екипировка`, `ballet shop`, `dance shop`, `danceshop`, `boxova`, `бойна екипировка`
- `kids_food_catering` (8) — `детска кухня`, `детско меню`, `детски кетъринг`, `bio детска`, `kids catering`, `kids food`, `дкх`, `био детска`, `кетъринг`, `catering`
- `kids_books` (8) — `детски книг`, `kids book`, `children's book`, `детско издателство`, `детски приказки`, `издателство`, `book publisher`

Home care — `Домашна грижа и помощ`
- `babysitter` (9) — `детегледач`, `бавач`, `nanny`, `babysitter`, `au pair`

Uncategorized
- `other` (1) — nothing matched. Preserve for manual review.

### Multi-niche rules

- Run all niches for each row (no early-exit).
- If a niche matches via keyword AND its `negative_keywords` don't match, assign it.
- Sort assigned niches by `priority DESC`, stable-sort by definition order as tiebreaker.
- Output `niches_all` = `; `-joined keys, `niche_primary` = first element, `niche_count` = length.
- Never assign `other` if any real niche matched. Only assign `other` when the list is empty.
- `spheres_all` = dedup of `sphere` across assigned niches, priority-ordered.

### Edge cases

- If `sport_general` (7) matches AND any other sport (9) matches → drop `sport_general` (it's a fallback).
- If `educational_center` (7) OR `private_lessons_subj` (8) matches AND any other learning niche (10) matches → drop the fallback.
- If `kindergarten` matches and `private_school` also matches, keep both (kindergarten wins primary by definition order — listed first in the taxonomy).

## Output CSV schema

Columns, in order:

1. `niche_primary` — main niche key (highest priority)
2. `sphere_primary` — sphere of the primary niche
3. `niches_all` — `; `-joined all matched niches
4. `spheres_all` — `; `-joined all matched spheres
5. `name_best` — cleaned display name
6. `domain` — normalized domain
7. `phones` — cleaned, `; `-joined, unique
8. `emails` — cleaned, `; `-joined, unique
9. `contact_names` — `; `-joined all `full_name` values from merged rows
10. `title` — contact title
11. `facebook` — all facebook urls, `; `-joined
12. `instagram` — all instagram urls, `; `-joined
13. `linkedin` — all linkedin urls, `; `-joined
14. `website_title` — from first merged record
15. `website_description` — from first merged record (truncated to 500 chars)
16. `has_gtm` — boolean
17. `has_fb_pixel` — boolean
18. `website_generator` — from first merged record
19. `merged_from` — int, how many raw rows merged into this record
20. `location_link` — kept for manual spot-check

CSV rows sorted by `sphere_primary` ASC, then `niche_primary` ASC, then `name_best` ASC.

## Run

```bash
python executions/clean_segment_prospects.py
```

Optional args:
- `--input PATH` — alt xlsx path (default `tmp/outscraper.xlsx`)
- `--output PATH` — alt output csv (default `tmp/prospects_clean.csv`)
- `--report PATH` — alt report path (default `tmp/prospects_clean_report.json`)

## Changelog

- 2026-04-19 — initial version.
- 2026-04-19 — narrowed `private_school` keywords: removed bare `school` and `училище`, which were falsely matching karate clubs, language schools, speech-therapy centers, etc. Directive's keyword list now matches the script verbatim.
