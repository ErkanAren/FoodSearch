#!/usr/bin/env python3
"""Search lab: score search methods against the test set (KR3.5, experiments E9 and E15).

    python3 -I tools/search/search_lab.py build   # corpus + FTS5 index -> work/search_lab.sqlite (seconds)
    python3 -I tools/search/search_lab.py check   # test-set sanity: how many correct items each query has
    python3 -I tools/search/search_lab.py eval    # score every method -> work/search_lab/report.md + details.json

Corpus = roughly what the KnowD1 library will contain (PIPELINE.md §6 merge priority):
  * Open Food Facts products of the Greek market (the browser's OFF tab), and
  * OpenNutrition everyday + prepared + restaurant foods (its grocery items are OFF barcodes, left out).
It is built from work/browser.sqlite, so run the browser build first.

Test set = tools/search/queries.json. Instead of fixed IDs, each query says what a correct result looks like,
as regexes on the result's normalized name. That way new products that fit count as correct automatically.
  match      regex on the name
  match_any  regex on name + brand
  brand      regex on the brand
  not        regex on the name: excluded even if the rest matches
  src        "off" or "on": only that source counts
  ids        explicit IDs that are always correct
  same_as    reuse another query's rules (e.g. the Greeklish twin of a Greek query)
All given conditions must hold. Regexes are matched against normalized text (lower-case, no accents,
final ς = σ, punctuation = space), and they are normalized the same way, so accents in them are harmless.

Metrics (over answerable queries, i.e. queries with at least one correct item in the corpus):
  hit@1, hit@5 (= KR3.5), MRR@10 (mean of 1/rank of the first correct result, 0 if not in the top 10).
"""
import argparse
import json
import re
import sqlite3
import statistics
import sys
import time
import unicodedata
from collections import defaultdict
from contextlib import closing
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "tools" / "browser"))
from foods_browser import FTS_WEIGHTS, fts_match, norm  # noqa: E402  (shared so browser and lab agree)

BROWSER_DB = ROOT / "work" / "browser.sqlite"
LAB_DB = ROOT / "work" / "search_lab.sqlite"
OUT_DIR = ROOT / "work" / "search_lab"
QUERIES = HERE / "queries.json"
K = 10  # results kept per query


# ---------------------------------------------------------------------------
# Corpus + index
# ---------------------------------------------------------------------------
def build():
    if not BROWSER_DB.exists():
        sys.exit(f"{BROWSER_DB} not found. Run: python3 -I tools/browser/foods_browser.py build")
    LAB_DB.parent.mkdir(parents=True, exist_ok=True)
    tmp = LAB_DB.with_suffix(".sqlite.tmp")
    tmp.unlink(missing_ok=True)
    t0 = time.time()
    con = sqlite3.connect(tmp.as_uri(), uri=True)
    con.execute("ATTACH ? AS src", (BROWSER_DB.as_uri() + "?mode=ro",))
    con.create_function("norm", 1, norm, deterministic=True)
    con.executescript("""
        CREATE TABLE docs(rid INTEGER PRIMARY KEY, id TEXT UNIQUE, src TEXT, type TEXT, name TEXT, brand TEXT,
                          sort_key TEXT, scans INT, search TEXT);
        INSERT INTO docs(id, src, type, name, brand, sort_key, scans, search)
            SELECT id, 'off', 'packaged', name, brand, sort_key, scans, search FROM src.off;
        INSERT INTO docs(id, src, type, name, brand, sort_key, scans, search)
            SELECT id, 'on', type, name, brand, sort_key, NULL, search FROM src.on_foods WHERE type <> 'grocery';
        CREATE VIRTUAL TABLE docs_fts USING fts5(id UNINDEXED, name, brand, other,
                                                 tokenize='unicode61 remove_diacritics 2', prefix='2 3');
        INSERT INTO docs_fts(rowid, id, name, brand, other) SELECT rid, id, norm(name), norm(brand), search FROM docs;
        CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
    """)
    con.execute("INSERT INTO meta VALUES ('built_at', ?)", (time.strftime("%Y-%m-%d %H:%M"),))
    con.commit()
    counts = con.execute("SELECT src, type, COUNT(*) FROM docs GROUP BY 1, 2 ORDER BY 1, 2").fetchall()
    con.close()
    tmp.replace(LAB_DB)
    print(f"Corpus built in {time.time() - t0:.1f}s -> {LAB_DB} ({LAB_DB.stat().st_size / 1e6:.0f} MB)")
    for src, typ, n in counts:
        print(f"  {src:3s} {typ:10s} {n:7,}")


def connect():
    if not LAB_DB.exists():
        sys.exit(f"{LAB_DB} not found. Run: python3 -I {Path(__file__).relative_to(ROOT)} build")
    return sqlite3.connect(LAB_DB.as_uri() + "?mode=ro", uri=True)


