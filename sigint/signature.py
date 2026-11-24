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

Added in batch 14 (selcall_ccir became a catch-all, results/classifier_b14_10_seed5.json):
  CCIR selcall  tones 0=1981 1=1124 2=1197 3=1275 4=1358 5=1446 6=1540 7=1640 8=1747 9=1860
                E(repeat)=2110 Hz, 100 ms (CCIR-1) or 70 ms (CCIR-2) per tone
                (https://www.sigidwiki.com/wiki/CCIR_Selcall). Test: per 40 ms frame (5 ms hop) the
                strongest CCIR tone must stand 3 dB clear of the band floor and of the other CCIR
                tones; score = number of single-tone segments lasting 30-120 ms of hops, counting only
                segments in runs of >= 3 back-to-back different tones (a 5-tone call has 5).

Thresholds are set by stress/tune_signature.py on training-seed windows (not the test windows).
"""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfiltfilt

FS = 12000
THRESH = {"wwv": 3.0, "dtmf": 2, "hamdrm": 3.0, "stanag4539": 0.0, "ale3g": 0.0, "selcall_ccir": 0}  # overwritten by tuning
CHECKED = ("wwv", "dtmf", "hamdrm", "stanag4539", "ale3g", "selcall_ccir")


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


CCIR_TONES = np.array([1981, 1124, 1197, 1275, 1358, 1446, 1540, 1640, 1747, 1860, 2110], float)


def selcall_score(x: np.ndarray, margin_db: float = 3.0) -> int:
    win, hop = 480, 60
    w = np.hanning(win)
    fr = np.fft.rfftfreq(1024, 1 / FS)
    ti = [int(np.argmin(abs(fr - f))) for f in CCIR_TONES]
    band = (fr > 900) & (fr < 2300)
    lim = 10 ** (margin_db / 10)
    seq = []                                   # per frame: tone index or -1
    for s in range(0, len(x) - win, hop):
        P = np.abs(np.fft.rfft(x[s:s + win] * w, 1024)) ** 2
        t = P[ti]
        a = int(np.argmax(t))
        ok = t[a] > lim * (np.median(P[band]) + 1e-12) and t[a] > lim * np.max(np.delete(t, a))
        seq.append(a if ok else -1)
    segs = []                                  # (tone, start frame, length)
    i = 0
    while i < len(seq):
        j = i
        while j < len(seq) and seq[j] == seq[i]:
            j += 1
        segs.append((seq[i], i, j - i))
        i = j
    good = [s[0] >= 0 and 6 <= s[2] <= 24 for s in segs]       # 30-120 ms of 5 ms hops (40 ms frames)
    score, run, prev_end, prev_tone = 0, 0, None, None
    for g, (tone, st, ln) in zip(good, segs):
        if g and prev_end is not None and st - prev_end <= 3 and tone != prev_tone:
            run += 1
        elif g:
            if run >= 3:
                score += run
            run = 1
        else:
            if tone == -1 and ln <= 3:         # a short blank between tones keeps the run
                continue
            if run >= 3:
                score += run
            run = 0
        if g:
            prev_end, prev_tone = st + ln, tone
    if run >= 3:
        score += run
    return score


SCORES = {"wwv": wwv_score, "dtmf": dtmf_score, "hamdrm": hamdrm_score,
          "stanag4539": stanag4539_score, "ale3g": ale3g_score,
          "selcall_ccir": selcall_score}


def passes(label: str, x: np.ndarray) -> bool:
    return SCORES[label](x) >= THRESH[label]


UNKNOWN = "unknown"


def reweight(label, probs, classes, x):
    """If `label` is checked and its signature is absent, report "unknown" rather than a second
    guess (user's choice, 2026-11-24: a blocked weak window more often got another wrong label
    than the right one, docs/batch11_results.md section 4). Unchecked labels pass unchanged.
    Returns (label, conf, probs, note); conf stays the model's probability for its top label."""
    conf = float(probs[classes.index(label)])
    if label not in CHECKED or passes(label, x):
        return label, conf, probs, None
    return UNKNOWN, conf, probs, f"{label} signature absent"


def _load_thresholds():
    import json
    import os
    f = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "signature_thresholds.json")
    if os.path.exists(f):
        THRESH.update(json.load(open(f)))


_load_thresholds()
