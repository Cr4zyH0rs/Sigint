"""Batch 14 generators: VHF/UHF FM signals the IC-7100 can receive (ID-only: every payload is
random, nothing here decodes anything).

IC-7100 (read 2026-11-24): receive 0.030-199.999 MHz and 400.000-470.000 MHz; modes include FM,
DV (D-STAR) and WFM (https://icomamerica.com/lineup/products/IC-7100USA/). FM selectivity
>12 kHz at -6 dB (https://www.qsl.net/ab4oj/icom/ic7100/IC-7100_USA.pdf). With ACC/USB Output
Select = AF, the USB connector carries "the received audio"
(https://www.manualslib.com/manual/1419805/Icom-Ic-7100.html?page=190); 9600 bps data is only on
DATA2 pin 3 (https://www.manualslib.com/manual/834640/Icom-Ic-7100.html?page=338). So the model
sees ordinary FM receiver audio, and only modes that live in the voice band are built here.

Sources:
  APRS     Bell 202 AFSK, 1200 Hz mark / 2200 Hz space, 1200 bit/s
           (https://en.wikipedia.org/wiki/Bell_202_modem); AX.25 at 1200 Bd Bell 202, NRZI
           (https://en.wikipedia.org/wiki/AX.25); 144.390 MHz N. America, 144.800 MHz Europe
           (https://www.sigidwiki.com/wiki/APRS). Audio from Dire Wolf's own modulator
           (gen_packets, Debian package direwolf 1.7).
  POCSAG   preamble of 1010... for at least 576 bits; batch = sync codeword 0x7CD215D8 + 8 frames
           of 2 codewords; 32-bit codewords, 21 information + 10 BCH + 1 parity bits; address
           codewords start with 0, message codewords with 1
           (https://www.itu.int/dms_pubrec/itu-r/rec/m/R-REC-M.584-2-199711-I!!PDF-E.pdf);
           idle codeword 0x7A89C197 (https://en.wikipedia.org/wiki/POCSAG); 512/1200/2400 bit/s,
           FSK, "+4.5 kHz represents a 0" (https://www.sigidwiki.com/wiki/POCSAG).
  SAME     520.83 bit/s, mark 2083.3 Hz, space 1562.5 Hz; preamble 16 bytes of 0xAB; header and
           EOM "NNNN" each sent 3 times with 1 s pauses; EAS attention signal 853 + 960 Hz for
           8-25 s (https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-11/subpart-B/section-11.31);
           NOAA Weather Radio 1050 Hz tone (https://en.wikipedia.org/wiki/Specific_Area_Message_Encoding).
           AFSK from minimodem's "same" mode (Debian package minimodem 0.24).
  MDC-1200 1200 Bd AFSK, mark/space 1200 / 1800 Hz, bursts on the voice channel
           (https://en.wikipedia.org/wiki/MDC-1200).
  CCIR     5-tone selcall, CCIR-1 100 ms and CCIR-2 70 ms per tone, tones 0=1981 1=1124 2=1197
  selcall  3=1275 4=1358 5=1446 6=1540 7=1640 8=1747 9=1860 E=2110 Hz
           (https://www.sigidwiki.com/wiki/CCIR_Selcall).

ASSUMED (not stated in those sources):
  - Receiver audio: 300-3000 Hz pass band (4th-order Butterworth). POCSAG is direct FSK, so the
    receiver's low-frequency response decides what is left of it; that response is not published,
    so its low cut is random between 20 and 300 Hz (3000 Hz high cut), with a 6 dB/octave
    de-emphasis above 300 Hz in half the windows. An independent decoder (multimon-ng) still reads
    the pages with the de-emphasis alone but not with a 300 Hz low cut (results/verify_b14_seed14.json). Modes sent as audio tones (APRS, SAME, MDC, selcall) are
    pre-emphasised and de-emphasised, so they are taken as flat.
  - APRS: 1-8 packets per window from different stations (levels within 10 dB), random calls and
    position text, digipeated copies 0.3-2 s later in 40% of packets.
  - POCSAG: 1-8 batches per transmission, 1-6 transmissions per window, gaps 0.3-4 s; random
    addresses and message bits; BCH(31,21) generator x^10+x^9+x^8+x^6+x^5+x^3+1.
  - SAME: random but well-formed header text; 1-4 s of silence in place of the voice message;
    the window is placed so it holds at least one header, attention tone or EOM.
  - MDC-1200: preamble 24 bits of 1010, a fixed 40-bit sync word, 112 random data bits; bursts
    at the start and/or end of 2-6 s voice overs (espeak-ng speech).
  - Selcall: E replaces a repeated digit; 1-4 calls per window, sometimes followed by speech.
"""
from __future__ import annotations

