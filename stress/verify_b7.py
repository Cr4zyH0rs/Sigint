"""Measure batch 7 audio against the published parameters (sigint/synth_b7.py docstring).
Clean (noise-free) waveforms. Usage: python stress/verify_b7.py SEED -> results/verify_b7_seed{SEED}.json"""
import json, os, sys
import numpy as np
from scipy.signal import welch, hilbert, find_peaks
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sigint import synth_b7 as b7
from sigint.synth import FS
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify_b5 import obw99, acf_peak_ms


def span(x):
    nz = np.flatnonzero(np.abs(x) > 1e-9)
    return x[nz[0]:nz[-1] + 1]


def inst_freq(x):
    return np.diff(np.unwrap(np.angle(hilbert(x)))) * FS / (2 * np.pi)


def two_peaks(fi, lo, hi, mid):
    e = np.arange(lo, hi, 5); h, _ = np.histogram(fi, e); c = e[:-1] + 2.5
    return [float(c[c < mid][np.argmax(h[c < mid])]), float(c[c > mid][np.argmax(h[c > mid])])]


def main(seed):
    rng = np.random.default_rng(seed)
    out = {}
    # SELCAL: tone frequencies and segment timing (clean, no mistuning check: off is random)
    x, m = b7.gen_selcal(rng, 300.0)
    env = np.convolve(np.abs(x), np.ones(240) / 240, "same") > 0.2
    ed = np.flatnonzero(np.diff(env.astype(int)))
    segs = [round((b - a) / FS, 3) for a, b in zip(ed[::2], ed[1::2])]
    gaps = [round((a - b) / FS, 3) for b, a in zip(ed[1::2], ed[2::2])]
    a = ed[0]
    f, p = welch(x[a:a + FS], fs=FS, nperseg=FS)
    pk, _ = find_peaks(10 * np.log10(p + 1e-20), prominence=20)
    out["selcal"] = dict(code=m["code"], segments_s=segs[:4], gaps_s=gaps[:3], first_pair_hz=f[pk][np.argsort(p[pk])[-2:]].tolist(),
                         expected="1 s tone pair, 0.2 s gap, 1 s tone pair; tones per SELCAL table (+-50 Hz mistuning)")
    # DSC: shift and bit rate; dot pattern -> 50 Hz line in the FSK frequency track
    x, m = b7.gen_dsc(np.random.default_rng(seed), 300.0)
    xs = span(x)
    fi = inst_freq(xs); fc = m["centre"]
    pkz = two_peaks(fi, fc - 200, fc + 200, fc)
    out["dsc"] = dict(tones_hz=pkz, shift_hz=pkz[1] - pkz[0], obw99_hz=round(obw99(xs)),
                      expected="170 Hz shift, 100 Bd, 350-500 Hz")
    x, m = b7.gen_ccir493(np.random.default_rng(seed + 1), 300.0)
    xs = span(x)
    fi = np.convolve(inst_freq(xs), np.ones(60) / 60, "same")
    steady = np.abs(np.diff(fi)) < 0.5
    run = np.max(np.diff(np.flatnonzero(np.r_[True, ~steady, True]))) / FS
    out["ccir493"] = dict(longest_steady_tone_s=round(float(run), 2), meta=m,
                          shift_hz=float(np.subtract(*two_peaks(inst_freq(xs), m["centre"] - 200, m["centre"] + 200, m["centre"])[::-1])),
                          expected="long CW tone preamble, 170 Hz shift, 100 Bd")
    # HFDL: carrier 1440 Hz and 1800 Bd symbol-rate line in |x|^2 envelope
    x = b7._hfdl_burst(np.random.default_rng(seed), 4.3, 4)
    e2 = np.abs(hilbert(x)) ** 2
    f, p = welch(e2 - e2.mean(), fs=FS, nperseg=FS)
    b = (f > 1000) & (f < 3000)
    f2, p2 = welch(x, fs=FS, nperseg=FS)
    cen = float(np.sum(f2 * p2) / np.sum(p2))
    out["hfdl"] = dict(symbol_rate_line_hz=float(f[b][np.argmax(p[b])]), centre_hz=round(cen, 1),
                       obw99_hz=round(obw99(x)), expected="1440 Hz sub-carrier, 1800 Bd, 2400 Hz")
    # MSK144: tones from instantaneous frequency, packet period from envelope-free ACF of FM track
    from sigint.synth_wsjt import _sim_wav
    y = _sim_wav(["msk144sim", "K1ABC W9XYZ EN37", "15", "1500", "2.5", "30", "1"], rng)
    on = np.flatnonzero(np.abs(y) > 0.2 * np.abs(y).max())
    y = y[on[0]:on[-1]]
    fi = inst_freq(y)
    tones = two_peaks(fi, 700, 2300, 1500)
    lag = acf_peak_ms(y, 1500.0, 40, 150)
    out["msk144"] = dict(tones_hz=tones, packet_period_ms=lag, obw99_hz=round(obw99(y)),
                         expected="tones 1000/2000 Hz, 2000 bps, ACF 72 ms, 2.5 kHz")
    os.makedirs("results", exist_ok=True)
    json.dump(out, open(f"results/verify_b7_seed{seed}.json", "w"), indent=1, default=float)
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main(int(sys.argv[1]))
