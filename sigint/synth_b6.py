"""Batch 6 generators built from published on-air descriptions (ID-only: random payloads).

Sources (read 2026-11-22 through the user's Claude-app browser; sigidwiki is blocked here):
  FSQ     https://www.sigidwiki.com/wiki/FSQ and the developers' description
          https://www.qsl.net/zl1bpu/MFSK/FSQweb.htm : 33 tones 8.7890625 Hz apart (= 1.5 x the
          highest baud rate), IFK+ (tone = previous tone + character number + 1, minus 33 when
          over range), speeds nominally 6, 4.5, 3, 2 Bd, no idle: a transmission starts with no
          padding and stops when the buffer is empty; 300 Hz bandwidth.
  PACKET  https://www.sigidwiki.com/wiki/PACKET : HF 300 Bd FSK with 200 Hz shift (FSK300), also
          BPSK300 / QPSK600 (IL2P); frames derived from X.25/HDLC; 730 Hz listed bandwidth.
  SITOR-A https://www.sigidwiki.com/wiki/SITOR-A : ARQ, 100 Bd FSK, 170 Hz shift most common
          (300/400/850 Hz also seen), ACF 450 ms, 350 Hz; based on CCIR 476-4.
          https://cartoonman.github.io/Shoc/sitora.htm : bursts 0.065-0.290 s, pauses >= 0.2 s.
  NDB     https://www.sigidwiki.com/wiki/Non-Directional_Beacon_(NDB) : A2A, continuous carrier
          with a Morse callsign of one or more letters modulated as AM at 400 or 1020 Hz.

ASSUMED (not stated in those sources): FSQ burst/pause lengths and that the 4.5/3/2 Bd speeds
keep the same 1.5x ratio as 6 Bd; packet TXDELAY flag preamble, frame lengths, NRZI + bit
stuffing (HDLC as used by AX.25) and inter-frame gaps; SITOR-A block = 3 characters x 7 bits
(210 ms) and control signal = 1 character (70 ms) from the 7-unit CCIR 476 code, which fits
the 450 ms ACF and the 0.065-0.290 s burst range; NDB keying speed, ID repeat gap and
modulation depth.
"""
from __future__ import annotations

import numpy as np

from .synth import FS, N_WIN, MORSE
from .synth_b5 import _finish, arq_session, fsk

# ------------------------------------------------------------------ FSQ
FSQ_SPACING = 8.7890625
FSQ_BAUDS = {"6": FSQ_SPACING / 1.5, "4.5": FSQ_SPACING / 1.5 * 0.75,
             "3": FSQ_SPACING / 1.5 * 0.5, "2": FSQ_SPACING / 1.5 / 3}


def fsq_tones(rng, n_sym):
    d = rng.integers(0, 32, n_sym)
    t = np.zeros(n_sym, int)
    t[0] = rng.integers(0, 33)
    for i in range(1, n_sym):
        t[i] = (t[i - 1] + d[i] + 1) % 33
    return t


def mfsk_phase_coherent(tones, baud, f0, spacing):
    sps = FS / baud
    edges = np.round(np.arange(len(tones) + 1) * sps).astype(int)
    f = np.empty(edges[-1])
    for i, tn in enumerate(tones):
        f[edges[i]:edges[i + 1]] = f0 + tn * spacing
    return np.sin(np.cumsum(2 * np.pi * f / FS))


def gen_fsq(rng, snr_db):
    sp = str(rng.choice(list(FSQ_BAUDS), p=[0.4, 0.3, 0.2, 0.1]))
    baud = FSQ_BAUDS[sp]
    f0 = float(rng.uniform(800, 1800))            # lowest tone; signal spans 32 x 8.79 = 281 Hz
    x = np.zeros(N_WIN * 2)
    t = float(rng.uniform(-6, 2))
    while t < len(x) / FS:
        dur = float(rng.uniform(3, 12))           # one chat over (ASSUMED)
        b = mfsk_phase_coherent(fsq_tones(rng, max(2, int(dur * baud))), baud, f0, FSQ_SPACING)
        a = int(t * FS)
        lo, hi = max(0, a), min(len(x), a + len(b))
        if hi > lo:
            x[lo:hi] = b[lo - a:hi - a]
        t += len(b) / FS + float(rng.uniform(1, 6))
    x = x[:N_WIN]
    if not np.any(x):
        x[: int(3 * FS)] = mfsk_phase_coherent(fsq_tones(rng, int(3 * baud)), baud, f0, FSQ_SPACING)[: int(3 * FS)]
    return _finish(rng, x, snr_db, dict(submode=f"{sp}Bd", centre=f0 + 16 * FSQ_SPACING))


