"""Batch 10 generators built outside fldigi: codec2 data modes (DATAC*) and HamDRM digital SSTV
(ID-only: random payloads). The fldigi classes of this batch (ifkp, pskr, mcpsk, ofdm) are real
fldigi 4.2.03 transmissions recorded by stress/record_b10.sh and played by sigint/synth_fldigi.py.

Sources (read 2026-11-23):
  DATAC   https://github.com/drowe67/codec2/blob/main/README_data.md : OFDM + LDPC raw data modes;
          DATAC0 500 Hz / 0.44 s bursts, DATAC1 1700 Hz / 4.18 s, DATAC3 500 Hz / 3.19 s,
          DATAC4 250 Hz / 5.17 s, DATAC13 200 Hz / 2.0 s; frames are preamble | data | postamble.
          Audio comes from codec2 1.2.0's own modulator (tools/datac_tx.c, libcodec2
          freedv_rawdatatx), so the waveform is the real one. Used by FreeDATA and Mercury
          (https://github.com/Rhizomatica/mercury).
  HamDRM  https://sstv-handbook.com/download/sstv_10.pdf (section 10.2, table 10.2): DRM-derived
          COFDM for a 2.5 kHz SSB channel; modes A, B, E with 53/57, 45/51, 29/31 sub-carriers at
          2.3/2.5 kHz; QAM-4/16/64; a lead-in at the start of a transmission.
          https://qsl.net/o/on4qz/qsstv/manual/drmmodes.html : mode B and E on HF, 2.2 or 2.5 kHz.
          https://www.sigidwiki.com/wiki/WinDRM : QAM/OFDM, 2.2-2.4 kHz, ACF 400 ms.
          OFDM timing from DRM: https://www.etsi.org/deliver/etsi_ES/201900_201999/201980/04.03.01_60/es_201980v040301p.pdf
          (ES 201 980 clause 4.4.2.2, table 2): T = 1/12 kHz; mode A Tu 24 ms, Tg 2 2/3 ms;
          mode B Tu 21 1/3 ms, Tg 5 1/3 ms; frame 400 ms (15 symbols).

ASSUMED (not stated in those sources): DATAC bursts of 1-4 frames with 0.3-3 s gaps (the other
station's ACKs not modelled), audio centre 1500 Hz +-50 Hz; HamDRM: only modes A and B (mode E's
timing is not in the pages read), centre 1500 Hz +-50 Hz, pilot layout (first symbol of each frame
all-pilot; every 4th carrier a boosted pilot, shifting by one each symbol; 3 fixed boosted carriers),
lead-in of 1-3 frames of pilot symbols, transmissions of 30-120 s with 2-8 s gaps.
"""
from __future__ import annotations

import os
import subprocess

import numpy as np
from scipy.signal import hilbert, resample_poly

from .synth import FS, N_WIN
from .synth_b5 import _finish
from .synth_b7 import _place

_TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
DATAC_MODES = {"DATAC0": 0.44, "DATAC1": 4.18, "DATAC3": 3.19, "DATAC4": 5.17, "DATAC13": 2.0}


def _shift(x, hz):
    return np.real(hilbert(x) * np.exp(2j * np.pi * hz * np.arange(len(x)) / FS))


def datac_burst(mode: str, nframes: int, seed: int) -> np.ndarray:
    raw = subprocess.run([os.path.join(_TOOLS, "datac_tx"), mode, str(nframes), str(seed)],
                         capture_output=True, check=True).stdout
    return resample_poly(np.frombuffer(raw, np.int16).astype(float) / 32768.0, 3, 2)


def gen_datac(rng, snr_db):
    mode = str(rng.choice(list(DATAC_MODES)))
    x = np.zeros(N_WIN)
    t = float(rng.uniform(-4, 2))
    while t < 15:
        nf = 1 if mode in ("DATAC0", "DATAC13") else int(rng.integers(1, 4))
        b = datac_burst(mode, nf, int(rng.integers(1, 2**31 - 1)))
        x += _place(b, t)
        t += len(b) / FS + float(rng.uniform(0.3, 3))
    if not np.any(x):
        x += _place(datac_burst(mode, 1, 1), 1.0)
    off = float(rng.uniform(-50, 50))
    return _finish(rng, _shift(x, off), snr_db, dict(submode=mode, centre=1500.0 + off))


# ------------------------------------------------------------------ HamDRM
HAMDRM = {  # mode: (Tu samples at 12 kHz, Tg samples, carriers at 2.3 kHz, carriers at 2.5 kHz)
    "A": (288, 32, 53, 57),
    "B": (256, 64, 45, 51),
}


def hamdrm_signal(rng, mode: str, wide: bool, seconds: float, fc: float, with_lead: bool = True):
    nu, ng, n23, n25 = HAMDRM[mode]
    nc = n25 if wide else n23
    spacing = FS / nu
    k0 = int(round(fc / spacing)) - nc // 2
    qam = int(rng.choice([4, 16, 64], p=[0.5, 0.35, 0.15]))
    m = int(np.sqrt(qam))
    lv = (2 * np.arange(m) - (m - 1)) / np.sqrt(2 * (qam - 1) / 3)
    n_sym = int(seconds * FS / (nu + ng)) + 1
    lead = 15 * int(rng.integers(1, 4)) if with_lead else 0
    s0 = 0 if with_lead else int(rng.integers(0, 15))      # joined mid-frame
    pil = np.exp(2j * np.pi * np.random.default_rng(1615).random(nc))
    fixed = [nc // 6, nc // 2, 5 * nc // 6]
    out = np.zeros(n_sym * (nu + ng))
    for s in range(n_sym):
        if s < lead or (s + s0) % 15 == 0:
            cells = pil * np.sqrt(2)
        else:
            cells = lv[rng.integers(0, m, nc)] + 1j * lv[rng.integers(0, m, nc)]
            idx = np.arange((s % 4), nc, 4)
            cells[idx] = pil[idx] * np.sqrt(2)
            cells[fixed] = np.sqrt(2)
        spec = np.zeros(nu, complex)
        spec[k0:k0 + nc] = cells
        sym = np.fft.ifft(spec) * nu
        sym = np.concatenate([sym[-ng:], sym])       # cyclic prefix (guard interval)
        out[s * (nu + ng):(s + 1) * (nu + ng)] = np.real(sym)
    return out, qam, nc * spacing


def gen_hamdrm(rng, snr_db):
    mode = str(rng.choice(list(HAMDRM)))
    wide = rng.random() < 0.5
    fc = 1500.0 + float(rng.uniform(-50, 50))
    x = np.zeros(N_WIN)
    t = float(rng.uniform(-100, 5))
    while t < 15:
        dur = float(rng.uniform(30, 120))
        a, b = max(t, 0.0), min(t + dur, 15.0)
        if b > a:
            seg, qam, bw = hamdrm_signal(rng, mode, wide, b - a, fc, with_lead=t >= 0)
            x += _place(seg[:int((b - a) * FS)], a)
        t += dur + float(rng.uniform(2, 8))
    return _finish(rng, x[:N_WIN], snr_db, dict(submode=f"mode {mode} {'2.5' if wide else '2.3'} kHz", centre=fc))


GENERATORS = dict(datac=gen_datac, hamdrm=gen_hamdrm)
