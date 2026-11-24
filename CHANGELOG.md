# Changelog

Version numbers: MINOR = signal batch (new classes and model), PATCH = fixes, tooling and
sigidwiki-monitor updates within a batch. Each entry links to its results document.
Format based on https://keepachangelog.com/en/1.1.0/ .

## [0.12.1] - 2026-11-24
### Added
- CCIR selcall signature check (sigidwiki tone table, 70/100 ms tones) in sigint/signature.py:
  a selcall label needs CCIR tones in sequence, else "unknown". False selcall labels 73 -> 0,
  wrong mode labels 700 -> 627; 98.33% at SNR >= -10 dB, 99.07% at >= 0 dB.
  docs/batch14_results.md 4a.
- stress/tune_signature.py: SIGINT_TUNE_ONLY tunes chosen checks and keeps the others.

## [0.12.0] - 2026-11-24
### Added
- Batch 14, IC-7100 VHF/UHF (docs/batch14_results.md): APRS (Dire Wolf modulator), POCSAG
  (ITU-R M.584-2), NOAA/EAS SAME (47 CFR 11.31, minimodem), MDC-1200 and CCIR 5-tone selcall.
  71-class model data/resnet18_modes_b14_10.pt: 98.41% at SNR >= -10 dB, 99.11% at >= 0 dB
  with signature checks. ACARS and FLEX dropped (no physical-layer source found).
### Changed
- The 66-class model is replaced by the 71-class one; setup guide points to it.

## [0.11.2] - 2026-11-24
### Added
- docs/setup_ic7300.md: one-page guide to running the ID-only pipeline on your own computer
  with the IC-7300 (packages, rig menu settings, device name, run command, results, checks).

## [0.11.1] - 2026-11-24
### Changed
- A WWV, DTMF, HamDRM or STANAG 4539 label whose signature is absent is now reported as
  "unknown" instead of the model's next choice (user's choice). Wrong mode labels 807 -> 612 on
  the 100-window test; 98.10% at SNR >= -10 dB, 99.00% at >= 0 dB. docs/batch11_results.md 4a.
- stress/run_all.py counts "unknown" in the confusion matrix (n_unknown fields).

## [0.11.0] - 2026-11-24
### Added
- Batch 11 (docs/batch11_results.md): STANAG 4539, STANAG 4529, 3G ALE (STANAG 4538), Link-11
  SLEW and STANAG 4481 FSK, built from Shoc and sigidwiki parameters (sigint/synth_b11.py).
  66-class model data/resnet18_modes_b11_10.pt: 98.20% at SNR >= -10 dB, 99.04% at >= 0 dB.
  STANAG 4197, Link-11 CLEW and STANAG 4481 PSK are reported as existing classes
  (mil110_39tone, mil110_16tone, stanag4285).
- STANAG 4539 signature check (ACF 119.6 ms) in sigint/signature.py; a 3G ALE check is present
  but switched off.
### Changed
- stress/train.py: SIGINT_MMAP=1 keeps the training array on disk (66 classes no longer fit in RAM).
- The 61-class model is replaced by the 66-class one.

## [0.10.1] - 2026-11-24
### Fixed
- Weak signals of other modes labelled WWV, DTMF or HamDRM: `sigint/signature.py` keeps those
  labels only when the published signature is present (WWV 1 s tick, DTMF row+column tone pair,
  DRM OFDM symbol timing), otherwise takes the next class. False labels 207 -> 65 on the
  100-window test; accuracy 98.42% at SNR >= -10 dB, 98.89% at >= 0 dB. Thresholds tuned on
  training windows (`stress/tune_signature.py`). See `docs/signature_check_results.md`.
### Added
- `stress/run_all.py` reports accuracy at SNR >= 0 dB.

## [0.10.0] - 2026-11-23
### Added
- Batch 10: fldigi IFKP, PSK-R, multi-carrier PSK and OFDM (real fldigi takes, `stress/record_b10.sh`),
  codec2 DATAC data modes (codec2's own modulator, `tools/datac_tx.c`) and HamDRM (modes A/B,
  built from published DRM/HamDRM parameters) in `sigint/synth_b10.py`; checks in
  `stress/verify_b10.py`. 61 classes, `data/resnet18_modes_b10_10.pt` (replaces
  `resnet18_modes_b9_10.pt`). 98.4% at SNR >= -10 dB. See `docs/batch10_results.md`.
### Known issues
- HamDRM joins WWV and DTMF as catch-alls for weak signals; HamDRM mode E not built.

