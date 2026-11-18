#!/usr/bin/env python3
"""Stage 05: do Greek training names help products with only a Greek name? (owner, 2026-11-18; no generative AI)

Test set: out/greek_test.json, written by build_off_train.py. Products with only a Greek name, held out (never trained
on); the answer is the category given by their Open Food Facts tags (tools/categories/off_map.py), not checked by a
person. The same models are trained without and with the Greek examples; the product text is the name.

    HF_HUB_OFFLINE=1 .venv/bin/python -I stages/05-category-model/eval_greek.py   # ≈ 10 min the first time
      -> out/greek_eval.json + a score table on screen
"""
import gc
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from bench import CATS, OUT  # noqa: E402
from serve_models import Models  # noqa: E402
from text_variants import KEYS  # noqa: E402
from vote import LEVELS, VOTE, agreement, rank_vote  # noqa: E402

CHECKS = ["Κουλούρι κανέλας", "Κουλούρι Θεσσαλονίκης"]  # the owner's example (no OFF tags, so not in the test set)
RUNS = {"English names only": ("en",), "+ Greek names": ("en", "el")}
MEMBERS = {"vote": "3-model vote", "qwen3-0.6b|lr": "Qwen3 classifier", "qwen3-0.6b|knn": "Qwen3 kNN",
           "arctic-l-v2|knn": "Arctic kNN", "arctic-l-v2|lr": "Arctic classifier"}


def run(models, texts, nutrs):
    tops = {}
    for key in KEYS:
        _, per_method = models.scores(key, texts)
        for m, sc in per_method.items():
            tops[f"{key}|{m}"] = [[t["code"] for t in models.top3(sc[i], nutrs[i])] for i in range(len(texts))]
    members = [[tops[f"{k}|{m}"][i] for k, m in VOTE] for i in range(len(texts))]
    tops["vote"] = [[c for c, _ in rank_vote(x)][:3] for x in members]
    tops["agree"] = [agreement(x) for x in members]
    return tops


def main():
    import torch

    cats = {c["code"]: c["name"] for c in json.loads(CATS.read_text())["categories"]}
    test = json.loads((OUT / "greek_test.json").read_text())["products"]
    texts = [p["text"] for p in test] + CHECKS
    nutrs = [p["nutr"] or {} for p in test] + [{}] * len(CHECKS)
    res = {}
    for name, langs in RUNS.items():
        print(f"== {name}", flush=True)
        models = Models(langs)
        res[name] = run(models, texts, nutrs)
        del models
        gc.collect()
        torch.mps.empty_cache()
    n = len(test)
    truth = [p["code"] for p in test]
    acc = lambda tops, k: sum(truth[i] in tops[i][:k] for i in range(n)) / n  # noqa: E731

    print(f"\n{n} products with only a Greek name (answer = their OFF tags). Top-1 (top-3):")
    print(f"{'':20}" + "".join(f"{r:>24}" for r in RUNS))
    for m, label in MEMBERS.items():
        print(f"{label:20}" + "".join(f"{acc(res[r][m], 1):>15.1%} ({acc(res[r][m], 3):5.1%})" for r in RUNS))
    for r in RUNS:
        parts = []
        for lv, lname in LEVELS.items():
            idx = [i for i in range(n) if res[r]["agree"][i] == lv]
            right = sum(res[r]["vote"][i][0] == truth[i] for i in idx)
            parts.append(f"{lname}: {len(idx)} products, vote right {right / max(len(idx), 1):.0%}")
        print(f"agreement, {r}: " + " · ".join(parts))
    before, after = (res[r]["vote"] for r in RUNS)
    fixed = [i for i in range(n) if before[i][0] != truth[i] and after[i][0] == truth[i]]
    broke = [i for i in range(n) if before[i][0] == truth[i] and after[i][0] != truth[i]]
    print(f"\nvote fixed {len(fixed)}, broke {len(broke)}")
    for tag, idx in (("fixed", fixed[:12]), ("broke", broke[:8])):
        for i in idx:
            print(f"  {tag}: {texts[i]} | {before[i][0]} {cats[before[i][0]]} -> {after[i][0]} {cats[after[i][0]]} "
                  f"(answer {truth[i]} {cats[truth[i]]})")
    print("\nowner's example:")
    for j, t in enumerate(CHECKS):
        i = n + j
        print(f"  {t}: " + " | ".join(f"{r}: {', '.join(f'{c} {cats[c]}' for c in res[r]['vote'][i])} ({res[r]['agree'][i]})"
                                      for r in RUNS))
    (OUT / "greek_eval.json").write_text(json.dumps({"test": test, "checks": CHECKS, "results": res},
                                                    ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.exit(main())
