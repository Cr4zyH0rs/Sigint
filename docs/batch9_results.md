# Batch 9: time stations, utility FSK and Russian MFSK/selcall signals (ID-only)

Run 2026-11-23. 100 test windows per mode, random SNR −20 to +15 dB (2500 Hz reference).
This batch only identifies signals. Nothing is demodulated or decoded. Number-station digit
groups and FSK data are random.

Raw numbers:
- `results/verify_b9_seed9.json`: checks against the specs
- `results/classifier_b9_10_seed5.json`: classifier test, 55 classes
- `results/end_to_end_seed5.json`: ID-only pipeline run
- `results/train_history_b9_10.json`: training log

## 1. Modes and sources

| Class | What is built | Source |
|---|---|---|
| `wwv` | WWV or WWVH: 5 ms second ticks (1000 / 1200 Hz) with 10 ms silence before and 25 ms after; none on seconds 29 and 59; 800 ms minute marker (1500 Hz on the hour); 500/600/440 Hz tones by each station's minute table; voice ~7.5 s (WWV) or ~15 s (WWVH) before the minute | [NIST WWV/WWVH format](https://www.nist.gov/pml/div688/grp40/wwv_format) |
| `rwm` | Keyed carrier heard as a beat note: 1 Hz pulses (100 ms, minute 500 ms), 10 Hz pulses (20 ms, second 40 ms, minute 500 ms), or the Morse ID | [sigidwiki: RWM](https://www.sigidwiki.com/wiki/RWM) (ACF 1000 / 100 ms), [Wikipedia: RWM](https://en.wikipedia.org/wiki/RWM) |
| `arqe` | Continuous 2-FSK at the listed baud/shift pairs 72/85, 96/170, 192/160 and 288/400 | [sigidwiki: ARQ-E(E3)](https://www.sigidwiki.com/wiki/ARQ-E(E3)) |
| `cis_fsk` | CIS-36-50 (36–150 Bd, 85–500 Hz shift) and CIS-50-50 (50/100 Bd, 85–500 Hz), with 50 Bd dot reversals before traffic. One class, because sigidwiki calls them very similar. | [sigidwiki: CIS-36-50](https://www.sigidwiki.com/wiki/CIS-36-50), [sigidwiki: CIS-50-50](https://www.sigidwiki.com/wiki/CIS-50-50) |
| `xpa` | 17-tone MFSK at 10 Bd with Priyom's tone table, preamble (520/1280 Hz alternation, 600/1120 Hz tones, fixed tone string, 1200/1160 Hz, space tones) and 5-digit groups | [sigidwiki: XPA](https://www.sigidwiki.com/wiki/CIS_MFSK-20_XPA), [Priyom: XPA protocol](https://priyom.org/number-stations/digital/xpa/protocol) |
| `xpa2` | 16 tone slots 15.625 Hz apart from 1000 Hz, 7.8125 Bd, with Priyom's preamble and 5-digit groups | [sigidwiki: XPA2](https://www.sigidwiki.com/wiki/CIS_MFSK-16_XPA2), [Priyom: XPA2 protocol](https://priyom.org/number-stations/digital/xpa2/protocol) |
| `mazielka` | 6 tones 815–990 Hz (±5 Hz), 333 ms each, then a ~1.32 s pause, repeated | [sigidwiki: Mazielka (X06)](https://www.sigidwiki.com/wiki/Mazielka_(X06)), [Priyom: X06](https://priyom.org/diplomatic-stations/russia/x06) |

**Dropped from the plan:**
- **Codan Selcall:** its sigidwiki page did not load, and no other spec was found.
- **XPB:** sigidwiki gives no baud rate or tone spacing.

**Assumptions** (not stated in the sources above; also listed in `sigint/synth_b9.py`):
- **WWV:**
  - The receiver is zero-beat on the carrier.
  - The tones run for seconds 1–44.
  - The 100 Hz BCD code is left out, since it sits below most SSB passbands.
  - The voice is a synthetic time announcement.
- **RWM:**
  - Heard as a 400–1500 Hz beat note.
  - Carrier-only periods are left out, because a bare tone has nothing to identify.
  - DUT1 extra pulses are left out.
  - Morse at 12–20 wpm.
- **ARQ-E / CIS:** random bits, with no repetition cycle or alphabet modelled.
- **XPA / XPA2:** how much of the 2-minute preamble falls in a window, and the number of groups.
- **Mazielka:** uses Priyom's tone set; hfunderground lists 840–1015 Hz instead. Each call is a random order of the 6 tones.

## 2. Checks against the specs (`stress/verify_b9.py`, clean audio)

| Check | Measured | Published |
|---|---|---|
| WWV / WWVH minute marker | 800 ms at 1000 / 1200 Hz | 800 ms, 1000 / 1200 Hz |
| WWV / WWVH ticks, seconds 1–44 | 43 ticks (none on second 29), about 5 ms, 1000 / 1200 Hz, starting exactly on the second | 5 ms, each second except 29 and 59 |
| WWV minute 4 tone | 500 Hz | 500 Hz (WWV table) |
| RWM 1 Hz pulses | 100 ms, period 1.0 s | 100 ms, 1 pps |
| RWM 10 Hz pulses | 20 ms, second 40 ms, minute 521 ms, period 0.1 s | 20 / 40 / 500 ms |
| ARQ-E | 400 Hz with 3.5 ms bits (288 Bd); 170 Hz with 10.4 ms bits (96 Bd) | 288/400 and 96/170 pairs |
| CIS FSK | Shifts 85 and 125 Hz; bit lengths 20 ms (50 Bd dots), 10 ms (100 Bd), 27.8 ms (36 Bd) | Listed bauds and shifts |
| XPA tone set | 17 tones: 520, 600, 680, 720, 760–1120 Hz in 40 Hz steps, 1160, 1200, 1280 Hz; 100 ms symbols | Same (Priyom) |
| XPA2 tone set | 14 of the 16 slots used, 15.625 Hz apart, 128 ms symbols | sigidwiki: 14 tones in 16 slots, 15 Hz spacing; Priyom: 15.625 Hz, 7.8125 Bd |
| Mazielka | 2.0 s call, 1.32 s pause, 6 tones at 815–990 Hz less a 41 Hz dial offset | 333 ms × 6, ~1320 ms pause |

## 3. Classifier, 55 classes, 100 windows each (`resnet18_modes_b9_10.pt`)

The 48-class model `resnet18_modes_b8_10.pt` was fine-tuned for 10 epochs to 55 classes.
Validation accuracy reached 96.2% (epoch 9) and ended at 96.1%.

| | Batch 8 model (48 classes) | Batch 9 model (55 classes) |
|---|---|---|
| All windows | 89.3% | 89.0% |
| SNR −10 dB and up | 98.5% | **98.4%** |

Neither row uses the fldigi decode checks.

| SNR | −20…−15 | −15…−10 | −10…−5 | −5…0 | 0…5 | 5…10 | 10…15 |
|---|---|---|---|---|---|---|---|
| Accuracy | 44% | 86% | 97% | 99% | 99% | 98% | 99% |

| New mode | Correct (all SNR) | At −10 dB and up | Mistaken for (all SNR) |
|---|---|---|---|
| RWM | 93% | 100% | DTMF 3, and 1 each for 4 others |
| XPA2 | 92% | 98.7% | MIL-110 39-tone 2, WWV 2, and 1 each for 4 others |
| CIS FSK | 90% | 97.1% | RWM 3, Hell 2, and 1 each for 5 others |
| XPA | 90% | 100% | WWV 4, and 1 each for 6 others |
| Mazielka | 90% | 100% | WWV 3, DTMF 3, SSB 2, and 1 each for 2 others |
| WWV/WWVH | 86% | **90%** | DTMF 4, NDB 3, and 1 each for 7 others |
| ARQ-E | 83% | 100% | Hell 5, SITOR-A 4, and 1 each for 8 others |

- **WWV is the weakest new class at −10 dB and up (9 errors).** Its windows are mostly sparse 5 ms ticks, and in minutes with no tone that is nearly all there is. Those windows were called DTMF, ALE, XPA, RWM, SSB, MSK144 and NDB.
- **WWV and DTMF are now the catch-alls for weak signals** (71 and 67 windows of other modes). Both are sparse, bursty windows.
- **Olivia/Contestia:** 31 errors at −10 dB and up, the same as batch 8. The fldigi decode check is not included here.

At confidence ≥ 0.9 (88% of windows), 96.9% were correct.

## 4. ID-only end-to-end (100 windows)

- No crashes, no decoders run, no decoded text stored, and no prompts containing message text.
- Label accuracy was 86%, and 60 of 100 windows got a frequency.
- Ollama is mocked, as in every batch.

## 5. Not done in this batch

- No separate frequency and bandwidth test for the new modes.
- The WWV and DTMF catch-alls are not fixed. A simple rule could check the timing that the specs fix:
  - WWV: a 1000 or 1200 Hz tick every 1.000 s.
  - DTMF: a tone pair on the Q.23 grid.
  
  This rule is untested.

## 6. Files

- New: `sigint/synth_b9.py`, `stress/verify_b9.py`, `stress/run_b9.sh`.
- Changed:
  - `sigint/synth.py`: 55 CLASSES.
  - `sigint/features.py`: settings for the new modes.
  - `stress/make_dataset.py`: mc9 mode.
  - `stress/train.py`: mc9 data.
