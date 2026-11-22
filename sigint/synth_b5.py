"""Batch 5 generators: NATO/US military HF data modems and PACTOR, from published descriptions.

No encoder for these modems is available here, so each generator reproduces the on-air
structure (carrier(s), symbol rate, frame/known-symbol periodicity, ARQ timing) that an ID
classifier sees. Payload bits are random. Nothing here demodulates or decodes anything.

Sources (parameters quoted in the report, docs/batch5_results.md):
  sigidwiki (read 2026-11-19 via its MediaWiki API):
    https://www.sigidwiki.com/wiki/STANAG_4285            2750 Hz, ACF 106.66 ms, BPSK/QPSK/8PSK
    https://www.sigidwiki.com/wiki/MIL-STD-188-110_Serial  2400 Bd, ACF header 200 ms, body 66.66 ms
    https://www.sigidwiki.com/wiki/MIL-STD-188-110_Appendix_A_16-Tone  75 Bd/tone, 605 Hz pilot, 2100 Hz
    https://www.sigidwiki.com/wiki/MIL-STD-188-110_Appendix_B_39-Tone  44.44 Bd, ~393 Hz pilot, DQPSK
    https://www.sigidwiki.com/wiki/STANAG_4197             39-tone variant without the pilot
    https://www.sigidwiki.com/wiki/PACTOR_I  /PACTOR_II  /PACTOR_III
  ARRL protocol pages (read 2026-11-19):
    https://www.arrl.org/pactor      0.96 s packet + 0.12 s CS + 0.17 s idle = 1.25 s; 100/200 Bd; CS at 100 Bd
    https://www.arrl.org/pactor-ii   2 DPSK tones 200 Hz apart, 100 Bd; 0.8 s packet, 0.28 s CS, 1.25 s
                                     cycle; long packets 3.28 s in a 3.75 s cycle
    https://www.arrl.org/pactor-iii  up to 18 carriers on a 120 Hz grid, 100 sym/s DBPSK/DQPSK,
                                     speed levels 1-6 = 2/6/14/14/16/18 carriers, 400-2600 Hz
Assumptions (not found in those pages) are marked ASSUMED below.
"""
from __future__ import annotations

import numpy as np

from .synth import FS, N_WIN, add_awgn

NEW_CLASSES = ["stanag4285", "mil110_serial", "mil110_16tone", "mil110_39tone",
               "pactor1", "pactor2", "pactor3"]

PSK_FC = 1800.0          # serial-tone carrier for STANAG 4285 and 110 serial
SER_BAUD = 2400
SER_SPS = FS // SER_BAUD  # 5 samples per symbol


def rrc(beta, sps, span=8):
    t = (np.arange(-span * sps, span * sps + 1)) / sps
    h = np.zeros_like(t)
    for i, ti in enumerate(t):
        if abs(ti) < 1e-9:
            h[i] = 1 - beta + 4 * beta / np.pi
        elif beta and abs(abs(ti) - 1 / (4 * beta)) < 1e-9:
            h[i] = beta / np.sqrt(2) * ((1 + 2 / np.pi) * np.sin(np.pi / (4 * beta)) +
                                        (1 - 2 / np.pi) * np.cos(np.pi / (4 * beta)))
        else:
            h[i] = (np.sin(np.pi * ti * (1 - beta)) + 4 * beta * ti * np.cos(np.pi * ti * (1 + beta))) / \
                   (np.pi * ti * (1 - (4 * beta * ti) ** 2))
    return h / np.sqrt(np.sum(h ** 2))


_RRC = rrc(0.15, SER_SPS)   # ASSUMED roll-off; 2400 Bd x 1.15 = 2760 Hz, close to sigidwiki's 2750 Hz


def serial_psk(symbols_c, fc):
    up = np.zeros(len(symbols_c) * SER_SPS, complex)
    up[::SER_SPS] = symbols_c
    bb = np.convolve(up, _RRC, mode="same")
    t = np.arange(len(bb)) / FS
    return np.real(bb * np.exp(2j * np.pi * fc * t))


def lfsr(taps, nbits, n, seed=1):
    """Fibonacci LFSR bit sequence (taps are exponents of the feedback polynomial)."""
    s, out = seed, []
    for _ in range(n):
        out.append(s & 1)
        fb = 0
        for t in taps:
            fb ^= (s >> (t - 1)) & 1 if t else 0
        s = (s >> 1) | (fb << (nbits - 1))
    return np.array(out)


PSK8 = np.exp(2j * np.pi * np.arange(8) / 8)


# ------------------------------------------------------------------ STANAG 4285
# 256-symbol frame (106.67 ms, matches sigidwiki ACF 106.66 ms):
# 80 sync symbols, then D32 R16 D32 R16 D32 R16 D32 (data / known reference).
_S4285_SYNC = PSK8[4 * lfsr([5, 2], 5, 80)]             # BPSK sync from a period-31 sequence
_S4285_SCR = np.random.default_rng(4285).integers(0, 8, 176)  # ASSUMED stand-in for the 176-symbol scrambler


