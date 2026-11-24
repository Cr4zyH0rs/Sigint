"""Batch 11 generators: wide military / NATO HF modems built from published parameters (ID-only:
random payloads, nothing is encoded to a real standard and nothing is decoded).

Sources (read 2026-11-24):
  STANAG 4539  https://cartoonman.github.io/Shoc/stanag4539.htm and .../stanag4539hdr.htm :
               QPSK/8PSK/16QAM/32QAM/64QAM, 2400 Bd, 3000 Hz, tuning 1800 Hz,
               3200/4800/6400/8000/9600(/12800) bit/s; "equivalent to MIL-STD-188-110 B appendix C".
               https://www.sigidwiki.com/wiki/STANAG_4539 : ACF 119.6 ms, 12800 bit/s = 64QAM no FEC.
  STANAG 4529  https://cartoonman.github.io/Shoc/stanag4529.htm : BPSK/QPSK/8PSK, 1200 Bd, 1300 Hz,
               75-1800 bit/s. https://www.sigidwiki.com/wiki/STANAG_4529 : 1.24 kHz, ACF 213.32 ms.
  3G ALE       https://www.sigidwiki.com/wiki/Automatic_Link_Establishment_(3G_ALE_ARCS)
               (STANAG 4538 / MIL-STD-188-141B App C): 8-PSK, 2400 Bd, centred at 1800 Hz, 3 kHz;
               TLC 106.667 ms (256 symbols); bursts BW0 613.333 ms (preamble 160 ms),
               BW1 1.30667 s (240 ms), BW2 640 ms + n*400 ms, n = 3/6/12/24 (26.67 ms),
               BW3 373.33 ms + n*13.33 ms, n = 64/128/256/512 (266.67 ms), BW4 640 ms (none),
               BW5 1013.33 ms (240 ms) = 256 TLC + 576 preamble + 1600 data symbols; ACF (BW3) 13.3 ms.
               https://cartoonman.github.io/Shoc/ale3g.htm : PSK, 2400 Bd, 3000 Hz.
  Link-11 SLEW https://www.sigidwiki.com/wiki/Link-11 : 8-PSK, single tone (serial), 2400 Bd, 3000 Hz.
               https://cartoonman.github.io/Shoc/link11slew.htm : bursts 0.100-2.000 s, minimum
               pause 0.004 s.
  STANAG 4481  https://cartoonman.github.io/Shoc/stanag4481.htm : FSK, 850 Hz shift,
               75/100/150/300/600 Bd, 1500 Hz.

Not new classes (see docs/batch11_results.md):
  STANAG 4197  39 QPSK tones 56.25 Hz apart (https://www.sigidwiki.com/wiki/STANAG_4197): already the
               no-pilot sub-mode of mil110_39tone (sigint/synth_b5.py, batch 5).
  Link-11 CLEW 16 tones at 75 Bd, DQPSK, 2500 Hz (https://www.sigidwiki.com/wiki/Link-11): the same
               tone count and rate as mil110_16tone (16 tones, 75 Bd per tone,
               https://www.sigidwiki.com/wiki/MIL-STD-188-110_Appendix_A_16-Tone); tone frequencies
               for CLEW are not in the pages read, so it is reported as mil110_16tone.
  STANAG 4481 PSK  BPSK, 2400 Bd, 1800 Hz, 3000 Hz (Shoc): the same parameters as stanag4285.

ASSUMED (not stated in those pages):
  - STANAG 4539: frame of 287 symbols (ACF 119.6 ms x 2400 Bd = 287.0), split as 256 data + 31
    known probe symbols; one fixed 8-PSK preamble of 0.24 s; probe and preamble content random but
    fixed; square 16/64QAM and cross 32QAM; centre 1800 +- 50 Hz; RRC roll-off 0.15.
  - STANAG 4529: the STANAG 4285 frame layout (80 sync, then D32 R16 D32 R16 D32 R16 D32) at
    1200 Bd, giving 256 symbols = 213.33 ms, which matches the ACF 213.32 ms; centre 1800 +- 50 Hz;
    RRC roll-off 0.05 (1200 x 1.05 = 1260 Hz, between 1.24 and 1.3 kHz).
  - 3G ALE: every burst is TLC + preamble + data (this adds up exactly for BW5, BW3 and BW0);
    TLC, preamble and the BW3 known half-blocks are random but fixed 8-PSK; each 13.33 ms BW3
    block is 16 data + 16 known symbols; an exchange is a call (BW5 or BW0), a BW0 reply and a
    BW0 confirm, then HDL (BW2 + BW1 ACK) or LDL (BW3 + BW4 ACK) traffic or nothing;
    turnaround gaps 0.1-0.6 s; the two stations differ by 0-12 dB.
  - Link-11 SLEW: carrier 1800 +- 50 Hz; no frame structure (none published in the pages read);
    roll call of 0.1-2.0 s bursts with 4-150 ms pauses; stations differ by up to 10 dB.
  - STANAG 4481 FSK: centre 1700 +- 100 Hz; continuous random bits.
"""
from __future__ import annotations

