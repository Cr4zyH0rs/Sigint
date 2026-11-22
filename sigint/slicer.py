"""Cut 15 s UTC-aligned windows from the ring buffer and resample to 12 kHz.

FT8 transmissions start 0.5 s after each 15 s UTC boundary (:00, :15, :30, :45)
and jt9 expects 15 s of 16-bit 12000 Hz mono (WSJT-X User Guide, sec. "FT8";
Franke, Somerville & Taylor, QEX 2020). Resampling uses
scipy.signal.resample_poly (polyphase FIR with Kaiser window).
"""
from __future__ import annotations

import math

import numpy as np
from scipy.signal import resample_poly

PERIOD = 15.0
OUT_FS = 12000


def period_start(utc: float, period: float = PERIOD) -> float:
    """Most recent period boundary at or before utc."""
    return math.floor(utc / period) * period


def next_boundaries(last_done: float | None, now: float, period: float = PERIOD):
    """Yield period starts whose full window has elapsed and haven't been sliced yet."""
    newest_complete = period_start(now, period) - period
    start = newest_complete if last_done is None else last_done + period
    t = start
    while t <= newest_complete + 1e-9:
        yield t
        t += period


def to_12k(x: np.ndarray, fs_in: int) -> np.ndarray:
    if fs_in == OUT_FS:
        return x.astype(np.float32)
    g = math.gcd(OUT_FS, fs_in)
    return resample_poly(x, OUT_FS // g, fs_in // g).astype(np.float32)


def slice_window(capture, t_start: float, period: float = PERIOD):
    """Return a 12 kHz window for [t_start, t_start+period) or None if unavailable."""
    i0 = capture.utc_to_index(t_start)
    if i0 is None:
        return None
    n = int(round(period * capture.fs))
    raw = capture.ring.read_abs(i0, n)
    if raw is None:
        return None
    y = to_12k(raw, capture.fs)
    want = int(period * OUT_FS)
    if len(y) != want:  # guard against off-by-one from rounding
        y = np.pad(y, (0, max(0, want - len(y))))[:want]
    return y
