"""Batch 11 checks on clean audio against the published parameters (sources in sigint/synth_b11.py)."""
import json, os, sys
import numpy as np
from scipy.signal import welch
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sigint import synth_b11 as b
from sigint.acf import acf_profile
from sigint.synth import FS
from sigint.synth_b5 import PSK8

def obw99(x):
    f, p = welch(x, FS, nperseg=4096); c = np.cumsum(p) / p.sum()
    return round(float(f[np.searchsorted(c, .995)] - f[np.searchsorted(c, .005)]))

def baud_line(x, baud):
    """dB by which the squared envelope's spectral line at the expected baud stands above the
    median of 300-3000 Hz (a symbol-rate check; low roll-off makes the line weak)."""
    from scipy.signal import hilbert
    e = np.abs(hilbert(x)) ** 2
    f, p = welch(e - e.mean(), FS, nperseg=FS)
    m = (f > 300) & (f < 3000)
    k = np.abs(f - baud) <= 1
    return round(float(10 * np.log10(p[k].max() / np.median(p[m]))), 1)

def acf_peak(x, lo, hi):
    lags, r = acf_profile(x, 1800.0, lo, hi)
    return round(float(lags[np.argmax(r)]), 2)

rng = np.random.default_rng(11)
out = {}
for rate, mod in b.S4539_RATES.items():
    c = b.CONST[mod]
    body = np.concatenate([np.concatenate([c[rng.integers(0, len(c), 256)], b._4539_PROBE]) for _ in range(60)])
    x = b.serial(body, 2400, 1800.0, 0.15)
    out[f"stanag4539_{rate}"] = dict(constellation_points=len(c), obw99_hz=obw99(x), baud_line_db_at_2400=baud_line(x, 2400),
                                     acf_peak_ms=acf_peak(x, 80, 160), published="2400 Bd, 3000 Hz, ACF 119.6 ms")
if True:
    x, _ = b.gen_stanag4529(np.random.default_rng(3), 60)
    out[f"stanag4529"] = dict(obw99_hz=obw99(x), baud_line_db_at_1200=baud_line(x, 1200), acf_peak_ms=acf_peak(x, 150, 260),
                              published="1200 Bd, 1240-1300 Hz, ACF 213.32 ms")
r = np.random.default_rng(5)
lens = {}
for bw, n in (("BW0", None), ("BW1", None), ("BW2", 3), ("BW3", 64), ("BW4", None), ("BW5", None)):
    s = b.ale3g_burst(r, bw, n)
    lens[bw + (f" n={n}" if n else "")] = round(len(s) / 2400 * 1000, 2)
x3 = b.serial(np.concatenate([b.ale3g_burst(r, "BW3", 512)]), 2400, 1800.0, 0.15)
lags, rr = acf_profile(x3, 1800.0, 5, 30)
out["ale3g"] = dict(burst_ms=lens, published_ms="BW0 613.333, BW1 1306.67, BW2 640+3*400=1840, BW3 373.33+64*13.33=1226.4, BW4 640, BW5 1013.33",
                    bw3_acf_peak_ms=round(float(lags[np.argmax(rr)]), 2), published_acf="13.3 ms",
                    obw99_hz=obw99(x3), baud_line_db_at_2400=baud_line(x3, 2400))
x, _ = b.gen_link11_slew(np.random.default_rng(4), 60)
e = np.abs(x) > 1e-9
out["link11_slew"] = dict(obw99_hz=obw99(x), baud_line_db_at_2400=baud_line(x, 2400), published="8PSK 2400 Bd 3000 Hz, bursts 0.1-2.0 s, pause >= 4 ms")
for baud in (75, 100, 150, 300, 600):
    xf = b.fsk(np.random.default_rng(baud).integers(0, 2, 16 * baud), baud, 1700 - 425, 1700 + 425)
    from scipy.signal import hilbert
    inst = np.diff(np.unwrap(np.angle(hilbert(xf)))) * FS / 2 / np.pi   # instantaneous frequency
    lo, hi = np.median(inst[inst < 1700]), np.median(inst[inst > 1700])
    sps = FS // baud
    out[f"stanag4481_{baud}"] = dict(shift_hz=round(float(hi - lo)), bit_ms=round(sps / FS * 1000, 2),
                                     published=f"850 Hz shift, {baud} Bd ({1000/baud:.2f} ms)")
os.makedirs("results", exist_ok=True)
json.dump(out, open("results/verify_b11_seed11.json", "w"), indent=1)
print(json.dumps(out, indent=1))
