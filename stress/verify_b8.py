"""Batch 8 checks on clean generator audio against the published specs (see sigint/synth_b8.py)."""
import json, os, sys
import numpy as np
from scipy.signal import welch, find_peaks
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sigint import synth_b8 as b8
from sigint.synth import FS

def obw99(x, fs=FS):
    f, p = welch(x, fs, nperseg=8192); c = np.cumsum(p) / p.sum()
    return float(f[np.searchsorted(c, 0.995)] - f[np.searchsorted(c, 0.005)]), f, p

def carriers(f, p, lo, hi, min_hz):
    m = (f > lo) & (f < hi); db = 10 * np.log10(p[m] + 1e-30)
    k, _ = find_peaks(db, distance=max(1, int(min_hz / (f[1] - f[0]))), prominence=3)
    return f[m][k]

out = {}
for mode, exp in [("1600", "14 DQPSK carriers 75 Hz apart + centre pilot, 1.125-1.3 kHz"),
                  ("700C", "14 carriers, 1.5 kHz"), ("700D", "17 carriers, 1.0 kHz"), ("700E", "21 carriers, 1.5 kHz")]:
    x = b8.freedv_audio(mode, 60, 7)
    bw, f, p = obw99(x)
    out["freedv" + mode] = dict(obw99_hz=round(bw), centroid_hz=round(float((f * p).sum() / p.sum())), expected=exp)
# FDMDV pilot: strongest line
x = b8.freedv_audio("1600", 60, 7); f, p = welch(x, FS, nperseg=8192)
out["freedv1600"]["strongest_line_hz"] = round(float(f[np.argmax(p)]), 1)

rng = np.random.default_rng(8)
for q in (False, True):
    x = b8.rpr_packet(rng, 20, q, 1500.0)
    bw, f, p = obw99(x)
    # DBPSK: x^2 removes the 0/pi phase steps -> a line at 2 f_k per carrier; DQPSK: x^4 -> 4 f_k
    pw = 4 if q else 2
    f2, p2 = welch(x ** pw, FS, nperseg=1 << 14)
    pk = carriers(f2, p2, pw * 1250, pw * 1750, pw * 40) / pw
    r = dict(obw99_hz=round(bw), expected="8 carriers, 60 Hz, centre 1500 Hz, 500 Hz")
    if not q:   # the x^4 lines for DQPSK are buried in cross-products; same carrier grid code
        r.update(carriers_hz=[round(v) for v in pk], spacing_hz=round(float(np.median(np.diff(pk))), 1))
    out["rpr_" + ("qpsk" if q else "bpsk")] = r
out["rpr_preamble_ms"] = 8 / b8.RPR_BAUD * 1000

# DTMF: detect pairs with a Goertzel-like FFT on each tone burst
x, meta = b8.gen_dtmf(np.random.default_rng(3), 200.0)
from scipy.signal import hilbert
a = np.convolve(np.abs(hilbert(x)), np.ones(30) / 30, "same")
env = a > 0.3 * a.max()
edges = np.flatnonzero(np.diff(env.astype(int)))
pairs, durs = [], []
for a, b in zip(edges[::2], edges[1::2]):
    seg = x[a:b]; F = np.abs(np.fft.rfft(seg, 1 << 15)); fr = np.fft.rfftfreq(1 << 15, 1 / FS)
    r = max(b8.DTMF_ROWS, key=lambda h: F[np.argmin(abs(fr - h))]); c = max(b8.DTMF_COLS, key=lambda h: F[np.argmin(abs(fr - h))])
    pk = fr[np.argsort(F)[-1]]
    pairs.append((r, c)); durs.append(round((b - a) / FS * 1000))
out["dtmf"] = dict(profile=meta["submode"], n_digits=len(pairs), pairs=pairs[:6], tone_ms=durs[:6],
                   expected="row 697/770/852/941 + column 1209/1336/1477/1633 Hz; timing per profile")
os.makedirs("results", exist_ok=True)
json.dump(out, open("results/verify_b8_seed8.json", "w"), indent=1)
print(json.dumps(out, indent=1))
