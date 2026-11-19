#!/usr/bin/env python3
"""KnowD1 food data browser: two tabs (Open Food Facts Greece | OpenNutrition), deterministic search.

OFF tab = products sold in Greece OR with a Greek GS1 barcode (520-521).

Run from anywhere (paths are resolved relative to this file):

    python3 -I tools/browser/foods_browser.py build    # one-time, a few minutes -> work/browser.sqlite
    python3 -I tools/browser/foods_browser.py serve    # http://127.0.0.1:8765

Stage 05 category pages: /category-review (answer key), /category-results (each model vs the answer key on the
200 test products) and /category-test (live tester; needs the model service in .venv:
    HF_HUB_OFFLINE=1 .venv/bin/python -I stages/05-category-model/serve_models.py   # http://127.0.0.1:8766 )

Search rules (deterministic: same query -> same rows in the same order):
  * Text: the query is normalized (lower-case, Greek accents/diacritics removed, final sigma = sigma,
    apostrophes removed, other punctuation -> space) and split into words. A row matches when EVERY
    query word is the START of a word in the row (SQLite FTS5 prefix match: "γιαο" finds "γιαούρτι",
    but "cola" no longer finds "chocolate").
      - OFF searches all product names (every language), generic names and brands.
      - OpenNutrition searches the name and alternate names.
  * Barcode: a query of 8-14 digits only is an exact barcode lookup (leading zeros ignored); filters are ignored.
  * Order: BM25 relevance (a hit in the name counts 4x, in the brand 2x, in other names 1x), then
    popularity (OFF scans), then name A->Z, then ID. An empty query lists all rows A->Z.
    No fuzzy matching (typos are not corrected).

Only Python's standard library + pyarrow (for reading the parquet file during `build`).
"""
import argparse
import csv
import json
import math
import re
import sqlite3
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.request
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent  # the Foods/ folder
OFF_PARQUET = ROOT / "openfoodfacts" / "food.parquet"
ON_TSV = ROOT / "opennutrition-dataset-2025.1" / "opennutrition_foods.tsv"
DB_PATH = ROOT / "work" / "browser.sqlite"
INDEX_HTML = HERE / "index.html"
NO_IMAGE_SVG = HERE / "no-image.svg"
PILOT_HTML = HERE / "photo_pilot.html"
CATREV_HTML = HERE / "category_review.html"
CATRES_HTML = HERE / "category_results.html"
CATTEST_HTML = HERE / "category_test.html"
CATREV_DIR = ROOT / "stages" / "05-category-model" / "out"  # written by stages/05-category-model/bench.py
CATS_JSON = ROOT / "tools" / "categories" / "categories.json"
ICONS_HTML = HERE / "icons.html"
ICONS_JSON = ROOT / "tools" / "categories" / "icons.json"  # built by tools/categories/build_icons.py
PILOT_RUNS = {  # photo pilot runs: name -> output folder
    "cutout": ROOT / "work" / "photo_pilot",  # E11 background removal, tools/photos/cleanup_pilot.py
    "crop": ROOT / "work" / "photo_pilot_crop",  # E14 OFF crop model, tools/photos/crop_pilot.py
    "trial50": ROOT / "stages" / "00-trial-50" / "out",  # v2 pipeline trial, stages/00-trial-50/run_trial.py
    "cutoutall": ROOT / "stages" / "01-cutout-all" / "out",  # trial 2: run_trial.py --variant cutout-all
    "bigmodel": ROOT / "stages" / "02-big-model" / "out",  # trial 3: run_trial.py --variant big
    "bitefix": ROOT / "stages" / "03-bite-fix" / "out",  # trial 4: run_trial.py --variant bitefix
}
PILOT_SCRIPTS = {"cutout": "tools/photos/cleanup_pilot.py", "crop": "tools/photos/crop_pilot.py",
                 "trial50": "stages/00-trial-50/run_trial.py",
                 "cutoutall": "stages/00-trial-50/run_trial.py --variant cutout-all",
                 "bigmodel": "stages/00-trial-50/run_trial.py --variant big",
                 "bitefix": "stages/00-trial-50/run_trial.py --variant bitefix"}
PAGE_SIZE = 50
NO_NAME_SORT = "￿"  # rows without a name sort last

# ---------------------------------------------------------------------------
# Normalization (shared by build and search, so both sides always agree)
# ---------------------------------------------------------------------------
_APOSTROPHES = re.compile(r"['’‘`]")
_PUNCT = re.compile(r"[^\w\s]|_")
_GREEK = re.compile("[Ͱ-Ͽἀ-῿]")
_BARCODE = re.compile(r"^\d{8,14}$")


def norm(text):
    """Lower-case, strip accents/diacritics (Greek tonos too), fold final sigma, drop punctuation."""
    if not text:
        return ""
    s = unicodedata.normalize("NFKD", text.casefold())  # casefold also turns final sigma into sigma
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = _APOSTROPHES.sub("", s)
    s = _PUNCT.sub(" ", s)
    return " ".join(s.split())


