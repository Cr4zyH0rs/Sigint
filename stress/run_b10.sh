#!/bin/bash
# Batch 10: build 3-channel data for the 6 new classes, fine-tune the 55-class b9_10 model to 61.
cd "$(dirname "$0")/.."
export XDG_RUNTIME_DIR=/tmp/xdg SIGINT_FEATS=mc SIGINT_INIT=data/resnet18_modes_b9_10.pt SIGINT_MAXLR=1e-3
[ -f data/val_mc_b10.npz ] || python3 stress/make_dataset.py 600 mc10
python3 -u stress/train.py 10 mc10 b10_10
