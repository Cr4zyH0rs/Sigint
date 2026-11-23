"""Batch 9 generators: time stations, utility FSK and Russian MFSK/selcall signals
(ID-only: random payloads; nothing is decoded).

Sources (read 2026-11-23):
  WWV/WWVH https://www.nist.gov/pml/div688/grp40/wwv_format : 5 ms second ticks (WWV 1000 Hz,
           WWVH 1200 Hz) with 10 ms silence before and 25 ms after; no tick on seconds 29 and 59;
           800 ms minute marker (1000 / 1200 Hz), 1500 Hz on the hour; 500/600/440 Hz tone
           minutes per station (table on that page); voice ~7.5 s (WWV) or ~15 s (WWVH) before
           the minute.
  RWM      https://www.sigidwiki.com/wiki/RWM (OOK, 4.996/9.996/14.996 MHz, ACF 1000/100 ms) and
           https://en.wikipedia.org/wiki/RWM : carrier :00-:08, Morse ID :09, 1 Hz pulses :10
           (100 ms, minute pulse 500 ms), 10 Hz pulses :20 (20 ms, second 40 ms, minute 500 ms).
  ARQ-E    https://www.sigidwiki.com/wiki/ARQ-E(E3) : synchronous ARQ FSK, 30-650 Bd (mostly
           96-233), baud/shift pairs 72/85, 96/170, 192/160, 288/400; idles for hours.
  CIS FSK  https://www.sigidwiki.com/wiki/CIS-36-50 (36/50/75/100/150 Bd, shifts 85/125/250/500)
           and https://www.sigidwiki.com/wiki/CIS-50-50 (50 or 100 Bd, shifts 85/125/200/250/500,
           idles with 50 Bd dot reversals then traffic). One class: the wiki calls them very similar.
  XPA      https://www.sigidwiki.com/wiki/CIS_MFSK-20_XPA and
           https://priyom.org/number-stations/digital/xpa/protocol : 17-tone MFSK, 10 Bd; tones
           520/600/680/720, digits 760-1120 Hz in 40 Hz steps, 1160/1200/1280 Hz; 2 min preamble
           of 400 ms 520 Hz / 1600 ms 1280 Hz; 40 tones 600/1120; fixed tone string; 20 tones
           1200/1160; 10 space tones; 5-digit groups.
  XPA2     https://www.sigidwiki.com/wiki/CIS_MFSK-16_XPA2 and
           https://priyom.org/number-stations/digital/xpa2/protocol : 16 tones 15.625 Hz apart
           from 1000 Hz, 7.8125 Bd; 2 min preamble of 400 ms 1234.375 Hz / 1600 ms 1000 Hz;
           fixed string; 20 repeat/start tones; 10 spaces; 5-digit groups; 20 end/repeat tones.
  Mazielka https://www.sigidwiki.com/wiki/Mazielka_(X06) (6 tones, 200 Hz) and
           https://priyom.org/diplomatic-stations/russia/x06 : tones 815/845/875/910/950/990 Hz
           (+-5 Hz), 333 1/3 ms each, ~1320 ms pause, repeated for minutes.

Not built (no usable spec found): Codan Selcall (sigidwiki page did not load; no Shoc page) and
XPB (sigidwiki gives no baud rate or tone spacing).

ASSUMED (not stated in those sources): receiver zero-beat on the WWV carrier (audio = the AM
modulation only), 500/600/440 Hz tones running seconds 1-44 at the tick level, the 100 Hz BCD
code left out (below most SSB passbands); RWM heard as a 400-1500 Hz beat note in USB, carrier-only
periods left out (a bare tone has nothing to identify), DUT1 extra pulses left out, Morse 12-20 wpm;
ARQ-E and CIS FSK random bits (no repetition cycle or alphabet modelled), audio centre 1000-2000 Hz
and dial mistuning; XPA/XPA2 preamble phase length shown in a window, 20-60 groups; Mazielka uses
priyom's tone set (hfunderground lists 840-1015 Hz), each call a random order of the 6 tones.
"""
from __future__ import annotations

import numpy as np

from .synth import FS, N_WIN
from .synth_b5 import _finish, fsk
from .synth_b6 import _morse_env
from .synth_b7 import _place


def tone_seq(freqs, durs, ramp_s=0.002):
    """Phase-continuous tone sequence; freq 0 = silence. Short ramps at on/off edges."""
    out = []
    ph = 0.0
    for f, d in zip(freqs, durs):
        n = int(round(d * FS))
        if f <= 0:
            out.append(np.zeros(n))
            continue
        p = ph + 2 * np.pi * f * np.arange(1, n + 1) / FS
        out.append(np.sin(p))
        ph = p[-1] if n else ph
    x = np.concatenate(out) if out else np.zeros(0)
    on = np.concatenate([np.full(int(round(d * FS)), f > 0, float) for f, d in zip(freqs, durs)])
    r = max(1, int(ramp_s * FS))
    return x * np.convolve(on, np.ones(r) / r, mode="same")


