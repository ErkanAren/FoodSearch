#!/usr/bin/env python3
"""Stage 05 (owner, 2026-11-19): fine-tune Qwen3-Embedding-0.6B itself on our labelled foods. No generative AI.

Until now the embedding models were used as downloaded; only the classifier and the kNN memory on top learned from our
labelled foods. Here the model's top layers learn too:
  * a cosine classifier head (one vector per category, started from the category means of the original embeddings)
    on the model's normalised embedding; cross-entropy with label smoothing 0.1, because the OFF labels are noisy;
  * the top --layers transformer layers and the final norm are trained, the rest stays frozen (faster, less memory,
    less forgetting of what the model already knows);
  * training data: the current training set (trainset.CURRENT) minus 2 % of its OFF products, held out to watch the
    accuracy during training. The test products (200 answer key, Greek-only, big test) are never in the training set.
Afterwards the fine-tuned model is used like the others (eval_finetune.py: classifier + kNN on its embeddings).

    HF_HUB_OFFLINE=1 .venv/bin/python -I stages/05-category-model/finetune.py --probe   # speed and memory, 60 steps
    HF_HUB_OFFLINE=1 .venv/bin/python -I stages/05-category-model/finetune.py           # one pass over the data
Outputs (git-ignored): work/models/st/local__qwen3-0.6b-ft (≈ 2.4 GB), out/finetune_log.json
"""
import argparse
import hashlib
import json
import math
import random
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from bench import CATS, HF_CACHE, MODELS, OUT, ROOT  # noqa: E402
from embstore import Store  # noqa: E402
import trainset  # noqa: E402

KEY = "qwen3-0.6b"
FT_DIR = ROOT / "work" / "models" / "st" / "local__qwen3-0.6b-ft"
LOG = OUT / "finetune_log.json"


def held_out(key):
    return bool(key) and int(hashlib.sha1(key.encode()).hexdigest()[:8], 16) % 50 == 0  # 2 % of OFF products


