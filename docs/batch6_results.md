# Batch 6: 8PSK, FSQ, HF PACKET, SITOR-A and NDB (ID-only)

Run 2026-11-21/22. 100 test windows per mode, random SNR −20 to +15 dB (2500 Hz reference).
This batch only identifies signals. Nothing is demodulated or decoded, and the generated payloads are random.

Raw numbers:
- `results/verify_b6_seed6.json`: checks against the specs, plus frequency and bandwidth estimates
- `results/classifier_b6_10_seed5.json`: classifier test, 38 classes
- `results/end_to_end_seed5.json`: ID-only pipeline run

## 1. Modes and sources

| Class | How the audio is made | Source |
|---|---|---|
| `psk8` | fldigi 4.2.03's own transmitter: 8PSK125, 250, 500 and 1000. Training and test use separate recordings (8 training takes, 1 test take). | [sigidwiki: 8PSK](https://www.sigidwiki.com/wiki/8PSK), 0.125–1.2 kHz |
| `fsq` | 33 tones 8.7890625 Hz apart. IFK+ coding: each tone = previous tone + character number + 1, minus 33 when out of range. Speeds 6, 4.5, 3 and 2 Bd. No idle signal: a transmission starts with no padding and stops when the text runs out. | [sigidwiki: FSQ](https://www.sigidwiki.com/wiki/FSQ), [ZL1BPU/ZL2AFP FSQ description](https://www.qsl.net/zl1bpu/MFSK/FSQweb.htm) |
| `packet` | HF FSK300: 300 Bd with a 200 Hz shift (70% of windows). BPSK300 in the other 30%. HDLC-style frames sent in bursts. | [sigidwiki: PACKET](https://www.sigidwiki.com/wiki/PACKET) |
| `sitora` | ARQ at 100 Bd. Shift is 170 Hz in 70% of windows, otherwise 300, 400 or 850 Hz. Cycle 450 ms. The other station's control signal is weaker or not heard. | [sigidwiki: SITOR-A](https://www.sigidwiki.com/wiki/SITOR-A) (ACF 450 ms, 350 Hz), [Shoc: SITOR-A](https://cartoonman.github.io/Shoc/sitora.htm) (bursts 0.065–0.290 s, pauses ≥ 0.2 s) |
| `ndb` | A2A: a continuous carrier, with a 1–3 letter Morse callsign sent as AM at 400 or 1020 Hz. | [sigidwiki: NDB](https://www.sigidwiki.com/wiki/Non-Directional_Beacon_(NDB)) |

**Dropped from the plan:**
- **CHU:** sigidwiki says the station shut down on 2026-06-22, so the rig can no longer hear it.
- **fldigi's FSQ transmitter:** when driven over XML-RPC it sent only about 5 s per 160 s take. FSQ is built from its spec instead.

**Assumptions** (not stated in the sources above; also listed in `sigint/synth_b6.py`):
- **FSQ:**
  - The 4.5, 3 and 2 Bd speeds keep 6 Bd's ratio to the tone spacing (1.5×).
  - The lengths of each transmission (3–12 s) and of the pauses (1–6 s).
- **PACKET:**
  - The flag preamble length.
  - The frame lengths.
  - NRZI coding with bit stuffing, as in AX.25/HDLC.
  - The gaps between frames.
  - IL2P framing is not modelled.
- **SITOR-A:**
  - A data block is 3 characters × 7 bits = 210 ms, and the control signal is 1 character = 70 ms.
  - Both follow from the 7-unit CCIR 476 code that sigidwiki cites, and they fit the 450 ms ACF and Shoc's burst range.
- **NDB:**
  - The keying speed (5–12 wpm).
  - The gap before the ID repeats.
  - The modulation depth.

## 2. Checks against the specs (`stress/verify_b6.py`, clean audio)

| Check | Measured | Published |
|---|---|---|
| FSQ tone grid | 8.789 Hz, all 33 tones used, 0 repeated tones (IFK+) | 33 tones, 8.7890625 Hz |
| FSQ 99% bandwidth | 286 Hz | 300 Hz |
| Packet FSK shift | Instantaneous-frequency peaks at 1405 and 1595 Hz (10 Hz bins), set at 1400/1600 | 200 Hz |
| Packet bit time | Shortest run 3.33 ms | 300 Bd |
| SITOR-A cycle | 0.45 s | ACF 450 ms |
| SITOR-A bursts | 0.087 s and 0.252 s (50 ms smoothing adds about 20–40 ms) | 0.065–0.290 s |
| NDB spectrum | Carrier 110 dB, upper sideband at +1020 Hz 98 dB, half-way point 21.5 dB (above the median spectrum level) | Carrier plus a 400 or 1020 Hz tone |
| 8PSK 20 dB width (fldigi takes) | 8PSK125: 176 Hz, 250: 324 Hz, 500: 647 Hz, 1000: 1296 Hz | 0.125–1.2 kHz |

## 3. Frequency and bandwidth, SNR 0 to 15 dB

| Mode | No signal found | Centre error, median | Bandwidth, median |
|---|---|---|---|
| 8PSK (125 / 250 / 500 / 1000) | 0 of 60 | 1–2 Hz | 205 / 322 / 668 / 1163 Hz |
| FSQ | 0 of 60 | 5–13 Hz | 306–311 Hz |
| Packet FSK300 | 0 of 36 | 19 Hz | 356 Hz |
| Packet BPSK300 | 0 of 24 | 88 Hz* | 404 Hz |
| SITOR-A 170 Hz | 0 of 37 | 1.7 Hz | 246 Hz |
| SITOR-A 300 / 400 / 850 Hz | 0 of 23 | 64 / 113 / 339 Hz* | 463 / 545 / 94 Hz |
| NDB | 0 of 60 | 0 Hz | 12–15 Hz (carrier only) |

\* Packet and SITOR-A take their centre from a two-tone fit: 200 Hz for packet, 170 Hz for SITOR-A, the same method used for RTTY and PACTOR I. That fit is off for BPSK packet and for the wider SITOR-A shifts. The fix is to try several shifts and keep the best, which is not done yet.

**Fixed along the way:**
- 8PSK1000 first read as 847 Hz wide, with the centre 290 Hz off. It now uses the wide-signal settings.
- Packet first locked onto one tone, giving a 6 Hz width. It now uses the two-tone fit.

## 4. Classifier, 38 classes, 100 windows each (`resnet18_modes_b6_10.pt`)

The 33-class model `resnet18_modes_mc3_10.pt` was fine-tuned for 10 epochs to 38 classes. Validation accuracy reached 96.4% (epoch 8) and stayed there (96.4% at epoch 10).

| | Batch 5 model (33 classes) | Batch 6 model (38 classes) |
|---|---|---|
| All windows | 90.2% | 90.2% |
| SNR −10 dB and up | 97.9% | **98.4%** |

Neither row uses the fldigi decode checks.

| SNR | −20…−15 | −15…−10 | −10…−5 | −5…0 | 0…5 | 5…10 | 10…15 |
|---|---|---|---|---|---|---|---|
| Accuracy | 50% | 88% | 97% | 99% | 99% | 98% | 98% |

| New mode | Correct (all SNR) | At −10 dB and up | Mistaken for |
|---|---|---|---|
| NDB | 99% | 100% | 39-tone 1 |
| FSQ | 94% | 100% | MFSK 2, CW beacon 2, THOR 1, SSB 1 |
| Packet | 94% | 100% | CW beacon 2, and 1 each for 4 others |
| SITOR-A | 88% | 100% | 1–2 each across 8 classes |
| 8PSK | 86% | 100% | 39-tone 4, SITOR-A 4, Hell 2 |

All new-mode errors are below −10 dB.

- **SITOR-A is a catch-all for weak signals.** 33 windows of other modes were called SITOR-A, for example MFSK 5, SITOR-B 5, FT8 4 and 8PSK 4.
- **Olivia/Contestia got worse at −10 dB and up:** 26 errors, against 18 for the batch 5 model. The fldigi decode check is not included in these numbers.

At confidence ≥ 0.9 (88% of windows), 97.1% were correct.

## 5. ID-only end-to-end (100 windows)

- No crashes, no decoders run, no decoded text stored, and no prompts containing message text.
- Label accuracy was 90%, and 66 of 100 windows got a frequency.
- Ollama is mocked, as in every batch.

## 6. Files

- New: `sigint/synth_b6.py`, `stress/verify_b6.py`, `stress/record_b6.sh`, `stress/run_b6.sh`, and the fldigi takes `data/fldigi_tx/{train,test}/psk8__*`.
- Changed:
  - `sigint/synth.py`: 38 CLASSES.
  - `sigint/features.py`: occupancy settings for psk8, fsq, packet and sitora.
  - `stress/record_fldigi.py`: the psk8 and fsq entries.
  - `stress/make_dataset.py`: mc6 mode.
  - `stress/train.py`: mc6 data, and fine-tuning to more classes.
