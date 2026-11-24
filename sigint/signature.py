"""Signature checks for labels the classifier over-uses on weak signals (WWV, DTMF, HamDRM).

Batches 8-10 showed these three labels acting as catch-alls: weak, bursty or noise-like windows
of other modes were called WWV (87 windows), HamDRM (70) and DTMF (50) in
results/classifier_b10_10_seed5.json. A label is kept only if the window shows the signal's
published signature; otherwise the next most likely class is used instead.

  WWV/WWVH  a 5 ms tick at 1000 Hz (WWV) or 1200 Hz (WWVH) every second
            (https://www.nist.gov/pml/div688/grp40/wwv_format). Test: a 5 ms matched filter at each
            tick tone, folded at exactly 1.000 s; require a narrow peak (a tick, not a 100 ms RWM
            pulse or a steady tone).
  DTMF      one row tone (697/770/852/941 Hz) plus one column tone (1209/1336/1477/1633 Hz)
            at once (https://en.wikipedia.org/wiki/Dual-tone_multi-frequency_signaling); tones
            last >= 20 ms (https://www.sigidwiki.com/wiki/Dual_Tone_Multi_Frequency_(DTMF)).
            Test: per 20 ms frame (5 ms hop), the strongest row and column tones both stand 4 dB
            clear of the other tones and of the band floor; count frames in runs of >= 3
            frames (about 30 ms) with the same pair.
  HamDRM    DRM OFDM timing: symbol Ts = 26 2/3 ms with useful part Tu = 24 ms (mode A) or
            21 1/3 ms (mode B), i.e. a cyclic prefix (ETSI ES 201 980 clause 4.4.2.2 table 2,
            https://www.etsi.org/deliver/etsi_ES/201900_201999/201980/04.03.01_60/es_201980v040301p.pdf).
            Test: the product x[n] x[n+Tu], folded at Ts, has a peak where the prefix sits;
            compared with the same fold at a lag that is not Tu. (This tests the published
            symbol timing rather than the pilot layout, which is assumed in our generator and
            would make the check circular.)

Added in batch 11, when two new classes became catch-alls (results/classifier_b11_10_seed5.json):
  STANAG 4539  ACF 119.6 ms (https://www.sigidwiki.com/wiki/STANAG_4539). Test: robust z-score of the
               complex-baseband |ACF| at 119.58 ms (287 symbols at 2400 Bd) against lags 80-160 ms.
  3G ALE       8-PSK at 2400 Bd centred at 1800 Hz
               (https://www.sigidwiki.com/wiki/Automatic_Link_Establishment_(3G_ALE_ARCS)). Test: dB by
               which the 2400 Hz symbol-rate line of the squared envelope stands above 300-3000 Hz.

Thresholds are set by stress/tune_signature.py on training-seed windows (not the test windows).
"""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfiltfilt

FS = 12000
THRESH = {"wwv": 3.0, "dtmf": 2, "hamdrm": 3.0, "stanag4539": 0.0, "ale3g": 0.0}  # overwritten by tuning
CHECKED = ("wwv", "dtmf", "hamdrm", "stanag4539", "ale3g")


def _bp(x, f, half_bw):
    sos = butter(4, [f - half_bw, f + half_bw], "bandpass", fs=FS, output="sos")
    return sosfiltfilt(sos, x)


