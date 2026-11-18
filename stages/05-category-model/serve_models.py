#!/usr/bin/env python3
"""Stage 05: live category tester, model side (no generative AI).

Loads Qwen3-Embedding-0.6B and Arctic-embed-l-v2 once, with the training set trainset.CURRENT (USDA foods +
definition phrases + OFF products from out/off_train.json; see REPORT.md), and answers one product at a time over local HTTP.
The page is http://127.0.0.1:8765/category-test (tools/browser/foods_browser.py forwards to this service).

    HF_HUB_OFFLINE=1 .venv/bin/python -I stages/05-category-model/serve_models.py      # http://127.0.0.1:8766

Start-up: about 30 s. The labelled foods' embeddings come from the per-text cache out/store_*.npy (embstore.py);
the classifiers are trained once and cached in out/lr_*.npz (coefficients only, no pickle).

    GET  /health    {"ready": true, ...}
    POST /predict   {"name": "...", "description": "...", "ingredients": "...", "fat": 3.1, "sugars": null}
                    -> for each text (title, title+desc, title+desc+ingr): every model's top 3 with confidence,
                       the 3-model vote, the agreement level and the 5 nearest labelled foods per model
"""
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from bench import CATS, HF_CACHE, MODELS, NEVER, OUT, ROOT, apply_rules, first_sentence, knn_scores  # noqa: E402
from embstore import Store  # noqa: E402
import trainset  # noqa: E402
from text_variants import KEYS, compose, ingredients_text  # noqa: E402
from vote import VOTE, agreement, rank_vote  # noqa: E402

PORT = 8766
HOSTS = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}  # refuse other Host headers (DNS rebinding)
LIMITS = {"name": 300, "description": 3000, "ingredients": 6000}
SRC = {"fndds": "USDA food", "definition": "our definition", "off": "OFF product"}


class Models:
    def __init__(self, langs=("en", "el"), variant=None):
        """langs: which OFF examples to use ("en" English names, "el" Greek names); variant: a training set from
        trainset.VARIANTS (default trainset.CURRENT). Embeddings come from the per-text cache (embstore.py)."""
        from sentence_transformers import SentenceTransformer

        t0 = time.time()
        cats = json.loads(CATS.read_text())["categories"]
        self.classes = [c["code"] for c in cats if c["code"] not in NEVER]
        self.variant = variant or trainset.CURRENT
        self.ref_text, self.ref_code, self.ref_src, _ = trainset.build(cats, self.variant, langs)
        self.m, self.R, self.lr = {}, {}, {}
        for key in KEYS:
            hub, qp, _ = MODELS[key]
            local = ROOT / "work" / "models" / "st" / hub.replace("/", "__")
            model = SentenceTransformer(str(local) if (local / "config.json").exists() else hub,
                                        cache_folder=str(HF_CACHE), device="mps")
            self.m[key] = (model, qp)
            store = Store(key)
            if store.missing(self.ref_text):
                print(f"  {key}: embedding {len(store.missing(self.ref_text)):,} new labelled foods (once)", flush=True)
                store.fill(lambda xs, k=key: self.encode(k, xs), self.ref_text)
            self.R[key] = store.get(self.ref_text)
            del store
            self.lr[key] = trainset.classifier(key, self.ref_text, self.ref_code, self.R[key])
            print(f"  {key}: ready ({time.time() - t0:.0f}s)", flush=True)
        self.labelled = len(self.ref_text)

    def encode(self, key, xs):
        model, qp = self.m[key]
        return model.encode(xs, prompt=qp, batch_size=64, normalize_embeddings=True, convert_to_numpy=True,
                            show_progress_bar=False).astype(np.float32)

    def scores(self, key, texts):
        """-> (similarity to every labelled food, {"lr": class probabilities, "knn": class vote shares}) per text."""
        P = self.encode(key, texts)
        sim = P @ self.R[key].T
        lr = self.lr[key]
        proba = lr.predict_proba(P)
        lr_full = np.zeros((len(texts), len(self.classes)))
        for j, c in enumerate(lr.classes_):
            lr_full[:, self.classes.index(c)] = proba[:, j]
        return sim, {"lr": lr_full, "knn": knn_scores(sim, self.ref_code, self.classes)}

    def top3(self, row, nutr):
        """Same top 3 as bench.predict: best 3 classes, then the nutrient rules (duplicates they create dropped)."""
        top = []
        for j in np.argsort(-row)[:3]:
            code = apply_rules(self.classes[j], nutr)
            if code not in [t["code"] for t in top]:
                top.append({"code": code, "p": round(float(row[j]), 3),
                            "ruled_from": self.classes[j] if code != self.classes[j] else None})
        return top

    def predict(self, name, description, ingredients, nutr):
        texts = compose(name, first_sentence(description), ingredients_text(ingredients))
        names = list(texts)
        out = {v: {"text": texts[v], "models": {}, "neighbours": {}} for v in names}
        for key in KEYS:
            sim, per_method = self.scores(key, [texts[v] for v in names])
            for i, v in enumerate(names):
                for method, scores in per_method.items():
                    out[v]["models"][f"{key}|{method}"] = self.top3(scores[i], nutr)
                out[v]["neighbours"][key] = [
                    {"text": self.ref_text[j], "code": str(self.ref_code[j]), "src": SRC.get(str(self.ref_src[j]), ""),
                     "sim": round(float(sim[i, j]), 3)} for j in np.argsort(-sim[i])[:5]]
        for v in names:
            tops = [[t["code"] for t in out[v]["models"][f"{k}|{m}"]] for k, m in VOTE]
            out[v]["vote"] = [{"code": c, "points": round(p, 1)} for c, p in rank_vote(tops)][:3]
            out[v]["agreement"] = agreement(tops)
        return out


