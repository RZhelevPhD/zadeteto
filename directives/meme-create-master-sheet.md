# meme-create-master-sheet

## Цел
Генерира (или регенерира) `meme-master-sheet.xlsx` — главният вход за Meme Machine pipeline-а.

## Изход
Файл: `0. MEME MACHINE - Copy/meme-master-sheet.xlsx`

## Структура на workbook-а

Workbook-ът съдържа 5 таба. Всички табове имат:
- Bold header row (ред 1)
- Frozen panes на `A2` (header винаги видим при скрол)
- Колонни ширини, съобразени със съдържанието
- Arial 10pt, consistent styling
- Коментари на Excel клетки за по-специфичните полета

### Таб 1 — CONFIG
Глобални настройки, ползвани от формули в другите табове и от pipeline скриптовете.

| Key | Value | Notes |
|---|---|---|
| char_budget_multiplier | 1.25 | Множител за budget: sample_chars × multiplier |
| funnel_L1_target_pct | 35 | Unaware |
| funnel_L2_target_pct | 25 | Problem Aware |
| funnel_L3_target_pct | 18 | Solution Aware |
| funnel_L4_target_pct | 17 | Our Solution Aware |
| funnel_L5_target_pct | 5 | Most Aware |
| default_timezone | Europe/Sofia | За QUEUE post_time |
| default_brand | ZaDeteto | |
| default_brand_url | https://zadeteto.com | |

Схема: `key` (колона A) — named-range-friendly; `value` (колона B); `notes` (колона C).

### Таб 2 — AVATARS
Профили на целевите персонaji.

Колони:
- `avatar_id` (PK, формат A01, A02, ...)
- `avatar_name` (кратък label на БГ)
- `demographics` (възраст, локация, доходи — едно изречение)
- `role_context` (професия, житейска фаза)
- `core_pains` (ключови болки; разделител `; `)
- `core_desires` (желания; разделител `; `)
- `fears` (страхове)
- `daily_reality` (конкретни ежедневни сцени; `; `)
- `voice_style` (dropdown: sarcastic / warm / direct / skeptical / self-deprecating / earnest)
- `cultural_refs` (БГ културни котви; comma-separated)
- `notes`

### Таб 3 — PRODUCTS
Продукти / услуги, към които се насочва съдържание.

Колони:
- `product_id` (PK, P01, P02, ...)
- `product_name`
- `category`
- `key_benefit` (едно изречение)
- `differentiation` (vs конкуренти)
- `level_5_cta_bg` (Bulgarian CTA text — пействат се директно в L5 captions)
- `cta_url`
- `notes`

### Таб 4 — FORMULAS
Meme templates / формули.

Колони:
- `formula_id` (PK, F01, F02, ...)
- `formula_name` (кратък label)
- `template_text_bg` (Bulgarian template с `[X]`, `[Y]`, `[Z]` placeholders)
- `var_X_description` (какво заема позиция X)
- `var_Y_description`
- `var_Z_description`
- `sample_meme_text` (оригинален sample на оригиналния език)
- `sample_char_count` — **Excel формула** `=LEN(sample_meme_text)`
- `char_budget` — **Excel формула** `=CEILING(sample_char_count * <multiplier>, 1)`, където `<multiplier>` се взема от CONFIG чрез **INDEX/MATCH по ключ** (`INDEX(CONFIG!$B:$B, MATCH("char_budget_multiplier", CONFIG!$A:$A, 0))`). Търси се по името на ключа в колона A, а не по фиксирана клетка (`CONFIG!$B$2`) — така формулата оцелява при пренареждане на редовете в CONFIG.
- `theme_folder` (име на подпапка в `0. MEME MACHINE - Copy/0. Themes/`)
- `format_type` (dropdown: image+text / text_only / graph / list / speech_bubble / pie_chart / bar_chart)
- `source` (произход на формулата, напр. "Meme Maker Brian")
- `notes`

### Таб 5 — QUEUE
Опашка от посланията за генериране.

Колони:
- `queue_id` (PK, Q001, Q002, ...)
- `post_date` (YYYY-MM-DD)
- `post_time` (HH:MM)
- `platform` (dropdown: Facebook / Instagram / LinkedIn / TikTok / Google)
- `product_id` (FK → PRODUCTS.product_id, data validation)
- `avatar_id` (FK → AVATARS.avatar_id, data validation)
- `formula_id` (FK → FORMULAS.formula_id, data validation)
- `awareness_level` (dropdown 1-5)
- `status` (dropdown: pending / generated / approved / scheduled / posted / skipped; по подразбиране `pending`)
- `notes`

## Data validation (dropdowns)

- `AVATARS.voice_style` → inline list: sarcastic, warm, direct, skeptical, self-deprecating, earnest
- `FORMULAS.format_type` → inline list: image+text, text_only, graph, list, speech_bubble, pie_chart, bar_chart
- `QUEUE.platform` → inline list: Facebook, Instagram, LinkedIn, TikTok, Google
- `QUEUE.awareness_level` → inline list: 1, 2, 3, 4, 5 (seed редовете съхраняват стойностите като **низове** `"1"`…`"5"`, а не като числа, за да съвпадат точно с inline-list dropdown-а — иначе Excel рисува зелени validation triangles върху seed клетките)
- `QUEUE.status` → inline list: pending, generated, approved, scheduled, posted, skipped
- `QUEUE.product_id` → range reference `=PRODUCTS!$A$2:$A$200`
- `QUEUE.avatar_id` → range reference `=AVATARS!$A$2:$A$200`
- `QUEUE.formula_id` → range reference `=FORMULAS!$A$2:$A$200`

Забележка за inline lists: Excel има таван от **255 символа** за inline comma-separated списъка (включително кавичките). Helper-ът `add_list_validation` assert-ва това ограничение и хвърля грешка с ясно съобщение, ако някой бъдещ enum го надхвърли — в такъв случай опциите трябва да се преместят в скрит sheet и да се реферират като range.

## Seed rows

Скриптът инжектира по 2-3 примерни реда във всеки таб, за да е ясен форматът. Потребителят ги презаписва.

## Изпълнение

```bash
python executions/meme_create_master_sheet.py
```

### Флагове
- `--force` — презаписва съществуващия файл без питане. По подразбиране скриптът спира, ако `meme-master-sheet.xlsx` вече съществува.
- `--no-seed` — прескача seed редовете (създава празен template само с headers).

## Safety
- НЕ презаписва съществуващ файл без `--force`
- НЕ пипа нищо извън `0. MEME MACHINE - Copy/meme-master-sheet.xlsx`

## Changelog
- 2026-04-19: Initial version.
- 2026-04-19: Documented reviewer-round fixes: `char_budget` formula now uses INDEX/MATCH by key against CONFIG (not a fixed `$B$2` reference); `QUEUE.awareness_level` seed values stored as strings to match the inline dropdown; noted the 255-char Excel inline-list ceiling asserted by `add_list_validation`.
- 2026-05-07: Domain rename `zadeteto.bg` → `zadeteto.com` in CONFIG `default_brand_url` and in P01 / P02 product seed CTAs.
