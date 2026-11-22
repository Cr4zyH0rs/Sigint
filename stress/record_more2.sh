#!/bin/bash
# Round 3: more MFSK/THOR (and Olivia/Contestia) training audio, 4 seeds x 160 s each.
cd "$(dirname "$0")/.."
export XDG_RUNTIME_DIR=/tmp/xdg PULSE_SERVER=unix:/tmp/xdg/pulse/native
for seed in 41 42 43 44; do
  [ -f /tmp/claude-0/rec3_done_$seed ] && continue
  python3 stress/record_fldigi.py data/fldigi_tx/train 160 $seed mfsk,thor,olivia,contestia && touch /tmp/claude-0/rec3_done_$seed
done
