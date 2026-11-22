"""Measure batch 5 audio against the published parameters (no decoder exists here).

Clean (noise-free) waveforms are measured with numpy/scipy and compared with the values on
sigidwiki and the ARRL PACTOR pages cited in sigint/synth_b5.py.
Usage: python stress/verify_b5.py N SEED -> results/verify_b5_seed{SEED}.json
"""
import json, os, sys
import numpy as np
from scipy.signal import welch, find_peaks, butter, sosfiltfilt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sigint import synth_b5 as b5
from sigint.synth import FS


def obw99(x):
    """ITU-style occupied bandwidth: 0.5% of power below, 0.5% above."""
    f, p = welch(x, fs=FS, nperseg=8192)
    c = np.cumsum(p) / p.sum()
    return float(f[np.searchsorted(c, 0.995)] - f[np.searchsorted(c, 0.005)])


def acf_peak_ms(x, fc, lo_ms=40, hi_ms=260):
    """Strongest normalised autocorrelation peak of the complex baseband (sigidwiki 'ACF')."""
    t = np.arange(len(x)) / FS
    bb = x * np.exp(-2j * np.pi * fc * t)
    sos = butter(6, 1500, fs=FS, output="sos")
    bb = sosfiltfilt(sos, bb.real) + 1j * sosfiltfilt(sos, bb.imag)
    n = len(bb)
    F = np.fft.fft(bb, 2 * n)
    r = np.abs(np.fft.ifft(F * np.conj(F)))[:n]
    r /= r[0]
    lo, hi = int(lo_ms * FS / 1000), int(hi_ms * FS / 1000)
    k = lo + int(np.argmax(r[lo:hi]))
    return round(k / FS * 1000, 2), round(float(r[k]), 3)


def tone_grid(x, lo=300, hi=3000, prom_db=6):
    f, p = welch(x, fs=FS, nperseg=FS)          # 1 Hz bins
    b = (f > lo) & (f < hi)
    f, pdb = f[b], 10 * np.log10(p[b] + 1e-20)
    pk, _ = find_peaks(pdb, prominence=prom_db, distance=30)
    return f[pk]


def _count_carriers(x):
    """Power on each of the 18 grid positions (+-20 Hz); a carrier is present if within 10 dB of the max."""
    f, p = welch(x, fs=FS, nperseg=FS)
    pw = np.array([p[np.abs(f - (1500 + (k - 8.5) * 120)) <= 20].sum() for k in range(18)])
    return int(np.sum(pw > pw.max() / 10))


def cp_symbol_rate(x, t_core):
    """Cyclic-prefix test: x(t) x(t + T_core) is periodic at the OFDM symbol rate."""
    d = int(round(t_core * FS))
    pr = x[:-d] * x[d:]
    pr = np.convolve(pr, np.ones(40) / 40, mode="same")
    f, p = welch(pr - pr.mean(), fs=FS, nperseg=FS * 4)
    b = (f > 20) & (f < 80)
    return round(float(f[b][np.argmax(p[b])]), 2)


def env_period(x, lo_s, hi_s):
    env = np.convolve(np.abs(x), np.ones(240) / 240, mode="same")
    e = env - env.mean()
    r = np.correlate(e, e, "full")[len(e) - 1:]
    lo, hi = int(lo_s * FS), int(hi_s * FS)
    return round((lo + int(np.argmax(r[lo:hi]))) / FS, 3)


def burst_lengths(x):
    env = np.convolve(np.abs(x), np.ones(600) / 600, mode="same") > 0.05 * np.abs(x).max()  # 50 ms: spans DPSK symbol nulls
    e = np.flatnonzero(np.diff(np.r_[0, env.astype(int), 0]))
    return [round((b - a) / FS, 3) for a, b in zip(e[::2], e[1::2])]