def code_norm(code):
    code = (code or "").strip()
    return (code.lstrip("0") or code) if code.isdigit() else code


def is_greek_gs1(code):
    code = (code or "").strip()
    if not code.isdigit():
        return False
    prefix = code[:3] if len(code) == 8 else code.zfill(13)[:3]
    return prefix in ("520", "521")


def json_safe(obj):
    """Replace NaN/Infinity (invalid in JSON for the browser) with None, recursively."""
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_safe(v) for v in obj]
    return obj


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
OFF_COLS = [
    "code", "product_name", "generic_name", "brands", "quantity", "serving_size", "serving_quantity",
    "nutrition_data_per", "nutriments", "countries_tags", "food_groups_tags", "categories_tags",
    "labels_tags", "stores", "lang", "completeness", "unique_scans_n", "scans_n",
    "data_quality_errors_tags", "data_quality_warnings_tags", "created_t", "last_modified_t",
    "ingredients_text", "allergens_tags", "traces_tags", "nova_group", "nutriscore_grade", "link",
]


def pick_off_name(names):
    """Greek first, then any Greek-script name, then the main-language name, then English, then anything."""
    names = [n for n in (names or []) if (n.get("text") or "").strip()]
    checks = (
        lambda n: n["lang"] == "el",
        lambda n: _GREEK.search(n["text"]),
        lambda n: n["lang"] == "main",
        lambda n: n["lang"] == "en",
        lambda n: True,
    )
    for check in checks:
        for n in names:
            if check(n):
                return n["text"].strip(), n["lang"]
    return "", ""


# OFF product photos are hosted online; the parquet only lists them (key, rev, sizes).
IMG_BASE = "https://images.openfoodfacts.org/images/products"
PHOTO_KINDS = ("front", "nutrition", "ingredients", "packaging")


def image_folder(code):
    """OFF rule (verified): numeric codes are zero-padded to 13 digits, then split 3/3/3/rest."""
    c = code.zfill(13) if code.isdigit() else code
    return f"{c[:3]}/{c[3:6]}/{c[6:9]}/{c[9:]}" if c.isdigit() and len(c) > 9 else c


def _first_size(sizes, prefs, default):
    return next((p for p in prefs if (sizes or {}).get(p)), default)


def off_photos(code, images, lang):
    """Return (thumb_url, {kind: {key, thumb, medium, full}}) for one OFF product.

    Selected photos (front/nutrition/ingredients/packaging) prefer Greek, then the product's
    language, then English. Products with only unassigned uploads get their first upload.
    """
    images = images or []
    folder = f"{IMG_BASE}/{image_folder(code)}"
    selected = {x["key"]: x for x in images if x.get("key") and not x["key"].isdigit() and x.get("rev") is not None}
    photos = {}
    for kind in PHOTO_KINDS:
        keys = sorted(k for k in selected if k == kind or k.startswith(kind + "_"))
        if not keys:
            continue
        key = next((k for k in (f"{kind}_el", f"{kind}_{lang}", f"{kind}_en", kind) if k in selected), keys[0])
        x = selected[key]
        stem = f"{folder}/{key}.{x['rev']}"
        photos[kind] = {
            "key": key,
            "thumb": f"{stem}.{_first_size(x.get('sizes'), ('200', '400', '100'), '400')}.jpg",
            "medium": f"{stem}.{_first_size(x.get('sizes'), ('400', 'full'), '400')}.jpg",
            "full": f"{stem}.full.jpg",
        }
    thumb = photos.get("front", {}).get("thumb")
    if not photos:
        uploads = sorted((x for x in images if (x.get("key") or "").isdigit()), key=lambda x: int(x["key"]))
        if uploads:
            x = uploads[0]
            medium = f"{folder}/{x['key']}.{_first_size(x.get('sizes'), ('400', '100'), '400')}.jpg"
            photos["photo"] = {"key": x["key"], "thumb": medium, "medium": medium, "full": f"{folder}/{x['key']}.jpg"}
    if not thumb and photos:
        thumb = next(iter(photos.values()))["thumb"]
    return thumb, photos


