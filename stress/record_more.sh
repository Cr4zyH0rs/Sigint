#!/bin/bash
# Extra fldigi training takes (round 2 of the 99% push): 4 more seeds x 160 s per class.
cd "$(dirname "$0")/.."
export XDG_RUNTIME_DIR=/tmp/xdg PULSE_SERVER=unix:/tmp/xdg/pulse/native
for seed in 21 22 23 24; do
  [ -f /tmp/claude-0/rec_done_$seed ] && continue
  python3 stress/record_fldigi.py data/fldigi_tx/train 160 $seed && touch /tmp/claude-0/rec_done_$seed
done
