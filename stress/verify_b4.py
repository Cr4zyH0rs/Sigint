"""Check batch 4 audio against the published parameters it is meant to follow.

No SSTV/fax/ALE decoder is installed here (installing one from PyPI was not allowed), so each
check measures the on-air structure from the clean waveform (instantaneous frequency via the
Hilbert transform, scipy.signal.hilbert) and compares it with the spec values cited in
sigint/synth_b4.py. SITOR-B/NAVTEX audio is fldigi's own; its shift and baud are measured.

Usage: python stress/verify_b4.py N SEED  -> results/verify_b4_seed{SEED}.json
"""
import json, os, sys
import numpy as np
from scipy.signal import hilbert, welch
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sigint import synth_b4 as b4, synth_fldigi
from sigint.synth import FS

EXPECT_LINE_MS = {"Martin M1": 446.446, "Martin M2": 226.798, "Scottie S1": 428.22,
                  "Scottie S2": 277.692, "Robot 36": 150.0, "PD120": 508.48}
EXPECT_VIS = {k: v[0] for k, v in b4.SSTV_MODES.items()}


def inst_freq(x):
    a = hilbert(x)
    return np.diff(np.unwrap(np.angle(a))) * FS / (2 * np.pi)


def smooth(v, n):
    return np.convolve(v, np.ones(n) / n, mode="same")


def read_vis(f):
    """Decode the VIS byte: find the 30 ms 1200 Hz start bit after the 1900 Hz leader."""
    fs = smooth(f, 60)
    lead = np.flatnonzero(np.abs(fs - 1900) < 40)
    i = lead[0] + int(0.61 * FS)                     # 300 + 10 + 300 ms
    bits = [int(np.median(fs[i + int((0.03 * (k + 1) + 0.005) * FS): i + int((0.03 * (k + 2) - 0.005) * FS)]) < 1200)
            for k in range(8)]
    code = sum(b << k for k, b in enumerate(bits[:7]))
    return code, bits[7] == sum(bits[:7]) % 2


def line_period_ms(f, start):
    """Median spacing of 1200 Hz sync pulse starts."""
    sync = smooth(f[start:], 24) < 1300
    on = np.flatnonzero(np.diff(sync.astype(int)) == 1)
    d = np.diff(on) / FS * 1000
    d = d[d > 100]
    return float(np.median(d)) if len(d) else None


def check_sstv(rng):
    out = []
    for mode in b4.SSTV_MODES:
        _, track = b4.sstv_transmission(rng, mode)
        x = b4.fm_tone(track)
        f = inst_freq(x)
        code, par = read_vis(f)
        lp = line_period_ms(f, int(0.91 * FS))
        exp = EXPECT_LINE_MS[mode] * (2 if mode == "PD120" else 1) / (2 if mode == "PD120" else 1)
        pix = f[int(1 * FS):]
        out.append(dict(mode=mode, vis=code, vis_ok=code == EXPECT_VIS[mode] and par,
                        line_ms=lp, line_ms_expected=exp,
                        line_ok=lp is not None and abs(lp - exp) < 1.0,
                        f_min=float(np.percentile(pix, 0.5)), f_max=float(np.percentile(pix, 99.5)),
                        total_s=len(track) / FS))
    return out


def check_wefax(rng, n):
    res = []
    for _ in range(n):
        tr = b4.wefax_transmission(rng, 120, 576, lines=40)
        f = smooth(inst_freq(b4.fm_tone(tr)), 6)
        st = f[: 5 * FS]
        # start tone: count black->white transitions per second
        trans = np.sum(np.diff((st > 1900).astype(int)) == 1) / 5.0
        ph = f[5 * FS: 35 * FS]
        white = (ph > 1900).astype(float)
        ac = np.correlate(white - white.mean(), white - white.mean(), "full")[len(white) - 1:]
        lag = int(np.argmax(ac[int(0.3 * FS): int(0.7 * FS)])) + int(0.3 * FS)
        stop = f[-15 * FS: -10 * FS]
        trans_stop = np.sum(np.diff((stop > 1900).astype(int)) == 1) / 5.0
        res.append(dict(start_hz=float(trans), stop_hz=float(trans_stop), line_s=lag / FS,
                        black=float(np.percentile(f[35 * FS:-15 * FS], 1)),
                        white=float(np.percentile(f[35 * FS:-15 * FS], 99))))
    ok = all(abs(r["start_hz"] - 300) < 1 and abs(r["stop_hz"] - 450) < 1 and abs(r["line_s"] - 0.5) < 0.002
             for r in res)
    return dict(n=n, all_ok=ok, first=res[0])