import os
import subprocess
import tempfile

import numpy as np
import soundfile as sf
from scipy import signal as sps

from .synth import FS, N_WIN, random_call
from .synth_b5 import _finish

NEW_CLASSES = ["aprs", "pocsag", "same", "mdc1200", "selcall_ccir"]

_BP = sps.butter(4, [300, 3000], "bandpass", fs=FS, output="sos")


def fm_audio(x):
    return sps.sosfilt(_BP, x)


def _deemph(x, f0=300.0):
    b, a = sps.butter(1, f0, fs=FS)       # 6 dB/octave above f0
    return sps.lfilter(b, a, x)


def _place(out, b, t):
    a = int(t * FS)
    lo, hi = max(0, a), min(len(out), a + len(b))
    if hi > lo:
        out[lo:hi] += b[lo - a:hi - a]


def afsk(bits, baud, f_mark, f_space):
    sps_ = FS / baud
    n = int(round(len(bits) * sps_))
    idx = np.minimum((np.arange(n) / sps_).astype(int), len(bits) - 1)
    f = np.where(np.asarray(bits)[idx] == 1, f_mark, f_space)
    return np.sin(np.cumsum(2 * np.pi * f / FS))


def speech(rng, seconds):
    words = " ".join(rng.choice(["unit", "copy", "en route", "standby", "affirmative", "location",
                                 "check", "over", "received", "go ahead", "clear"], int(seconds * 2.5)))
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "v.wav")
        subprocess.run(["espeak-ng", "-v", str(rng.choice(["en-us", "en", "en+f3", "en+m3"])),
                        "-s", str(int(rng.integers(140, 190))), "-w", p, words],
                       check=True, capture_output=True, timeout=30)
        x, fs = sf.read(p, dtype="float64")
    x = sps.resample_poly(x if x.ndim == 1 else x.mean(1), FS, fs)[:int(seconds * FS)]
    return x / (np.std(x) + 1e-12) * 0.5


# ------------------------------------------------------------------ APRS (Dire Wolf)
def aprs_packet(rng):
    call = random_call(rng)
    ssid = "" if rng.random() < 0.4 else f"-{int(rng.integers(1, 16))}"
    lat = f"{int(rng.integers(0, 90)):02d}{rng.uniform(0, 60):05.2f}{rng.choice(['N', 'S'])}"
    lon = f"{int(rng.integers(0, 180)):03d}{rng.uniform(0, 60):05.2f}{rng.choice(['E', 'W'])}"
    text = "".join(rng.choice(list("abcdefghijklmnopqrstuvwxyz0123456789 "), int(rng.integers(0, 40))))
    line = f"{call}{ssid}>APRS,WIDE1-1,WIDE2-1:!{lat}/{lon}>{text}\n"
    with tempfile.TemporaryDirectory() as d:
        src, wav = os.path.join(d, "p.txt"), os.path.join(d, "p.wav")
        open(src, "w").write(line)
        subprocess.run(["gen_packets", "-r", str(FS), "-o", wav, src], check=True, capture_output=True)
        x, _ = sf.read(wav, dtype="float64")
    return x / (np.std(x[np.abs(x) > 1e-4]) + 1e-12)


