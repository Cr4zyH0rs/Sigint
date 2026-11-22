# Batch 5: STANAG, MIL-STD-188-110 and PACTOR (ID-only)

Run 2026-11-19/20. 100 test windows per mode, random SNR −20 to +15 dB (2500 Hz reference).
This batch only identifies signals. Nothing is demodulated or decoded, and the generated payloads are random bits.

Raw numbers:
- `results/verify_b5_seed5.json`
- `results/batch5_occupancy_seed0.json`
- `results/classifier_seed5.json`
- `results/end_to_end_seed5.json`
- `results/tiebreak_seed5.json`

## 1. Modes and sources

No encoder for any of these modems is available here, and none is free and open. PACTOR II/III are proprietary (SCS).
So each one is generated in `sigint/synth_b5.py` from its published on-air description.

**Sources:**
- sigidwiki pages, read on 2026-11-19 through the wiki's API in your browser.
- The ARRL protocol pages for PACTOR, PACTOR-II and PACTOR-III, read the same day.

| Class | What is generated | Parameters and source |
|---|---|---|
| `stanag4285` | 2400 Bd single-tone PSK at 1800 Hz. Each 256-symbol frame has 80 BPSK sync symbols, then data blocks with 16-symbol known probes in between. | ACF 106.66 ms, 2750 Hz, BPSK/QPSK/8PSK ([sigidwiki](https://www.sigidwiki.com/wiki/STANAG_4285)) |
| `mil110_serial` | 2400 Bd PSK at 1800 Hz. Preamble of 200 ms segments (3 or 24). Body is 20 unknown + 20 known symbols, or 32 + 16, with a 160-symbol scrambler. | 2400 Bd, ACF header 200 ms, body 66.66 ms, 2750 Hz ([sigidwiki](https://www.sigidwiki.com/wiki/MIL-STD-188-110_Serial)) |
| `mil110_16tone` | 16 DQPSK tones, 935–2585 Hz, 110 Hz apart, 75 Bd. A 605 Hz pilot is present in half the windows. | 75 Bd per tone, 605 Hz pilot, 2100 Hz ([sigidwiki](https://www.sigidwiki.com/wiki/MIL-STD-188-110_Appendix_A_16-Tone)) |
| `mil110_39tone` | 39 DQPSK tones, 675–2812.5 Hz, 56.25 Hz apart, 44.44 Bd with a cyclic guard. 393.75 Hz pilot. 30% of windows are STANAG 4197 (no pilot). | 44.44 Bd, ~393 Hz pilot, 2400 Hz ([App B](https://www.sigidwiki.com/wiki/MIL-STD-188-110_Appendix_B_39-Tone), [STANAG 4197](https://www.sigidwiki.com/wiki/STANAG_4197)) |
| `pactor1` | 2-FSK with a 200 Hz shift at 100 or 200 Bd. 0.96 s packets, 0.12 s control signal, 1.25 s cycle. | [ARRL PACTOR](https://www.arrl.org/pactor), [sigidwiki](https://www.sigidwiki.com/wiki/PACTOR_I) (300 Hz) |
| `pactor2` | Two DPSK tones 200 Hz apart, 100 Bd, DBPSK through 16-DPSK. Short cycle (0.8 s packet, 0.28 s control signal, 1.25 s) or long cycle (3.28 s packet, 3.75 s). | [ARRL PACTOR-II](https://www.arrl.org/pactor-ii), [sigidwiki](https://www.sigidwiki.com/wiki/PACTOR_II) (450 Hz) |
| `pactor3` | Speed levels 1–6: 2/6/14/14/16/18 carriers on a 120 Hz grid at the ARRL carrier positions, 100 Bd DBPSK/DQPSK. | [ARRL PACTOR-III](https://www.arrl.org/pactor-iii), [sigidwiki](https://www.sigidwiki.com/wiki/PACTOR_III) |

In every window, the other station's ARQ control signals are 0 to 20 dB weaker, or not heard at all (30% of windows).

**Assumptions** (not stated in the sources above, marked `ASSUMED` in the code):
- The PSK pulse filter: root-raised-cosine, roll-off 0.15.
- The exact STANAG 4285 sync and scrambler sequences, and the 110 serial preamble content. Their periods follow the sigidwiki ACF values.
- The 39-tone pilot level (twice a data tone).
- PACTOR-III cycle timing, borrowed from PACTOR-II long packets, and its control signal.
- PACTOR-II/III symbol shaping. Hann-shaped symbols were chosen because they give PACTOR-II a 461 Hz 99% bandwidth, against 450 Hz on sigidwiki.

## 2. Checks against the specs (`stress/verify_b5.py`)

Each row measures clean (noise-free) audio and compares it with the published value.

| Check | Measured | Published |
|---|---|---|
| STANAG 4285 frame ACF | 106.67 ms (5/5) | 106.66 ms |
| 110 serial body ACF (20/20) | 66.67 ms (2 of 3; the third peaked at 133.33 ms, a multiple) | 66.66 ms |
| 110 serial preamble ACF | 200.0 ms | 200 ms |
| 16-tone grid | pilot 605 Hz, spacing 110–111 Hz, 13 ms symbols | 605 Hz, 75 Bd |
| 39-tone symbol rate (cyclic-prefix test) | 44.5 Hz, spacing 56 Hz | 44.44 Bd |
| PACTOR I | cycle 1.25 s, packet ≈0.96 s, CS ≈0.12 s, shift 200 Hz | ARRL |
| PACTOR II | cycles 1.25 s and 3.75 s, packets 0.82 s / 3.30 s (includes 20 ms smoothing), 99% bandwidth 461 Hz | ARRL 0.8 / 3.28 s, sigidwiki 450 Hz |
| PACTOR III | cycle 3.75 s, packet 3.28 s. Level 6 spans 208–2789 Hz at −40 dB; at −30 dB it spans 300–2700 Hz. | ARRL: 300–2700 Hz at −40 dB |

PACTOR III's −40 dB width comes out about 180 Hz wider than ARRL's figure. The symbol shaping I chose has slightly wider skirts than the real modem.

## 3. Frequency and bandwidth, 100 windows per mode

| Mode | No signal found | Centre error, median | Bandwidth, median | sigidwiki |
|---|---|---|---|---|
| STANAG 4285 | 39 | 6 Hz | 2.36 kHz | 2.75 kHz |
| 110 serial | 48 | 16 Hz | 2.50–2.56 kHz | 2.75 kHz |
| 110 16-tone | 58 | 81 Hz* | 2.12 kHz (with pilot), 1.83 kHz (without) | 2.1 kHz |
| 110 39-tone | 47 | 134 Hz* | 2.53 kHz (App B), 2.26 kHz (4197) | 2.4 kHz |
| PACTOR I | 26 | 3 Hz | 255 Hz (200 Bd), 308 Hz (100 Bd) | 300 Hz |
| PACTOR II | 41 | 2 Hz | 416–530 Hz | 450 Hz |
| PACTOR III | 55 | 4 Hz | 316 Hz (level 1†) to 2.20 kHz (level 6) | 400 Hz, 2.4 kHz |

\* The pilot tone pulls the energy centre below the middle of the data tones. This is expected, not a measurement error.

† Level 1 has two carriers 840 Hz apart, and the estimate measures only one of them.

**Fixed along the way:** at first, PACTOR II gave "no signal" even at +30 dB. The 600 Hz running-median noise floor sat inside the 450 Hz-wide signal. It now uses a global noise floor.
PACTOR I's centre also comes from the mark/space midpoint now (200 Hz shift), the same method RTTY uses.

"No signal found" is mostly below −10 dB, where these 2–2.5 kHz-wide signals spread their power thinly.

## 4. Classifier, 33 classes, 100 windows each (`data/resnet18_modes_b5.pt`)

Training ran for 8 epochs, and validation reached 84.2% at the end, still rising.

**Overall: 83.4%** (3,300 windows). With the frequency tie-breaker it is **85.2%** (76 fixed, 4 broken).
At confidence ≥ 0.9 (60% of windows), 99.8% were correct.

| SNR | Accuracy |
|---|---|
| −20 to −15 dB | 43% |
| −15 to −10 dB | 76% |
| Above −10 dB | 91–93% |

| New mode | Correct | Mistaken for |
|---|---|---|
| PACTOR II | 97% | Contestia 2 |
| PACTOR I | 92% | RTTY 2 |
| 110 16-tone | 85% | 110 serial 9 |
| STANAG 4285 | 84% | SSTV 3, PACTOR III 3, 110 serial 3 |
| PACTOR III | 84% | 110 serial 6, 16-tone 4 |
| 110 serial | 81% | 16-tone 8, 39-tone 4 |
| 110 39-tone | 76% | 16-tone 9, 110 serial 8 |

- **STANAG 4285 and 110 serial are rarely confused with each other** (3 each way), even though sigidwiki calls them "very similar". The frame structure differs enough.
- The new confusions are within the wide military group: 110 serial, the 16-tone and 39-tone modems, and PACTOR III. All are 2–2.5 kHz wide blocks.
- SSB voice is called 110 serial 3 times in 100.
- The old family confusions remain:
  - Olivia/Contestia: Contestia is at 40%, and 39 of its windows were called Olivia.
  - MFSK/THOR: MFSK improved to 73%.
  - CW/CW beacon: 82% and 76%.
- **Other classes that moved by 8 points or more since batch 4:**
  - Up: JS8 (55→73%), THOR (77→91%), SSTV (79→90%).
  - Down: FT8 (83→66%), ALE (93→84%).

## 5. ID-only end-to-end (100 windows, 33-class model)

- No crashes, no decoders run, no decoded text stored, and no prompts containing message text.
- Label accuracy was 85%, and 64 of 100 windows got a frequency.
- Ollama is mocked, as in every batch.

## 6. Suggestions

- **Measure the autocorrelation period directly.** sigidwiki lists it for many military modems, and the verification above already measures it reliably (106.67 vs 66.67 vs 200 ms). Used as a second check, it could separate 4285 from 110 serial with certainty, and help other PSK modems in later batches.
- Report modes as families where single 15 s windows can't tell them apart: Olivia/Contestia, MFSK/THOR, CW/beacon, and "wide military PSK/OFDM".
- Train for more epochs (12–15). Validation was still rising in batches 3, 4 and 5.

## 7. Files

- New: `sigint/synth_b5.py`, `stress/verify_b5.py`.
- Changed:
  - `sigint/synth.py`: 33 CLASSES.
  - `sigint/features.py`: occupancy settings for batch 5, and the PACTOR I pair-centre method.
  - `stress/make_dataset.py`, `stress/train.py`.
  - `stress/run_all.py`: the batch5_occupancy test.
