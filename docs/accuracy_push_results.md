# Pushing accuracy toward 99% (windows at −10 dB and up)

Runs 2026-11-20. Every test uses the same 3,300 windows: 100 per mode × 33 modes, SNR −20 to +15 dB
(2500 Hz reference). The target the user chose is the 2,358 windows at −10 dB or better.

The fldigi-based modes are tested on separate recordings from the ones used in training (different text, carrier and seed).

## Results

| Step | Model | All windows | ≥ −10 dB | Results file |
|---|---|---|---|---|
| Batch 5 model (8 epochs) | `resnet18_modes_b5.pt` | 83.4% | — | `results/classifier_b5_seed5.json` |
| Same data, 15 epochs | `resnet18_modes_b5e15.pt` | 87.1% | ~95% | `results/classifier_b5e15_seed5.json` |
| Round 1: 3-channel input, 25 epochs | `resnet18_modes_mc25.pt` | 88.5% | 95.4% | `results/classifier_mc25_seed5.json` |
| Round 2: 5x more real fldigi audio, +15 epochs | `resnet18_modes_mc2_15.pt` | 89.7% | 97.9% | `results/classifier_mc2_15_navfix_seed5.json` |
| Round 3: more MFSK/THOR/Olivia/Contestia audio, +10 epochs | `resnet18_modes_mc3_10.pt` | 90.2% | 97.9% | `results/classifier_mc3_10_seed5.json` |
| Round 3 + Olivia/Contestia decode check, v1 | same | 90.7% | 98.5% | `results/oc_check_v1_seed5.json` |
| Round 3 + decode check v2 (tries every sub-mode on weak windows) | same | 90.8% | 98.6% | `results/oc_check_seed5.json` |
| Round 3 + Olivia/Contestia check v2 + MFSK/THOR check | same | 90.9% | **98.7%** | `results/fam_check_seed5.json` |

Below −10 dB the windows stay hard: at −20 to −15 dB, 53% are right. Many of those signals are under their own decoders' working level.
For example, jt9 decodes FT8 reliably only from −18 dB up ([`results/ft8_jt9_seed0.json`](../results/ft8_jt9_seed0.json)).

## What each round changed

- **3-channel input** (`sigint/features.py: spectrogram_mc`). The original 15 s overview is now joined by two zoomed views:
  - A 1.46 Hz-resolution zoom around the strongest signal.
  - A 10.7 ms-resolution view of the middle 3.75 s.

  This removed nearly all FST4/JT9, JS8/FT8 and CW/beacon errors.
- **More real audio.** The fldigi modes had only about 40 s of recorded transmission per sub-mode. Rounds 2 and 3 added fldigi 4.2.03 recordings from 8 more seeds, so most fldigi modes now have about 800 s each, and MFSK/THOR/Olivia/Contestia have about 1,400 s.
- **Faulty test recording replaced.** The NAVTEX test take began with 12 s of plain carrier at the centre frequency, which is not 170 Hz FSK, and caused all the SITOR-B test errors. It was replaced with a clean re-recording. The note is in `data/fldigi_tx/rejected/README.txt`.
- **Training fixes:**
  - Each epoch is checkpointed, so a container restart doesn't lose the run.
  - The dataset builder no longer holds two copies in memory (the old one was OOM-killed).

## Olivia vs Contestia