def build_off(con, on_codes):
    """Greek-market OFF table. Also returns photo info for OFF products whose barcode is in `on_codes`
    (OpenNutrition grocery items), as a list of (thumb, photos_json, code_norm)."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    con.execute("""CREATE TABLE off(
        id TEXT PRIMARY KEY, code_norm TEXT, name TEXT, name_lang TEXT, brand TEXT,
        sort_key TEXT, search TEXT, sold_gr INT, gs1_gr INT,
        kcal REAL, carbs REAL, sugars REAL, fiber REAL, protein REAL, fat REAL, salt REAL,
        per TEXT, scans INT, thumb TEXT, photos TEXT, raw TEXT)""")
    pf = pq.ParquetFile(OFF_PARQUET)
    total_groups = pf.metadata.num_row_groups
    inserted = skipped_dupes = 0
    on_photos = []
    t0 = time.time()
    for i in range(total_groups):
        head = pf.read_row_group(i, columns=["code", "countries_tags"])
        codes = head["code"].to_pylist()
        idx = [
            j for j, (code, countries) in enumerate(zip(codes, head["countries_tags"].to_pylist()))
            if "en:greece" in (countries or []) or is_greek_gs1(code)
        ]
        idx_on = [j for j, code in enumerate(codes) if code and code_norm(code) in on_codes]
        if idx_on:
            for r in pf.read_row_group(i, columns=["code", "lang", "images"]).take(pa.array(idx_on)).to_pylist():
                code = r["code"].strip()
                thumb, photos = off_photos(code, r["images"], r["lang"])
                if photos:
                    on_photos.append((thumb, json.dumps(photos), code_norm(code)))
        if idx:
            rows = pf.read_row_group(i, columns=OFF_COLS + ["images"]).take(pa.array(idx)).to_pylist()
            batch = []
            for r in rows:
                code = (r["code"] or "").strip()
                if not code:
                    continue
                thumb, photos = off_photos(code, r.pop("images"), r["lang"])
                name, lang = pick_off_name(r["product_name"])
                if not name:
                    name, lang = pick_off_name(r["generic_name"])
                texts = [n.get("text") or "" for n in (r["product_name"] or []) + (r["generic_name"] or [])]
                countries = set(r["countries_tags"] or [])
                nut = {n["name"]: n["100g"] for n in (r["nutriments"] or []) if n.get("100g") is not None}
                batch.append((
                    code, code_norm(code), name, lang, (r["brands"] or "").strip(),
                    norm(name) or NO_NAME_SORT, norm(" ".join(texts + [r["brands"] or ""])),
                    int("en:greece" in countries), int(is_greek_gs1(code)),
                    nut.get("energy-kcal"), nut.get("carbohydrates"), nut.get("sugars"), nut.get("fiber"),
                    nut.get("proteins"), nut.get("fat"), nut.get("salt"),
                    r["nutrition_data_per"], r["unique_scans_n"],
                    thumb, json.dumps(photos) if photos else None,
                    json.dumps(json_safe(r), ensure_ascii=False, default=str),
                ))
            before = con.total_changes
            con.executemany("INSERT OR IGNORE INTO off VALUES (" + ",".join("?" * 21) + ")", batch)
            added = con.total_changes - before
            inserted += added
            skipped_dupes += len(batch) - added
        if i % 400 == 0 or i == total_groups - 1:
            print(f"  OFF row group {i + 1}/{total_groups} - {inserted:,} products - {time.time() - t0:.0f}s", flush=True)
    print(f"  OFF done: {inserted:,} products ({skipped_dupes} duplicate barcodes skipped)")
    return on_photos


ON_JSON_COLS = ("alternate_names", "source", "serving", "nutrition_100g", "labels", "package_size", "ingredient_analysis")


def fmt_qty(q):
    return f"{q:g}" if isinstance(q, (int, float)) else str(q or "")


def build_on(con):
    con.execute("""CREATE TABLE on_foods(
        id TEXT PRIMARY KEY, code_norm TEXT, name TEXT, type TEXT, brand TEXT,
        sort_key TEXT, search TEXT, serving TEXT,
        kcal REAL, carbs REAL, sugars REAL, fiber REAL, protein REAL, fat REAL, sodium_mg REAL,
        thumb TEXT, photos TEXT, raw TEXT)""")
    csv.field_size_limit(10**9)
    t0 = time.time()
    batch, count = [], 0
    with open(ON_TSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE):
            rec = {}
            for k, v in row.items():
                if k in ON_JSON_COLS and v:
                    try:
                        rec[k] = json.loads(v)
                    except ValueError:
                        rec[k] = v
                else:
                    rec[k] = v or None
            name = (rec["name"] or "").strip()
            typ = rec["type"] or ""
            brand = name.rsplit(" by ", 1)[1].strip() if typ == "grocery" and " by " in name else None
            alt = rec["alternate_names"] if isinstance(rec["alternate_names"], list) else []
            sv = rec["serving"] if isinstance(rec["serving"], dict) else {}
            common, metric = sv.get("common") or {}, sv.get("metric") or {}
            serving = " ".join(p for p in (fmt_qty(common.get("quantity")), common.get("unit") or "") if p)
            if metric:
                serving = f"{serving} = {fmt_qty(metric.get('quantity'))} {metric.get('unit') or ''}".strip(" =")
            nut = rec["nutrition_100g"] if isinstance(rec["nutrition_100g"], dict) else {}
            batch.append((
                rec["id"], code_norm(rec["ean_13"]) if rec["ean_13"] else None, name, typ, brand,
                norm(name) or NO_NAME_SORT, norm(" ".join([name] + [a for a in alt if isinstance(a, str)])), serving,
                nut.get("calories"), nut.get("carbohydrates"), nut.get("total_sugars"), nut.get("dietary_fiber"),
                nut.get("protein"), nut.get("total_fat"), nut.get("sodium"),
                None, None,  # thumb, photos: filled from OFF by barcode after the OFF scan
                json.dumps(json_safe(rec), ensure_ascii=False),
            ))
            if len(batch) >= 5000:
                con.executemany("INSERT INTO on_foods VALUES (" + ",".join("?" * 18) + ")", batch)
                count += len(batch)
                batch = []
                if count % 50000 == 0:
                    print(f"  OpenNutrition {count:,} rows - {time.time() - t0:.0f}s", flush=True)
    con.executemany("INSERT INTO on_foods VALUES (" + ",".join("?" * 18) + ")", batch)
    count += len(batch)
    print(f"  OpenNutrition done: {count:,} foods")


def build_fts(con):
    """One FTS5 index per tab. Columns: name, brand, other (= the full normalized search text).
    The text is already normalized by norm(), so build and query always agree. Rows are joined back
    by `id` (not rowid: VACUUM may renumber the rowids of the main tables)."""
    con.create_function("norm", 1, norm, deterministic=True)
    for tab in TABS.values():
        t = tab["table"]
        con.execute(f"""CREATE VIRTUAL TABLE {t}_fts USING fts5(id UNINDEXED, name, brand, other,
                        tokenize='unicode61 remove_diacritics 2', prefix='2 3')""")
        con.execute(f"INSERT INTO {t}_fts SELECT id, norm(name), norm(brand), search FROM {t}")


def build():
    for p in (OFF_PARQUET, ON_TSV):
        if not p.exists():
            sys.exit(f"Missing raw file: {p}")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = DB_PATH.with_suffix(".sqlite.tmp")
    tmp.unlink(missing_ok=True)
    con = sqlite3.connect(tmp)
    con.execute("PRAGMA journal_mode=OFF")
    con.execute("PRAGMA synchronous=OFF")
    t0 = time.time()
    print("Building OpenNutrition table…")
    build_on(con)
    con.execute("CREATE INDEX on_code ON on_foods(code_norm)")
    con.commit()
    on_codes = {c for (c,) in con.execute("SELECT code_norm FROM on_foods WHERE code_norm IS NOT NULL")}
    print("Building Open Food Facts table (sold in Greece + Greek barcodes) + photos for OpenNutrition barcodes…")
    on_photos = build_off(con, on_codes)
    con.executemany("UPDATE on_foods SET thumb = ?, photos = ? WHERE code_norm = ?", on_photos)
    print(f"  OpenNutrition grocery items with OFF photos: {len(on_photos):,}")
    con.commit()
    print("Indexing…")
    con.executescript("""
        CREATE INDEX off_sort ON off(sort_key, id);
        CREATE INDEX off_code ON off(code_norm);
        CREATE INDEX on_sort ON on_foods(sort_key, id);
        CREATE INDEX on_type_sort ON on_foods(type, sort_key, id);
        CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
    """)
    con.execute("INSERT INTO meta VALUES ('built_at', ?)", (time.strftime("%Y-%m-%d %H:%M"),))
    con.commit()
    print("Building full-text indexes (FTS5)…")
    build_fts(con)
    con.commit()
    con.execute("VACUUM")
    con.close()
    tmp.replace(DB_PATH)
    print(f"Done in {time.time() - t0:.0f}s -> {DB_PATH} ({DB_PATH.stat().st_size / 1e6:.0f} MB)")


# ---------------------------------------------------------------------------
# Search + HTTP server
# ---------------------------------------------------------------------------
TABS = {
    "off": {
        "table": "off",
        "cols": ["id", "thumb", "name", "name_lang", "brand", "sold_gr", "gs1_gr",
                 "kcal", "carbs", "sugars", "fiber", "protein", "fat", "salt", "per", "scans"],
        "filters": {"all": None, "sold_gr": "sold_gr = 1", "gs1_gr": "gs1_gr = 1"},
        "tiebreak": "t.scans DESC, ",  # popularity; NULL sorts last
    },
    "on": {
        "table": "on_foods",
        "cols": ["id", "thumb", "name", "type", "brand", "code_norm", "serving",
                 "kcal", "carbs", "sugars", "fiber", "protein", "fat", "sodium_mg"],
        "filters": {"all": None, "everyday": "type = 'everyday'", "prepared": "type = 'prepared'",
                    "restaurant": "type = 'restaurant'", "grocery": "type = 'grocery'"},
        "tiebreak": "",
    },
}
FTS_WEIGHTS = "0, 4.0, 2.0, 1.0"  # bm25() weight per FTS column: id (unindexed), name, brand, other


def fts_match(words, op="AND"):
    """FTS5 query: every word as a quoted prefix term. norm() has removed all punctuation, so a word
    can't contain a quote or FTS syntax."""
    return f" {op} ".join(f'"{w}"*' for w in words)


