-- ════════════════════════════════════════════════════════════════════════
-- ZaDeteto 2.0 — Polish: rewrite mock descriptions to be punchier
--
-- The original sample-100-mockup-partners.sql gave every paid-tier mock
-- the same boring template description ("X предлага професионални услуги
-- в категория Y. Опит, качество, индивидуален подход..."). It looked
-- robotic and broke the search page tagline algorithm because the first
-- sentence was >60 characters.
--
-- This file rewrites the description on every paid-tier mock to a short,
-- varied, category-specific opener (≤60 chars first sentence) followed by
-- a one-liner with detail. Categories get distinct copy so the grid feels
-- like real businesses, not template duplicates.
--
-- Safe to re-run: it's a plain UPDATE, no schema changes.
-- Targets ONLY rows where is_sample = true AND legacy_id LIKE 'mock-%' AND
-- description IS NOT NULL — never touches real data, never touches the 6
-- hand-crafted sample-businesses rows.
-- ════════════════════════════════════════════════════════════════════════

-- Specialists (Специалисти)
UPDATE public.businesses
SET description = 'Грижа и подкрепа за всяко дете. Сертифицирани специалисти, индивидуален подход, безопасна среда.'
WHERE is_sample = true AND legacy_id LIKE 'mock-%' AND categories @> ARRAY['Специалисти']::text[] AND tier IN ('Доверен','Проверен');

-- Учене и умения
UPDATE public.businesses
SET description = 'Учим децата да мислят и да създават. Малки групи, опитни преподаватели, забавни уроци.'
WHERE is_sample = true AND legacy_id LIKE 'mock-%' AND categories @> ARRAY['Учене и умения']::text[] AND tier IN ('Доверен','Проверен');

-- Игри и забавления
UPDATE public.businesses
SET description = 'Място, където детската смях е цел. Безопасни игри, креативни занимания, незабравими преживявания.'
WHERE is_sample = true AND legacy_id LIKE 'mock-%' AND categories @> ARRAY['Игри и забавления']::text[] AND tier IN ('Доверен','Проверен');

-- Култура
UPDATE public.businesses
SET description = 'Култура за деца, поднесена с любов. Театър, изкуство и творчество за всяка възраст.'
WHERE is_sample = true AND legacy_id LIKE 'mock-%' AND categories @> ARRAY['Култура']::text[] AND tier IN ('Доверен','Проверен');

-- Спорт и движение
UPDATE public.businesses
SET description = 'Спорт, дисциплина, забавление. Опитни треньори и здравословна среда за развитие.'
WHERE is_sample = true AND legacy_id LIKE 'mock-%' AND categories @> ARRAY['Спорт и движение']::text[] AND tier IN ('Доверен','Проверен');

-- Тържества и събития
UPDATE public.businesses
SET description = 'Перфектното парти за вашето дете. Аниматори, декорация, торта и спомени за цял живот.'
WHERE is_sample = true AND legacy_id LIKE 'mock-%' AND categories @> ARRAY['Тържества и събития']::text[] AND tier IN ('Доверен','Проверен');

-- Стоки
UPDATE public.businesses
SET description = 'Качествени продукти за деца, подбрани с грижа. Бързи доставки и реална гаранция.'
WHERE is_sample = true AND legacy_id LIKE 'mock-%' AND categories @> ARRAY['Стоки']::text[] AND tier IN ('Доверен','Проверен');

-- Домашна грижа и помощ
UPDATE public.businesses
SET description = 'Доверена помощ в дома. Проверени бавачки, помощници и услуги, на които може да разчитате.'
WHERE is_sample = true AND legacy_id LIKE 'mock-%' AND categories @> ARRAY['Домашна грижа и помощ']::text[] AND tier IN ('Доверен','Проверен');

-- Verify the update
SELECT
  unnest(categories) AS category,
  count(*) AS rows,
  avg(length(description))::int AS avg_desc_length,
  min(length(description)) AS min_len,
  max(length(description)) AS max_len
FROM public.businesses
WHERE is_sample = true AND legacy_id LIKE 'mock-%' AND description IS NOT NULL
GROUP BY category
ORDER BY category;
