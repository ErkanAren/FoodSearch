#!/usr/bin/env python3
"""Search lab: score search methods against the test set (KR3.5, experiments E9 and E15).

Every command takes --corpus (default: library). Each corpus lives in its own folder work/search_lab/<corpus>/.

Keyword part (standard library only, any python3):
    python3 -I tools/search/search_lab.py build --corpus opennutrition   # corpus + FTS5 index (seconds)
    python3 -I tools/search/search_lab.py check --corpus opennutrition   # how many correct items each query has
    python3 -I tools/search/search_lab.py eval --corpus opennutrition    # scores -> report.md + details.json

Semantic part (needs the project venv with tools/search/requirements.txt installed):
    .venv/bin/python -I tools/search/search_lab.py embed --corpus opennutrition --model e5-small   # item vectors
    .venv/bin/python -I tools/search/search_lab.py sweep --corpus opennutrition --model e5-small   # weight 0 -> 1
    .venv/bin/python -I tools/search/search_lab.py eval --corpus opennutrition --methods bm25,dense:e5-small,rrf:e5-small
    .venv/bin/python -I tools/search/search_lab.py serve --corpus opennutrition   # http://127.0.0.1:8767

Corpora (all built from work/browser.sqlite, so run the browser build first):
  library        Open Food Facts Greek market (the browser's OFF tab) + OpenNutrition everyday, prepared and
                 restaurant foods. Roughly the Greek library of PIPELINE.md §6 (≈ 40 k items).
  opennutrition  All OpenNutrition foods, grocery included (≈ 327 k items).
  all            Both: Open Food Facts Greek market + all OpenNutrition (≈ 353 k items).

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

Methods (--methods, comma-separated):
  like               the browser's old search: every word as a substring, sorted A->Z
  bm25               FTS5 + BM25, every word must match the start of a word (the browser's search now)
  bm25_or            bm25, filled up with rows matching ANY word when fewer than 10 match all words
  dense:MODEL        semantic only: cosine similarity between query and item vectors
  rrf:MODEL          reciprocal rank fusion of BM25 (any word) and dense: sum of 1 / (60 + rank)
  mix:MODEL:W        weighted sum after rescaling each side to 0..1 per query: W * BM25 + (1 - W) * dense
                     (so mix:MODEL:0.25 = 0.25 BM25 + 0.75 semantic)
  Greek queries on English names (experiment E16; MODE = words | names, MT = a translation model below):
  kw_el:MODE         BM25 + an offline Greek index of the translated names (built by `translate`). No model at search time.
                     Queries in Latin letters are also matched as Greeklish (karpouzi -> καρπούζι -> Watermelon).
  hyb_el:MODE:MODEL  RRF of BM25, the offline Greek index and semantic search.
  kw_mt:MT           BM25 + BM25 on the query translated to English at search time (only for Greek queries).
  hyb_mt:MT:MODEL    RRF of BM25 on the query, and BM25 + semantic on its English translation.
  rr:METHOD          re-rank METHOD's top 30 (+ typo-tolerant name matches): closest name first, generic foods
                     before branded variants, original order as tie-break. No model. e.g. rr:kw_el:words
  rrg:METHOD         like rr:, but non-brand (generic) foods that match well always come before branded products,
                     unless the query names a brand (e.g. "coca cola zero"). e.g. rrg:kw_el:words
  Translation models (MT): en-el-big, en-el-tiny (offline, English -> Greek); el-en-tiny (at search time).
  (opus-mt-tc-big-el-en was tried at search time: it produced garbage with transformers 5.23, so it is not listed.)
  Offline Greek index:
    .venv/bin/python -I tools/search/search_lab.py translate --corpus opennutrition --mode words --mt en-el-big

Metrics (over answerable queries, i.e. queries with at least one correct item in the corpus):
  hit@1, hit@5 (= KR3.5), MRR@10 (mean of 1/rank of the first correct result, 0 if not in the top 10).
  ms = time per query, including embedding the query on the CPU (as on a plain server).
"""
import argparse
import difflib
import hashlib
import json
import os
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
LAB_ROOT = ROOT / "work" / "search_lab"
HF_CACHE = ROOT / "work" / "models" / "hf"
# corpus -> (description, include the OFF Greek tab?, filter on OpenNutrition rows)
CORPORA = {
    "library": ("OFF Greek market + OpenNutrition everyday / prepared / restaurant", True, "WHERE type <> 'grocery'"),
    "opennutrition": ("All OpenNutrition foods, grocery included", False, ""),
    "all": ("OFF Greek market + all OpenNutrition foods", True, ""),
}
CORPUS = "library"
LAB_DB = LAB_ROOT / CORPUS / "corpus.sqlite"
OUT_DIR = LAB_ROOT / CORPUS


def set_corpus(name):
    global CORPUS, LAB_DB, OUT_DIR
    CORPUS, OUT_DIR = name, LAB_ROOT / name
    LAB_DB = OUT_DIR / "corpus.sqlite"
QUERIES = HERE / "queries.json"
K = 10          # results kept per query
POOL = 100      # candidates taken from each side before fusion
RRF_K = 60

# Embedding models. Prefixes follow each model card: e5 wants "query: " / "passage: ".
# Qwen3-Embedding wants an instruction on the query side only; we describe our task instead of web search.
MODELS = {
    "e5-small": {"hf": "intfloat/multilingual-e5-small", "doc": "passage: ", "query": "query: "},
    "qwen3-0.6b": {"hf": "Qwen/Qwen3-Embedding-0.6B", "doc": "",
                   "query": "Instruct: Given a food search query in Greek, Greeklish or English, "
                            "retrieve the matching food or food product\nQuery:"},
}


# ---------------------------------------------------------------------------
# Corpus + index
# ---------------------------------------------------------------------------
def embed_text(name, brand, others, max_others):
    """What the embedding model reads for one item: the name, a few other names, the brand."""
    name = (name or "").strip()
    seen, extra = {norm(name)}, []
    for o in others:
        o = (o or "").strip() if isinstance(o, str) else ""
        if o and norm(o) not in seen:
            seen.add(norm(o))
            extra.append(o)
        if len(extra) == max_others:
            break
    text = name + (f" ({'; '.join(extra)})" if extra else "")
    brand = (brand or "").strip()[:60]
    return text + (f" - {brand}" if brand else "")


