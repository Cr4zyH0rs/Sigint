# Signature checks for WWV, DTMF and HamDRM (false-label fix)

Run 2026-11-23/24 on the 61-class batch 10 model (`resnet18_modes_b10_10.pt`). The test set is the
same as batch 10: 100 windows per mode, SNR −20 to +15 dB, seed 5. Nothing is decoded.

Raw numbers:
- `results/classifier_b10_10_nocheck_seed5.json`: test without the checks
- `results/classifier_b10_10_sigcheck_seed5.json`: test with the checks
- `results/signature_tune.json`, `data/signature_thresholds.json`: threshold tuning

## 1. The problem

In batch 10 the model gave three labels to weak signals of many other modes:

| Label | Windows of other modes given this label |
|---|---|
| WWV | 87 |
| HamDRM | 70 |
| DTMF | 50 |

These windows were almost all below −10 dB.

## 2. The fix (`sigint/signature.py`)

A WWV, DTMF or HamDRM label is kept only if the audio shows that signal's published signature. Otherwise the model's next most likely class is used, and that class is checked too if it is one of the three.

| Label | Signature tested | Source |
|---|---|---|
| WWV/WWVH | A 5 ms tick at 1000 Hz (WWV) or 1200 Hz (WWVH) every 1.000 s. Test: a 5 ms matched filter, folded at exactly 1 s, must show a narrow peak. A 100 ms RWM pulse or a steady tone fails. | [NIST WWV/WWVH format](https://www.nist.gov/pml/div688/grp40/wwv_format) |
| DTMF | One row tone (697/770/852/941 Hz) and one column tone (1209/1336/1477/1633 Hz) at once, both 4 dB clear of the other tones and the floor, for at least 3 frames (about 30 ms). Tones last at least 20 ms. | [DTMF tone table](https://en.wikipedia.org/wiki/Dual-tone_multi-frequency_signaling), [sigidwiki: DTMF](https://www.sigidwiki.com/wiki/Dual_Tone_Multi_Frequency_(DTMF)) |
| HamDRM | DRM OFDM timing: 26⅔ ms symbols whose useful part is 24 ms (mode A) or 21⅓ ms (mode B). Test: the cyclic-prefix correlation at that lag, folded at 26⅔ ms, compared with a control lag. | [ETSI ES 201 980](https://www.etsi.org/deliver/etsi_ES/201900_201999/201980/04.03.01_60/es_201980v040301p.pdf), clause 4.4.2.2, table 2 |

The HamDRM check tests the published symbol timing, not the pilot layout. Our HamDRM generator's pilot layout is an assumption (batch 10), so checking pilots would only test the generator against itself.

**How the thresholds were set** (`stress/tune_signature.py`):
- 40 windows per class from the training recordings, with a different seed from the test set: 2,440 windows.
- The rule: get as many windows right as possible at all SNRs, without losing any accuracy at −10 dB and up.
- Resulting thresholds: WWV 4.5, DTMF 2 frames, HamDRM 1.5.
- The WWV check was rebuilt once. The first version, a band-pass envelope fold, removed only 2 of WWV's 87 false labels. The 5 ms matched filter separates real ticks from other signals much better: on 30 real WWV windows at −10 dB and up, 95% scored 10.6 or more, while no weak window of another mode scored above 5.2.

## 3. Results, 100 windows per mode

| | Without checks | With checks |
|---|---|---|
| All windows | 88.84% | 88.93% |
| **SNR 0 dB and up** | 98.85% | **98.89%** |
| SNR −10 dB and up | 98.40% | **98.42%** |
| Confidence ≥ 0.9 | 97.13% (88% of windows) | 97.40% (87% of windows) |

**False labels (windows of other modes given the label):**

| Label | Without checks | With checks |
|---|---|---|
| WWV | 87 | **27** |
| HamDRM | 70 | **20** |
| DTMF | 50 | **18** |
| **Total** | **207** | **65** |

**Cost to the real signals:**

| Class | Correct without checks | Correct with checks | At −10 dB and up, without → with |
|---|---|---|---|
| WWV | 89% | 87% | 92.5% → 93.8% |
| DTMF | 82% | 74% | 95.9% → 94.6% (one window) |
| HamDRM | 82% | 77% | 98.4% → 98.4% |

The losses are below −10 dB, where the signature is buried in noise.

**Why overall accuracy barely moves:** most blocked windows are so weak that the model's next choice is also wrong. They now go to ALE (19), SSB (18), MIL-110 serial (17), CW beacon (15), RWM (13) and others, and only 6 more windows end up correct. The fix spreads low-SNR guesses out rather than making them right. Those windows are below −10 dB, where the model is 43–86% accurate anyway.

**One possible next step (not done):** report "unknown" instead of a second guess when the top label fails its check and confidence is low.

## 4. Pipeline

- `sigint/pipeline.py` now runs `signature.reweight` after the existing ACF check. The test harness turns it on with `SIGINT_SIGCHECK=1`.
- ID-only end-to-end run (100 windows):
  - No crashes, no decoders run, nothing decoded or stored.
  - Label accuracy was 84%, against 86% without the checks. That is a difference of 2 of 100 windows.
- `stress/run_all.py` now reports accuracy at SNR 0 dB and up (`acc_snr_ge_0`) in every classifier run.
