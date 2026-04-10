-- ════════════════════════════════════════════════════════════════════════
-- ZaDeteto 2.0 — Sample test businesses (6 rows for listing-page demo)
--
-- Run this in Supabase SQL editor AFTER applying migrations 0003 + 0004.
-- Inserts 6 sample businesses (1 elite hero + 5 supporting) so the listing
-- page has something to render and the "Подобни специалисти" section has
-- something to populate.
--
-- All rows are flagged is_sample = true (set in the INSERT below) so they
-- can be cleanly deleted later without touching real partner data.
--
-- Safe to re-run: uses ON CONFLICT (legacy_id) DO UPDATE so re-running
-- updates the rows in place instead of creating duplicates.
--
-- Cleanup (deletes ALL sample data including the 100-mockup batch):
--   DELETE FROM public.businesses WHERE is_sample = true;
-- ════════════════════════════════════════════════════════════════════════

INSERT INTO public.businesses (
  legacy_id, name, tier, city, address, lat, lng,
  description, services, categories, age_groups,
  logo, audit_score, sop, phone, email, website,
  facebook, instagram, cta_label_1, cta_url_1, cta_label_2, cta_url_2,
  working_hours, gallery_urls, published, is_sample
) VALUES
(
  'sample-001',
  'Little Engineers',
  'Доверен',
  'София',
  'ул. Витоша 15, София 1000',
  42.6977, 23.3219,
  'Учебен център за деца от 6 до 14 години с фокус върху STEM, роботика и креативно мислене. Работим с LEGO Education, Arduino и 3D принтери. Малки групи (макс. 8 деца), сертифицирани преподаватели, индивидуален подход за всяко дете.',
  ARRAY['LEGO роботика', '3D печат', 'Arduino', 'Кодиране за деца', 'Лятна академия'],
  ARRAY['Учене и умения'],
  ARRAY['6-12', '13-19'],
  'https://placehold.co/200x200/7c4dff/white?text=LE',
  185, false,
  '+359 88 888 8888',
  'office@littleengineers.bg',
  'https://littleengineers.bg',
  'https://facebook.com/littleengineers',
  'https://instagram.com/littleengineers',
  'Запиши се', 'https://littleengineers.bg/signup',
  'Виж курсове', 'https://littleengineers.bg/courses',
  '{"mon":"9:00-19:00","tue":"9:00-19:00","wed":"9:00-19:00","thu":"9:00-19:00","fri":"9:00-19:00","sat":"10:00-15:00","sun":"closed","note":"Затворено в национални празници"}'::jsonb,
  ARRAY[
    'https://placehold.co/600x400/7c4dff/white?text=Klasna+staya',
    'https://placehold.co/600x400/2e994d/white?text=LEGO+lab',
    'https://placehold.co/600x400/c89a00/white?text=3D+printer',
    'https://placehold.co/600x400/7c4dff/white?text=Demo+den',
    'https://placehold.co/600x400/2e994d/white?text=Otbor',
    'https://placehold.co/600x400/c89a00/white?text=Sertifikat'
  ],
  true, true
),
(
  'sample-002',
  'STEM Lab София',
  'Проверен',
  'София',
  'бул. Цариградско шосе 47',
  42.6789, 23.3456,
  'Лаборатория за наука и технологии. Експерименти, опити, кодиране. За любопитни деца от 7 до 14 години.',
  ARRAY['Експерименти', 'Кодиране', 'Електроника'],
  ARRAY['Учене и умения'],
  ARRAY['6-12'],
  'https://placehold.co/200x200/2e994d/white?text=SL',
  120, false,
  '+359 88 111 2233',
  'info@stemlab.bg',
  'https://stemlab.bg',
  'https://facebook.com/stemlabsofia',
  null,
  'Резервирай', 'https://stemlab.bg/book',
  null, null,
  '{"mon":"closed","tue":"15:00-19:00","wed":"15:00-19:00","thu":"15:00-19:00","fri":"15:00-19:00","sat":"10:00-16:00","sun":"closed"}'::jsonb,
  ARRAY[]::text[],
  true, true
),
(
  'sample-003',
  'Coding Kids Academy',
  'Проверен',
  'София',
  'ул. Граф Игнатиев 22',
  42.6912, 23.3242,
  'Програмиране за деца — Scratch, Python, JavaScript. От първи стъпки до собствени проекти.',
  ARRAY['Scratch', 'Python', 'JavaScript', 'Уеб сайтове'],
  ARRAY['Учене и умения'],
  ARRAY['6-12', '13-19'],
  'https://placehold.co/200x200/c89a00/white?text=CK',
  95, true,
  '+359 88 222 3344',
  'hi@codingkids.bg',
  'https://codingkids.bg',
  null, null,
  'Запиши се за демо', 'https://codingkids.bg/demo',
  null, null,
  null,
  ARRAY[]::text[],
  true, true
),
(
  'sample-004',
  'Robotics School Sofia',
  'Стандартен',
  'София',
  null, null, null,
  'Малък роботски клуб за начинаещи.',
  ARRAY['Роботика'],
  ARRAY['Учене и умения'],
  ARRAY['6-12'],
  'https://placehold.co/200x200/777/white?text=RS',
  60, false,
  '+359 88 333 4455',
  'contact@robotics.bg',
  null, null, null, null, null, null, null,
  null, ARRAY[]::text[], true, true
),
(
  'sample-005',
  'Детска школа Изкуство',
  'Доверен',
  'Пловдив',
  'ул. Главна 12, Пловдив',
  42.1354, 24.7453,
  'Школа по рисуване, керамика и приложни изкуства за деца от 5 до 16 години. Обучение по програма, изложби, лятни лагери.',
  ARRAY['Рисуване', 'Керамика', 'Скулптура', 'Графика'],
  ARRAY['Култура'],
  ARRAY['3-5', '6-12', '13-19'],
  'https://placehold.co/200x200/7c4dff/white?text=DI',
  150, false,
  '+359 32 555 6677',
  'info@izkustvo.bg',
  'https://izkustvo.bg',
  'https://facebook.com/izkustvo',
  'https://instagram.com/izkustvo',
  'Запиши се', 'https://izkustvo.bg/signup',
  'Лятна школа', 'https://izkustvo.bg/leto',
  '{"mon":"10:00-18:00","tue":"10:00-18:00","wed":"10:00-18:00","thu":"10:00-18:00","fri":"10:00-18:00","sat":"10:00-14:00","sun":"closed"}'::jsonb,
  ARRAY[]::text[],
  true, true
),
(
  'sample-006',
  'Online Code Camp',
  'Проверен',
  'Онлайн',
  null, null, null,
  'Онлайн програмиране за деца чрез интерактивна платформа. Малки групи, преподаватели на живо.',
  ARRAY['Scratch', 'Python', 'Game development'],
  ARRAY['Учене и умения'],
  ARRAY['6-12', '13-19'],
  'https://placehold.co/200x200/2e994d/white?text=OC',
  110, false,
  null, 'support@onlinecode.bg',
  'https://onlinecode.bg',
  null, null,
  'Безплатна първа лекция', 'https://onlinecode.bg/trial',
  null, null,
  null,
  ARRAY[]::text[],
  true, true
)
ON CONFLICT (legacy_id) DO UPDATE SET
  name = EXCLUDED.name,
  tier = EXCLUDED.tier,
  city = EXCLUDED.city,
  address = EXCLUDED.address,
  lat = EXCLUDED.lat,
  lng = EXCLUDED.lng,
  description = EXCLUDED.description,
  services = EXCLUDED.services,
  categories = EXCLUDED.categories,
  age_groups = EXCLUDED.age_groups,
  logo = EXCLUDED.logo,
  audit_score = EXCLUDED.audit_score,
  sop = EXCLUDED.sop,
  phone = EXCLUDED.phone,
  email = EXCLUDED.email,
  website = EXCLUDED.website,
  facebook = EXCLUDED.facebook,
  instagram = EXCLUDED.instagram,
  cta_label_1 = EXCLUDED.cta_label_1,
  cta_url_1 = EXCLUDED.cta_url_1,
  cta_label_2 = EXCLUDED.cta_label_2,
  cta_url_2 = EXCLUDED.cta_url_2,
  working_hours = EXCLUDED.working_hours,
  gallery_urls = EXCLUDED.gallery_urls,
  published = EXCLUDED.published,
  is_sample = EXCLUDED.is_sample;

-- Verify the inserts
SELECT id, legacy_id, name, tier, city, working_hours IS NOT NULL AS has_hours,
       array_length(gallery_urls, 1) AS gallery_count
FROM public.businesses
WHERE legacy_id LIKE 'sample-%'
ORDER BY legacy_id;
