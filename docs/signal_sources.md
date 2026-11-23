# Signal sources beyond sigidwiki

Researched 2026-11-23 for the IC-7300 (HF, about 3 kHz SSB/data passband) ID-only classifier.
Already covered: the 43 classes of batch 7 (`results/classifier_b7_10_seed5.json`) plus batch 8
(FreeDV 1600/700C/700D-E, Robust Packet, DTMF). VARA and Winlink are left out because you
declined them. VHF/UHF-only items for the IC-7100 are in section 6.

Every claim links to the page it came from. "Not stated" means the page I read did not say.

## 1. Short answer

- **Most new modes are already on sigidwiki** but not yet built. Of the candidates below, ROS,
  Clover, CIS modes, Codan, Link-11, STANAG 4197/4481/4529/4539, 3G ALE, XPA, Mazielka, the
  Buzzer/Pip markers, WWV, RWM, ARQ-E, PACTOR IV, Japanese Slot Machine, Chinese 4+4 and DRM
  all appear in `docs/ic7300_sigidwiki_signals.md`. What the other sources add is **better
  specs, real recordings and working generators**, not many new names.
- **Biggest win for real-world accuracy: auto-labelled real recordings.** Record public KiwiSDRs
  with `kiwirecorder.py` and label each clip from PSK Reporter or the Reverse Beacon Network
  spots for that time and frequency (section 3).
- **Best mode checklist:** Scholl 2025 lists 160 HF classes that a real classifier was trained
  on (section 2.1). It is a ready to-do list, but its data is not public.
- **Open generators for modes not yet built:** QSSTV (HamDRM digital SSTV), codec2 data modes
  (DATAC*, as used by Mercury), ardopcf (ARDOP, but it is a Winlink transport, so it needs your
  OK), and the NIST spec for WWV/WWVH.

## 2. Catalogs and mode lists

### 2.1 Scholl 2025, "Large-Scale Classification of Shortwave Communication Signals"
- Source: https://arxiv.org/html/2504.05455v1 (Table III, "Table of supported modes").
- **What it adds:** 160 HF classes with a published real-world test (143 of 160 had real test
  recordings; about 90% top-1 at high SNR). Data is 4 kHz complex IQ, about 1 s per sample, so it
  matches our passband.
- **Access/licence:** no dataset or code link in the paper. The paper itself is CC BY-NC-ND 4.0.
  Author contact is Panoradio SDR (research@panoradio-sdr.de, as given in the paper).
- **Classes not in our 48 that fit the IC-7300:** 3G ALE, ALE-400, ALIS, ALIS-2, ARQ-E(E3),
  Chinese 4+4, Chinese MIL Datalink 30, CIS-11/12/20/36/45/60/93/112/128/8181/3000,
  CIS-36-50/50-50, CIS-75-250, CIS-200-500, CIS-MFSK-16/20/68 (XPA, XPA2, XPB), Clover II/2000/
  2500, Codan, Codan Chirp, Codan Selcall, DPRK FSK, D-Marker, T-Marker, FSK 50/850, HC-265,
  Iran Navy PSK modems, Israel Navy Hybrid Preamble, Japan 8/32-Channel, Japan Slot Machine,
  Link-11 CLEW and SLEW, Link-22, Mahovik, Mazielka, Nokia Adaptive MSG Terminal, OTH Radar,
  PACTOR 4, Pol Intel FSK/PSK types, PSK 10, PSK 220F, QPSK 31/63/125, RDFT, ROS-4/8/16,
  RWM time, Saab Grintek MHF-50, Siemens CHX-200, Sine, Skyfax, STANAG 4197, STANAG 4481 FSK,
  STANAG 4529, STANAG 4539, Thales Skyhopper, markers (The Air Horn, The Alarm, The Buzzer,
  The Goose, The Pip, The Squeaky Wheel), Vezha-S. (VARA HF is also in their list; skipped.)
