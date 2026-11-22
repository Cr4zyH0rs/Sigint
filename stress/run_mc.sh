#!/bin/bash
# Build the 3-channel dataset (if missing) and train/resume the 3-channel model. Restart-safe.
cd "$(dirname "$0")/.."
export XDG_RUNTIME_DIR=/tmp/xdg SIGINT_FEATS=mc
[ -f data/val_mc.npz ] || python3 stress/make_dataset.py 600 mc
python3 -u stress/train.py ${1:-25} mc mc${1:-25}
