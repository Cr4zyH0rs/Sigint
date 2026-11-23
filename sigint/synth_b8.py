"""Batch 8 generators: FreeDV digital voice, Robust Packet Radio and DTMF (ID-only: random payloads).

Sources (read 2026-11-22):
  FreeDV 1600 https://www.sigidwiki.com/wiki/Frequency_Division_Multiplex_Digital_Voice_(FDMDV) :
              14 DQPSK carriers at 50 Bd, 75 Hz apart, plus a centre BPSK pilot at 2x power;
              FreeDV 1600 1.3 kHz wide.
  FreeDV 700C https://www.sigidwiki.com/wiki/FreeDV_COHPSK : 14-carrier coherent QPSK (7 carriers
              duplicated), 1.5 kHz. The page also names 700D.
  FreeDV 700D/700E https://github.com/drowe67/codec2/blob/main/README_freedv.md : 700D 17-carrier
              OFDM/QPSK 1000 Hz, 700E 21-carrier OFDM/QPSK 1500 Hz; all modes ~50 Hz symbol rate.
              All four FreeDV modes are made by codec2 1.2.0's own modulator (libcodec2 freedv_tx,
              tools/freedv_tx_min.c), fed with random noise in place of speech.
  RPR         https://www.sigidwiki.com/wiki/Robust_PACKET : OFDM, 8 DBPSK/DQPSK carriers, 60 Hz
              spacing, 50 Bd each, 500 Hz; 200 bps BPSK / 600 bps QPSK.
              https://wavecom.ch/content/pdf/advanced_protocol_robust-packet.pdf : centre 1500 Hz,
              each packet led by a 160 ms preamble of 64 DPSK symbols across the 8 carriers.
  DTMF        https://www.sigidwiki.com/wiki/Dual_Tone_Multi_Frequency_(DTMF) : two tones per symbol;
              tone/space timing 20/20 ms (Genave) to 250/250 ms (Motorola) and up to 1000/1000 ms
              (Federal Signal); manual keying variable. Tone table (697/770/852/941 Hz rows,
              1209/1336/1477/1633 Hz columns): https://en.wikipedia.org/wiki/Dual-tone_multi-frequency_signaling

ASSUMED (not stated in those sources): FreeDV overs of 3-15 s with 0.5-4 s gaps, or a whole
window; +-50 Hz mistuning on FreeDV and RPR; 700D/700E share one class (both codec2 OFDM);
RPR symbol shaping (raised-cosine edges, 20% of a symbol), packet lengths 1-6 s, gaps
0.3-4 s, 160 ms preamble = 8 BPSK symbols on all 8 carriers; DTMF digit counts 3-16, the
mix of timing profiles, and a 0-10 dB twist between the two tones.
"""
from __future__ import annotations

import os
import subprocess

import numpy as np
from scipy.signal import hilbert, resample_poly

from .synth import FS, N_WIN
from .synth_b5 import _finish
from .synth_b7 import _place

_TX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "freedv_tx_min")


def _shift(x, hz):
    return np.real(hilbert(x) * np.exp(2j * np.pi * hz * np.arange(len(x)) / FS))


# ------------------------------------------------------------------ FreeDV (codec2's modulator)
def freedv_audio(mode: str, seconds: float, seed: int) -> np.ndarray:
    raw = subprocess.run([_TX, mode, f"{seconds:.2f}", str(seed)], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.int16).astype(float) / 32768.0
    return resample_poly(x, 3, 2)                   # 8 kHz -> 12 kHz


def _gen_freedv(rng, snr_db, modes):
    mode = str(rng.choice(modes))
    seed = int(rng.integers(1, 2**31 - 1))
    x = np.zeros(N_WIN)
    if rng.random() < 0.5:                          # carrier on for the whole window
        x[:] = freedv_audio(mode, 16, seed)[:N_WIN]
    else:                                           # overs with gaps (ASSUMED)
        t = float(rng.uniform(-6, 3))
        while t < 15:
            dur = float(rng.uniform(3, 15))
            x += _place(freedv_audio(mode, dur, seed + int(t * 100)), t)
            t += dur + float(rng.uniform(0.5, 4))
        if not np.any(x):
            x[:] = freedv_audio(mode, 16, seed)[:N_WIN]
    off = float(rng.uniform(-50, 50))
    x = _shift(x, off)
    return _finish(rng, x, snr_db, dict(submode=mode, centre=1500.0 + off))