- Useful also as a guide to **sub-mode splits** we lump together: separate RTTY shifts
  (45/170, 50/425, 50/450, 75/170, 100/450, 100/850), Olivia/Contestia sizes, DominoEX 4–22,
  THOR 8–22, MT63 500/1000/2000, SSTV Martin/Scottie/Robot.

### 2.2 RadioReference wiki HF mode pages
- Sources: https://wiki.radioreference.com/index.php/HF_Modes_List ,
  https://wiki.radioreference.com/index.php/HF_Modes_Currently_Active ,
  https://wiki.radioreference.com/index.php/HF_and_LF_Modes_used_by_MultiPSK
- **What it adds:** an "is this still on the air" filter. The Active page splits modes into
  active, sporadic and amateur. Active modes we lack: CLOVER-2000, 8-tone Clover, Codan
  9001/3021 16-tone, FSK100, AK10, Japanese Slot Machine, KEGURI, MIL-STD-188-203-1A (Link-11),
  RDFT, STANAG 4481, NATO-75, WinDRM. Sporadic: Australian Forces 50/600 Bd, Chinese 4+4,
  Japanese Mil 8-FSK, MIL-STD-188-110B/C, PACTOR IV, Saab Grintek MHF50, STANAG 4197/4538/4539,
  Thales HFXM, Skymaster.
- The MultiPSK page adds ARQ-E, ARQ-E3, ARQ-FAE/ALE400, Coquelet, DGPS (no longer active in the US).
- **Licence:** wiki text, no licence checked. Use it as a pointer only.
- Not read yet: the linked "Radars and Sounders", "CIS Modes" and "Voice Scrambling" pages.

### 2.3 Artemis (AresValley)
- Sources: https://raw.githubusercontent.com/AresValley/Artemis/b7753d18d33e8ac43425596445ca6e71f4e4cf41/README.md ,
  https://aresvalley.github.io/Artemis/database/db_signals
- **What it adds:** an offline database of "over 500 recognized signals", built with the
  sigidwiki admin's help, and each entry links to its sigidwiki page. It is mostly a mirror of
  sigidwiki, so little new for us.
- **Licence:** software GPL-3. The database licence is not stated. Audio samples are not stated.

### 2.4 Shoc mode pages (decoder-style spec sheets)
- Sources: https://cartoonman.github.io/Shoc/stanag4539.htm ,
  https://cartoonman.github.io/Shoc/ale3g.htm , and sibling pages such as
  https://cartoonman.github.io/Shoc/milstd188110b16tone.htm ,
  https://cartoonman.github.io/Shoc/stanag4415.htm
- **What it adds:** exact generator parameters. Example: STANAG 4539 = QPSK to 64QAM,
  2400 Bd, 3000 Hz, centre 1800 Hz, interleaver 0.12 s or 8.64 s. 3G ALE (STANAG 4538) =
  8-PSK, 2400 Bd, 3000 Hz, burst waveforms BW0/1/4/5.
- **Licence/origin:** not stated on the pages (decoder help files republished on GitHub Pages).
  Use for parameters only, do not copy text or images.

### 2.5 Commercial decoder mode lists (Wavecom, PROCITEC)
- Wavecom W61PC/W74PC manuals list HF modes with parameters, e.g.
  https://www.manualsdir.com/manuals/791818/wavecom-w74pc-v870.html?page=41 (HF-modes menu),
  Clover-2000 at https://www.manualsdir.com/manuals/791829/wavecom-w61pc-v750.html?page=139 ,
  CIS-50-50/Clover-2 at https://www.manualsdir.com/manuals/791818/wavecom-w74pc-v870.html?page=152
- PROCITEC decoder list: https://procitec.com/application/files/1517/0591/7104/24.1_PROCITEC_Decoderlist.pdf
- **What they add:** parameters for proprietary/military modes (Clover, CIS, Codan, Skymaster).
- **Licence:** copyrighted manuals, no samples. Parameters only. I have not read these PDFs in
  full; they are listed from search results.

