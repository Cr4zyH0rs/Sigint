"""Batch 2 generators: FT4, JS8, WSPR, JT65, JT9, FST4, Q65 (12 kHz, 15 s windows).

Where WSJT-X ships a simulator that writes audio, it is used as-is (real encoder
and modulator): jt65sim, jt49sim (JT9), fst4sim, q65sim. Where it does not,
the channel symbols come from the WSJT-X encoder (ft4code, wsprsim -c, ft8code)
and are modulated here following the published waveform parameters:

- FT4: 4-GFSK, 576 samples/symbol at 12 kHz (48 ms), tone spacing 20.833 Hz,
  BT = 1.0, 105 channel symbols incl. ramp symbols (Franke, Somerville & Taylor,
  QEX 2020, https://downloads.hamradiodeluxe.com/FT4_FT8_QEX.pdf ).
- WSPR: 4-FSK, 8192 samples/symbol at 12 kHz (0.683 s), spacing 1.4648 Hz,
  162 symbols, ~110.6 s (WSJT-X User Guide, https://wsjt.sourceforge.io/wsjtx-doc/wsjtx-main-2.7.0.html ).
- JS8 ("Normal"): 8-GFSK, 6.25 Hz spacing, 160 ms symbols, 79 symbols, same
  grid as FT8 (JS8Call guide, https://js8call.com ). JS8 uses its own Costas
  sync arrays; the arrays here are a stand-in permutation, NOT verified against
  JS8Call source, so this is "JS8-like".

A 15 s window is a random slice of longer transmissions (WSPR, JT65, JT9,
FST4-60, Q65-30), since the pipeline always sees 15 s at a time.
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile

import numpy as np
import soundfile as sf
from scipy.special import erf

from .synth import FS, N_WIN, _unit_rms, add_awgn, random_call, random_ft8_message, random_grid

NEW_CLASSES = ["ft4", "js8", "wspr", "jt65", "jt9", "fst4", "q65"]


def _run(cmd, d, timeout=60):
    return subprocess.run(cmd, cwd=d, capture_output=True, text=True, timeout=timeout)


def gfsk_pulse(bt: float, t: np.ndarray) -> np.ndarray:
    c = np.pi * np.sqrt(2 / np.log(2))
    return 0.5 * (erf(c * bt * (t + 0.5)) - erf(c * bt * (t - 0.5)))


def gfsk(symbols, nsps, spacing, f0, bt=None):
    """Continuous-phase (G)FSK. bt=None gives plain FSK."""
    symbols = np.asarray(symbols, float)
    if bt is None:
        dev = np.repeat(symbols, nsps)
    else:
        # convolve symbol train with a Gaussian-filtered rectangular pulse 3 symbols long
        # WSJT-X style: frequency = sum_k sym_k * pulse(t - k), pulse spans 3 symbols
        p = gfsk_pulse(bt, (np.arange(3 * nsps) - 1.5 * nsps + 0.5) / nsps)
        train = np.zeros(len(symbols) * nsps)
        train[nsps // 2::nsps] = symbols
        dev = np.convolve(train, p, mode="full")[int(1.5 * nsps) - nsps // 2:][:len(train)]
    f = f0 + spacing * dev
    ph = 2 * np.pi * np.cumsum(f) / FS
    s = np.sin(ph)
    r = nsps // 8  # short amplitude ramp at ends
    s[:r] *= np.linspace(0, 1, r)
    s[-r:] *= np.linspace(1, 0, r)
    return s


def _digits_after(text, header):
    tail = text.split(header, 1)[1]
    return [int(c) for c in re.sub(r"[^0-9]", "", tail.split("\n\n")[0] if "\n\n" in tail else tail)]


def ft4_symbols(msg):
    with tempfile.TemporaryDirectory() as d:
        out = _run(["ft4code", msg], d).stdout
    line = [l for l in out.splitlines() if re.fullmatch(r"[0-3 ]{100,}", l.strip())][-1]
    return [int(c) for c in line if c.isdigit()]


def ft8_symbols(msg):
    with tempfile.TemporaryDirectory() as d:
        out = _run(["ft8code", msg], d).stdout
    line = [l for l in out.splitlines() if re.fullmatch(r"[0-7 ]{79,}", l.strip())][-1]
    return [int(c) for c in line if c.isdigit()]


def wspr_symbols(msg):
    with tempfile.TemporaryDirectory() as d:
        out = _run(["wsprsim", "-c", msg], d).stdout
    tail = out.split("Channel symbols:", 1)[1]
    return [int(c) for c in tail.split()][:162]


def _place_at(sig, start):
    out = np.zeros(N_WIN)
    n = min(len(sig), N_WIN - start)
    out[start:start + n] = sig[:n]
    return out


def _slice15(x, rng, tx_start, tx_len):
    """Random 15 s window that overlaps the transmission by at least 10 s."""
    lo = max(0, tx_start - 5 * FS)
    hi = max(lo, min(len(x) - N_WIN, tx_start + tx_len - 10 * FS))
    s = int(rng.integers(lo, hi + 1))
    seg = x[s:s + N_WIN]
    return np.pad(seg, (0, N_WIN - len(seg)))


def gen_ft4(rng, snr):
    x = np.zeros(N_WIN)
    meta = []
    for slot in range(int(rng.integers(1, 3))):  # FT4 period is 7.5 s: 1-2 TX per window
        m = random_ft8_message(rng)
        f0 = float(rng.uniform(300, 2600))
        s = _unit_rms(gfsk(ft4_symbols(m), 576, 12000 / 576, f0, bt=1.0))
        st = int((slot * 7.5 + 0.5 + rng.uniform(-0.2, 0.3)) * FS)
        x += _place_at(s, st)
        meta.append(dict(msg=m, f0=f0))
    return add_awgn(x, snr, rng, 1.0), meta


_JS8_COSTAS = [4, 2, 5, 6, 1, 3, 0]  # stand-in; see module docstring


def gen_js8(rng, snr):
    m = random_ft8_message(rng)
    sym = ft8_symbols(m)
    for k in (0, 36, 72):
        sym[k:k + 7] = _JS8_COSTAS
    f0 = float(rng.uniform(300, 2600))
    s = _unit_rms(gfsk(sym, 1920, 6.25, f0, bt=2.0))
    x = _place_at(s, int((0.5 + rng.uniform(-0.3, 1.0)) * FS))
    return add_awgn(x, snr, rng, 1.0), dict(f0=f0)


def gen_wspr(rng, snr):
    msg = f"{random_call(rng)} {random_grid(rng)} {int(rng.choice([23, 30, 33, 37, 40]))}"
    f0 = float(rng.uniform(1400, 1600))
    s = _unit_rms(gfsk(wspr_symbols(msg), 8192, 12000 / 8192, f0))
    full = np.concatenate([np.zeros(FS), s, np.zeros(FS)])
    x = _slice15(full, rng, FS, len(s))
    return add_awgn(x, snr, rng, 1.0), dict(f0=f0 + 1.5 * 12000 / 8192)


def _sim_wav(cmd, rng):
    with tempfile.TemporaryDirectory() as d:
        r = _run(cmd, d, timeout=120)
        wavs = sorted(f for f in os.listdir(d) if f.endswith(".wav"))
        if not wavs:
            raise RuntimeError(f"{cmd[0]} wrote no wav: {r.stdout[-200:]} {r.stderr[-200:]}")
        x, fs = sf.read(os.path.join(d, wavs[0]), dtype="float64")
    assert fs == FS
    return x


def gen_jt65(rng, snr):
    f0 = float(rng.uniform(500, 2300))
    sub = str(rng.choice(["A", "B", "C"]))
    x = _sim_wav(["jt65sim", "-m", sub, "-n", "1", "-F", f"{f0:.0f}", "-s", "99",
                  "-f", "1", "-M", random_ft8_message(rng)], rng)
    on = np.flatnonzero(np.abs(x) > 1e-6)
    x = _unit_rms(x)
    x = _slice15(x, rng, int(on[0]), int(on[-1] - on[0]))
    return add_awgn(x, snr, rng, 1.0), dict(f0=f0, sub=sub)


def gen_jt9(rng, snr):
    x = _sim_wav(["jt49sim", random_ft8_message(rng), "9A", "1", "0.0", "0.0", "0.0", "1", "99"], rng)
    on = np.flatnonzero(np.abs(x) > 1e-6)
    x = _unit_rms(x)
    x = _slice15(x, rng, int(on[0]), int(on[-1] - on[0]))
    # jt49sim fixes f0=1500; shift randomly to avoid a frequency shortcut
    shift = float(rng.uniform(-1100, 1000))
    from scipy.signal import hilbert
    x = np.real(hilbert(x) * np.exp(2j * np.pi * shift * np.arange(len(x)) / FS))
    return add_awgn(x, snr, rng, 1.0), dict(f0=1500 + shift)


def gen_fst4(rng, snr):
    tr = int(rng.choice([15, 30, 60]))
    f0 = float(rng.uniform(500, 2300))
    x = _sim_wav(["fst4sim", random_ft8_message(rng), str(tr), f"{f0:.0f}", "0.0", "0.0",
                  "0.0", "1", "99", "F"], rng)
    on = np.flatnonzero(np.abs(x) > 1e-6)
    x = _unit_rms(x)
    x = _slice15(x, rng, int(on[0]), int(on[-1] - on[0]))
    return add_awgn(x, snr, rng, 1.0), dict(f0=f0, tr=tr)


def gen_q65(rng, snr):
    tr = int(rng.choice([15, 30]))
    sub = str(rng.choice(["A", "B", "C", "D"]))
    f0 = float(rng.uniform(500, 2300))
    x = _sim_wav(["q65sim", random_ft8_message(rng), sub, f"{f0:.0f}", "0.0", "0.0", "0.0",
                  "0", str(tr), "1", "1", "99"], rng)
    on = np.flatnonzero(np.abs(x) > 1e-6)
    x = _unit_rms(x)
    x = _slice15(x, rng, int(on[0]), int(on[-1] - on[0]))
    return add_awgn(x, snr, rng, 1.0), dict(f0=f0, tr=tr, sub=sub)


GENERATORS = dict(ft4=gen_ft4, js8=gen_js8, wspr=gen_wspr, jt65=gen_jt65, jt9=gen_jt9,
                  fst4=gen_fst4, q65=gen_q65)
