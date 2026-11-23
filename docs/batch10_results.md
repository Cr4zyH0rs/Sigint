# Batch 10: fldigi IFKP / PSK-R / multi-carrier PSK / OFDM, codec2 data modes and HamDRM (ID-only)

Run 2026-11-23. 100 test windows per mode, random SNR −20 to +15 dB (2500 Hz reference).
This batch only identifies signals. Nothing is demodulated or decoded. Payloads are random:
fldigi sends random words, codec2 random bytes, and HamDRM random QAM symbols.

Raw numbers:
- `results/verify_b10_seed10.json`: checks against the specs
- `results/classifier_b10_10_seed5.json`: classifier test, 61 classes
- `results/end_to_end_seed5.json`: ID-only pipeline run
- `results/train_history_b10_10.json`: training log

## 1. Modes and sources

| Class | How the audio is made | Source |
|---|---|---|
| `ifkp` | fldigi 4.2.03's own transmitter, IFKP | [fldigi mode table](https://www.w1hkj.org/FldigiHelp/mode_table_page.html): 33-FSK, 386 Hz |
| `pskr` | fldigi: PSK125R, PSK250R, PSK500R, PSK1000R | fldigi mode table; [fldigi PSK page](https://www.w1hkj.org/FldigiHelp/psk_page.html): FEC plus interleaving |
| `mcpsk` | fldigi multi-carrier PSK: PSK63RC10, PSK125RC4, PSK250RC3, PSK500RC2 | fldigi mode table (BPSK on each carrier) |
| `ofdm` | fldigi OFDM500F and OFDM750F | fldigi's own modulator; the fldigi help has no OFDM page, so the transmitter itself is the reference |
| `datac` | codec2 1.2.0's own modulator (`tools/datac_tx.c`, libcodec2 `freedv_rawdatatx`): DATAC0, 1, 3, 4, 13 bursts with preamble and postamble | [codec2 README_data](https://github.com/drowe67/codec2/blob/main/README_data.md) |
| `hamdrm` | Built from published parameters: DRM-style OFDM, mode A (Tu 24 ms) or B (Tu 21.33 ms), 53/57 or 45/51 carriers for 2.3/2.5 kHz, QAM-4/16/64 | [SSTV handbook ch. 10](https://sstv-handbook.com/download/sstv_10.pdf) (table 10.2), [QSSTV DRM modes](https://qsl.net/o/on4qz/qsstv/manual/drmmodes.html), [sigidwiki: WinDRM](https://www.sigidwiki.com/wiki/WinDRM), [ETSI ES 201 980](https://www.etsi.org/deliver/etsi_ES/201900_201999/201980/04.03.01_60/es_201980v040301p.pdf) (table 2) |

All four fldigi modes were named in [Bundscherer et al. 2025](https://arxiv.org/html/2501.07337v1) as modes our model lacked. There are 7 takes of 160 s per class: 6 for training (seeds 101–106) and 1 for testing (seed 109).

**Why HamDRM is spec-built:** QSSTV, the open HamDRM transmitter, can only transmit from its GUI, so it can't be scripted here.

**Assumptions** (not stated in the sources above; also listed in `sigint/synth_b10.py`):
- **DATAC:**
  - Bursts of 1–3 frames, with gaps of 0.3–3 s.
  - The other station's ACKs are not modelled.
  - Centre 1500 Hz ±50 Hz.
- **HamDRM:**
  - Modes A and B only; mode E's timing was not in the pages read.
  - Centre 1500 Hz ±50 Hz.
  - Pilot layout: the first symbol of each 400 ms frame is all pilots; every 4th carrier is a boosted pilot, moving by one carrier each symbol; 3 fixed boosted carriers.
  - A lead-in of 1–3 pilot frames.
  - Transmissions of 30–120 s.

**New setup step:** `gcc -O2 -o tools/datac_tx tools/datac_tx.c -lcodec2 -lm` (same packages as batch 8). Only training needs this.

## 2. Checks against the specs (`stress/verify_b10.py`, clean audio)

| Check | Measured (99% bandwidth) | Published |
|---|---|---|
| IFKP | 378 Hz | 386 Hz |
| PSK125R / 250R / 500R / 1000R | 179 / 366 / 747 / 1509 Hz | Table lists 125 / 250 / 500 / 1800 Hz. The first three table values equal the baud rate; a 99% bandwidth is wider. |
| PSK63RC10 / 125RC4 / 250RC3 / 500RC2 | 850 / 697 / 1078 / 1603 Hz | 850 / 650 / 950 / 1400 Hz |
| OFDM500F / 750F | 439 / 645 Hz | No published figure; consistent with the names |
| DATAC0 / 1 / 3 / 4 / 13 width | 735 / 1685 / 721 / 302 / 264 Hz | 500 / 1700 / 500 / 250 / 200 Hz (README "RF bandwidth"; a 99% bandwidth is wider) |
| DATAC burst length (with pre- and postamble) | 0.66 / 4.40 / 3.41 / 5.39 / 2.20 s | 0.44 / 4.18 / 3.19 / 5.17 / 2.0 s (without the 0.22 s pre- and postamble) |
| HamDRM useful symbol (cyclic-prefix correlation) | Mode A 24.00 ms, mode B 21.33 ms; symbol 26.67 ms | ETSI table 2: Tu 24 / 21⅓ ms, Ts 26⅔ ms |
| HamDRM width | A: 2197 / 2364 Hz; B: 2101 / 2382 Hz | 2.3 / 2.5 kHz |

## 3. Classifier, 61 classes, 100 windows each (`resnet18_modes_b10_10.pt`)

The 55-class model `resnet18_modes_b9_10.pt` was fine-tuned for 10 epochs to 61 classes.
Validation accuracy peaked at 95.7% (epoch 8) and ended at 95.6%.

| | Batch 9 model (55 classes) | Batch 10 model (61 classes) |
|---|---|---|
| All windows | 89.0% | 88.8% |
| SNR −10 dB and up | 98.4% | **98.4%** |

Neither row uses the fldigi decode checks.

| SNR | −20…−15 | −15…−10 | −10…−5 | −5…0 | 0…5 | 5…10 | 10…15 |
|---|---|---|---|---|---|---|---|
| Accuracy | 43% | 86% | 97% | 99% | 99% | 98% | 99% |

| New mode | Correct (all SNR) | At −10 dB and up | Mistaken for (all SNR) |
|---|---|---|---|
| IFKP | 98% | 100% | SSB 1, WWV 1 |
| PSK-R | 94% | 98.6% | 1 each for 6 classes |
| fldigi OFDM | 92% | 100% | multi-carrier PSK 3, and 1 each for 5 others |
| codec2 DATAC | 87% | 98.6% | PACTOR III 3, RPR 2, and 1 each for 8 others |
| HamDRM | 82% | 98.4% | MIL-110 serial 4, DTMF 3, WWV 3, and 1–2 each for 6 others |
| Multi-carrier PSK | 80% | 100% | WWV 5, MT63 4, FreeDV 700D/E 3, and 1–2 each for 6 others |

- **At −10 dB and up, the new modes made 4 errors in all:** PSK-R called MT63, DATAC called PACTOR III, HamDRM called MIL-110 serial, and one MIL-110 serial window called IFKP.
- **Weak-signal catch-alls:** WWV (87 windows of other modes), HamDRM (70) and DTMF (50). HamDRM is new on that list. A wide, noise-like OFDM signal looks like weak noise of any kind.
- **Olivia/Contestia:** 34 errors at −10 dB and up, against 31 in batch 9. The fldigi decode check is not included here.

At confidence ≥ 0.9 (88% of windows), 97.1% were correct.

## 4. ID-only end-to-end (100 windows)

- No crashes, no decoders run, no decoded text stored, and no prompts containing message text.
- Label accuracy was 86%, and 71 of 100 windows got a frequency.
- Ollama is mocked, as in every batch.

## 5. Not done in this batch

- HamDRM mode E is not built.
- QSSTV's real HamDRM transmitter is not used; it would need GUI automation.
- No separate frequency and bandwidth test for the new modes.
- The WWV/DTMF timing check is still queued.

## 6. Files

- New:
  - `sigint/synth_b10.py`, `tools/datac_tx.c`, `stress/verify_b10.py`, `stress/record_b10.sh`, `stress/run_b10.sh`
  - fldigi takes in `data/fldigi_tx/{train,test}/{ifkp,pskr,mcpsk,ofdm}__*` (not pushed; WAVs stay out of git)
- Changed:
  - `sigint/synth.py`: 61 CLASSES.
  - `sigint/features.py`: settings for the new modes.
  - `stress/record_fldigi.py`: the new mode entries.
  - `stress/make_dataset.py`: mc10 mode.
  - `stress/train.py`: mc10 data.