def build():
    if not BROWSER_DB.exists():
        sys.exit(f"{BROWSER_DB} not found. Run: python3 -I tools/browser/foods_browser.py build")
    LAB_DB.parent.mkdir(parents=True, exist_ok=True)
    tmp = LAB_DB.with_suffix(".sqlite.tmp")
    tmp.unlink(missing_ok=True)
    t0 = time.time()
    desc, with_off, on_filter = CORPORA[CORPUS]
    con = sqlite3.connect(tmp.as_uri(), uri=True)
    con.execute("ATTACH ? AS src", (BROWSER_DB.as_uri() + "?mode=ro",))
    con.create_function("norm", 1, norm, deterministic=True)
    con.execute("""CREATE TABLE docs(rid INTEGER PRIMARY KEY, id TEXT UNIQUE, src TEXT, type TEXT, name TEXT, brand TEXT,
                                     sort_key TEXT, scans INT, search TEXT, embed_text TEXT)""")
    if with_off:
        con.execute("""INSERT INTO docs(id, src, type, name, brand, sort_key, scans, search)
                       SELECT id, 'off', 'packaged', name, brand, sort_key, scans, search FROM src.off""")
    con.execute(f"""INSERT INTO docs(id, src, type, name, brand, sort_key, scans, search)
                    SELECT id, 'on', type, name, brand, sort_key, NULL, search FROM src.on_foods {on_filter}""")
    con.executescript("""
        CREATE VIRTUAL TABLE docs_fts USING fts5(id UNINDEXED, name, brand, other,
                                                 tokenize='unicode61 remove_diacritics 2', prefix='2 3');
        INSERT INTO docs_fts(rowid, id, name, brand, other) SELECT rid, id, norm(name), norm(brand), search FROM docs;
        CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
    """)
    # Embedding text: OFF = name + other product/generic names + brand; OpenNutrition = name + synonyms.
    # Other OFF names: Greek, English and the product's main language only (never Turkish: project scope is
    # Greece + Cyprus). This also drops noise such as Chinese or Russian names on imported products.
    updates = []
    for rid, name, brand, lang, pn, gn in con.execute("""
            SELECT d.rid, d.name, d.brand, json_extract(o.raw, '$.lang'), json_extract(o.raw, '$.product_name'),
                   json_extract(o.raw, '$.generic_name')
            FROM docs d JOIN src.off o ON o.id = d.id WHERE d.src = 'off'"""):
        keep = {"el", "en"} | ({"main"} if lang != "tr" else set())
        names = (json.loads(pn) if pn else []) + (json.loads(gn) if gn else [])
        others = [n.get("text") for n in names if isinstance(n, dict) and n.get("lang") in keep]
        updates.append((embed_text(name, brand, others, 3), rid))
    # OpenNutrition grocery names already end in "by <Brand>", so no separate brand is added.
    for rid, name, alt in con.execute("""
            SELECT d.rid, d.name, json_extract(o.raw, '$.alternate_names')
            FROM docs d JOIN src.on_foods o ON o.id = d.id WHERE d.src = 'on'"""):
        alt = json.loads(alt) if alt else []
        updates.append((embed_text(name, None, alt if isinstance(alt, list) else [], 5), rid))
    con.executemany("UPDATE docs SET embed_text = ? WHERE rid = ?", updates)
    texts = [t for (t,) in con.execute("SELECT embed_text FROM docs ORDER BY rid")]
    con.executemany("INSERT INTO meta VALUES (?, ?)", [
        ("built_at", time.strftime("%Y-%m-%d %H:%M")),
        ("corpus", CORPUS), ("description", desc),
        ("embed_sha", hashlib.sha1("\n".join(texts).encode()).hexdigest()),
    ])
    con.commit()
    counts = con.execute("SELECT src, type, COUNT(*) FROM docs GROUP BY 1, 2 ORDER BY 1, 2").fetchall()
    con.close()
    tmp.replace(LAB_DB)
    print(f"Corpus '{CORPUS}' ({desc}) built in {time.time() - t0:.1f}s -> {LAB_DB} ({LAB_DB.stat().st_size / 1e6:.0f} MB)")
    for src, typ, n in counts:
        print(f"  {src:3s} {typ:10s} {n:7,}")
    print(f"  total        {sum(n for *_, n in counts):7,}")


def connect():
    if not LAB_DB.exists():
        sys.exit(f"{LAB_DB} not found. Run: python3 -I {Path(__file__).relative_to(ROOT)} build --corpus {CORPUS}")
    return sqlite3.connect(LAB_DB.as_uri() + "?mode=ro", uri=True)


def meta(con, key):
    row = con.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------
def load_model(name, device):
    os.environ.setdefault("HF_HOME", str(HF_CACHE))
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    from sentence_transformers import SentenceTransformer
    if name not in MODELS:
        sys.exit(f"unknown model {name!r}; choose from: {', '.join(MODELS)}")
    kwargs = {}
    if device == "cpu":  # bfloat16 (Qwen3's default) is slow on most CPUs
        import torch
        kwargs["model_kwargs"] = {"dtype": torch.float32}
    return SentenceTransformer(MODELS[name]["hf"], device=device, cache_folder=str(HF_CACHE), **kwargs)


def vec_paths(name):
    return OUT_DIR / f"vec_{name}.npy", OUT_DIR / f"vec_{name}.json"


def embed(name, batch):
    import numpy as np
    import torch
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    with closing(connect()) as con:
        rows = con.execute("SELECT rid, embed_text FROM docs ORDER BY rid").fetchall()
        corpus_sha = meta(con, "embed_sha")
    if [r[0] for r in rows] != list(range(1, len(rows) + 1)):
        sys.exit("docs.rid is not 1..N; rebuild the corpus")
    t0 = time.time()
    model = load_model(name, device)
    load_s = time.time() - t0
    texts = [MODELS[name]["doc"] + t for _, t in rows]
    t0 = time.time()
    vecs = model.encode(texts, batch_size=batch, normalize_embeddings=True, convert_to_numpy=True,
                        show_progress_bar=True).astype(np.float32)
    secs = time.time() - t0
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    npy, info = vec_paths(name)
    np.save(npy, vecs)
    info.write_text(json.dumps({
        "model": name, "hf": MODELS[name]["hf"], "dims": int(vecs.shape[1]), "items": len(rows),
        "device": device, "batch": batch, "seconds": round(secs, 1), "items_per_s": round(len(rows) / secs, 1),
        "model_load_seconds": round(load_s, 1), "corpus_embed_sha": corpus_sha, "built_at": time.strftime("%Y-%m-%d %H:%M"),
        "mb": round(npy.stat().st_size / 1e6, 1),
    }, indent=1))
    print(f"{name}: {len(rows):,} items x {vecs.shape[1]} dims in {secs:.0f}s on {device} "
          f"({len(rows) / secs:.0f} items/s) -> {npy} ({npy.stat().st_size / 1e6:.0f} MB)")


class Dense:
    """One model's item vectors + a CPU copy of the model for embedding queries (like a plain server)."""
    _cache = {}

    @classmethod
    def get(cls, name):
        if name not in cls._cache:
            cls._cache[name] = cls(name)
        return cls._cache[name]

    def __init__(self, name):
        import numpy as np
        self.np = np
        npy, info = vec_paths(name)
        if not npy.exists():
            sys.exit(f"No vectors for {name} in corpus '{CORPUS}'. Run: .venv/bin/python -I tools/search/search_lab.py "
                     f"embed --corpus {CORPUS} --model {name}")
        with closing(connect()) as con:
            if json.loads(info.read_text())["corpus_embed_sha"] != meta(con, "embed_sha"):
                sys.exit(f"Vectors for {name} were made from an older corpus. Re-run embed --corpus {CORPUS} --model {name}.")
        self.vecs = np.load(npy)
        self.prefix = MODELS[name]["query"]
        self.model = load_model(name, "cpu")
        self.model.encode([self.prefix + "warm up"], normalize_embeddings=True)
        self._q = {}

    def query_vec(self, q):
        if q not in self._q:
            self._q[q] = self.model.encode([self.prefix + q], normalize_embeddings=True, convert_to_numpy=True)[0]
        return self._q[q]

    def scores(self, q):
        return self.vecs @ self.query_vec(q)  # cosine similarity: all vectors are unit length

    def top(self, q, n):
        s = self.scores(q)
        idx = self.np.argpartition(-s, min(n, len(s) - 1))[:n]
        idx = idx[self.np.lexsort((idx, -s[idx]))]  # best first; ties by row number, so results are stable
        return [(int(i) + 1, float(s[i])) for i in idx]  # (rid, cosine)


# ---------------------------------------------------------------------------
# Greek <-> English translation (experiment E16)
#   offline:  translate OpenNutrition's English names (or their words) to Greek once, index the Greek
#   runtime:  translate a Greek query to English at search time
# ---------------------------------------------------------------------------
MT_MODELS = {
    "en-el-big": "Helsinki-NLP/opus-mt-tc-big-en-el",   # offline, quality first (CC-BY-4.0)
    "en-el-tiny": "Helsinki-NLP/opus-mt_tiny_eng-ell",  # offline, fast (Apache-2.0)
    "el-en-tiny": "Helsinki-NLP/opus-mt_tiny_ell-eng",  # at query time, cheap (Apache-2.0)
}
_HAS_GREEK = re.compile("[α-ω]")
_BY_BRAND = re.compile(r"\s+by\s+.*$", re.IGNORECASE)
_EN_WORD = re.compile(r"[a-z][a-z'-]+")
# Light Greek stemmer for normalized text (no accents, final ς already σ): strip one common ending,
# keep at least 3 letters. Used on both sides, so "καρπουζια" (query) meets "καρπουζι" (index).
_EL_ENDINGS = sorted(["ιεσ", "ιων", "ουσ", "εων", "ων", "ησ", "εσ", "ασ", "οσ", "ου", "οι", "ια", "ιο", "εισ",
                      "α", "ε", "η", "ι", "ο", "υ", "σ"], key=len, reverse=True)