import numpy as np

from .synth import FS, N_WIN
from .synth_b5 import PSK8, _S4285_SYNC, _finish, fsk, rrc

NEW_CLASSES = ["stanag4539", "stanag4529", "ale3g", "link11_slew", "stanag4481"]

FC = 1800.0


def serial(symbols, baud, fc, beta):
    sps = FS // baud
    h = rrc(beta, sps)
    up = np.zeros(len(symbols) * sps, complex)
    up[::sps] = symbols
    bb = np.convolve(up, h, mode="same")
    return np.real(bb * np.exp(2j * np.pi * fc * np.arange(len(bb)) / FS))


def qam(m):
    """Unit-power constellation: square for 16/64, cross for 32."""
    if m == 32:
        k = np.arange(-5, 6, 2)
        pts = np.array([a + 1j * b for a in k for b in k if not (abs(a) == 5 and abs(b) == 5)])
    else:
        k = np.arange(-(int(np.sqrt(m)) - 1), int(np.sqrt(m)), 2)
        pts = np.array([a + 1j * b for a in k for b in k])
    return pts / np.sqrt(np.mean(np.abs(pts) ** 2))


CONST = {"QPSK": np.exp(2j * np.pi * (np.arange(4) + 0.5) / 4), "8PSK": PSK8,
         "16QAM": qam(16), "32QAM": qam(32), "64QAM": qam(64), "BPSK": np.array([1, -1], complex)}

_FIX = np.random.default_rng(4539)
_4539_PROBE = PSK8[_FIX.integers(0, 8, 31)]
_4539_PRE = PSK8[_FIX.integers(0, 8, 576)]
S4539_RATES = {3200: "QPSK", 4800: "8PSK", 6400: "16QAM", 8000: "32QAM", 9600: "64QAM", 12800: "64QAM"}


def gen_stanag4539(rng, snr_db):
    rate = int(rng.choice(list(S4539_RATES)))
    c = CONST[S4539_RATES[rate]]
    n_fr = int(30 * 2400 / 287)
    body = np.concatenate([np.concatenate([c[rng.integers(0, len(c), 256)], _4539_PROBE]) for _ in range(n_fr)])
    off = float(rng.uniform(-50, 50))
    x = serial(np.concatenate([_4539_PRE, body]), 2400, FC + off, 0.15)
    return _finish(rng, x, snr_db, dict(submode=f"{rate} bit/s {S4539_RATES[rate]}", centre=FC + off))


_4529_SCR = np.random.default_rng(4529).integers(0, 8, 176)


