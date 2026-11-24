# Batch 11: wide military and NATO HF modems (ID-only)

Run 2026-11-24. 100 test windows per mode, random SNR −20 to +15 dB (2500 Hz reference), seed 5.
This batch only identifies signals. Nothing is demodulated or decoded, and every payload is random.

Raw numbers:
- `results/verify_b11_seed11.json`: checks against the published parameters
- `results/classifier_b11_10_nocheck_seed5.json`: classifier test, 66 classes, no signature checks
- `results/classifier_b11_10_seed5.json`: classifier test with the signature checks (the live setting)
- `results/end_to_end_seed5.json`: ID-only pipeline run
- `results/signature_tune.json`, `results/signature_tune_rows.json`: signature threshold tuning
- `results/train_history_b11_10.json`: training log

## 1. Modes and sources

| Class | What is built | Source |
|---|---|---|
| `stanag4539` | Serial tone at 1800 Hz, 2400 Bd, QPSK / 8PSK / 16QAM / 32QAM / 64QAM for 3200–12800 bit/s, 3000 Hz | [Shoc: STANAG 4539](https://cartoonman.github.io/Shoc/stanag4539.htm), [Shoc: 4539 HDR](https://cartoonman.github.io/Shoc/stanag4539hdr.htm), [sigidwiki: STANAG 4539](https://www.sigidwiki.com/wiki/STANAG_4539) (ACF 119.6 ms) |
| `stanag4529` | Serial tone, 1200 Bd, BPSK / QPSK / 8PSK, about 1.25 kHz wide | [Shoc: STANAG 4529](https://cartoonman.github.io/Shoc/stanag4529.htm), [sigidwiki: STANAG 4529](https://www.sigidwiki.com/wiki/STANAG_4529) (1.24 kHz, ACF 213.32 ms) |
| `ale3g` | 3G ALE (STANAG 4538): 8-PSK, 2400 Bd at 1800 Hz; bursts BW0, BW1, BW2, BW3, BW4 and BW5 with the published lengths, TLC 106.667 ms and preambles | [sigidwiki: 3G ALE](https://www.sigidwiki.com/wiki/Automatic_Link_Establishment_(3G_ALE_ARCS)), [Shoc: 3G ALE](https://cartoonman.github.io/Shoc/ale3g.htm) |
| `link11_slew` | Link-11 SLEW: single-tone 8-PSK, 2400 Bd, 3000 Hz; bursts of 0.1–2.0 s, pauses from 4 ms | [sigidwiki: Link-11](https://www.sigidwiki.com/wiki/Link-11), [Shoc: Link-11 SLEW](https://cartoonman.github.io/Shoc/link11slew.htm) |
| `stanag4481` | STANAG 4481 FSK: 850 Hz shift at 75, 100, 150, 300 or 600 Bd | [Shoc: STANAG 4481](https://cartoonman.github.io/Shoc/stanag4481.htm) |

**Planned modes that are not new classes:**
- **STANAG 4197:** 39 QPSK tones, 56.25 Hz apart ([sigidwiki](https://www.sigidwiki.com/wiki/STANAG_4197)). Batch 5 already builds it as the no-pilot sub-mode of `mil110_39tone`.
- **Link-11 CLEW:** 16 tones at 75 Bd ([sigidwiki: Link-11](https://www.sigidwiki.com/wiki/Link-11)). That is the same tone count and rate as `mil110_16tone` ([sigidwiki: 110 App. A](https://www.sigidwiki.com/wiki/MIL-STD-188-110_Appendix_A_16-Tone)). No page read gives CLEW's tone frequencies, so a CLEW signal is reported as `mil110_16tone`.
- **STANAG 4481 PSK:** BPSK, 2400 Bd, 1800 Hz, 3000 Hz ([Shoc](https://cartoonman.github.io/Shoc/stanag4481.htm)). These are the same parameters as `stanag4285`, so it is reported as that class.

**Pages that did not load:** sigidwiki's `3G_ALE`, `3G-ALE`, `Link_11_CLEW` and `Link_11_SLEW` pages. The Shoc pages and the sigidwiki pages linked above were used instead.

**Assumptions** (not stated in the sources; also listed in `sigint/synth_b11.py`):
- **STANAG 4539:**
  - The frame is 287 symbols, because ACF 119.6 ms × 2400 Bd = 287. It is split into 256 data and 31 known symbols.
  - A fixed 0.24 s preamble.
  - Square 16/64QAM and cross 32QAM.
  - Centre 1800 Hz ±50 Hz.
- **STANAG 4529:**
  - Uses STANAG 4285's frame layout at 1200 Bd. That gives 256 symbols = 213.33 ms, which matches the published ACF of 213.32 ms.
  - Centre 1800 Hz ±50 Hz.
- **3G ALE:**
  - Every burst is TLC, then preamble, then data. The published BW0, BW3 and BW5 lengths add up exactly this way.
  - Each 13.33 ms BW3 block is 16 data and 16 known symbols.
  - An exchange is a call, a reply and a confirm, then HDL traffic, LDL traffic, or nothing.
  - Gaps of 0.1–0.6 s; the two stations differ by 0–12 dB.
- **Link-11 SLEW:**
  - Carrier 1800 Hz ±50 Hz.
  - No frame structure, because none is published in the pages read.
  - Pauses of 4–150 ms; stations differ by up to 10 dB.
- **STANAG 4481:** centre 1700 Hz ±100 Hz.

## 2. Checks against the sources (`stress/verify_b11.py`, clean audio)

| Check | Measured | Published |
|---|---|---|
| STANAG 4539 frame period (ACF peak) | 119.58 ms at all six rates | ACF 119.6 ms |
| STANAG 4539 width (99%) / symbol-rate line | 2.50 kHz / 2400 Hz line 13–16 dB clear | 3000 Hz / 2400 Bd |
| STANAG 4529 frame period / width | 213.33 ms / 1.18 kHz; 1200 Hz line 36 dB clear | ACF 213.32 ms / 1.24–1.3 kHz / 1200 Bd |
| 3G ALE burst lengths | BW0 613.33, BW1 1306.67, BW2 (n=3) 1840.0, BW3 (n=64) 1226.67, BW4 640.0, BW5 1013.33 ms | 613.333, 1306.67, 640 + 3 × 400, 373.33 + 64 × 13.33, 640, 1013.33 ms |
| 3G ALE BW3 ACF | 13.33 ms | 13.3 ms |
| Link-11 SLEW width / symbol-rate line | 2.51 kHz / 2400 Hz line clear | 3000 Hz / 2400 Bd |
| STANAG 4481 shift | 850 Hz at all five bauds | 850 Hz |

## 3. Classifier, 66 classes, 100 windows each (`resnet18_modes_b11_10.pt`)

The 61-class model `resnet18_modes_b10_10.pt` was fine-tuned for 10 epochs to 66 classes. Validation accuracy ended at 95.1%. The training data no longer fits in memory, so `stress/train.py` now reads it from a memory-mapped file (`SIGINT_MMAP=1`).

| | Batch 10 model, with checks | Batch 11 model, no checks | **Batch 11 model, with checks** |
|---|---|---|---|
| All windows | 88.93% | 87.62% | **87.77%** |
| SNR −10 dB and up | 98.42% | 98.14% | **98.20%** |
| SNR 0 dB and up | 98.89% | 99.00% | **99.04%** |
| Confidence ≥ 0.9 | 97.40% | 96.74% | **97.17%** (86% of windows) |

| SNR | −20…−15 | −15…−10 | −10…−5 | −5…0 | 0…5 | 5…10 | 10…15 |
|---|---|---|---|---|---|---|---|
| Accuracy | 41% | 82% | 96% | 98% | 99% | 99% | 99% |

| New mode | Correct (all SNR) | At −10 dB and up | Mistaken for (all SNR) |
|---|---|---|---|
| STANAG 4481 | 94% | 100% | WWV 2, and 1 each for 4 others |
| STANAG 4529 | 91% | 100% | SSTV 3, STANAG 4285 2, multi-carrier PSK 2, and 2 others |
| 3G ALE | 84% | 96.1% | Link-11 SLEW 3, and 1–2 each for 10 others |
| Link-11 SLEW | 78% | 100% | 3G ALE 8, CW beacon 3, STANAG 4539 3, and 1–2 each for 6 others |
| STANAG 4539 | 69% | 94.1% | MIL-110 serial 7, CW beacon 4, PACTOR III 4, 3G ALE 4, and 1–2 each for 8 others |

- **STANAG 4539 and MIL-110 serial are mixed up.** At −10 dB and up there are 4 windows one way and 3 the other. MIL-110 serial fell from 95.7% to 91.3% at −10 dB and up. Both are 2400 Bd serial PSK at 1800 Hz.
- **Two new weak-signal catch-alls:** without checks, STANAG 4539 was given to 70 windows of other modes and 3G ALE to 46.
- **Olivia/Contestia:** 32 errors at −10 dB and up, against 34 in batch 10. The fldigi decode check is not included here.

## 4. Signature checks (`sigint/signature.py`)

The batch 10 checks (WWV, DTMF, HamDRM) stay at their v0.10.1 thresholds. One check is added:

| Label | Signature | Source |
|---|---|---|
| STANAG 4539 | Its ACF peak at 119.58 ms (287 symbols at 2400 Bd) must stand 1.5 robust z-units above lags 80–160 ms | [sigidwiki: STANAG 4539](https://www.sigidwiki.com/wiki/STANAG_4539) (ACF 119.6 ms) |

A 3G ALE check was tried: the 2400 Bd symbol-rate line ([sigidwiki](https://www.sigidwiki.com/wiki/Automatic_Link_Establishment_(3G_ALE_ARCS))). It is switched off: below −5 dB the line is too weak to separate real 3G ALE from other modes. Every threshold that blocked false labels also lost real 3G ALE windows at −10 dB and up.

The tuner (`stress/tune_signature.py`, 40 training-seed windows per class) proposed switching the DTMF check off and loosening WWV and HamDRM, with no loss at −10 dB and up. I kept the v0.10.1 thresholds instead, because you asked for these labels to need their real signature. On the tuning windows, the two choices give the same accuracy at −10 dB and up (98.99% against 99.04%) and the same at 0 dB and up.

**False labels (windows of other modes given the label), 100 test windows per mode:**

| Label | No checks | With checks |
|---|---|---|
| WWV | 75 | **22** |
| HamDRM | 77 | **20** |
| DTMF | 50 | **17** |
| STANAG 4539 | 70 | **44** |
| 3G ALE (no check) | 46 | 102 |
| **Total** | **318** | **205** |

**3G ALE is now where most blocked windows end up.** It went from 46 to 102 false labels, mostly from DTMF (12), 2G ALE (8), Link-11 SLEW (8) and HamDRM (7). These windows are below −10 dB. The checks move weak guesses from one label to another rather than making them right.

### 4a. "Unknown" instead of a second guess (v0.11.1)

You chose this on 2026-11-24. Now, when the top label fails its check, the pipeline reports "unknown" instead of the model's next choice (`sigint/signature.reweight`). Test: `results/classifier_b11_10_unknown_seed5.json`, same 100 windows per mode.

| | Next choice (v0.11.0) | **Unknown (v0.11.1)** |
|---|---|---|
| Windows given a wrong mode label | 807 | **612** |
| False labels on WWV, DTMF, HamDRM, STANAG 4539, 3G ALE | 205 | **113** |
| Windows reported "unknown" | 0 | 229 (9 at −10 dB and up, 1 at 0 dB and up) |
| All windows correct | 87.77% | 87.26% |
| SNR −10 dB and up | 98.20% | **98.10%** |
| SNR 0 dB and up | 99.04% | **99.00%** |

- 3G ALE false labels fell from 102 to 46, back to the level with no checks at all.
- In these figures an "unknown" counts as wrong. That is why accuracy falls slightly.
- ID-only end-to-end run: no crashes, nothing decoded or stored, label accuracy 86%.

## 5. ID-only end-to-end (100 windows)

- No crashes, no decoders run, no decoded text stored, and no prompts containing message text.
- Label accuracy was 87%, and 57 of 100 windows got a frequency.
- Ollama is mocked, as in every batch.

## 6. Not done in this batch

- No frame structure was found for STANAG 4539's probes, 3G ALE's preambles or Link-11 SLEW. Those parts are assumed, as listed in section 1.
- Link-11 CLEW's tone frequencies were not found, so it is not a separate class.
- No separate frequency and bandwidth test for the new modes.

## 7. Files

- New:
  - `sigint/synth_b11.py`, `stress/verify_b11.py`, `stress/run_b11.sh`, `docs/batch11_results.md`
- Changed:
  - `sigint/synth.py`: 66 CLASSES.
  - `sigint/features.py`: settings for the new modes.
  - `sigint/signature.py`: the STANAG 4539 check, plus a 3G ALE check that is switched off.
  - `stress/tune_signature.py`: new checks; the search starts with nothing blocked.
  - `stress/make_dataset.py`: mc11 mode.
  - `stress/train.py`: mc11 data and `SIGINT_MMAP=1`.
  - `data/signature_thresholds.json`.
