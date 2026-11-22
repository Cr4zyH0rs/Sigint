# Batch 7: SELCAL, DSC, CCIR 493-4 selcall, HFDL and MSK144 (ID-only)

Run 2026-11-22. 100 test windows per mode, random SNR −20 to +15 dB (2500 Hz reference).
This batch only identifies signals. Nothing is demodulated or decoded, and the generated payloads are random.

Raw numbers:
- `results/verify_b7_seed7.json`: checks against the specs
- `results/classifier_b7_10_seed5.json`: classifier test, 43 classes
- `results/end_to_end_seed5.json`: ID-only pipeline run
- `results/train_history_b7_10.json`: training log

## 1. Modes and sources

| Class | How the audio is made | Source |
|---|---|---|
| `selcal` | Two tones together for 1 s, 0.2 s gap, two more tones for 1 s. 16-tone or older 12-tone alphabet. Sometimes sent twice, sometimes followed by voice. | [sigidwiki: ICAO Selcal](https://www.sigidwiki.com/wiki/ICAO_Selcal); tone frequencies from [Wikipedia: SELCAL](https://en.wikipedia.org/wiki/SELCAL) |
| `dsc` | 2-FSK, 170 Hz shift, 100 Bd: a dot pattern (alternating bits) then data. | [sigidwiki: GMDSS DSC](https://www.sigidwiki.com/wiki/GMDSS_Digital_Selective_Calling), [Shoc: DSC](https://cartoonman.github.io/Shoc/dsc.htm) |
| `ccir493` | 2-FSK, 170 Hz shift, 100 Bd, with a long steady-tone preamble before the data. | [sigidwiki: CCIR 493-4 Selcall](https://www.sigidwiki.com/wiki/CCIR_493-4_Selcall) |
| `hfdl` | 1800 Bd BPSK, QPSK or 8PSK on a 1440 Hz sub-carrier, short (1.8 s) or long (4.3 s) bursts. | [sigidwiki: HFDL](https://www.sigidwiki.com/wiki/High_Frequency_Data_Link_(HFDL)) |
| `msk144` | WSJT-X's own `msk144sim`: meteor-scatter pings of 0.05–2.5 s. | [sigidwiki: MSK144](https://www.sigidwiki.com/wiki/MSK144), [WSJT-X](https://wsjt.sourceforge.io/wsjtx.html) |

**Assumptions** (not stated in the sources above; also listed in `sigint/synth_b7.py`):
- **SELCAL:** ±50 Hz mistuning, and how often voice follows the call.
- **DSC:** 2 s dot pattern, then 4–8 s of data. The full protocol (ITU-R M.493) was not read.
- **CCIR 493-4:** 1–4 s preamble on one tone, then 2–5 s of data. Shoc's Codan page lists a 200 Hz shift; sigidwiki's 170 Hz is used.
- **HFDL:** burst lengths, a 0.3 s BPSK preamble, 30 data + 15 known probe symbols, roll-off 0.3, 1–3 bursts per window. The full standard (ARINC 753) was not read.
- **MSK144:** ping widths and 1–3 pings per window.

## 2. Checks against the specs (`stress/verify_b7.py`, clean audio)

| Check | Measured | Published |
|---|---|---|
| SELCAL timing | Tone segments 1.01 s, gap 0.19 s | 1 s, 0.2 s, 1 s |
| DSC shift and width | 170 Hz; 99% bandwidth 311 Hz | 170 Hz shift; 350 Hz listed |
| CCIR 493-4 | Steady preamble 3.96 s (set to 4.0 s), shift 170 Hz | Long tone preamble, 170 Hz |
| HFDL | Symbol-rate line at 1800 Hz, centre 1432 Hz, 99% bandwidth 2020 Hz | 1800 Bd, 1440 Hz, 2400 Hz listed |
| MSK144 | Tones 1042 / 2032 Hz, ACF 72.0 ms, 99% bandwidth 3057 Hz | 1000 / 2000 Hz, ACF 72 ms, 2.5 kHz listed |

The MSK144 tones read 32–42 Hz high. The cause was not checked; MSK's frequency spreading may move the measured peaks.

## 3. Classifier, 43 classes, 100 windows each (`resnet18_modes_b7_10.pt`)

The 38-class model `resnet18_modes_b6_10.pt` was fine-tuned for 10 epochs to 43 classes.
Validation accuracy was 95.8% after epoch 1 and 96.4% after epoch 10, the best epoch.

| | Batch 6 model (38 classes) | Batch 7 model (43 classes) |
|---|---|---|
| All windows | 90.2% | 90.0% |
| SNR −10 dB and up | 98.4% | **98.6%** |

Neither row uses the fldigi decode checks.

| SNR | −20…−15 | −15…−10 | −10…−5 | −5…0 | 0…5 | 5…10 | 10…15 |
|---|---|---|---|---|---|---|---|
| Accuracy | 47% | 89% | 97% | 99% | 99% | 99% | 99% |

| New mode | Correct (all SNR) | At −10 dB and up | Mistaken for (all SNR) |
|---|---|---|---|
| DSC | 94% | 98.5% | SSB 2, and 1 each for CCIR 493-4, packet, PACTOR III, 39-tone |
| CCIR 493-4 | 95% | 98.7% | CW beacon 3, DSC 1, 39-tone 1 |
| HFDL | 89% | 100% | ALE 6, SSB 2, PACTOR III 2, CW beacon 1 |
| MSK144 | 87% | 100% | 3 each for CW beacon, MIL-110 serial and PACTOR III; 4 others |
| SELCAL | 86% | 100% | CW beacon 11, and 1 each for SSB, ALE, 39-tone |

- **The only new-mode errors at −10 dB and up are DSC and CCIR 493-4 mistaken for each other, once each.** They use the same 170 Hz, 100 Bd FSK and differ only in the preamble.
- **SELCAL is called CW beacon at low SNR.** A weak tone pair looks like a keyed carrier.
- **Olivia/Contestia remains the largest error** at −10 dB and up: 28 errors, against 26 with the batch 6 model. The fldigi decode check fixes most of these and is not included here.
- **CW beacon is the catch-all for weak signals** in this model (51 windows of other modes), replacing SITOR-A from batch 6.

At confidence ≥ 0.9 (88% of windows), 97.0% were correct.

## 4. ID-only end-to-end (100 windows)

- No crashes, no decoders run, no decoded text stored, and no prompts containing message text.
- Label accuracy was 87%, and 60 of 100 windows got a frequency.
- Ollama is mocked, as in every batch.

## 5. Not done in this batch

- No separate frequency and bandwidth test for the new modes. DSC and CCIR 493-4 use the same 170 Hz two-tone fit as RTTY and SITOR-A, and HFDL and MSK144 use the wide-signal settings.

## 6. Files

- New: `sigint/synth_b7.py`, `stress/verify_b7.py`, `stress/run_b7.sh`.
- Changed:
  - `sigint/synth.py`: 43 CLASSES.
  - `sigint/features.py`: settings for dsc, ccir493, hfdl and msk144.
  - `stress/make_dataset.py`: mc7 mode.
  - `stress/train.py`: mc7 data; copies the old output rows when the class count grows.
