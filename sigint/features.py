"""Spectrogram features with librosa.

librosa.stft / librosa.amplitude_to_db: https://librosa.org/doc/latest/generated/librosa.stft.html
A linear-frequency STFT is used rather than mel, because the modes of interest
are narrowband (FT8 50 Hz, PSK31 ~60 Hz, RTTY 250 Hz) and sit anywhere in
200-3000 Hz; mel scaling would blur the upper part of the passband.
"""
from __future__ import annotations

import librosa
import numpy as np

FS = 12000
N_FFT = 2048          # 5.86 Hz bins
HOP = 512             # 42.7 ms
F_LO, F_HI = 100.0, 3100.0
F_BINS = 128          # pooled frequency bins (~23 Hz each)


def spectrogram(x: np.ndarray) -> np.ndarray:
    S = np.abs(librosa.stft(x.astype(np.float32), n_fft=N_FFT, hop_length=HOP,
                            window="hann", center=True)) ** 2
    freqs = librosa.fft_frequencies(sr=FS, n_fft=N_FFT)
    S = S[(freqs >= F_LO) & (freqs < F_HI)]
    # average-pool frequency to F_BINS rows
    k = S.shape[0] // F_BINS
    S = S[: k * F_BINS].reshape(F_BINS, k, -1).mean(1)
    D = librosa.power_to_db(S, ref=np.max, top_db=80.0)
    # per-image standardisation, robust to gain changes
    D = (D - D.mean()) / (D.std() + 1e-6)
    return D.astype(np.float32)


def _std(D):
    return ((D - D.mean()) / (D.std() + 1e-6)).astype(np.float32)


def spectrogram_mc(x: np.ndarray) -> np.ndarray:
    """3-channel input, each 128 x 352 (same size as `spectrogram`):
    0: the original 15 s overview (5.86 Hz bins pooled to 23 Hz, 42.7 ms hop).
    1: frequency zoom: 1.46 Hz bins (n_fft 8192), 128 bins centred on the strongest signal,
       42.7 ms hop. Separates very narrow modes (JT9 1.74 Hz tone spacing, FST4, WSPR 1.46 Hz,
       FT8 vs JS8) that the 23 Hz overview merges.
    2: time zoom: n_fft 512 (23.4 Hz bins, 128 rows over 100-3100 Hz), 10.7 ms hop, middle 3.75 s.
       Resolves symbol lengths the 42.7 ms hop cannot (Contestia 16 ms vs Olivia 32 ms symbols
       at 250 Hz; MFSK vs THOR keying).
    """
    x = x.astype(np.float32)
    ch0 = spectrogram(x)
    # frequency zoom
    S = np.abs(librosa.stft(x, n_fft=8192, hop_length=HOP, window="hann", center=True)) ** 2
    f = librosa.fft_frequencies(sr=FS, n_fft=8192)
    band = (f >= F_LO) & (f < F_HI)
    prof = np.convolve(S[band].mean(1), np.ones(9) / 9, mode="same")
    k = int(np.flatnonzero(band)[0] + np.argmax(prof))
    k = min(max(k, 64), S.shape[0] - 64)
    Z = librosa.power_to_db(S[k - 64:k + 64], ref=np.max, top_db=80.0)[:, :ch0.shape[1]]
    # time zoom
    S2 = np.abs(librosa.stft(x, n_fft=512, hop_length=128, window="hann", center=True)) ** 2
    f2 = librosa.fft_frequencies(sr=FS, n_fft=512)
    S2 = S2[(f2 >= F_LO)][:F_BINS]
    mid = S2.shape[1] // 2
    T = librosa.power_to_db(S2[:, mid - 176:mid + 176], ref=np.max, top_db=80.0)
    return np.stack([ch0, _std(Z), _std(T)])