def el_stem(word):
    if not _HAS_GREEK.search(word):
        return word
    for e in _EL_ENDINGS:
        if word.endswith(e) and len(word) - len(e) >= 3:
            return word[: -len(e)]
    return word


def el_index_text(greek):
    """Stemmed, normalized Greek, each word once: translated names often repeat the food
    ("Banana Pops, Banana" -> "μπανάνα ... μπανάνα"), which would let them outrank the plain food."""
    return " ".join(dict.fromkeys(el_stem(w) for w in norm(greek).split()))


def el_match(stems, op):
    """FTS query for the Greek index. Stems of 4+ letters match as prefixes; shorter ones only as whole words,
    so "γαλ" (from γάλα) doesn't also find "γαλοπουλ" (turkey)."""
    return f" {op} ".join(f'"{s}"*' if len(s) >= 4 else f'"{s}"' for s in stems)


def base_name(name):
    """OpenNutrition grocery names end in 'by <Brand>'; the brand is not translated."""
    return _BY_BRAND.sub("", name or "").strip()


# Greeklish (experiment E9): Greek written in Latin letters ("karpouzi"). Instead of guessing one Greek spelling,
# both sides are reduced to the same rough Latin "skeleton": the Greek words of the index (καρπουζι -> karpuz) and
# the query (karpouzi -> karpuz). Sounds Greeks spell in several ways are merged (η/ι/υ/ει/οι -> i, ο/ω -> o,
# ου -> u, αι/ε -> e, μπ -> b, ντ -> d, χ -> h), doubled letters collapse and one ending is removed.
_GR_SKEL_PAIRS = [("ου", "u"), ("αι", "e"), ("ει", "i"), ("οι", "i"), ("υι", "i"), ("αυ", "av"), ("ευ", "ev"),
                  ("μπ", "b"), ("ντ", "d"), ("γκ", "g"), ("γγ", "g"), ("τσ", "ts"), ("τζ", "tz"),
                  ("θ", "th"), ("χ", "h"), ("ψ", "ps"), ("ξ", "ks")]
_GR_SKEL = str.maketrans("αβγδεζηικλμνοπρστυφω", "avgdeziiklmnoprstifo")
_LAT_SKEL_PAIRS = [("ou", "u"), ("ai", "e"), ("ei", "i"), ("oi", "i"), ("ui", "i"), ("ph", "f"), ("ch", "h"),
                   ("kh", "h"), ("mp", "b"), ("nt", "d"), ("gk", "g"), ("gg", "g"), ("x", "h"), ("w", "o"),
                   ("y", "i"), ("c", "k"), ("q", "k")]
_SKEL_ENDINGS = ["ies", "es", "as", "os", "is", "us", "ia", "io", "a", "e", "i", "o", "u", "s"]
_DOUBLE = re.compile(r"(.)\1+")


def skeleton(word):
    """Rough common spelling of a normalized Greek or Greeklish word, without its ending."""
    if _HAS_GREEK.search(word):
        for a, b in _GR_SKEL_PAIRS:
            word = word.replace(a, b)
        word = word.translate(_GR_SKEL)
    else:
        for a, b in _LAT_SKEL_PAIRS:
            word = word.replace(a, b)
    word = _DOUBLE.sub(r"\1", word)
    for e in _SKEL_ENDINGS:
        if word.endswith(e) and len(word) - len(e) >= 3:
            return word[: -len(e)]
    return word


def ensure_greeklish_index():
    """FTS index of the skeletons of every item's Greek words: the offline translation (OpenNutrition) and Greek
    names already in the data (Open Food Facts). Built once per corpus; `translate` drops it so it is rebuilt."""
    with closing(sqlite3.connect(LAB_DB.as_uri(), uri=True)) as con:
        if con.execute("SELECT 1 FROM sqlite_master WHERE name = 'greeklish_fts'").fetchone():
            return
        t0 = time.time()
        has_el = con.execute("SELECT 1 FROM sqlite_master WHERE name = 'el_words_fts'").fetchone()
        el = dict(con.execute("SELECT rowid, text FROM el_words_fts")) if has_el else {}
        rows = []
        for rid, search in con.execute("SELECT rid, search FROM docs"):
            greek = [el_stem(w) for w in (search or "").split() if _HAS_GREEK.search(w)] + el.get(rid, "").split()
            skel = dict.fromkeys(skeleton(w) for w in greek if w)
            if skel:
                rows.append((rid, " ".join(skel)))
        con.executescript("""CREATE VIRTUAL TABLE greeklish_fts USING fts5(text, tokenize='unicode61', prefix='2 3');""")
        con.executemany("INSERT INTO greeklish_fts(rowid, text) VALUES (?, ?)", rows)
        con.commit()
        print(f"Built the Greeklish index ({len(rows):,} items) in {time.time() - t0:.0f}s", flush=True)


def greeklish_ranked(con, words, op, limit):
    """Ranked rids for a query in Latin letters, matched as Greeklish against the items' Greek words."""
    if not con.execute("SELECT 1 FROM sqlite_master WHERE name = 'greeklish_fts'").fetchone():
        ensure_greeklish_index()
    skel = [skeleton(w) for w in words]
    sql = "SELECT rowid FROM greeklish_fts WHERE greeklish_fts MATCH ? ORDER BY bm25(greeklish_fts), rowid LIMIT ?"
    return [r for (r,) in con.execute(sql, (el_match(skel, op), limit))]


class MT:
    """A Marian translation model. Queries are cached like the embedding cache (cleared per timed call in eval)."""
    _cache = {}

    @classmethod
    def get(cls, name, device="cpu"):
        if (name, device) not in cls._cache:
            cls._cache[(name, device)] = cls(name, device)
        return cls._cache[(name, device)]

    def __init__(self, name, device):
        os.environ.setdefault("HF_HOME", str(HF_CACHE))
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        if name not in MT_MODELS:
            sys.exit(f"unknown translation model {name!r}; choose from: {', '.join(MT_MODELS)}")
        self.torch, self.device = torch, device
        self.tok = AutoTokenizer.from_pretrained(MT_MODELS[name], cache_dir=str(HF_CACHE))
        self.model = AutoModelForSeq2SeqLM.from_pretrained(MT_MODELS[name], cache_dir=str(HF_CACHE)).to(device).eval()
        self.model.generation_config.max_length = None  # we set max_new_tokens; avoids a warning per call
        self._q = {}

    def translate(self, texts, batch=64):
        order = sorted(range(len(texts)), key=lambda i: len(texts[i]))  # similar lengths per batch = less padding
        out = [None] * len(texts)
        for s in range(0, len(order), batch):
            idx = order[s:s + batch]
            enc = self.tok([texts[i] for i in idx], return_tensors="pt", padding=True, truncation=True,
                           max_length=64).to(self.device)
            with self.torch.no_grad():
                gen = self.model.generate(**enc, num_beams=1, max_new_tokens=48)
            for i, t in zip(idx, self.tok.batch_decode(gen, skip_special_tokens=True)):
                out[i] = t.strip()
        return out

    def query(self, q):
        if q not in self._q:
            self._q[q] = self.translate([q])[0]
        return self._q[q]


