# sigidwiki signals the IC-7300 can receive

Pulled 2026-11-19 from sigidwiki's own structured data (Semantic MediaWiki `ask` API,
`[[Category:Signal]]` with the Frequencies, Bandwidth, Modulation and Mode properties),
read through the browser because sigidwiki is blocked from the test container.

**Counts:** 599 signals on sigidwiki. 342 have a listed frequency inside the IC-7300's
receive range. Of those, **235 fit the SSB/data passband (Tier A)**, **51 need the AM or FM
filter (Tier B)**, **21 have no bandwidth listed (Tier U)** and **35 are wider than the
receiver can pass (excluded)**. 245 are entirely outside the range and 12 list no frequency.

## How "can hear" was decided

1. **Frequency:** at least part of the signal's listed range falls within **0.030–74.8 MHz**,
   the IC-7300 receive range (Icom product page and manual specifications:
   https://icomamerica.com/lineup/products/IC-7300/ ,
   https://www.manualslib.com/manual/1106166/Icom-Ic-7300.html?page=145 ).
2. **Bandwidth:** the narrowest listed bandwidth must fit an IC-7300 IF filter. The SSB/data
   filters go up to 3.6 kHz, AM up to about 10 kHz and FM up to 15 kHz (IC-7300 manual, IF
   filter section; same manual link). Tier A ≤ 3.6 kHz, Tier B 3.6–15 kHz, excluded > 15 kHz.
3. Each signal links to its sigidwiki page, which is the reference for its frequency,
   bandwidth and modulation.

## Caveats on the data

- sigidwiki's properties are user-entered. Some are rough or wrong. For example, Morse Code
  lists "0.003–250000 MHz", and many utility modes just say "3–30 MHz". The pages themselves
  are the reference. I have not corrected them.
- Entries listed as "30–800 MHz" (selcall formats, CTCSS, DMR, pagers) are mostly VHF/UHF
  signals. They count as in range only because low-band VHF (30–50 MHz) is inside 74.8 MHz.
  Expect them rarely on this rig.
- Below about 1.8 MHz (LF time signals, NDBs, DCF77, SAS) the IC-7300 receives, but Icom
  rates its sensitivity only above 1.8 MHz (same spec page), so reception there depends on
  antenna and noise.
- **Sample recordings:** sigidwiki's copyright page says the site does not own submitted
  content and grants no licence to reuse it
  (https://www.sigidwiki.com/wiki/Signal_Identification_Wiki:Copyrights). So **the test batches
  will use synthetic signals**, not sigidwiki recordings. Where a real encoder is installed
  here (WSJT-X: ft4sim/jt65sim/wsprsim/q65sim/fst4sim; fldigi's own transmitter for Olivia,
  MFSK, THOR, MT63 and others), it will generate the test audio.

## Proposed test batches (ID-only, 100 windows per signal)

| Batch | Signals | Generator |
|---|---|---|
| 2 | FT4, JS8, WSPR, JT65, JT9, FST4/FST4W, Q65 | WSJT-X simulators (real encoders); JS8 synthesized (8-GFSK like FT8) |
| 3 | Olivia, Contestia, MFSK, THOR, DominoEX, MT63, PSK63/125, Hellschreiber, THROB | fldigi's own transmitter into the virtual sound card |
| 4 | SSTV, WEFAX (HF fax), 2G ALE, CW beacons, NAVTEX/SITOR-B | Synthetic generators; fldigi WEFAX transmitter |
| 5 | STANAG 4285, MIL-STD-188-110 serial, PACTOR I, CLOVER, VARA-like OFDM | Synthetic PSK/OFDM generators from the published waveform specs |
| 6+ | Remaining Tier A, then Tier B (AM, NFM, jammers, time signals, radars) | Synthetic |

The classifier gets retrained as classes are added, because a 6-class model can't name
signals it has never seen.

---

## Tier A — fits the SSB/data passband (≤ 3.6 kHz)

| Signal (sigidwiki) | Frequencies, MHz | Bandwidth, kHz | Modulation | Rig mode |
|---|---|---|---|---|
| [29B6 'Kontayner' OTH Radar](https://www.sigidwiki.com/wiki/29B6_%27Kontayner%27_OTH_Radar) | 6.1–32 | 3.5, 7, 14, 28 | FMOP, Pulsed | USB |
| [8PSK](https://www.sigidwiki.com/wiki/8PSK) | 3, 30, 300, 3000 | 0.125, 0.25, 0.5, 1, 1.2 | 8PSK | USB,FM |
| [Accurate positioning by Low Frequencies (ALF)](https://www.sigidwiki.com/wiki/Accurate_positioning_by_Low_Frequencies_(ALF)) | 0.1237 | 2.1 | PSK | USB |
| [AKKORD-SS-PD](https://www.sigidwiki.com/wiki/AKKORD-SS-PD) | 7.051 | 1.2 | MSK | USB |
| [ALE-400](https://www.sigidwiki.com/wiki/ALE-400) | 1.806–144.1625 | 0.4 | MFSK | USB |
| [Amplitude Modulation Signalling System (AMSS)](https://www.sigidwiki.com/wiki/Amplitude_Modulation_Signalling_System_(AMSS)) | 0.1–30 | 0.2 | AM, PSK | SSB |
| [ARQ-E(E3)](https://www.sigidwiki.com/wiki/ARQ-E(E3)) | 3–30 | 0.085, 0.16, 0.17, 0.19, 0.34, … | FSK | USB |
| [ARQ-M2-242](https://www.sigidwiki.com/wiki/ARQ-M2-242) | 3–30 | 0.6 | FSK | USB |
| [ARQ-M2-342](https://www.sigidwiki.com/wiki/ARQ-M2-342) | 3–30 | 0.6 | FSK | USB |
| [ARQ-M4-242](https://www.sigidwiki.com/wiki/ARQ-M4-242) | 3–30 | 0.25 | FSK | USB |
| [ARQ-M4-342](https://www.sigidwiki.com/wiki/ARQ-M4-342) | 3–30 | 0.6 | FSK | USB |
| [ARQ-N](https://www.sigidwiki.com/wiki/ARQ-N) | 3–30 | 0.085, 0.16, 0.17, 0.19, 0.34, … | FSK | USB |
| [ARQ6-90](https://www.sigidwiki.com/wiki/ARQ6-90) | 10–23 | 0.7 | FSK | USB |
| [ARQ6-98](https://www.sigidwiki.com/wiki/ARQ6-98) | 10–23 | 0.4 | FSK | USB |
| [ASCII](https://www.sigidwiki.com/wiki/ASCII) | 3–450 | 0.3 | FSK | NFM, USB |
| [Automatic Link Establishment (2G ALE)](https://www.sigidwiki.com/wiki/Automatic_Link_Establishment_(2G_ALE)) | 3.068–28.3125 | 2 | MFSK | USB |
| [Automatic Link Establishment (3G ALE ARCS)](https://www.sigidwiki.com/wiki/Automatic_Link_Establishment_(3G_ALE_ARCS)) | 3–30 | 3 | PSK | USB |
| [Automatic Link Establishment (4G ALE WALE)](https://www.sigidwiki.com/wiki/Automatic_Link_Establishment_(4G_ALE_WALE)) | 3–30 | 3 | PSK | USB |
| [Automatic Link Set-up (ALIS)](https://www.sigidwiki.com/wiki/Automatic_Link_Set-up_(ALIS)) | 3–30 | 0.27 | FSK | USB |
| [AUTOSPEC](https://www.sigidwiki.com/wiki/AUTOSPEC) | 3–30 | 0.35 | FSK | USB |
| [BPC](https://www.sigidwiki.com/wiki/BPC) | 0.0685 | 0.001 | AM | USB |
| [BPM](https://www.sigidwiki.com/wiki/BPM) | 2.5, 5, 10, 15 | 3.5 | AM | AM |
| [BR-6028](https://www.sigidwiki.com/wiki/BR-6028) | 5.75, 8.045, 11.01, 13.4582, … | 3.1 | FSK | USB |
| [CBET](https://www.sigidwiki.com/wiki/CBET) | 0.0005, 1.7, 88, 108 | 2 | FM, AM | — |
| [CCIR 493-4 Selcall](https://www.sigidwiki.com/wiki/CCIR_493-4_Selcall) | 3–30 | 0.3 | FSK | USB |
| [Chinese 30-tone OFDM modem](https://www.sigidwiki.com/wiki/Chinese_30-tone_OFDM_modem) | 3–20 | 3 | QPSK, BPSK, OFDM | LSB, USB (rare) |
| [Chinese 4+4](https://www.sigidwiki.com/wiki/Chinese_4%2B4) | 3–30 | 2.5 | PSK | USB |
| [Chinese-64 MFSK](https://www.sigidwiki.com/wiki/Chinese-64_MFSK) | 3.673, 12.916, 16.989 | 2.5 | MFSK | USB,LSB (rare) |
| [CHIP](https://www.sigidwiki.com/wiki/CHIP) | 7.09, 14.077, 14.11 | 0.58 | PSK | USB |
| [CHU](https://www.sigidwiki.com/wiki/CHU) | 3.33, 7.85, 14.67 | 2.25 | FSK, OOK | USB |
| [CIS 3x100 VFT](https://www.sigidwiki.com/wiki/CIS_3x100_VFT) | 3–30 | 3.1 | FSK | USB |
| [CIS 3x144 VFT](https://www.sigidwiki.com/wiki/CIS_3x144_VFT) | 3–30 | 3.1 | FSK | USB |
| [CIS 3xBaudot-50 VFT](https://www.sigidwiki.com/wiki/CIS_3xBaudot-50_VFT) | 3–30 | 3.1 | FSK | USB |
| [CIS MFSK-11](https://www.sigidwiki.com/wiki/CIS_MFSK-11) | 7.8–23.8 | 3.3 | MFSK | USB |
| [CIS MFSK-16 XPA2](https://www.sigidwiki.com/wiki/CIS_MFSK-16_XPA2) | 3–30 | 0.25 | MFSK | USB |
| [CIS MFSK-16 XPB](https://www.sigidwiki.com/wiki/CIS_MFSK-16_XPB) | 4.4, 10, 20 | 2.8 | MFSK | USB |
| [CIS MFSK-20 XPA](https://www.sigidwiki.com/wiki/CIS_MFSK-20_XPA) | 3–30 | 0.8 | MFSK | USB |
| [CIS MFSK-21-13](https://www.sigidwiki.com/wiki/CIS_MFSK-21-13) | 4.834–16.292 | 3.3 | MFSK | USB |
| [CIS OFDM HDR Modem](https://www.sigidwiki.com/wiki/CIS_OFDM_HDR_Modem) | 3–30 | 2.8, 2.95, 3 | PSK, OFDM | USB |
| [CIS OFDM-121](https://www.sigidwiki.com/wiki/CIS_OFDM-121) | 4.454–20.866 | 2.7, 3.1 | OFDM, QPSK | USB |
| [CIS-11](https://www.sigidwiki.com/wiki/CIS-11) | 3–30 | 0.65 | FSK | USB |
| [CIS-112](https://www.sigidwiki.com/wiki/CIS-112) | 3–30 | 3 | PSK, OFDM | USB |
| [CIS-12](https://www.sigidwiki.com/wiki/CIS-12) | 0.3–30 | 3.1 | PSK | USB |
| [CIS-1200 (T-230-1A 'Mahovik')](https://www.sigidwiki.com/wiki/CIS-1200_(T-230-1A_%27Mahovik%27)) | 3–30 | 2.5 | SDPSK, BPSK | USB |
| [CIS-128](https://www.sigidwiki.com/wiki/CIS-128) | 3–30 | 3.1, 6.1 | PSK, OFDM, QAM | USB |
| [CIS-1280](https://www.sigidwiki.com/wiki/CIS-1280) | 3, 5.752, 7.663, 9.058, … | 1.28 | PSK | USB |
| [CIS-14](https://www.sigidwiki.com/wiki/CIS-14) | 3–30 | 0.65 | FSK | USB |
| [CIS-16](https://www.sigidwiki.com/wiki/CIS-16) | 3–30 | 2.7 | PSK | USB |
| [CIS-20](https://www.sigidwiki.com/wiki/CIS-20) | 3–30 | 2.75 | PSK, OFDM | USB |
| [CIS-300](https://www.sigidwiki.com/wiki/CIS-300) | 3–30 | 0.37 | FSK | USB |
| [CIS-3000](https://www.sigidwiki.com/wiki/CIS-3000) | 3–30 | 3.4 | PSK | USB |
| [CIS-36-50](https://www.sigidwiki.com/wiki/CIS-36-50) | 3–30 | 0.3, 0.55 | FSK | USB |
| [CIS-40.5](https://www.sigidwiki.com/wiki/CIS-40.5) | 3–30 | 0.6 | FSK | USB |
| [CIS-50-50](https://www.sigidwiki.com/wiki/CIS-50-50) | 3–30 | 0.15, 0.63 | FSK | USB |
| [CIS-8181](https://www.sigidwiki.com/wiki/CIS-8181) | 3–30 | 0.6 | FSK | USB |
| [CLOVER 2000](https://www.sigidwiki.com/wiki/CLOVER_2000) | 3–30 | 2 | PSK, QAM | USB |
| [CLOVER 2500](https://www.sigidwiki.com/wiki/CLOVER_2500) | 3–30 | 2.5 | PSK, QAM | USB |
| [CLOVER-I](https://www.sigidwiki.com/wiki/CLOVER-I) | 3–30 | 0.1 | PSK, QAM | USB |
| [CLOVER-II](https://www.sigidwiki.com/wiki/CLOVER-II) | 3–30 | 0.5 | PSK, QAM | USB |
| [Codan Data Modem](https://www.sigidwiki.com/wiki/Codan_Data_Modem) | 3–30 | 0.4, 1.8, 2.56 | PSK, FSK | USB |
| [Coherent BPSK](https://www.sigidwiki.com/wiki/Coherent_BPSK) | 0.138, 1.881, 14.081, 18.081 | 0.2 | PSK | USB |
| [Coherent CW](https://www.sigidwiki.com/wiki/Coherent_CW) | 3–30 | 0.001 | OOK | USB |
| [Contestia](https://www.sigidwiki.com/wiki/Contestia) | 3–30 | 0.15, 0.25, 0.5, 1, 2 | MFSK | USB |
| [Coquelet](https://www.sigidwiki.com/wiki/Coquelet) | 3–30 | 0.3, 0.5 | MFSK | USB |
| [CRY2001 Voice Scrambler](https://www.sigidwiki.com/wiki/CRY2001_Voice_Scrambler) | 3–300 | 3 | FSK | USB |
| [CV-786](https://www.sigidwiki.com/wiki/CV-786) | 3–30 | 0.9 | FSK | USB |
| [Datawell Buoy HF Link](https://www.sigidwiki.com/wiki/Datawell_Buoy_HF_Link) | 25.5, 35.5, 45 | 0.2, 0.4 | FSK, MFSK | USB |
| [DB0UPB research beacon](https://www.sigidwiki.com/wiki/DB0UPB_research_beacon) | 3.6, 7.05, 14.101 | 2.7 | MFSK, LSB, USB | LSB, USB |
| [DCF77](https://www.sigidwiki.com/wiki/DCF77) | 0.0775 | 1.3 | AM, PSK | USB |
| [DeltaFix](https://www.sigidwiki.com/wiki/DeltaFix) | 1.7–3.4 | 0.25 | FSK | USB |
| [Differential Global Positioning System (DGPS)](https://www.sigidwiki.com/wiki/Differential_Global_Positioning_System_(DGPS)) | 0.2835–2.95 | 0.15, 0.25 | MSK | USB |
| [Digital NBTV](https://www.sigidwiki.com/wiki/Digital_NBTV) | 3–470 | 2.5 | BPSK | SSB, FM |
| [DominoEX](https://www.sigidwiki.com/wiki/DominoEX) | 5.332, 10.142, 28.117 | 0.173, 0.244, 0.262, 0.346, 0.355, … | IFK | USB |
| [DominoF](https://www.sigidwiki.com/wiki/DominoF) | 1.838–28.08 | 0.22 | IFK | USB |
| [Driftnet Buoy Radio Beacon](https://www.sigidwiki.com/wiki/Driftnet_Buoy_Radio_Beacon) | 1.6, 2.85, 4, 28 | 0.001 | OOK | USB |
| [Dual Tone Multi Frequency (DTMF)](https://www.sigidwiki.com/wiki/Dual_Tone_Multi_Frequency_(DTMF)) | 30–800 | 3.3 | MFSK | NFM |
| [DUP-ARQ](https://www.sigidwiki.com/wiki/DUP-ARQ) | 3–30 | 0.325 | FSK | USB |
| [DUP-ARQ-2](https://www.sigidwiki.com/wiki/DUP-ARQ-2) | 3–30 | 1.3 | FSK | USB |
| [DUP-FEC-2](https://www.sigidwiki.com/wiki/DUP-FEC-2) | 3–30 | 1.1 | FSK | USB |
| [EFR Teleswitch](https://www.sigidwiki.com/wiki/EFR_Teleswitch) | 0.1291, 0.1356, 0.1399 | 1 | FSK | USB |
| [F03 numbers station](https://www.sigidwiki.com/wiki/F03_numbers_station) | 4–21 | 0.2, 0.4, 0.8 | FSK, MFSK | USB |
| [FEC-A](https://www.sigidwiki.com/wiki/FEC-A) | 3–30 | 0.1, 1.2 | FSK | USB |
| [FM NBTV](https://www.sigidwiki.com/wiki/FM_NBTV) | 3–470 | 2.3 | FM, BPSK | SSB, FM |
| [FreeDV COHPSK](https://www.sigidwiki.com/wiki/FreeDV_COHPSK) | 3–30 | 1.5 | PSK, QPSK, DQPSK, OFDM | USB |
| [FreeDV plus Video](https://www.sigidwiki.com/wiki/FreeDV_plus_Video) | 3, 14.236, 30 | 3.5 | OFDM, FM | USB |
| [Frequency Division Multiplex Digital Voice (FDMDV)](https://www.sigidwiki.com/wiki/Frequency_Division_Multiplex_Digital_Voice_(FDMDV)) | 3–30 | 1.125, 1.3 | PSK | USB |
| [FSQ](https://www.sigidwiki.com/wiki/FSQ) | 3.58, 7.104, 10.149 | 0.3 | IFK+ | USB |
| [FST4](https://www.sigidwiki.com/wiki/FST4) | 0.137–0.474 | 0, 0.001, 0.002, 0.006, 0.012, … | GFSK | USB |
| [FST4W](https://www.sigidwiki.com/wiki/FST4W) | 0.136, 0.4742, 1.839 | 0, 0.001, 0.002, 0.006 | GFSK | USB |
| [FT4](https://www.sigidwiki.com/wiki/FT4) | 0.0101, 3.575, 7.0475, 14.08, … | 0.083 | 4FSK | USB |
| [FT8](https://www.sigidwiki.com/wiki/FT8) | 1.84, 3.573, 7.074, 10.136, … | 0.05 | 8-FSK | USB |
| [G-TOR](https://www.sigidwiki.com/wiki/G-TOR) | 3–30 | 0.35 | FSK | USB |
| [Globe Wireless HF Network](https://www.sigidwiki.com/wiki/Globe_Wireless_HF_Network) | 3–30 | 0.4, 0.75, 2 | PSK, FSK, OFDM | USB |
| [GM2100 (R&S)](https://www.sigidwiki.com/wiki/GM2100_(R%26S)) | 3–30 | 3 | PSK | USB |
| [GMDSS Digital Selective Calling](https://www.sigidwiki.com/wiki/GMDSS_Digital_Selective_Calling) | 2.177, 2.1875, 4.2075, 6.312, … | 0.35 | FSK | USB |
| [Golay Paging (GSC)](https://www.sigidwiki.com/wiki/Golay_Paging_(GSC)) | 33–932 | 2.6 | FSK | NFM |
| [HC-265 Voice Scrambler](https://www.sigidwiki.com/wiki/HC-265_Voice_Scrambler) | 3–30 | 2.25, 3 | FSK | USB |
| [HC-ARQ](https://www.sigidwiki.com/wiki/HC-ARQ) | 3–30 | 0.3 | FSK | USB |
| [Hellschreiber](https://www.sigidwiki.com/wiki/Hellschreiber) | 3–30 | 0.35, 0.8 | OOK, FSK, MSK | USB |
| [HFGCS (High Frequency Global Communications System)](https://www.sigidwiki.com/wiki/HFGCS_(High_Frequency_Global_Communications_System)) | 4.724, 6.712, 6.739, 8.992, … | 2.95 | USB | USB |
| [High Frequency Data and Voice Link (HFDVL)](https://www.sigidwiki.com/wiki/High_Frequency_Data_and_Voice_Link_(HFDVL)) | 14.35–14.8285 | 3 | PSK, OFDM, QAM | USB |
| [High Frequency Data Link (HFDL)](https://www.sigidwiki.com/wiki/High_Frequency_Data_Link_(HFDL)) | 2.9–22 | 2.4 | PSK | USB |
| [HNG-FEC](https://www.sigidwiki.com/wiki/HNG-FEC) | 2.4–24 | 0.6 | FSK | USB |
| [HP Laptop](https://www.sigidwiki.com/wiki/HP_Laptop) | 0.0509 | 1.5 | USB, LSB | CW |
| [HyperFix](https://www.sigidwiki.com/wiki/HyperFix) | 1.6–3.4 | 0.25 | — | USB |
| [ICAO Selcal](https://www.sigidwiki.com/wiki/ICAO_Selcal) | 3–300 | 1.5 | MFSK | USB |
| [Improved Automatic Link Set-up (ALIS-2)](https://www.sigidwiki.com/wiki/Improved_Automatic_Link_Set-up_(ALIS-2)) | 3–30 | 2 | FSK | USB |
| [Ionosonde](https://www.sigidwiki.com/wiki/Ionosonde) | 1–40 | 0.001 | FMCW | USB |
| [IRA-ARQ](https://www.sigidwiki.com/wiki/IRA-ARQ) | 3–30 | 0.65, 1.35 | FSK | USB |
| [Iranian Navy QPSK Modem](https://www.sigidwiki.com/wiki/Iranian_Navy_QPSK_Modem) | 8.046, 8.475, 10.724, 17.3822 | 0.3, 0.62, 0.7, 1.25, 1.42, … | PSK | USB |
| [ISCAT](https://www.sigidwiki.com/wiki/ISCAT) | 50, 54, 144, 148 | 0.904, 1.809 | MFSK | USB |
| [Israeli Intelligence VFT](https://www.sigidwiki.com/wiki/Israeli_Intelligence_VFT) | 3–30 | 3.1 | FSK | USB |
| [Israeli Navy Hybrid Modem (188-110 MOD)](https://www.sigidwiki.com/wiki/Israeli_Navy_Hybrid_Modem_(188-110_MOD)) | 3–30 | 2.75 | PSK | USB |
| [Israeli VFT](https://www.sigidwiki.com/wiki/Israeli_VFT) | 3–30 | 3.1 | FSK, PSK | USB |
| [Japan Military 8-Channel FSK](https://www.sigidwiki.com/wiki/Japan_Military_8-Channel_FSK) | 4.295–16.5535 | 2.4 | FSK | USB |
| [Japanese Slot Machine (XSL)](https://www.sigidwiki.com/wiki/Japanese_Slot_Machine_(XSL)) | 4.1525, 4.231, 4.2905, 6.2495, … | 2 | PSK | USB |
| [Jindalee Operational Radar Network (JORN)](https://www.sigidwiki.com/wiki/Jindalee_Operational_Radar_Network_(JORN)) | 5.7, 8.992, 10.153, 22.95, … | 3, 10, 12, 15, 30, … | FMCW | USB |
| [JJY](https://www.sigidwiki.com/wiki/JJY) | 0.04–0.06 | 0.001 | AM | USB |
| [JS8](https://www.sigidwiki.com/wiki/JS8) | 1.842, 3.578, 7.078, 10.13, … | 0.05 | GFSK | USB |
| [JT65](https://www.sigidwiki.com/wiki/JT65) | 1.838, 3.576, 7.039, 7.076, … | 0.18, 0.36, 0.71 | MFSK | USB |
| [JT6M](https://www.sigidwiki.com/wiki/JT6M) | 50.215–50.25 | 1 | MFSK | USB |
| [JT9](https://www.sigidwiki.com/wiki/JT9) | 3.578–28.079 | 0.016, 0.03, 0.057, 0.113, 0.224, … | MFSK | USB |
| [JTMS](https://www.sigidwiki.com/wiki/JTMS) | 3–30 | 1.7 | MSK | USB |
| [KG-STV](https://www.sigidwiki.com/wiki/KG-STV) | 3.733, 7.173, 14.233, 10489.625 | 0.5, 2.5 | 4FSK, MSK | USB |
| [Lentus](https://www.sigidwiki.com/wiki/Lentus) | 0.1363, 1.837, 3.589, 7.0375, … | 0.025 | MFSK | USB |
| [Link-11](https://www.sigidwiki.com/wiki/Link-11) | 2–29.9999 | 2.5, 3, 5, 6 | PSK | USB |
| [Long Dashes](https://www.sigidwiki.com/wiki/Long_Dashes) | 6.496, 8.999, 11.999, 12.494, … | 1 | OOK | USB |
| [Low Frequency Bicycle Computer Sensor](https://www.sigidwiki.com/wiki/Low_Frequency_Bicycle_Computer_Sensor) | 0.11–0.115 | 2 | Pulse | USB |
| [Marconi Selenia 25-Tone Modem](https://www.sigidwiki.com/wiki/Marconi_Selenia_25-Tone_Modem) | 3–30 | 1.6 | PSK, OFDM | USB |
| [Mazielka (X06)](https://www.sigidwiki.com/wiki/Mazielka_(X06)) | 4.963–23.458 | 0.2 | MFSK | USB |
| [MD-522](https://www.sigidwiki.com/wiki/MD-522) | 3–30 | 0.2, 0.25, 0.3 | FSK | USB |
| [MD-674](https://www.sigidwiki.com/wiki/MD-674) | 3–30 | 0.2, 0.25, 0.3 | FSK | USB |
| [MFJ-269C Antenna SWR Analyzer](https://www.sigidwiki.com/wiki/MFJ-269C_Antenna_SWR_Analyzer) | 0.5–500 | 1 | — | AM, NFM |
| [MIL-STD-110-342](https://www.sigidwiki.com/wiki/MIL-STD-110-342) | 3–30 | 3.1 | FSK | USB |
| [MIL-STD-188-110 Appendix A 16-Tone](https://www.sigidwiki.com/wiki/MIL-STD-188-110_Appendix_A_16-Tone) | 3–30 | 2.1 | PSK, OFDM | USB |
| [MIL-STD-188-110 Appendix B 39-Tone](https://www.sigidwiki.com/wiki/MIL-STD-188-110_Appendix_B_39-Tone) | 3–30 | 2.4 | PSK, OFDM | USB |
| [MIL-STD-188-110 Serial](https://www.sigidwiki.com/wiki/MIL-STD-188-110_Serial) | 3–30 | 2.75 | PSK | USB |
| [Modernised High Frequency Communications System (MHFCS)](https://www.sigidwiki.com/wiki/Modernised_High_Frequency_Communications_System_(MHFCS)) | 2.01–27.4775 | 0.4, 0.75 | FSK | USB |
| [MPDA](https://www.sigidwiki.com/wiki/MPDA) | 1.8–53 | 0.5, 1, 1.5, 2 | MP‑DASK | USB |
| [MSF](https://www.sigidwiki.com/wiki/MSF) | 0.06 | 0.005 | OOK | USB |
| [MSK144](https://www.sigidwiki.com/wiki/MSK144) | 30, 50, 70, 144, … | 2.5 | MSK | FM |
| [MSM-1250 Modem](https://www.sigidwiki.com/wiki/MSM-1250_Modem) | 3–30 | 2.4, 2.5 | FSK | USB |
| [MT63](https://www.sigidwiki.com/wiki/MT63) | 3–30 | 0.5, 1, 2 | OFDM, PSK | USB |
| [Multi Frequency Shift Keying (MFSK)](https://www.sigidwiki.com/wiki/Multi_Frequency_Shift_Keying_(MFSK)) | 3–30 | 0.154, 0.218, 0.316, 0.33, 0.435, … | MFSK | USB |
| [Nokia Adaptive Message Terminal](https://www.sigidwiki.com/wiki/Nokia_Adaptive_Message_Terminal) | 3–30 | 1, 1.6 | FSK | USB |
| [Non-Directional Beacon (NDB)](https://www.sigidwiki.com/wiki/Non-Directional_Beacon_(NDB)) | 0.19, 0.535, 1.75 | 2 | AM | CW |
| [North Korean Diplo FSK](https://www.sigidwiki.com/wiki/North_Korean_Diplo_FSK) | 9–29 | 1.2, 1.4 | FSK | USB |
| [North Korean Diplo PSK](https://www.sigidwiki.com/wiki/North_Korean_Diplo_PSK) | 9–29 | 0.3, 0.6, 1.2, 2.4 | PSK | USB |
| [OFDM NBTV](https://www.sigidwiki.com/wiki/OFDM_NBTV) | 0–30 | 2 | Analog OFDM | SSB |
| [Olivia](https://www.sigidwiki.com/wiki/Olivia) | 3–30 | 0.125, 0.25, 0.5, 1, 2 | MFSK | USB |
| [OOK RC Car Remote Control](https://www.sigidwiki.com/wiki/OOK_RC_Car_Remote_Control) | 27–49 | 1.6 | OOK | AM |
| [OPERA Beacon and Data](https://www.sigidwiki.com/wiki/OPERA_Beacon_and_Data) | 0.136–10000 | 0.002 | ASK | USB |
| [P03 numbers station](https://www.sigidwiki.com/wiki/P03_numbers_station) | 4–21 | 0.2 | BPSK, QPSK | USB |
| [P07 numbers station](https://www.sigidwiki.com/wiki/P07_numbers_station) | 4.6–10.45 | 3.5 | FSK, BPSK, QPSK, OFDM | USB |
| [PACKET](https://www.sigidwiki.com/wiki/PACKET) | 3–800 | 0.73 | FSK | USB |
| [PACTOR I](https://www.sigidwiki.com/wiki/PACTOR_I) | 3–30 | 0.3 | FSK | USB |
| [PACTOR II](https://www.sigidwiki.com/wiki/PACTOR_II) | 3–30 | 0.45 | PSK | USB |
| [PACTOR III](https://www.sigidwiki.com/wiki/PACTOR_III) | 3–30 | 0.4, 2.4 | PSK | USB |
| [PACTOR IV](https://www.sigidwiki.com/wiki/PACTOR_IV) | 3–30 | 0.3, 2.4 | PSK, QAM | USB |
| [Panther-H Modem](https://www.sigidwiki.com/wiki/Panther-H_Modem) | 1.5–30 | 3 | PSK | USB |
| [PAX](https://www.sigidwiki.com/wiki/PAX) | 3.59, 7.042, 10.148, 14.075, … | 0.5 | MFSK | USB |
| [Phase Shift Keying (PSK)](https://www.sigidwiki.com/wiki/Phase_Shift_Keying_(PSK)) | 1.838, 3.58, 7.035, 7.04, … | 0.01, 0.031, 0.063, 0.125, 0.25, … | PSK | USB |
| [PI4](https://www.sigidwiki.com/wiki/PI4) | 28, 40, 50, 70, … | 0.709 | MFSK | USB |
| [Piccolo](https://www.sigidwiki.com/wiki/Piccolo) | 3–30 | 0.18, 0.3 | MFSK | USB |
| [POL-ARQ](https://www.sigidwiki.com/wiki/POL-ARQ) | 3–30 | 0.35 | FSK | USB |
| [Polish Intelligence 100bd 625Hz FSK](https://www.sigidwiki.com/wiki/Polish_Intelligence_100bd_625Hz_FSK) | 4–20 | 3.5 | FSK | USB |
| [PRC-16](https://www.sigidwiki.com/wiki/PRC-16) | 14.3 | 2.2 | PSK, OFDM | USB |
| [PSK-AM](https://www.sigidwiki.com/wiki/PSK-AM) | 10.148, 14.075, 144.62 | 0.04, 0.11, 0.18 | PSK | USB |
| [PSK2K](https://www.sigidwiki.com/wiki/PSK2K) | 50.36–144.36 | 2 | PSK | USB |
| [Q-MAC HF Modem](https://www.sigidwiki.com/wiki/Q-MAC_HF_Modem) | 3–30 | 2 | PSK, OFDM, PSK8 | USB |
| [Q15X25](https://www.sigidwiki.com/wiki/Q15X25) | 3.585, 7.035, 14.109 | 1.95, 2.35 | PSK, OFDM | USB |
| [Q65](https://www.sigidwiki.com/wiki/Q65) | 50.275, 50.305, 144.17 | 0.019, 0.038, 0.049, 0.075, 0.098, … | MFSK | USB |
| [RAC-ARQ](https://www.sigidwiki.com/wiki/RAC-ARQ) | 3–30 | 1, 1.3 | FSK | USB |
| [Radio Teletype (RTTY)](https://www.sigidwiki.com/wiki/Radio_Teletype_(RTTY)) | 0.1473, 3.57, 4.583, 5.3305, … | 0.085, 0.17, 0.45, 0.85 | FSK | USB |
| [RBU](https://www.sigidwiki.com/wiki/RBU) | 0.0667 | 0.65 | FSK | USB |
| [Redundant Digital File Transfer (RDFT)](https://www.sigidwiki.com/wiki/Redundant_Digital_File_Transfer_(RDFT)) | 9.065–9.24 | 1.8 | PSK | USB |
| [RFID](https://www.sigidwiki.com/wiki/RFID) | 0.125–13.56 | 3.3 | ASK, FSK, OOK | RAW |
| [Robust PACKET](https://www.sigidwiki.com/wiki/Robust_PACKET) | 3.61, 7.0473, 10.1473, 14.1033 | 0.5 | PSK, OFDM | USB |
| [ROS](https://www.sigidwiki.com/wiki/ROS) | 1.8–30 | 2 | DSSS | USB |
| [RTTYM](https://www.sigidwiki.com/wiki/RTTYM) | 3–30 | 0.15, 0.25, 0.5, 1, 2 | MFSK | USB |
| [RUM-FEC](https://www.sigidwiki.com/wiki/RUM-FEC) | 3–30 | 0.75 | FSK | USB |
| [RUM-MOI FEC](https://www.sigidwiki.com/wiki/RUM-MOI_FEC) | 3–30 | 0.6 | FSK | USB |
| [Russian Diplo VFT PSK 64Bd](https://www.sigidwiki.com/wiki/Russian_Diplo_VFT_PSK_64Bd) | 4.022–23.131 | 2.5 | PSK | USB |
| [Russian Intelligence 200bd 1000Hz FSK (F06)](https://www.sigidwiki.com/wiki/Russian_Intelligence_200bd_1000Hz_FSK_(F06)) | 4–23 | 1 | FSK | USB |
| [Russian Intelligence 200bd 500Hz FSK (F01)](https://www.sigidwiki.com/wiki/Russian_Intelligence_200bd_500Hz_FSK_(F01)) | 4–23 | 0.5 | FSK | USB |
| [Russian MFSK-OFDM-chirp hybrid modem](https://www.sigidwiki.com/wiki/Russian_MFSK-OFDM-chirp_hybrid_modem) | 12.176, 16.257, 16.259 | 3, 12, 24, 48, 96 | MFSK, OFDM, FM, FMCW | USB |
| [Russian overhead power line telemetry system](https://www.sigidwiki.com/wiki/Russian_overhead_power_line_telemetry_system) | 0.05–1 | 0.4 | FSK | USB |
| [RWM](https://www.sigidwiki.com/wiki/RWM) | 4.996, 9.996, 14.996 | 0.005 | OOK | USB |
| [Saab Grintek MHF-50 MFSK Modem](https://www.sigidwiki.com/wiki/Saab_Grintek_MHF-50_MFSK_Modem) | 4.245, 4.346, 6.407, 6.493, … | 2.2 | MFSK, FSK | USB |
| [Serdolik](https://www.sigidwiki.com/wiki/Serdolik) | 3–30 | 1.4 | MFSK | USB |
| [SI-ARQ](https://www.sigidwiki.com/wiki/SI-ARQ) | 3–30 | 0.35 | FSK | USB |
| [SI-FEC](https://www.sigidwiki.com/wiki/SI-FEC) | 3–30 | 0.28 | FSK | USB |
| [Siemens CHX-200 FSK Modem](https://www.sigidwiki.com/wiki/Siemens_CHX-200_FSK_Modem) | 1.5–30 | 0.3 | FSK | USB |
| [Single frequency russian overhead power line telemetry system](https://www.sigidwiki.com/wiki/Single_frequency_russian_overhead_power_line_telemetry_system) | 0.05–1 | 0.3 | AM | SSB |
| [Single Sideband Voice](https://www.sigidwiki.com/wiki/Single_Sideband_Voice) | 3–30 | 1.9 | AM | SSB |
| [SITOR-A](https://www.sigidwiki.com/wiki/SITOR-A) | 3–30 | 0.35 | FSK | USB |
| [SITOR-B](https://www.sigidwiki.com/wiki/SITOR-B) | 3–30 | 0.35 | FSK | USB |
| [SkyOFDM](https://www.sigidwiki.com/wiki/SkyOFDM) | 3–30 | 2, 2.4 | PSK, OFDM | USB |
| [Slow-Scan Television (SSTV)](https://www.sigidwiki.com/wiki/Slow-Scan_Television_(SSTV)) | 3–450 | 3 | FM | USB, LSB, NFM |
| [Sonne](https://www.sigidwiki.com/wiki/Sonne) | 0.25–0.35 | 0.001 | OOK | USB |
| [SP-14 (XP)](https://www.sigidwiki.com/wiki/SP-14_(XP)) | 9–12 | 1.2 | MFSK | AM |
| [SPREAD](https://www.sigidwiki.com/wiki/SPREAD) | 3–30 | 0.6 | FSK | USB |
| [STANAG 4197](https://www.sigidwiki.com/wiki/STANAG_4197) | 3–30 | 2.3 | PSK, OFDM | USB |
| [STANAG 4285](https://www.sigidwiki.com/wiki/STANAG_4285) | 1.89–22.7 | 2.75 | PSK | USB |
| [STANAG 4415](https://www.sigidwiki.com/wiki/STANAG_4415) | 3–30 | 2.75 | PSK | USB |
| [STANAG 4481](https://www.sigidwiki.com/wiki/STANAG_4481) | 2.815, 3.046, 8.986, 11.213, … | 1.5, 2.75 | FSK, PSK | USB |
| [STANAG 4529](https://www.sigidwiki.com/wiki/STANAG_4529) | 3, 9.87, 30 | 1.24 | PSK, BPSK, QPSK, 8PSK | USB |
| [STANAG 4539](https://www.sigidwiki.com/wiki/STANAG_4539) | 3–30 | 3 | PSK, QAM, QPSK | USB |
| [STANAG 5065](https://www.sigidwiki.com/wiki/STANAG_5065) | 0.05–0.16 | 0.235, 0.36 | FSK, MSK | USB |
| [STANAG 5069](https://www.sigidwiki.com/wiki/STANAG_5069) | 3–30 | 3, 6, 9, 12, 15, … | PSK, QAM | USB |
| [SWED-ARQ](https://www.sigidwiki.com/wiki/SWED-ARQ) | 3–30 | 0.6 | FSK | USB |
| [TDF](https://www.sigidwiki.com/wiki/TDF) | 0.162 | 0.001 | PSK | USB |
| [Thales Système 3000 HF Modem](https://www.sigidwiki.com/wiki/Thales_Syst%C3%A8me_3000_HF_Modem) | 1.5–30 | 2, 3 | PSK, MFSK | USB |
| [Thales Système 3000 Skyhopper](https://www.sigidwiki.com/wiki/Thales_Syst%C3%A8me_3000_Skyhopper) | 1.5–30 | 2, 2.6 | PSK, MFSK | USB |
| [Thales Système 3000 Voice Scrambler](https://www.sigidwiki.com/wiki/Thales_Syst%C3%A8me_3000_Voice_Scrambler) | 1.5–30 | 3 | PSK, MFSK | USB |
| [The Alarm](https://www.sigidwiki.com/wiki/The_Alarm) | 4.77 | 2.4 | — | USB |
| [The Buzzer (ZhUOZ MDZhB UZB76)](https://www.sigidwiki.com/wiki/The_Buzzer_(ZhUOZ_MDZhB_UZB76)) | 4.625 | 2.8 | USB | AM |
| [The Goose](https://www.sigidwiki.com/wiki/The_Goose) | 3.243–4.31 | 3.1 | AM | USB |
| [THOR](https://www.sigidwiki.com/wiki/THOR) | 3–30 | 0.173, 0.244, 0.262, 0.346, 0.355, … | IFK | USB |
| [THROB](https://www.sigidwiki.com/wiki/THROB) | 3–30 | 0.072, 0.094, 0.144, 0.188 | MFSK | USB |
| [TT2300](https://www.sigidwiki.com/wiki/TT2300) | 5.0287, 5.1097, 7.7167, 7.7197 | 1.6, 1.7 | MFSK | USB |
| [TWINPLEX](https://www.sigidwiki.com/wiki/TWINPLEX) | 3–30 | 0.45, 0.55, 0.66, 0.75, 0.95 | MFSK | USB |
| [UK AM Data System (UK-AMDS)](https://www.sigidwiki.com/wiki/UK_AM_Data_System_(UK-AMDS)) | 0.198 | 0.085 | AM, PSK | SSB |
| [UK GOV MIL WINDRM51](https://www.sigidwiki.com/wiki/UK_GOV_MIL_WINDRM51) | 9.104–13.4512 | 2.5 | OFDM | USB |
| [VARA HF](https://www.sigidwiki.com/wiki/VARA_HF) | 1.8–54 | 2.75 | BPSK, 4-8PSK, 16-32QAM, FSK | USB |
| [VEZHA-S](https://www.sigidwiki.com/wiki/VEZHA-S) | 2.755–12.165 | 0.65 | FSK | USB |
| [VISEL](https://www.sigidwiki.com/wiki/VISEL) | 3–30 | 0.4 | FSK | USB |
| [VOICE](https://www.sigidwiki.com/wiki/VOICE) | 3–30 | 0.2 | MFSK | USB |
| [WEFAX](https://www.sigidwiki.com/wiki/WEFAX) | 3–30 | 3 | FM | USB |
| [WinDRM](https://www.sigidwiki.com/wiki/WinDRM) | 14.236 | 2.2, 2.4 | QAM, OFDM | USB |
| [WSPR](https://www.sigidwiki.com/wiki/WSPR) | 0.136, 0.4742, 1.8366, 3.5686, … | 0.006 | MFSK | USB |
| [WWVB](https://www.sigidwiki.com/wiki/WWVB) | 0.06 | 0.001 | ASK | CW |
| [Yachta T-219 Voice Scrambler](https://www.sigidwiki.com/wiki/Yachta_T-219_Voice_Scrambler) | 3–30 | 2.7 | FSK | USB |
| [Yugoslavian 16-Tone Modem](https://www.sigidwiki.com/wiki/Yugoslavian_16-Tone_Modem) | 3–30 | 2.1 | PSK, OFDM | USB |
| [Yugoslavian 20-Tone Modem](https://www.sigidwiki.com/wiki/Yugoslavian_20-Tone_Modem) | 3–30 | 2.2 | PSK, OFDM | USB |

## Tier B — needs the AM or FM filter (3.6–15 kHz)

| Signal (sigidwiki) | Frequencies, MHz | Bandwidth, kHz | Modulation | Rig mode |
|---|---|---|---|---|
| [AFSK Paging Link](https://www.sigidwiki.com/wiki/AFSK_Paging_Link) | 72, 76, 450, 460, … | 9 | AFSK | NFM |
| [Amplitude Modulation (AM)](https://www.sigidwiki.com/wiki/Amplitude_Modulation_(AM)) | 0.153–137 | 10 | AM | AM |
| [Automatic Transmitter Identification System (ATIS)](https://www.sigidwiki.com/wiki/Automatic_Transmitter_Identification_System_(ATIS)) | 30–800 | 12 | FSK | NFM |
| [Binary Interchange of Information and Signaling (BIIS)](https://www.sigidwiki.com/wiki/Binary_Interchange_of_Information_and_Signaling_(BIIS)) | 35, 150, 446, 800 | 6 | FFSK | NFM |
| [BRAS-3 (RS-10)](https://www.sigidwiki.com/wiki/BRAS-3_(RS-10)) | 1.685, 1.712, 1.774, 1.791, … | 14 | AM, Pulse | AM |
| [CCIR Selcall](https://www.sigidwiki.com/wiki/CCIR_Selcall) | 30–800 | 5 | MFSK | NFM |
| [CCITT](https://www.sigidwiki.com/wiki/CCITT) | 30–800 | 5 | MFSK | NFM |
| [Chinese 'Foghorn' OTH radar](https://www.sigidwiki.com/wiki/Chinese_%27Foghorn%27_OTH_radar) | 6–29 | 10 | FMCW | USB |
| [Chinese Firedrake Jammer](https://www.sigidwiki.com/wiki/Chinese_Firedrake_Jammer) | 6–18 | 10 | AM | AM |
| [Chinese Multitonal Jammer](https://www.sigidwiki.com/wiki/Chinese_Multitonal_Jammer) | 9.045 | 10 | PPM | USB |
| [CIS FTM-4](https://www.sigidwiki.com/wiki/CIS_FTM-4) | 4–20 | 13 | MFSK | USB |
| [CIS MFSK-68](https://www.sigidwiki.com/wiki/CIS_MFSK-68) | 7.659–18.28 | 10 | MFSK, PSK | USB |
| [Continuous Tone-Coded Squelch System (CTCSS)](https://www.sigidwiki.com/wiki/Continuous_Tone-Coded_Squelch_System_(CTCSS)) | 30–800 | 5, 12.5, 30 | CW | NFM |
| [Cuban Jammer](https://www.sigidwiki.com/wiki/Cuban_Jammer) | 5.98, 6.03, 7.335, 7.355, … | 10 | — | DSB |
| [Digital Mobile Radio (DMR)](https://www.sigidwiki.com/wiki/Digital_Mobile_Radio_(DMR)) | 66, 88, 136, 174, … | 12.5 | 4FSK | NFM |
| [Digital Radio Mondiale (DRM)](https://www.sigidwiki.com/wiki/Digital_Radio_Mondiale_(DRM)) | 0.531–26.06 | 4.5, 5, 9, 10, 18, … | QAM, OFDM | USB |
| [EEA](https://www.sigidwiki.com/wiki/EEA) | 30–800 | 5 | MFSK | NFM |
| [EIA](https://www.sigidwiki.com/wiki/EIA) | 30–800 | 5 | MFSK | NFM |
| [Électricité de France HNZ](https://www.sigidwiki.com/wiki/%C3%89lectricit%C3%A9_de_France_HNZ) | 68.5–73.3 | 8 | AFSK | FM |
| [End of Train Device (EOTD)](https://www.sigidwiki.com/wiki/End_of_Train_Device_(EOTD)) | 0.0005–457.9375 | 8 | FSK | NFM |
| [EURO](https://www.sigidwiki.com/wiki/EURO) | 30–800 | 5 | MFSK | NFM |
| [F07 number station](https://www.sigidwiki.com/wiki/F07_number_station) | 5–17.5 | 4 | MFSK, BPSK, FSK | USB |
| [Futuba RC Controller](https://www.sigidwiki.com/wiki/Futuba_RC_Controller) | 72–75 | 12 | — | AM |
| [HF trading link '120 Hz FMCW idle tone'](https://www.sigidwiki.com/wiki/HF_trading_link_%27120_Hz_FMCW_idle_tone%27) | 19.31, 20.24, 20.548 | 9, 10 | OFDM | USB |
| [Iranian 'Bubble' Jammer](https://www.sigidwiki.com/wiki/Iranian_%27Bubble%27_Jammer) | 1.547, 1.575, 7.49, 7.5, … | 10, 15 | AM | AM |
| [M17 RF Protocol](https://www.sigidwiki.com/wiki/M17_RF_Protocol) | 30–10500 | 9 | 4FSK | NFM |
| [MDC1200](https://www.sigidwiki.com/wiki/MDC1200) | 30–960 | 12.5, 20 | AFSK | FM |
| [MODAT](https://www.sigidwiki.com/wiki/MODAT) | 30–800 | 5 | MFSK | NFM |
| [Motorola MOSCAD SCADA telemetry](https://www.sigidwiki.com/wiki/Motorola_MOSCAD_SCADA_telemetry) | 0.0001–470 | 12.5 | FSK | FM |
| [Multitone Paging](https://www.sigidwiki.com/wiki/Multitone_Paging) | 25, 54, 137, 174, … | 12.5, 25 | FFSK | NFM |
| [Narrow-Bandwidth Television (NBTV)](https://www.sigidwiki.com/wiki/Narrow-Bandwidth_Television_(NBTV)) | 1.8–50 | 13 | AM, FM | — |
| [NATEL](https://www.sigidwiki.com/wiki/NATEL) | 30–800 | 5 | MFSK | NFM |
| [NFM Voice](https://www.sigidwiki.com/wiki/NFM_Voice) | 27, 162.4, 470, 864 | 5, 12.5, 30 | FM | NFM |
| [Nissan Qashqai Keyless Entry LF (Intelligent Key)](https://www.sigidwiki.com/wiki/Nissan_Qashqai_Keyless_Entry_LF_(Intelligent_Key)) | 0.125 | 10 | ASK | AM / CW |
| [North Korean noise jammer](https://www.sigidwiki.com/wiki/North_Korean_noise_jammer) | 6.6 | 7 | AM | AM |
| [POCSAG](https://www.sigidwiki.com/wiki/POCSAG) | 25–932 | 9 | FSK | NFM |
| [Qi (with Xiaomi Proprietary Extension)](https://www.sigidwiki.com/wiki/Qi_(with_Xiaomi_Proprietary_Extension)) | 0.145 | 10 | ASK / FSK | AM |
| [Radio Data System (RDS)](https://www.sigidwiki.com/wiki/Radio_Data_System_(RDS)) | 65–108 | 4 | PSK | DSB |
| [Relocatable Over-the-Horizon Radar (ROTHR)](https://www.sigidwiki.com/wiki/Relocatable_Over-the-Horizon_Radar_(ROTHR)) | 5–28 | 4, 8, 16, 50, 100 | FMCW | USB |
| [Russian military 20bd 7kHz FSK](https://www.sigidwiki.com/wiki/Russian_military_20bd_7kHz_FSK) | 6.941, 6.9425, 6.961, 6.9625, … | 7 | FSK | USB |
| [Samsung Washing Machine Interference](https://www.sigidwiki.com/wiki/Samsung_Washing_Machine_Interference) | 6 | 15 | FM | USB |
| [Snap Circuits SCROV-10 Remote Control](https://www.sigidwiki.com/wiki/Snap_Circuits_SCROV-10_Remote_Control) | 27.145 | 6 | ASK | RAW |
| [SNOTEL (Snow Telemetry)](https://www.sigidwiki.com/wiki/SNOTEL_(Snow_Telemetry)) | 40.67 | 9 | PSK | NFM |
| [SOLRAD 7B (COSPAR ID: 1965-016D)](https://www.sigidwiki.com/wiki/SOLRAD_7B_(COSPAR_ID:_1965-016D)) | 0.0001–136.806 | 6 | AM, IRIG | USB |
| [Spectrum Painting](https://www.sigidwiki.com/wiki/Spectrum_Painting) | 2–10 | 4 | OFDM | USB, LSB |
| [SuperDARN (Super Dual Auroral Radar Network)](https://www.sigidwiki.com/wiki/SuperDARN_(Super_Dual_Auroral_Radar_Network)) | 9–16 | 6 | PPM | USB |
| [The 'Air Horn'](https://www.sigidwiki.com/wiki/The_%27Air_Horn%27) | 4.93 | 7 | — | USB |
| [Traffic Light Control R09](https://www.sigidwiki.com/wiki/Traffic_Light_Control_R09) | 68, 87.5, 146, 174, … | 10 | AFSK | — |
| [UTC (Coordinated Universal Time) Time Standard](https://www.sigidwiki.com/wiki/UTC_(Coordinated_Universal_Time)_Time_Standard) | 2.5, 5, 10, 15, … | 4 | — | AM |
| [VDEW](https://www.sigidwiki.com/wiki/VDEW) | 30–800 | 5 | MFSK | NFM |
| [ZVEI Selcall](https://www.sigidwiki.com/wiki/ZVEI_Selcall) | 30–800 | 5 | MFSK | NFM |

## Tier U — in range, bandwidth not listed on sigidwiki

| Signal (sigidwiki) | Frequencies, MHz | Bandwidth, kHz | Modulation | Rig mode |
|---|---|---|---|---|
| [49MHz RC Car Controller](https://www.sigidwiki.com/wiki/49MHz_RC_Car_Controller) | 49.2 | — | — | USB |
| [EasyPal Digital SSTV](https://www.sigidwiki.com/wiki/EasyPal_Digital_SSTV) | 3.735 | — | — | LSB |
| [Eurobalise downlink](https://www.sigidwiki.com/wiki/Eurobalise_downlink) | 27.095 | — | — | AM |
| [GYN2 GBR](https://www.sigidwiki.com/wiki/GYN2_GBR) | 0.081 | — | — | — |
| [High Power Auroral Stimulation (HIPAS)](https://www.sigidwiki.com/wiki/High_Power_Auroral_Stimulation_(HIPAS)) | 2.85–4.53 | — | — | — |
| [Lightning Sferics](https://www.sigidwiki.com/wiki/Lightning_Sferics) | 0–30 | — | — | — |
| [Morse Code (CW)](https://www.sigidwiki.com/wiki/Morse_Code_(CW)) | 0.003–250000 | — | OOK | CW |
| [North Korean Siren Jammer](https://www.sigidwiki.com/wiki/North_Korean_Siren_Jammer) | 4.45 | — | — | AM |
| [One Beep, Two Beeps](https://www.sigidwiki.com/wiki/One_Beep,_Two_Beeps) | 4.5, 4.508, 6.4292 | — | — | USB |
| [Pulse Coded Modulated (PCM) RC Toy](https://www.sigidwiki.com/wiki/Pulse_Coded_Modulated_(PCM)_RC_Toy) | 27.145–49 | — | PCM | — |
| [RF heating and welding interference](https://www.sigidwiki.com/wiki/RF_heating_and_welding_interference) | 24, 27, 30 | — | CW, FM | USB |
| [Russian OTH 'Ghadir' type](https://www.sigidwiki.com/wiki/Russian_OTH_%27Ghadir%27_type) | 28.6 | — | — | USB |
| [SAS/SRC](https://www.sigidwiki.com/wiki/SAS/SRC) | 0.0404 | — | MSK | — |
| [SAS2](https://www.sigidwiki.com/wiki/SAS2) | 0.0425 | — | MSK | — |
| [SAS3](https://www.sigidwiki.com/wiki/SAS3) | 0.0442 | — | MSK | — |
| [SHR](https://www.sigidwiki.com/wiki/SHR) | 0.038 | — | MSK | — |
| [Siemens 1.5T MRI Scanner](https://www.sigidwiki.com/wiki/Siemens_1.5T_MRI_Scanner) | 64 | — | — | — |
| [SSTV](https://www.sigidwiki.com/wiki/SSTV) | 3.5–4 | — | ssb | lsb |
| [Switching Electronic Interference](https://www.sigidwiki.com/wiki/Switching_Electronic_Interference) | 0.01–200 | — | — | — |
| [The Pip](https://www.sigidwiki.com/wiki/The_Pip) | 3.756–5.448 | — | — | USB,AM |
| [Zaliv52](https://www.sigidwiki.com/wiki/Zaliv52) | 4.11 | — | J3E | USB |

## Excluded — wider than the receiver (> 15 kHz)

The IC-7300 hears only a slice of these, so they're left out per your instruction.

['Ghadir' OTH Radar](https://www.sigidwiki.com/wiki/%27Ghadir%27_OTH_Radar) (60, 1000 kHz) · ['OTH-SW' OTH Radar](https://www.sigidwiki.com/wiki/%27OTH-SW%27_OTH_Radar) (40, 60, 80 kHz) · [17067bps FSK](https://www.sigidwiki.com/wiki/17067bps_FSK) (25 kHz) · [AC Interference](https://www.sigidwiki.com/wiki/AC_Interference) (30 kHz) · [ATSC Broadcast](https://www.sigidwiki.com/wiki/ATSC_Broadcast) (6000 kHz) · [Canadian Meteor Orbit Radar (CMOR)](https://www.sigidwiki.com/wiki/Canadian_Meteor_Orbit_Radar_(CMOR)) (28 kHz) · [Chinese 160kHz-wide OTH radar](https://www.sigidwiki.com/wiki/Chinese_160kHz-wide_OTH_radar) (160 kHz) · [CIS W-MFSK-17](https://www.sigidwiki.com/wiki/CIS_W-MFSK-17) (37.5 kHz) · [CIS-48](https://www.sigidwiki.com/wiki/CIS-48) (2000, 3000 kHz) · [CODAR](https://www.sigidwiki.com/wiki/CODAR) (50 kHz) · [Contrôle de vitesse par balises (KVB)](https://www.sigidwiki.com/wiki/Contr%C3%B4le_de_vitesse_par_balises_(KVB)) (100 kHz) · [Digisonde](https://www.sigidwiki.com/wiki/Digisonde) (30 kHz) · [Digital Radio Mondiale Plus (DRM+)](https://www.sigidwiki.com/wiki/Digital_Radio_Mondiale_Plus_(DRM%2B)) (100 kHz) · [Duga radar](https://www.sigidwiki.com/wiki/Duga_radar) (40, 800 kHz) · [Ethernet Over Powerline](https://www.sigidwiki.com/wiki/Ethernet_Over_Powerline) (60000 kHz) · [FM Broadcast Radio](https://www.sigidwiki.com/wiki/FM_Broadcast_Radio) (38–200 kHz) · [Gonets](https://www.sigidwiki.com/wiki/Gonets) (20 kHz) · [Google Pixel Interference](https://www.sigidwiki.com/wiki/Google_Pixel_Interference) (1000 kHz) · [HD Radio (AM)](https://www.sigidwiki.com/wiki/HD_Radio_(AM)) (30 kHz) · [HAARP](https://www.sigidwiki.com/wiki/High_Frequency_Active_Auroral_Research_Program_(HAARP)) (100 kHz) · [LORAN](https://www.sigidwiki.com/wiki/LORAN) (20 kHz) · [Multiplexed Analogue Components (MAC)](https://www.sigidwiki.com/wiki/Multiplexed_Analogue_Components_(MAC)) (7800+ kHz) · [Near Field Communication (NFC)](https://www.sigidwiki.com/wiki/Near_Field_Communication_(NFC)) (1700 kHz) · [NTSC Broadcast](https://www.sigidwiki.com/wiki/NTSC_Broadcast) (6000 kHz) · [PAL Broadcast](https://www.sigidwiki.com/wiki/PAL_Broadcast) (6000+ kHz) · [PLUTO II OTH Radar](https://www.sigidwiki.com/wiki/PLUTO_II_OTH_Radar) (20, 40 kHz) · [Podsolnukh 'Sunflower' Radar](https://www.sigidwiki.com/wiki/Podsolnukh_%27Sunflower%27_Radar) (50 kHz) · [Primex Wireless Time Sync](https://www.sigidwiki.com/wiki/Primex_Wireless_Time_Sync) (20 kHz) · [SECAM](https://www.sigidwiki.com/wiki/SECAM) (6000+ kHz) · [SIMONe meteor radar](https://www.sigidwiki.com/wiki/SIMONe_meteor_radar) (140 kHz) · [SKiYMET meteor radar](https://www.sigidwiki.com/wiki/SKiYMET_meteor_radar) (160 kHz) · [Thales SALAMANDRE (HFXL)](https://www.sigidwiki.com/wiki/Thales_SALAMANDRE_(HFXL)) (150 kHz) · [Ultra Low Latency (ULL) Electronic Trading Network](https://www.sigidwiki.com/wiki/Ultra_Low_Latency_(ULL)_Electronic_Trading_Network) (30, 60 kHz) · [Vietnamese Siren Jammer](https://www.sigidwiki.com/wiki/Vietnamese_Siren_Jammer) (2700 kHz) · [XMPP trials](https://www.sigidwiki.com/wiki/XMPP_trials) (34 kHz)

## Excluded — no frequency listed on sigidwiki

[4G LTE 450MHz](https://www.sigidwiki.com/wiki/4G_LTE_450MHz) · [ATSC 3.0 Broadcast](https://www.sigidwiki.com/wiki/ATSC_3.0_Broadcast) · [COFDMTV](https://www.sigidwiki.com/wiki/COFDMTV) · [Induction cooker interference](https://www.sigidwiki.com/wiki/Induction_cooker_interference) · [JT4](https://www.sigidwiki.com/wiki/JT4) · [Kia SVI-JFRGE04 Key Fob](https://www.sigidwiki.com/wiki/Kia_SVI-JFRGE04_Key_Fob) · [National Public Alerting System (NPAS)](https://www.sigidwiki.com/wiki/National_Public_Alerting_System_(NPAS)) · [TRIAD](https://www.sigidwiki.com/wiki/TRIAD) · [Unknown FHSS between two iPhones in the same room](https://www.sigidwiki.com/wiki/Unknown_FHSS_between_two_iPhones_in_the_same_room) · [WLO](https://www.sigidwiki.com/wiki/WLO) · [Whelen DTMF](https://www.sigidwiki.com/wiki/Whelen_DTMF) · [WiMAX](https://www.sigidwiki.com/wiki/WiMAX)

(JT4 and COFDMTV are HF-capable amateur modes despite having no frequency on sigidwiki; I'll include them in the amateur-mode batches.)