def connect_ro():
    return sqlite3.connect(DB_PATH.as_uri() + "?mode=ro", uri=True)


def search(tab, q, filt, page):
    cfg = TABS[tab]
    table, fts = cfg["table"], cfg["table"] + "_fts"
    q = (q or "").strip()
    words = norm(q).split()
    sql_from, where, params, order = f"{table} t", [], [], "t.sort_key, t.id"
    if _BARCODE.match(q):
        mode = "barcode"
        where.append("t.code_norm = ?")
        params.append(code_norm(q))
    else:
        mode = "text"
        if words:
            sql_from = f"{fts} JOIN {table} t ON t.id = {fts}.id"
            where.append(f"{fts} MATCH ?")
            params.append(fts_match(words))
            order = f"bm25({fts}, {FTS_WEIGHTS}), {cfg['tiebreak']}t.sort_key, t.id"
        clause = cfg["filters"].get(filt)
        if clause:
            where.append(clause)
    sql_where = (" WHERE " + " AND ".join(where)) if where else ""
    cols = ", ".join("t." + c for c in cfg["cols"])
    with closing(connect_ro()) as con:
        total = con.execute(f"SELECT COUNT(*) FROM {sql_from}{sql_where}", params).fetchone()[0]
        cur = con.execute(
            f"SELECT {cols} FROM {sql_from}{sql_where} ORDER BY {order} LIMIT ? OFFSET ?",
            params + [PAGE_SIZE, page * PAGE_SIZE],
        )
        rows = [dict(zip(cfg["cols"], r)) for r in cur.fetchall()]
    return {"mode": mode, "query_words": words if mode == "text" else [q],
            "ranked": mode == "text" and bool(words),
            "total": total, "page": page, "page_size": PAGE_SIZE, "rows": rows}


