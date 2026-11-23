# Changelog

Version numbers: MINOR = signal batch (new classes and model), PATCH = fixes, tooling and
sigidwiki-monitor updates within a batch. Each entry links to its results document.
Format based on https://keepachangelog.com/en/1.1.0/ .

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