def main(n, seed):
    rng = np.random.default_rng(seed)
    out = {}
    # serial PSK
    acfs = [acf_peak_ms(b5.serial_psk(b5.stanag4285_symbols(rng, 60), 1800), 1800) for _ in range(5)]
    x = b5.serial_psk(b5.stanag4285_symbols(rng, 60), 1800)
    out["stanag4285"] = dict(acf_ms=acfs, acf_expected_ms=106.66, obw99_hz=round(obw99(x)),
                             bw_expected_hz=2750)
    lo = [acf_peak_ms(b5.serial_psk(b5.mil110_symbols(rng, 2400 * 6, 0, False), 1800), 1800) for _ in range(3)]
    hi = [acf_peak_ms(b5.serial_psk(b5.mil110_symbols(rng, 2400 * 6, 0, True), 1800), 1800) for _ in range(3)]
    pre = acf_peak_ms(b5.serial_psk(b5.PSK8[np.tile(b5._M110_PRE, 24)], 1800), 1800, 100, 300)
    out["mil110_serial"] = dict(acf_ms_body_20_20=lo, acf_ms_body_32_16=hi, acf_ms_preamble=pre,
                                expected="header 200 ms, body 66.66 ms",
                                obw99_hz=round(obw99(b5.serial_psk(b5.mil110_symbols(rng, 24000, 0, True), 1800))))
    # parallel tone
    x = b5.multitone_dpsk(rng, b5.TONES_16, 1 / 75, 75 * 20, pilot=605.0)
    g = tone_grid(x)
    out["mil110_16tone"] = dict(n_peaks=len(g), first=float(g[0]), last=float(g[-1]),
                                spacing=float(np.median(np.diff(g[1:]))),
                                expected="605 Hz pilot + 16 tones 935-2585 Hz / 110 Hz",
                                symbol_period_s=env_period(x ** 2, 0.008, 0.02),
                                obw99_hz=round(obw99(x)))
    x = b5.multitone_dpsk(rng, b5.TONES_39, 1 / 44.444, 44 * 20, pilot=393.75, pilot_gain=2.0, edge=0.05)
    g = tone_grid(x, prom_db=3)
    out["mil110_39tone"] = dict(n_peaks=len(g), first=float(g[0]), last=float(g[-1]),
                                spacing=float(np.median(np.diff(g[1:]))),
                                expected="393.75 Hz pilot + 39 tones 675-2812.5 Hz / 56.25 Hz, 44.44 Bd",
                                symbol_rate_hz=cp_symbol_rate(x, 1 / 56.25),
                                obw99_hz=round(obw99(x)))
    # PACTOR
    pr = {}
    for name, gen, cyc in (("pactor1", b5.gen_pactor1, (1.0, 1.6)), ("pactor2", b5.gen_pactor2, (1.0, 4.5)),
                           ("pactor3", b5.gen_pactor3, (3.0, 4.5))):
        rows = []
        for i in range(n):
            r = np.random.default_rng(seed * 1000 + i)
            x, meta = gen(r, 200.0)
            x = x - np.mean(x)
            bl = burst_lengths(x)
            mid = [b for b in bl[1:-1]]        # drop bursts cut by the window edges
            rows.append(dict(sub=meta["submode"], cycle_s=env_period(x, *cyc),
                             bursts_s=sorted(set(mid))[:4]))
        pr[name] = rows
    tone_checks = {}
    r = np.random.default_rng(seed)
    tone_checks["pactor1"] = np.diff(tone_grid(b5.fsk(r.integers(0, 2, 2000), 200, 1400, 1600), prom_db=10)).tolist()
    tone_checks["pactor2"] = np.diff(tone_grid(b5.dpsk_tones(r, 2000, 100, [1400, 1600], 2), prom_db=3)).tolist()
    # PACTOR III: per-level 99% bandwidth, and level-6 -40 dB edges (ARRL: 2.4 kHz, 300-2700 Hz)
    lv = {}
    for L, ks in b5.P3_LEVELS.items():
        x = b5.dpsk_tones(r, 1000, 100, [1500 + (k - 8.5) * 120 for k in ks], 2 if L <= 3 else 4)
        lv[L] = round(obw99(x))
        if L == 6:
            f, p = welch(x, fs=FS, nperseg=4096)
            pdb = 10 * np.log10(p / p.max() + 1e-20)
            above = f[(pdb > -40) & (f > 100)]
            edges40 = (float(above.min()), float(above.max()))
    tone_checks["pactor3_obw99_by_level"] = lv
    tone_checks["pactor3_level6_minus40db_hz"] = edges40
    x = b5.dpsk_tones(r, 2000, 100, [1400, 1600], 2)
    tone_checks["pactor2_obw99_hz"] = round(obw99(x))
    out["pactor"] = dict(tone_checks=tone_checks,
                         summary={k: dict(cycles=sorted({row["cycle_s"] for row in v}),
                                          bursts=sorted({b for row in v for b in row["bursts_s"]}))
                                  for k, v in pr.items()})
    os.makedirs("results", exist_ok=True)
    json.dump(out, open(f"results/verify_b5_seed{seed}.json", "w"), indent=1, default=float)
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