def gen_freedv1600(rng, snr_db):
    return _gen_freedv(rng, snr_db, ["1600"])


def gen_freedv700c(rng, snr_db):
    return _gen_freedv(rng, snr_db, ["700C"])


def gen_freedv700de(rng, snr_db):
    return _gen_freedv(rng, snr_db, ["700D", "700E"])


# ------------------------------------------------------------------ Robust Packet Radio
RPR_FC, RPR_SPACING, RPR_BAUD, RPR_N = 1500.0, 60.0, 50.0, 8


def rpr_packet(rng, dur_s, qpsk, fc):
    sps = int(FS / RPR_BAUD)                        # 240 samples per symbol
    n_sym = 8 + int(dur_s * RPR_BAUD)               # 8-symbol (160 ms) preamble
    m = 4 if qpsk else 2
    t = np.arange(n_sym * sps) / FS
    ramp = int(0.2 * sps)
    w = np.ones(sps)
    w[:ramp] = 0.5 - 0.5 * np.cos(np.pi * np.arange(ramp) / ramp)
    w[-ramp:] = w[:ramp][::-1]
    pre = np.random.default_rng(64).integers(0, 2, 8)
    x = np.zeros(len(t))
    for k in range(RPR_N):
        f = fc + (k - (RPR_N - 1) / 2) * RPR_SPACING
        dphi = np.concatenate([np.pi * pre, 2 * np.pi * rng.integers(0, m, n_sym - 8) / m])
        sym = np.repeat(np.cumsum(dphi), sps)        # differential PSK: data in phase changes
        x += np.tile(w, n_sym) * np.cos(2 * np.pi * f * t + sym + rng.uniform(0, 2 * np.pi))
    return x


def gen_rpr(rng, snr_db):
    qpsk = rng.random() < 0.5
    fc = RPR_FC + float(rng.uniform(-50, 50))
    x = np.zeros(N_WIN)
    t = float(rng.uniform(-3, 2))
    while t < 15:
        dur = float(rng.uniform(1, 6))
        amp = 1.0 if rng.random() < 0.6 else 10 ** (rng.uniform(-15, 0) / 20)   # other station
        x += amp * _place(rpr_packet(rng, dur, qpsk, fc), t)
        t += dur + 0.16 + float(rng.uniform(0.3, 4))
    return _finish(rng, x, snr_db, dict(submode="600bps DQPSK" if qpsk else "200bps DBPSK", centre=fc))


# ------------------------------------------------------------------ DTMF
DTMF_ROWS = [697.0, 770.0, 852.0, 941.0]
DTMF_COLS = [1209.0, 1336.0, 1477.0, 1633.0]
DTMF_TIMING = {"whelen": (0.040, 0.020), "motorola": (0.250, 0.250), "genave": (0.020, 0.020),
               "federal": (0.035, 0.005), "federal_slow": (1.0, 1.0)}


def gen_dtmf(rng, snr_db):
    prof = str(rng.choice(list(DTMF_TIMING) + ["manual"], p=[0.15, 0.2, 0.1, 0.1, 0.05, 0.4]))
    x = np.zeros(N_WIN)
    t0 = float(rng.uniform(0.2, 8))
    t = t0
    for _ in range(int(rng.integers(3, 17))):
        if prof == "manual":
            on, off = float(rng.uniform(0.08, 0.4)), float(rng.uniform(0.1, 0.6))
        else:
            on, off = DTMF_TIMING[prof]
        r, c = DTMF_ROWS[rng.integers(0, 4)], DTMF_COLS[rng.integers(0, 4)]
        n = np.arange(int(on * FS)) / FS
        twist = 10 ** (-rng.uniform(0, 10) / 20)
        tone = np.sin(2 * np.pi * r * n) * twist + np.sin(2 * np.pi * c * n)
        x += _place(tone, t)
        t += on + off
        if t > 14.5:
            break
    if rng.random() < 0.3 and t < 10:               # sequence sent again
        seg = x[int(t0 * FS):int(t * FS)].copy()
        x += _place(seg, t + float(rng.uniform(0.5, 2)))
    return _finish(rng, x, snr_db, dict(submode=prof, centre=None))


GENERATORS = dict(freedv1600=gen_freedv1600, freedv700c=gen_freedv700c, freedv700de=gen_freedv700de,
                  rpr=gen_rpr, dtmf=gen_dtmf)
