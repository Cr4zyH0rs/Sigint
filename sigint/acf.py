"""Second-opinion check for wide military HF modems: autocorrelation period and OFDM symbol rate.

sigidwiki lists an autocorrelation (ACF) period for many military modems, which is the
standard way analysts tell look-alike PSK modems apart:
  STANAG 4285              ACF 106.66 ms   https://www.sigidwiki.com/wiki/STANAG_4285
  MIL-STD-188-110 serial   ACF header 200 ms, body 66.66 ms
                                           https://www.sigidwiki.com/wiki/MIL-STD-188-110_Serial
  MIL-STD-188-110 App B    44.44 Bd OFDM (39 tones, 56.25 Hz)
                                           https://www.sigidwiki.com/wiki/MIL-STD-188-110_Appendix_B_39-Tone
For OFDM with a cyclic guard, x(t)*x(t + 1/spacing) repeats at the symbol rate, which gives a
spectral line at 44.44 Hz for the 39-tone modem (and STANAG 4197).

This only measures periodicities of the received waveform; it does not demodulate anything.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfiltfilt, welch

FS = 12000
_SOS = butter(6, 1500, fs=FS, output="sos")


def acf_profile(x, fc=1800.0, lo_ms=40.0, hi_ms=260.0):
    """Normalised |ACF| of the complex baseband around fc, for lags lo..hi ms (1 sample steps)."""
    t = np.arange(len(x)) / FS
    bb = x * np.exp(-2j * np.pi * fc * t)
    bb = sosfiltfilt(_SOS, bb.real) + 1j * sosfiltfilt(_SOS, bb.imag)
    n = len(bb)
    F = np.fft.fft(bb, 2 * n)
    r = np.abs(np.fft.ifft(F * np.conj(F)))[:n]
    r = r / r[0]
    lo, hi = int(lo_ms * FS / 1000), int(hi_ms * FS / 1000)
    return np.arange(lo, hi) / FS * 1000, r[lo:hi]


def _at(lags, r, ms, tol=1.0):
    m = np.abs(lags - ms) <= tol
    return float(r[m].max())


def cp_line(x, spacing_hz, rate_hz):
    """Strength (dB above the median of 20-80 Hz) of the symbol-rate line in x(t)x(t+1/spacing)."""
    d = int(round(FS / spacing_hz))
    pr = x[:-d] * x[d:]
    pr = np.convolve(pr, np.ones(40) / 40, mode="same")
    f, p = welch(pr - pr.mean(), fs=FS, nperseg=FS * 4)
    b = (f > 20) & (f < 80)
    k = np.abs(f - rate_hz) <= 0.5
    return float(10 * np.log10(p[k].max() / np.median(p[b])))


def features(x, fc=1800.0):
    lags, r = acf_profile(x, fc)
    floor = float(np.median(r))
    return dict(
        floor=floor,
        s4285=_at(lags, r, 106.67) - floor,
        m110=max(_at(lags, r, 66.67), _at(lags, r, 133.33), _at(lags, r, 200.0)) - floor,
        cp39=cp_line(x, 56.25, 44.444),
    )


WIDE_MIL = ("stanag4285", "mil110_serial", "mil110_16tone", "mil110_39tone", "pactor3")


def decide(f, th_acf=0.02, th_cp=5.0):
    """Label implied by the periodicities, or None if nothing clear. Thresholds were tuned on
    windows generated with different seeds from the test windows (stress/tune_acf.py; 60 per
    class: 46/60 STANAG 4285 and 46/60 110-serial named, 32/60 39-tone, 0 wrong among them,
    0 false calls on 16-tone and PACTOR III, 2/60 on SSB)."""
    if f["s4285"] > th_acf and f["s4285"] > f["m110"] * 1.5:
        return "stanag4285"
    if f["m110"] > th_acf and f["m110"] > f["s4285"] * 1.5:
        return "mil110_serial"
    if f["cp39"] > th_cp:
        return "mil110_39tone"
    return None


def reweight(label, probs, classes, x, fc=None, boost=0.9):
    """If the classifier's top label is a wide military mode and the periodicity check names
    a different (or the same) one, move `boost` of the group's probability onto it.
    Returns (label, confidence, probs, check_label)."""
    p = np.asarray(probs, float).copy()
    if label not in WIDE_MIL:
        return label, float(p.max()), p, None
    chk = decide(features(x, fc if fc else 1800.0))
    if chk is None or chk not in classes:
        return label, float(p.max()), p, None
    idx = [classes.index(c) for c in WIDE_MIL if c in classes]
    mass = p[idx].sum()
    p[idx] *= (1 - boost)
    p[classes.index(chk)] += boost * mass
    i = int(p.argmax())
    return classes[i], float(p[i]), p, chk
