#!/bin/bash
# Batch 15: build 3-channel data for the 5 digital-voice-on-FM classes, fine-tune the 71-class b14_10 model to 76.
cd "$(dirname "$0")/.."
export XDG_RUNTIME_DIR=/tmp/xdg SIGINT_FEATS=mc SIGINT_INIT=data/resnet18_modes_b14_10.pt SIGINT_MAXLR=1e-3 SIGINT_MMAP=1
[ -f data/val_mc_b15.npz ] || python3 stress/make_dataset.py 600 mc15
python3 -u stress/train.py 10 mc15 b15_10