# ------------------------------------------------------------------ PACKET
def hdlc_bits(rng, n_bytes, n_flags):
    flag = [0, 1, 1, 1, 1, 1, 1, 0]
    data = rng.integers(0, 2, n_bytes * 8)
    stuffed, ones = [], 0
    for bit in data:                               # bit stuffing: 0 after five 1s
        stuffed.append(int(bit))
        ones = ones + 1 if bit else 0
        if ones == 5:
            stuffed.append(0)
            ones = 0
    raw = flag * n_flags + stuffed + flag * 2
    out, level = [], 1                             # NRZI: 0 -> transition, 1 -> no change
    for bit in raw:
        if bit == 0:
            level ^= 1
        out.append(level)
    return np.array(out)


def gen_packet(rng, snr_db):
    psk = rng.random() < 0.3
    fc = float(rng.uniform(1000, 2000))
    x = np.zeros(N_WIN * 2)
    t = float(rng.uniform(-3, 2))
    while t < len(x) / FS:
        bits = hdlc_bits(rng, int(rng.integers(20, 260)), int(rng.integers(15, 60)))
        if psk:                                    # BPSK300 (IL2P framing not modelled)
            b = _bpsk300(bits, fc)
        else:
            b = fsk(bits, 300, fc - 100, fc + 100)
        a = int(t * FS)
        lo, hi = max(0, a), min(len(x), a + len(b))
        if hi > lo:
            x[lo:hi] = b[lo - a:hi - a] * (1.0 if rng.random() < 0.6 else 10 ** (rng.uniform(-15, 0) / 20))
        t += len(b) / FS + float(rng.uniform(0.3, 4))
    x = x[:N_WIN]
    return _finish(rng, x, snr_db, dict(submode="BPSK300" if psk else "FSK300", centre=fc))


def _bpsk300(bits, fc):
    from .synth_b5 import rrc
    sps = FS // 300 if FS % 300 == 0 else int(round(FS / 300))
    sym = np.where(bits > 0, 1.0, -1.0)
    up = np.zeros(len(sym) * sps)
    up[::sps] = sym
    bb = np.convolve(up, rrc(0.5, sps), mode="same")
    t = np.arange(len(bb)) / FS
    return bb * np.cos(2 * np.pi * fc * t)


# ------------------------------------------------------------------ SITOR-A
def gen_sitora(rng, snr_db):
    shift = float(rng.choice([170, 300, 400, 850], p=[0.7, 0.1, 0.1, 0.1]))
    fc = float(rng.uniform(1000, 2000))
    pk = lambda: fsk(rng.integers(0, 2, 21), 100, fc - shift / 2, fc + shift / 2)
    cs = lambda: fsk(rng.integers(0, 2, 7), 100, fc - shift / 2, fc + shift / 2)
    x = arq_session(rng, 0.45, 0.21, 0.07, pk, cs)
    return _finish(rng, x, snr_db, dict(submode=f"{int(shift)}Hz", centre=fc))


# ------------------------------------------------------------------ NDB
def _morse_env(text, wpm):
    dot = int(1.2 / wpm * FS)
    env = []
    for w, word in enumerate(text.split()):
        for c, ch in enumerate(word):
            for s, sym in enumerate(MORSE[ch]):
                env += [1] * (dot if sym == "." else 3 * dot) + [0] * dot
            env += [0] * (2 * dot)
        env += [0] * (4 * dot)
    return np.array(env, float)


def gen_ndb(rng, snr_db):
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    call = "".join(rng.choice(list(letters), int(rng.integers(1, 4))))
    tone = float(rng.choice([400.0, 1020.0]))
    fc = float(rng.uniform(450, 1800))             # carrier's audio offset in USB
    wpm = float(rng.uniform(5, 12))
    depth = float(rng.uniform(0.3, 0.95))
    env1 = _morse_env(call, wpm)
    gap = np.zeros(int(rng.uniform(1.0, 6.0) * FS))
    env = np.tile(np.concatenate([env1, gap]), N_WIN // (len(env1) + len(gap)) + 2)
    s = int(rng.integers(0, len(env) - N_WIN))
    env = np.convolve(env[s:s + N_WIN], np.ones(60) / 60, mode="same")     # 5 ms key shaping
    t = np.arange(N_WIN) / FS
    ph = rng.uniform(0, 2 * np.pi)
    x = np.cos(2 * np.pi * fc * t + ph) * (1 + depth * env * np.cos(2 * np.pi * tone * t))
    # USB receiver: the lower sideband (fc - tone) is only heard when it stays above ~150 Hz
    if fc - tone < 150:
        from scipy.signal import butter, sosfiltfilt
        x = sosfiltfilt(butter(8, 150 + 30, "highpass", fs=FS, output="sos"), x)
    return _finish(rng, x, snr_db, dict(submode=f"{int(tone)}Hz", centre=fc))


GENERATORS = dict(fsq=gen_fsq, packet=gen_packet, sitora=gen_sitora, ndb=gen_ndb)
