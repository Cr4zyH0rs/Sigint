#!/bin/bash
# Batch 10: fldigi IFKP, PSK-R, multi-carrier PSK and OFDM; 6 training seeds x 160 s per class, 1 test seed.
cd "$(dirname "$0")/.."
export XDG_RUNTIME_DIR=/tmp/xdg PULSE_SERVER=unix:/tmp/xdg/pulse/native
for seed in 109; do
  [ -f /tmp/claude-0/rec10_done_$seed ] && continue
  python3 stress/record_fldigi.py data/fldigi_tx/test 160 $seed ifkp,pskr,mcpsk,ofdm && touch /tmp/claude-0/rec10_done_$seed
done
for seed in 101 102 103 104 105 106; do
  [ -f /tmp/claude-0/rec10_done_$seed ] && continue
  python3 stress/record_fldigi.py data/fldigi_tx/train 160 $seed ifkp,pskr,mcpsk,ofdm && touch /tmp/claude-0/rec10_done_$seed
done
