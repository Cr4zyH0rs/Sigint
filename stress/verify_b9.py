"""Batch 9 checks on clean generator audio against the published specs (see sigint/synth_b9.py)."""
import json, os, sys
import numpy as np
from scipy.signal import hilbert
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sigint import synth_b9 as b9
from sigint.synth import FS

def bursts(x, thr=0.3, smooth=12):
    a = np.convolve(np.abs(hilbert(x)), np.ones(smooth) / smooth, "same")
    on = np.concatenate([[0], (a > thr * a.max()).astype(int), [0]])
    e = np.flatnonzero(np.diff(on)); s = e[::2]; t = e[1::2]
    return [(int(p), int(q)) for p, q in zip(s, t)]

def freq(seg):
    F = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), 1 << 17)); return float(np.fft.rfftfreq(1 << 17, 1 / FS)[np.argmax(F)])

def inst_freq(x):
    ph = np.unwrap(np.angle(hilbert(x))); return np.diff(ph) * FS / (2 * np.pi)

out = {}
rng = np.random.default_rng(9)
# WWV: one minute with no tone minute (0) so ticks stand alone
for st in ("WWV", "WWVH"):
    x = b9._wwv_minute(rng, st, 0, False)
    b = bursts(x[:44 * FS + FS // 2])            # before either station's voice
    marker = b[0]; ticks = b[1:]
    out[st] = dict(marker_ms=round((marker[1] - marker[0]) / FS * 1000), marker_hz=round(freq(x[marker[0]:marker[1]])),
                   n_ticks_s1_44=len(ticks), tick_ms=round(float(np.median([(q - p) / FS * 1000 for p, q in ticks])), 1),
                   tick_hz=round(freq(x[ticks[0][0]:ticks[0][0] + int(0.005 * FS)])),
                   tick_starts_s=[round(p / FS, 3) for p, _ in ticks[:3]],
                   silent_second_29=not any(abs(p / FS - 29) < 0.1 for p, _ in ticks),
                   expected="marker 800 ms (WWV 1000 / WWVH 1200 Hz); 5 ms ticks each second except 29 and 59")
x = b9._wwv_minute(rng, "WWV", 4, False)
out["WWV_minute4_tone_hz"] = round(freq(x[2 * FS + 200: 2 * FS + 4000]))
# RWM
for part in ("1pps", "10pps"):
    for s in range(20):
        x, m = b9.gen_rwm(np.random.default_rng(s), 300.0)
        if m["submode"] == part: break
    b = bursts(x)
    w = sorted({round((q - p) / FS * 1000) for p, q in b})
    gaps = np.diff([p for p, _ in b]) / FS
    out["rwm_" + part] = dict(pulse_ms=w, median_period_s=round(float(np.median(gaps)), 3),
                              expected="1 pps: 100 ms, minute 500 ms; 10 pps: 20 ms, second 40 ms, minute 500 ms")
# ARQ-E / CIS: shift from inst-freq histogram, shortest element from run lengths
for name, gen in (("arqe", b9.gen_arqe), ("cis_fsk", b9.gen_cis_fsk)):
    rows = []
    for s in range(4):
        x, m = gen(np.random.default_rng(s), 300.0)
        f = inst_freq(x)[1000:-1000]; f = np.convolve(f, np.ones(9) / 9, "same")
        hi = f > m["centre"]; shift = np.median(f[hi]) - np.median(f[~hi])
        runs = np.diff(np.flatnonzero(np.diff(hi.astype(int))))
        c = np.bincount(runs[runs > 20]); top = sorted(np.argsort(c)[-2:])   # CIS: 50 Bd dots + data bit
        rows.append(dict(set=m["submode"], shift_hz=round(float(shift)), common_runs_ms=[round(v / FS * 1000, 1) for v in top]))
    out[name] = rows
# XPA / XPA2 / Mazielka: tone grid and symbol length
def grid(f_list, d_list):
    return sorted({round(v, 3) for v, d in zip(f_list, d_list) if v > 0})
f, d = b9._xpa_freqs(np.random.default_rng(1))
out["xpa"] = dict(tones_hz=grid(f, d), n_tones=len(grid(f, d)), symbol_ms=100,
                  expected="17 tones: 520,600,680,720,760-1120 (40 Hz),1160,1200,1280; 10 Bd")
f, d = b9._xpa2_freqs(np.random.default_rng(2))
g = grid(f, d)
out["xpa2"] = dict(tones_hz=g, n_tones=len(g), spacing_hz=float(np.min(np.diff(g))), symbol_ms=1000 / 7.8125,
                   expected="16 tones 15.625 Hz apart from 1000 Hz, 7.8125 Bd")
x, m = b9.gen_mazielka(np.random.default_rng(3), 300.0)
b = bursts(x, smooth=60)[1:]                     # skip a call cut by the window start
out["mazielka"] = dict(call_s=round((b[0][1] - b[0][0]) / FS, 2), pause_s=round((b[1][0] - b[0][1]) / FS, 2),
                       tones_hz=sorted(round(freq(x[b[0][0] + int(i / 3 * FS) + 200: b[0][0] + int((i + 1) / 3 * FS) - 200])) for i in range(6)),
                       dial_offset_hz=round(m["centre"] - 902.5, 1),
                       expected="6 tones 815-990 Hz (+-5 Hz, plus dial offset), 333 ms each (2.0 s), ~1.32 s pause")
json.dump(out, open("results/verify_b9_seed9.json", "w"), indent=1)
print(json.dumps(out, indent=1))
