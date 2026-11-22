"""Synthetic HF test-signal generators (12 kHz, mono, float32).

Every generator returns a clean signal normalised to unit RMS over the part
where the signal is keyed, so add_awgn() can set an SNR the same way WSJT-X
reports it: signal power over noise power in a 2500 Hz reference bandwidth.

References
- FT8 waveform: produced by WSJT-X's own `ft8sim` (Franke, Somerville & Taylor,
  "The FT4 and FT8 Communication Protocols", QEX Jul/Aug 2020).
- PSK31 varicode and BPSK keying: P. Martinez G3PLX, "PSK31: A new radio-teletype
  mode", RadCom Dec 1998 / Jan 1999; table matches fldigi src/psk/pskvaricode.cxx.
- RTTY: ITA2 / US-TTY Baudot, 45.45 Bd, 170 Hz shift, 1 start, 5 data, 1.5 stop
  (ITU-T S.1 / ARRL Handbook, "Digital Modes" chapter).
- CW timing: PARIS standard, dit = 1.2 / WPM seconds (ITU-R M.1677-1).
- SSB voice: espeak-ng text-to-speech, band-limited to 300-2700 Hz.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

import numpy as np
import soundfile as sf
from scipy import signal as sps

FS = 12000
WIN_S = 15.0
N_WIN = int(FS * WIN_S)
CLASSES = ["ft8", "cw", "rtty", "psk31", "ssb", "noise",
           # batch 2 (sigint/synth_wsjt.py)
           "ft4", "js8", "wspr", "jt65", "jt9", "fst4", "q65",
           # batch 3 (sigint/synth_fldigi.py, real fldigi transmissions)
           "olivia", "contestia", "mfsk", "thor", "dominoex", "mt63", "hell", "throb",
           # batch 4 (sigint/synth_b4.py from published specs; sitorb = real fldigi SITOR-B/NAVTEX)
           "sstv", "wefax", "ale", "cw_beacon", "sitorb",
           # batch 5 (sigint/synth_b5.py, from published descriptions)
           "stanag4285", "mil110_serial", "mil110_16tone", "mil110_39tone",
           "pactor1", "pactor2", "pactor3",
           # batch 6 (psk8 = real fldigi 8PSK125/250/500/1000 takes; the rest from
           # published descriptions in sigint/synth_b6.py)
           "psk8", "fsq", "packet", "sitora", "ndb",
           # batch 7 (sigint/synth_b7.py; msk144 = WSJT-X msk144sim)
           "selcal", "dsc", "ccir493", "hfdl", "msk144"]

# --------------------------------------------------------------------------
# Noise / SNR
# --------------------------------------------------------------------------

def add_awgn(x: np.ndarray, snr_db: float, rng: np.random.Generator,
             sig_rms: float | None = None) -> np.ndarray:
    """Add white Gaussian noise so that SNR (in 2500 Hz) == snr_db.

    White noise sampled at FS spreads its power over FS/2 Hz, so the noise
    power that lands in 2500 Hz is total * 2500 / (FS/2) (WSJT-X convention).
    """
    if sig_rms is None:
        sig_rms = float(np.sqrt(np.mean(x[np.abs(x) > 0] ** 2))) if np.any(x) else 1.0
    p_sig = sig_rms ** 2
    p_noise_2500 = p_sig / (10 ** (snr_db / 10))
    p_noise_total = p_noise_2500 * (FS / 2) / 2500.0
    return x + rng.normal(0.0, np.sqrt(p_noise_total), x.shape)


def noise_only(rng: np.random.Generator, n: int = N_WIN) -> np.ndarray:
    """Band noise: white, pink, or white + impulsive QRN, plus optional birdie."""
    kind = rng.integers(3)
    w = rng.normal(0, 1, n)
    if kind == 1:  # pink via 1/f shaping in the frequency domain
        f = np.fft.rfftfreq(n, 1 / FS)
        spec = np.fft.rfft(w) / np.sqrt(np.maximum(f, 1.0))
        w = np.fft.irfft(spec, n)
    elif kind == 2:  # impulsive static crashes
        k = rng.integers(5, 60)
        idx = rng.integers(0, n - 200, k)
        for i in idx:
            w[i:i + 200] += rng.normal(0, rng.uniform(5, 30), 200) * np.hanning(200)
    # receiver passband shaping like an SSB filter (~200-3000 Hz)
    b, a = sps.butter(4, [200, 3000], btype="band", fs=FS)
    w = sps.lfilter(b, a, w)
    if rng.random() < 0.3:  # unmodulated carrier / birdie
        f0 = rng.uniform(300, 2800)
        w += rng.uniform(0.05, 0.5) * np.std(w) * np.sin(2 * np.pi * f0 * np.arange(n) / FS)
    return (w / np.std(w)).astype(np.float32)


def _place(sig: np.ndarray, rng: np.random.Generator, n: int = N_WIN,
           start: int | None = None) -> np.ndarray:
    out = np.zeros(n)
    if len(sig) >= n:
        return sig[:n].copy()
    if start is None:
        start = int(rng.integers(0, n - len(sig) + 1))
    out[start:start + len(sig)] = sig
    return out


def _unit_rms(x: np.ndarray) -> np.ndarray:
    on = np.abs(x) > 1e-9
    r = np.sqrt(np.mean(x[on] ** 2)) if np.any(on) else 1.0
    return x / r


# --------------------------------------------------------------------------
# FT8 via WSJT-X ft8sim (real encoder)
# --------------------------------------------------------------------------
_CALL_PREFIX = ["K", "W", "N", "AA", "KB", "VE", "G", "DL", "JA", "VK", "EA", "F", "I", "PY"]
_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def random_call(rng):
    p = _CALL_PREFIX[rng.integers(len(_CALL_PREFIX))]
    return p + str(rng.integers(0, 10)) + "".join(rng.choice(list(_LETTERS), rng.integers(1, 4)))


def random_grid(rng):
    return (rng.choice(list("ABCDEFGHIJKLMNOPQR")) + rng.choice(list("ABCDEFGHIJKLMNOPQR"))
            + str(rng.integers(10)) + str(rng.integers(10)))


def random_ft8_message(rng):
    a, b = random_call(rng), random_call(rng)
    form = rng.integers(4)
    if form == 0:
        return f"CQ {a} {random_grid(rng)}"
    if form == 1:
        return f"{a} {b} {random_grid(rng)}"
    if form == 2:
        return f"{a} {b} {rng.choice(['-', '+'])}{rng.integers(1, 25):02d}"
    return f"{a} {b} RR73"


def ft8sim_available() -> bool:
    return shutil.which("ft8sim") is not None


def ft8_clean(msg: str, f0: float, dt: float, rng=None) -> np.ndarray:
    """Return a noiseless 15 s FT8 waveform from WSJT-X ft8sim (snr>90 => no noise)."""
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["ft8sim", msg, f"{f0:.1f}", f"{dt:.2f}", "0.0", "0.0", "1", "99"],
                       cwd=d, check=True, capture_output=True, timeout=30)
        wav = [f for f in os.listdir(d) if f.endswith(".wav")][0]
        x, fs = sf.read(os.path.join(d, wav), dtype="float64")
    assert fs == FS
    return _unit_rms(x)


def gen_ft8(rng, snr_db, n_signals=1):
    x = np.zeros(N_WIN)
    msgs = []
    for _ in range(n_signals):
        m = random_ft8_message(rng)
        f0 = float(rng.uniform(300, 2700))
        dt = float(np.round(rng.uniform(-0.5, 1.5), 2))
        x += ft8_clean(m, f0, dt)
        msgs.append(dict(msg=m, f0=f0, dt=dt))
    # snr_db is per signal (each FT8 signal has unit RMS), as WSJT-X reports it
    return add_awgn(x, snr_db, rng, sig_rms=1.0), msgs


# --------------------------------------------------------------------------
# CW
# --------------------------------------------------------------------------
MORSE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.", "G": "--.",
    "H": "....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..", "M": "--", "N": "-.",
    "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.", "S": "...", "T": "-", "U": "..-",
    "V": "...-", "W": ".--", "X": "-..-", "Y": "-.--", "Z": "--..",
    "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-", "5": ".....",
    "6": "-....", "7": "--...", "8": "---..", "9": "----.", "/": "-..-.", "?": "..--..",
}


def cw_keying(text: str, wpm: float) -> np.ndarray:
    dit = 1.2 / wpm
    n_dit = int(round(dit * FS))
    seq = []
    for wi, word in enumerate(text.upper().split()):
        if wi:
            seq.append(np.zeros(n_dit * 7))
        for ci, ch in enumerate(word):
            if ci:
                seq.append(np.zeros(n_dit * 3))
            code = MORSE.get(ch)
            if code is None:
                continue
            for ei, el in enumerate(code):
                if ei:
                    seq.append(np.zeros(n_dit))
                seq.append(np.ones(n_dit * (1 if el == "." else 3)))
    env = np.concatenate(seq) if seq else np.zeros(1)
    # 5 ms raised-cosine edges to avoid key clicks
    r = int(0.005 * FS)
    win = np.hanning(2 * r + 1)
    win /= win.sum()
    return np.convolve(env, win, mode="same")


def gen_cw(rng, snr_db, text=None):
    if text is None:
        text = f"CQ CQ DE {random_call(rng)} {random_call(rng)} K"
    wpm = float(rng.uniform(12, 35))
    f0 = float(rng.uniform(400, 1000))
    env = cw_keying(text, wpm)
    t = np.arange(len(env)) / FS
    s = env * np.sin(2 * np.pi * f0 * t + rng.uniform(0, 2 * np.pi))
    s = _unit_rms(s)
    return add_awgn(_place(s, rng), snr_db, rng, sig_rms=1.0), dict(text=text, wpm=wpm, f0=f0)


# --------------------------------------------------------------------------
# RTTY (ITA2 Baudot, FSK)
# --------------------------------------------------------------------------
ITA2_LTRS = {"E": 1, "\n": 2, "A": 3, " ": 4, "S": 5, "I": 6, "U": 7, "\r": 8, "D": 9, "R": 10,
             "J": 11, "N": 12, "F": 13, "C": 14, "K": 15, "T": 16, "Z": 17, "L": 18, "W": 19,
             "H": 20, "Y": 21, "P": 22, "Q": 23, "O": 24, "B": 25, "G": 26, "M": 28, "X": 29,
             "V": 30}
ITA2_FIGS = {"3": 1, "-": 3, "8": 6, "7": 7, "4": 10, ",": 12, ":": 14, "5": 16, ")": 18,
             "2": 19, "6": 21, "0": 22, "1": 23, "9": 24, "?": 25, ".": 28, "/": 29}
LTRS, FIGS = 31, 27


def baudot_encode(text: str) -> list[int]:
    codes, shift = [LTRS, LTRS], "L"
    for ch in text.upper():
        if ch in (" ", "\r", "\n"):
            codes.append(ITA2_LTRS[ch])
        elif ch in ITA2_LTRS:
            if shift != "L":
                codes.append(LTRS)
                shift = "L"
            codes.append(ITA2_LTRS[ch])
        elif ch in ITA2_FIGS:
            if shift != "F":
                codes.append(FIGS)
                shift = "F"
            codes.append(ITA2_FIGS[ch])
    return codes


def rtty_bits(codes: list[int]) -> list[float]:
    """Return list of (bit, duration_in_bits): 1 start(space=0), 5 data LSB-first, 1.5 stop."""
    out = []
    for c in codes:
        out.append((0, 1.0))
        for i in range(5):
            out.append(((c >> i) & 1, 1.0))
        out.append((1, 1.5))
    return out


def gen_rtty_clean(text: str, fc: float, baud=45.45, shift=170.0, mark_high=True,
                   lead_s=1.0) -> np.ndarray:
    """Continuous-phase FSK.  Amateur convention puts mark on the higher RF
    frequency; demodulated in USB (IC-7300 USB-D) that is the higher audio tone,
    which is what fldigi expects with Reverse off.  (Bug found in testing: the
    first version had mark low, and fldigi printed garbage.)"""
    bits = [(1, lead_s * baud)] + rtty_bits(baudot_encode(text)) + [(1, 0.5 * baud)]
    freqs = []
    for b, dur in bits:
        n = int(round(dur * FS / baud))
        mark = (b == 1)
        hi = mark if mark_high else (not mark)
        freqs.append(np.full(n, fc + (shift / 2 if hi else -shift / 2)))
    f = np.concatenate(freqs)
    phase = 2 * np.pi * np.cumsum(f) / FS
    s = np.sin(phase)
    r = int(0.01 * FS)
    s[:r] *= np.linspace(0, 1, r)
    s[-r:] *= np.linspace(1, 0, r)
    return s


def random_text(rng, n_words=6):
    words = ["CQ", "DE", "TEST", "QTH", "RST", "599", "NAME", "OP", "TU", "73", "QSL",
             "RIG", "ANT", "DIPOLE", "WX", "SUNNY", "PWR", "100W", "HELLO"]
    return " ".join(rng.choice(words, n_words)) + " " + random_call(rng)


def gen_rtty(rng, snr_db, text=None, fc=None):
    text = text or random_text(rng)
    fc = float(fc if fc is not None else rng.uniform(800, 2300))
    s = _unit_rms(gen_rtty_clean(text, fc))
    return add_awgn(_place(s, rng), snr_db, rng, sig_rms=1.0), dict(text=text, fc=fc)


# --------------------------------------------------------------------------
# PSK31 (BPSK, varicode)
# --------------------------------------------------------------------------
VARICODE = {
    " ": "1", "a": "1011", "b": "1011111", "c": "101111", "d": "101101", "e": "11",
    "f": "111101", "g": "1011011", "h": "101011", "i": "1101", "j": "111101011",
    "k": "10111111", "l": "11011", "m": "111011", "n": "1111", "o": "111", "p": "111111",
    "q": "110111111", "r": "10101", "s": "10111", "t": "101", "u": "110111", "v": "1111011",
    "w": "1101011", "x": "11011111", "y": "1011101", "z": "111010101",
    "A": "1111101", "B": "11101011", "C": "10101101", "D": "10110101", "E": "1110111",
    "F": "11011011", "G": "11111101", "H": "101010101", "I": "1111111", "J": "111111101",
    "K": "101111101", "L": "11010111", "M": "10111011", "N": "11011101", "O": "10101011",
    "P": "11010101", "Q": "111011101", "R": "10101111", "S": "1101111", "T": "1101101",
    "U": "101010111", "V": "110110101", "W": "101011101", "X": "101110101",
    "Y": "101111011", "Z": "1010101101",
    "0": "10110111", "1": "10111101", "2": "11101101", "3": "11111111", "4": "101110111",
    "5": "101011011", "6": "101101011", "7": "110101101", "8": "110101011", "9": "110110111",
    "/": "110101111", "?": "1010101111", ".": "1010111", ",": "1110101", "-": "110101",
    "\n": "11101", "\r": "11111",
}


def psk31_bits(text: str, pre=48, post=32) -> list[int]:
    bits = [0] * pre  # idle reversals for receiver sync
    for ch in text:
        if ch in VARICODE:
            bits += [int(b) for b in VARICODE[ch]] + [0, 0]
    bits += [1] * post
    return bits


def gen_psk31_clean(text: str, fc: float, baud=31.25) -> np.ndarray:
    bits = psk31_bits(text)
    sps_ = int(round(FS / baud))  # 384 samples per symbol at 12 kHz
    # differential encoding: 0 -> phase reversal, 1 -> no change
    d = [1.0]
    for b in bits:
        d.append(d[-1] if b else -d[-1])
    d = np.array(d)
    t = np.arange(sps_) / sps_
    w_new = (1 - np.cos(np.pi * t)) / 2  # raised-cosine transition
    bb = np.concatenate([d[k - 1] * (1 - w_new) + d[k] * w_new for k in range(1, len(d))])
    # amplitude ramp on/off
    r = sps_
    bb[:r] *= np.linspace(0, 1, r)
    bb[-r:] *= np.linspace(1, 0, r)
    n = np.arange(len(bb))
    return bb * np.cos(2 * np.pi * fc * n / FS)


def random_psk_text(rng):
    words = ["cq", "de", "test", "name", "qth", "rig", "ant", "tnx", "fer", "qso", "73",
             "hello", "pse", "k", "rst", "599", "weather", "is", "sunny", "the"]
    return " ".join(rng.choice(words, 6)) + " " + random_call(rng).lower()


def gen_psk31(rng, snr_db, text=None, fc=None):
    text = text or random_psk_text(rng)
    fc = float(fc if fc is not None else rng.uniform(600, 2400))
    s = _unit_rms(gen_psk31_clean(text, fc))
    return add_awgn(_place(s, rng), snr_db, rng, sig_rms=1.0), dict(text=text, fc=fc)


# --------------------------------------------------------------------------
# SSB voice via espeak-ng
# --------------------------------------------------------------------------
_SENTENCES = [
    "CQ CQ CQ this is {c} calling CQ and standing by",
    "{c} you are five nine here in {g} thanks for the call",
    "roger roger the name here is {n} and the rig is a hundred watts",
    "copy that {c} we have a little fading on the band tonight",
    "this is {c} portable checking into the net with no traffic",
    "QRZ QRZ this is {c} listening on frequency",
]
_NAMES = ["bob", "alice", "ken", "maria", "joe", "sam", "lee"]


def espeak_available() -> bool:
    return shutil.which("espeak-ng") is not None


def gen_ssb(rng, snr_db, text=None):
    c = " ".join(random_call(rng))
    text = text or rng.choice(_SENTENCES).format(c=c, g=random_grid(rng), n=rng.choice(_NAMES))
    voice = rng.choice(["en-us", "en", "en-gb-x-rp", "en-us+m3", "en+f3", "en+m5"])
    speed = int(rng.integers(130, 190))
    pitch = int(rng.integers(20, 80))
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "v.wav")
        subprocess.run(["espeak-ng", "-v", voice, "-s", str(speed), "-p", str(pitch),
                        "-w", p, text], check=True, capture_output=True, timeout=30)
        x, fs = sf.read(p, dtype="float64")
    if x.ndim > 1:
        x = x.mean(1)
    x = sps.resample_poly(x, FS, fs)
    b, a = sps.butter(6, [300, 2700], btype="band", fs=FS)
    x = sps.lfilter(b, a, x)
    # random frequency shift of up to +/-150 Hz = SSB mistuning (Weaver-less: hilbert shift)
    shift = rng.uniform(-150, 150)
    xa = sps.hilbert(x)
    x = np.real(xa * np.exp(2j * np.pi * shift * np.arange(len(x)) / FS))
    # speech RMS measured over voiced parts only
    voiced = np.abs(x) > 0.02 * np.abs(x).max()
    s = x / np.sqrt(np.mean(x[voiced] ** 2))
    return add_awgn(_place(s, rng), snr_db, rng, sig_rms=1.0), dict(text=text, voice=voice)


# --------------------------------------------------------------------------
GENERATORS = {"ft8": gen_ft8, "cw": gen_cw, "rtty": gen_rtty, "psk31": gen_psk31, "ssb": gen_ssb}


def generate(label: str, rng: np.random.Generator, snr_db: float):
    """Return (float32 15 s waveform scaled to ~0.1 RMS, metadata)."""
    if label == "noise":
        x, meta = noise_only(rng), {}
    elif label in CLASSES[13:21] or label in ("sitorb", "psk8"):
        from . import synth_fldigi
        x, meta = synth_fldigi.generate(label, rng, snr_db)
    elif label in CLASSES[38:]:
        from . import synth_b7
        x, meta = synth_b7.GENERATORS[label](rng, snr_db)
    elif label in CLASSES[34:38]:
        from . import synth_b6
        x, meta = synth_b6.GENERATORS[label](rng, snr_db)
    elif label in CLASSES[26:33]:
        from . import synth_b5
        x, meta = synth_b5.GENERATORS[label](rng, snr_db)
    elif label in CLASSES[21:26]:
        from . import synth_b4
        x, meta = synth_b4.GENERATORS[label](rng, snr_db)
    elif label not in GENERATORS:
        from . import synth_wsjt
        x, meta = synth_wsjt.GENERATORS[label](rng, snr_db)
    else:
        x, meta = GENERATORS[label](rng, snr_db)
    x = x / (np.std(x) + 1e-12) * 0.1
    return x.astype(np.float32), meta


def write_wav_12k(path: str, x: np.ndarray):
    """16-bit PCM 12 kHz mono, the format jt9 expects."""
    y = np.clip(x / (np.abs(x).max() + 1e-12) * 0.5, -1, 1)
    sf.write(path, y, FS, subtype="PCM_16")
