"""RF-frequency tie-breaker for modes that look alike on a spectrogram.

FT8/JS8 (both 8-FSK, 6.25 Hz, 160 ms) and JT9/WSPR/FST4 (very narrow MFSK) are
hard to separate from 15 s of audio, but by convention each sits on its own
dial frequency. Given the rig's dial frequency (USB) and the signal's audio
offset, RF = dial + offset. A mode that has published working frequencies is
down-weighted when RF falls outside all of its windows [dial, dial + 3 kHz].
Modes without a frequency list here (CW, RTTY, SSB, PSK31...) are left alone.

Frequencies (MHz, USB dial) are the lists on each mode's sigidwiki page,
retrieved 2026-11-19 through sigidwiki's Semantic MediaWiki data:
  https://www.sigidwiki.com/wiki/FT8   https://www.sigidwiki.com/wiki/FT4
  https://www.sigidwiki.com/wiki/JS8   https://www.sigidwiki.com/wiki/WSPR
  https://www.sigidwiki.com/wiki/JT65  https://www.sigidwiki.com/wiki/JT9
  https://www.sigidwiki.com/wiki/Q65   https://www.sigidwiki.com/wiki/FST4
Only HF/6 m/4 m entries inside the IC-7300 range (0.03-74.8 MHz) are kept.
sigidwiki's lists are incomplete (e.g. JT9 lists only 3.578 and 28.079), so the
penalty is soft, not a veto.
"""
from __future__ import annotations

import numpy as np

DIALS_MHZ = {
    "ft8": [1.84, 3.573, 7.074, 10.136, 14.074, 18.1, 21.074, 24.915, 28.074, 50.313, 50.323, 70.1],
    "ft4": [3.575, 7.0475, 14.08, 18.104, 21.14, 24.919, 28.18, 50.318],
    "js8": [1.842, 3.578, 7.078, 10.13, 14.078, 18.104, 21.078, 24.922, 27.245, 28.078, 50.318],
    "wspr": [0.136, 0.4742, 1.8366, 3.5686, 7.0386, 10.1387, 14.0956, 18.1046, 21.0946,
             24.9246, 28.1246, 50.293, 70.091],
    "jt65": [1.838, 3.576, 7.039, 7.076, 10.139, 14.076, 18.098, 18.102, 24.917, 50.276],
    "jt9": [3.578, 28.079],
    "q65": [50.275, 50.305],
    "fst4": [0.137, 0.474],
}
PASSBAND_HZ = 3000.0
OFF_PLAN_WEIGHT = 0.1  # how much to trust a planned mode heard off its frequencies


def in_plan(label: str, rf_hz: float) -> bool | None:
    """True/False if the mode has a frequency list; None if it has none."""
    dials = DIALS_MHZ.get(label)
    if dials is None:
        return None
    return any(d * 1e6 <= rf_hz <= d * 1e6 + PASSBAND_HZ for d in dials)


def reweight(probs, classes, dial_hz: float | None, offset_hz: float | None):
    """Return (label, confidence, new_probs). No-op when dial or offset is unknown."""
    p = np.asarray(probs, float)
    if dial_hz is None or offset_hz is None:
        i = int(p.argmax())
        return classes[i], float(p[i]), p
    rf = dial_hz + offset_hz
    w = np.array([OFF_PLAN_WEIGHT if in_plan(c, rf) is False else 1.0 for c in classes])
    q = p * w
    q = q / q.sum() if q.sum() > 0 else p
    i = int(q.argmax())
    return classes[i], float(q[i]), q
