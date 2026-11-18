"""Stage 05: embedding cache per text and model, so training sets that share texts embed each text only once.

    out/store_<model>.npy   one row per text (float32, normalised)
    out/store_<model>.json  the texts, in row order
Both are git-ignored and can be deleted at any time (they are rebuilt, which takes a while).
"""
import json
import time

import numpy as np

from bench import OUT


class Store:
    def __init__(self, key):
        self.key = key
        self.vec_path, self.idx_path = OUT / f"store_{key}.npy", OUT / f"store_{key}.json"
        if self.vec_path.exists() and self.idx_path.exists():
            self.texts = json.loads(self.idx_path.read_text())
            self.V = np.load(self.vec_path)
            assert len(self.texts) == len(self.V), f"{self.vec_path} and {self.idx_path} disagree"
        else:
            self.texts, self.V = [], None
        self.pos = {t: i for i, t in enumerate(self.texts)}

    def missing(self, texts):
        return [t for t in dict.fromkeys(texts) if t not in self.pos]

    def add(self, texts, vectors):
        texts = [t for t in texts]
        vectors = np.asarray(vectors, dtype=np.float32)
        self.V = vectors if self.V is None else np.concatenate([self.V, vectors])
        for t in texts:
            self.pos[t] = len(self.texts)
            self.texts.append(t)
        self.save()

    def save(self):
        tmp_v, tmp_i = self.vec_path.with_suffix(".tmp.npy"), self.idx_path.with_suffix(".tmp.json")
        np.save(tmp_v, self.V)
        tmp_i.write_text(json.dumps(self.texts, ensure_ascii=False))
        tmp_v.replace(self.vec_path)
        tmp_i.replace(self.idx_path)

    def fill(self, encode, texts, chunk=20_000):
        """Embed the texts not in the store yet with encode(list of texts) -> array; saves after every chunk."""
        todo = self.missing(texts)
        t0 = time.time()
        for i in range(0, len(todo), chunk):
            part = todo[i:i + chunk]
            self.add(part, encode(part))
            done = i + len(part)
            rate = done / max(time.time() - t0, 1e-9)
            print(f"  {self.key}: embedded {done:,}/{len(todo):,} ({rate:.0f}/s, "
                  f"≈ {(len(todo) - done) / max(rate, 1e-9) / 60:.0f} min left)", flush=True)
        return len(todo)

    def get(self, texts):
        return self.V[[self.pos[t] for t in texts]]
