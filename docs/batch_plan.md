# Batch plan after batch 8

Written 2026-11-23 when the user asked to add the sources in `docs/signal_sources.md` to the
model. The order follows section 5 of that document. Same rules as every batch: ID-only (nothing
decoded or stored), 100 test windows per mode, and a reference for every spec.

| Batch | Modes | How the audio is made | Spec sources (from `signal_sources.md`) |
|---|---|---|---|
| 9 | WWV/WWVH, RWM, ARQ-E/E3, CIS-36-50 / CIS-50-50, Codan Selcall, XPA/XPA2/XPB, Mazielka (X06) | Built from published specs | [NIST WWV format](https://www.nist.gov/pml/div688/grp40/wwv_format); sigidwiki pages for each (listed in `docs/ic7300_sigidwiki_signals.md`); [Priyom](https://priyom.org/number-stations) |
| 9 (sub-labels) | RTTY shifts 45/170, 50/425, 50/450, 75/170, 100/450, 100/850 and FSK 50/850 | Existing RTTY generator, reported as sub-modes, not new classes | [Scholl 2025, Table III](https://arxiv.org/html/2504.05455v1) |
| 10 | HamDRM (digital SSTV), codec2 DATAC modes, fldigi IFKP, PSKR, multi-carrier PSK and OFDM | Real encoders: [QSSTV](https://github.com/ON4QZ/QSSTV), codec2 (already installed), fldigi | [Bundscherer 2025](https://arxiv.org/html/2501.07337v1), [Mercury](https://github.com/Rhizomatica/mercury) |
| 11 | STANAG 4539, 4529, 4197, 4481, 3G ALE, Link-11 CLEW/SLEW | Built from published parameters | [Shoc pages](https://cartoonman.github.io/Shoc/stanag4539.htm), Wavecom manuals |
| 12 | Real recordings for existing classes; Fraunhofer SSB samples into `ssb` | [kiwirecorder](https://github.com/jks-prv/kiwiclient) on public KiwiSDRs, labelled from [PSK Reporter](https://pskreporter.info/pskdev.html) / RBN spots (mode label only); [Fraunhofer FKIE SSB files](https://zenodo.org/records/7977073) (CC BY 4.0) | Section 3 of `signal_sources.md` |
| 13 | Clover, PACTOR IV, ROS, Codan 16-tone | Real recordings only (no open generator) | Needs batch 12's recording pipeline |

**On hold until the user confirms:**
- **ARDOP:** it carries Winlink traffic, which the user declined.
- **UDXF recordings:** UDXF requires written approval for any use ([udxf.nl/about](https://www.udxf.nl/about.html)).

**Open questions to check when each batch starts:**
- Batch 12 needs the cloud container to reach KiwiSDR receivers and pskreporter.info. Both may be blocked by the network policy, like sigidwiki was.
- Batch 13 depends on how many real recordings batch 12 can label.
