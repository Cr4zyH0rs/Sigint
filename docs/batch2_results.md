# Batch 2 results: FT4, JS8, WSPR, JT65, JT9, FST4, Q65 (ID-only)

Run 2026-11-19. Classifier retrained on 13 classes (the 6 from the first round plus these 7),
5,200 synthetic training windows, 8 epochs on CPU. Test: 100 fresh windows per class at
random SNR from −20 to +15 dB (2500 Hz reference), 1,300 windows total, plus 100 random
windows through the ID-only pipeline. Raw numbers: `results/classifier_seed2.json`,
`results/batch2_occupancy_seed0.json`, `results/end_to_end_seed2.json`.

## Where the test audio came from

| Mode | Source | Check that it's right |
|---|---|---|
| JT65, JT9, FST4, Q65 | WSJT-X's own simulators (`jt65sim`, `jt49sim`, `fst4sim`, `q65sim`), real encoder and modulator | Built by WSJT-X |
| FT4 | Symbols from WSJT-X `ft4code`, modulated here (4-GFSK, 20.833 Hz, 48 ms, BT 1) | Real `jt9 -5` decoded 10/10 of my FT4 clips at −8 dB |
| WSPR | Symbols from WSJT-X `wsprsim -c`, modulated here (4-FSK, 1.465 Hz, 0.683 s) | Real `wsprd` decoded my 2-minute clip at −10 dB |
| JS8 | Synthetic: FT8 symbols with a stand-in sync pattern (8-FSK, 6.25 Hz, 160 ms) | **Not verified**: JS8Call isn't installed here and its sync arrays weren't checked |

Longer transmissions (WSPR 110 s, JT65/JT9 ~50 s, FST4-60, Q65-30) are cut to a random
15 s slice, because the pipeline always looks at 15 s at a time.

## Classifier, 100 windows per mode

| Mode | Correct | Most common mistake |
|---|---|---|
| FT4 | 99% | — |
| WSPR | 98% | — |
| PSK31 | 98% | — |
| SSB voice, noise | 100% | — |
| JT65 | 94% | Q65 (3) |
| RTTY | 93% | SSB (4) |
| CW | 90% | SSB (6) |
| Q65 | 86% | SSB (5), JT65 (4) |
| **FT8** | **77%** (was 97% before JS8 was added) | JS8 (18) |
| **FST4** | **70%** | JT9 (19), WSPR (7) |
| **JT9** | **63%** | WSPR (34) |
| **JS8** | **47%** | FT8 (46) |
| **All 13** | **85.8%** (99.6% when confidence ≥ 0.9, which 56% of windows reach) | |

ID-only end-to-end with the new model: 0 crashes, 100 windows logged, 0 decoders run,
0 message text stored, 84% labels correct.

## What this means

1. **FT8 and JS8 look almost the same to a spectrogram.** Both are 8-tone, 6.25 Hz-spaced,
   160 ms symbols, 79 symbols (sigidwiki lists both at 50 Hz bandwidth:
   https://www.sigidwiki.com/wiki/FT8 , https://www.sigidwiki.com/wiki/JS8 ). The classifier
   can't tell them apart reliably. Since my JS8 is a stand-in, the real split may differ, but
   the shapes are inherently close.
2. **JT9, WSPR and FST4 are all very narrow, slow MFSK** (sigidwiki: JT9 from 16 Hz, WSPR 6 Hz,
   FST4 from 1 Hz: https://www.sigidwiki.com/wiki/JT9 , https://www.sigidwiki.com/wiki/WSPR ,
   https://www.sigidwiki.com/wiki/FST4 ). At this spectrogram's 23 Hz frequency resolution
   they blur into similar thin lines.
3. **The fix for both is frequency, not a bigger model.** These modes live on different dial
   frequencies (sigidwiki: FT8 14.074 MHz, JS8 14.078 MHz, WSPR 14.0956 MHz on 20 m). The
   pipeline already stores the dial frequency (`--dial-hz`) and the audio offset, so it can
   break ties by RF frequency. A finer spectrogram (≤ 6 Hz bins) for narrow signals would also
   help JT9/WSPR/FST4. I'd do both before adding more modes.

## Frequency and bandwidth estimates (100 windows per mode)

| Mode | Found a signal | Centre within 25 Hz | Measured bandwidth (median) | Nominal (sigidwiki) |
|---|---|---|---|---|
| FT4 | 68% | 90% (max error 46 Hz, inside one FT4 width) | 79 Hz | 83 Hz |
| JS8 | 83% | 100% (median 2 Hz) | 53 Hz | 50 Hz |
| WSPR | 100% | 100% (median 0.2 Hz) | 15 Hz | 6 Hz |
| JT9 | 98% | 100% (median 0.7 Hz) | 23 Hz | 16 Hz (JT9A) |
| JT65 | 94% | — | 18 Hz | 180 Hz (JT65A) |
| FST4 | 84% | — | 26 Hz | 1–67 Hz by sub-mode |
| Q65 | 83% | — | 32 Hz | 19–1700 Hz by sub-mode |

JT65 and Q65 bandwidth is badly underestimated. The estimator grows outward from the
strongest tone, and these modes spread weak data tones far from their sync tone. A per-mode
nominal bandwidth from the mode table is the simple fix; a smarter estimator is the better one.

## References

- WSJT-X 2.7.0 User Guide (FT4/FT8/JT65/JT9/WSPR/FST4/Q65 parameters): https://wsjt.sourceforge.io/wsjtx-doc/wsjtx-main-2.7.0.html
- Franke, Somerville & Taylor, "The FT4 and FT8 Communication Protocols", QEX 2020: https://downloads.hamradiodeluxe.com/FT4_FT8_QEX.pdf
- sigidwiki mode pages linked above, and the full eligibility list in `docs/ic7300_sigidwiki_signals.md`
- JS8Call: https://js8call.com
