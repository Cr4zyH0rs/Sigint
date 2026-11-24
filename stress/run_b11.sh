#!/bin/bash
# Batch 11: build 3-channel data for the 5 new classes, fine-tune the 61-class b10_10 model to 66.
cd "$(dirname "$0")/.."
export XDG_RUNTIME_DIR=/tmp/xdg SIGINT_FEATS=mc SIGINT_INIT=data/resnet18_modes_b10_10.pt SIGINT_MAXLR=1e-3 SIGINT_MMAP=1
[ -f data/val_mc_b11.npz ] || python3 stress/make_dataset.py 600 mc11
python3 -u stress/train.py 10 mc11 b11_10
