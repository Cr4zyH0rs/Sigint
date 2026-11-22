# sigint: IC-7300 signal-ID pipeline

Captures USB audio from the rig, cuts 15 s UTC-aligned 12 kHz windows, classifies
the mode with a ResNet-18 on spectrograms, measures centre frequency and bandwidth,
logs to SQLite and (optionally) asks a local Ollama model to explain each window.

**Default is ID-only**: mode, confidence, UTC time, audio offset and bandwidth. No
content decoder runs and no message text is stored. `--label-mode` (opt-in) also runs
jt9 / faster-whisper / fldigi, only for labelling amateur training data.

## Layout
- `sigint/capture.py`: sounddevice InputStream to ring buffer with UTC anchors
- `sigint/slicer.py`: 15 s UTC boundaries, resample to 12 kHz
- `sigint/features.py`: librosa STFT spectrogram; occupancy (centre / bandwidth)
- `sigint/model.py`: ResNet-18 (1-channel) classifier
- `sigint/decoders.py`: jt9, faster-whisper, fldigi (label mode only)
- `sigint/wsjtx_udp.py`: WSJT-X UDP Decode parser (port 2237)
- `sigint/db.py`: SQLite (WAL) log
- `sigint/explain.py`: Ollama `/api/generate` client
- `sigint/pipeline.py`: orchestration and CLI
- `sigint/synth.py`: synthetic FT8 (via WSJT-X ft8sim), CW, RTTY, PSK31, SSB (espeak-ng), noise
- `stress/`: dataset build, training, and the 100x stress harness (`run_all.py`)
- `results/`: JSON output of every stress run

## Run
```
pip install numpy scipy librosa soundfile sounddevice torch torchvision requests
sudo apt install wsjtx            # jt9, ft8sim (training data + label mode)
python stress/make_dataset.py 400 && python stress/train.py 8
python -m sigint.pipeline --model data/resnet18_modes.pt --device "USB Audio CODEC" --dial-hz 14074000
python stress/run_all.py --n 100 --seed 0      # all stress tests
```
