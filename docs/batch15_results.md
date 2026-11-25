# Batch 15: digital voice heard on an FM receiver (ID-only)

Run 2026-11-25. 100 test windows per mode, random SNR −20 to +15 dB (2500 Hz reference), seed 5.
This batch only identifies signals. Nothing is demodulated, vocoded or decoded, and every payload bit is random.

Raw numbers:
- `results/verify_b15_seed15.json`: sync checks with an independent decoder
- `results/classifier_b15_10_seed5.json`: classifier test, 76 classes, with signature checks (the live setting)
- `results/classifier_b15_10_nocheck_seed5.json`: the same test without checks
- `results/end_to_end_seed5.json`: ID-only pipeline run
- `results/train_history_b15_10.json`: training log

## 1. What the rig hears

In FM mode the IC-7100's USB port carries normal receiver audio ([manual p. 190](https://www.manualslib.com/manual/1419805/Icom-Ic-7100.html?page=190)). An FM receiver's audio is the transmitter's frequency deviation over time. So a digital voice signal shows up as its 4-level FSK or GMSK baseband, shaped by the receiver's audio filters. The generators build that baseband and pass it through the same assumed audio chain as POCSAG in batch 14.

## 2. Modes and sources

| Class | Physical layer | Sources |
|---|---|---|
| `dmr` | 4FSK, 4800 symbols/s. 30 ms slots, 60 ms frame, 360 ms voice superframe. 264-bit burst = 2 × 108 payload + 48-bit sync. Two TDMA slots in 12.5 kHz | [ETSI TS 102 361-1](https://www.etsi.org/deliver/etsi_ts/102300_102399/10236101/02.06.01_60/ts_10236101v020601p.pdf), [Wikipedia](https://en.wikipedia.org/wiki/Digital_mobile_radio), [sigidwiki](https://www.sigidwiki.com/wiki/Digital_Mobile_Radio_(DMR)) |
| `p25` | Phase 1 C4FM, 4800 Bd, 9600 bit/s, 12.5 kHz, 12-bit NAC | [Wikipedia](https://en.wikipedia.org/wiki/Project_25), [sigidwiki](https://www.sigidwiki.com/wiki/Project_25_(P25)) |
| `dstar` | GMSK at 4800 bit/s. 20 ms frames, 420 ms superframe, 6.25 kHz | [sigidwiki](https://www.sigidwiki.com/wiki/D-STAR), [Wikipedia](https://en.wikipedia.org/wiki/D-STAR) |
| `ysf` | Yaesu System Fusion, C4FM, 12.5 kHz | [sigidwiki](https://www.sigidwiki.com/wiki/Yaesu_System_Fusion) |
| `nxdn` | NXDN48: 4FSK, 2400 Bd, 4800 bit/s, 6.25 kHz, ACF 80 ms | [sigidwiki](https://www.sigidwiki.com/wiki/Next_Generation_Digital_Narrowband_(NXDN)), [Wikipedia](https://en.wikipedia.org/wiki/NXDN) |

**What those pages leave out.** None of them gives the sync words, the pulse filters or the deviations. These come from the open-source MMDVM hotspot firmware and MMDVMHost (G4KLX, GPL), read 2026-11-25. This falls under your "any resource needed to identify signals" permission.

| Item | Value | File |
|---|---|---|
| DMR sync words | BS voice 0x755FD7DF75F7, BS data 0xDFF57D75DF5D, MS voice 0x7F7D5DD57DFD, MS data 0xD5D7F77FD757 | [MMDVM DMRDefines.h](https://github.com/g4klx/MMDVM/blob/master/DMRDefines.h) |
| DMR symbol map | dibit 01 = +3, 00 = +1, 10 = −1, 11 = −3 | DMRDefines.h symbol tables |
| DMR and YSF filter | root-raised cosine, roll-off 0.2 | [DMRTX.cpp](https://github.com/g4klx/MMDVM/blob/master/DMRTX.cpp), [YSFTX.cpp](https://github.com/g4klx/MMDVM/blob/master/YSFTX.cpp) |
| P25 sync and frames | 0x5575F5FF77FF. Header 99 bytes, LDU 216 bytes (180 ms), terminator 18 or 54 bytes, TSDU 45 bytes | [MMDVMHost P25Defines.h](https://github.com/g4klx/MMDVMHost/blob/master/P25Defines.h) |
| P25 filter | raised cosine 0.2 (not root) | [P25TX.cpp](https://github.com/g4klx/MMDVM/blob/master/P25TX.cpp) |
| D-STAR | Gaussian BT 0.35. Bits sent LSB first, bit 1 = negative. Frame sync EA A6, 660-bit header, voice frame 9 + 3 bytes, slow-data sync 55 2D 16 every 21st frame, end pattern 55 55 55 55 C8 7A | [DStarTX.cpp](https://github.com/g4klx/MMDVM/blob/master/DStarTX.cpp), [MMDVMHost DStarDefines.h](https://github.com/g4klx/MMDVMHost/blob/master/DStarDefines.h) |
| YSF | 120-byte frame (100 ms), sync 0xD471C9634D, FICH 200 bits | [MMDVMHost YSFDefines.h](https://github.com/g4klx/MMDVMHost/blob/master/YSFDefines.h), [MMDVM YSFDefines.h](https://github.com/g4klx/MMDVM/blob/master/YSFDefines.h) |
| NXDN | 384-bit frame (80 ms at 2400 Bd, which matches sigidwiki's 80 ms ACF), sync 0xCDF59, RRC 0.2 | [MMDVM NXDNDefines.h](https://github.com/g4klx/MMDVM/blob/master/NXDNDefines.h), [NXDNTX.cpp](https://github.com/g4klx/MMDVM/blob/master/NXDNTX.cpp) |

**Deviation (inferred).** MSK means a modulation index of 0.5, so D-STAR deviates ±1200 Hz. MMDVM's level ratios then give:
- DMR ±1944/648 Hz
- P25 ±1798/599 Hz
- YSF ±2701/900 Hz
- NXDN ±1049/350 Hz. The ±350 Hz matches sigidwiki's NXDN table.

The model does not depend on these numbers, because every window is normalised.

**Not included:**
- **P25 Phase 2:** no slot timing found in the pages read.
- **NXDN96:** MMDVM only implements 2400 Bd NXDN.
- **dPMR:** not looked at.

**Assumptions** (also listed in `sigint/synth_b15.py`):
- **Receiver audio:** the same chain as batch 14's POCSAG:
  - a random low cut of 20–300 Hz and a 3000 Hz high cut
  - de-emphasis in half the windows
  - a random sign, because the IC-7100's discriminator polarity is not published
- **Carrier-off time is silent.** With the squelch open, the real rig would give FM noise there.
- **Random bits:** payload, EMB, CACH, NID (apart from a fixed per-window NAC), FICH and header bits are all random. P25 status symbols are left out.
- **Traffic:**
  - DMR: a repeater with both slots in 60% of windows, direct mode (a 27.5 ms burst every 60 ms) in 40%.
  - P25 and NXDN: a continuous control channel in 25% of windows.
  - Overs last 1.5–10 s, with 0.3–4 s gaps.
  - Half of the overs start with an MMDVM-style preamble.

## 3. Checks (`stress/verify_b15.py`)

DSDcc (Debian package `dsdcc` 1.9.3) is an independent decoder. It was run only on our own random test transmissions (10 per mode), with audio output off. Only its "good sync found" lines are counted. DSDcc reports a sync when it gains lock, not on every frame, so the useful number is "transmissions detected".

| Mode | Clean audio | De-emphasis, 20–3000 Hz | 300–3000 Hz | Sync types seen |
|---|---|---|---|---|
| DMR repeater | 10/10 | 10/10 | 7/10 | +DMRv, +DMRd |
| DMR direct | 10/10 | 2/10 | 10/10 | +DMRv, +DMRd |
| D-STAR | 10/10 | 6/10 | 10/10 | +D-STAR, +D-STAR_HD |
| YSF | 10/10 (294 of 300 frame syncs) | 2/10 | 3/10 | +YSF |
| NXDN48 | 10/10 | 7/10 | 10/10 | +NXDN48 |
| P25 (own matched filter, not independent) | 10/10 (180/180) | 3/10 | 1/10 | |

DSDcc can't read P25. Its help text says P25 Phase 1 is "not supported", so P25 was checked with our own sync matcher instead.

As with POCSAG, the receiver's audio filters often stop a decoder. That matters for decoding, not for identifying the mode.

## 4. Classifier, 76 classes, 100 windows each (`resnet18_modes_b15_10.pt`)

The 71-class model was fine-tuned for 10 epochs to 76 classes. Validation accuracy ended at 94.2%.

| | v0.12.1 (71 classes) | **Batch 15, with checks** | Batch 15, no checks |
|---|---|---|---|
| All windows | 87.55% | **86.42%** | 86.79% |
| SNR −10 dB and up | 98.33% | **97.81%** | 97.94% |
| SNR 0 dB and up | 99.07% | **98.83%** | 98.86% |
| Windows reported "unknown" | 257 | 217 (16 at −10 dB and up, 3 at 0 dB and up) | 0 |

| SNR | −20…−15 | −15…−10 | −10…−5 | −5…0 | 0…5 | 5…10 | 10…15 |
|---|---|---|---|---|---|---|---|
| Accuracy | 36% | 78% | 95% | 98% | 98% | 99% | 99% |

| New mode | Correct (all SNR) | At −10 dB and up | Mistaken for (all SNR) |
|---|---|---|---|
| P25 | 85% | 100% | 1–2 each for 10 others |
| D-STAR | 76% | 93.1% | YSF 8, NXDN 6, DMR 3, unknown 3 |
| NXDN48 | 77% | 92.8% | D-STAR 9, YSF 4, DMR 2 |
| DMR | 65% | 88.7% | YSF 13, unknown 5, D-STAR 4 |
| YSF | 60% | 78.1% | DMR 22, unknown 7, D-STAR 4 |

- **The older classes are unchanged.** At −10 dB and up they made 87 errors (85 in v0.12.1). No window of an older mode was called a new mode at −10 dB and up.
- **The whole drop comes from the new modes.** They made 32 errors at −10 dB and up. Most are YSF ↔ DMR: 21 of them. Both are 4800 Bd 4FSK with RRC 0.2 shaping, so through voice-band audio they differ mainly in frame timing (a YSF sync every 100 ms, DMR's 30 ms slots).
- **New weak-signal catch-alls.** P25 and YSF took 43 and 40 windows of older modes, all below −10 dB. Neither has a signature check yet.

**A possible fix, not done.** Add a frame-sync signature check for the 4FSK group. It would correlate the audio with each mode's sync word, which is in the MMDVM files above, at its known repeat interval (YSF 100 ms, DMR 30/60 ms, P25 180 ms, NXDN 80 ms). Labels that fail the check would become "unknown". It would use the same "unknown" rule as the selcall check.

## 5. ID-only end-to-end (100 windows)

- No crashes, no decoders run, no decoded text stored, and no prompts containing message text.
- Label accuracy was 89%, and 64 of 100 windows got a frequency.
- Ollama is mocked, as in every batch.

## 6. Files

- New:
  - `sigint/synth_b15.py`, `stress/verify_b15.py`, `stress/run_b15.sh`, `docs/batch15_results.md`
- Changed:
  - `sigint/synth.py`: 76 CLASSES.
  - `sigint/features.py`: settings for the new modes.
  - `stress/make_dataset.py`: mc15 mode. Older batch modes now use fixed class ranges, so a rebuild gives the same data.
  - `stress/train.py`: mc15 data.
- New setup step (checks only): `apt install dsdcc`. It is used only by `verify_b15.py`.