def translate_corpus(mode, mt_name, batch):
    """Offline: Greek text for every OpenNutrition item, stored as an extra FTS index el_<mode>_fts (rowid = rid).
    mode 'words': translate each distinct English word once; an item's Greek = its words' translations.
    mode 'names': translate each distinct product name (without 'by Brand'); more context, more work."""
    import torch
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    con = sqlite3.connect(LAB_DB.as_uri(), uri=True)
    rows = con.execute("SELECT rid, name FROM docs WHERE src = 'on' ORDER BY rid").fetchall()
    bases = {rid: base_name(n) for rid, n in rows}
    if mode == "words":
        doc_units = {rid: list(dict.fromkeys(_EN_WORD.findall(b.lower()))) for rid, b in bases.items()}
    else:
        doc_units = {rid: [b.lower()] if b else [] for rid, b in bases.items()}
    units = sorted({u for us in doc_units.values() for u in us})
    con.execute(f"CREATE TABLE IF NOT EXISTS mt_{mode}(src TEXT PRIMARY KEY, el TEXT)")
    done = {s for (s,) in con.execute(f"SELECT src FROM mt_{mode}")}
    todo = [u for u in units if u not in done]  # resumable: already translated units are skipped
    print(f"{mode}: {len(units):,} distinct units, {len(todo):,} to translate with {mt_name} on {device}", flush=True)
    t0 = time.time()
    if todo:
        mt = MT.get(mt_name, device)
        load_s = time.time() - t0
        t0 = time.time()
        step = batch * 20
        for s in range(0, len(todo), step):
            chunk = todo[s:s + step]
            con.executemany(f"INSERT OR REPLACE INTO mt_{mode} VALUES (?, ?)", zip(chunk, mt.translate(chunk, batch)))
            con.commit()
            el = time.time() - t0
            print(f"  {s + len(chunk):,}/{len(todo):,} · {(s + len(chunk)) / el:.0f}/s", flush=True)
        secs = time.time() - t0
    else:
        load_s = secs = 0.0
    tr = dict(con.execute(f"SELECT src, el FROM mt_{mode}"))
    con.executescript(f"""DROP TABLE IF EXISTS el_{mode}_fts; DROP TABLE IF EXISTS greeklish_fts;
        CREATE VIRTUAL TABLE el_{mode}_fts USING fts5(text, tokenize='unicode61 remove_diacritics 2', prefix='2 3');""")
    con.executemany(f"INSERT INTO el_{mode}_fts(rowid, text) VALUES (?, ?)",
                    ((rid, el_index_text(" ".join(tr.get(u, "") for u in us))) for rid, us in doc_units.items()))
    meta_rows = [(f"el_{mode}_model", mt_name), (f"el_{mode}_units", str(len(units)))]
    if todo:
        meta_rows.append((f"el_{mode}_seconds", f"{secs:.0f}"))
    con.executemany("INSERT OR REPLACE INTO meta VALUES (?, ?)", meta_rows)
    con.commit()
    sample = con.execute(f"SELECT src, el FROM mt_{mode} ORDER BY random() LIMIT 400").fetchall()
    con.close()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"mt_{mode}_sample.txt").write_text("\n".join(f"{s}\t{e}" for s, e in sorted(sample)) + "\n")
    rate = f", {len(todo) / secs:.0f} units/s" if todo and secs else ""
    print(f"Done: {len(units):,} units, model load {load_s:.0f}s, translation {secs:.0f}s{rate}. "
          f"Greek index el_{mode}_fts built. Sample: {OUT_DIR / f'mt_{mode}_sample.txt'}")


# ---------------------------------------------------------------------------
# Search methods. Each takes (con, query, k=K) and returns up to k doc rids, best first.
# ---------------------------------------------------------------------------
def like_escape(word):
    return "%" + word.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def m_like(con, q, k=K):
    """The browser's search before 2026-11-13: every word as a substring, sorted A->Z (no ranking)."""
    words = norm(q).split()
    if not words:
        return []
    where = " AND ".join(["search LIKE ? ESCAPE '\\'"] * len(words))
    sql = f"SELECT rid FROM docs WHERE {where} ORDER BY sort_key, id LIMIT {int(k)}"
    return [r[0] for r in con.execute(sql, [like_escape(w) for w in words])]


def bm25_scored(con, words, op, limit):
    """[(rid, score)] best first; score = -bm25() so that higher is better."""
    sql = f"""SELECT d.rid, -bm25(docs_fts, {FTS_WEIGHTS}) FROM docs_fts JOIN docs d ON d.rid = docs_fts.rowid
              WHERE docs_fts MATCH ?
              ORDER BY bm25(docs_fts, {FTS_WEIGHTS}), d.scans DESC, d.sort_key, d.id LIMIT ?"""
    return con.execute(sql, (fts_match(words, op), limit)).fetchall()


def m_bm25(con, q, k=K):
    """FTS5 + BM25: every word must match the start of a word (the browser's search since 2026-11-13)."""
    words = norm(q).split()
    return [r for r, _ in bm25_scored(con, words, "AND", k)] if words else []


def m_bm25_or(con, q, k=K):
    """Like bm25, but when fewer than k rows match ALL words, fill up with rows matching ANY word."""
    words = norm(q).split()
    if not words:
        return []
    hits = [r for r, _ in bm25_scored(con, words, "AND", k)]
    if len(hits) < k and len(words) > 1:
        seen = set(hits)
        hits += [r for r, _ in bm25_scored(con, words, "OR", 2 * k) if r not in seen][: k - len(hits)]
    return hits


def fusion_inputs(con, dense, q):
    """BM25 (any word) and dense candidates for one query, each side rescaled to 0..1."""
    words = norm(q).split()
    bm = bm25_scored(con, words, "OR", POOL) if words else []
    dn = dense.top(q, POOL)
    cand = sorted({r for r, _ in bm} | {r for r, _ in dn})
    cos = dense.scores(q)
    d_raw = {r: float(cos[r - 1]) for r in cand}

    def rescale(d):
        if not d:
            return {}
        lo, hi = min(d.values()), max(d.values())
        return {r: (v - lo) / (hi - lo) if hi > lo else 1.0 for r, v in d.items()}

    b_n, d_n = rescale(dict(bm)), rescale(d_raw)
    ranks_b = {r: i for i, (r, _) in enumerate(bm, 1)}
    ranks_d = {r: i for i, (r, _) in enumerate(dn, 1)}
    return cand, b_n, d_n, ranks_b, ranks_d


def mix_rank(inputs, w, k=K):
    cand, b_n, d_n, _, _ = inputs
    return sorted(cand, key=lambda r: (-(w * b_n.get(r, 0.0) + (1 - w) * d_n[r]), r))[:k]


def rrf_rank(inputs, k=K):
    cand, _, _, rb, rd = inputs
    score = {r: (1 / (RRF_K + rb[r]) if r in rb else 0) + (1 / (RRF_K + rd[r]) if r in rd else 0) for r in cand}
    return sorted(cand, key=lambda r: (-score[r], r))[:k]


def rrf_fuse(lists, k=K):
    """Reciprocal rank fusion of any number of ranked rid lists."""
    score = defaultdict(float)
    for lst in lists:
        for i, r in enumerate(lst, 1):
            score[r] += 1 / (RRF_K + i)
    return sorted(score, key=lambda r: (-score[r], r))[:k]


def el_ranked(con, mode, words, op, limit):
    """Ranked rids from the offline Greek index (stemmed words as prefixes)."""
    stems = [el_stem(w) for w in words]
    sql = f"SELECT rowid FROM el_{mode}_fts WHERE el_{mode}_fts MATCH ? ORDER BY bm25(el_{mode}_fts), rowid LIMIT ?"
    return [r for (r,) in con.execute(sql, (el_match(stems, op), limit))]


