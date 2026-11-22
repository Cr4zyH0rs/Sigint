"""Olivia vs Contestia tie-break by trial decoding in fldigi (user's choice, 2026-11-20).

Olivia and Contestia sub-modes have identical tones, symbol rate and bandwidth on air
(measured: results/fldigi_rates.json); they differ only in their FEC block coding
(Contestia is derived from Olivia: https://www.sigidwiki.com/wiki/Contestia ,
https://www.sigidwiki.com/wiki/Olivia). So when the classifier says Olivia or Contestia,
the window is played into fldigi once per candidate sub-mode of each family, and the
family whose decoder prints the most word-like text wins.

Scope: this is the only place the ID pipeline runs a content decoder outside --label-mode.
The decoded text is scored in memory and discarded; it is never returned, logged or stored.
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
import time

import numpy as np
import soundfile as sf

FAMILIES = ("olivia", "contestia")
# nominal bandwidth -> fldigi sub-mode names per family (sub-modes used in this project)
SUBMODES = {
    250: {"olivia": ["OLIVIA-8/250"], "contestia": ["Cont-8/250"]},
    500: {"olivia": ["OLIVIA-16/500", "OLIVIA-8/500"], "contestia": ["Cont-16/500", "Cont-8/500"]},
    1000: {"olivia": ["OLIVIA-32/1K"], "contestia": ["Cont-32/1K"]},
}
_WORD = re.compile(r"[A-Za-z0-9]{2,}")
# English letter frequencies (%), R. Lewand, "Cryptological Mathematics", MAA 2000, p. 36
_EN = dict(zip("abcdefghijklmnopqrstuvwxyz",
               [8.167, 1.492, 2.782, 4.253, 12.702, 2.228, 2.015, 6.094, 6.966, 0.153, 0.772, 4.025,
                2.406, 6.749, 7.507, 1.929, 0.095, 5.987, 6.327, 9.056, 2.758, 0.978, 2.360, 0.150,
                1.974, 0.074]))


def nominal_bw(bw_hz):
    if bw_hz is None:
        return None
    return 250 if bw_hz < 375 else (500 if bw_hz < 750 else 1000)


def score(text: str) -> float:
    """How English-like the decoded text is: log-likelihood ratio of its letters under English
    letter frequencies vs uniform letters, minus a penalty for symbols. A wrong-mode decode
    prints near-random characters (first version counted word-like tokens, which garbage from
    the Contestia decoder also produced)."""
    llr = 0.0
    for ch in text.lower():
        if ch in _EN:
            llr += np.log((_EN[ch] / 100) / (1 / 26))
        elif ch.isdigit() or ch in " \n\r":
            continue
        else:
            llr -= 1.0
    return float(llr)


def _play(x, sink="radio"):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        sf.write(f.name, (x / (np.abs(x).max() + 1e-12) * 0.5).astype(np.float32), 12000,
                 subtype="PCM_16")
    try:
        subprocess.run(["paplay", f"--device={sink}", f.name], check=True, timeout=60)
    finally:
        os.unlink(f.name)


def _smoothed_peak(x, lo=300.0, hi=2700.0):
    from scipy.signal import welch
    f, p = welch(x, fs=12000, nperseg=4096)
    k = max(1, int(100 / (f[1] - f[0])))
    ps = np.convolve(p, np.ones(k) / k, mode="same")
    b = (f >= lo) & (f <= hi)
    return float(f[b][np.argmax(ps[b])])


def decide(client, x12k, centre_hz, bw_hz, settle=1.5):
    """Return (family or None, {submode: score}). None when no candidate prints words, or the
    bandwidth is unknown; the caller then keeps the classifier's label."""
    # Low-SNR windows often get no (or an implausibly narrow) bandwidth from the occupancy
    # estimate; 12 of 14 undecided tuning windows were like that. Then try every sub-mode,
    # tuned to the peak of a 100 Hz-smoothed spectrum.
    if bw_hz is None or bw_hz < 150 or centre_hz is None:
        modes = [m for nb in SUBMODES.values() for fam in FAMILIES for m in nb[fam]]
        centre_hz = _smoothed_peak(x12k)
    else:
        nb = nominal_bw(bw_hz)
        modes = [m for fam in FAMILIES for m in SUBMODES[nb][fam]]
    scores = {}
    for mode in modes:
        client.proxy.modem.set_by_name(mode)
        client.proxy.modem.set_carrier(int(round(centre_hz)))
        client.proxy.main.set_squelch(False)
        client.clear()
        time.sleep(0.3)
        _play(x12k)
        time.sleep(settle)          # let the decoder flush its last block
        txt = client.rx_text()
        client.clear()               # decoded text is discarded here
        scores[mode] = dict(score=score(txt), chars=len(txt.strip()),
                            symbols=sum(not (c.isalnum() or c.isspace()) for c in txt))
        del txt
    return rule(scores), scores


def rule(scores, min_chars=10, lo=0.10, hi=0.15):
    """Decision from the Contestia decoders' output only. Contestia's character set has no
    lower case and its decoder prints clean text on a Contestia signal, but punctuation-heavy
    garbage on an Olivia signal; the Olivia decoder mostly prints nothing on Contestia, which
    is less informative. Tuned on 50 training-split windows (stress/tune_oc.py,
    results/tune_oc.json): 41 right, 0 wrong, 9 undecided (all at SNR <= -1 dB).
    The English-letter score above is kept as a diagnostic only."""
    rat = [v["symbols"] / v["chars"] for k, v in scores.items()
           if k.startswith("Cont") and v["chars"] >= min_chars]
    if not rat:
        return None
    if min(rat) < lo:
        return "contestia"
    if min(rat) > hi:
        return "olivia"
    return None
