"""Mode-specific decoders the router dispatches to.

FT8   -> WSJT-X `jt9 -8` command-line decoder (ships with WSJT-X; same decoder
         the GUI uses). Output line format: "hhmmss snr dt freq ~ message".
Voice -> faster-whisper WhisperModel.transcribe (https://github.com/SYSTRAN/faster-whisper)
RTTY/PSK31 -> fldigi via XML-RPC (see fldigi_client.py)
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass

import numpy as np

from .synth import write_wav_12k

_JT9_LINE = re.compile(r"^\s*(\d{4,6})\s+(-?\d+)\s+(-?\d+\.\d)\s+(\d+)\s+~\s+(.*?)\s*$")


@dataclass
class Decode:
    mode: str
    text: str
    snr: float | None = None
    dt: float | None = None
    freq: float | None = None


def parse_jt9(stdout: str) -> list[Decode]:
    out = []
    for line in stdout.splitlines():
        m = _JT9_LINE.match(line)
        if m:
            # jt9 may append a flag such as "a1" or "?" after a run of spaces
            msg = re.split(r"\s{2,}", m.group(5).strip())[0]
            out.append(Decode("FT8", msg, float(m.group(2)), float(m.group(3)), float(m.group(4))))
    return out


def decode_ft8(x12k: np.ndarray, depth: int = 3, timeout: float = 30.0,
               jt9: str = "jt9") -> list[Decode]:
    """Write a 15 s 12 kHz WAV and run jt9 -8 on it in a private temp dir.

    jt9 writes scratch files (timer.out, decoded.txt, jt9_wisdom.dat) into its
    working directory, so each call needs its own cwd to be safe in parallel.
    """
    if shutil.which(jt9) is None:
        raise FileNotFoundError("jt9 not found; install WSJT-X")
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "000000_000000.wav")
        write_wav_12k(wav, x12k)
        r = subprocess.run([jt9, "-8", "-d", str(depth), "-a", d, "-t", d, wav], cwd=d,
                           capture_output=True, text=True, timeout=timeout)
        return parse_jt9(r.stdout)


class WhisperDecoder:
    """faster-whisper wrapper. Model weights come from the Hugging Face Hub on first
    use; pass `model=` to inject a stand-in when weights are unavailable."""

    def __init__(self, size="base.en", device="cpu", compute_type="int8", model=None):
        if model is None:
            from faster_whisper import WhisperModel
            model = WhisperModel(size, device=device, compute_type=compute_type)
        self.model = model

    def decode(self, x12k: np.ndarray) -> list[Decode]:
        # faster-whisper expects 16 kHz float32 mono when given a numpy array
        from scipy.signal import resample_poly
        x16 = resample_poly(x12k, 4, 3).astype(np.float32)
        segments, info = self.model.transcribe(x16, language="en", vad_filter=True,
                                               beam_size=1)
        text = " ".join(s.text.strip() for s in segments).strip()
        return [Decode("SSB", text)] if text else []


def decode_fldigi(client, label: str, carrier_hz: float | None = None) -> list[Decode]:
    """Read what fldigi has printed for the window, then clear the RX pane."""
    text = client.rx_text()
    client.clear()
    text = text.strip()
    return [Decode(label.upper(), text, freq=carrier_hz)] if text else []


def estimate_carrier(x12k: np.ndarray, label: str = "psk31", lo=300.0, hi=2800.0,
                     smooth_hz=30.0, rtty_shift=170.0) -> float:
    """Centre frequency to point fldigi at (Welch PSD, scipy.signal.welch).

    PSK31: strongest narrowband peak. RTTY: the frequency c that maximises
    P(c - shift/2) + P(c + shift/2), i.e. the midpoint of the mark/space pair.
    (First version used the single strongest peak for RTTY too, which landed on
    the mark tone, 85 Hz off centre, and fldigi's AFC did not pull it in.)"""
    from scipy.signal import welch
    f, p = welch(x12k, fs=12000, nperseg=4096)
    df = f[1] - f[0]
    k = max(1, int(smooth_hz / df))
    ps = np.convolve(p, np.ones(k) / k, mode="same")
    band = (f >= lo) & (f <= hi)
    if label == "rtty":
        h = int(round(rtty_shift / 2 / df))
        score = np.zeros_like(ps)
        score[h:-h] = ps[:-2 * h] + ps[2 * h:]
        return float(f[band][np.argmax(score[band])])
    return float(f[band][np.argmax(ps[band])])
