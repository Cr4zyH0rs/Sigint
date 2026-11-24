"""End-to-end pipeline: capture -> slice -> classify -> measure -> log -> explain.

Default mode is ID-only: each window is reported as mode label, confidence, UTC
time, audio-offset frequency and occupied bandwidth. No content decoder runs and
no message text is stored.

`--label-mode` (opt-in) additionally runs the content decoders (jt9, faster-whisper,
fldigi). It exists only to label amateur training data, e.g. keep an FT8 clip as
training data only if WSJT-X's own decoder confirms it is FT8.

Run live:   python -m sigint.pipeline --device "USB Audio CODEC" --model data/resnet18_modes.pt
Run on WAVs: python -m sigint.pipeline --wav file1.wav file2.wav ...
"""
from __future__ import annotations

import argparse
import datetime as dt
import logging
import time
from dataclasses import dataclass, field

import numpy as np
import soundfile as sf

from . import acf, bandplan, decoders, features, signature, slicer
from .synth import CLASSES
from .db import Log
from .explain import Explainer, build_prompt, build_prompt_id

log = logging.getLogger("sigint")


@dataclass
class WindowResult:
    utc_start: float
    label: str
    confidence: float
    freq_hz: float | None = None
    bw_hz: float | None = None
    snr_db: float | None = None
    decodes: list = field(default_factory=list)
    explanation: str = ""
    timings: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)