def item(tab, item_id):
    with closing(connect_ro()) as con:
        row = con.execute(f"SELECT raw, photos FROM {TABS[tab]['table']} WHERE id = ?", (item_id,)).fetchone()
    if not row:
        return None
    return {"id": item_id, "raw": json.loads(row[0]), "photos": json.loads(row[1]) if row[1] else {}}


def counts():
    with closing(connect_ro()) as con:
        out = {t: con.execute(f"SELECT COUNT(*) FROM {c['table']}").fetchone()[0] for t, c in TABS.items()}
        out["built_at"] = con.execute("SELECT value FROM meta WHERE key = 'built_at'").fetchone()[0]
    return out


# --- Photo pilots (E11 cut-out, E14 crop): manifest, images and good/bad reviews --------------
_PILOT_IMG = re.compile(r"^/pilot/(cutout|crop|trial50|cutoutall|bigmodel|bitefix)/(before|after)/([0-9A-Za-z_-]{1,40})\.jpg$")
_review_lock = threading.Lock()


def _read_reviews(folder):
    path = folder / "review.json"
    return json.loads(path.read_text()) if path.exists() else {}


def pilot_data(run):
    if run not in PILOT_RUNS:
        raise ValueError("unknown run")
    folder = PILOT_RUNS[run]
    manifest = folder / "manifest.json"
    if not manifest.exists():
        return {"error": f"Pilot not run yet. Run: .venv/bin/python -I {PILOT_SCRIPTS[run]}"}
    data = json.loads(manifest.read_text())
    data["run"] = run
    data["reviews"] = _read_reviews(folder)
    compare = data["summary"].get("compare_run")
    if compare in PILOT_RUNS and compare != run:  # e.g. the crop page also shows the cut-out verdicts
        data["compare_reviews"] = _read_reviews(PILOT_RUNS[compare])
    return data


def save_review(run, code, verdict):
    if verdict not in ("good", "bad", None):
        raise ValueError("verdict must be good, bad or null")
    with _review_lock:
        data = pilot_data(run)
        if "error" in data or code not in {it["code"] for it in data["items"]}:
            raise ValueError("unknown product")
        reviews = data["reviews"]
        if verdict is None:
            reviews.pop(code, None)
        else:
            reviews[code] = verdict
        folder = PILOT_RUNS[run]
        tmp = folder / "review.json.tmp"
        tmp.write_text(json.dumps(reviews, indent=1, sort_keys=True))
        tmp.replace(folder / "review.json")
    return reviews


# --- Stage 05: owner's answers for the category-model test (one category per sample product) ----------
_catrev_lock = threading.Lock()


def _choosable():
    cats = json.loads(CATS_JSON.read_text())["categories"]
    return [{"code": c["code"], "name": c["name"], "group": c["group"], "definition": c["definition"]}
            for c in cats if c.get("assignable", True)]