MODELS_READY = None


def clean_request(body):
    if not isinstance(body, dict):
        raise ValueError("expected a JSON object")
    out = {}
    for field, limit in LIMITS.items():
        v = body.get(field) or ""
        if not isinstance(v, str):
            raise ValueError(f"{field} must be text")
        out[field] = v[:limit]
    if not out["name"].strip():
        raise ValueError("name is required")
    nutr = {}
    for field, key in (("fat", "total_fat"), ("sugars", "total_sugars")):
        v = body.get(field)
        if v is not None and v != "":
            try:
                if isinstance(v, bool) or not isinstance(v, (int, float, str)):
                    raise ValueError
                v = float(v)
            except ValueError:
                raise ValueError(f"{field} must be a number") from None
            if not 0 <= v <= 100:
                raise ValueError(f"{field} must be 0-100 g per 100 g")
            nutr[key] = v
    out["nutr"] = nutr
    return out


class Handler(BaseHTTPRequestHandler):
    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _host_ok(self):
        if self.headers.get("Host") in HOSTS:
            return True
        self._json({"error": "bad host"}, 403)
        return False

    def do_GET(self):
        if not self._host_ok():
            return
        if self.path == "/health":
            return self._json({"ready": True, "models": KEYS, "vote": [f"{k}|{m}" for k, m in VOTE],
                               "labelled_foods": MODELS_READY.labelled, "training_set": MODELS_READY.variant,
                               "training_label": trainset.VARIANTS[MODELS_READY.variant]["label"]})
        self._json({"error": "not found"}, 404)

    def do_POST(self):
        if not self._host_ok():
            return
        if self.path != "/predict":
            return self._json({"error": "not found"}, 404)
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            return self._json({"error": "expected application/json"}, 415)
        length = int(self.headers.get("Content-Length") or 0)
        if length > 50_000:
            return self._json({"error": "too large"}, 413)
        try:
            req = clean_request(json.loads(self.rfile.read(length) or b"{}"))
        except ValueError as e:
            return self._json({"error": str(e)}, 400)
        t0 = time.time()
        res = MODELS_READY.predict(req["name"], req["description"], req["ingredients"], req["nutr"])
        self._json({"variants": res, "nutr_used": req["nutr"], "ms": round((time.time() - t0) * 1000)})

    def log_message(self, fmt, *args):
        pass


def main():
    global MODELS_READY
    print("Loading the category models…", flush=True)
    MODELS_READY = Models()
    server = HTTPServer(("127.0.0.1", PORT), Handler)  # one request at a time: the GPU models are not thread-safe
    print(f"Category model service ready at http://127.0.0.1:{PORT} "
          f"({MODELS_READY.labelled:,} labelled foods). Page: http://127.0.0.1:8765/category-test", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    sys.exit(main())