### 2.6 Numbers stations (Priyom, numbers-stations.com)
- Sources: https://priyom.org/number-stations , https://www.numbers-stations.com/digital
- **What it adds:** live schedules, which let us record real transmissions at known times.
  Digital classes: F (FSK), P (PSK), XP (polytones), HM (hybrid). Active digital stations
  listed: F01, F03, P03, F06, F06a, XPA, XPA2, XPB, HM01; plus X06 Mazielka (Russian
  selcall, "MFSK-6").
- **Licence:** Priyom site text is CC BY-NC-SA 4.0. No recording licence stated.
- **ID-only note:** we would identify the mode only. These carry encrypted traffic; nothing is
  decoded or kept.

### 2.7 UDXF (Utility DXers Forum)
- Sources: https://udxf.nl/ , https://www.udxf.nl/about.html
- **What it adds:** utility logs (0–30 MHz) and recording collections UC 1–6 (time signals,
  utility, coastal/navigation, military, government, VOLMET/aero/NDB).
- **Licence:** non-commercial use free with UDXF credited; **logs need written approval for any
  use**. Ask before using recordings for training.

## 3. Real recordings and how to label them

### 3.1 KiwiSDR network + kiwirecorder (best route)
- Source: https://github.com/jks-prv/kiwiclient
- **What it adds:** scripted audio or IQ recording from public KiwiSDRs worldwide
  (`-m iq --kiwi-wav` writes WAV with GNSS timestamps; several Kiwis at once; scan with squelch).
  Real fading, QRM and receiver noise, which our synthetic data lacks.