def batches(idx, lengths, size, rng):
    """Shuffled batches of similar length (less padding = faster), in random order."""
    idx = list(idx)
    rng.shuffle(idx)
    out = []
    for s in range(0, len(idx), size * 50):
        chunk = sorted(idx[s:s + size * 50], key=lambda i: lengths[i])
        out += [chunk[j:j + size] for j in range(0, len(chunk), size)]
    rng.shuffle(out)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", default=trainset.CURRENT, choices=list(trainset.VARIANTS))
    ap.add_argument("--layers", type=int, default=8, help="top transformer layers to train (of 28)")
    ap.add_argument("--epochs", type=float, default=1.0)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--max-len", type=int, default=128, help="tokens per text")
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--head-lr", type=float, default=5e-3)
    ap.add_argument("--probe", action="store_true", help="60 steps to measure speed and memory, nothing saved")
    args = ap.parse_args()

    import torch
    import torch.nn.functional as F
    from sentence_transformers import SentenceTransformer
    from sentence_transformers.util import batch_to_device

    t0 = time.time()
    rng = random.Random(0)
    torch.manual_seed(0)
    cats = json.loads(CATS.read_text())["categories"]
    texts, codes, _, keys = trainset.build(cats, args.set)
    classes = sorted(set(codes))
    y_all = np.array([classes.index(c) for c in codes])
    val = [i for i, k in enumerate(keys) if held_out(k)]
    val_set = set(val)
    train = [i for i in range(len(texts)) if i not in val_set]
    hub, qp, _ = MODELS[KEY]

    # head start: category means of the original (frozen) embeddings, from the cache
    R = Store(KEY).get([texts[i] for i in train])
    W0 = np.zeros((len(classes), R.shape[1]), dtype=np.float32)
    np.add.at(W0, y_all[train], R)
    W0 /= np.linalg.norm(W0, axis=1, keepdims=True)
    del R

    dev = "mps"
    model = SentenceTransformer(hub, cache_folder=str(HF_CACHE), device=dev)
    loaded_dtype = next(model.parameters()).dtype  # bfloat16: fine for embedding, too coarse for training updates
    model.float()
    model.max_seq_length = args.max_len
    tr = model[0].auto_model
    for p in tr.parameters():
        p.requires_grad = False
    for layer in tr.layers[-args.layers:]:
        for p in layer.parameters():
            p.requires_grad = True
    for p in tr.norm.parameters():
        p.requires_grad = True
    body = [p for p in model.parameters() if p.requires_grad]
    head = torch.nn.Parameter(torch.tensor(W0, device=dev))
    scale = 20.0
    opt = torch.optim.AdamW([{"params": body, "lr": args.lr, "weight_decay": 0.01},
                             {"params": [head], "lr": args.head_lr, "weight_decay": 0.0}])
    lengths = [len(texts[i]) for i in range(len(texts))]
    plan = []
    while len(plan) < math.ceil(len(train) * args.epochs / args.batch):
        plan += batches(train, lengths, args.batch, rng)
    plan = plan[:60] if args.probe else plan[:math.ceil(len(train) * args.epochs / args.batch)]
    warm = max(1, len(plan) // 20)
    sched = torch.optim.lr_scheduler.LambdaLR(  # linear warm-up over 5 % of the steps, then linear decay to 0
        opt, lambda s: (s + 1) / warm if s < warm else max(0.0, (len(plan) - s) / max(1, len(plan) - warm)))
    print(f"set {args.set}: {len(train):,} training texts, {len(val):,} held out, {len(classes)} categories · "
          f"training the top {args.layers} of {len(tr.layers)} layers ({sum(p.numel() for p in body) / 1e6:.0f}M "
          f"weights) · {len(plan):,} steps of {args.batch} ({time.time() - t0:.0f}s)", flush=True)

    def embed(ix, grad):
        feats = batch_to_device(model.preprocess([texts[i] for i in ix], prompt=qp), dev)  # as model.encode(prompt=qp)
        with torch.set_grad_enabled(grad):
            return model(feats)["sentence_embedding"]

    def val_acc(n=3000):
        model.eval()
        ix = val[:n]
        right = 0
        with torch.no_grad():
            Wn = F.normalize(head, dim=1)
            for s in range(0, len(ix), 64):
                b = ix[s:s + 64]
                pred = (embed(b, False) @ Wn.T).argmax(1).cpu().numpy()
                right += int((pred == y_all[b]).sum())
        model.train()
        return right / len(ix)

    model.eval()  # check: our forward pass gives the same embeddings as model.encode()
    a = model.encode([texts[i] for i in train[:4]], prompt=qp, normalize_embeddings=True, convert_to_tensor=True)
    b = embed(train[:4], False)
    print(f"  check vs model.encode(): cosine {F.cosine_similarity(a, b).min().item():.5f}", flush=True)
    log = {"args": vars(args), "steps": [], "val": []}
    if not args.probe:
        a = val_acc()
        log["val"].append((0, a))
        print(f"  held-out accuracy before training: {a:.1%}", flush=True)
    model.train()
    t1, seen, run_loss, run_acc, k = time.time(), 0, 0.0, 0.0, 0
    for step, b in enumerate(plan, 1):
        yb = torch.tensor(y_all[b], device=dev)
        emb = embed(b, True)
        logits = scale * emb @ F.normalize(head, dim=1).T
        loss = F.cross_entropy(logits, yb, label_smoothing=0.1)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(body + [head], 1.0)
        opt.step()
        sched.step()
        opt.zero_grad(set_to_none=True)
        seen += len(b)
        run_loss += loss.item()
        run_acc += (logits.argmax(1) == yb).float().mean().item()
        k += 1
        if step % (20 if args.probe else 200) == 0 or step == len(plan):
            rate = seen / (time.time() - t1)
            left = (len(plan) - step) * args.batch / rate
            mem = torch.mps.driver_allocated_memory() / 2 ** 30
            print(f"  step {step:,}/{len(plan):,} · loss {run_loss / k:.3f} · batch accuracy {run_acc / k:.1%} · "
                  f"{rate:.0f} texts/s · ≈ {left / 60:.0f} min left · GPU memory {mem:.1f} GB", flush=True)
            log["steps"].append((step, run_loss / k, run_acc / k, rate))
            run_loss, run_acc, k = 0.0, 0.0, 0
        if not args.probe and (step % 2000 == 0 or step == len(plan)):
            a = val_acc()
            log["val"].append((step, a))
            print(f"  held-out accuracy: {a:.1%}", flush=True)
            LOG.write_text(json.dumps(log))
    if args.probe:
        print(f"probe done in {(time.time() - t0) / 60:.1f} min; full run ≈ "
              f"{math.ceil(len(train) / args.batch) * args.batch / (seen / (time.time() - t1)) / 60:.0f} min per pass")
        return
    FT_DIR.parent.mkdir(parents=True, exist_ok=True)
    model.to(loaded_dtype)  # saved in the original's format, so embedding runs as fast as before
    model.save(str(FT_DIR))
    (FT_DIR / "finetune.json").write_text(json.dumps({"from": hub, "set": args.set, **vars(args),
                                                      "classes": classes}, indent=1))
    LOG.write_text(json.dumps(log))
    print(f"saved -> {FT_DIR} · done in {(time.time() - t0) / 60:.0f} min")


if __name__ == "__main__":
    sys.exit(main())
