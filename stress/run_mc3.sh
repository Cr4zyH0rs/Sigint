#!/bin/bash
# Round 3: rebuild 3-channel dataset with more MFSK/THOR/Olivia/Contestia audio, fine-tune from mc2_15.
cd "$(dirname "$0")/.."
export XDG_RUNTIME_DIR=/tmp/xdg SIGINT_FEATS=mc SIGINT_INIT=data/resnet18_modes_mc2_15.pt SIGINT_MAXLR=5e-4
[ -f data/val_mc.npz ] || python3 stress/make_dataset.py 600 mc
python3 -u stress/train.py 10 mc mc3_10
