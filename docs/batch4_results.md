# Batch 4: SSTV, HF fax, 2G ALE, CW beacons, NAVTEX/SITOR-B (ID-only)

Run 2026-11-19. 100 test windows per mode, random SNR −20 to +15 dB (2500 Hz reference).
No content decoding: the pipeline stores mode, confidence, time, audio offset and bandwidth only.
Raw numbers: `results/verify_b4_seed4.json`, `results/batch4_occupancy_seed0.json`,
`results/classifier_seed4.json`, `results/end_to_end_seed4.json`, `results/tiebreak_seed4.json`,
`results/train_history_b4.json`.

## 1. Where the test audio came from

| Class | Source | sigidwiki | Spec used |
|---|---|---|---|
| `sitorb` (SITOR-B + NAVTEX) | **Real fldigi 4.2.03 transmissions** (its SITORB and NAVTEX modems), recorded like batch 3. Separate train/test takes. | [SITOR-B](https://www.sigidwiki.com/wiki/SITOR-B) | 100 Bd, 170 Hz FSK |
| `sstv` | Own generator from the published mode timings: Martin M1/M2, Scottie S1/S2, Robot 36, PD120, with VIS header and random colour test pictures. | [SSTV](https://www.sigidwiki.com/wiki/Slow-Scan_Television_(SSTV)) | J.L. Barber N7CXI, [*Proposal for SSTV Mode Specifications* ("Dayton paper")](https://www.darc.de/fileadmin/filemounts/distrikte/q/ortsverbaende/01/images/SSTV/Dayton_Paper.pdf) |
| `wefax` | Own generator: 120 or 60 lines/min, IOC 576 or 288, 1500 Hz black / 2300 Hz white, 300 Hz start tone, phasing, synthetic weather chart, 450 Hz stop tone. | [WEFAX](https://www.sigidwiki.com/wiki/WEFAX) | [Radiofax (Wikipedia)](https://en.wikipedia.org/wiki/Radiofax), [xwefax manual](https://www.qsl.net/5b4az/pkg/xwefax/xwefax.html) |
| `ale` | Own generator: 8-FSK, tones 750–2500 Hz every 250 Hz, 8 ms symbols, 49-symbol (392 ms) words, 1–2 bursts per window. Word bits are random (no Golay coding), since only the on-air shape matters for ID. | [2G ALE](https://www.sigidwiki.com/wiki/Automatic_Link_Establishment_(2G_ALE)) | MIL-STD-188-141, summarised by [Wavecom](https://www.wavecom.ch/content/ext/DecoderOnlineHelp/worddocuments/mil188141a.htm) |
| `cw_beacon` | Own generator. 60%: NCDXF/IARU beacons (callsign at 22 wpm, then four 1 s dashes at 100/10/1/0.1 W, 10 s slots, the 18 real callsigns in schedule order, independent fading per slot). 40%: generic "VVV DE CALL/B" beacons with a long key-down. | (CW; no dedicated page) | [NCDXF beacon schedule](https://ncdxf.org/beacon/beaconschedule.html), [International Beacon Project (Wikipedia)](https://en.wikipedia.org/wiki/International_Beacon_Project) |

**Not used:** no SSTV/fax/ALE encoder or decoder was available. Installing the `pysstv`
and `sstv` Python packages from PyPI was refused by this environment's safety check, so I
wrote the generators from the specs and checked them by measurement (section 2) instead of
with an independent decoder. sigidwiki recordings were not used (no licence granted on them).

## 2. Checks against the specs (`stress/verify_b4.py`, all pass)

| Mode | Measured | Spec |
|---|---|---|
| SSTV, 6 modes | VIS codes 44, 40, 60, 56, 8, 95 read back with correct parity; line period 446.42 / 226.83 / 428.25 / 277.67 / 150.00 / 508.50 ms | 446.446 / 226.798 / 428.22 / 277.692 / 150.0 / 508.48 ms (Dayton paper) |
| WEFAX, 10 transmissions | start 300.0 Hz, stop 450.0 Hz, line 0.500 s, black 1492 Hz, white 2309 Hz | 300 / 450 Hz, 120 lpm, 1500 / 2300 Hz |
| 2G ALE, 100 bursts | 8 tones at 750…2500 Hz (worst error 7 Hz vs 250 Hz spacing), 8 ms symbol, 0.392 s word | MIL-STD-188-141 |
| NCDXF, all 18 calls | four 1.000 s dashes at 0 / −10 / −20 / −30 dB, callsign ends by 4.4 s of the 10 s slot | NCDXF schedule page |
| SITOR-B / NAVTEX, 4 fldigi takes | shift 170 Hz, 100 Bd | [SITOR-B](https://www.sigidwiki.com/wiki/SITOR-B) |

Fixed along the way:
- The beacon generator ran the callsign's last element into the first dash; it now has a word space between them.
- One fldigi SITOR-B test take stopped after 18 s, so I re-recorded it.

## 3. Frequency and bandwidth, 100 windows per mode

| Mode | No signal found | Centre error, median | Bandwidth, median |
|---|---|---|---|
| CW beacon | 15 | 0 Hz | 21 Hz (NCDXF), 38 Hz (generic) |
| SITOR-B / NAVTEX | 14 | 9 Hz (100% within 100 Hz) | 211 Hz |
| 2G ALE | 47 | 18 Hz (91% within 100 Hz) | 1.91 kHz (sigidwiki lists 2 kHz) |
| SSTV | 24 | 126 Hz* | 0.80–1.10 kHz by sub-mode |
| WEFAX | 18 | 395 Hz* | 105–246 Hz* |

\* For SSTV and fax, the reference centre is the nominal 1900 Hz band centre. The estimator
reports where the energy is, which depends on the picture. A weather chart is mostly white,
so fax energy sits at the 2300 Hz white tone (about 400 Hz above centre) and the measured width
is narrow. These numbers describe the picture content, not an error in the mode ID.

**Bug fixed:** ALE first measured 108 Hz wide (it stopped at the gap between two tones) and
SSTV about 360 Hz. Wider smoothing and bridging gaps up to 300 Hz brought ALE to 1.91 kHz and SSTV to about 1 kHz (`sigint/features.py`).
"No signal found" is mostly at −20 to −10 dB, where a 1–2 kHz-wide signal spreads its power
thinly across many bins.

## 4. Classifier, 26 classes, 100 windows each (`data/resnet18_modes_b4.pt`)

Trained on 8 epochs as before. Validation accuracy was 83.0%, and was still rising slowly at the end.

Overall: **82.4%** (2,600 windows), or **84.9% with the frequency tie-breaker** (77 fixed, 4 broken).
When confidence was 0.9 or higher (52% of windows), **99.9%** were correct.

By SNR: 49% at −20 to −15 dB, 78% at −15 to −10 dB, and 88–90% above −10 dB.

| New mode | Correct | Mistaken for |
|---|---|---|
| 2G ALE | 93% | MT63 (7) |
| SITOR-B / NAVTEX | 92% | Olivia 3, DominoEX 2 |
| WEFAX | 91% | WSPR 6, JT9 2 |
| SSTV | 79% | MT63 9, Contestia 4 |
| CW beacon | 77% | **CW 12**, ALE 7 |

Effects on the older classes:
- **Plain CW and CW beacons are confused with each other in both directions.** 9 CW windows were called beacons, and 12 beacon windows were called CW. Both are on-off keyed carriers; the beacon cue is the long dashes, which a 15 s window may not contain.
- **SSB voice is sometimes called ALE** (9 of 100 SSB windows). Both fill about 2 kHz.
- The Olivia/Contestia and MFSK/THOR confusions from batch 3 got worse with 5 more classes: Contestia 65%→46%, MFSK 64%→56%, THOR 88%→77%.
- JT9 (59%→76%) and FT8 (70%→83%) improved.

## 5. ID-only end-to-end (100 windows, 26-class model)

- 0 crashes, and 0 decoders run.
- 0 decoded text rows stored, and 0 prompts containing message text.
- Label accuracy was 80%, and 74 of 100 windows got a frequency.
- The Ollama server is mocked, as in every batch, because ollama.com is blocked here.

## 6. Suggestions before batch 5

- Report **CW and CW beacon** as one "CW" family, and flag a beacon only when the stepped 1 s dashes are seen. Do the same for Olivia/Contestia and MFSK/THOR.
- Train for more epochs (12–15). Validation was still rising.
- Next batch as planned: STANAG / MIL-STD / PACTOR family.

## 7. Files

- New: `sigint/synth_b4.py`, `stress/verify_b4.py`.
- Changed: `sigint/synth.py` (26 CLASSES), `sigint/features.py` (occupancy for wide FM/MFSK modes and SITOR-B), `stress/record_fldigi.py` (sitorb class, class filter), `stress/make_dataset.py`, `stress/train.py`, `stress/run_all.py` (batch4_occupancy).
- Audio: `data/fldigi_tx/{train,test}/sitorb__*.wav`.
