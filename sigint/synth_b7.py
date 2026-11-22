"""Batch 7 generators: calling and data links (ID-only: random payloads).

Sources (read 2026-11-22 through the user's Claude-app browser):
  ICAO SELCAL https://www.sigidwiki.com/wiki/ICAO_Selcal : two simultaneous tones for 1 s, a
              200 ms pause, two more tones for 1 s; 16 tones (A-M without I, plus P-S); USB with
              full carrier, usually followed by USB voice. Tone frequencies:
              https://en.wikipedia.org/wiki/SELCAL (table "Alphabet-audio frequency equivalents").
  GMDSS DSC   https://www.sigidwiki.com/wiki/GMDSS_Digital_Selective_Calling (FSK, 350 Hz,
              derived from CCIR 493-4) and https://cartoonman.github.io/Shoc/dsc.htm
              (2-FSK, 170 Hz shift, 100 Bd). Full protocol: ITU-R M.493 (not read here).
  CCIR 493-4  https://www.sigidwiki.com/wiki/CCIR_493-4_Selcall : 170 Hz shift, 100 Bd, a long
  Selcall     CW tone as the preamble, 300 Hz. (Shoc's Codan SelCal page lists a 200 Hz shift;
              sigidwiki's 170 Hz is used here.)
  HFDL        https://www.sigidwiki.com/wiki/High_Frequency_Data_Link_(HFDL) : USB, 1440 Hz
              sub-carrier, 1800 Bd, BPSK/QPSK/8PSK (300-1800 bps), 2400 Hz; short and long
              interleave samples. Defined in ARINC 753 (not read here).
  MSK144      https://www.sigidwiki.com/wiki/MSK144 : MSK, 2000 bps, tones 1000 and 2000 Hz,
              72 ms packets (ACF 72 ms), meteor-scatter pings. Audio from WSJT-X's own msk144sim.

ASSUMED (not stated in those sources): SELCAL mistuning (+-50 Hz) and the share of windows
with voice after the call; DSC: 2 s dot pattern (alternating bits) then 4-8 s of 100 Bd data;
CCIR selcall: 1-4 s steady tone on one FSK frequency then 2-5 s of data; HFDL: burst lengths
(1.8 s short, 4.3 s long), 0.3 s BPSK preamble, 30 data + 15 known probe symbols, RRC roll-off
0.3, 1-3 bursts per window; MSK144: ping widths 0.05-2.5 s and 1-3 pings per window.
"""
from __future__ import annotations

import numpy as np

from .synth import FS, N_WIN, add_awgn
from .synth_b5 import _finish, fsk, rrc

SELCAL_HZ = dict(A=312.6, B=346.7, C=384.6, D=426.6, E=473.2, F=524.8, G=582.1, H=645.7,
                 J=716.1, K=794.3, L=881.0, M=977.2, P=1083.9, Q=1202.3, R=1333.5, S=1479.1)


def _place(x_burst, start_s, n=N_WIN):
    out = np.zeros(n)
    a = int(start_s * FS)
    lo, hi = max(0, a), min(n, a + len(x_burst))
    if hi > lo:
        out[lo:hi] = x_burst[lo - a:hi - a]
    return out


# ------------------------------------------------------------------ ICAO SELCAL
def gen_selcal(rng, snr_db):
    letters = list(SELCAL_HZ)
    if rng.random() < 0.5:                         # older 12-tone codes
        letters = letters[:12]
    code = rng.choice(letters, 4, replace=False)
    pairs = [sorted(code[:2]), sorted(code[2:])]
    off = float(rng.uniform(-50, 50))
    t = np.arange(FS) / FS
    seg = []
    for p in pairs:
        seg.append(sum(np.sin(2 * np.pi * (SELCAL_HZ[c] + off) * t + rng.uniform(0, 6.3)) for c in p))
        seg.append(np.zeros(int(0.2 * FS)))
    call = np.concatenate(seg[:-1])
    # call sent once or twice, 2-4 s apart; rest of window silent or voice (ASSUMED)
    x = np.zeros(N_WIN)
    t0 = float(rng.uniform(0.5, 9))
    x += _place(call, t0)
    end = t0 + len(call) / FS
    if rng.random() < 0.3 and end + 4 + len(call) / FS < 15:
        t1 = end + rng.uniform(2, 4)
        x += _place(call, t1)
        end = t1 + len(call) / FS
    x = x / np.sqrt(np.mean(x[np.abs(x) > 1e-6] ** 2))
    if rng.random() < 0.3 and end < 12:
        from .synth import gen_ssb
        v, _ = gen_ssb(rng, 200.0)
        v = v / np.sqrt(np.mean(v[np.abs(v) > 0.02 * np.abs(v).max()] ** 2))
        x += _place(v, end + rng.uniform(0.5, 1.5))[:N_WIN]
    code_s = "".join(pairs[0]) + "-" + "".join(pairs[1])
    return add_awgn(x, snr_db, rng, 1.0), dict(submode=("16-tone" if len(letters) == 16 else "12-tone"),
                                               code=code_s, centre=None)


