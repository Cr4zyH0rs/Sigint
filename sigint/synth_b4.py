"""Batch 4 generators built from published specifications (no encoder available here).

SSTV  - mode timings and VIS header from the "Dayton paper", J.L. Barber N7CXI, *Proposal
        for SSTV Mode Specifications* (2000):
        https://www.darc.de/fileadmin/filemounts/distrikte/q/ortsverbaende/01/images/SSTV/Dayton_Paper.pdf
        sigidwiki: https://www.sigidwiki.com/wiki/Slow-Scan_Television_(SSTV)
        FM: sync 1200 Hz, black 1500 Hz, white 2300 Hz.
WEFAX - HF radiofax: 120 lines/min (also 60), index of cooperation 576 (also 288),
        black 1500 Hz / white 2300 Hz, start tone = 300 Hz black/white alternation,
        stop tone = 450 Hz alternation, then phasing lines.
        https://en.wikipedia.org/wiki/Radiofax , https://www.sigidwiki.com/wiki/WEFAX ,
        xwefax manual https://www.qsl.net/5b4az/pkg/xwefax/xwefax.html
2G ALE - MIL-STD-188-141 8-FSK: tones 750..2500 Hz in 250 Hz steps, 125 symbols/s
        (8 ms), 3 bits/symbol; each 24-bit word is Golay-coded to 48 bits + 1 stuff bit
        and sent 3 times = 49 symbols = 392 ms.
        https://www.sigidwiki.com/wiki/Automatic_Link_Establishment_(2G_ALE)
        https://www.wavecom.ch/content/ext/DecoderOnlineHelp/worddocuments/mil188141a.htm
        Simplification: word bits are random (no Golay/interleaver); the on-air
        tone/timing structure is what the classifier sees.
CW beacon - NCDXF/IARU International Beacon Project: 18 beacons share 14.100, 18.110,
        21.150, 24.930, 28.200 MHz; each sends for 10 s: callsign at 22 wpm at 100 W,
        then four 1 s dashes at 100 W, 10 W, 1 W, 0.1 W.
        https://ncdxf.org/beacon/beaconschedule.html
        https://en.wikipedia.org/wiki/International_Beacon_Project
        Also generic "VVV DE CALL/B" beacons with a long key-down, as heard on 10 m.
"""
from __future__ import annotations

import numpy as np

from .synth import FS, N_WIN, add_awgn, cw_keying, random_call, _unit_rms

NEW_CLASSES = ["sstv", "wefax", "ale", "cw_beacon"]


def fm_tone(freq: np.ndarray, phase0=0.0) -> np.ndarray:
    return np.sin(phase0 + 2 * np.pi * np.cumsum(freq) / FS)


