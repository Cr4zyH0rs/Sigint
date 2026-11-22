#!/bin/bash
# Batch 6: build 3-channel data for the 5 new classes, fine-tune the 33-class mc3_10 model to 38.
cd "$(dirname "$0")/.."
export XDG_RUNTIME_DIR=/tmp/xdg SIGINT_FEATS=mc SIGINT_INIT=data/resnet18_modes_mc3_10.pt SIGINT_MAXLR=1e-3
[ -f data/val_mc_b6.npz ] || python3 stress/make_dataset.py 600 mc6
python3 -u stress/train.py 10 mc6 b6_10