## [0.9.0] - 2026-11-23
### Added
- Batch 9: WWV/WWVH, RWM, ARQ-E, CIS-36-50/50-50 (one class), XPA, XPA2 and Mazielka (X06)
  (`sigint/synth_b9.py`, checks in `stress/verify_b9.py`); 55 classes,
  `data/resnet18_modes_b9_10.pt` (replaces `resnet18_modes_b8_10.pt`). 98.4% at SNR >= -10 dB.
  See `docs/batch9_results.md`.
### Removed
- Codan Selcall and XPB from the batch 9 plan: no usable spec found.
### Known issues
- WWV is 90% at SNR >= -10 dB; WWV and DTMF act as catch-alls for weak bursty signals.

## [0.8.0] - 2026-11-23
### Added
- Batch 8: FreeDV 1600, 700C and 700D/E (codec2's own modulator via `tools/freedv_tx_min.c`),
  Robust Packet Radio and DTMF (`sigint/synth_b8.py`, checks in `stress/verify_b8.py`);
  48 classes, `data/resnet18_modes_b8_10.pt` (replaces `resnet18_modes_b7_10.pt`).
  98.5% at SNR >= -10 dB. See `docs/batch8_results.md`.
- `docs/signal_sources.md` (signal sources beyond sigidwiki) and `docs/batch_plan.md`
  (batches 9-13).
### Known issues
- DTMF is called for 108 weak windows of other modes (catch-all); not fixed.

## [0.7.0] - 2026-11-22
### Added
- Batch 7: ICAO SELCAL, GMDSS DSC, CCIR 493-4 selcall, HFDL and MSK144 (`sigint/synth_b7.py`,
  checks in `stress/verify_b7.py`); 43 classes, `data/resnet18_modes_b7_10.pt` (replaces
  `resnet18_modes_b6_10.pt`). 98.6% at SNR >= -10 dB; new modes 98.5-100%.
  See `docs/batch7_results.md`.
## [0.6.1] - 2026-11-22
### Added
- `stress/sigidwiki_monitor.py`: monthly check of sigidwiki's `[[Category:Signal]]` pages
  (Semantic MediaWiki ask API) against `data/sigidwiki_snapshot.json`; writes
  `docs/sigidwiki_changes/YYYY-MM-DD.md` listing new/removed signals, changed listed parameters,
  and edited pages, flagging the ones this project models.
- `VERSION` and this changelog.

## [0.6.0] - 2026-11-22 (commit ce98ee6)
### Added
- Batch 6: 8PSK (real fldigi), FSQ, HF PACKET, SITOR-A, NDB; 38 classes,
  `data/resnet18_modes_b6_10.pt`. 98.4% at SNR >= -10 dB. See `docs/batch6_results.md`.
### Removed
- CHU from the plan: sigidwiki lists it as shut down on 2026-06-22.

## [0.5.1] - 2026-11-21
### Added
- 3-channel spectrogram input, more fldigi training audio, Olivia/Contestia and MFSK/THOR
  fldigi trial-decode checks (`sigint/oc_check.py`, `sigint/mt_check.py`; decoded text never
  stored). 98.7% at SNR >= -10 dB with both checks. See `docs/accuracy_push_results.md`.
### Fixed
- Faulty NAVTEX test recording replaced.

## [0.5.0] - 2026-11-20
### Added
- Batch 5: STANAG 4285, MIL-STD-188-110 serial/16-tone/39-tone, PACTOR I/II/III (33 classes).
  See `docs/batch5_results.md`.

## [0.4.0] - 2026-11-19
### Added
- Batch 4: SSTV, WEFAX, 2G ALE, CW beacon, SITOR-B/NAVTEX (26 classes). See `docs/batch4_results.md`.

## [0.3.0] - 2026-11-19
### Added
- Batch 3: Olivia, Contestia, MFSK, THOR, DominoEX, MT63, Hell, THROB from real fldigi
  transmissions (21 classes); RF band-plan tie-breaker. See `docs/batch3_results.md`.

## [0.2.0] - 2026-11-19
### Added
- Batch 2: FT4, JS8, WSPR, JT65, JT9, FST4, Q65 (13 classes). See `docs/batch2_results.md`.

## [0.1.0] - 2026-11-19
### Added
- ID-only pipeline (capture, 15 s slicer, ResNet-18, occupancy, SQLite, Ollama explainer) with
  FT8, CW, RTTY, PSK31, SSB and noise; IC-7300 receivable-signal list
  `docs/ic7300_sigidwiki_signals.md`.