def m_kw_el(con, q, mode, k=K):
    """Keyword only, plus the offline Greek index: Greek queries also search the translated names. No model."""
    words = norm(q).split()
    if not words:
        return []
    en = [r for r, _ in bm25_scored(con, words, "AND", k)]
    if not _HAS_GREEK.search(" ".join(words)):
        gl = greeklish_ranked(con, words, "AND", k)  # "karpouzi" -> items whose Greek words read karpuz...
        return rrf_fuse([en, gl], k) if gl else en
    return rrf_fuse([en, el_ranked(con, mode, words, "AND", k)], k)


def m_hyb_el(con, q, mode, model, k=K):
    """Hybrid: BM25 (English names) + BM25 (offline Greek index) + semantic, fused with RRF."""
    words = norm(q).split()
    lists = [[r for r, _ in bm25_scored(con, words, "OR", POOL)]] if words else []
    if words and _HAS_GREEK.search(" ".join(words)):
        lists.append(el_ranked(con, mode, words, "OR", POOL))
    elif words:
        lists.append(greeklish_ranked(con, words, "OR", POOL))
    lists.append([r for r, _ in Dense.get(model).top(q, POOL)])
    return rrf_fuse(lists, k)


def m_kw_mt(con, q, mt, k=K):
    """Keyword only, plus translating a Greek query to English at search time (model runs per Greek query)."""
    words = norm(q).split()
    if not words:
        return []
    lists = [[r for r, _ in bm25_scored(con, words, "AND", k)]]
    if _HAS_GREEK.search(" ".join(words)):
        en_words = norm(MT.get(mt).query(q)).split()
        if en_words:
            lists.append([r for r, _ in bm25_scored(con, en_words, "AND", k)])
    return rrf_fuse(lists, k)


def m_hyb_mt(con, q, mt, model, k=K):
    """Hybrid with query translation: for a Greek query, BM25 on the original + BM25 and semantic on the English."""
    words = norm(q).split()
    if not words or not _HAS_GREEK.search(" ".join(words)):
        return rrf_rank(fusion_inputs(con, Dense.get(model), q), k)
    q_en = MT.get(mt).query(q)
    en_words = norm(q_en).split()
    lists = [[r for r, _ in bm25_scored(con, words, "OR", POOL)]]
    if en_words:
        lists.append([r for r, _ in bm25_scored(con, en_words, "OR", POOL)])
    lists.append([r for r, _ in Dense.get(model).top(q_en or q, POOL)])
    return rrf_fuse(lists, k)


# ---------------------------------------------------------------------------
# Re-ranking (rr:METHOD): put "the real one" first.
#   1. closest name first: query vs the item's name, its name with brand, and its Greek translation,
#      allowing small spelling differences (musaka ~ moussaka); extra words in the name count against it
#   2. generic foods (OpenNutrition everyday / prepared) before branded variants
#   3. the original order breaks ties
# Candidates = the method's top RR_DEPTH + the best generic foods + typo-tolerant name matches (trigram index,
# only when the query matches fewer than 3 items exactly).
# No model.
# ---------------------------------------------------------------------------
RR_DEPTH = 30
GENERIC_BONUS = 0.08
TRANSLATED_WEIGHT = 0.9  # a name match through the offline word translation counts a little less than a direct one
GENERIC_FIRST_MIN_SIM = 0.6  # rrg: a generic food goes above all brands only if its name matches this well
POSITION_WEIGHT = 0.10


def ensure_name_trigrams():
    """Trigram index over each item's normalized name without 'by Brand' (built once per corpus, seconds)."""
    with closing(sqlite3.connect(LAB_DB.as_uri(), uri=True)) as con:
        if con.execute("SELECT 1 FROM sqlite_master WHERE name = 'names_tri'").fetchone():
            return
        t0 = time.time()
        con.create_function("base_norm", 1, lambda n: norm(base_name(n)), deterministic=True)
        con.executescript("""CREATE VIRTUAL TABLE names_tri USING fts5(name, tokenize='trigram');
                             INSERT INTO names_tri(rowid, name) SELECT rid, base_norm(name) FROM docs;""")
        con.commit()
        print(f"Built the name trigram index in {time.time() - t0:.0f}s", flush=True)


def trigram_candidates(con, q, limit):
    """Items whose name shares the most 3-letter pieces with the query, e.g. 'moussaka' for 'musaka'."""
    grams = sorted({w[i:i + 3] for w in norm(q).split() for i in range(len(w) - 2)})
    if not grams:
        return []
    sql = "SELECT rowid FROM names_tri WHERE names_tri MATCH ? ORDER BY bm25(names_tri), rowid LIMIT ?"
    return [r for (r,) in con.execute(sql, (" OR ".join(f'"{g}"' for g in grams), limit))]


GENERIC_TYPES = ("everyday", "prepared")


def build_generic_index():
    """Small FTS index of the generic foods only (OpenNutrition everyday + prepared, ~9 k items): English names and
    synonyms + the offline Greek words when they exist. Rebuilt when the re-ranker starts (under a second)."""
    with closing(sqlite3.connect(LAB_DB.as_uri(), uri=True)) as con:
        has_el = con.execute("SELECT 1 FROM sqlite_master WHERE name = 'el_words_fts'").fetchone()
        greek = f"COALESCE((SELECT e.text FROM el_words_fts e WHERE e.rowid = d.rid), '')" if has_el else "''"
        greek += " || ' ' || COALESCE((SELECT g.text FROM greeklish_fts g WHERE g.rowid = d.rid), '')"
        con.executescript(f"""DROP TABLE IF EXISTS generic_fts;
            CREATE VIRTUAL TABLE generic_fts USING fts5(text, tokenize='unicode61 remove_diacritics 2', prefix='2 3');
            INSERT INTO generic_fts(rowid, text)
                SELECT d.rid, d.search || ' ' || {greek} FROM docs d
                WHERE d.src = 'on' AND d.type IN {GENERIC_TYPES};""")
        con.commit()


def generic_candidates(con, q, limit):
    """Best-matching generic foods, so the plain food is always a candidate even when thousands of branded
    products match the query first."""
    words = norm(q).split()
    if not words:
        return []
    if _HAS_GREEK.search(" ".join(words)):
        match = el_match([el_stem(w) for w in words], "AND")
    else:  # English words, or Greeklish matched against the skeletons
        match = f"({fts_match(words, 'AND')}) OR ({el_match([skeleton(w) for w in words], 'AND')})"
    sql = "SELECT rowid FROM generic_fts WHERE generic_fts MATCH ? ORDER BY bm25(generic_fts), rowid LIMIT ?"
    return [r for (r,) in con.execute(sql, (match, limit))]


def few_keyword_hits(con, q, n=3):
    """True when the query's words match fewer than n items exactly (English or Greek index): a typo is likely,
    so the slower typo-tolerant trigram lookup is worth it."""
    words = norm(q).split()
    if not words:
        return False
    hits = con.execute("SELECT COUNT(*) FROM (SELECT 1 FROM docs_fts WHERE docs_fts MATCH ? LIMIT ?)",
                       (fts_match(words, "AND"), n)).fetchone()[0]
    if hits < n and not _HAS_GREEK.search(" ".join(words)):
        hits += len(greeklish_ranked(con, words, "AND", n))
    if hits < n and _HAS_GREEK.search(" ".join(words)) and con.execute(
            "SELECT 1 FROM sqlite_master WHERE name = 'el_words_fts'").fetchone():
        hits += con.execute("SELECT COUNT(*) FROM (SELECT 1 FROM el_words_fts WHERE el_words_fts MATCH ? LIMIT ?)",
                            (el_match([el_stem(w) for w in words], "AND"), n)).fetchone()[0]
    return hits < n


def token_sim(qt, nt):
    if qt == nt:
        return 1.0
    if len(qt) >= 3 and nt.startswith(qt):  # still typing: "γιαο" -> "γιαουρτ" (below a whole-word match)
        return 0.8
    if len(qt) >= 4 and len(nt) >= 4:
        r = difflib.SequenceMatcher(None, qt, nt).ratio()  # spelling: "musaka" vs "moussaka" = 0.86
        if r >= 0.75:
            return r
    return 0.0