def wwv_score(x: np.ndarray) -> float:
    """Robust z-score of a narrow peak in the 1 s-folded output of a 5 ms tick matched filter
    (max over 1000 / 1200 Hz). The peak must stand above the profile 30-100 ms away too, so a
    100 ms RWM pulse or a steady tone does not count."""
    best = 0.0
    n = (len(x) // FS) * FS
    t = np.arange(60) / FS                                            # 5 ms
    idx = np.arange(400)
    for f in (1000.0, 1200.0):
        h = np.exp(-2j * np.pi * f * t) * np.hanning(60)
        y = np.abs(np.convolve(x[:n], h, mode="same")) ** 2
        prof = y.reshape(-1, FS).mean(0).reshape(-1, 30).mean(1)      # fold at 1.000 s, 2.5 ms bins
        i = int(np.argmax(prof))
        med = np.median(prof)
        mad = np.median(np.abs(prof - med)) + 1e-12
        d = np.minimum(np.abs(idx - i), 400 - np.abs(idx - i))
        near = np.median(prof[(d >= 12) & (d <= 40)])
        best = max(best, float((prof[i] - max(near, med)) / (1.4826 * mad)))
    return best


ROWS = np.array([697.0, 770.0, 852.0, 941.0])
COLS = np.array([1209.0, 1336.0, 1477.0, 1633.0])


def dtmf_score(x: np.ndarray, margin_db: float = 4.0, min_run: int = 3) -> int:
    """Frames (20 ms window, 5 ms hop) inside runs of >= min_run frames where the same row and
    column tone both stand margin_db clear of the other row/column tones and of the band floor.
    (Settings picked on 40 DTMF and 40 weak non-DTMF windows, stress/tune_signature.py notes.)"""
    win, hop = 240, 60
    w = np.hanning(win)
    fr = np.fft.rfftfreq(1024, 1 / FS)
    ri = [int(np.argmin(abs(fr - f))) for f in ROWS]
    ci = [int(np.argmin(abs(fr - f))) for f in COLS]
    band = (fr > 500) & (fr < 2000)
    lim = 10 ** (margin_db / 10)
    total, run, last = 0, 0, None
    for s in range(0, len(x) - win, hop):
        P = np.abs(np.fft.rfft(x[s:s + win] * w, 1024)) ** 2
        floor = np.median(P[band]) + 1e-12
        r, c = P[ri], P[ci]
        a, b = int(np.argmax(r)), int(np.argmax(c))
        ok = (r[a] > lim * floor and c[b] > lim * floor and
              r[a] > lim * np.max(np.delete(r, a)) and c[b] > lim * np.max(np.delete(c, b)))
        if ok and last == (a, b):
            run += 1
        else:
            if run >= min_run:
                total += run
            run, last = (1, (a, b)) if ok else (0, None)
    if run >= min_run:
        total += run
    return total


def hamdrm_score(x: np.ndarray) -> float:
    """Cyclic-prefix fold contrast at DRM timing, best of modes A and B, minus a control lag."""
    ts = 320
    out = 0.0
    for tu, tg in ((288, 32), (256, 64)):
        def fold(lag):
            y = x[:-lag] * x[lag:]
            y = np.convolve(y, np.ones(tg) / tg, mode="same")
            n = (len(y) // ts) * ts
            prof = y[:n].reshape(-1, ts).mean(0)
            return (prof.max() - np.median(prof)) / (np.mean(x ** 2) + 1e-12)
        out = max(out, float(fold(tu) / (fold(tu + 37) + 1e-6)))
    return out


def stanag4539_score(x: np.ndarray) -> float:
    from .acf import acf_profile
    lags, r = acf_profile(x, 1800.0, 80.0, 160.0)
    pk = float(r[np.abs(lags - 119.58) <= 0.5].max())
    med = np.median(r)
    mad = np.median(np.abs(r - med)) + 1e-12
    return float((pk - med) / (1.4826 * mad))


def ale3g_score(x: np.ndarray) -> float:
    from scipy.signal import hilbert, welch
    e = np.abs(hilbert(x)) ** 2
    f, p = welch(e - e.mean(), FS, nperseg=FS)
    band = (f > 300) & (f < 3000)
    k = np.abs(f - 2400) <= 1
    return float(10 * np.log10(p[k].max() / (np.median(p[band]) + 1e-30)))


SCORES = {"wwv": wwv_score, "dtmf": dtmf_score, "hamdrm": hamdrm_score,
          "stanag4539": stanag4539_score, "ale3g": ale3g_score}


def passes(label: str, x: np.ndarray) -> bool:
    return SCORES[label](x) >= THRESH[label]


def reweight(label, probs, classes, x):
    """Keep `label` if its signature is present; otherwise take the most likely class whose
    signature is present (unchecked classes always pass). Returns (label, conf, probs, note)."""
    if label not in CHECKED:
        return label, float(probs[classes.index(label)]), probs, None
    p = np.array(probs, float)
    tried = []
    for i in np.argsort(-p):
        c = classes[i]
        if c in CHECKED:
            tried.append(c)
            if not passes(c, x):
                continue
        note = None if c == label else f"{label} signature absent; next choice {c}"
        return c, float(p[i]), probs, note
    return label, float(p[classes.index(label)]), probs, "no class passed"


def _load_thresholds():
    import json
    import os
    f = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "signature_thresholds.json")
    if os.path.exists(f):
        THRESH.update(json.load(open(f)))


_load_thresholds()
