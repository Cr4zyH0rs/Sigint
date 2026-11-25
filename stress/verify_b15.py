"""Batch 15 checks: does an independent decoder (DSDcc, Debian package dsdcc 1.9.3) find the frame
syncs in our own random test frames? Only DSDcc's "good sync found" lines are counted (a transmission counts as detected when at
least one appears; DSDcc reports a sync when it gains lock, not on every frame); it is run
with -n (no audio out) and anything else it prints is discarded. DSDcc has no P25 support
("-f1 Decode only P25 Phase 1 - not supported", dsdccx -h), so P25 is checked with our own
matched filter against the published-in-MMDVM sync word instead (not independent).

Usage: python3 stress/verify_b15.py  -> results/verify_b15_seed15.json
"""
from __future__ import annotations

import json
import subprocess
import sys

import numpy as np
from scipy import signal as sps

sys.path.insert(0, ".")
from sigint import synth_b15 as b  # noqa: E402

FLAGS = dict(dmr=["-fr"], dmr_direct=["-fr"], dstar=["-fd"], ysf=["-fy"], nxdn=["-fi", "-d", "0"])


def over(rng, mode):
    if mode == "dmr":
        return b.dmr_repeater_over(rng, 3.0), 4800, b._RRC5
    if mode == "dmr_direct":
        return b.dmr_direct_over(rng, 3.0), 4800, b._RRC5
    if mode == "dstar":
        return b.dstar_over(rng, 3.0), 4800, b._GAUSS
    if mode == "ysf":
        return b.ysf_over(rng, 3.0), 4800, b._RRC5
    if mode == "nxdn":
        return b.nxdn_over(rng, 3.0), 2400, b._RRC10
    if mode == "p25":
        return b.p25_over(rng, 3.0, b.rand_syms(rng, 6)), 4800, b._RC5


def expected(mode, syms, baud):
    """Sync words actually present in the frames we built."""
    if mode in ("dmr", "dmr_direct"):
        kind = "bs" if mode == "dmr" else "ms"
        pats = [b.bits_to_syms(b.DMR_SYNC[kind + k], 48) for k in ("_voice", "_data")]
    elif mode == "ysf":
        pats = [b.YSF_SYNC]
    elif mode == "nxdn":
        pats = [b.NXDN_FSW]
    elif mode == "p25":
        pats = [b.P25_SYNC]
    else:
        return 1                                                   # D-STAR header frame sync
    n = 0
    for p in pats:
        L = len(p)
        n += sum(np.array_equal(syms[i:i + L], p) for i in range(len(syms) - L + 1))
    return int(n)


def audio(syms, baud, h, band):
    x = b.shape(np.concatenate([np.zeros(baud), syms, np.zeros(baud)]), baud, h)
    if band == "300-3000 Hz":
        x = sps.sosfilt(sps.butter(4, [300, 3000], "bandpass", fs=b.FS48, output="sos"), x)
    elif band == "de-emphasis, 20-3000 Hz":
        bb, a = sps.butter(1, 300.0, fs=b.FS48)
        x = sps.sosfilt(sps.butter(4, [20, 3000], "bandpass", fs=b.FS48, output="sos"), sps.lfilter(bb, a, x))
    return x


def dsdcc_syncs(x, flags):
    pcm = (x / np.max(np.abs(x)) * 12000).astype("<i2").tobytes()
    p = subprocess.run(["dsdccx", "-i", "-", "-o", "/dev/null", "-n", "-v", "2", *flags],
                       input=pcm, capture_output=True, timeout=120)
    lines = [l for l in (p.stdout + p.stderr).decode(errors="replace").splitlines() if "good sync found" in l]
    return len(lines), sorted({l.split()[1] for l in lines})


def p25_syncs(x, baud, h):
    tpl = b.shape(np.concatenate([np.zeros(8), b.P25_SYNC, np.zeros(8)]), baud, h)
    c = np.correlate(x, tpl, "valid") / (np.linalg.norm(tpl) * np.sqrt(np.convolve(x ** 2, np.ones(len(tpl)), "valid")) + 1e-12)
    pk, _ = sps.find_peaks(c, height=0.6, distance=24 * b.FS48 // baud)
    return len(pk), ["own matched filter"]


def main():
    out = {}
    for mode in ["dmr", "dmr_direct", "dstar", "ysf", "nxdn", "p25"]:
        for band in ["flat", "de-emphasis, 20-3000 Hz", "300-3000 Hz"]:
            found = exp = det = 0
            kinds = set()
            for k in range(10):
                rng = np.random.default_rng(15_000 + k)
                syms, baud, h = over(rng, mode)
                x = audio(syms, baud, h, band)
                n, ks = p25_syncs(x, baud, h) if mode == "p25" else dsdcc_syncs(x, FLAGS[mode])
                det += n > 0
                found += min(n, expected(mode, syms, baud))
                exp += expected(mode, syms, baud)
                kinds |= set(ks)
            out[f"{mode} | {band}"] = dict(transmissions_detected=det, transmissions=10, sync_lines=found,
                                           syncs_sent=exp, sync_types=sorted(kinds))
            print(mode, "|", band, det, "/ 10 detected;", found, "sync lines /", exp, "syncs sent", sorted(kinds), flush=True)
    json.dump(out, open("results/verify_b15_seed15.json", "w"), indent=1)


if __name__ == "__main__":
    main()