def catrev_data():
    sample_path, preds_path = CATREV_DIR / "sample.json", CATREV_DIR / "predictions.json"
    if not sample_path.exists() or not preds_path.exists():
        return {"error": "Test not run yet. Run: .venv/bin/python -I stages/05-category-model/bench.py run"}
    sample = json.loads(sample_path.read_text())
    preds = json.loads(preds_path.read_text())
    cand = {p["id"]: [] for p in sample}
    for info in preds.values():  # top-1 of every model and method; neutral order, no model names shown
        for by_pid in info["methods"].values():
            for pid, codes in by_pid.items():
                if pid in cand and codes and codes[0] not in cand[pid]:
                    cand[pid].append(codes[0])
    first = next(iter(preds.values()), None)
    if first:  # pad with the runner-ups of one classifier so there are usually 3+ choices
        for pid, codes in first["methods"].get("lr", {}).items():
            for c in codes[1:3]:
                if pid in cand and c not in cand[pid] and len(cand[pid]) < 6:
                    cand[pid].append(c)
    thumbs = {}
    with closing(connect_ro()) as con:
        ids = [p["id"] for p in sample]
        for pid, thumb in con.execute(f"SELECT id, thumb FROM on_foods WHERE id IN ({','.join('?' * len(ids))})", ids):
            thumbs[pid] = thumb
    for p in sample:
        p["candidates"] = sorted(cand[p["id"]])
        p["thumb"] = thumbs.get(p["id"])
    review = json.loads((CATREV_DIR / "review.json").read_text()) if (CATREV_DIR / "review.json").exists() else {}
    by_claude = json.loads((CATREV_DIR / "answers_by_claude.json").read_text()) if (CATREV_DIR / "answers_by_claude.json").exists() else {}
    claude = {pid: v.get("unsure") or "" for pid, v in by_claude.items() if review.get(pid) == v["code"]}  # still Claude's
    return {"sample": sample, "categories": _choosable(), "answers": review, "claude": claude, "models_done": list(preds)}


def save_catrev(pid, code):
    allowed = {c["code"] for c in _choosable()}
    if code is not None and code not in allowed:
        raise ValueError("unknown category")
    with _catrev_lock:
        ids = {p["id"] for p in json.loads((CATREV_DIR / "sample.json").read_text())}
        if pid not in ids:
            raise ValueError("unknown product")
        path = CATREV_DIR / "review.json"
        answers = json.loads(path.read_text()) if path.exists() else {}
        if code is None:
            answers.pop(pid, None)
        else:
            answers[pid] = code
        tmp = CATREV_DIR / "review.json.tmp"
        tmp.write_text(json.dumps(answers, indent=1, sort_keys=True))
        tmp.replace(path)
    return answers


def icons_data():
    """Icon plan + categories + the stage-05 products with a category (owner's answer, else a model guess)."""
    plan = json.loads(ICONS_JSON.read_text())
    cats = {c["code"]: {"name": c["name"], "group": c["group"], "definition": c["definition"]}
            for c in json.loads(CATS_JSON.read_text())["categories"]}
    out = {"plan": plan, "categories": cats, "products": [], "guess_model": None}
    rev = catrev_data()
    if "error" in rev:
        return out
    preds = json.loads((CATREV_DIR / "predictions.json").read_text())
    key = "qwen3-0.6b" if "qwen3-0.6b" in preds else next(iter(preds), None)
    guess = preds[key]["methods"]["lr"] if key else {}
    out["guess_model"] = f"{key} classifier" if key else None
    for p in rev["sample"]:
        code = rev["answers"].get(p["id"])
        source = "Claude's answer" if p["id"] in rev["claude"] else "your answer"
        if not code and guess.get(p["id"]):
            code, source = guess[p["id"]][0], "model guess"
        out["products"].append({"id": p["id"], "name": p["name"], "type": p["type"], "thumb": p["thumb"],
                                "code": code, "source": source})
    return out


# --- Stage 05: model results on the 200 products, and the live tester ----------------------------------------
# The live tester forwards to stages/05-category-model/serve_models.py (a separate .venv process with the models).
sys.path.insert(0, str(CATREV_DIR.parent))
from vote import LEVELS, VOTE, VOTE_ORIGINAL, agreement, rank_vote  # noqa: E402  (standard library only)

CATRES_MEMBERS = {"qwen3-ft|lr": "Qwen3 fine-tuned classifier", "qwen3-ft|knn": "Qwen3 fine-tuned kNN",
                  "qwen3-0.6b|lr": "Qwen3 classifier", "qwen3-0.6b|knn": "Qwen3 kNN",
                  "arctic-l-v2|knn": "Arctic kNN", "arctic-l-v2|lr": "Arctic classifier"}
VARIANTS = {"title": "Title", "title+desc": "Title + description", "title+desc+ingr": "Title + description + ingredients"}
MODEL_SERVICE = "http://127.0.0.1:8766"
MODEL_START = "HF_HUB_OFFLINE=1 .venv/bin/python -I stages/05-category-model/serve_models.py"
_no_proxy = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # always talk to 127.0.0.1 directly


def _all_categories():
    return {c["code"]: {"name": c["name"], "group": c["group"]} for c in json.loads(CATS_JSON.read_text())["categories"]}


