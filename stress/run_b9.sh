#!/bin/bash
# Batch 9: build 3-channel data for the 7 new classes, fine-tune the 48-class b8_10 model to 55.
cd "$(dirname "$0")/.."
export XDG_RUNTIME_DIR=/tmp/xdg SIGINT_FEATS=mc SIGINT_INIT=data/resnet18_modes_b8_10.pt SIGINT_MAXLR=1e-3
[ -f data/val_mc_b9.npz ] || python3 stress/make_dataset.py 600 mc9
python3 -u stress/train.py 10 mc9 b9_10
