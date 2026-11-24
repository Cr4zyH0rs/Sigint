# Batch 14: IC-7100 VHF/UHF FM signals (ID-only)

Run 2026-11-24. 100 test windows per mode, random SNR −20 to +15 dB (2500 Hz reference), seed 5.
This batch only identifies signals. Nothing is demodulated or decoded, and every payload is random.

Raw numbers:
- `results/verify_b14_seed14.json`: checks against the published parameters
- `results/classifier_b14_10_seed5.json`: classifier test, 71 classes, with signature checks (the live setting)
- `results/classifier_b14_10_nocheck_seed5.json`: the same test without checks
- `results/end_to_end_seed5.json`: ID-only pipeline run
- `results/train_history_b14_10.json`: training log

## 1. What the IC-7100 gives the computer

- **Receive range:** 0.030–199.999 MHz and 400–470 MHz. Modes include FM, DV (D-STAR) and WFM ([Icom America](https://icomamerica.com/lineup/products/IC-7100USA/)).
- **FM selectivity:** more than 12 kHz at −6 dB ([Icom brochure](https://www.qsl.net/ab4oj/icom/ic7100/IC-7100_USA.pdf)).
- **USB audio:** with ACC/USB Output Select = AF, the USB port carries "the received audio" ([manual p. 190](https://www.manualslib.com/manual/1419805/Icom-Ic-7100.html?page=190)). That is normal FM receiver audio, not raw discriminator output.
- **9600 bps data:** only available on DATA2 pin 3, not on USB ([manual p. 338](https://www.manualslib.com/manual/834640/Icom-Ic-7100.html?page=338)).

So this batch adds VHF/UHF signals that live in the voice band. HF on the IC-7100 is the same set the IC-7300 already covers.

## 2. Modes and sources

| Class | How the audio is made | Source |
|---|---|---|
| `aprs` | Dire Wolf's own modulator (`gen_packets`, Debian `direwolf` 1.7); random calls and positions | [Bell 202](https://en.wikipedia.org/wiki/Bell_202_modem): 1200/2200 Hz, 1200 bit/s; [AX.25](https://en.wikipedia.org/wiki/AX.25): NRZI; [sigidwiki: APRS](https://www.sigidwiki.com/wiki/APRS): 144.390 / 144.800 MHz |
| `pocsag` | Built from the standard: ≥ 576-bit 1010 preamble, sync 0x7CD215D8, batches of 16 BCH(31,21)+parity codewords, idle 0x7A89C197; 512 / 1200 / 2400 bit/s | [ITU-R M.584-2](https://www.itu.int/dms_pubrec/itu-r/rec/m/R-REC-M.584-2-199711-I!!PDF-E.pdf), [Wikipedia: POCSAG](https://en.wikipedia.org/wiki/POCSAG), [sigidwiki: POCSAG](https://www.sigidwiki.com/wiki/POCSAG) |
| `same` | NOAA Weather Radio / EAS alert: header ×3 with 1 s pauses, attention tone (853+960 Hz, or 1050 Hz for NWR), end-of-message "NNNN" ×3. The AFSK comes from minimodem's `same` mode (Debian `minimodem` 0.24) | [47 CFR 11.31](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-11/subpart-B/section-11.31): 520.83 bit/s, 2083.3/1562.5 Hz, 16 × 0xAB; [Wikipedia: SAME](https://en.wikipedia.org/wiki/Specific_Area_Message_Encoding) |
| `mdc1200` | Motorola MDC-1200 ID bursts (1200 Bd, 1200/1800 Hz) at the start and/or end of voice overs | [Wikipedia: MDC-1200](https://en.wikipedia.org/wiki/MDC-1200) |
| `selcall_ccir` | CCIR 5-tone selective calling, CCIR-1 (100 ms tones) and CCIR-2 (70 ms), with the repeat tone | [sigidwiki: CCIR Selcall](https://www.sigidwiki.com/wiki/CCIR_Selcall) |

**Dropped:**
- **ACARS:** only "AM, MSK, 5 kHz" was found ([sigidwiki](https://www.sigidwiki.com/wiki/ACARS)). No source read gave the bit rate, tones or sync.
- **FLEX paging:** only the rates (1600/3200/6400) and the 1.875 s frame were found ([Wikipedia](https://en.wikipedia.org/wiki/FLEX_(protocol)), [ITU-R M.584-2](https://www.itu.int/dms_pubrec/itu-r/rec/m/R-REC-M.584-2-199711-I!!PDF-E.pdf)). No sync word or deviation was found.
- **ZVEI selcall:** its sigidwiki page failed to load.
- **Digital voice heard on FM** (DMR, P25, D-STAR, NXDN): this would need more assumptions about the rig's audio filter. It could be its own later batch.
- **9600 bps packet and AIS:** these don't reach the USB port (see section 1).

**Assumptions** (also listed in `sigint/synth_b14.py`):
- **Receiver audio:** 300–3000 Hz. The IC-7100's audio response is not published.
- **POCSAG:** it is direct FSK, so it depends on the receiver's low-frequency response.
  - The training data uses a random low cut of 20–300 Hz, with de-emphasis in half the windows.
  - With a 300 Hz low cut, the test decoder can no longer read the pages (section 3).
- **Traffic patterns:** these are assumed:
  - APRS: 1–8 packets per window, with digipeated copies.
  - POCSAG: 1–6 transmissions per window.
  - MDC-1200: bursts on 2–6 s voice overs.
  - Selcall: 1–4 calls per window.
- **MDC-1200:** the preamble and sync word are assumed, because neither is published in the pages read.
- **SAME:** 1–4 s of silence stands in for the spoken message.

## 3. Checks (`stress/verify_b14.py`, clean audio)

multimon-ng is an independent decoder. It was run only on our own random test frames, to count how many it accepts. Its text output is discarded.

| Check | Measured | Published |
|---|---|---|
| APRS tones | 1195 / 2205 Hz | 1200 / 2200 Hz |
| APRS frames accepted by multimon-ng | 10 of 10 | (valid AX.25 frames) |
| POCSAG addresses accepted, raw FSK audio | 4/4 (512), 5/5 (1200), 5/6 (2400) | ITU-R M.584-2 frame format |
| POCSAG, with de-emphasis only | 4/4, 5/5, 1/6 | |
| POCSAG, with a 300–3000 Hz pass band | 0 at every rate | |
| SAME tones / bit length | 1565 / 2085 Hz, 1.92 ms | 1562.5 / 2083.3 Hz, 1.92 ms |
| SAME headers | 1 message decoded from the 3 header copies | header sent 3 times |
| MDC-1200 tones | 1175 / 1795 Hz | 1200 / 1800 Hz |
| CCIR selcall "12234" | 1124, 1197, 2110 (repeat), 1275, 1358 Hz; 100 / 70 ms | the same tones; 100 / 70 ms |

## 4. Classifier, 71 classes, 100 windows each (`resnet18_modes_b14_10.pt`)

The 66-class model `resnet18_modes_b11_10.pt` was fine-tuned for 10 epochs to 71 classes. Validation accuracy ended at 95.3%.

| | Batch 11 model (v0.11.1) | **Batch 14 model, with checks** | Batch 14 model, no checks |
|---|---|---|---|
| All windows | 87.26% | **87.76%** | 88.08% |
| SNR −10 dB and up | 98.10% | **98.41%** | 98.43% |
| SNR 0 dB and up | 99.00% | **99.11%** | 99.11% |
| Windows reported "unknown" | 229 | 169 (6 at −10 dB and up, 0 at 0 dB and up) | 0 |

| SNR | −20…−15 | −15…−10 | −10…−5 | −5…0 | 0…5 | 5…10 | 10…15 |
|---|---|---|---|---|---|---|---|
| Accuracy | 38% | 83% | 96% | 98% | 99% | 99% | 99% |

| New mode | Correct (all SNR) | At −10 dB and up | Mistaken for (all SNR) |
|---|---|---|---|
| NOAA/EAS SAME | 93% | 98.6% | unknown 2, and 1 each for 5 others |
| POCSAG | 91% | 100% | SSB 2, STANAG 4539 2, selcall 2, and 1 each for 3 others |
| APRS | 89% | 100% | selcall 4, and 1 each for 5 others |
| CCIR selcall | 83% | 97.3% | unknown 6, STANAG 4539 3, and 1–2 each for 4 others |
| MDC-1200 | 79% | 98.5% | SSB 7, unknown 6, selcall 4, and 1–2 each for 2 others |

- **At −10 dB and up the new modes made 4 errors in all.** The older classes are unchanged: Olivia/Contestia 30 errors, MFSK→THOR 5, MIL-110 serial/STANAG 4539 mix-ups.
- **CCIR selcall is a new weak-signal catch-all.** It got 73 windows of other modes, almost all below −10 dB. It has no signature check yet. Its tones are fixed ([sigidwiki](https://www.sigidwiki.com/wiki/CCIR_Selcall)), so one could be added the same way as for DTMF.
- **MDC-1200 is mistaken for SSB.** Most of an MDC window is speech, and the ID burst lasts only 0.15 s.

## 4a. CCIR selcall signature check (v0.12.1)

You approved this on 2026-11-24. A `selcall_ccir` label is now kept only if the audio holds CCIR tones in sequence. Otherwise the window is reported as "unknown" (`sigint/signature.py`).

**How the check works:**
- The tones are from the [sigidwiki table](https://www.sigidwiki.com/wiki/CCIR_Selcall).
- Every 5 ms, a 40 ms frame is checked: the strongest CCIR tone must stand 3 dB clear of the band floor and of the other CCIR tones.
- The score counts single-tone segments 30–120 ms long, in runs of at least 3 different tones back to back. A 5-tone call scores 5.

**Threshold: 3.** It was tuned on 40 training-seed windows per class (`results/signature_tune_b14.json`, `results/signature_tune_rows.json`). Any threshold from 1 to 5 blocked all 13 false selcall labels there with no loss at −10 dB and up. 3 is the middle of that range. The test gave the same results at threshold 1.

| 100 windows per mode | Before (v0.12.0) | **With the selcall check** |
|---|---|---|
| Windows of other modes called selcall | 73 | **0** |
| Windows given a wrong mode label | 700 | **627** |
| Real selcall correct, all SNR / −10 dB and up | 83% / 97.3% | 68% / 91.8% |
| SNR −10 dB and up | 98.41% | 98.33% |
| SNR 0 dB and up | 99.11% | 99.07% |
| Windows reported "unknown" | 169 | 257 (14 at −10 dB and up, 3 at 0 dB and up) |

**The cost:** 4 real selcall windows at −10 dB and up are now "unknown" instead of correct. Of 80 extra selcall windows at 0 dB and up, all passed the check, so the misses are weak or partly cut-off calls.

ID-only end-to-end run: no crashes, nothing decoded or stored, label accuracy 88%.

## 5. ID-only end-to-end (100 windows)

- No crashes, no decoders run, no decoded text stored, and no prompts containing message text.
- Label accuracy was 88%, and 65 of 100 windows got a frequency.
- Ollama is mocked, as in every batch.

## 6. Files

- New:
  - `sigint/synth_b14.py`, `stress/verify_b14.py`, `stress/run_b14.sh`, `docs/batch14_results.md`
- Changed:
  - `sigint/synth.py`: 71 CLASSES.
  - `sigint/features.py`: settings for the new modes.
  - `stress/make_dataset.py`: mc14 mode.
  - `stress/train.py`: mc14 data.
- New setup step (training only): `apt install direwolf minimodem`. multimon-ng is used only by `verify_b14.py`.
