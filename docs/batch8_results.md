# Batch 8: FreeDV, Robust Packet Radio and DTMF (ID-only)

Run 2026-11-23. 100 test windows per mode, random SNR −20 to +15 dB (2500 Hz reference).
This batch only identifies signals. Nothing is demodulated or decoded. FreeDV is fed random noise
in place of speech, and the other payloads are random.

Raw numbers:
- `results/verify_b8_seed8.json`: checks against the specs
- `results/classifier_b8_10_seed5.json`: classifier test, 48 classes
- `results/end_to_end_seed5.json`: ID-only pipeline run
- `results/train_history_b8_10.json`: training log

## 1. Modes and sources

| Class | How the audio is made | Source |
|---|---|---|
| `freedv1600` | codec2 1.2.0's own FreeDV modulator (`tools/freedv_tx_min.c`, libcodec2 `freedv_tx`), mode 1600 | [sigidwiki: FDMDV](https://www.sigidwiki.com/wiki/Frequency_Division_Multiplex_Digital_Voice_(FDMDV)): 14 DQPSK carriers at 50 Bd, 75 Hz apart, plus a centre BPSK pilot; FreeDV 1600 is 1.3 kHz wide |
| `freedv700c` | Same modulator, mode 700C | [sigidwiki: FreeDV COHPSK](https://www.sigidwiki.com/wiki/FreeDV_COHPSK): 14-carrier coherent QPSK, 1.5 kHz |
| `freedv700de` | Same modulator, modes 700D and 700E (one class) | [codec2 README_freedv](https://github.com/drowe67/codec2/blob/main/README_freedv.md): 700D 17-carrier OFDM/QPSK, 1000 Hz; 700E 21-carrier OFDM/QPSK, 1500 Hz |
| `rpr` | Built from its spec: 8 carriers 60 Hz apart, 50 Bd each, DBPSK (200 bps) or DQPSK (600 bps), centre 1500 Hz, 160 ms preamble per packet | [sigidwiki: Robust PACKET](https://www.sigidwiki.com/wiki/Robust_PACKET), [Wavecom RPR datasheet](https://wavecom.ch/content/pdf/advanced_protocol_robust-packet.pdf) |
| `dtmf` | Standard tone pairs. Keying speeds are Whelen 40/20 ms, Motorola 250/250 ms, Genave 20/20 ms and Federal Signal 35/5 or 1000/1000 ms, plus manual keying. | [sigidwiki: DTMF](https://www.sigidwiki.com/wiki/Dual_Tone_Multi_Frequency_(DTMF)), tone table: [Wikipedia: DTMF](https://en.wikipedia.org/wiki/Dual-tone_multi-frequency_signaling) |

**Assumptions** (not stated in the sources above; also listed in `sigint/synth_b8.py`):
- **FreeDV:**
  - Half the windows have the carrier on throughout. The other half have overs of 3–15 s with gaps of 0.5–4 s.
  - ±50 Hz mistuning.
  - 700D and 700E share one class.
- **RPR:**
  - Raised-cosine symbol edges.
  - Packets of 1–6 s with gaps of 0.3–4 s.
  - The preamble is 8 BPSK symbols on all 8 carriers (64 symbols in 160 ms, as Wavecom states).
- **DTMF:**
  - 3–16 digits.
  - The mix of timing profiles.
  - 0–10 dB twist between the two tones.

**New setup step:** FreeDV needs `apt install codec2 libcodec2-dev`, then
`gcc -O2 -o tools/freedv_tx_min tools/freedv_tx_min.c -lcodec2 -lm`. Only training needs this; identifying signals on the rig does not.

## 2. Checks against the specs (`stress/verify_b8.py`, clean audio)

| Check | Measured | Published |
|---|---|---|
| FreeDV 1600 width | 99% bandwidth 1222 Hz, centre 1499 Hz, strongest line (pilot) 1487 Hz | 1.125–1.3 kHz, centre pilot at 2× power |
| FreeDV 700C width | 1458 Hz | 1.5 kHz |
| FreeDV 700D width | 1166 Hz | 1000 Hz (README); the extra is roll-off counted in the 99% figure |
| FreeDV 700E width | 1646 Hz | 1500 Hz |
| RPR carriers (DBPSK, lines in x²) | 8 carriers, 1290 to 1710 Hz, 60.1 Hz apart | 8 carriers, 60 Hz, centre 1500 Hz |
| RPR width | 514 Hz (BPSK), 516 Hz (QPSK) | 500 Hz |
| RPR preamble | 160 ms | 160 ms |
| DTMF | Each detected pair is one row tone plus one column tone; Whelen tone length 41 ms | Q.23 table; 40 ms |

## 3. Classifier, 48 classes, 100 windows each (`resnet18_modes_b8_10.pt`)

The 43-class model `resnet18_modes_b7_10.pt` was fine-tuned for 10 epochs to 48 classes.
Validation accuracy reached 95.9% (epochs 9 and 10).

| | Batch 7 model (43 classes) | Batch 8 model (48 classes) |
|---|---|---|
| All windows | 90.0% | 89.3% |
| SNR −10 dB and up | 98.6% | **98.5%** |

Neither row uses the fldigi decode checks.

| SNR | −20…−15 | −15…−10 | −10…−5 | −5…0 | 0…5 | 5…10 | 10…15 |
|---|---|---|---|---|---|---|---|
| Accuracy | 46% | 86% | 97% | 99% | 99% | 98% | 99% |

| New mode | Correct (all SNR) | At −10 dB and up | Mistaken for (all SNR) |
|---|---|---|---|
| FreeDV 1600 | 92% | 100% | MSK144 3, MIL-110 serial 2, and 1 each for 3 others |
| RPR | 90% | 100% | DTMF 4, MIL-110 serial 2, PACTOR III 2, and 1 each for 2 others |
| FreeDV 700C | 89% | 100% | PACTOR III 5, SSB 2, and 1 each for 4 others |
| DTMF | 88% | 95.9% | ALE 4, MIL-110 serial 3, and 1 each for 5 others |
| FreeDV 700D/E | 78% | 98.6% | FreeDV 700C 9, MT63 5, PACTOR III 3, MSK144 2, and 1 each for 4 others |

- **DTMF is the new catch-all for weak signals.** 108 windows of other modes were called DTMF, spread over 33 classes, for example MSK144 10, SELCAL 9, SSB 7 and ALE 7. A DTMF window is mostly silence with short tone bursts, so a weak, bursty signal of any kind looks like it. It replaces CW beacon (51 windows in batch 7). Noise windows were still 100% correct.
- **The new-mode errors at −10 dB and up are:** DTMF called ALE twice and FSQ once, and FreeDV 700D/E called 700C once.
- **Olivia/Contestia:** 31 errors at −10 dB and up, against 28 in batch 7. The fldigi decode check is not included here.

At confidence ≥ 0.9 (88% of windows), 97.0% were correct.

## 4. ID-only end-to-end (100 windows)

- No crashes, no decoders run, no decoded text stored, and no prompts containing message text.
- Label accuracy was 83%, and 65 of 100 windows got a frequency.
- Ollama is mocked, as in every batch.

## 5. Not done in this batch

- No separate frequency and bandwidth test for the new modes.
- The DTMF catch-all is not fixed. One option is to require at least one clean tone pair (both tones on the Q.23 grid) before accepting a DTMF label. This is untested.

## 6. Files

- New: `sigint/synth_b8.py`, `tools/freedv_tx_min.c`, `stress/verify_b8.py`, `stress/run_b8.sh`.
- Changed:
  - `sigint/synth.py`: 48 CLASSES.
  - `sigint/features.py`: settings for the new modes.
  - `stress/make_dataset.py`: mc8 mode.
  - `stress/train.py`: mc8 data.