# ---------------------------------------------------------------------------
# Search methods. Each takes (con, query) and returns up to K doc IDs, best first.
# ---------------------------------------------------------------------------
def like_escape(word):
    return "%" + word.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def m_like(con, q):
    """The browser's search before 2026-11-13: every word as a substring, sorted A->Z (no ranking)."""
    words = norm(q).split()
    if not words:
        return []
    where = " AND ".join(["search LIKE ? ESCAPE '\\'"] * len(words))
    sql = f"SELECT id FROM docs WHERE {where} ORDER BY sort_key, id LIMIT {K}"
    return [r[0] for r in con.execute(sql, [like_escape(w) for w in words])]


def _bm25(con, words, op, limit):
    sql = f"""SELECT d.id FROM docs_fts JOIN docs d ON d.rid = docs_fts.rowid
              WHERE docs_fts MATCH ?
              ORDER BY bm25(docs_fts, {FTS_WEIGHTS}), d.scans DESC, d.sort_key, d.id LIMIT ?"""
    return [r[0] for r in con.execute(sql, (fts_match(words, op), limit))]


def m_bm25(con, q):
    """FTS5 + BM25: every word must match the start of a word (the browser's search since 2026-11-13)."""
    words = norm(q).split()
    return _bm25(con, words, "AND", K) if words else []


def m_bm25_or(con, q):
    """Like bm25, but when fewer than K rows match ALL words, fill up with rows matching ANY word."""
    words = norm(q).split()
    if not words:
        return []
    hits = _bm25(con, words, "AND", K)
    if len(hits) < K and len(words) > 1:
        seen = set(hits)
        hits += [i for i in _bm25(con, words, "OR", 2 * K) if i not in seen][: K - len(hits)]
    return hits


METHODS = {"like": m_like, "bm25": m_bm25, "bm25_or": m_bm25_or}


# ---------------------------------------------------------------------------
# Test set + judging
# ---------------------------------------------------------------------------
def norm_pattern(p):
    p = unicodedata.normalize("NFKD", p)
    return "".join(c for c in p if not unicodedata.combining(c)).replace("ς", "σ")


def compile_rules(spec):
    rx = {k: re.compile(norm_pattern(spec[k]), re.IGNORECASE) for k in ("match", "match_any", "brand", "not") if k in spec}
    return {"rx": rx, "src": spec.get("src"), "ids": set(spec.get("ids", []))}


def load_queries():
    raw = json.loads(QUERIES.read_text())
    by_id = {q["id"]: q for q in raw}
    out = []
    for q in raw:
        rules_spec = by_id[q["same_as"]] if "same_as" in q else q
        out.append({**q, "rules": compile_rules(rules_spec)})
    return out


def is_correct(rules, doc):
    if doc["id"] in rules["ids"]:
        return True
    rx = rules["rx"]
    if not any(k in rx for k in ("match", "match_any", "brand")):
        return False
    if rules["src"] and doc["src"] != rules["src"]:
        return False
    if "match" in rx and not rx["match"].search(doc["n_name"]):
        return False
    if "match_any" in rx and not rx["match_any"].search(doc["n_name"] + " " + doc["n_brand"]):
        return False
    if "brand" in rx and not rx["brand"].search(doc["n_brand"]):
        return False
    if "not" in rx and rx["not"].search(doc["n_name"]):
        return False
    return True


def load_docs(con):
    docs = {}
    for id_, src, typ, name, brand, scans in con.execute("SELECT id, src, type, name, brand, scans FROM docs"):
        docs[id_] = {"id": id_, "src": src, "type": typ, "name": name or "", "brand": brand or "", "scans": scans,
                     "n_name": norm(name), "n_brand": norm(brand)}
    return docs


def correct_ids(queries, docs):
    return {q["id"]: {d["id"] for d in docs.values() if is_correct(q["rules"], d)} for q in queries}


def check(show=None):
    queries = load_queries()
    with closing(connect()) as con:
        docs = load_docs(con)
    if show:
        for q in (q for q in queries if q["id"] in show):
            ok = sorted((d for d in docs.values() if is_correct(q["rules"], d)), key=lambda d: (-(d["scans"] or 0), d["name"]))
            print(f"\n## {q['id']} {q['q']} ({q['want']}): {len(ok)} correct items")
            for d in ok:
                print(f"   {d['src']:3s} {d['name'][:70]:70s} | {d['brand'][:30]}")
        return
    correct = correct_ids(queries, docs)
    empty = []
    for q in queries:
        ids = correct[q["id"]]
        by_src = defaultdict(int)
        for i in ids:
            by_src[docs[i]["src"]] += 1
        sample = sorted((docs[i] for i in ids), key=lambda d: (-(d["scans"] or 0), len(d["name"])))[:4]
        names = " | ".join(f"{d['name'][:38]}" for d in sample)
        print(f"{q['id']} {q['q'][:26]:26s} {len(ids):5d}  (off {by_src['off']:4d}, on {by_src['on']:4d})  {names}")
        if not ids:
            empty.append(q["id"])
    print(f"\n{len(queries)} queries, {len(queries) - len(empty)} answerable. "
          f"No correct item in the corpus (data gap, not a search problem): {', '.join(empty) or 'none'}")


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------
def first_rank(result_ids, ok):
    for rank, i in enumerate(result_ids, 1):
        if i in ok:
            return rank
    return None


