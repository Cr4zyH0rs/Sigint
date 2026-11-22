#!/bin/bash
# Round 2: rebuild 3-channel dataset with 5x more fldigi audio, fine-tune from mc25. Restart-safe.
cd "$(dirname "$0")/.."
export XDG_RUNTIME_DIR=/tmp/xdg SIGINT_FEATS=mc SIGINT_INIT=data/resnet18_modes_mc25.pt SIGINT_MAXLR=1e-3
[ -f data/val_mc.npz ] || python3 stress/make_dataset.py 600 mc
python3 -u stress/train.py 15 mc mc2_15