# ------------------------------------------------------------------ WWV / WWVH
WWV_500 = {4, 6, 12, 14, 16, 20, 22, 24, 26, 28, 32, 34, 36, 38, 40, 42, 52, 54, 56, 58}
WWV_600 = {1, 3, 5, 7, 11, 13, 15, 17, 19, 21, 23, 25, 27, 31, 33, 35, 37, 39, 41, 53, 55, 57}
WWVH_500 = {3, 5, 7, 11, 13, 21, 23, 25, 27, 31, 33, 35, 37, 39, 41, 43, 44, 45, 47, 48, 49, 50, 51, 53, 55, 57}
WWVH_600 = {2, 4, 6, 12, 20, 22, 24, 26, 28, 32, 34, 36, 38, 40, 42, 46, 52, 54, 56, 58}


def _wwv_minute(rng, station, minute, hour_mark):
    tick_f = 1000.0 if station == "WWV" else 1200.0
    x = np.zeros(60 * FS)
    if station == "WWV":
        tone = 500.0 if minute in WWV_500 else 600.0 if minute in WWV_600 else 440.0 if minute == 2 else 0.0
    else:
        tone = 500.0 if minute in WWVH_500 else 600.0 if minute in WWVH_600 else 440.0 if minute == 1 else 0.0
    if tone:
        t = np.arange(44 * FS) / FS
        tn = 0.5 * np.sin(2 * np.pi * tone * t)
        for s in range(1, 45):                     # 40 ms notch around each tick
            a = int((s - 0.010) * FS) - FS
            tn[max(0, a):a + int(0.040 * FS)] = 0
        x[FS:45 * FS] = tn
    x += _place(tone_seq([1500.0 if hour_mark else tick_f], [0.8]), 0, 60 * FS)
    for s in range(1, 60):
        if s in (29, 59):
            continue
        x += _place(tone_seq([tick_f], [0.005], ramp_s=0.0005), s, 60 * FS)
    from .synth import gen_ssb
    v, _ = gen_ssb(rng, 200.0, text=f"At the tone, {int(rng.integers(0, 24))} hours, {(minute + 1) % 60} minutes, "
                                     "Coordinated Universal Time.")
    on = np.flatnonzero(np.abs(v) > 0.02 * np.abs(v).max())
    v = v[on[0]:on[-1] + 1][: int(6 * FS)]
    v = 0.5 * v / (np.abs(v).max() + 1e-9)
    x += _place(v, 60 - (7.5 if station == "WWV" else 15.0), 60 * FS)
    return x


def gen_wwv(rng, snr_db):
    station = str(rng.choice(["WWV", "WWVH"]))
    m = int(rng.integers(0, 60))
    full = np.concatenate([_wwv_minute(rng, station, m, False), _wwv_minute(rng, station, (m + 1) % 60, rng.random() < 0.1)])
    s = int(rng.integers(0, len(full) - N_WIN))
    return _finish(rng, full[s:s + N_WIN], snr_db, dict(submode=station, centre=None))


# ------------------------------------------------------------------ RWM
def gen_rwm(rng, snr_db):
    fc = float(rng.uniform(400, 1500))
    part = str(rng.choice(["1pps", "10pps", "morse"], p=[0.4, 0.4, 0.2]))
    sec0 = int(rng.integers(0, 60))
    if part == "morse":
        env = _morse_env("RWM RWM RWM RWM RWM RWM RWM RWM", float(rng.uniform(12, 20)))
        env = np.tile(env, 3)
        s = int(rng.integers(0, max(1, len(env) - N_WIN)))
        env = env[s:s + N_WIN]
        env = np.pad(env, (0, N_WIN - len(env)))
    else:
        env = np.zeros(N_WIN)
        step = 1.0 if part == "1pps" else 0.1
        for k in range(int(15 / step) + 1):
            t = k * step
            sec = (sec0 + int(t + 1e-9)) % 60
            on_second = abs(t - round(t)) < 1e-6
            if on_second and sec == 0:
                d = 0.5
            elif part == "1pps":
                d = 0.1
            else:
                d = 0.04 if on_second else 0.02
            if part == "10pps" and sec == 0 and not on_second and (t - int(t)) < 0.5:
                continue                           # inside the 500 ms minute pulse
            a = int(t * FS)
            env[a:a + int(d * FS)] = 1.0
    env = np.convolve(env, np.ones(24) / 24, mode="same")      # 2 ms key shaping
    x = env * np.sin(2 * np.pi * fc * np.arange(N_WIN) / FS + rng.uniform(0, 6.3))
    return _finish(rng, x, snr_db, dict(submode=part, centre=fc))


# ------------------------------------------------------------------ ARQ-E and CIS FSK
ARQE_PAIRS = [(72, 85), (96, 170), (192, 160), (288, 400)]


