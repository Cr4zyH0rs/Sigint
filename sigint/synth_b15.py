"""Batch 15 generators: digital voice systems heard through an FM receiver (IC-7100 in FM mode).
ID-only: every payload bit is random, nothing is vocoded, encoded to a real call or decoded.

An FM receiver's audio is its discriminator output, i.e. the transmitter's frequency deviation
over time, after the receiver's audio stages. So each generator builds the baseband deviation
signal (4-level FSK or GMSK) with the published frame structure and sync words, then passes it
through the same assumed receiver audio chain as POCSAG in batch 14 (sigint/synth_b14.py).

Sources (read 2026-11-25):
  DMR      4FSK, 4800 symbols/s, 9600 bit/s (https://en.wikipedia.org/wiki/Digital_mobile_radio);
           30 ms timeslot, 60 ms frame, 360 ms voice superframe of 6 bursts A-F, burst = two
           108-bit payload fields + 48-bit sync or signalling field (264 bits), CACH 24 bits,
           12.5 kHz, 2 TDMA slots, different SYNC patterns for voice and data
           (https://www.etsi.org/deliver/etsi_ts/102300_102399/10236101/02.06.01_60/ts_10236101v020601p.pdf);
           frame 60 ms / slot 30 ms (https://www.sigidwiki.com/wiki/Digital_Mobile_Radio_(DMR)).
  P25 Ph1  C4FM, 4800 Bd, 2 bit/symbol, 9600 bit/s, 12.5 kHz, NAC 12 bits
           (https://en.wikipedia.org/wiki/Project_25, https://www.sigidwiki.com/wiki/Project_25_(P25)).
  D-STAR   GMSK (https://www.sigidwiki.com/wiki/D-STAR), "minimum-shift keying", 4800 bit/s on
           air, 3600 bit/s voice + 1200 FEC... (https://en.wikipedia.org/wiki/D-STAR); 20 ms frames,
           420 ms superframe, 6.25 kHz (sigidwiki).
  YSF      Yaesu System Fusion: C4FM, 12.5 kHz, AMBE+2 (https://www.sigidwiki.com/wiki/Yaesu_System_Fusion).
  NXDN     NXDN48: 2400 Bd, 4800 bit/s, 6.25 kHz, 4FSK; ACF 80 ms
           (https://www.sigidwiki.com/wiki/Next_Generation_Digital_Narrowband_(NXDN),
           https://en.wikipedia.org/wiki/NXDN).
  MMDVM    The open-source MMDVM modem firmware and MMDVMHost (G4KLX, GPL), read 2026-11-25, give
           what the pages above do not:
             https://github.com/g4klx/MMDVM/blob/master/DMRDefines.h   DMR sync words (48 bits):
                 BS voice 0x755FD7DF75F7, BS data 0xDFF57D75DF5D, MS voice 0x7F7D5DD57DFD,
                 MS data 0xD5D7F77FD757; symbol values, e.g. MS voice = +3 -3 -3 -3 +3 ...
                 (so dibit 01 = +3, 00 = +1, 10 = -1, 11 = -3); burst 264 bits = 132 symbols;
                 EMB 8 + embedded signalling 16 symbols in place of the sync; CACH 12 symbols.
             .../MMDVM/blob/master/DMRTX.cpp, YSFTX.cpp  root-raised-cosine, roll-off 0.2
                 ("rcosdesign(0.2, 8, 5, 'sqrt')"); levels 1362/454 (DMR), 1893/631 and 948/316
                 (YSF high / low deviation).
             .../MMDVM/blob/master/P25TX.cpp  raised cosine (not root) 0.2 + low-pass; levels 1260/420;
                 0x77 bytes during the TX delay.
             .../MMDVMHost/blob/master/P25Defines.h  sync 0x5575F5FF77FF (48 bits); header 99 bytes,
                 LDU 216 bytes, terminator 18 bytes, terminator with LC 54 bytes, TSDU 45 bytes.
             .../MMDVM/blob/master/DStarTX.cpp  Gaussian filter "gaussfir(0.35, 1, 5)" (BT 0.35);
                 bit sync 0xAA during the TX delay; frame sync bytes EA A6 00; bytes sent LSB first,
                 bit 1 = negative level; header FEC section 660 bits.
             .../MMDVMHost/blob/master/DStarDefines.h  voice frame 9 + 3 data bytes, slow-data sync
                 55 2D 16 (every 21st frame, which gives the 420 ms superframe); end pattern
                 55 55 55 55 C8 7A.
             .../MMDVMHost/blob/master/YSFDefines.h  frame 120 bytes, sync 0xD471C9634D (40 bits);
                 .../MMDVM/blob/master/YSFDefines.h  FICH 200 bits.
             .../MMDVM/blob/master/NXDNDefines.h  frame 384 bits (192 symbols at 2400 Bd = 80 ms,
                 matching the 80 ms ACF), frame sync word 0xCDF59 (20 bits); NXDNTX.cpp RRC 0.2,
                 levels 735/245, preamble 57 75 FD.
           Deviation (inferred, not needed by the model because each window is normalised): MSK
           means h = 0.5, so D-STAR at 4800 bit/s deviates +-1200 Hz; MMDVM's D-STAR level is 841,
           so 1.427 Hz per level unit, giving DMR +-1944/648 Hz, P25 +-1798/599 Hz, YSF +-2701/900 Hz
           (high) and NXDN +-1049/350 Hz. NXDN's +-350 Hz matches sigidwiki's NXDN96 table.

ASSUMED (not stated in those sources):
  - Receiver audio chain as for POCSAG (batch 14): random low cut 20-300 Hz, 3000 Hz high cut,
    6 dB/octave de-emphasis above 300 Hz in half the windows. The discriminator polarity is not
    published for the IC-7100, so the sign is random.
  - Carrier-off time is silent; the real rig with the squelch open would give FM noise there.
  - All payload, EMB, CACH, NID (apart from a fixed per-window NAC), FICH and header bits random.
    P25 status symbols are not inserted.
  - Traffic: DMR is a repeater (both slots, continuous while keyed; idle slot carries data-sync
    bursts) in 60% of windows and direct mode (one 27.5 ms burst every 60 ms) in 40%. P25 and NXDN
    are a continuous control channel in 25% of windows, otherwise voice overs. Overs last 1.5-10 s
    with 0.3-4 s gaps. An MMDVM-style TX-delay preamble (0-0.3 s) starts half of the overs.
"""
from __future__ import annotations