def occupancy(x: np.ndarray, lo=150.0, hi=3100.0, thresh_db=6.0, nperseg=4096,
              gap_hz=25.0, smooth_hz=0.0, local_floor_hz=600.0, floor_pct=50.0):
    """Estimate audio centre frequency and occupied bandwidth of the dominant signal.

    Welch PSD (scipy.signal.welch) -> noise floor = median PSD in the passband ->
    bins more than `thresh_db` above the floor, grown out from the strongest bin
    with up to 25 Hz gaps allowed. Returns (centre_hz, bandwidth_hz, peak_snr_db)
    or (None, None, peak) when nothing rises above the floor.
    Reported frequency is audio offset; dial frequency + offset = RF (USB).
    """
    from scipy.signal import welch
    f, p = welch(x, fs=FS, nperseg=nperseg)
    band = (f >= lo) & (f <= hi)
    f, p = f[band], p[band]
    df = f[1] - f[0]
    if smooth_hz > 0:  # wideband signals (voice) have gappy harmonic spectra
        m = max(1, int(smooth_hz / df))
        p = np.convolve(p, np.ones(m) / m, mode="same")
    pdb = 10 * np.log10(p + 1e-20)
    if local_floor_hz:
        # running-median floor follows receiver-filter roll-off and 1/f noise; the
        # first version used one global median and flagged pink noise as a signal
        from scipy.ndimage import median_filter
        floor = median_filter(pdb, size=max(3, int(local_floor_hz / df) | 1), mode="nearest")
    else:
        floor = np.full_like(pdb, np.percentile(pdb, floor_pct))
    rel = pdb - floor
    k = int(np.argmax(rel))
    peak = float(rel[k])
    if peak < thresh_db:
        return None, None, peak
    above = rel > thresh_db
    gap = max(1, int(gap_hz / df))
    i = j = k
    while True:
        nxt = [t for t in range(j + 1, min(len(f), j + 1 + gap)) if above[t]]
        if not nxt:
            break
        j = nxt[-1]
    while True:
        prv = [t for t in range(max(0, i - gap), i) if above[t]]
        if not prv:
            break
        i = prv[0]
    w = p[i:j + 1]
    centre = float(np.sum(f[i:j + 1] * w) / np.sum(w))
    return centre, float(f[j] - f[i] + df), peak


OCCUPANCY_ARGS = {
    # voice is wide: global floor, smoothing across harmonics, bridge pauses between formants
    "ssb": dict(gap_hz=200.0, smooth_hz=150.0, thresh_db=3.0, local_floor_hz=0),
    # RTTY is two tones 170 Hz apart; bridge the ~125 Hz hole between mark and space
    # (first version locked onto one tone: median centre error 84 Hz)
    "rtty": dict(gap_hz=150.0),
    # SITOR-B / NAVTEX: also 170 Hz FSK (ITU-R M.476/M.625), same two-tone handling
    "sitorb": dict(gap_hz=150.0),
}
# Wide multi-carrier / multi-tone modes: a running-median floor 600 Hz wide sits *inside*
# a 0.5-2 kHz-wide flat signal and hides it, so use one global floor (found in batch 3:
# MT63 centre error ~500 Hz, bandwidth 9 Hz, before this)
# 10th-percentile floor: a 2 kHz signal fills most of the passband, so the median is signal
_WIDE = dict(local_floor_hz=0, gap_hz=100.0, smooth_hz=30.0, thresh_db=6.0, floor_pct=10.0)
for _m in ("olivia", "contestia", "mfsk", "mt63", "jt65", "q65", "thor", "dominoex"):
    OCCUPANCY_ARGS[_m] = _WIDE
# Batch 6: 8PSK up to 1.3 kHz wide (8PSK1000); with the default 600 Hz running floor the
# estimate read 8PSK1000 as 847 Hz, centre 290 Hz off.
OCCUPANCY_ARGS["psk8"] = _WIDE
# Batch 4: SSTV/WEFAX (FM 1200/1500-2300 Hz) and 2G ALE (8 tones 250 Hz apart, 750-2500 Hz).
# With _WIDE the estimate stopped at the first gap between ALE tones or at the white-level
# peak of a fax chart (ALE 108 Hz, fax 158 Hz median). Wider smoothing + 300 Hz bridging gives
# ALE 1.89 kHz, SSTV 1.06 kHz, fax 1.16 kHz median at SNR > 0 dB (40-window sweep, batch 4).
_FM_WIDE = dict(local_floor_hz=0, gap_hz=300.0, smooth_hz=100.0, thresh_db=3.0, floor_pct=10.0)
for _m in ("sstv", "wefax", "ale"):
    OCCUPANCY_ARGS[_m] = _FM_WIDE
# Batch 5: wide single-carrier PSK (2400 Bd) and multi-tone modems use the same wide settings;
# PACTOR I/II are two tones 200 Hz apart (ARRL). The 600 Hz running-median floor sits inside
# PACTOR II's ~450 Hz signal (no signal found at +30 dB), so use a global 10th-percentile floor.
for _m in ("stanag4285", "mil110_serial", "mil110_16tone", "mil110_39tone", "pactor3"):
    OCCUPANCY_ARGS[_m] = _FM_WIDE