- **Licence:** code licence not on the README page (check the repo's LICENSE file). Using a
  public receiver is subject to each owner's terms; keep use light.
- Recording from WebSDR/OpenWebRX by browser: https://www.ab9il.net/software-defined-radio/recording-sdr.html

### 3.2 Auto-labels from PSK Reporter and Reverse Beacon Network
- PSK Reporter query API: https://pskreporter.info/pskdev.html. Returns spots with sender,
  frequency (Hz), time and mode (ADIF names) for up to 24 h back; at most one query per 5 min.
- Reverse Beacon Network: telnet.reversebeacon.net port 7000 (CW, RTTY) and 7001 (FT8)
  (https://www.arrl.org/news/reverse-beacon-network-beta-testing-separate-spot-stream-for-ft8 ,
  https://www.kb6nu.com/rbn-spotting-ft8-signals/ ; 2018 pages, current ports not re-checked).
- **Idea:** record a KiwiSDR near a spotter, then label each window by the spot's mode and
  frequency. Only the mode label is used; no callsign or message is stored. Gives real CW,
  RTTY, PSK, FT8/FT4, JS8, WSPR, Olivia etc.
- Related open tool: CWSL_DIGI (GPL-3) decodes FT8/FT4/JT65/WSPR/FST4/FST4W/JS8 and spots
  to PSK Reporter/RBN: https://github.com/alexranaldi/CWSL_DIGI

### 3.3 Fraunhofer FKIE SSB example files
- Source: https://zenodo.org/records/7977073 (DOI 10.5281/zenodo.7977073)
- **What it adds:** 8 WAVs, two real HF SSB recordings and six voice clips with simulated HF
  channel effects. Small, but **CC BY 4.0**, so usable for the `ssb` class right away.

### 3.4 Research datasets (mostly not downloadable)
- Scholl 2019, 18 HF modes, synthetic with a Watterson/CCIR 520 channel, 2048-sample IQ at 6 kHz:
  https://arxiv.org/pdf/1906.04459 . Download and licence not stated. Useful as a recipe for
  our own channel model.
- Bundscherer et al. 2025, 17 modes / 98 sub-modes, fldigi-generated training plus real
  over-the-air test: https://arxiv.org/html/2501.07337v1 . Public release not stated. It names
  fldigi modes we do not have: **IFKP, PSKR, multi-carrier PSK and fldigi OFDM**, which our
  existing fldigi setup can make.
- latterworks/sigid on Hugging Face: a 314-row sigidwiki-like table with mostly empty audio
  fields: https://huggingface.co/datasets/latterworks/sigid/viewer/default/train?p=2 . Licence
  not seen. Adds nothing over sigidwiki.

### 3.5 RadioML and TorchSig (not a good fit)
- DeepSig RadioML 2016/2018: 11 to 24 generic modulations, CC BY-NC-SA 4.0:
  https://www.deepsig.io/datasets-old
- TorchSig: MIT licence, 60+ generic signal types, aimed at wideband detection:
  https://github.com/TorchDSP/torchsig
- **Why not:** these are generic modulations (BPSK, QAM, FM) at RF, not named HF protocols in a
  3 kHz audio channel. Only useful as extra impairment/augmentation code.

## 4. Open generators for modes not yet built

| Mode(s) | Generator | Licence | Notes |
|---|---|---|---|
| HamDRM / digital SSTV (EasyPal-compatible) | QSSTV, https://github.com/ON4QZ/QSSTV | GPL-3 | Transmits SSTV and HamDRM. Also more analog SSTV sub-modes. |
| codec2 data modes (DATAC1/3/4/13/14/15 etc.) | codec2 (already installed for batch 8); Mercury uses them: https://github.com/Rhizomatica/mercury | GPL-3 (Mercury) | Mercury lists DATAC15 about 200 Hz, DATAC17/QAM16C2 about 2100 Hz. These are the FreeDATA/Mercury HF data modes. Mercury itself is VARA-like but open; not Winlink. |
| ARDOP | ardopcf, https://github.com/pflarue/ardop | MIT | Development discontinued. **Winlink transport, so skip unless you say so.** |
| MIL-STD-188-110B serial / STANAG 4539 data phase | MATLAB example, https://it.mathworks.com/help/comm/ug/defense-communications-us-mil-std-188-110b-baseband-link-level.html | Needs MATLAB + Communications Toolbox | Only useful if you have MATLAB; Shoc parameters (2.4) let us spec-build instead. |
| WWV/WWVH time stations | Spec: https://www.nist.gov/pml/div688/grp40/wwv_format | US Gov | Ticks 5 ms at 1000/1200 Hz, 800 ms minute tone, 500/600 Hz tones, 100 Hz BCD. Easy to spec-build. |
| IFKP, PSKR, MC-PSK, OFDM | fldigi (already in use) | GPL | Named in Bundscherer 2025 (above). |
| Proprietary: Clover, PACTOR IV, Codan, ROS, CIS modes | None open found | n/a | Spec-build from Wavecom/Shoc parameters, or use real recordings. |

multimon-ng is decode-only (no generator): https://man.archlinux.org/man/multimon-ng.1.raw

## 5. Suggested next batches (my ranking)

1. **Easy spec builds, fill gaps on sigidwiki list:** WWV/WWVH + RWM, ARQ-E/E3, FSK 50/850 and
   other RTTY shifts as sub-labels, CIS-36-50/50-50, Codan Selcall, XPA/XPA2/XPB, Mazielka.
2. **Open generators:** HamDRM (QSSTV), codec2 DATAC modes, fldigi IFKP/PSKR/OFDM.
3. **Wide military PSK:** STANAG 4539, 4529, 4197, 4481, 3G ALE, Link-11 CLEW/SLEW (Shoc and
   Wavecom parameters).
4. **Real-data pipeline:** KiwiSDR + PSK Reporter/RBN auto-labels to retrain on real signals.
5. Proprietary (Clover, PACTOR IV, ROS, Codan 16-tone): only from real recordings.

## 6. VHF/UHF only (for the IC-7100 later)

- multimon-ng decoders show the common VHF/UHF formats: POCSAG 512/1200/2400, FLEX, EAS,
  AFSK1200 (APRS), FSK9600, ZVEI/EEA/EIA/CCIR selcall, X10:
  https://man.archlinux.org/man/multimon-ng.1.raw
- RadioML/TorchSig (section 3.5) fit wideband VHF/UHF work better than HF.
- sigidwiki's 30–800 MHz entries (DMR, pagers, CTCSS) are already listed in
  `docs/ic7300_sigidwiki_signals.md` as mostly VHF/UHF.