def summarize(rows):
    n = len(rows)
    if not n:
        return {"n": 0, "hit1": 0.0, "hit5": 0.0, "mrr": 0.0}
    return {"n": n,
            "hit1": sum(r is not None and r <= 1 for r in rows) / n,
            "hit5": sum(r is not None and r <= 5 for r in rows) / n,
            "mrr": sum(1 / r for r in rows if r is not None) / n}


def evaluate(methods):
    queries = load_queries()
    with closing(connect()) as con:
        docs = load_docs(con)
        correct = correct_ids(queries, docs)
        answerable = [q for q in queries if correct[q["id"]]]
        ranks = {m: {} for m in methods}
        times = {m: [] for m in methods}
        details = []
        for q in answerable:
            entry = {"id": q["id"], "q": q["q"], "kind": q["kind"], "want": q["want"],
                     "n_correct": len(correct[q["id"]]), "methods": {}}
            for m in methods:
                t0 = time.perf_counter()
                res = METHODS[m](con, q["q"])
                times[m].append(1000 * (time.perf_counter() - t0))
                ranks[m][q["id"]] = first_rank(res, correct[q["id"]])
                entry["methods"][m] = {"first_correct_rank": ranks[m][q["id"]],
                                       "top5": [{"name": docs[i]["name"], "brand": docs[i]["brand"], "src": docs[i]["src"],
                                                 "ok": i in correct[q["id"]]} for i in res[:5]]}
            details.append(entry)

    kinds = sorted({q["kind"] for q in answerable}, key=lambda k: [q["kind"] for q in answerable].index(k))
    overall = {m: summarize(list(ranks[m].values())) for m in methods}
    per_kind = {m: {k: summarize([ranks[m][q["id"]] for q in answerable if q["kind"] == k]) for k in kinds} for m in methods}
    lat = {m: (statistics.mean(times[m]), sorted(times[m])[int(0.95 * (len(times[m]) - 1))]) for m in methods}

    with closing(connect()) as con:
        built = con.execute("SELECT value FROM meta WHERE key = 'built_at'").fetchone()[0]
    overall_tbl = ["| Method | hit@1 | hit@5 (KR3.5) | MRR@10 | mean ms | p95 ms |", "|---|---|---|---|---|---|"]
    for m in methods:
        o = overall[m]
        overall_tbl.append(f"| {m} | {o['hit1']:.0%} | **{o['hit5']:.0%}** | {o['mrr']:.2f} | {lat[m][0]:.1f} | {lat[m][1]:.1f} |")
    kind_tbl = ["| Kind | n | " + " | ".join(methods) + " |", "|---|---|" + "---|" * len(methods)]
    for k in kinds:
        kind_tbl.append(f"| {k} | {per_kind[methods[0]][k]['n']} | "
                        + " | ".join(f"{per_kind[m][k]['hit5']:.0%}" for m in methods) + " |")
    rank_tbl = ["| ID | Query | Kind | " + " | ".join(methods) + " |", "|---|---|---|" + "---|" * len(methods)]
    for e in details:
        cells = [str(e["methods"][m]["first_correct_rank"] or "–") for m in methods]
        rank_tbl.append(f"| {e['id']} | {e['q']} | {e['kind']} | " + " | ".join(cells) + " |")
    header = [f"# Search lab report", "",
              f"Run {time.strftime('%Y-%m-%d %H:%M')} · corpus built {built} · {len(docs):,} items · "
              f"{len(answerable)} of {len(queries)} queries answerable"]
    report = "\n".join(header + ["", "## Overall", ""] + overall_tbl + ["", "## hit@5 by query kind", ""] + kind_tbl
                       + ["", "## First correct rank per query (– = not in top 10)", ""] + rank_tbl) + "\n"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "report.md").write_text(report)
    (OUT_DIR / "details.json").write_text(json.dumps(details, ensure_ascii=False, indent=1))

    print(header[2], "", *overall_tbl, "", *kind_tbl, sep="\n")
    print(f"\nFull report: {OUT_DIR / 'report.md'}\nTop-5 per query and method: {OUT_DIR / 'details.json'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build", help="build the corpus + FTS5 index from work/browser.sqlite")
    ck = sub.add_parser("check", help="show how many correct items each test query has")
    ck.add_argument("--show", help="comma-separated query IDs: list every item counted as correct")
    ev = sub.add_parser("eval", help="score the search methods on the test set")
    ev.add_argument("--methods", default=",".join(METHODS), help=f"comma-separated, from: {', '.join(METHODS)}")
    args = ap.parse_args()
    if args.cmd == "build":
        build()
    elif args.cmd == "check":
        check(set(args.show.split(",")) if args.show else None)
    else:
        methods = [m.strip() for m in args.methods.split(",") if m.strip()]
        unknown = [m for m in methods if m not in METHODS]
        if unknown:
            sys.exit(f"unknown method(s): {', '.join(unknown)}")
        evaluate(methods)


if __name__ == "__main__":
    main()
