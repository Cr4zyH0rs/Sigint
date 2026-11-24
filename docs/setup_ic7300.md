# Setup guide: running sigint on your own computer with the IC-7300

Version 0.12.0, written 2026-11-24. The pipeline only identifies signals. It names the mode and
logs the time, audio offset, bandwidth and confidence. It never decodes or stores message text.

## 1. Get the code and the model

```
git clone https://github.com/Cr4zyH0rs/Sigint.git sigint
cd sigint
```
The newest model, `data/resnet18_modes_b14_10.pt` (71 classes), is in the repo.

## 2. Install Python packages

Use Python 3.11 or newer. These are the versions the tests ran with:
```
pip install numpy==2.5.3 scipy==1.18.1 librosa==1.0.1 soundfile==0.14.0 sounddevice==0.5.6 torch==2.15.0 torchvision==0.29.2 requests==2.34.2
```
- `sounddevice` needs PortAudio. pip installs it automatically on Windows and macOS. On Linux, install `libportaudio2` ([python-sounddevice](https://python-sounddevice.readthedocs.io/en/latest/installation.html)).
- On Windows, install Icom's IC-7300 USB driver from Icom's website. It is the Silicon Labs CP210x installer `CP210xVCPInstaller_x64.exe` ([SCARCS IC-7300 digital setup](https://scarcs.ca/howto/7300digital)).
- WSJT-X, fldigi and Ollama are **not** needed for ID-only use.

## 3. Rig settings (MENU → SET → Connectors)

| Setting | Value | Source |
|---|---|---|
| Mode | USB-D (USB data mode) | [SCARCS](https://scarcs.ca/howto/7300digital), [3FS](https://3fs.net.au/ic-7300/icom-ic-7300-digital-setup-for-wsjt-x/) |
| ACC/USB Output Select | AF (IF would send a 12 kHz IF signal instead) | [IC-7300 Full Manual p. 12-7](https://www.manualslib.com/manual/1106166/Icom-Ic-7300.html?page=122) |
| ACC/USB AF Output Level | Start at 40%. Lower it if the audio clips. | SCARCS 40%, 3FS 10–30%, manual default 50% |
| DATA MOD | USB | [Manual p. 12-8](https://www.manualslib.com/manual/1106166/Icom-Ic-7300.html?page=123), SCARCS |
| Filter | FIL1, BW 3.6k (the widest). Several modes here are up to 3 kHz wide. | SCARCS, 3FS |

Turn AGC and noise reduction off, or set them low. They change the audio the model was trained on. This is my recommendation; none of the sources above states it.

### IC-7100 (VHF/UHF FM signals, batch 14)

The steps are the same. Set the radio to FM and set these:
- ACC/USB Output Select = AF.
- USB Audio SQL = OFF (OPEN), so the audio is not gated by squelch. Both are in the Connectors menu ([IC-7100 manual p. 190](https://www.manualslib.com/manual/1419805/Icom-Ic-7100.html?page=190)).

Useful checks:
- APRS on 144.390 MHz (North America) or 144.800 MHz (Europe) ([sigidwiki](https://www.sigidwiki.com/wiki/APRS)).
- NOAA Weather Radio alerts.

## 4. Find the audio device name

```
python3 -m sounddevice
```
This lists every audio device ([sounddevice docs](https://python-sounddevice.readthedocs.io/en/latest/usage.html)). Pick the IC-7300 input; it usually contains "USB Audio CODEC". Use part of that name with `--device`.

## 5. Run it

```
python -m sigint.pipeline --model data/resnet18_modes_b14_10.pt --device "USB Audio CODEC" --dial-hz 14074000 --no-llm --db sigint.sqlite
```
- Every 15 s on the UTC boundary, it logs one window: the mode label, confidence, audio offset (Hz), bandwidth and rough SNR.
- `--dial-hz` is the rig's dial frequency. It helps tell FT8 from JS8, and JT9 from WSPR and FST4 (`sigint/bandplan.py`). Change it when you change band.
- `--no-llm` skips the explanation. To get short plain-English notes instead, install [Ollama](https://ollama.com) and run `ollama pull llama3.2:3b`. Then leave out `--no-llm`. The pipeline calls Ollama at `http://localhost:11434`.
- To test without the rig: `python -m sigint.pipeline --model data/resnet18_modes_b14_10.pt --no-llm --wav file.wav`.

## 6. Where results go

Results go to the SQLite file `sigint.sqlite`, table `windows`:
- `utc_start`, `label`, `confidence`
- `freq_hz`: the audio offset. Add `dial_hz` to get the RF frequency.
- `bw_hz`, `snr_db`, `dial_hz`

The `decodes` table stays empty in ID-only mode. Example query:
```
sqlite3 sigint.sqlite "select datetime(utc_start,'unixepoch'), label, round(confidence,2), round(freq_hz), round(bw_hz) from windows order by id desc limit 20;"
```

## 7. Check it against known signals

- Tune 14.074 MHz USB-D. That is the 20 m FT8 frequency ([sigidwiki: FT8](https://www.sigidwiki.com/wiki/FT8), [M0PWX list](https://www.qsl.net/m0pwx/modes-and-freq.htm)). Most windows should say `ft8` with confidence near 1.
- WWV on 10 or 15 MHz ([NIST](https://www.nist.gov/pml/div688/grp40/wwv_format)) should say `wwv` when the ticks are audible.

**What to expect from the tests on synthetic and recorded test audio** (`docs/batch11_results.md`):
- About 99% correct at 0 dB SNR and up.
- About 98% correct at −10 dB and up.
- Below −10 dB, many windows are wrong.
- "unknown" means the model's pick failed its signature check (`sigint/signature.py`).
- Real on-air audio has not been tested yet; that was the skipped batch 12.

## 8. Reporting a miss

Send the UTC time, dial frequency, the label it gave and what the signal really was. If you can, record the audio first. Make a 15 s 48 kHz WAV, for example from Audacity, and run it with `--wav`, then send the WAV. That lets me add it to testing.