# Words that don't make a product "something else" (normalized, stemmed): "Chicken Breast, Boneless Skinless, Cooked"
# counts as plain chicken breast, while "Fried Chicken Breast" has an extra word.
NEUTRAL_WORDS = {"raw", "cooked", "fresh", "plain", "boneless", "skinless", "boiled", "steamed", "regular", "original",
                 "whole", "classic", "natural", "ωμο", "ωμα", "ωμη", "μαγειρεμεν", "φρεσκ", "βραστ", "σκετ",
                 "ολοκληρ", "πληρ", "αποστεωμεν", "φυσικ", "κλασικ"}


def name_sim(q_tokens, n_tokens):
    """How well the query covers the name AND the name covers the query (extra words in the name cost,
    neutral words such as 'raw' or 'cooked' don't)."""
    if not q_tokens or not n_tokens:
        return 0.0
    used, total = set(), 0.0
    for qt in q_tokens:
        best, bi = 0.0, None
        for i, nt in enumerate(n_tokens):
            s = token_sim(qt, nt)
            if s > best:
                best, bi = s, i
        total += best
        if bi is not None:
            used.add(bi)
    content = [i for i, t in enumerate(n_tokens) if t not in NEUTRAL_WORDS]
    cover = len(used & set(content)) / len(content) if content else 1.0
    return (total / len(q_tokens)) * (0.6 + 0.4 * cover)


_EL2LAT_PAIRS = [("ου", "ou"), ("γκ", "g"), ("γγ", "ng"), ("τσ", "ts"), ("τζ", "tz"), ("θ", "th"), ("χ", "ch"),
                 ("ψ", "ps"), ("ξ", "x")]
_EL2LAT = str.maketrans("αβγδεζηικλμνοπρστυφω", "avgdeziiklmnoprstyfo")


def greek_to_latin(word):
    """Rough Greek -> Latin spelling of a normalized word, to compare a Greek query with English names
    (φετα -> feta, μουσακασ -> mousakas, μπανανα -> banana)."""
    if word.startswith("μπ"):
        word = "b" + word[2:]
    elif word.startswith("ντ"):
        word = "d" + word[2:]
    word = word.replace("μπ", "mp").replace("ντ", "nt")
    for a, b in _EL2LAT_PAIRS:
        word = word.replace(a, b)
    return word.translate(_EL2LAT)


class Reranker:
    _inst = None

    @classmethod
    def get(cls):
        if cls._inst is None:
            cls._inst = cls()
        return cls._inst

    def __init__(self):
        ensure_name_trigrams()
        ensure_greeklish_index()
        build_generic_index()
        with closing(connect()) as con:
            has_mt = con.execute("SELECT 1 FROM sqlite_master WHERE name = 'mt_words'").fetchone()
            self.mt_words = dict(con.execute("SELECT src, el FROM mt_words")) if has_mt else {}
            self.brands = self._brand_phrases(con)

    @staticmethod
    def _brand_phrases(con):
        """Brand names seen in the data ("... by Brand" in OpenNutrition, the brand field in OFF), used to tell a
        brand query ("coca cola zero") from a food query ("banana"). Left out: brands made only of words that also
        name generic foods (a brand called "Banana"), and single words that are common in product names ("organic")."""
        generic_words, word_freq, counts = set(), defaultdict(int), defaultdict(int)
        for name, src, typ, brand in con.execute("SELECT name, src, type, brand FROM docs"):
            base = norm(base_name(name)).split()
            for w in set(base):
                word_freq[w] += 1
            if src == "on" and typ in GENERIC_TYPES:
                generic_words.update(base)
            m = re.search(r"\s+by\s+(.+)$", name or "", re.IGNORECASE)
            phrase = norm(m.group(1)) if src == "on" and m else norm((brand or "").split(",")[0]) if src == "off" else ""
            if phrase:
                counts[phrase] += 1
        out = set()
        for phrase, c in counts.items():
            toks = phrase.split()
            if c < 2 or len(phrase) < 3 or len(toks) > 4 or set(toks) <= generic_words:
                continue
            if len(toks) == 1 and word_freq[toks[0]] > 2000:  # a descriptor like "organic", not a brand
                continue
            out.add(phrase)
        return out

    def query_brand(self, q):
        """The first brand name found in the query (as whole words), or None."""
        toks = norm(q).split()
        for n in range(min(4, len(toks)), 0, -1):
            for i in range(len(toks) - n + 1):
                phrase = " ".join(toks[i:i + n])
                if phrase in self.brands:
                    return phrase
        return None

    def reps(self, name, src):
        """(direct, translated) token lists the query is compared with: the name without brand and the full name,
        and the Greek word translation of OpenNutrition names."""
        base = base_name(name)
        direct = [[el_stem(t) for t in toks] for toks in (norm(base).split(), norm(name).split()) if toks]
        translated = []
        if src == "on" and self.mt_words:
            greek = norm(" ".join(self.mt_words.get(w, "") for w in _EN_WORD.findall(base.lower()))).split()
            if greek:
                translated.append([el_stem(t) for t in greek])
        return direct, translated

    def similarity(self, q_tokens, q_latin, q_skel, name, src):
        """Best match of the query with the item's names. A match through the word translation counts a little
        less than a direct one, so for φετα "Feta Cheese" (also matched as 'feta') beats "Apple Slices" (φέτες)."""
        direct, translated = self.reps(name, src)
        sims = [name_sim(q_tokens, toks) for toks in direct]
        if q_latin:
            sims += [name_sim(q_latin, toks) for toks in direct]
        sims += [TRANSLATED_WEIGHT * name_sim(q_tokens, toks) for toks in translated]
        if q_skel:  # Greeklish query: compare skeletons with the item's Greek words
            for toks in translated + [t for t in direct if any(_HAS_GREEK.search(x) for x in t)]:
                sims.append(TRANSLATED_WEIGHT * name_sim(q_skel, [skeleton(t) for t in toks]))
        return max(sims, default=0.0)

    def rerank(self, con, q, ranked, k=K, generic_first=False):
        """generic_first: non-brand foods that match well (name similarity >= GENERIC_FIRST_MIN_SIM) go above every
        branded product, unless the query names a brand."""
        q_tokens = [el_stem(t) for t in norm(q).split()]
        if not q_tokens:
            return ranked[:k]
        q_latin = [greek_to_latin(t) for t in norm(q).split()] if _HAS_GREEK.search(norm(q)) else None
        q_skel = None if q_latin else [skeleton(t) for t in norm(q).split()]
        typo = trigram_candidates(con, q, RR_DEPTH) if few_keyword_hits(con, q) else []
        cand = list(dict.fromkeys(ranked + typo + generic_candidates(con, q, 10 if not generic_first else RR_DEPTH)))
        if not cand:
            return []
        pos = {r: i for i, r in enumerate(ranked)}
        info = {r: (n, s, t) for r, n, s, t in con.execute(
            f"SELECT rid, name, src, type FROM docs WHERE rid IN ({','.join('?' * len(cand))})", cand)}
        group_generic = generic_first and self.query_brand(q) is None

        def score(r):
            name, src, typ = info[r]
            sim = self.similarity(q_tokens, q_latin, q_skel, name, src)
            is_generic = src == "on" and typ in GENERIC_TYPES
            position = POSITION_WEIGHT * (1 - pos[r] / len(ranked)) if r in pos else 0.0
            group = 0 if (group_generic and is_generic and sim >= GENERIC_FIRST_MIN_SIM) else 1
            return group, sim + (GENERIC_BONUS if is_generic else 0.0) + position

        scored = {r: score(r) for r in cand}
        return sorted(cand, key=lambda r: (scored[r][0], -scored[r][1], pos.get(r, RR_DEPTH), r))[:k]


EL_MODES = ("words", "names")


