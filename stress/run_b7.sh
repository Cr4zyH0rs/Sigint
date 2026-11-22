#!/bin/bash
# Batch 7: build 3-channel data for the 5 new classes, fine-tune the 38-class b6_10 model to 43.
cd "$(dirname "$0")/.."
export XDG_RUNTIME_DIR=/tmp/xdg SIGINT_FEATS=mc SIGINT_INIT=data/resnet18_modes_b6_10.pt SIGINT_MAXLR=1e-3
[ -f data/val_mc_b7.npz ] || python3 stress/make_dataset.py 600 mc7
python3 -u stress/train.py 10 mc7 b7_10
