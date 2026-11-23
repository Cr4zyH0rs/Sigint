#!/bin/bash
# Batch 8: build 3-channel data for the 5 new classes, fine-tune the 43-class b7_10 model to 48.
cd "$(dirname "$0")/.."
export XDG_RUNTIME_DIR=/tmp/xdg SIGINT_FEATS=mc SIGINT_INIT=data/resnet18_modes_b7_10.pt SIGINT_MAXLR=1e-3
[ -f data/val_mc_b8.npz ] || python3 stress/make_dataset.py 600 mc8
python3 -u stress/train.py 10 mc8 b8_10
