"""Clean, dedupe, and segment prospect records scraped from Google Maps / Outscraper.

See directives/clean-segment-prospects.md for full spec.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Iterable

import openpyxl


# ---------- taxonomy ----------

# Each niche: (key, label_bg, sphere, priority, keywords)
# Matching is case-insensitive substring against the concatenated
# (name + title + description + domain) text.
NICHES: list[tuple[str, str, str, int, list[str]]] = [
    # Games & Entertainment
    ("animators", "Аниматори / парти агенции", "Игри и забавления", 10, [
        "аниматор", "парти агенция", "клоун", "шоу програм",
        "magic show", "фокусник", "big bubble", "балон шоу",
        "dj за детско", "party talent",
    ]),
    ("party_center", "Детски парти център", "Игри и забавления", 10, [
        "парти център", "детски парти център", "детски център",
        "детски клуб", "парти зала", "playground", "kids land",
        "детски кът", "игротек",
    ]),

    # Celebrations & Events
    ("photographer", "Фотограф", "Тържества и събития", 10, [
        "фотограф", "photograph", "детска фотография",
    ]),
    ("party_decor", "Декорация / балони", "Тържества и събития", 9, [
        "балони", "декорация", "украса за", "party decor", "балонена къща",
    ]),

    # Sport
    ("martial_arts", "Бойни изкуства", "Спорт и движение", 9, [
        "карате", "айкидо", "aikido", "таекуондо", "taekwondo",
        "винг чун", "wing chun", "wing tsung",
        "джу джицу", "jiu jitsu", "jiu-jitsu", "jiujitsu",
        "кикбокс", "kickbox", "муай тай", "muay thai",
        "капоейра", "capoeira", "джудо", "judo", "бойн",
        "кунг фу", "kung fu", "бокс", "самбо", "фехтовк",
        "тай чи", "tai chi", "хапкидо", "кумдо",
        "mma", "fight club", "доджо", "додж", "додо",
        "борба", "wrestling",
    ]),
    ("dance_ballet", "Танци / балет", "Спорт и движение", 9, [
        "балет", "ballet", "танц", "tanci", "dance", "школа по танц",
        "zumba", "зумба", "хореограф", "латино танц",
        "tango", "танго", "народни танци",
    ]),
    ("football", "Футбол", "Спорт и движение", 9, [
        "футбол", "football", "soccer", "фк ", "fc ",
    ]),
    ("swimming", "Плуване", "Спорт и движение", 9, [
        "плуване", "swim", "басейн", "аква", "waterpolo",
    ]),
    ("basketball", "Баскетбол", "Спорт и движение", 9, [
        "баскет", "basket",
    ]),
    ("volleyball", "Волейбол", "Спорт и движение", 9, [
        "волейбол", "volley",
    ]),
    ("tennis", "Тенис", "Спорт и движение", 9, [
        "тенис", "tennis",
    ]),
    ("ice_skating", "Ледена пързалка / кънки", "Спорт и движение", 9, [
        "ледена пързалка", "кънки", "хокей", "hockey",
        "фигурно пързаляне", "ice centre", "ice center",
    ]),
    ("athletics", "Лека атлетика", "Спорт и движение", 9, [
        "лека атлетика", "athletics", "track and field",
    ]),
    ("gymnastics", "Гимнастика", "Спорт и движение", 9, [
        "гимнастик", "gymnastic",
    ]),
    ("climbing", "Катерене / алпинизъм", "Спорт и движение", 9, [
        "катерене", "climbing", "алпинизъм", "boulder",
    ]),
    ("sport_general", "Спортен клуб (общо)", "Спорт и движение", 7, [
        "спортен клуб", "sport club", "спортен център", "sport center",
        "спортен комплекс", "sport complex",
        "спортна академия", "fitness", "фитнес",
        "федерация по", "sports federation",
    ]),

    # Learning & Skills
    ("kindergarten", "Детска градина / ясла", "Учене и умения", 10, [
        "детска градина", "детска ясла", "чдг", "чдя",
        "kindergarten", "nursery", "daycare", "montessori",
        "edutainment", "bilingual", "multilingual children",
    ]),
    ("private_school", "Частно училище / лицей", "Учене и умения", 10, [
        "частно училище", "частен лицей", "частно основно", "частно средно",
        "лицей", "гимназия", "соу",
        "основно училище", "средно училище",
        "private school", "primary school", "secondary school",
        "high school", "international school",
    ]),
    ("afterschool", "Занималня", "Учене и умения", 10, [
        "занималн", "after school", "brain academy",
        "целодневна подготовка", "афтършкул",
        "ментална аритметика", "smartykids", "smarty kids",
    ]),
    ("language_school", "Езикова школа", "Учене и умения", 10, [
        "езиков", "language", "курсове по английски", "курсове по немски",
        "курсове по испански", "курсове по френски", "курсове по италиански",
        "курсове по руски", "english school", "английски език",
        "немски език", "испански език", "френски език",
        "ielts", "toefl", "cambridge", "cae", "fce", "cpe",
    ]),
    ("music_school", "Музикална школа", "Учене и умения", 10, [
        "музикална школа", "music school", "music center", "music lab",
        "музикален център", "музикално студио", "музикално обучителн",
        "уроци по пиано", "уроци по китара", "уроци по цигулка",
        "уроци по пеене", "уроци по гайда", "уроци по музик",
        "уроци по барабани", "уроци по барабан",
        "solfege", "солфеж", "venera music", "city music", "music box",
        "rhythm-academy", "rhythm academy", "drum cover", "drum lessons",
        "певчески", "искам да пея",
    ]),
    ("art_school", "Арт школа / рисуване", "Учене и умения", 10, [
        "уроци по рисуване", "art school", "школа по рисуване",
        "арт студио", "керамика", "drawing class", "рисуване за",
    ]),
    ("driving_school", "Автошкола", "Учене и умения", 10, [
        "автошкола", "шофьорски курс", "driving school",
    ]),
    ("private_lessons_subj", "Частни уроци (предметни)", "Учене и умения", 8, [
        "частни уроци", "уроци по математика", "уроци по български",
        "уроци по биология", "уроци по химия",
        "подготовка за нво", "подготовка за матур", "матура по",
        "нво", "кандидат-студент", "учебен център",
    ]),
    ("educational_center", "Учебен център (общо)", "Учене и умения", 7, [
        "учебен център", "образователен център",
        "center for learning", "learning center",
        "академия", "academy", "academi",
    ]),

    # Specialists
    ("speech_therapist", "Логопед", "Специалисти", 10, [
        "логопед", "speech therap", "speechtherap", "логопедичен", "logoped",
        "езиково-говорна",
    ]),
    ("child_psychologist", "Детски психолог / психотерапевт", "Специалисти", 10, [
        "детски психолог", "детски психотерап", "child psycholog",
        "психомоторик", "арт терапия", "арттерапия",
        "детско развитие", "детска психология", "детски коуч",
        # Generic psychologist/psychotherapist terms — all records in this
        # dataset were scraped from the "детски психолог" search query, so
        # even without the "детски" qualifier they either work with children
        # directly or serve parents / families.
        "психолог", "психотерапев", "психотерапия",
        "psycholog", "psychotherap",
        "психологическо консултиране", "психологична помощ",
        "психологично консултиране", "психиатр",
        "семейни констелации", "фамилни констелации",
        "хипнотерап", "хипноза",
    ]),
    ("therapy_center", "Терапевтичен център", "Специалисти", 9, [
        "терапевтичен център", "ерготерапия", "occupational therap",
        "сензорна интеграция", "сензорно-интегративна",
        "център за детско развитие", "развитие и игра",
        "център за развитие", "психологически кът",
    ]),

    # Culture
    ("theatre_opera", "Театър / опера", "Култура", 9, [
        "опера", "opera", "театър", "theatre", "theater", "филхармон",
    ]),
    ("museum", "Музей", "Култура", 9, [
        "музей", "museum",
    ]),
    ("community_cultural_center", "Читалище", "Култура", 9, [
        "читалище",
    ]),

    # Goods
    ("kids_clothing_shoes", "Детски дрехи / обувки", "Стоки", 8, [
        "детски дрехи", "детски дрешки", "бебешки дрехи", "бебешки дрешки",
        "детски обувки", "бебешки обувки", "детски магазин",
        "kids shoes", "kids clothes", "baby clothes", "bebeshki dreshki",
        "боси обувки", "боти", "ботуши", "маратонки за деца",
    ]),
    ("kids_toys", "Детски играчки", "Стоки", 8, [
        "детски играчки", "играчк", "toys", "toy store",
    ]),
    ("baby_goods", "Бебешки стоки", "Стоки", 8, [
        "бебешки магазин", "бебешки мебели", "бебешки кошар",
        "бебешки колич", "кошара", "креватче", "бебешки стоки",
        "baby shop", "бебешки гнезд",
    ]),
    ("sports_gear", "Спортна екипировка", "Стоки", 8, [
        "спортна екипировка", "екипировка за", "танцова екипировка",
        "ballet shop", "dance shop", "danceshop", "boxova",
        "бойна екипировка",
    ]),
    ("kids_food_catering", "Детска кухня / кетъринг", "Стоки", 8, [
        "детска кухня", "детско меню", "детски кетъринг",
        "kids catering", "kids food", "био детска", "bio детска", "дкх",
        "кетъринг", "catering",
    ]),
    ("kids_books", "Детски книги / издателство", "Стоки", 8, [
        "детски книг", "kids book", "children's book",
        "детско издателство", "детски приказки",
        "издателство", "book publisher",
    ]),

    # Home care
    ("babysitter", "Детегледачка", "Домашна грижа и помощ", 9, [
        "детегледач", "бавач", "nanny", "babysitter", "au pair",
    ]),
]

NICHE_ORDER = {n[0]: i for i, n in enumerate(NICHES)}  # definition order
NICHE_META = {n[0]: {"label_bg": n[1], "sphere": n[2], "priority": n[3]} for n in NICHES}

# Niches that are "fallback" generalists — dropped when a more specific sibling in the same sphere matched.
FALLBACK_RULES = [
    ("sport_general", "Спорт и движение"),
    ("educational_center", "Учене и умения"),
    ("private_lessons_subj", "Учене и умения"),
]


# ---------- utility ----------

WS_RE = re.compile(r"\s+")
NON_DIGIT_RE = re.compile(r"\D+")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def norm_domain(d: str | None) -> str:
    if not d:
        return ""
    d = d.strip().lower()
    d = re.sub(r"^https?://", "", d)
    d = re.sub(r"^www\.", "", d)
    d = d.rstrip("/")
    return d


def norm_phone(p: str | None) -> str:
    """Return canonical phone (digits-only, E.164-ish) or empty string if unusable."""
    if not p:
        return ""
    digits = NON_DIGIT_RE.sub("", p)
    if len(digits) < 7:
        return ""
    if digits.startswith("00359") and len(digits) == 14:
        return "+" + digits[2:]
    if digits.startswith("359") and len(digits) == 12:
        return "+" + digits
    if digits.startswith("0") and len(digits) == 10:
        return "+359" + digits[1:]
    return digits


def split_multi(value: str | None) -> list[str]:
    """Split a multi-value cell like '+359..., 0888...' into parts."""
    if not value:
        return []
    parts = re.split(r"[,;|]+", value)
    return [p.strip() for p in parts if p and p.strip()]


def norm_emails(raw_values: Iterable[str | None]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in raw_values:
        if not raw:
            continue
        for piece in split_multi(raw):
            email = piece.strip().lower()
            if not EMAIL_RE.match(email):
                continue
            if email in seen:
                continue
            seen.add(email)
            out.append(email)
    return out


def norm_phones(raw_values: Iterable[str | None]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in raw_values:
        if not raw:
            continue
        for piece in split_multi(raw):
            p = norm_phone(piece)
            if not p or p in seen:
                continue
            seen.add(p)
            out.append(p)
    return out


def norm_url(u: str | None) -> str:
    if not u:
        return ""
    return u.strip().rstrip("/")


def dedup_urls(values: Iterable[str | None]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for v in values:
        u = norm_url(v)
        if not u or u.lower() in seen:
            continue
        seen.add(u.lower())
        out.append(u)
    return out


TITLE_SUFFIX_RE = re.compile(
    r"\s*[-–|:]\s*(my site|home page|home|начало|контакти|галерия|за нас|"
    r"политика за поверителност|общи условия|цени|welcome page|contact)\s*$",
    re.IGNORECASE,
)


def clean_title(t: str | None) -> str:
    if not t:
        return ""
    s = WS_RE.sub(" ", t).strip()
    # strip trailing boilerplate segments
    for _ in range(3):
        new = TITLE_SUFFIX_RE.sub("", s).strip()
        if new == s:
            break
        s = new
    return s


def best_name(company_name: str | None, website_title: str | None, full_name: str | None) -> str:
    for candidate in (company_name, website_title, full_name):
        c = (candidate or "").strip()
        if c:
            return clean_title(c) if candidate is website_title else WS_RE.sub(" ", c)
    return ""


# ---------- loading ----------

def load_rows(xlsx_path: Path) -> tuple[list[str], list[dict[str, object]]]:
    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    try:
        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)
        try:
            header = list(next(rows_iter))
        except StopIteration:
            return [], []
        headers = [h if h is not None else "" for h in header]
        records: list[dict[str, object]] = []
        for raw in rows_iter:
            if not any(raw):
                continue
            rec = {headers[i]: raw[i] for i in range(min(len(headers), len(raw)))}
            records.append(rec)
        return headers, records
    finally:
        wb.close()


# ---------- classification ----------

def classify(text: str) -> list[str]:
    """Return list of niche keys that match, sorted by priority DESC then definition order."""
    text_l = text.lower()
    matched: list[str] = []
    for key, _label, _sphere, _priority, keywords in NICHES:
        for kw in keywords:
            if kw in text_l:
                matched.append(key)
                break

    # Drop fallback niches when a more-specific sibling in the same sphere matched.
    if matched:
        matched_set = set(matched)
        for fb_key, fb_sphere in FALLBACK_RULES:
            if fb_key not in matched_set:
                continue
            specific_peers = [
                k for k in matched_set
                if k != fb_key
                and NICHE_META[k]["sphere"] == fb_sphere
                and NICHE_META[k]["priority"] > NICHE_META[fb_key]["priority"]
            ]
            if specific_peers:
                matched = [m for m in matched if m != fb_key]

    matched.sort(key=lambda k: (-NICHE_META[k]["priority"], NICHE_ORDER[k]))
    return matched


# ---------- dedup + merge ----------

def merge_record(dst: dict, src: dict) -> None:
    """Merge src record into dst (in-place). Scalars keep first; lists extend unique."""
    for k, v in src.items():
        if k in ("phones", "emails", "contact_names", "facebook", "instagram",
                 "linkedin", "niches_all", "spheres_all", "_domains"):
            existing = dst.setdefault(k, [])
            for item in v or []:
                if item and item not in existing:
                    existing.append(item)
        elif k == "merged_from":
            dst[k] = dst.get(k, 0) + (v or 0)
        else:
            if not dst.get(k):
                dst[k] = v


def key_for_lookup(rec: dict, domain_to_key: dict, phone_to_key: dict, email_to_key: dict) -> str | None:
    """Return existing canonical key if this record matches by domain/phone/email; else None."""
    for d in rec.get("_domains", []):
        if not d:
            continue
        k = domain_to_key.get(d)
        if k:
            return k
    for p in rec.get("phones", []):
        k = phone_to_key.get(p)
        if k:
            return k
    for e in rec.get("emails", []):
        k = email_to_key.get(e)
        if k:
            return k
    return None


def run(xlsx_path: Path, out_csv: Path, out_report: Path) -> dict:
    headers, rows = load_rows(xlsx_path)
    if not rows:
        print(f"[warn] no data rows in {xlsx_path}", file=sys.stderr)

    total_raw = len(rows)

    # Build a normalized record per raw row.
    norm_rows: list[dict] = []
    for r in rows:
        domain = norm_domain(r.get("domain_y") or r.get("domain_x"))
        emails = norm_emails([r.get("email")])
        phones = norm_phones([r.get("company_phone"), r.get("company_phones"),
                              r.get("contact_phone"), r.get("contact_phones")])

        # Drop completely unusable records (no domain, no phone, no email).
        if not domain and not phones and not emails:
            continue

        website_title = (r.get("website_title") or "").strip()
        company_name = (r.get("company_name") or "").strip()
        full_name = (r.get("full_name") or "").strip()
        website_desc = (r.get("website_description") or "").strip()

        text_for_match = " ".join([
            company_name, website_title, website_desc, domain,
        ])
        niches = classify(text_for_match)
        spheres: list[str] = []
        for nk in niches:
            sphere = NICHE_META[nk]["sphere"]
            if sphere not in spheres:
                spheres.append(sphere)

        rec = {
            "_domains": [domain] if domain else [],
            "domain": domain,
            "name_best": best_name(company_name, website_title, full_name),
            "emails": emails,
            "phones": phones,
            "contact_names": [full_name] if full_name else [],
            "title": (r.get("title") or "").strip(),
            "facebook": dedup_urls([r.get("company_facebook"), r.get("contact_facebook")]),
            "instagram": dedup_urls([r.get("company_instagram"), r.get("contact_instagram")]),
            "linkedin": dedup_urls([r.get("company_linkedin"), r.get("contact_linkedin")]),
            "website_title": clean_title(website_title),
            "website_description": website_desc[:500],
            "has_gtm": bool(r.get("website_has_gtm")),
            "has_fb_pixel": bool(r.get("website_has_fb_pixel")),
            "website_generator": (r.get("website_generator") or "").strip(),
            "location_link": (r.get("location_link") or "").strip(),
            "niches_all": niches,
            "spheres_all": spheres,
            "merged_from": 1,
        }
        norm_rows.append(rec)

    # Dedup pass.
    canonical: "OrderedDict[str, dict]" = OrderedDict()
    domain_to_key: dict[str, str] = {}
    phone_to_key: dict[str, str] = {}
    email_to_key: dict[str, str] = {}

    for rec in norm_rows:
        key = key_for_lookup(rec, domain_to_key, phone_to_key, email_to_key)
        if key is None:
            key = rec["domain"] or (rec["phones"][0] if rec["phones"] else rec["emails"][0])
        if key not in canonical:
            canonical[key] = {}
        merge_record(canonical[key], rec)

        # Update lookup indices for merged record.
        merged = canonical[key]
        for d in merged.get("_domains", []):
            if d:
                domain_to_key.setdefault(d, key)
        for p in merged.get("phones", []):
            phone_to_key.setdefault(p, key)
        for e in merged.get("emails", []):
            email_to_key.setdefault(e, key)

    # Re-classify after merge (combines text from potentially richer merged rec).
    for rec in canonical.values():
        text = " ".join([
            rec.get("name_best", ""),
            rec.get("website_title", ""),
            rec.get("website_description", ""),
            rec.get("domain", ""),
        ])
        merged_niches = classify(text)
        # union with any niches discovered per-row (in case one merged row had niche hints
        # the merged text lost — e.g. a distinct company_name that became secondary).
        for n in rec.get("niches_all", []):
            if n not in merged_niches:
                merged_niches.append(n)
        # Resort deterministically.
        merged_niches.sort(key=lambda k: (-NICHE_META[k]["priority"], NICHE_ORDER[k]))
        rec["niches_all"] = merged_niches
        rec["spheres_all"] = []
        for nk in merged_niches:
            s = NICHE_META[nk]["sphere"]
            if s not in rec["spheres_all"]:
                rec["spheres_all"].append(s)

    # Write CSV.
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "niche_primary", "sphere_primary",
        "niches_all", "spheres_all",
        "name_best", "domain",
        "phones", "emails",
        "contact_names", "title",
        "facebook", "instagram", "linkedin",
        "website_title", "website_description",
        "has_gtm", "has_fb_pixel", "website_generator",
        "merged_from", "location_link",
    ]

    def sort_key(rec: dict):
        sphere = rec["spheres_all"][0] if rec["spheres_all"] else "zzz"
        niche = rec["niches_all"][0] if rec["niches_all"] else "other"
        return (sphere, niche, rec.get("name_best", "").lower())

    sorted_recs = sorted(canonical.values(), key=sort_key)

    niche_counts: dict[str, int] = {}
    sphere_counts: dict[str, int] = {}
    with out_csv.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for rec in sorted_recs:
            niches = rec.get("niches_all") or ["other"]
            spheres = rec.get("spheres_all") or ["Друго"]
            primary_n = niches[0]
            primary_s = spheres[0]
            niche_counts[primary_n] = niche_counts.get(primary_n, 0) + 1
            sphere_counts[primary_s] = sphere_counts.get(primary_s, 0) + 1
            writer.writerow({
                "niche_primary": primary_n,
                "sphere_primary": primary_s,
                "niches_all": "; ".join(niches),
                "spheres_all": "; ".join(spheres),
                "name_best": rec.get("name_best", ""),
                "domain": rec.get("domain", ""),
                "phones": "; ".join(rec.get("phones", [])),
                "emails": "; ".join(rec.get("emails", [])),
                "contact_names": "; ".join(rec.get("contact_names", [])),
                "title": rec.get("title", ""),
                "facebook": "; ".join(rec.get("facebook", [])),
                "instagram": "; ".join(rec.get("instagram", [])),
                "linkedin": "; ".join(rec.get("linkedin", [])),
                "website_title": rec.get("website_title", ""),
                "website_description": rec.get("website_description", ""),
                "has_gtm": rec.get("has_gtm", False),
                "has_fb_pixel": rec.get("has_fb_pixel", False),
                "website_generator": rec.get("website_generator", ""),
                "merged_from": rec.get("merged_from", 1),
                "location_link": rec.get("location_link", ""),
            })

    report = {
        "input": str(xlsx_path),
        "output_csv": str(out_csv),
        "total_raw_rows": total_raw,
        "rows_after_drop_unusable": len(norm_rows),
        "unique_prospects": len(canonical),
        "niche_primary_counts": dict(sorted(niche_counts.items(), key=lambda x: -x[1])),
        "sphere_primary_counts": dict(sorted(sphere_counts.items(), key=lambda x: -x[1])),
    }
    out_report.parent.mkdir(parents=True, exist_ok=True)
    out_report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean + dedupe + segment prospect xlsx.")
    parser.add_argument("--input", default="tmp/outscraper.xlsx")
    parser.add_argument("--output", default="tmp/prospects_clean.csv")
    parser.add_argument("--report", default="tmp/prospects_clean_report.json")
    args = parser.parse_args()

    report = run(Path(args.input), Path(args.output), Path(args.report))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