def gen_stanag4529(rng, snr_db):
    mod = str(rng.choice(["BPSK", "QPSK", "8PSK"]))
    step = {"BPSK": 4, "QPSK": 2, "8PSK": 1}[mod]
    out = []
    for _ in range(int(30 / 0.21333)):
        body = []
        for k in range(4):
            body.append(rng.integers(0, 8 // step, 32) * step)
            if k < 3:
                body.append(np.zeros(16, int))
        body = (np.concatenate(body) + _4529_SCR) % 8
        out += [_S4285_SYNC, PSK8[body]]
    off = float(rng.uniform(-50, 50))
    x = serial(np.concatenate(out), 1200, FC + off, 0.05)
    return _finish(rng, x, snr_db, dict(submode=mod, centre=FC + off))


# ------------------------------------------------------------------ 3G ALE
_A = np.random.default_rng(4538)
_TLC = PSK8[_A.integers(0, 8, 256)]
_PRE = {k: PSK8[_A.integers(0, 8, n)] for k, n in
        dict(BW0=384, BW1=576, BW2=64, BW3=640, BW5=576).items()}
_BW3_KNOWN = PSK8[_A.integers(0, 8, 16)]


def ale3g_burst(rng, bw, n=None):
    """Symbols of one burst; lengths from the sigidwiki waveform table (2400 Bd)."""
    total = {"BW0": 1472, "BW1": 3136, "BW4": 1536, "BW5": 2432}.get(bw)
    if bw == "BW2":
        total = 1536 + 960 * n
    pre = _PRE.get(bw, np.zeros(0, complex))
    if bw == "BW3":
        data = np.concatenate([np.concatenate([PSK8[rng.integers(0, 8, 16)], _BW3_KNOWN]) for _ in range(n)])
    else:
        data = PSK8[rng.integers(0, 8, total - 256 - len(pre))]
    return np.concatenate([_TLC, pre, data])


def gen_ale3g(rng, snr_db):
    off = float(rng.uniform(-50, 50))
    g = [1.0, 10 ** (-rng.uniform(0, 12) / 20)]
    if rng.random() < 0.5:
        g = g[::-1]
    seq = [("BW5" if rng.random() < 0.3 else "BW0", 0, None), ("BW0", 1, None), ("BW0", 0, None)]
    traffic = rng.choice(["HDL", "LDL", "none"], p=[0.35, 0.45, 0.2])
    for _ in range(12):
        if traffic == "HDL":
            seq += [("BW2", 0, int(rng.choice([3, 6, 12, 24]))), ("BW1", 1, None)]
        elif traffic == "LDL":
            seq += [("BW3", 0, int(rng.choice([64, 128, 256, 512]))), ("BW4", 1, None)]
    x = np.zeros(int(40 * FS))
    t = float(rng.uniform(0, 1))
    for bw, who, n in seq:
        b = g[who] * serial(ale3g_burst(rng, bw, n), 2400, FC + off, 0.15)
        a = int(t * FS)
        if a >= len(x):
            break
        x[a:a + len(b)] = b[:len(x) - a]
        t += len(b) / FS + float(rng.uniform(0.1, 0.6))
    x = x[: max(int(t * FS), N_WIN)]
    # the window should hold the link setup sometimes, traffic other times
    s = int(rng.integers(0, max(1, len(x) - N_WIN)))
    return _finish(rng, x[s:s + N_WIN], snr_db, dict(submode=str(traffic), centre=FC + off))


# ------------------------------------------------------------------ Link-11 SLEW
def gen_link11_slew(rng, snr_db):
    off = float(rng.uniform(-50, 50))
    x = np.zeros(N_WIN)
    t = float(rng.uniform(-1, 0.5))
    while t < 15:
        d = float(rng.uniform(0.1, 2.0))
        b = serial(PSK8[rng.integers(0, 8, int(d * 2400))], 2400, FC + off, 0.15)
        b *= 10 ** (-rng.uniform(0, 10) / 20)
        a = int(t * FS)
        lo, hi = max(0, a), min(N_WIN, a + len(b))
        if hi > lo:
            x[lo:hi] = b[lo - a:hi - a]
        t += d + float(rng.uniform(0.004, 0.15))
    return _finish(rng, x, snr_db, dict(centre=FC + off))


# ------------------------------------------------------------------ STANAG 4481 FSK
def gen_stanag4481(rng, snr_db):
    baud = int(rng.choice([75, 100, 150, 300, 600]))
    fc = 1700.0 + float(rng.uniform(-100, 100))
    x = fsk(rng.integers(0, 2, int(16 * baud)), baud, fc - 425, fc + 425)[:N_WIN]
    return _finish(rng, x, snr_db, dict(submode=f"{baud}Bd/850Hz", centre=fc))


GENERATORS = dict(stanag4539=gen_stanag4539, stanag4529=gen_stanag4529, ale3g=gen_ale3g,
                  link11_slew=gen_link11_slew, stanag4481=gen_stanag4481)
