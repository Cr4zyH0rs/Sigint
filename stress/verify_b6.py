"""Measure batch 6 audio against the published parameters (sigint/synth_b6.py docstring).
Clean (noise-free) waveforms; also frequency/bandwidth estimates at 0..15 dB.
Usage: python stress/verify_b6.py N SEED -> results/verify_b6_seed{SEED}.json"""
import json, os, sys
import numpy as np
from scipy.signal import welch
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sigint import synth_b6 as b6, synth, features
from sigint.synth import FS
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify_b5 import obw99, acf_peak_ms, tone_grid, burst_lengths, env_period


def main(n, seed):
    rng = np.random.default_rng(seed)
    out = {}
    # FSQ: tone grid spacing and count, symbol rate from instantaneous-frequency changes
    tones = b6.fsq_tones(rng, 600)
    x = b6.mfsk_phase_coherent(tones, b6.FSQ_BAUDS["6"], 1000.0, b6.FSQ_SPACING)
    f, p = welch(x, fs=FS, nperseg=FS * 4)
    b = (f > 900) & (f < 1400)
    pk = f[b][p[b] > p[b].max() / 20]
    out["fsq"] = dict(ifk_repeats=int(np.sum(np.diff(tones) == 0)), tones_used=len(set(tones.tolist())),
                      grid_hz=round(float(np.median(np.diff(np.unique(np.round(pk / b6.FSQ_SPACING))))) * b6.FSQ_SPACING, 4),
                      obw99_hz=round(obw99(x)), expected="33 tones, 8.79 Hz, no repeated tones, 300 Hz",
                      bauds=b6.FSQ_BAUDS)
    # packet: shift from tone grid, bit rate from envelope of FM discriminator
    xb = b6.fsk(b6.hdlc_bits(rng, 200, 30), 300, 1400, 1600)
    from scipy.signal import hilbert
    fi = np.diff(np.unwrap(np.angle(hilbert(xb)))) * FS / (2 * np.pi)
    h, e = np.histogram(fi, bins=np.arange(1200, 1800, 10))
    c = e[:-1] + 5
    two = [c[c < 1500][np.argmax(h[c < 1500])], c[c > 1500][np.argmax(h[c > 1500])]]
    trans = np.flatnonzero(np.diff((fi > 1500).astype(int)) != 0)
    run = np.diff(trans) / FS
    out["packet"] = dict(inst_freq_peaks_hz=[float(v) for v in two], shift_hz=float(two[1] - two[0]),
                         shortest_run_s=round(float(np.percentile(run, 5)), 5), bit_s=round(1 / 300, 5),
                         obw99_hz=round(obw99(xb)),
                         expected="200 Hz shift, 300 Bd, 730 Hz listed")
    # SITOR-A: ACF of envelope (cycle) and burst lengths
    x, m = b6.gen_sitora(np.random.default_rng(seed), 200.0)
    out["sitora"] = dict(cycle_s=env_period(x - x.mean(), 0.3, 0.6),
                         bursts_s=sorted(set(burst_lengths(x)[1:-1]))[:4],
                         expected="ACF 450 ms, bursts 0.065-0.290 s, pauses >= 0.2 s")
    # NDB: carrier + sidebands at +-400/1020 Hz
    x, m = b6.gen_ndb(np.random.default_rng(seed + 1), 200.0)
    f, p = welch(x, fs=FS, nperseg=FS)
    fc, tn = m["centre"], float(m["submode"][:-2])
    lvl = lambda fr: float(10 * np.log10(p[np.abs(f - fr) <= 2].max() / np.median(p)))
    out["ndb"] = dict(meta=m, carrier_db=round(lvl(fc), 1), usb_db=round(lvl(fc + tn), 1),
                      lsb_db=round(lvl(fc - tn), 1) if fc - tn > 150 else None,
                      off_line_db=round(lvl(fc + tn / 2), 1),
                      expected="carrier, sidebands at +-400 or 1020 Hz (dB above median PSD)")
    # occupancy at 0..15 dB
    occ = {}
    for c in ("fsq", "packet", "sitora", "ndb"):
        r = np.random.default_rng(seed + 7)
        rows = []
        for i in range(n):
            x, m = synth.generate(c, r, float(r.uniform(0, 15)))
            fc, bw, _ = features.occupancy_for(c, x)
            rows.append((m["submode"], None if fc is None else abs(fc - m["centre"]), bw))
        by = {}
        for s, e, bw in rows:
            by.setdefault(s, []).append((e, bw))
        occ[c] = {s: dict(n=len(v), none=sum(e is None for e, _ in v),
                          centre_err_med=round(float(np.median([e for e, _ in v if e is not None])), 1) if any(e is not None for e, _ in v) else None,
                          bw_med=round(float(np.median([b for _, b in v if b])), 1) if any(b for _, b in v) else None)
                  for s, v in by.items()}
    out["occupancy_0_15db"] = occ
    os.makedirs("results", exist_ok=True)
    json.dump(out, open(f"results/verify_b6_seed{seed}.json", "w"), indent=1, default=float)
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