def gen_arqe(rng, snr_db):
    baud, shift = ARQE_PAIRS[int(rng.integers(0, len(ARQE_PAIRS)))]
    fc = float(rng.uniform(1000, 2000))
    x = fsk(rng.integers(0, 2, int(16 * baud)), baud, fc - shift / 2, fc + shift / 2)[:N_WIN]
    return _finish(rng, x, snr_db, dict(submode=f"{baud}Bd/{shift}Hz", centre=fc))


def gen_cis_fsk(rng, snr_db):
    if rng.random() < 0.5:
        kind, baud, shift = "CIS-36-50", int(rng.choice([36, 50, 75, 100, 150])), int(rng.choice([85, 125, 250, 500]))
    else:
        kind, baud, shift = "CIS-50-50", int(rng.choice([50, 100], p=[0.7, 0.3])), int(rng.choice([85, 125, 200, 250, 500], p=[0.1, 0.1, 0.3, 0.3, 0.2]))
    fc = float(rng.uniform(1000, 2000))
    n_dots = int(rng.uniform(0, 16) * 50)          # 50 Bd dot reversals, then traffic
    dots = fsk(np.arange(n_dots) % 2, 50, fc - shift / 2, fc + shift / 2)
    data = fsk(rng.integers(0, 2, int(16 * baud)), baud, fc - shift / 2, fc + shift / 2)
    x = np.concatenate([dots, data])[:N_WIN]
    return _finish(rng, x, snr_db, dict(submode=f"{kind} {baud}Bd/{shift}Hz", centre=fc))


# ------------------------------------------------------------------ XPA / XPA2
XPA_FIXED = "666662266262644444444446666622662626"
BARKER = "6666622662626"


def _xpa_freqs(rng):
    digit = lambda d: 760.0 + 40.0 * int(d)
    f, d = [], []
    for _ in range(int(rng.uniform(2, 15))):        # part of the 2-minute preamble
        f += [520.0, 1280.0]; d += [0.4, 1.6]
    sym = 0.1
    seq = [600.0, 1120.0] * 20 + [digit(c) for c in XPA_FIXED]
    sched = "".join(str(v) for v in rng.integers(0, 10, 4))
    seq += [digit(c) for c in sched * 3] + [600.0, 1120.0] * 20 + [digit(c) for c in XPA_FIXED]
    seq += [1200.0, 1160.0] * 10 + [680.0] * 10
    for g in range(int(rng.integers(20, 60))):
        if g and g % 64 == 0:
            seq += [digit(c) for c in BARKER]
        grp = rng.integers(0, 10, 5)
        for i, c in enumerate(grp):                # repeated digit -> "repeat" tone
            seq.append(1200.0 if i and c == grp[i - 1] else digit(c))
        seq.append(680.0)
    seq.append(720.0)
    return f + seq, d + [sym] * len(seq)


def gen_xpa(rng, snr_db):
    f, d = _xpa_freqs(rng)
    off = float(rng.uniform(-50, 50))
    x = tone_seq([v + off for v in f], d)
    return _finish(rng, x, snr_db, dict(submode="XPA", centre=940.0 + off))


def _xpa2_freqs(rng):
    sp, base = 15.625, 1000.0
    k = lambda i: base + sp * i
    digit = lambda c: k(6 + int(c))                # 0 -> 1093.75 ... 9 -> 1234.375 Hz
    f, d = [], []
    for _ in range(int(rng.uniform(2, 15))):
        f += [k(15), k(0)]; d += [0.4, 1.6]
    seq = [digit(c) for c in BARKER] + [k(5), k(2)] * 10 + [k(0)] * 10
    for _ in range(int(rng.integers(15, 40))):
        grp = rng.integers(0, 10, 5)
        for i, c in enumerate(grp):
            seq.append(k(5) if i and c == grp[i - 1] else digit(c))
        seq.append(k(0))
    seq += [k(3), k(5)] * 10
    return f + seq, d + [1 / 7.8125] * len(seq)


def gen_xpa2(rng, snr_db):
    f, d = _xpa2_freqs(rng)
    off = float(rng.uniform(-50, 50))
    x = tone_seq([v + off for v in f], d)
    return _finish(rng, x, snr_db, dict(submode="XPA2", centre=1117.0 + off))


# ------------------------------------------------------------------ Mazielka (X06)
X06_HZ = [815.0, 845.0, 875.0, 910.0, 950.0, 990.0]


def gen_mazielka(rng, snr_db):
    off = float(rng.uniform(-50, 50))
    order = rng.permutation(6)
    jit = rng.uniform(-5, 5, 6)
    f, d = [], []
    for _ in range(12):
        for i in order:
            f.append(X06_HZ[i] + jit[i] + off); d.append(1 / 3)
        f.append(0.0); d.append(1.32)
    x = tone_seq(f, d)
    return _finish(rng, x, snr_db, dict(submode="".join(str(i + 1) for i in order), centre=902.5 + off))


GENERATORS = dict(wwv=gen_wwv, rwm=gen_rwm, arqe=gen_arqe, cis_fsk=gen_cis_fsk,
                  xpa=gen_xpa, xpa2=gen_xpa2, mazielka=gen_mazielka)
