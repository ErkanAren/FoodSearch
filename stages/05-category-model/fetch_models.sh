#!/bin/bash
# Download sentence-transformers models with curl (resumable, retries stalled transfers) into work/models/st/<name>/.
# Used because the Hugging Face client's download hung for 2 h on 2026-11-16. Files skipped: ONNX exports, images, eval results.
set -u
cd "$(dirname "$0")/../.."
for repo in "$@"; do
  dest="work/models/st/${repo//\//__}"
  mkdir -p "$dest"
  files=$(curl -s --max-time 30 -A "generic-client/1.0" "https://huggingface.co/api/models/$repo" | python3 -I -c '
import json, sys
skip = ("onnx/", "imgs/", ".eval_results/", "openvino/", "colbert", "sparse_linear", ".gitattributes", "README", "long.jpg")
for s in json.load(sys.stdin)["siblings"]:
    f = s["rfilename"]
    if not any(f.startswith(x) or x in f for x in skip):
        print(f)')
  # prefer safetensors: skip pytorch_model.bin when model.safetensors exists
  if echo "$files" | grep -qx "model.safetensors"; then files=$(echo "$files" | grep -vx "pytorch_model.bin"); fi
  for f in $files; do
    mkdir -p "$dest/$(dirname "$f")"
    curl -sSL -A "generic-client/1.0" --retry 8 --retry-all-errors --retry-delay 5 -C - \
         --speed-limit 20000 --speed-time 60 -o "$dest/$f" "https://huggingface.co/$repo/resolve/main/$f" \
      || { echo "FAILED $repo/$f"; exit 1; }
  done
  echo "done $repo -> $dest ($(du -sh "$dest" | cut -f1))"
done