def catres_data():
    """Each test product: the answer, and every model's top 3 for each product text (out/text_variants.json)."""
    tv_path = CATREV_DIR / "text_variants.json"
    if not tv_path.exists():
        return {"error": "Not run yet. Run: HF_HUB_OFFLINE=1 .venv/bin/python -I stages/05-category-model/text_variants.py"}
    tv = json.loads(tv_path.read_text())
    rev = catrev_data()
    if "error" in rev:
        return rev
    members = {m: n for m, n in CATRES_MEMBERS.items() if f"{m.split('|')[0]}|title" in tv["predictions"]}
    vote = VOTE if all(f"{k}|{m}" in members for k, m in VOTE) else VOTE_ORIGINAL  # older results: original models
    products = []
    for p in rev["sample"]:
        pid, preds, agree = p["id"], {}, {}
        for v in VARIANTS:
            row = {m: tv["predictions"][f"{m.split('|')[0]}|{v}"][m.split("|")[1]][pid] for m in members}
            tops = [row[f"{k}|{m}"] for k, m in vote]
            row["vote"] = [c for c, _ in rank_vote(tops)][:3]
            preds[v], agree[v] = row, agreement(tops)
        answer = rev["answers"].get(pid)
        products.append({"id": pid, "type": p["type"], "name": p["name"], "description": p["description"],
                         "thumb": p["thumb"], "answer": answer,
                         "by": ("Claude" if pid in rev["claude"] else "owner") if answer else None,
                         "unsure": rev["claude"].get(pid) or "",
                         "texts": {v: tv["texts"][v][pid] for v in VARIANTS}, "preds": preds, "agree": agree})
    return {"categories": _all_categories(), "variants": VARIANTS,
            "training": {"set": tv.get("training_set"), "label": tv.get("training_label")},
            "members": {"vote": "3-model vote", **members},
            "vote_members": [CATRES_MEMBERS[f"{k}|{m}"] for k, m in vote], "levels": LEVELS, "products": products}


def _off_text(entries, main_lang, langs):
    """OFF multilingual field [{lang, text}] -> (text in the first available of `langs`, its language).
    "main" entries count as the product's main language. langs may end with None = any language."""
    found = {}
    for e in entries or []:
        text = (e.get("text") or "").strip()
        lang = main_lang if e.get("lang") == "main" else e.get("lang")
        if text and lang and lang not in found:
            found[lang] = text
    for want in langs:
        if want is None and found:
            return next(iter(found.items()))[::-1]
        if want in found:
            return found[want], want
    return "", ""


def _round(x):
    return round(x, 2) if isinstance(x, (int, float)) else x  # OFF stores float32: 5.199999809 -> 5.2


def cattest_product(tab, item_id):
    """The text and nutrients the tester sends to the models, for one catalogue product."""
    lang_col = "name_lang" if tab == "off" else "''"
    with closing(connect_ro()) as con:
        row = con.execute(f"SELECT name, thumb, raw, {lang_col} FROM {TABS[tab]['table']} WHERE id = ?", (item_id,)).fetchone()
    if not row:
        return None
    name, thumb, raw, shown_lang = row[0], row[1], json.loads(row[2]), row[3]
    if tab == "on":
        nut = raw.get("nutrition_100g") if isinstance(raw.get("nutrition_100g"), dict) else {}
        out = {"name": raw.get("name") or name, "description": raw.get("description") or "",
               "ingredients": raw.get("ingredients") or "", "fat": nut.get("total_fat"), "sugars": nut.get("total_sugars"),
               "kind": raw.get("type") or "", "note": ""}
    else:  # English when OFF has it (the models learned from English), else the language of the name shown in the browser
        main = raw.get("lang") or ""
        pname, name_lang = _off_text(raw.get("product_name"), main, ["en"])
        if not pname:  # no English name: the name the browser shows (Greek first)
            pname, name_lang = name or "", (main if shown_lang == "main" else shown_lang) or ""
        same = [name_lang] if name_lang else []
        generic, _ = _off_text(raw.get("generic_name"), main, same)  # never mix languages in name + description
        ingr, ingr_lang = _off_text(raw.get("ingredients_text"), main, same + ["en", None])
        nut = {n.get("name"): n.get("100g") for n in (raw.get("nutriments") or []) if isinstance(n, dict)}
        other = {x for x in (name_lang, ingr_lang) if x and x != "en"}
        if _GREEK.search(pname + " " + ingr):  # OFF sometimes files Greek text under "en"
            other.add("el")
        other = sorted(other)
        out = {"name": pname, "description": generic, "ingredients": ingr,
               "fat": _round(nut.get("fat")), "sugars": _round(nut.get("sugars")), "kind": (raw.get("brands") or "").strip(),
               "note": ("Greek text. The models also learned from about 1,300 Greek product names (since 2026-11-18), "
                        "far fewer than English, so check the confidence." if other == ["el"] else
                        f"Not in English ({', '.join(other)}). The models learned from English and Greek names only, "
                        "so expect weaker results." if other else "")}
    review = json.loads((CATREV_DIR / "review.json").read_text()) if (CATREV_DIR / "review.json").exists() else {}
    out.update({"tab": tab, "id": item_id, "thumb": thumb, "answer": review.get(item_id) if tab == "on" else None})
    return json_safe(out)