Their on-air signals measure the same: each Olivia sub-mode and its Contestia twin share tones, symbol rate and bandwidth ([`results/fldigi_rates.json`](../results/fldigi_rates.json)).
Contestia is derived from Olivia ([sigidwiki: Contestia](https://www.sigidwiki.com/wiki/Contestia)).

At the user's request, when the classifier says Olivia or Contestia, `sigint/oc_check.py` plays the window into fldigi with each candidate sub-mode. The decoded text is scored and then discarded; it is never returned, logged or stored.

The rule looks at the Contestia decoder's output:
- On a Contestia signal it prints clean text.
- On an Olivia signal it prints punctuation-heavy garbage.

The rule's thresholds were set on 50 windows from the *training* recordings (`results/tune_oc.json`): 41 right, 0 wrong, 9 undecided.

| On the 3,300-window test | v1 | v2 |
|---|---|---|
| Windows checked | 175 | 175 |
| Windows the check decided | 99 | 170 |
| Fixed | 17 | 29 |
| Broken | 2 | 11 |
| Accuracy at −10 dB and up | 98.5% | 98.6% |
| Time per check | median 34 s, at most 68 s | median 68 s, at most 135 s |

v2 adds a fallback: when the occupancy estimate gives no bandwidth (or under 150 Hz), it tries all 8 Olivia/Contestia sub-modes tuned to the smoothed spectral peak. It decides almost every window, but most of the extra fixes and all of the extra breakages are below −10 dB. At −10 dB and up it gained 2 windows. fldigi decodes in real time, so each extra sub-mode adds about 17 s.

## MFSK vs THOR check (`sigint/mt_check.py`)

Approved by the user on 2026-11-21 under the same rules as Olivia/Contestia: the text is scored in memory and never stored or shown.

- **Why it can work:** MFSK and THOR share symbol rates (`results/fldigi_rates.json`), but THOR uses incremental frequency keying, while MFSK sends Varicode on plain tones ([sigidwiki: MFSK](https://www.sigidwiki.com/wiki/MFSK), [sigidwiki: THOR](https://www.sigidwiki.com/wiki/THOR)). A decoder of the wrong family prints junk.
- **How it runs:** the window is played into fldigi once for each candidate sub-mode. Candidates are picked by measured width: 4 or 5 sub-modes, or all 8 when the width is unknown.
- **The rule:** a family wins if one of its decoders prints at least 8 words, with at most 3% symbols and at least 85% plain letter/digit words, and no decoder of the other family does.
  - It uses only generic counts, nothing from the test transmissions' vocabulary.
  - On 60 training windows (`results/tune_mt.json`) it got 41 right, 0 wrong and 19 undecided. Every threshold on the grid gave 0 wrong.

| On the 3,300-window test (`results/fam_check_seed5.json`) | Value |
|---|---|
| Windows checked | 206 |
| Decided | 89 |
| Fixed / broken, all windows | 6 / 2 |
| Fixed / broken, −10 dB and up | 3 / 1 |
| Time per check | median 92 s, at most 147 s |
| Whole test run | 10.8 h |

## Accuracy at −10 dB and up, with and without the checks (same 2,358 windows)

| Checks used | Accuracy |
|---|---|
| None | 97.9% |
| Olivia/Contestia | 98.6% |
| Olivia/Contestia + MFSK/THOR | 98.7% |
| Both, with Olivia/Contestia and MFSK/THOR each counted as one family | 99.4% |

## What still blocks 99% at −10 dB and up (31 errors in 2,358; 99% allows 23)

| Error | Count | Why |
|---|---|---|
| Contestia → Olivia | 8 | 7 of them were called Olivia *by the decode check*, all between −9 and −3 dB. A weak Contestia signal also decodes to junk in the Contestia decoder, which the rule reads as "Olivia". The training windows used to set the rule did not show this. |
| MFSK ↔ THOR | 9 | 8 were left undecided, 5 of them at +1.5 dB or better. The correct decoder does not produce clean text in a 15 s window often enough. |
| Others | 14 | Spread across 11 pairs, 1–2 each |

## Files

- New: `sigint/oc_check.py`, `sigint/mt_check.py`, `stress/tune_oc.py`, `stress/tune_mt.py`, `stress/measure_fldigi_rates.py`, `stress/run_mc*.sh`, `stress/record_more*.sh`.
- Changed:
  - `sigint/features.py`: spectrogram_mc.
  - `sigint/model.py`: 1 or 3 input channels.
  - `sigint/pipeline.py`: featurize.
  - `stress/train.py`: resume, init, max-LR.
  - `stress/make_dataset.py`: mc mode, lower memory.
  - `stress/run_all.py`: SNR ≥ −10 metrics, oc_check, acf_check.
- Also tried: an autocorrelation-period check for the military modems (`sigint/acf.py`). It fixed 5 windows and broke 4, so it doesn't help.

## Stopped here (user's choice, 2026-11-21)

The user chose to stop at 98.7% and move on to batch 6. Two fixes were started but not tested, and the code was put back to the tested version:
- **Olivia/Contestia:** re-tune the rule on weak (−10 to 0 dB) training windows, so that junk from the Contestia decoder stops counting as "Olivia". Partial tuning data is in `results/tune_oc_low.json`.
- **MFSK/THOR:** turn fldigi's AFC on, and add THOR22 to the narrow-signal candidates. In tuning, MFSK8/16/32 failed at +9 to +11 dB, and a 377 Hz THOR22 window never had its own decoder tried.
