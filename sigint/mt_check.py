"""MFSK vs THOR tie-break by trial decoding in fldigi (user's choice, 2026-11-21: "same rules as
Olivia/Contestia").

MFSK and THOR sub-modes share symbol rates on air (measured: results/fldigi_rates.json, e.g.
MFSK16 and THOR16 both show a 15.5 Hz rate line) and have similar widths. They differ in how
tones carry data: MFSK sends Varicode with FEC on plain tones; THOR uses incremental frequency
keying (IFK+), where the data is the tone *difference* between symbols
(https://www.sigidwiki.com/wiki/MFSK , https://www.sigidwiki.com/wiki/THOR). A decoder of the
wrong family therefore produces junk, so the window is played into fldigi once per candidate
sub-mode, and the family whose decoder prints cleaner text wins.

Scope: like sigint/oc_check.py, this runs a content decoder only to choose between two look-alike
families. The decoded text is scored in memory and discarded; it is never returned, logged or
stored.
"""
from __future__ import annotations

import time

from .oc_check import _play, _smoothed_peak, score

FAMILIES = ("mfsk", "thor")
FAM_OF = lambda mode: "mfsk" if mode.startswith("MFSK") else "thor"
# 20 dB widths measured on the fldigi takes (results/fldigi_rates.json):
# MFSK8 254, MFSK16 268, MFSK32 516, MFSK64 1025; THOR8 298, THOR11 218, THOR16 317, THOR22 436 Hz.
GROUPS = {
    "narrow": ["MFSK8", "MFSK16", "THOR8", "THOR11", "THOR16"],
    "mid": ["MFSK16", "MFSK32", "THOR16", "THOR22"],
    "wide": ["MFSK64", "MFSK32", "THOR22"],
}
ALL = ["MFSK8", "MFSK16", "MFSK32", "MFSK64", "THOR8", "THOR11", "THOR16", "THOR22"]


def candidates(bw_hz):
    if bw_hz is None or bw_hz < 150:
        return ALL
    return GROUPS["narrow"] if bw_hz < 380 else (GROUPS["mid"] if bw_hz < 750 else GROUPS["wide"])


def features(txt: str) -> dict:
    t = txt.strip()
    n = len(t)
    toks = t.split()
    # Generic text-cleanliness counts only; nothing tied to the test transmissions' vocabulary.
    return dict(chars=n, score=score(t),
                symbols=sum(not (c.isalnum() or c.isspace()) for c in t),
                letters=sum(c.isalpha() for c in t), spaces=sum(c == " " for c in t),
                tokens=len(toks), clean_tokens=sum(1 for w in toks if w.isalnum() and len(w) <= 10))


def decide(client, x12k, centre_hz, bw_hz, settle=3.0):
    """Return (family or None, {submode: features}). None leaves the classifier's label."""
    modes = candidates(bw_hz)
    if bw_hz is None or bw_hz < 150 or centre_hz is None:
        centre_hz = _smoothed_peak(x12k)
    feats = {}
    for mode in modes:
        client.proxy.modem.set_by_name(mode)
        client.proxy.modem.set_carrier(int(round(centre_hz)))
        client.proxy.main.set_squelch(False)
        client.clear()
        time.sleep(0.3)
        _play(x12k)
        time.sleep(settle)          # MFSK8/THOR8 interleavers need a few seconds to flush
        txt = client.rx_text()
        client.clear()               # decoded text is discarded here
        feats[mode] = features(txt)
        del txt
    return rule(feats), feats


def rule(feats, min_tokens=8, max_sym=0.03, min_clean=0.85):
    """Family whose decoder prints clean text: at least `min_tokens` words, at most `max_sym`
    of the characters are punctuation/symbols, and at least `min_clean` of the words are
    purely letters/digits. If decoders of both families (or neither) pass, return None.
    Uses only generic counts, nothing about the vocabulary of the test transmissions.
    Tuned on 60 training-split windows (stress/tune_mt.py, results/tune_mt.json): 41 right,
    0 wrong, 19 undecided. Every setting on the grid tokens 6/8/10, symbols 0.02/0.03/0.05,
    clean 0.85/0.9/0.95 gave 0 wrong; this one is mid-grid."""
    ok = {FAM_OF(m) for m, v in feats.items()
          if v["tokens"] >= min_tokens and v["symbols"] <= max_sym * v["chars"]
          and v["clean_tokens"] >= min_clean * v["tokens"]}
    return ok.pop() if len(ok) == 1 else None