def model_service(path, body=None):
    """Forward to the local model service -> (HTTP status, JSON)."""
    req = urllib.request.Request(MODEL_SERVICE + path, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"} if body is not None else {})
    try:
        with _no_proxy.open(req, timeout=120) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except ValueError:
            return e.code, {"error": f"model service error {e.code}"}
    except (urllib.error.URLError, OSError):
        return 503, {"error": "The model service is not running.", "start": MODEL_START}


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, body, ctype):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, status=200):
        self._send(status, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self):
        url = urlparse(self.path)
        qs = {k: v[0] for k, v in parse_qs(url.query).items()}
        try:
            if url.path in ("/", "/index.html"):
                self._send(200, INDEX_HTML.read_bytes(), "text/html; charset=utf-8")
            elif url.path == "/no-image.svg":
                self._send(200, NO_IMAGE_SVG.read_bytes(), "image/svg+xml")
            elif url.path == "/photo-pilot":
                self._send(200, PILOT_HTML.read_bytes(), "text/html; charset=utf-8")
            elif url.path == "/icons":
                self._send(200, ICONS_HTML.read_bytes(), "text/html; charset=utf-8")
            elif url.path == "/api/icons":
                self._json(icons_data())
            elif url.path == "/category-review":
                self._send(200, CATREV_HTML.read_bytes(), "text/html; charset=utf-8")
            elif url.path == "/api/category-review":
                self._json(catrev_data())
            elif url.path == "/category-results":
                self._send(200, CATRES_HTML.read_bytes(), "text/html; charset=utf-8")
            elif url.path == "/api/category-results":
                self._json(catres_data())
            elif url.path == "/category-test":
                self._send(200, CATTEST_HTML.read_bytes(), "text/html; charset=utf-8")
            elif url.path == "/api/category-test/status":
                status, out = model_service("/health")
                self._json(out, status)
            elif url.path == "/api/category-test/product":
                tab = qs.get("tab", "on")
                if tab not in TABS:
                    return self._json({"error": "unknown tab"}, 400)
                result = cattest_product(tab, qs.get("id", ""))
                self._json(result) if result else self._json({"error": "not found"}, 404)
            elif url.path == "/api/photo-pilot":
                self._json(pilot_data(qs.get("run", "cutout")))
            elif _PILOT_IMG.match(url.path):
                run, sub, name = _PILOT_IMG.match(url.path).groups()
                f = PILOT_RUNS[run] / sub / f"{name}.jpg"
                self._send(200, f.read_bytes(), "image/jpeg") if f.exists() else self._json({"error": "not found"}, 404)
            elif url.path == "/api/meta":
                self._json(counts())
            elif url.path == "/api/search":
                tab = qs.get("tab", "off")
                if tab not in TABS:
                    return self._json({"error": "unknown tab"}, 400)
                page = max(0, int(qs.get("page", "0") or 0))
                self._json(search(tab, qs.get("q", ""), qs.get("filter", "all"), page))
            elif url.path == "/api/item":
                tab = qs.get("tab", "off")
                if tab not in TABS:
                    return self._json({"error": "unknown tab"}, 400)
                result = item(tab, qs.get("id", ""))
                self._json(result) if result else self._json({"error": "not found"}, 404)
            else:
                self._json({"error": "not found"}, 404)
        except ValueError as e:
            self._json({"error": str(e)}, 400)

    def do_POST(self):
        path = urlparse(self.path).path
        if path not in ("/api/photo-pilot/review", "/api/category-review/answer", "/api/category-test/predict"):
            return self._json({"error": "not found"}, 404)
        # JSON-only: browsers must preflight this from other sites, and we never answer preflights.
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            return self._json({"error": "expected application/json"}, 415)
        length = int(self.headers.get("Content-Length") or 0)
        if length > (50_000 if path == "/api/category-test/predict" else 10_000):
            return self._json({"error": "too large"}, 413)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            if path == "/api/category-test/predict":  # the model service checks the fields again
                if not isinstance(body, dict):
                    raise ValueError("expected a JSON object")
                fields = ("name", "description", "ingredients", "fat", "sugars")
                status, out = model_service("/predict", {k: body.get(k) for k in fields})
                return self._json(out, status)
            if path == "/api/category-review/answer":
                code = body.get("code")
                answers = save_catrev(str(body.get("id", "")), None if code is None else str(code))
                return self._json({"ok": True, "answered": len(answers)})
            reviews = save_review(str(body.get("run", "cutout")), str(body.get("code", "")), body.get("verdict"))
            self._json({"ok": True, "reviewed": len(reviews)})
        except (ValueError, AttributeError) as e:
            self._json({"error": str(e)}, 400)

    def log_message(self, fmt, *args):
        pass  # keep the terminal quiet


def serve(port):
    if not DB_PATH.exists():
        sys.exit(f"{DB_PATH} not found. Run the build first:\n  python3 -I {Path(__file__)} build")
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Foods browser running at http://127.0.0.1:{port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build", help="build work/browser.sqlite from the raw files")
    sp = sub.add_parser("serve", help="start the local web page")
    sp.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    build() if args.cmd == "build" else serve(args.port)


if __name__ == "__main__":
    main()
