"""Batch 10 checks on clean audio against the published specs."""
import glob, json, os, sys
import numpy as np, soundfile as sf
from scipy.signal import welch
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sigint import synth_b10 as b10
from sigint.synth import FS

def obw99(x, fs=FS):
    f, p = welch(x, fs, nperseg=4096); c = np.cumsum(p) / p.sum()
    return round(float(f[np.searchsorted(c, .995)] - f[np.searchsorted(c, .005)]))

out = {}
# fldigi takes vs the fldigi mode table (https://www.w1hkj.org/FldigiHelp/mode_table_page.html)
table = {"IFKP": 386, "PSK125R": 125, "PSK250R": 250, "PSK500R": 500, "PSK1000R": 1800,
         "PSK63RC10": 850, "PSK125RC4": 650, "PSK250RC3": 950, "PSK500RC2": 1400, "OFDM500F": None, "OFDM750F": None}
for name, ref in table.items():
    fs_ = sorted(glob.glob(f"data/fldigi_tx/*/*__{name}__*.wav"))
    if not fs_:
        continue
    x, fs = sf.read(fs_[0])
    out["fldigi_" + name] = dict(obw99_hz=obw99(x, fs), table_bw_hz=ref, takes=len(fs_))
# codec2 DATAC (README_data.md: RF bandwidth, burst s)
readme = {"DATAC0": (500, 0.44), "DATAC1": (1700, 4.18), "DATAC3": (500, 3.19), "DATAC4": (250, 5.17), "DATAC13": (200, 2.0)}
for m, (bw, dur) in readme.items():
    x = b10.datac_burst(m, 1, 3)
    out[m] = dict(obw99_hz=obw99(x), burst_s_with_pre_postamble=round(len(x) / FS, 2), readme_bw_hz=bw, readme_burst_s=dur)
# HamDRM: carrier spacing and occupied band, symbol period from the cyclic-prefix autocorrelation
for mode in ("A", "B"):
    for wide in (False, True):
        x, qam, bw = b10.hamdrm_signal(np.random.default_rng(5), mode, wide, 20, 1500.0, with_lead=False)
        nu, ng = b10.HAMDRM[mode][:2]
        # CP correlation: x[n] vs x[n+nu] peaks at lag Tu
        lags = np.arange(nu - 40, nu + 41)
        r = [np.mean(x[:-l] * x[l:]) for l in lags]
        out[f"hamdrm_{mode}_{'2.5' if wide else '2.3'}"] = dict(
            carriers=(b10.HAMDRM[mode][3] if wide else b10.HAMDRM[mode][2]), spacing_hz=round(FS / nu, 3),
            occupied_hz=round(bw), obw99_hz=obw99(x), cp_corr_peak_ms=round(lags[int(np.argmax(r))] / FS * 1000, 2),
            symbol_ms=round((nu + ng) / FS * 1000, 2), expected="ETSI ES 201 980 table 2: Tu A 24 / B 21.33 ms, Ts 26.67 ms; handbook: 2.3/2.5 kHz")
json.dump(out, open("results/verify_b10_seed10.json", "w"), indent=1)
for k, v in out.items(): print(k, v)
