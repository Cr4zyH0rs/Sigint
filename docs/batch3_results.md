# Frequency tie-breaker + Batch 3 (fldigi modes), ID-only

Run 2026-11-19. 100 test windows per mode at random SNR −20 to +15 dB (2500 Hz reference).
Raw numbers: `results/tiebreak_seed0.json`, `results/tiebreak_seed3.json`,
`results/classifier_seed3.json`, `results/batch3_occupancy_seed0.json`, `results/end_to_end_seed3.json`.

## 1. RF-frequency tie-breaker (`sigint/bandplan.py`)

RF = dial + audio offset. A mode with listed working frequencies is weighted ×0.1 when
the signal is outside all of its 3 kHz windows; modes without a list (CW, RTTY, SSB, PSK31…)
are untouched. Frequency lists are the ones on each mode's sigidwiki page
(https://www.sigidwiki.com/wiki/FT8 , /JS8 , /FT4 , /WSPR , /JT65 , /JT9 , /Q65 , /FST4).

| Test | Before | After | Fixed / broken |
|---|---|---|---|
| 13-class model, 1,300 windows | 83.9% | **92.3%** | 109 / 0 |
| 21-class model, 2,100 windows | 82.4% | **86.8%** | 95 / 3 |

Per mode (13-class run): JS8 38%→78%, JT9 62%→95%, FT8 63%→81%, FST4 65%→77%.

**Caveat:** test dials come from the same lists the tie-breaker uses (a planned mode is on
one of its dials 80% of the time; unplanned modes are placed on a planned dial 30% of the
time). That is the best case for an operator following the band plan. sigidwiki's lists are
incomplete (JT9 lists only 3.578 and 28.079 MHz), so the penalty is soft, not a veto.

## 2. Batch 3 audio: real fldigi transmissions

fldigi 4.2.03's own modulators transmitted into a PulseAudio null sink, recorded at 12 kHz
(`stress/record_fldigi.py`). 31 training takes and 31 separate test takes (different text and
carrier):

| Class | Sub-modes |
|---|---|
| Olivia | 8/250, 16/500, 32/1K, 8/500 |
| Contestia | 8/250, 16/500, 32/1K, 8/500 |
| MFSK | MFSK8, 16, 32, 64 |
| THOR | THOR8, 11, 16, 22 |
| DominoEX | 8, 11, 16, 22 |
| MT63 | 500L, 1KS, 1KL, 2KL |
| Hellschreiber | Feld Hell, Hell80, HellX5, Slow Hell |
| THROB | THROB1, 2, 4 |

Each window is a random 15 s slice, shifted to a random audio frequency, with noise added.

## 3. Classifier, 21 classes, 100 windows each

Overall **82.7%** (86.8% with the tie-breaker); 99.7% correct when confidence ≥ 0.9 (50% of
windows). By SNR: 52% at −20 to −15 dB, 73% at −15 to −10, 86–91% above −10 dB.

| Mode | Correct | Main confusion |
|---|---|---|
| THROB | 97% | — |
| DominoEX | 96% | — |
| MT63 | 92% | Contestia (6) |
| THOR | 88% | — |
| Hellschreiber | 84% | CW (4), THROB (4) |
| Contestia | 65% | **Olivia (31)** |
| MFSK | 64% | **THOR (20)** |
| Olivia | 61% | **Contestia (27)** |

Earlier modes held up (RTTY 99%, FT4 99%, WSPR 99%, PSK31 96%, SSB 95%, JT65 94%), apart from
the known FT8/JS8 and JT9/FST4 pairs. Validation accuracy was still rising at the last epoch
(84%), so more training epochs should help.

**Why Olivia/Contestia and MFSK/THOR mix:** Contestia is derived from Olivia and uses the same
tone grids and bandwidths (sigidwiki: https://www.sigidwiki.com/wiki/Contestia ,
https://www.sigidwiki.com/wiki/Olivia ). THOR is an incremental-frequency-keyed MFSK
relative of DominoEX (https://www.sigidwiki.com/wiki/THOR ,
https://www.sigidwiki.com/wiki/Multi_Frequency_Shift_Keying_(MFSK) ). In 15 s of spectrogram
the difference is mostly symbol timing, which the 43 ms time step only partly resolves.
Reporting these as families ("Olivia/Contestia") would be honest at this resolution.

## 4. Frequency and bandwidth (100 windows per mode)

Testing found and fixed a bug: the sliding noise floor (600 Hz wide) sat *inside* wide
signals and hid them. MT63 was measured 9 Hz wide with ~500 Hz centre error. Wide modes now
use a 10th-percentile global floor.

| Mode | Centre within 25 Hz | Measured bandwidth by sub-mode (median) |
|---|---|---|
| Olivia | 87% | 8/250: 272, 16/500: 516, 8/500: 526, 32/1K: 1017 Hz |
| Contestia | 91% | 278 / 510 / 513 / 1022 Hz |
| MFSK | 86% | MFSK8: 275, 16: 270, 32: 516, 64: 1028 Hz |
| THOR | 98% | 227–412 Hz |
| DominoEX | 97% | 220–406 Hz |
| MT63 | 76% | 500L: 519, 1K: 1020, 2KL: 2004 Hz |
| Hell | 80% (100% within 100 Hz) | 32–56 Hz |
| THROB | 88% (100% within 100 Hz) | 67–138 Hz |

The fix also corrected batch 2: JT65 now measures 199 Hz (was 18 Hz; nominal 180 Hz for
JT65A) and Q65 422 Hz. Weak wide signals are often not measured (29–43% of windows), because
a 1–2 kHz signal at negative SNR barely rises above the floor in any one bin.

## 5. ID-only end-to-end with the 21-class model

100 windows: 0 crashes, 100 logged, 0 decoders run, 0 message text stored, 87% labels correct.