def stanag4285_symbols(rng, n_frames):
    out = []
    for _ in range(n_frames):
        body = []
        for blk in range(4):
            body.append(rng.integers(0, 8, 32))          # data (8-ary after scrambling)
            if blk < 3:
                body.append(np.zeros(16, int))           # known reference
        body = (np.concatenate(body) + _S4285_SCR) % 8   # same scrambler every frame
        out += [_S4285_SYNC, PSK8[body]]
    return np.concatenate(out)


# ------------------------------------------------------------------ MIL-STD-188-110 serial
# Body: unknown/known frames; data scrambler period 160 symbols (66.67 ms, sigidwiki body ACF).
# 150-600 bps: 20 unknown + 20 known (lcm(40,160) = 160 -> 66.67 ms ACF)
# 1200-2400 bps: 32 unknown + 16 known (lcm(48,160) = 480 -> 200 ms)
# Preamble: 200 ms segments (sigidwiki header ACF 200 ms), 3 segments (short interleave)
# or 24 (long). ASSUMED preamble content: one fixed 480-symbol 8-PSK pattern.
_M110_SCR = np.random.default_rng(110).integers(0, 8, 160)
_M110_PRE = np.random.default_rng(1101).integers(0, 8, 480)


def mil110_symbols(rng, n_sym, preamble_segments, high_rate):
    u, k = (32, 16) if high_rate else (20, 20)
    pre = np.tile(_M110_PRE, preamble_segments)
    nb = n_sym
    frames = []
    while sum(map(len, frames)) < nb:
        frames += [rng.integers(0, 8, u), np.zeros(k, int)]
    body = np.concatenate(frames)[:nb]
    body = (body + np.resize(_M110_SCR, nb)) % 8
    return PSK8[np.concatenate([pre, body])]


# ------------------------------------------------------------------ parallel-tone modems
def multitone_dpsk(rng, freqs, sym_s, n_sym, m=4, pilot=None, pilot_gain=1.0, edge=0.1):
    """Differential M-PSK on each tone, constant symbol length, raised-cosine symbol edges."""
    ns = int(round(sym_s * FS))
    t = np.arange(ns * n_sym) / FS
    x = np.zeros(ns * n_sym)
    win = np.ones(ns)
    r = max(1, int(edge * ns))
    win[:r] = 0.5 - 0.5 * np.cos(np.pi * np.arange(r) / r)
    win[-r:] = win[:r][::-1]
    env = np.tile(win, n_sym)
    for f in freqs:
        ph = np.cumsum(rng.integers(0, m, n_sym) * 2 * np.pi / m) + rng.uniform(0, 2 * np.pi)
        x += env * np.cos(2 * np.pi * f * t + np.repeat(ph, ns))
    if pilot is not None:
        x += pilot_gain * np.cos(2 * np.pi * pilot * t)
    return x


TONES_16 = 935.0 + 110.0 * np.arange(16)      # 935..2585 Hz; 605 Hz pilot (sigidwiki)
TONES_39 = 675.0 + 56.25 * np.arange(39)      # 675..2812.5 Hz; 393.75 Hz pilot


# ------------------------------------------------------------------ PACTOR
def fsk(bits, baud, f_lo, f_hi):
    sps = int(round(FS / baud))
    f = np.repeat(np.where(bits, f_hi, f_lo), sps).astype(float)
    return np.sin(np.cumsum(2 * np.pi * f / FS))


def dpsk_tones(rng, n_sym, baud, freqs, m):
    return multitone_dpsk(rng, freqs, 1.0 / baud, n_sym, m=m, edge=0.5)


def arq_session(rng, cycle_s, pkt_s, cs_s, make_pkt, make_cs, n=N_WIN * 3):
    """ISS packets + IRS control signals at a different level (or not heard). 0.17 s idle
    is what is left of the cycle (ARRL)."""
    g_cs = 0.0 if rng.random() < 0.3 else 10 ** (rng.uniform(-20, 0) / 20)
    x = np.zeros(n)
    t0 = 0.0
    while int(t0 * FS) < n:
        a = int(t0 * FS)
        p = make_pkt()
        x[a:a + len(p)] = p[: max(0, min(len(p), n - a))]
        b = int((t0 + pkt_s + (cycle_s - pkt_s - cs_s) / 2) * FS)
        c = g_cs * make_cs()
        if b < n:
            x[b:b + len(c)] = c[: max(0, min(len(c), n - b))]
        t0 += cycle_s
    return x


def gen_pactor1(rng, snr_db):
    fc = float(rng.uniform(1000, 2000))
    baud = 200 if rng.random() < 0.6 else 100
    pk = lambda: fsk(rng.integers(0, 2, int(0.96 * baud)), baud, fc - 100, fc + 100)
    cs = lambda: fsk(rng.integers(0, 2, 12), 100, fc - 100, fc + 100)
    x = arq_session(rng, 1.25, 0.96, 0.12, pk, cs)
    return _finish(rng, x, snr_db, dict(submode=f"{baud}Bd", centre=fc))