class Pipeline:
    def __init__(self, classifier, db: Log, explainer: Explainer | None = None,
                 whisper=None, fldigi=None, min_conf=0.5, always_try_ft8=True,
                 label_mode=False, dial_hz=None):
        self.clf, self.db, self.explainer = classifier, db, explainer
        self.label_mode = label_mode  # False = ID-only (default)
        self.dial_hz = dial_hz
        self.llm_pool = None  # set to a ThreadPoolExecutor in live mode
        self.whisper, self.fldigi = whisper, fldigi
        self.min_conf = min_conf
        # FT8 decoding is cheap (~1-2 s) and the classifier can miss weak FT8
        # under another label, so by default jt9 runs on every window.
        self.always_try_ft8 = always_try_ft8

    def _explain(self, wid, prompt, res):
        ok, text = self.explainer.explain(prompt)
        res.explanation = text
        self.db.log_explanation(wid, self.explainer.model, text, ok)

    def route(self, label, x12k, res: WindowResult):
        decs = []
        try:
            if label == "ft8" or self.always_try_ft8:
                t = time.perf_counter()
                decs += decoders.decode_ft8(x12k)
                res.timings["jt9"] = time.perf_counter() - t
            if label == "ssb" and self.whisper is not None:
                t = time.perf_counter()
                decs += self.whisper.decode(x12k)
                res.timings["whisper"] = time.perf_counter() - t
            if label in ("rtty", "psk31") and self.fldigi is not None:
                t = time.perf_counter()
                self.fldigi.tune(label)
                decs += decoders.decode_fldigi(self.fldigi, label)
                res.timings["fldigi"] = time.perf_counter() - t
        except Exception as e:  # one bad decoder must not kill the loop
            res.errors.append(f"{label}: {type(e).__name__}: {e}")
            log.exception("decoder failed")
        return decs

    def process(self, x12k: np.ndarray, utc_start: float, dial_hz: float | None = None) -> WindowResult:
        t0 = time.perf_counter()
        spec = self.clf.featurize(x12k)
        t1 = time.perf_counter()
        label, conf, probs = self.clf.predict(spec)
        t2 = time.perf_counter()
        dial = dial_hz if dial_hz is not None else self.dial_hz
        res = WindowResult(utc_start, label, conf)
        if label != "noise":
            res.freq_hz, res.bw_hz, res.snr_db = features.occupancy_for(label, x12k)
        if dial is not None and res.freq_hz is not None:
            # RF tie-breaker: FT8 vs JS8, JT9 vs WSPR vs FST4 (see bandplan.py)
            label, conf, probs = bandplan.reweight(probs, CLASSES[:len(probs)], dial, res.freq_hz)
            res.label, res.confidence = label, conf
        if label in acf.WIDE_MIL:
            # periodicity second opinion for look-alike military modems (sigint/acf.py)
            label, conf, probs, _ = acf.reweight(label, probs, CLASSES[:len(probs)], x12k, res.freq_hz)
            res.label, res.confidence = label, conf
        if label in signature.CHECKED:
            # WWV / DTMF / HamDRM / STANAG 4539 only when their published signature is present;
            # otherwise "unknown" (sigint/signature.py)
            label, conf, probs, _ = signature.reweight(label, probs, CLASSES[:len(probs)], x12k)
            res.label, res.confidence = label, conf
        t25 = time.perf_counter()
        res.timings.update(spectrogram=t1 - t0, classify=t2 - t1, occupancy=t25 - t2)
        if self.label_mode:
            res.decodes = self.route(label if conf >= self.min_conf else "unknown", x12k, res)
        t3 = time.perf_counter()
        wid = self.db.log_window(utc_start, label, conf, probs, res.decodes, res.freq_hz,
                                 res.bw_hz, res.snr_db, dial)
        res.timings["db"] = time.perf_counter() - t3
        if self.explainer is not None:
            iso = dt.datetime.fromtimestamp(utc_start, dt.timezone.utc).isoformat()
            prompt = (build_prompt(iso, label, conf, res.decodes) if self.label_mode else
                      build_prompt_id(iso, label, conf, res.freq_hz, res.bw_hz, res.snr_db))
            if self.llm_pool is not None:
                # live mode: never block the capture loop on the LLM (a down server with
                # timeout=60 s and 2 retries would otherwise stall it ~3 minutes)
                self.llm_pool.submit(self._explain, wid, prompt, res)
            else:
                t4 = time.perf_counter()
                self._explain(wid, prompt, res)
                res.timings["llm"] = time.perf_counter() - t4
        res.timings["total"] = time.perf_counter() - t0
        return res

    def run_live(self, capture, poll=0.5):
        from concurrent.futures import ThreadPoolExecutor
        self.llm_pool = ThreadPoolExecutor(max_workers=1)
        capture.start()
        last = None
        try:
            while True:
                now = time.time()
                for t in slicer.next_boundaries(last, now):
                    x = slicer.slice_window(capture, t)
                    last = t
                    if x is None:
                        log.warning("window %s not in buffer (overflow or startup)", t)
                        continue
                    r = self.process(x, t)
                    log.info("%s %s conf=%.2f f=%s bw=%s", t, r.label, r.confidence,
                             r.freq_hz, r.bw_hz)
                time.sleep(poll)
        finally:
            capture.stop()
            self.llm_pool.shutdown(wait=False, cancel_futures=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--db", default="sigint.sqlite")
    ap.add_argument("--device")
    ap.add_argument("--samplerate", type=int, default=48000)
    ap.add_argument("--wav", nargs="*")
    ap.add_argument("--ollama-model", default="llama3.2:3b")
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--whisper", default="base.en")
    ap.add_argument("--label-mode", action="store_true",
                    help="opt-in: also run content decoders to label training data")
    ap.add_argument("--dial-hz", type=float, help="rig dial frequency, stored with each window")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO)
    from .model import Classifier
    from .fldigi_client import FldigiClient
    whisper = fl = None
    if a.label_mode:
        fl = FldigiClient()
        fl = fl if fl.ping() else None
        try:
            whisper = decoders.WhisperDecoder(a.whisper)
        except Exception as e:
            log.warning("whisper unavailable: %s", e)
    p = Pipeline(Classifier(a.model), Log(a.db),
                 None if a.no_llm else Explainer(a.ollama_model), whisper, fl,
                 label_mode=a.label_mode, dial_hz=a.dial_hz)
    if a.wav:
        for f in a.wav:
            x, fs = sf.read(f, dtype="float32")
            x = slicer.to_12k(x if x.ndim == 1 else x.mean(1), fs)
            r = p.process(x, time.time())
            print(f, r.label, f"{r.confidence:.2f}", r.freq_hz, r.bw_hz,
                  [d.text for d in r.decodes] if a.label_mode else "", r.explanation)
    else:
        from .capture import AudioCapture
        p.run_live(AudioCapture(device=a.device, samplerate=a.samplerate))


if __name__ == "__main__":
    main()
