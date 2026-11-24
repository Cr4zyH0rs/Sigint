#!/bin/bash
# Batch 14: build 3-channel data for the 5 IC-7100 VHF/UHF classes, fine-tune the 66-class b11_10 model to 71.
cd "$(dirname "$0")/.."
export XDG_RUNTIME_DIR=/tmp/xdg SIGINT_FEATS=mc SIGINT_INIT=data/resnet18_modes_b11_10.pt SIGINT_MAXLR=1e-3 SIGINT_MMAP=1
[ -f data/val_mc_b14.npz ] || python3 stress/make_dataset.py 600 mc14
python3 -u stress/train.py 10 mc14 b14_10