def gen_aprs(rng, snr_db):
    x = np.zeros(N_WIN)
    t = float(rng.uniform(-0.5, 3))
    for _ in range(int(rng.integers(1, 9))):
        if t > 14.5:
            break
        p = aprs_packet(rng) * 10 ** (-rng.uniform(0, 10) / 20)
        _place(x, p, t)
        end = t + len(p) / FS
        if rng.random() < 0.4:                         # digipeated copy
            t2 = end + float(rng.uniform(0.3, 2))
            _place(x, p * 10 ** (-rng.uniform(0, 10) / 20), t2)
            end = t2 + len(p) / FS
        t = end + float(rng.uniform(0.2, 4))
    if not np.any(x):
        _place(x, aprs_packet(rng), 1.0)
    return _finish(rng, fm_audio(x), snr_db, dict(centre=1700.0))


# ------------------------------------------------------------------ POCSAG
SYNC, IDLE = 0x7CD215D8, 0x7A89C197
_GEN = 0b11101101001          # x^10+x^9+x^8+x^6+x^5+x^3+1


def bch_word(info21: int) -> int:
    r = info21 << 10
    for i in range(30, 9, -1):
        if r >> i & 1:
            r ^= _GEN << (i - 10)
    cw = (info21 << 10 | r) << 1
    return cw | (bin(cw).count("1") & 1)              # even parity


def pocsag_bits(rng, n_batches):
    bits = [i & 1 ^ 1 for i in range(576)]           # 1010...
    words = []
    while len(words) < 16 * n_batches:
        addr = int(rng.integers(0, 2 ** 21))
        frame = addr & 7
        while len(words) % 16 != 2 * frame:
            words.append(IDLE)
        words.append(bch_word((addr >> 3) << 2 | int(rng.integers(0, 4))))
        for _ in range(int(rng.integers(0, 8))):
            words.append(bch_word(1 << 20 | int(rng.integers(0, 2 ** 20))))
    words = words[:16 * n_batches]
    for b in range(n_batches):
        for w in [SYNC] + words[16 * b:16 * b + 16]:
            bits += [(w >> (31 - i)) & 1 for i in range(32)]
    return np.array(bits)


def gen_pocsag(rng, snr_db):
    baud = int(rng.choice([512, 1200, 2400]))
    x = np.zeros(N_WIN)
    t = float(rng.uniform(-1, 2))
    for _ in range(int(rng.integers(1, 7))):
        if t > 14.5:
            break
        bits = pocsag_bits(rng, int(rng.integers(1, 9)))
        n = int(round(len(bits) * FS / baud))
        lvl = np.where(bits[np.minimum((np.arange(n) * baud / FS).astype(int), len(bits) - 1)] == 0, 1.0, -1.0)
        _place(x, lvl, t)
        t += n / FS + float(rng.uniform(0.3, 4))
    if not np.any(x):
        bits = pocsag_bits(rng, 2)
        n = int(round(len(bits) * FS / baud))
        _place(x, np.where(bits[np.minimum((np.arange(n) * baud / FS).astype(int), len(bits) - 1)] == 0, 1.0, -1.0), 1.0)
    lo = float(np.exp(rng.uniform(np.log(20), np.log(300))))
    deem = rng.random() < 0.5
    if deem:
        x = _deemph(x)
    x = sps.sosfilt(sps.butter(4, [lo, 3000], "bandpass", fs=FS, output="sos"), x)
    return _finish(rng, x, snr_db, dict(submode=f"{baud} bit/s, low cut {lo:.0f} Hz{', de-emphasis' if deem else ''}", centre=None))


# ------------------------------------------------------------------ SAME (minimodem)
def same_burst(text: str) -> np.ndarray:
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "s.wav")
        p = subprocess.run(["minimodem", "--tx", "same", "-R", str(FS), "-f", wav],
                           input=(b"\xab" * 16) + text.encode(), capture_output=True, check=True)
        x, _ = sf.read(wav, dtype="float64")
    return x / (np.std(x) + 1e-12)


EVENTS = ["RWT", "RMT", "TOR", "SVR", "FFW", "WSW", "SPS", "CEM", "EAN", "DMO"]


