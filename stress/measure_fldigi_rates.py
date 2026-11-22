"""Symbol-rate line and occupied bandwidth (20 dB) of each fldigi test take.
Usage: python stress/measure_fldigi_rates.py -> results/fldigi_rates.json"""
import glob, json, numpy as np, soundfile as sf
from scipy.signal import hilbert, welch
out = {}
for cls in ("olivia", "contestia", "mfsk", "thor"):
    for f in sorted(glob.glob(f"data/fldigi_tx/test/{cls}__*.wav")):
        x, _ = sf.read(f); x = x[12000:12000 * 30]
        fc = float(f.split("__")[-1][:-4])
        fr, p = welch(x, fs=12000, nperseg=24000); b = (fr > fc - 600) & (fr < fc + 600)
        pd = 10 * np.log10(p[b]); occ = fr[b][pd > pd.max() - 20]
        fi = np.diff(np.unwrap(np.angle(hilbert(x)))) * 12000 / (2 * np.pi)
        fi = np.convolve(fi, np.ones(24) / 24, "same"); tr = np.abs(np.diff(fi))
        ff, pp = welch(tr - tr.mean(), fs=12000, nperseg=24000); s = (ff > 5) & (ff < 200)
        out[f.split("/")[-1]] = dict(strongest_rate_lines_hz=sorted(ff[s][np.argsort(pp[s])[-3:]].round(2).tolist()),
                                     occupied_bw_20db_hz=round(float(occ.max() - occ.min())))
json.dump(out, open("results/fldigi_rates.json", "w"), indent=1)
print(json.dumps(out, indent=1))