def gen_pactor2(rng, snr_db):
    fc = float(rng.uniform(1000, 2000))
    f2 = [fc - 100, fc + 100]
    long_ = rng.random() < 0.4
    m = int(rng.choice([2, 4, 8, 16]))
    pkt_s, cyc = (3.28, 3.75) if long_ else (0.8, 1.25)
    pk = lambda: dpsk_tones(rng, int(pkt_s * 100), 100, f2, m)
    cs = lambda: dpsk_tones(rng, 28, 100, f2, 2)
    x = arq_session(rng, cyc, pkt_s, 0.28, pk, cs)
    return _finish(rng, x, snr_db, dict(submode=("long " if long_ else "") + f"{m}-DPSK", centre=fc))


# carrier indices per speed level (ARRL table); carrier k at 1500 + (k - 8.5) * 120 Hz
P3_LEVELS = {1: [5, 12], 2: [3, 5, 7, 10, 12, 14], 3: list(range(2, 16)), 4: list(range(2, 16)),
             5: list(range(1, 17)), 6: list(range(0, 18))}


def gen_pactor3(rng, snr_db):
    lvl = int(rng.integers(1, 7))
    off = float(rng.uniform(-100, 100))       # dial mistuning
    freqs = [1500 + (k - 8.5) * 120 + off for k in P3_LEVELS[lvl]]
    m = 2 if lvl <= 3 else 4
    # ASSUMED: PACTOR-II long-packet timing (3.28 s in 3.75 s) and a PACTOR-II-style
    # two-tone DBPSK control signal on carriers 5 and 12.
    cs_f = [1500 + (k - 8.5) * 120 + off for k in (5, 12)]
    pk = lambda: dpsk_tones(rng, 328, 100, freqs, m) / np.sqrt(len(freqs))
    cs = lambda: dpsk_tones(rng, 28, 100, cs_f, 2) / np.sqrt(2)
    x = arq_session(rng, 3.75, 3.28, 0.28, pk, cs)
    return _finish(rng, x, snr_db, dict(submode=f"level {lvl}", centre=1500 + off))


# ------------------------------------------------------------------ continuous modems
def _continuous(rng, x_full):
    """Place a transmission so the window may contain its start or end (or neither)."""
    n = len(x_full)
    s = int(rng.integers(-2 * FS, max(1, n - N_WIN + 2 * FS)))
    out = np.zeros(N_WIN)
    a, b = max(0, s), min(n, s + N_WIN)
    if b > a:
        out[a - s:b - s] = x_full[a:b]
    return out


def _finish(rng, x, snr_db, meta):
    if len(x) > N_WIN:
        x = _continuous(rng, x)
    on = np.abs(x) > 1e-6
    x = x / np.sqrt(np.mean(x[on] ** 2))      # windows always overlap >= 13 s of signal
    return add_awgn(x, snr_db, rng, 1.0), meta


def gen_stanag4285(rng, snr_db):
    off = float(rng.uniform(-50, 50))
    x = serial_psk(stanag4285_symbols(rng, int(25 / 0.10667)), PSK_FC + off)
    return _finish(rng, x, snr_db, dict(centre=PSK_FC + off))


def gen_mil110_serial(rng, snr_db):
    off = float(rng.uniform(-50, 50))
    pre = 3 if rng.random() < 0.7 else 24
    hi = bool(rng.random() < 0.5)
    x = serial_psk(mil110_symbols(rng, 25 * SER_BAUD, pre, hi), PSK_FC + off)
    return _finish(rng, x, snr_db, dict(submode=("32/16" if hi else "20/20") + f" pre{pre}",
                                        centre=PSK_FC + off))


def gen_mil110_16tone(rng, snr_db):
    off = float(rng.uniform(-50, 50))
    pilot = 605.0 + off if rng.random() < 0.5 else None
    x = multitone_dpsk(rng, TONES_16 + off, 1 / 75, int(25 * 75), m=4, pilot=pilot, pilot_gain=1.0)
    return _finish(rng, x, snr_db, dict(submode="pilot" if pilot else "no pilot",
                                        centre=float(np.mean(TONES_16)) + off))


def gen_mil110_39tone(rng, snr_db):
    off = float(rng.uniform(-50, 50))
    s4197 = rng.random() < 0.3              # STANAG 4197 (ANDVT): same tones, no pilot
    # ASSUMED pilot level: 2x a data tone's amplitude
    x = multitone_dpsk(rng, TONES_39 + off, 1 / 44.444, int(25 * 44.444), m=4,
                       pilot=None if s4197 else 393.75 + off, pilot_gain=2.0, edge=0.05)
    return _finish(rng, x, snr_db, dict(submode="STANAG 4197" if s4197 else "App B",
                                        centre=float(np.mean(TONES_39)) + off))


GENERATORS = dict(stanag4285=gen_stanag4285, mil110_serial=gen_mil110_serial,
                  mil110_16tone=gen_mil110_16tone, mil110_39tone=gen_mil110_39tone,
                  pactor1=gen_pactor1, pactor2=gen_pactor2, pactor3=gen_pactor3)