import numpy as np
from scipy import signal as sps

from .synth import FS, N_WIN
from .synth_b5 import _finish
from .synth_b14 import _deemph

NEW_CLASSES = ["dmr", "p25", "dstar", "ysf", "nxdn"]

FS48 = 48000
DUR = 15.5                     # seconds generated before the window is cut

# dibit -> level, from MMDVM's DMR symbol tables (01 = +3, 00 = +1, 10 = -1, 11 = -3)
_LVL = {0b01: 3.0, 0b00: 1.0, 0b10: -1.0, 0b11: -3.0}


def bits_to_syms(value: int, nbits: int) -> np.ndarray:
    return np.array([_LVL[(value >> (nbits - 2 - 2 * i)) & 3] for i in range(nbits // 2)])


def bytes_to_syms(bs) -> np.ndarray:
    return np.concatenate([bits_to_syms(b, 8) for b in bs])


def rand_syms(rng, n):
    return rng.choice([3.0, 1.0, -1.0, -3.0], int(n))


def rcos(beta, sps_, span=8, root=True):
    t = (np.arange(span * sps_ + 1) - span * sps_ / 2) / sps_
    if root:
        h = np.zeros_like(t)
        for i, ti in enumerate(t):
            if abs(ti) < 1e-9:
                h[i] = 1 - beta + 4 * beta / np.pi
            elif abs(abs(4 * beta * ti) - 1) < 1e-9:
                h[i] = beta / np.sqrt(2) * ((1 + 2 / np.pi) * np.sin(np.pi / (4 * beta))
                                            + (1 - 2 / np.pi) * np.cos(np.pi / (4 * beta)))
            else:
                h[i] = (np.sin(np.pi * ti * (1 - beta)) + 4 * beta * ti * np.cos(np.pi * ti * (1 + beta))) \
                    / (np.pi * ti * (1 - (4 * beta * ti) ** 2))
    else:
        h = np.sinc(t) * np.cos(np.pi * beta * t) / np.maximum(1 - (2 * beta * t) ** 2, 1e-9)
        h[np.abs(1 - (2 * beta * t) ** 2) < 1e-9] = np.pi / 4 * np.sinc(1 / (2 * beta))
    return h / np.sum(h)


def gauss(bt, sps_, span=4):
    t = (np.arange(span * sps_ + 1) - span * sps_ / 2) / sps_
    a = np.sqrt(np.log(2) / 2) / bt
    h = np.sqrt(np.pi) / a * np.exp(-(np.pi * t / a) ** 2)
    return h / np.sum(h)


def shape(syms, baud, h):
    """Symbol-rate levels (0 = carrier off) -> 48 kHz deviation signal."""
    sps_ = FS48 // baud
    up = np.zeros(len(syms) * sps_)
    up[::sps_] = syms
    on = np.repeat(np.asarray(syms) != 0, sps_).astype(float)
    y = np.convolve(up, h * sps_, mode="same")
    # NRZ-style hold so carrier-off stretches stay at zero and carrier-on ones keep the pulse shape
    return y * np.convolve(on, np.ones(sps_) / sps_, mode="same").clip(0, 1)


def rx_chain(rng, x48):
    """Assumed IC-7100 FM audio chain (see module docstring); returns 12 kHz audio + description."""
    lo = float(np.exp(rng.uniform(np.log(20), np.log(300))))
    deem = bool(rng.random() < 0.5)
    if deem:
        b, a = sps.butter(1, 300.0, fs=FS48)
        x48 = sps.lfilter(b, a, x48)
    x48 = sps.sosfilt(sps.butter(4, [lo, 3000], "bandpass", fs=FS48, output="sos"), x48)
    x = sps.resample_poly(x48, 1, FS48 // FS)
    return x, f"low cut {lo:.0f} Hz{', de-emphasis' if deem else ''}"


def schedule(rng, baud, make_over, cont_prob=0.0, make_cont=None):
    """Lay overs (symbol arrays) on a DUR-second symbol grid; 0 = carrier off."""
    n = int(DUR * baud)
    out = np.zeros(n)
    if make_cont is not None and rng.random() < cont_prob:
        seg = make_cont(rng, n)
        out[:] = seg[:n]
        return out, "control channel"
    t = int(rng.uniform(-3, 2) * baud)
    while t < n:
        over = make_over(rng, float(rng.uniform(1.5, 10)))
        lo, hi = max(t, 0), min(n, t + len(over))
        if hi > lo:
            out[lo:hi] = over[lo - t:hi - t]
        t += len(over) + int(rng.uniform(0.3, 4) * baud)
    if not np.any(out):
        over = make_over(rng, 3.0)
        out[baud:baud + len(over)] = over[:n - baud]
    return out, "voice overs"


def preamble(rng, baud, byte):
    if rng.random() < 0.5:
        return np.zeros(0)
    return np.tile(bits_to_syms(byte, 8), int(rng.uniform(0, 0.3) * baud / 4) + 1)


def finish(rng, syms, baud, h, snr_db, sub):
    x48 = shape(syms, baud, h) * float(rng.choice([-1.0, 1.0]))
    x, rxd = rx_chain(rng, x48)
    s = int(rng.integers(0, max(1, len(x) - N_WIN)))
    return _finish(rng, x[s:s + N_WIN], snr_db, dict(submode=f"{sub}, {rxd}", centre=None))


# ------------------------------------------------------------------ DMR
DMR_SYNC = dict(bs_voice=0x755FD7DF75F7, bs_data=0xDFF57D75DF5D,
                ms_voice=0x7F7D5DD57DFD, ms_data=0xD5D7F77FD757)
_RRC5 = rcos(0.2, 10)          # 4800 Bd at 48 kHz = 10 samples/symbol


def dmr_burst(rng, mid):
    return np.concatenate([rand_syms(rng, 54), mid, rand_syms(rng, 54)])


def dmr_slot_bursts(rng, n_bursts, kind, voice=True):
    """kind 'bs' or 'ms'. Voice: 1-3 LC header bursts (data sync), superframes, terminator."""
    sv, sd = bits_to_syms(DMR_SYNC[kind + "_voice"], 48), bits_to_syms(DMR_SYNC[kind + "_data"], 48)
    if not voice:
        return [dmr_burst(rng, sd) for _ in range(n_bursts)]
    out = [dmr_burst(rng, sd) for _ in range(int(rng.integers(1, 4)))]
    k = 0
    while len(out) < n_bursts - 1:
        out.append(dmr_burst(rng, sv if k % 6 == 0 else rand_syms(rng, 24)))
        k += 1
    out.append(dmr_burst(rng, sd))
    return out[:n_bursts]


def dmr_repeater_over(rng, seconds):
    n = int(seconds / 0.06)
    s1 = dmr_slot_bursts(rng, n, "bs")
    s2 = dmr_slot_bursts(rng, n, "bs", voice=bool(rng.random() < 0.4))
    seq = []
    for a, b in zip(s1, s2):
        seq += [rand_syms(rng, 12), a, rand_syms(rng, 12), b]      # CACH + burst, 30 ms each
    return np.concatenate(seq)


def dmr_direct_over(rng, seconds):
    n = int(seconds / 0.06)
    seq = [preamble(rng, 4800, 0x77)]
    for b in dmr_slot_bursts(rng, n, "ms"):
        seq += [b, np.zeros(156)]                                  # 27.5 ms on, 32.5 ms off
    return np.concatenate(seq)


def gen_dmr(rng, snr_db):
    rep = rng.random() < 0.6
    syms, sub = schedule(rng, 4800, dmr_repeater_over if rep else dmr_direct_over)
    return finish(rng, syms, 4800, _RRC5, snr_db, ("repeater" if rep else "direct") + " " + sub)


# ------------------------------------------------------------------ P25 phase 1
P25_SYNC = bits_to_syms(0x5575F5FF77FF, 48)
_RC5 = rcos(0.2, 10, root=False)


def p25_frame(rng, nac_syms, nbytes):
    body = rand_syms(rng, nbytes * 4 - 24 - 6)
    return np.concatenate([P25_SYNC, nac_syms, body])


def p25_over(rng, seconds, nac):
    seq = [preamble(rng, 4800, 0x77), p25_frame(rng, nac, 99)]
    for _ in range(max(1, int(seconds / 0.18))):
        seq.append(p25_frame(rng, nac, 216))
    seq.append(p25_frame(rng, nac, int(rng.choice([18, 54]))))
    return np.concatenate(seq)


def gen_p25(rng, snr_db):
    nac = rand_syms(rng, 6)                                        # 12-bit NAC, fixed per window
    syms, sub = schedule(rng, 4800, lambda r, s: p25_over(r, s, nac), 0.25,
                         lambda r, n: np.concatenate([p25_frame(r, nac, 45) for _ in range(n // 180 + 1)]))
    return finish(rng, syms, 4800, _RC5, snr_db, sub)


# ------------------------------------------------------------------ D-STAR
def lsb_bits(bs):
    return [(b >> i) & 1 for b in bs for i in range(8)]


_GAUSS = gauss(0.35, 10)
_DS_SYNC = lsb_bits([0x55, 0x2D, 0x16])
_DS_END = lsb_bits([0x55, 0x55, 0x55, 0x55, 0xC8, 0x7A])
_DS_FS = lsb_bits([0xEA, 0xA6])[:15]


def dstar_over(rng, seconds):
    bits = []
    if rng.random() < 0.5:
        bits += lsb_bits([0xAA] * int(rng.integers(8, 60)))
    else:
        bits += [1, 0] * int(rng.integers(32, 64))
    bits += _DS_FS + list(rng.integers(0, 2, 660))
    for k in range(max(21, int(seconds / 0.02))):
        bits += list(rng.integers(0, 2, 72))
        bits += _DS_SYNC if k % 21 == 0 else list(rng.integers(0, 2, 24))
    bits += _DS_END
    return np.where(np.array(bits) == 1, -1.0, 1.0)                 # bit 1 = negative level


def gen_dstar(rng, snr_db):
    syms, sub = schedule(rng, 4800, dstar_over)
    return finish(rng, syms, 4800, _GAUSS, snr_db, sub)


# ------------------------------------------------------------------ Yaesu System Fusion
YSF_SYNC = bits_to_syms(0xD471C9634D, 40)


def ysf_over(rng, seconds):
    seq = [preamble(rng, 4800, 0x77)]
    for _ in range(max(2, int(seconds / 0.1))):
        seq += [YSF_SYNC, rand_syms(rng, 480 - 20)]
    return np.concatenate(seq)


def gen_ysf(rng, snr_db):
    syms, sub = schedule(rng, 4800, ysf_over)
    return finish(rng, syms, 4800, _RRC5, snr_db, sub)


# ------------------------------------------------------------------ NXDN48
NXDN_FSW = bits_to_syms(0xCDF59, 20)
_RRC10 = rcos(0.2, 20)          # 2400 Bd at 48 kHz = 20 samples/symbol


def nxdn_frames(rng, n):
    return np.concatenate([np.concatenate([NXDN_FSW, rand_syms(rng, 182)]) for _ in range(n)])


def nxdn_over(rng, seconds):
    pre = bytes_to_syms([0x57, 0x75, 0xFD]) if rng.random() < 0.5 else np.zeros(0)
    return np.concatenate([pre, nxdn_frames(rng, max(2, int(seconds / 0.08)))])


def gen_nxdn(rng, snr_db):
    syms, sub = schedule(rng, 2400, nxdn_over, 0.25, lambda r, n: nxdn_frames(r, n // 192 + 1))
    return finish(rng, syms, 2400, _RRC10, snr_db, "NXDN48 " + sub)


GENERATORS = dict(dmr=gen_dmr, p25=gen_p25, dstar=gen_dstar, ysf=gen_ysf, nxdn=gen_nxdn)