OCCUPANCY_ARGS["pactor1"] = OCCUPANCY_ARGS["pactor2"] = dict(
    local_floor_hz=0, gap_hz=150.0, smooth_hz=30.0, thresh_db=6.0, floor_pct=10.0)

# Batch 6: packet FSK300 (200 Hz shift) and SITOR-A (170 Hz mostly) are two-tone FSK like
# PACTOR I; FSQ is 33 tones over ~290 Hz (wide settings).
OCCUPANCY_ARGS["packet"] = OCCUPANCY_ARGS["sitora"] = OCCUPANCY_ARGS["pactor1"]
OCCUPANCY_ARGS["fsq"] = _WIDE
# Batch 7: DSC and CCIR 493-4 selcall are 100 Bd / 170 Hz FSK (pair fit like SITOR); HFDL
# (1800 Bd PSK, 2.4 kHz) and MSK144 (2000 bps MSK, ~2.5 kHz) are wide.
OCCUPANCY_ARGS["dsc"] = OCCUPANCY_ARGS["ccir493"] = OCCUPANCY_ARGS["pactor1"]
OCCUPANCY_ARGS["hfdl"] = OCCUPANCY_ARGS["msk144"] = _FM_WIDE
# Batch 8: FreeDV (1.0-1.6 kHz multi-carrier) uses the wide settings; RPR (8 carriers over
# 480 Hz) like 8PSK; DTMF tones are 500-1000 Hz apart, so bridge wide gaps.
for _m in ("freedv1600", "freedv700c", "freedv700de", "dtmf"):
    OCCUPANCY_ARGS[_m] = _FM_WIDE
OCCUPANCY_ARGS["rpr"] = _WIDE
# Batch 9: ARQ-E and CIS FSK are two-tone FSK (pair method below); XPA (520-1280 Hz) and
# WWV (tones and ticks 440-1500 Hz) are spread out, so bridge wide gaps; XPA2 and Mazielka
# are ~250 Hz MFSK like FSQ; RWM is one keyed carrier (default settings).
OCCUPANCY_ARGS["arqe"] = OCCUPANCY_ARGS["cis_fsk"] = OCCUPANCY_ARGS["pactor1"]
OCCUPANCY_ARGS["xpa"] = OCCUPANCY_ARGS["wwv"] = _FM_WIDE
OCCUPANCY_ARGS["xpa2"] = OCCUPANCY_ARGS["mazielka"] = _WIDE
# Batch 10: all multi-carrier or MFSK 0.2-2.5 kHz wide, flat-topped -> wide settings
for _m in ("ifkp", "pskr", "ofdm"):
    OCCUPANCY_ARGS[_m] = _WIDE
for _m in ("mcpsk", "datac", "hamdrm"):
    OCCUPANCY_ARGS[_m] = _FM_WIDE

# Batch 11: wide serial PSK (2400/1200 Bd) like STANAG 4285; STANAG 4481 is two-tone FSK
for _m in ("stanag4539", "stanag4529", "ale3g", "link11_slew"):
    OCCUPANCY_ARGS[_m] = _FM_WIDE
OCCUPANCY_ARGS["stanag4481"] = OCCUPANCY_ARGS["pactor1"]

# Batch 14: AFSK / tone-sequence modes spread over 1-2.3 kHz; POCSAG is baseband NRZ
for _m in ("aprs", "same", "mdc1200", "selcall_ccir", "pocsag"):
    OCCUPANCY_ARGS[_m] = _FM_WIDE


def occupancy_for(label: str, x: np.ndarray):
    fc, bw, pk = occupancy(x, **OCCUPANCY_ARGS.get(label, {}))
    if label in ("rtty", "sitorb") and fc is not None:
        # centre = midpoint of the best-matching 170 Hz mark/space pair; the
        # energy-weighted centroid drifts toward whichever tone is stronger
        from .decoders import estimate_carrier
        fc = estimate_carrier(x, "rtty")
    if label in ("sitora", "dsc", "ccir493") and fc is not None:
        from .decoders import estimate_carrier
        fc = estimate_carrier(x, "rtty")
    if label in ("pactor1", "packet") and fc is not None:
        # 200 Bd FSK with h = 1 puts strong lines on each tone; same pair method, 200 Hz shift
        from .decoders import estimate_carrier
        fc = estimate_carrier(x, "rtty", rtty_shift=200.0)
    return fc, bw, pk