class _Track:
    """Frequency track built from (freq, seconds) segments with fractional-sample timing."""

    def __init__(self):
        self.parts, self.t, self.n = [], 0.0, 0

    def tone(self, f, sec):
        self.t += sec
        m = int(round(self.t * FS)) - self.n
        self.parts.append(np.full(m, f, float)); self.n += m

    def pixels(self, vals, sec, lo=1500.0, hi=2300.0):
        self.t += sec
        m = int(round(self.t * FS)) - self.n
        idx = np.minimum((np.arange(m) * len(vals)) // max(m, 1), len(vals) - 1)
        self.parts.append(lo + (hi - lo) * np.clip(vals[idx], 0, 1)); self.n += m

    def array(self):
        return np.concatenate(self.parts) if self.parts else np.zeros(0)


# ------------------------------------------------------------------ test images
def random_image(rng, h, w):
    """Colour test picture: gradient background, rectangles, discs and a noisy band."""
    yy, xx = np.mgrid[0:h, 0:w] / np.array([h, w])[:, None, None]
    img = np.stack([a * xx + b * yy + c for a, b, c in rng.uniform(-0.5, 0.8, (3, 3))], -1)
    for _ in range(int(rng.integers(3, 10))):
        y0, x0 = rng.integers(0, h), rng.integers(0, w)
        hh, ww = rng.integers(h // 10, h // 2), rng.integers(w // 10, w // 2)
        img[y0:y0 + hh, x0:x0 + ww] = rng.uniform(0, 1, 3)
    for _ in range(int(rng.integers(0, 4))):
        cy, cx, r = rng.uniform(0, h), rng.uniform(0, w), rng.uniform(h / 12, h / 4)
        img[(np.mgrid[0:h, 0:w][0] - cy) ** 2 + (np.mgrid[0:h, 0:w][1] - cx) ** 2 < r * r] = rng.uniform(0, 1, 3)
    y0 = int(rng.integers(0, h)); img[y0:y0 + h // 8] += rng.normal(0, 0.2, (len(img[y0:y0 + h // 8]), w, 3))
    return np.clip(img, 0, 1)


# ------------------------------------------------------------------ SSTV
def vis(track, code):
    track.tone(1900, 0.300); track.tone(1200, 0.010); track.tone(1900, 0.300)
    track.tone(1200, 0.030)
    bits = [(code >> i) & 1 for i in range(7)]
    for b in bits + [sum(bits) % 2]:          # LSB first, even parity
        track.tone(1100 if b else 1300, 0.030)
    track.tone(1200, 0.030)


def sstv_martin(track, img, pix_ms):
    for row in img:
        track.tone(1200, 4.862e-3); track.tone(1500, 0.572e-3)
        for ch in (1, 2, 0):                   # G, B, R
            track.pixels(row[:, ch], pix_ms * 1e-3); track.tone(1500, 0.572e-3)


def sstv_scottie(track, img, pix_ms):
    track.tone(1200, 9e-3)                     # starting sync, first line only
    for row in img:
        track.tone(1500, 1.5e-3); track.pixels(row[:, 1], pix_ms * 1e-3)
        track.tone(1500, 1.5e-3); track.pixels(row[:, 2], pix_ms * 1e-3)
        track.tone(1200, 9e-3); track.tone(1500, 1.5e-3); track.pixels(row[:, 0], pix_ms * 1e-3)


def _yuv(img):
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    y = 0.299 * r + 0.587 * g + 0.114 * b
    return y, np.clip(0.5 + 0.713 * (r - y), 0, 1), np.clip(0.5 + 0.564 * (b - y), 0, 1)


def sstv_robot36(track, img):
    y, ry, by = _yuv(img)
    for i in range(len(img)):
        track.tone(1200, 9e-3); track.tone(1500, 3e-3); track.pixels(y[i], 88e-3)
        track.tone(1500 if i % 2 == 0 else 2300, 4.5e-3); track.tone(1900, 1.5e-3)
        track.pixels((ry if i % 2 == 0 else by)[i], 44e-3)


def sstv_pd(track, img, pix_ms):
    y, ry, by = _yuv(img)
    for i in range(0, len(img) - 1, 2):
        track.tone(1200, 20e-3); track.tone(1500, 2.08e-3)
        track.pixels(y[i], pix_ms * 1e-3)
        track.pixels((ry[i] + ry[i + 1]) / 2, pix_ms * 1e-3)
        track.pixels((by[i] + by[i + 1]) / 2, pix_ms * 1e-3)
        track.pixels(y[i + 1], pix_ms * 1e-3)


# name: (VIS code, lines, width, writer)
SSTV_MODES = {
    "Martin M1": (44, 256, 320, lambda t, im: sstv_martin(t, im, 146.432)),
    "Martin M2": (40, 256, 160, lambda t, im: sstv_martin(t, im, 73.216)),
    "Scottie S1": (60, 256, 320, lambda t, im: sstv_scottie(t, im, 138.240)),
    "Scottie S2": (56, 256, 160, lambda t, im: sstv_scottie(t, im, 88.064)),
    "Robot 36": (8, 240, 320, sstv_robot36),
    "PD120": (95, 496, 640, lambda t, im: sstv_pd(t, im, 121.6)),
}


def sstv_transmission(rng, mode=None):
    mode = mode or list(SSTV_MODES)[int(rng.integers(len(SSTV_MODES)))]
    code, h, w, writer = SSTV_MODES[mode]
    tr = _Track()
    vis(tr, code)
    writer(tr, random_image(rng, h, w))
    return mode, tr.array()


def _window(freq_track, rng, lead_s=3.0):
    """15 s slice, sometimes starting before key-up so the VIS/start tone is included."""
    n = len(freq_track)
    s = int(rng.integers(-int(lead_s * FS), max(1, n - N_WIN)))
    out = np.zeros(N_WIN)
    a, b = max(0, s), min(n, s + N_WIN)
    out[a - s:b - s] = 1
    seg = np.zeros(N_WIN); seg[a - s:b - s] = freq_track[a:b]
    return seg, out.astype(bool)


def gen_sstv(rng, snr_db):
    mode, ftrack = sstv_transmission(rng)
    off = float(rng.uniform(-80, 80))             # dial mistuning
    f, on = _window(ftrack + off, rng)
    x = np.where(on, fm_tone(f, rng.uniform(0, 2 * np.pi)), 0.0)
    return add_awgn(_unit_rms_on(x, on), snr_db, rng, 1.0), dict(submode=mode, centre=1900 + off)


def _unit_rms_on(x, on):
    return x / np.sqrt(np.mean(x[on] ** 2)) if on.any() else x


# ------------------------------------------------------------------ WEFAX
def weather_chart(rng, h, w):
    """Mostly white chart: isobar-like contours, lat/long grid, coastline-ish curve, text blocks."""
    yy, xx = np.mgrid[0:h, 0:w] / float(w)
    field = sum(rng.uniform(0.5, 1.5) * np.sin(rng.uniform(2, 12) * xx + rng.uniform(1, 8) * yy + rng.uniform(0, 6))
                for _ in range(4))
    img = np.ones((h, w))
    img[np.abs((field * 4) % 1 - 0.5) < 0.04] = 0          # contours
    img[:, :: int(rng.integers(80, 200))] = 0              # meridians
    img[:: int(rng.integers(20, 50)), :] = 0.0              # parallels
    for _ in range(int(rng.integers(5, 25))):              # text / station plots
        y0, x0 = int(rng.integers(0, h - 4)), int(rng.integers(0, w - 60))
        blk = rng.random((int(rng.integers(2, 5)), int(rng.integers(20, 60)))) < 0.5
        img[y0:y0 + blk.shape[0], x0:x0 + blk.shape[1]][blk] = 0
    return img


def wefax_transmission(rng, lpm=120, ioc=576, lines=None):
    """Start tone (5 s) + phasing (30 s) + chart + stop tone (5 s) + black (10 s)."""
    line_s = 60.0 / lpm
    w = int(round(np.pi * ioc))
    lines = lines or int(rng.integers(60, 200))
    tr = _Track()
    def alt(rate_hz, sec):
        for _ in range(int(sec * rate_hz)):
            tr.tone(1500, 0.5 / rate_hz); tr.tone(2300, 0.5 / rate_hz)
    alt(300, 5.0)
    phasing = np.zeros(w); phasing[: int(0.05 * w)] = 1    # white pulse, rest black
    for _ in range(int(30 / line_s)):
        tr.pixels(phasing, line_s)
    for row in weather_chart(rng, lines, w):
        tr.pixels(row, line_s)
    alt(450, 5.0)
    tr.tone(1500, 10.0)
    return tr.array()


def gen_wefax(rng, snr_db):
    lpm = 60 if rng.random() < 0.15 else 120
    ioc = 288 if rng.random() < 0.15 else 576
    off = float(rng.uniform(-150, 150))
    ftrack = wefax_transmission(rng, lpm, ioc) + off
    f, on = _window(ftrack, rng, lead_s=0)
    x = np.where(on, fm_tone(f, rng.uniform(0, 2 * np.pi)), 0.0)
    return add_awgn(_unit_rms_on(x, on), snr_db, rng, 1.0), dict(submode=f"{lpm}/{ioc}", centre=1900 + off)


# ------------------------------------------------------------------ 2G ALE
ALE_TONES = 750.0 + 250.0 * np.arange(8)
ALE_SPS = FS // 125            # 96 samples = 8 ms


def ale_burst(rng, n_words):
    syms = []
    for _ in range(n_words):
        bits = rng.integers(0, 2, 49)
        syms.append(np.tile(bits, 3).reshape(49, 3) @ np.array([4, 2, 1]))
    syms = np.concatenate(syms)
    return np.repeat(ALE_TONES[syms], ALE_SPS)


def gen_ale(rng, snr_db):
    """One or two bursts (call / response / sounding) of 3..30 words, possibly with a gap."""
    f = np.zeros(N_WIN); on = np.zeros(N_WIN, bool)
    pos = int(rng.integers(-3 * FS, 2 * FS))
    off = float(rng.uniform(-40, 40))
    for _ in range(int(rng.integers(1, 3))):
        b = ale_burst(rng, int(rng.integers(3, 31))) + off
        a, e = max(0, pos), min(N_WIN, pos + len(b))
        if e > a:
            f[a:e] = b[a - pos:e - pos]; on[a:e] = True
        pos += len(b) + int(rng.uniform(0.3, 4) * FS)
    if not on.any():  # burst fell outside: put a short one in the middle
        b = ale_burst(rng, 5); s = N_WIN // 3
        f[s:s + len(b)] = b; on[s:s + len(b)] = True
    x = np.where(on, fm_tone(np.where(on, f, 1625.0), rng.uniform(0, 2 * np.pi)), 0.0)
    return add_awgn(_unit_rms_on(x, on), snr_db, rng, 1.0), dict(centre=1625.0 + off)


# ------------------------------------------------------------------ CW beacons
NCDXF_ORDER = ["4U1UN", "VE8AT", "W6WX", "KH6RS", "ZL6B", "VK6RBP", "JA2IGY", "RR9O", "VR2B",
               "4S7B", "ZS6DN", "5Z4B", "4X6TU", "OH2B", "CS3B", "LU4AA", "OA4B", "YV5B"]


def _ncdxf_slot(call):
    """10 s slot: callsign at 22 wpm, then four 1 s dashes at 0/-10/-20/-30 dB."""
    env = cw_keying(call + " ", 22)
    gap = int(0.164 * FS)                       # 3 dot units at 22 wpm (dot = 1.2/22 s)
    dash = np.ones(FS)
    parts = [env, np.zeros(7 * int(round(1.2 / 22 * FS)))]   # word space before the dashes
    for g in (1.0, 10 ** (-10 / 20), 10 ** (-20 / 20), 10 ** (-30 / 20)):
        parts += [g * dash, np.zeros(gap)]
    s = np.concatenate(parts)[: 10 * FS]
    return np.pad(s, (0, 10 * FS - len(s)))


def gen_cw_beacon(rng, snr_db):
    f0 = float(rng.uniform(400, 1000))
    if rng.random() < 0.6:
        # NCDXF: a 15 s window spans two consecutive 10 s slots; each beacon fades independently
        k = int(rng.integers(len(NCDXF_ORDER)))
        env = np.concatenate([_ncdxf_slot(NCDXF_ORDER[(k + i) % 18]) *
                              (0 if rng.random() < 0.25 else 10 ** (rng.uniform(-20, 0) / 20))
                              for i in range(3)])
        if env.max() == 0:
            env[: 10 * FS] = _ncdxf_slot(NCDXF_ORDER[k])
        s = int(rng.integers(0, 15 * FS))
        env, kind = env[s:s + N_WIN], "ncdxf"
    else:
        call = random_call(rng)
        msg = f"VVV VVV DE {call}/B {call}/B "
        wpm = float(rng.uniform(10, 20))
        one = np.concatenate([cw_keying(msg, wpm), np.ones(int(rng.uniform(2, 8) * FS)),
                              np.zeros(int(rng.uniform(0.5, 2) * FS))])
        env = np.tile(one, int(np.ceil(3 * N_WIN / len(one))))
        s = int(rng.integers(0, len(one)))
        env, kind = env[s:s + N_WIN], "generic"
    t = np.arange(N_WIN) / FS
    x = env * np.sin(2 * np.pi * f0 * t + rng.uniform(0, 2 * np.pi))
    on = env > 0.05
    return add_awgn(_unit_rms_on(x, on), snr_db, rng, 1.0), dict(submode=kind, f0=f0)


GENERATORS = dict(sstv=gen_sstv, wefax=gen_wefax, ale=gen_ale, cw_beacon=gen_cw_beacon)