# ------------------------------------------------------------------ DSC and CCIR 493-4 selcall
def gen_dsc(rng, snr_db):
    fc = float(rng.uniform(1000, 2000))
    dots = np.arange(200) % 2
    data = rng.integers(0, 2, int(rng.uniform(4, 8) * 100))
    call = fsk(np.concatenate([dots, data]), 100, fc - 85, fc + 85)
    t0 = float(rng.uniform(-len(call) / FS + 4, 11))
    x = _place(call, t0)
    return _finish(rng, x, snr_db, dict(submode="call", centre=fc))


def gen_ccir493(rng, snr_db):
    fc = float(rng.uniform(1000, 2000))
    pre_s = float(rng.uniform(1, 4))
    pre = np.ones(int(pre_s * 100), int) * int(rng.integers(0, 2))
    data = rng.integers(0, 2, int(rng.uniform(2, 5) * 100))
    call = fsk(np.concatenate([pre, data]), 100, fc - 85, fc + 85)
    t0 = float(rng.uniform(-len(call) / FS + 4, 11))
    x = _place(call, t0)
    return _finish(rng, x, snr_db, dict(submode=f"pre {pre_s:.1f}s", centre=fc))


# ------------------------------------------------------------------ HFDL
_HFDL_PRE = np.random.default_rng(753).integers(0, 2, int(0.3 * 1800)) * 2 - 1.0   # ASSUMED fixed


def _hfdl_burst(rng, dur_s, m):
    n = int(dur_s * 1800)
    syms = []
    probe = np.random.default_rng(1440).integers(0, 2, 15) * 2 - 1.0
    while len(syms) < n:
        k = rng.integers(0, m, 30)
        syms.extend(np.exp(2j * np.pi * k / m))
        syms.extend(probe)
    s = np.concatenate([_HFDL_PRE.astype(complex), np.array(syms[:n])])
    sps = 20                                      # 36 kHz / 1800 Bd, then decimate by 3
    up = np.zeros(len(s) * sps, complex)
    up[::sps] = s
    bb = np.convolve(up, rrc(0.3, sps), mode="same")[::3]
    t = np.arange(len(bb)) / FS
    return np.real(bb * np.exp(2j * np.pi * 1440.0 * t))


def gen_hfdl(rng, snr_db):
    m = int(rng.choice([2, 4, 8], p=[0.5, 0.35, 0.15]))
    long_ = rng.random() < 0.4
    dur = 4.3 if long_ else 1.8
    x = np.zeros(N_WIN)
    t = float(rng.uniform(-dur + 1.0, 6))
    for _ in range(int(rng.integers(1, 4))):
        if t >= 15:
            break
        x += _place(_hfdl_burst(rng, dur, m) * (1 if rng.random() < 0.6 else 10 ** (rng.uniform(-12, 0) / 20)), t)
        t += dur + float(rng.uniform(0.2, 6))
    off = float(rng.uniform(-50, 50))             # dial mistuning (ASSUMED)
    if off:
        from scipy.signal import hilbert
        x = np.real(hilbert(x) * np.exp(2j * np.pi * off * np.arange(N_WIN) / FS))
    return _finish(rng, x, snr_db, dict(submode=("long " if long_ else "short ") + {2: "BPSK", 4: "QPSK", 8: "8PSK"}[m],
                                        centre=1440.0 + off))


# ------------------------------------------------------------------ MSK144 (WSJT-X msk144sim)
def gen_msk144(rng, snr_db):
    from .synth import random_call, random_grid
    from .synth_wsjt import _sim_wav
    fc = float(rng.uniform(1400, 1600))
    x = np.zeros(N_WIN)
    widths = []
    for _ in range(int(rng.integers(1, 4))):
        w = float(rng.uniform(0.05, 2.5))
        msg = f"{random_call(rng)} {random_call(rng)} {random_grid(rng)}"
        y = _sim_wav(["msk144sim", msg, "15", f"{fc:.0f}", f"{w:.2f}", "30", "1"], rng)
        on = np.flatnonzero(np.abs(y) > 0.2 * np.abs(y).max())
        ping = y[max(0, on[0] - FS // 20): on[-1] + FS // 20]
        x += _place(ping, float(rng.uniform(0, 15 - min(len(ping) / FS, 14))))
        widths.append(round(w, 2))
    return _finish(rng, x, snr_db, dict(submode=f"{len(widths)} ping(s)", widths=widths, centre=fc))


GENERATORS = dict(selcal=gen_selcal, dsc=gen_dsc, ccir493=gen_ccir493, hfdl=gen_hfdl, msk144=gen_msk144)