def get_method(spec):
    """Parse a method spec (see the module docstring) into a function (con, query, k=K) -> rids."""
    if spec.startswith("rr:"):
        base = get_method(spec[3:])
        return lambda con, q, k=K: Reranker.get().rerank(con, q, base(con, q, RR_DEPTH), k)
    if spec.startswith("rrg:"):
        base = get_method(spec[4:])
        return lambda con, q, k=K: Reranker.get().rerank(con, q, base(con, q, RR_DEPTH), k, generic_first=True)
    static = {"like": m_like, "bm25": m_bm25, "bm25_or": m_bm25_or}
    if spec in static:
        return static[spec]
    kind, *args = spec.split(":")
    ok = {
        "dense": lambda a: len(a) == 1 and a[0] in MODELS,
        "rrf": lambda a: len(a) == 1 and a[0] in MODELS,
        "mix": lambda a: len(a) == 2 and a[0] in MODELS,
        "kw_el": lambda a: len(a) == 1 and a[0] in EL_MODES,
        "hyb_el": lambda a: len(a) == 2 and a[0] in EL_MODES and a[1] in MODELS,
        "kw_mt": lambda a: len(a) == 1 and a[0] in MT_MODELS,
        "hyb_mt": lambda a: len(a) == 2 and a[0] in MT_MODELS and a[1] in MODELS,
    }
    if kind not in ok or not ok[kind](args):
        sys.exit(f"unknown method {spec!r} (see --help)")
    if kind == "dense":
        return lambda con, q, k=K: [r for r, _ in Dense.get(args[0]).top(q, k)]
    if kind == "rrf":
        return lambda con, q, k=K: rrf_rank(fusion_inputs(con, Dense.get(args[0]), q), k)
    if kind == "mix":
        weight = float(args[1])
        return lambda con, q, k=K: mix_rank(fusion_inputs(con, Dense.get(args[0]), q), weight, k)
    if kind == "kw_el":
        return lambda con, q, k=K: m_kw_el(con, q, args[0], k)
    if kind == "hyb_el":
        return lambda con, q, k=K: m_hyb_el(con, q, args[0], args[1], k)
    if kind == "kw_mt":
        return lambda con, q, k=K: m_kw_mt(con, q, args[0], k)
    return lambda con, q, k=K: m_hyb_mt(con, q, args[0], args[1], k)


def clear_query_caches():
    """Each timed call must pay for its own model work (query embedding, query translation), as on the server."""
    for d in Dense._cache.values():
        d._q.clear()
    for m in MT._cache.values():
        m._q.clear()


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
    return [{**q, "rules": compile_rules(by_id[q["same_as"]] if "same_as" in q else q)} for q in raw]


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
    for rid, id_, src, typ, name, brand, scans in con.execute("SELECT rid, id, src, type, name, brand, scans FROM docs"):
        docs[rid] = {"rid": rid, "id": id_, "src": src, "type": typ, "name": name or "", "brand": brand or "",
                     "scans": scans, "n_name": norm(name), "n_brand": norm(brand)}
    return docs


def correct_rids(queries, docs):
    """Correct items per query. Judging 120 queries against ~330 k items takes a while, so the result is cached
    per (test set, corpus) and twin queries (same_as) are judged once."""
    with closing(connect()) as con:
        key = hashlib.sha1(QUERIES.read_bytes() + (meta(con, "embed_sha") or "").encode()).hexdigest()
    cache = OUT_DIR / "correct_cache.json"
    if cache.exists():
        c = json.loads(cache.read_text())
        if c.get("key") == key:
            return {qid: set(rids) for qid, rids in c["correct"].items()}
    by_rules = {}
    for q in queries:
        src = q.get("same_as", q["id"])
        if src not in by_rules:
            by_rules[src] = {d["rid"] for d in docs.values() if is_correct(q["rules"], d)}
    out = {q["id"]: by_rules[q.get("same_as", q["id"])] for q in queries}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"key": key, "correct": {k: sorted(v) for k, v in out.items()}}))
    return out


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
    correct = correct_rids(queries, docs)
    empty = []
    for q in queries:
        rids = correct[q["id"]]
        by_src = defaultdict(int)
        for r in rids:
            by_src[docs[r]["src"]] += 1
        sample = sorted((docs[r] for r in rids), key=lambda d: (-(d["scans"] or 0), len(d["name"])))[:4]
        names = " | ".join(f"{d['name'][:38]}" for d in sample)
        print(f"{q['id']} {q['q'][:26]:26s} {len(rids):5d}  (off {by_src['off']:4d}, on {by_src['on']:4d})  {names}")
        if not rids:
            empty.append(q["id"])
    print(f"\n{len(queries)} queries, {len(queries) - len(empty)} answerable. "
          f"No correct item in the corpus (data gap, not a search problem): {', '.join(empty) or 'none'}")


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------
def first_rank(result_rids, ok):
    for rank, r in enumerate(result_rids, 1):
        if r in ok:
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


def setup():
    queries = load_queries()
    con = connect()
    docs = load_docs(con)
    correct = correct_rids(queries, docs)
    return con, docs, correct, queries, [q for q in queries if correct[q["id"]]]


def evaluate(methods):
    con, docs, correct, queries, answerable = setup()
    funcs = {m: get_method(m) for m in methods}
    for m in methods:  # load every model before timing anything (a Greek and an English warm-up query)
        funcs[m](con, "γαλα")
        funcs[m](con, "milk")
    ranks = {m: {} for m in methods}
    times = {m: [] for m in methods}
    details = []
    with closing(con):
        for q in answerable:
            entry = {"id": q["id"], "q": q["q"], "kind": q["kind"], "want": q["want"],
                     "n_correct": len(correct[q["id"]]), "methods": {}}
            for m in methods:
                clear_query_caches()
                t0 = time.perf_counter()
                res = funcs[m](con, q["q"])
                times[m].append(1000 * (time.perf_counter() - t0))
                ranks[m][q["id"]] = first_rank(res, correct[q["id"]])
                entry["methods"][m] = {"first_correct_rank": ranks[m][q["id"]],
                                       "top5": [{"name": docs[r]["name"], "brand": docs[r]["brand"], "src": docs[r]["src"],
                                                 "ok": r in correct[q["id"]]} for r in res[:5]]}
            details.append(entry)
        built = meta(con, "built_at")

    kinds = list(dict.fromkeys(q["kind"] for q in answerable))
    overall = {m: summarize(list(ranks[m].values())) for m in methods}
    per_kind = {m: {k: summarize([ranks[m][q["id"]] for q in answerable if q["kind"] == k]) for k in kinds} for m in methods}
    # first call per query includes embedding the query; that is the realistic server cost
    lat = {m: (statistics.mean(times[m]), sorted(times[m])[int(0.95 * (len(times[m]) - 1))]) for m in methods}

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
              f"Run {time.strftime('%Y-%m-%d %H:%M')} · corpus '{CORPUS}' built {built} · {len(docs):,} items · "
              f"{len(answerable)} of {len(queries)} queries answerable"]
    report = "\n".join(header + ["", "## Overall", ""] + overall_tbl + ["", "## hit@5 by query kind", ""] + kind_tbl
                       + ["", "## First correct rank per query (– = not in top 10)", ""] + rank_tbl) + "\n"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "report.md").write_text(report)
    (OUT_DIR / "details.json").write_text(json.dumps(details, ensure_ascii=False, indent=1))

    print(header[2], "", *overall_tbl, "", *kind_tbl, sep="\n")
    print(f"\nFull report: {OUT_DIR / 'report.md'}\nTop-5 per query and method: {OUT_DIR / 'details.json'}")