def same_header(rng):
    org = str(rng.choice(["WXR", "EAS", "CIV", "PEP"]))
    areas = "-".join(f"{int(rng.integers(0, 10))}{int(rng.integers(1, 57)):02d}{int(rng.integers(1, 1000)):03d}"
                     for _ in range(int(rng.integers(1, 5))))
    dur = str(rng.choice(["0015", "0030", "0100", "0200"]))
    stn = "".join(rng.choice(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ/"), 8))
    return org, f"ZCZC-{org}-{rng.choice(EVENTS)}-{areas}+{dur}-{int(rng.integers(1, 366)):03d}{int(rng.integers(0, 24)):02d}{int(rng.integers(0, 60)):02d}-{stn}-"


def gen_same(rng, snr_db):
    org, hdr = same_header(rng)
    h, e = same_burst(hdr), same_burst("NNNN")
    sil = lambda s: np.zeros(int(s * FS))
    t = np.arange(int(rng.uniform(8, 25) * FS)) / FS
    if org == "WXR" and rng.random() < 0.5:
        att = np.sin(2 * np.pi * 1050 * t)
    else:
        att = (np.sin(2 * np.pi * 853 * t) + np.sin(2 * np.pi * 960 * t)) / np.sqrt(2)
    parts = [h, sil(1), h, sil(1), h, sil(1), att, sil(float(rng.uniform(1, 4))), e, sil(1), e, sil(1), e]
    seq = np.concatenate(parts)
    s = int(rng.integers(-2 * FS, len(seq) - 3 * FS))
    out = np.zeros(N_WIN)
    _place(out, seq, -s / FS)
    return _finish(rng, fm_audio(out), snr_db, dict(submode=f"{org}", centre=None))


# ------------------------------------------------------------------ MDC-1200
_MDC_SYNC = np.random.default_rng(1200).integers(0, 2, 40)


def mdc_burst(rng):
    bits = np.concatenate([np.arange(24) % 2, _MDC_SYNC, rng.integers(0, 2, 112)])
    return afsk(bits, 1200, 1200.0, 1800.0)


def gen_mdc1200(rng, snr_db):
    x = np.zeros(N_WIN)
    t = float(rng.uniform(-1, 2))
    while t < 14:
        over = speech(rng, float(rng.uniform(2, 6)))
        where = rng.choice(["pre", "post", "both"], p=[0.5, 0.2, 0.3])
        seg = [mdc_burst(rng)] if where in ("pre", "both") else []
        seg += [np.zeros(int(0.05 * FS)), over]
        if where in ("post", "both"):
            seg += [np.zeros(int(0.05 * FS)), mdc_burst(rng)]
        b = np.concatenate(seg) * 10 ** (-rng.uniform(0, 6) / 20)
        _place(x, b, t)
        t += len(b) / FS + float(rng.uniform(0.5, 3))
    return _finish(rng, fm_audio(x), snr_db, dict(submode=str(where), centre=1500.0))


# ------------------------------------------------------------------ CCIR 5-tone selcall
CCIR = {"0": 1981, "1": 1124, "2": 1197, "3": 1275, "4": 1358, "5": 1446, "6": 1540, "7": 1640,
        "8": 1747, "9": 1860, "E": 2110}


def selcall_tones(digits: str, dur_s: float) -> np.ndarray:
    seq, prev = [], None
    for d in digits:
        seq.append("E" if d == prev else d)
        prev = d
    n = int(dur_s * FS)
    t = np.arange(n) / FS
    return np.concatenate([np.sin(2 * np.pi * CCIR[s] * t) for s in seq])


def gen_selcall_ccir(rng, snr_db):
    dur = 0.1 if rng.random() < 0.5 else 0.07
    x = np.zeros(N_WIN)
    t = float(rng.uniform(0, 3))
    for _ in range(int(rng.integers(1, 5))):
        if t > 14:
            break
        b = selcall_tones("".join(rng.choice(list("0123456789"), 5)), dur)
        if rng.random() < 0.4:
            b = np.concatenate([b, np.zeros(int(0.3 * FS)), speech(rng, float(rng.uniform(1, 4)))])
        _place(x, b, t)
        t += len(b) / FS + float(rng.uniform(0.5, 4))
    return _finish(rng, fm_audio(x), snr_db, dict(submode=f"CCIR-{1 if dur == 0.1 else 2}", centre=1550.0))


GENERATORS = dict(aprs=gen_aprs, pocsag=gen_pocsag, same=gen_same, mdc1200=gen_mdc1200,
                  selcall_ccir=gen_selcall_ccir)
