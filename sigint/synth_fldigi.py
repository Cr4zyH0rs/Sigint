"""Batch 3 generators: windows cut from real fldigi transmissions.

Audio was produced by fldigi 4.2.03's own modulators (stress/record_fldigi.py):
fldigi transmits into a PulseAudio null sink and parecord captures it at 12 kHz.
Separate takes (different seeds and carrier frequencies) are used for training
and testing; set SIGINT_FLDIGI_SPLIT=train|test (default test).

Each window: random 15 s slice of a random take of that class (sub-modes rotate
across takes), random frequency shift, unit RMS, then AWGN at the requested SNR
(2500 Hz reference, same as the other generators).
"""
from __future__ import annotations

import glob
import os
from functools import lru_cache

import numpy as np
import soundfile as sf
from scipy.signal import hilbert, welch

from .synth import FS, N_WIN, add_awgn

NEW_CLASSES = ["olivia", "contestia", "mfsk", "thor", "dominoex", "mt63", "hell", "throb"]
ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "fldigi_tx")


@lru_cache(maxsize=None)
def _takes(split: str, cls: str):
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, split, f"{cls}__*.wav"))):
        x, fs = sf.read(f, dtype="float64")
        assert fs == FS, f
        on = np.flatnonzero(np.abs(x) > 0.01 * np.abs(x).max())
        x = x[on[0]:on[-1]] if len(on) else x  # trim silence before key-up / after abort
        sub = os.path.basename(f).split("__")[1]
        out.append((sub, x))
    if not out:
        raise FileNotFoundError(f"no fldigi takes for {cls} in {split}")
    return out


def _centroid_bw(x):
    f, p = welch(x, fs=FS, nperseg=4096)
    band = (f > 100) & (f < 3500)
    f, p = f[band], p[band]
    occ = f[p > 0.01 * p.max()]
    return float(np.sum(f * p) / np.sum(p)), float(occ.max() - occ.min())


def generate(cls: str, rng, snr_db: float):
    split = os.environ.get("SIGINT_FLDIGI_SPLIT", "test")
    takes = _takes(split, cls)
    sub, x = takes[int(rng.integers(len(takes)))]
    if len(x) > N_WIN:
        s = int(rng.integers(0, len(x) - N_WIN))
        x = x[s:s + N_WIN]
    else:  # shorter take: place it at a random offset
        y = np.zeros(N_WIN)
        s = int(rng.integers(0, N_WIN - len(x) + 1))
        y[s:s + len(x)] = x
        x = y
    c0, bw = _centroid_bw(x)
    half = min(bw / 2 + 50, 1250)
    target = float(rng.uniform(max(300 + half, 700), min(2900 - half, 2300)) if 2900 - half > 300 + half else 1600)
    x = np.real(hilbert(x) * np.exp(2j * np.pi * (target - c0) * np.arange(N_WIN) / FS))
    on = np.abs(x) > 1e-3 * np.abs(x).max()
    x = x / np.sqrt(np.mean(x[on] ** 2))
    return add_awgn(x, snr_db, rng, 1.0), dict(submode=sub, centre=target)
