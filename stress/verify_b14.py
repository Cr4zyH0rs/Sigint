"""Batch 14 checks on clean audio against the published parameters (sources in sigint/synth_b14.py).
multimon-ng (an independent decoder) is run on our own random test frames only to count how many
frames it accepts; its text output is discarded, never stored or shown."""
import json, os, subprocess, sys
import numpy as np
from scipy.signal import hilbert, resample_poly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sigint import synth_b14 as b
from sigint.synth import FS

def mm_count(x, demod, key):
    y = resample_poly(x, 147, 80); y = (y / np.abs(y).max() * 20000).astype(np.int16).tobytes()
    out = subprocess.run(["multimon-ng", "-q", "-t", "raw", "-a", demod, "-"], input=y, capture_output=True).stdout
    return out.decode(errors="ignore").count(key)

def inst_f(x):
    return np.diff(np.unwrap(np.angle(hilbert(x)))) * FS / 2 / np.pi

def tone_pair(x):
    f = inst_f(x); f = f[(f > 500) & (f < 3000)]
    h, e = np.histogram(f, bins=np.arange(500, 3000, 10)); c = (e[:-1] + e[1:]) / 2
    i = np.argsort(-h)
    a = c[i[0]]; b2 = next(c[j] for j in i if abs(c[j] - a) > 150)
    return sorted([round(float(a)), round(float(b2))])

rng = np.random.default_rng(14); out = {}
x = np.concatenate([b.fm_audio(b.aprs_packet(rng)) for _ in range(10)] + [np.zeros(FS)])
out["aprs"] = dict(frames_sent=10, frames_accepted_by_multimon=mm_count(x, "AFSK1200", "AFSK1200:"),
                   tones_hz=tone_pair(b.aprs_packet(rng)), published="Bell 202 1200/2200 Hz, 1200 bit/s")
for baud in (512, 1200, 2400):
    bits = b.pocsag_bits(rng, 4)
    w = [int("".join(map(str, bits[576 + 32 * i:608 + 32 * i])), 2) for i in range((len(bits) - 576) // 32)]
    sent = sum(1 for v in w if v not in (b.SYNC, b.IDLE) and not v >> 31)
    n = int(len(bits) * FS / baud)
    lvl = np.concatenate([np.zeros(FS // 2), np.where(bits[np.minimum((np.arange(n) * baud / FS).astype(int), len(bits) - 1)] == 0, 1.0, -1.0), np.zeros(FS // 2)])
    from scipy import signal as sps
    hp300 = sps.sosfilt(sps.butter(4, [300, 3000], "bandpass", fs=FS, output="sos"), lvl)
    hp30 = sps.sosfilt(sps.butter(4, [30, 3000], "bandpass", fs=FS, output="sos"), lvl)
    out[f"pocsag_{baud}"] = dict(address_codewords_sent=sent, accepted_raw=mm_count(lvl, f"POCSAG{baud}", "Address:"),
                                 accepted_deemphasis=mm_count(b._deemph(lvl), f"POCSAG{baud}", "Address:"),
                                 accepted_30_3000Hz=mm_count(hp30, f"POCSAG{baud}", "Address:"),
                                 accepted_300_3000Hz=mm_count(hp300, f"POCSAG{baud}", "Address:"),
                                 preamble_bits=576, sync=hex(b.SYNC), published="ITU-R M.584-2: >= 576-bit preamble, sync 0x7CD215D8, 16 codewords/batch")
org, h = b.same_header(rng); hb = b.same_burst(h)
x = np.concatenate([np.zeros(FS)] + [hb, np.zeros(FS)] * 3)
out["same"] = dict(header_bursts_sent=3, decoded_messages=mm_count(x, "EAS", "ZCZC"), tones_hz=tone_pair(hb),
                   bit_ms=round(1000 / 520.83, 2), preamble_bytes="16 x 0xAB",
                   published="520.83 bit/s, 2083.3/1562.5 Hz, 1.92 ms bits, 16 x 0xAB, header x3 with 1 s pauses")
mb = b.mdc_burst(rng)
out["mdc1200"] = dict(tones_hz=tone_pair(mb), burst_ms=round(len(mb) / FS * 1000, 1), published="1200 Bd, 1200/1800 Hz")
for dur, name in ((0.1, "CCIR-1"), (0.07, "CCIR-2")):
    s = b.selcall_tones("12234", dur)
    f = inst_f(s); seg = int(dur * FS)
    out["selcall_" + name] = dict(tones_hz=[round(float(np.median(f[i * seg + 50:(i + 1) * seg - 50]))) for i in range(5)],
                                  expected_hz=[1124, 1197, 2110, 1275, 1358], tone_ms=round(seg / FS * 1000, 1),
                                  published="sigidwiki CCIR tones; CCIR-1 100 ms, CCIR-2 70 ms; repeat tone E 2110 Hz")
os.makedirs("results", exist_ok=True)
json.dump(out, open("results/verify_b14_seed14.json", "w"), indent=1)
print(json.dumps(out, indent=1))