def sweep(model):
    """hit@1 / hit@5 / MRR for the weighted mix at BM25 weights 0, 0.1, ..., 1 (plus 0.25 and 0.75), and RRF."""
    con, docs, correct, queries, answerable = setup()
    dense = Dense.get(model)
    with closing(con):
        inputs = {q["id"]: fusion_inputs(con, dense, q["q"]) for q in answerable}
    weights = sorted({round(i / 10, 2) for i in range(11)} | {0.25, 0.75})
    lines = [f"Weighted mix for {model}: score = W x BM25 + (1 - W) x semantic, each rescaled to 0..1 per query",
             "", "| BM25 weight W | hit@1 | hit@5 | MRR@10 |", "|---|---|---|---|"]
    for w in weights:
        s = summarize([first_rank(mix_rank(inputs[q["id"]], w), correct[q["id"]]) for q in answerable])
        label = {0.0: "0 (semantic only)", 1.0: "1 (BM25 only, any word)"}.get(w, f"{w:g}")
        lines.append(f"| {label} | {s['hit1']:.0%} | {s['hit5']:.0%} | {s['mrr']:.2f} |")
    s = summarize([first_rank(rrf_rank(inputs[q["id"]]), correct[q["id"]]) for q in answerable])
    lines.append(f"| RRF (no weight) | {s['hit1']:.0%} | {s['hit5']:.0%} | {s['mrr']:.2f} |")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"sweep_{model}.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


# ---------------------------------------------------------------------------
# Compare page: type a query, see every method's top 10 side by side
# ---------------------------------------------------------------------------
COMPARE_HTML = HERE / "compare.html"


def method_label(spec):
    if spec.startswith("rr:"):
        return "Re-ranked · " + method_label(spec[3:])
    if spec.startswith("rrg:"):
        return "Re-ranked, non-brand first · " + method_label(spec[4:])
    kind, *a = spec.split(":")
    return {
        "like": lambda: "Old search (substring, A→Z)",
        "bm25": lambda: "Keyword · BM25 (current)",
        "bm25_or": lambda: "Keyword · BM25 + any-word fill-up",
        "dense": lambda: f"Semantic only · {a[0]}",
        "rrf": lambda: f"Hybrid RRF · {a[0]}",
        "mix": lambda: f"Hybrid {float(a[1]):g} BM25 / {1 - float(a[1]):g} semantic · {a[0]}",
        "kw_el": lambda: f"Keyword + offline Greek index ({a[0]}) · no model",
        "hyb_el": lambda: f"Hybrid + offline Greek index ({a[0]}) · {a[1]}",
        "kw_mt": lambda: f"Keyword + query translation · {a[0]}",
        "hyb_mt": lambda: f"Hybrid + query translation · {a[0]} · {a[1]}",
    }[kind]()


def compare_columns(models):
    cols = ["bm25"]
    for m in models:
        cols += [f"dense:{m}", f"rrf:{m}"]
    if models:
        cols.append(f"mix:{models[0]}:0.25")
    return cols


def serve(port, models, methods=None):
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import parse_qs, urlparse

    cols = [(m, method_label(m)) for m in (methods or compare_columns(models))]
    funcs = {m: get_method(m) for m, _ in cols}
    queries = load_queries()
    with closing(connect()) as con:
        docs = load_docs(con)
    correct = correct_rids(queries, docs)
    test_by_q = {norm(q["q"]): q for q in queries}
    examples = [{"id": q["id"], "q": q["q"], "kind": q["kind"]} for q in queries]
    lock = threading.Lock()  # one query at a time: the models are not shared safely across threads
    print("Loading models…", flush=True)
    with closing(connect()) as con:
        for m, _ in cols:  # warm-up loads every model before the first real query
            funcs[m](con, "γαλα")
            funcs[m](con, "milk")

    def compare(q):
        tq = test_by_q.get(norm(q))
        ok = correct[tq["id"]] if tq else None
        out = []
        with lock, closing(connect()) as con:
            for m, label in cols:
                clear_query_caches()  # each column pays for its own model work, as on the server
                t0 = time.perf_counter()
                res = funcs[m](con, q) if norm(q) else []
                ms = 1000 * (time.perf_counter() - t0)
                out.append({"method": m, "label": label, "ms": round(ms, 1), "first_ok": first_rank(res, ok) if ok else None,
                            "results": [{"name": docs[r]["name"], "brand": docs[r]["brand"], "src": docs[r]["src"],
                                         "type": docs[r]["type"], "ok": (r in ok) if ok is not None else None} for r in res]})
        return {"q": q, "test": {"id": tq["id"], "kind": tq["kind"], "want": tq["want"]} if tq else None, "columns": out}

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status, body, ctype):
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj):
            self._send(200, json.dumps(obj, ensure_ascii=False).encode(), "application/json; charset=utf-8")

        def do_GET(self):
            url = urlparse(self.path)
            if url.path in ("/", "/index.html"):
                self._send(200, COMPARE_HTML.read_bytes(), "text/html; charset=utf-8")
            elif url.path == "/api/examples":
                self._json({"examples": examples, "columns": [label for _, label in cols],
                            "corpus": {"name": CORPUS, "description": CORPORA[CORPUS][0], "items": len(docs)}})
            elif url.path == "/api/compare":
                self._json(compare(parse_qs(url.query).get("q", [""])[0].strip()[:200]))
            else:
                self._send(404, b'{"error": "not found"}', "application/json")

        def log_message(self, fmt, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Search compare page for corpus '{CORPUS}' ({len(docs):,} items) running at http://127.0.0.1:{port}"
          "  (Ctrl+C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--corpus", default="library", choices=list(CORPORA), help="which product set (default: library)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build", parents=[common], help="build the corpus + FTS5 index from work/browser.sqlite")
    ck = sub.add_parser("check", parents=[common], help="show how many correct items each test query has")
    ck.add_argument("--show", help="comma-separated query IDs: list every item counted as correct")
    em = sub.add_parser("embed", parents=[common], help="compute vectors for every corpus item")
    em.add_argument("--model", required=True, choices=list(MODELS))
    em.add_argument("--batch", type=int, default=64)
    sw = sub.add_parser("sweep", parents=[common], help="score the weighted mix at BM25 weights 0..1, and RRF")
    sw.add_argument("--model", required=True, choices=list(MODELS))
    tr = sub.add_parser("translate", parents=[common], help="offline: translate OpenNutrition names to Greek, index them")
    tr.add_argument("--mode", required=True, choices=EL_MODES)
    tr.add_argument("--mt", required=True, choices=[m for m in MT_MODELS if m.startswith("en-el")])
    tr.add_argument("--batch", type=int, default=64)
    ev = sub.add_parser("eval", parents=[common], help="score search methods on the test set")
    ev.add_argument("--methods", default="like,bm25,bm25_or", help="comma-separated; see the method list above")
    ev.add_argument("--threads", type=int, help="CPU threads for the models (1 = per-core speed)")
    sv = sub.add_parser("serve", parents=[common], help="web page: type a query, compare the methods side by side")
    sv.add_argument("--port", type=int, default=8767)
    sv.add_argument("--models", default="e5-small", help=f"comma-separated, from: {', '.join(MODELS)}")
    sv.add_argument("--methods", help="comma-separated method specs for the columns (overrides --models)")
    args = ap.parse_args()
    set_corpus(args.corpus)
    if getattr(args, "threads", None):
        import torch
        torch.set_num_threads(args.threads)
    if args.cmd == "serve":
        models = [m.strip() for m in args.models.split(",") if m.strip()]
        unknown = [m for m in models if m not in MODELS]
        if unknown:
            sys.exit(f"unknown model(s): {', '.join(unknown)}")
        methods = [m.strip() for m in args.methods.split(",") if m.strip()] if args.methods else None
        return serve(args.port, models, methods)
    if args.cmd == "translate":
        return translate_corpus(args.mode, args.mt, args.batch)
    if args.cmd == "build":
        build()
    elif args.cmd == "check":
        check(set(args.show.split(",")) if args.show else None)
    elif args.cmd == "embed":
        embed(args.model, args.batch)
    elif args.cmd == "sweep":
        sweep(args.model)
    else:
        evaluate([m.strip() for m in args.methods.split(",") if m.strip()])


if __name__ == "__main__":
    main()
