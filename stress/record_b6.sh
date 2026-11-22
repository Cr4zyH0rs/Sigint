#!/bin/bash
# Batch 6: fldigi 8PSK (FSQ: fldigi transmitted only ~5 s per take via XML-RPC, so FSQ moves to the spec-built group), 8 training seeds x 160 s per class, 1 test seed.
cd "$(dirname "$0")/.."
export XDG_RUNTIME_DIR=/tmp/xdg PULSE_SERVER=unix:/tmp/xdg/pulse/native
for seed in 59; do
  [ -f /tmp/claude-0/rec6_done_$seed ] && continue
  python3 stress/record_fldigi.py data/fldigi_tx/test 160 $seed psk8 && touch /tmp/claude-0/rec6_done_$seed
done
for seed in 51 52 53 54 55 56 57 58; do
  [ -f /tmp/claude-0/rec6_done_$seed ] && continue
  python3 stress/record_fldigi.py data/fldigi_tx/train 160 $seed psk8 && touch /tmp/claude-0/rec6_done_$seed
done