def check_ale(rng, n):
    errs, rates = [], []
    for _ in range(n):
        tr = b4.ale_burst(rng, 10)
        f = inst_freq(b4.fm_tone(tr))
        # sample each symbol centre and snap to nearest tone
        q = b4.ALE_SPS // 4   # middle half of each 8 ms symbol, away from the tone steps
        c = np.median(f[: len(f) // b4.ALE_SPS * b4.ALE_SPS].reshape(-1, b4.ALE_SPS)[:, q:-q], 1)
        errs.append(float(np.max(np.min(np.abs(c[:, None] - b4.ALE_TONES[None]), 1))))
        rates.append(len(tr) / FS / 10)
    return dict(n=n, tones=b4.ALE_TONES.tolist(), max_tone_err_hz=max(errs),
                word_s=float(np.mean(rates)), symbol_ms=1000 * b4.ALE_SPS / FS,
                all_ok=max(errs) < 10 and abs(np.mean(rates) - 0.392) < 1e-9)


def check_ncdxf():
    out = []
    for call in b4.NCDXF_ORDER:
        env = b4._ncdxf_slot(call)
        on = env > 1e-4
        # last four key-down runs are the dashes
        edges = np.flatnonzero(np.diff(np.r_[0, on.astype(int), 0]))
        runs = list(zip(edges[::2], edges[1::2]))[-4:]
        lens = [(b - a) / FS for a, b in runs]
        lv = [20 * np.log10(env[(a + b) // 2]) for a, b in runs]
        out.append(dict(call=call, dash_s=[round(v, 3) for v in lens],
                        level_db=[round(v, 1) for v in lv],
                        call_end_s=round(runs[0][0] / FS, 2)))
    ok = all(all(abs(d - 1.0) < 0.02 for d in o["dash_s"]) and
             np.allclose(o["level_db"], [0, -10, -20, -30], atol=0.2) and o["call_end_s"] < 6 for o in out)
    return dict(all_ok=ok, slots=out)


def check_sitorb():
    out = []
    for split in ("train", "test"):
        for sub, x in synth_fldigi._takes(split, "sitorb"):
            # shift: the two strongest modes of the instantaneous-frequency histogram
            # that are > 120 Hz apart (fldigi's NAVTEX idle/phasing adds a mid peak)
            fi = smooth(inst_freq(x), 40)
            env = np.abs(hilbert(x))[1:]
            hist, e = np.histogram(fi[env > 0.3 * env.max()], bins=np.arange(200, 3000, 5))
            c = (e[:-1] + e[1:]) / 2
            k1 = int(np.argmax(hist))
            k2 = int(np.argmax(np.where(np.abs(c - c[k1]) > 120, hist, 0)))
            shift = abs(c[k2] - c[k1])
            # baud: spectrum of |d inst_freq| (symbol transitions) peaks at the baud rate
            fi = smooth(inst_freq(x[: 20 * FS]), 12)
            tr = np.abs(np.diff(np.sign(fi - (c[k1] + c[k2]) / 2)))  # slice at the mark/space midpoint
            ff, pp = welch(tr, fs=FS, nperseg=FS)
            sel = (ff > 50) & (ff < 200)
            baud = float(ff[sel][np.argmax(pp[sel])])
            out.append(dict(split=split, submode=sub, shift_hz=round(float(shift), 1), baud=baud))
    ok = all(abs(o["shift_hz"] - 170) < 6 and abs(o["baud"] - 100) < 2 for o in out)
    return dict(all_ok=ok, takes=out)


if __name__ == "__main__":
    n, seed = int(sys.argv[1]), int(sys.argv[2])
    rng = np.random.default_rng(seed)
    r = dict(sstv=check_sstv(rng), wefax=check_wefax(rng, min(n, 10)), ale=check_ale(rng, n),
             ncdxf=check_ncdxf(), sitorb=check_sitorb())
    os.makedirs("results", exist_ok=True)
    json.dump(r, open(f"results/verify_b4_seed{seed}.json", "w"), indent=1, default=float)
    print(json.dumps(r, indent=1, default=float)[:6000])
