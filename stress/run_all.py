"""Run every pipeline piece N times (default 100) with randomized inputs.

Usage: python stress/run_all.py [test ...] [--n 100] [--seed 0]
Each test returns a dict of metrics; results go to results/<test>_seed<seed>.json.
"""
from __future__ import annotations

import argparse
import http.server
import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import traceback

import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sigint import capture, db, decoders, explain, features, slicer, synth, wsjtx_udp  # noqa

MODEL = os.environ.get("SIGINT_MODEL", os.path.join(ROOT, "data/resnet18_modes.pt"))
os.environ.setdefault("XDG_RUNTIME_DIR", "/tmp/xdg")
os.environ.setdefault("PULSE_SERVER", "unix:/tmp/xdg/pulse/native")


def pct(a, q):
    return float(np.percentile(a, q)) if len(a) else None


def timing(ts):
    ts = np.asarray(ts, float)
    if ts.size == 0:
        return None
    return dict(mean=float(ts.mean()), p50=pct(ts, 50), p95=pct(ts, 95), max=float(ts.max()))


def levenshtein_semiglobal(ref: str, hyp: str) -> int:
    """Edit distance of ref against the best-matching substring of hyp (leading /
    trailing noise characters in hyp are free). Used for fldigi character error rate."""
    n, m = len(ref), len(hyp)
    prev = [0] * (m + 1)  # free start anywhere in hyp
    for i in range(1, n + 1):
        cur = [i] + [0] * m
        for j in range(1, m + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ref[i - 1] != hyp[j - 1]))
        prev = cur
    return min(prev)  # free end anywhere


# ---------------------------------------------------------------- T1 ring buffer
def t_ringbuffer(n, seed):
    rng = np.random.default_rng(seed)
    fails, errs = 0, []
    for it in range(n):
        cap = int(rng.integers(1, 5000))
        rb = capture.RingBuffer(cap)
        ref = []
        for _ in range(int(rng.integers(1, 60))):
            k = int(rng.choice([0, 1, int(rng.integers(1, cap + 1)), cap, cap + int(rng.integers(1, 3 * cap))]))
            chunk = rng.normal(size=k).astype(np.float32)
            rb.write(chunk)
            ref.append(chunk)
        allx = np.concatenate(ref) if ref else np.zeros(0, np.float32)
        ok = rb.total == len(allx)
        for _ in range(20):
            s = int(rng.integers(-5, len(allx) + 5)) if len(allx) else 0
            L = int(rng.integers(0, cap + 3))
            got = rb.read_abs(s, L)
            avail = s >= max(0, len(allx) - cap) and s + L <= len(allx) and L <= cap and s >= 0
            if avail:
                ok &= got is not None and np.array_equal(got, allx[s:s + L])
            else:
                ok &= got is None
        if not ok:
            fails += 1
            errs.append(dict(it=it, cap=cap))
    return dict(runs=n, fails=fails, examples=errs[:5])


# ---------------------------------------------------------------- T2 live capture (virtual cable)
def t_capture(n, seed):
    """Play a known noise burst into PulseAudio null sink 'radio'; capture its
    monitor through sounddevice/PortAudio/ALSA-pulse; check we recover it."""
    rng = np.random.default_rng(seed)
    fs = 48000
    res, corr, lags, ovf = [], [], [], 0
    cap = capture.AudioCapture(device=None, samplerate=fs, seconds=10, blocksize=int(rng.choice([480, 1024, 4800])))
    cap.start()
    time.sleep(0.5)
    try:
        for it in range(n):
            dur = float(rng.uniform(0.2, 0.6))
            sig = (rng.normal(size=int(dur * fs)) * 0.3).astype(np.float32)
            sig = np.clip(sig, -0.99, 0.99)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                sf.write(f.name, sig, fs, subtype="FLOAT")
            t_play = time.time()
            i_before = cap.ring.total
            subprocess.run(["paplay", "--device=radio", f.name], check=True, timeout=10)
            time.sleep(0.4)
            os.unlink(f.name)
            got = cap.ring.read_abs(i_before, cap.ring.total - i_before)
            if got is None or len(got) < len(sig):
                res.append(False)
                continue
            # normalised cross-correlation peak
            from scipy.signal import correlate
            c = correlate(got, sig, mode="valid", method="fft")
            k = int(np.argmax(np.abs(c)))
            seg = got[k:k + len(sig)]
            r = float(np.dot(seg, sig) / (np.linalg.norm(seg) * np.linalg.norm(sig) + 1e-12))
            corr.append(r)
            # latency: time the burst appeared vs. when paplay was called
            utc_seen = cap.anchor[1] + (i_before + k - cap.anchor[0]) / fs
            lags.append(utc_seen - t_play)
            res.append(r > 0.98)  # PulseAudio null sink is s16le, so ~0.99 is the ceiling
        ovf = cap.overflows
    finally:
        cap.stop()
    return dict(runs=n, passes=int(sum(res)), fails=n - int(sum(res)),
                corr_min=float(min(corr)) if corr else None, corr_median=float(np.median(corr)) if corr else None,
                latency_s=timing(lags) if lags else None, input_overflows=int(ovf))


# ---------------------------------------------------------------- T3 slicer / UTC alignment
class FakeCapture:
    def __init__(self, fs, cap_s=40):
        self.fs = fs
        self.ring = capture.RingBuffer(int(fs * cap_s))
        self.anchor = None

    utc_to_index = capture.AudioCapture.utc_to_index


def t_slicer(n, seed):
    rng = np.random.default_rng(seed)
    fails, errs, offs, times = 0, [], [], []
    for it in range(n):
        fs = int(rng.choice([44100, 48000, 96000, 12000, 16000]))
        cap = FakeCapture(fs)
        utc0 = 1.7e9 + float(rng.uniform(0, 86400))  # random time of day
        jitter = float(rng.uniform(-0.02, 0.02))  # anchor timestamp error (callback jitter)
        dur = 35.0
        nsamp = int(dur * fs)
        x = (rng.normal(size=nsamp) * 0.01).astype(np.float32)
        # put a 5 ms click exactly at the first period boundary + 0.5 s (FT8 start time)
        b = slicer.period_start(utc0) + 15.0
        click_utc = b + 0.5
        ci = int(round((click_utc - utc0) * fs))
        x[ci:ci + int(0.005 * fs)] = 1.0
        # write in random block sizes, updating anchor like the callback does
        i = 0
        while i < nsamp:
            k = int(rng.integers(1, int(0.2 * fs)))
            cap.anchor = (cap.ring.total, utc0 + i / fs + jitter)
            cap.ring.write(x[i:i + k])
            i += k
        t = time.perf_counter()
        y = slicer.slice_window(cap, b)
        times.append(time.perf_counter() - t)
        ok = y is not None and len(y) == 180000
        if ok:
            pk = int(np.argmax(y > 0.5 * y.max())) / 12000.0  # rising edge of the click
            # anchor says utc = true + jitter, so the slice starts `jitter` early
            # and the click lands at 0.5 + jitter in the output
            offs.append(pk - 0.5 - jitter)
            ok &= abs(pk - 0.5 - jitter) < 0.002
        # boundary generator: no gaps/dupes
        seq, last = [], None
        now = utc0
        for _ in range(int(rng.integers(5, 40))):
            now += float(rng.uniform(0.1, 40))
            got = list(slicer.next_boundaries(last, now))
            seq += got
            if got:
                last = got[-1]
        ok &= all(abs(b2 - a2 - 15.0) < 1e-6 for a2, b2 in zip(seq, seq[1:]))
        ok &= all(abs(s % 15.0) < 1e-6 or abs(s % 15.0 - 15) < 1e-6 for s in seq)
        if not ok:
            fails += 1
            errs.append(dict(it=it, fs=fs, jitter=jitter, off_ms=(offs[-1] * 1000 if offs else None)))
    offs = np.abs(offs)
    return dict(runs=n, fails=fails, examples=errs[:5], click_offset_ms_max=float(offs.max() * 1000),
                slice_time=timing(times))


# ---------------------------------------------------------------- T4 FT8 via real jt9
def t_ft8_jt9(n, seed):
    rng = np.random.default_rng(seed)
    rows, times = [], []
    for it in range(n):
        snr = float(rng.uniform(-26, 0))
        x, msgs = synth.gen_ft8(rng, snr, 1)
        t = time.perf_counter()
        decs = decoders.decode_ft8(x)
        times.append(time.perf_counter() - t)
        want = msgs[0]["msg"]
        hit = any(d.text == want for d in decs)
        false = [d.text for d in decs if d.text != want]
        snr_rep = next((d.snr for d in decs if d.text == want), None)
        rows.append(dict(snr=snr, hit=hit, false=false, snr_reported=snr_rep, f0=msgs[0]["f0"]))
    bins = {}
    for lo in range(-26, 0, 2):
        r = [x for x in rows if lo <= x["snr"] < lo + 2]
        if r:
            bins[f"{lo}..{lo+2}"] = dict(n=len(r), decode_rate=sum(x["hit"] for x in r) / len(r))
    snr_err = [x["snr_reported"] - x["snr"] for x in rows if x["snr_reported"] is not None]
    # multi-signal windows (crowded band)
    multi = []
    for it in range(max(1, n // 4)):
        k = int(rng.integers(2, 9))
        x, msgs = synth.gen_ft8(rng, float(rng.uniform(-15, 0)), k)
        decs = decoders.decode_ft8(x)
        got = {d.text for d in decs}
        multi.append(dict(sent=k, decoded=sum(m["msg"] in got for m in msgs)))
    return dict(runs=n, decode_rate=sum(r["hit"] for r in rows) / n,
                false_decodes=sum(len(r["false"]) for r in rows), by_snr=bins,
                snr_report_bias_db=float(np.mean(snr_err)) if snr_err else None,
                snr_report_sd_db=float(np.std(snr_err)) if snr_err else None,
                jt9_time=timing(times), multi_signal=multi,
                multi_recall=sum(m["decoded"] for m in multi) / sum(m["sent"] for m in multi),
                false_examples=[f for r in rows for f in r["false"]][:5])


# ---------------------------------------------------------------- T5 classifier
def t_classifier(n, seed, model_path=None):
    model_path = model_path or MODEL
    from sigint.model import Classifier
    clf = Classifier(model_path)
    rng = np.random.default_rng(seed + 5_000_000)
    C = synth.CLASSES[:clf.model.fc.out_features]
    conf = np.zeros((len(C), len(C)), int)
    rows, times = [], []
    for ci, c in enumerate(C):
        for k in range(n):
            snr = float(rng.uniform(-20, 15))
            x, _ = synth.generate(c, rng, snr)
            s = clf.featurize(x)
            t = time.perf_counter()
            lab, p, probs = clf.predict(s)
            if os.environ.get("SIGINT_SIGCHECK") == "1":
                from sigint import signature
                lab, p, _, _ = signature.reweight(lab, probs, C, x)
            times.append(time.perf_counter() - t)
            conf[ci, C.index(lab)] += 1
            rows.append(dict(true=c, pred=lab, p=p, snr=snr))
    bins = {}
    for lo in range(-20, 15, 5):
        r = [x for x in rows if lo <= x["snr"] < lo + 5 and x["true"] != "noise"]
        bins[f"{lo}..{lo+5}"] = dict(n=len(r), acc=sum(x["true"] == x["pred"] for x in r) / max(1, len(r)))
    # determinism: same input 100x
    x, _ = synth.generate("psk31", np.random.default_rng(1), 0)
    s = clf.featurize(x)
    outs = {clf.predict(s)[0] for _ in range(n)}
    per_class = {c: float(conf[i, i] / conf[i].sum()) for i, c in enumerate(C)}
    # target set chosen by the user: windows at SNR >= -10 dB
    hi_rows = [r for r in rows if r["snr"] >= -10]
    ge0 = [r for r in rows if r["snr"] >= 0]
    per_class_ge_m10 = {c: (sum(r["pred"] == c for r in hi_rows if r["true"] == c) /
                            max(1, sum(r["true"] == c for r in hi_rows))) for c in C}
    errs_ge_m10 = {}
    for r in hi_rows:
        if r["pred"] != r["true"]:
            k = f'{r["true"]}->{r["pred"]}'
            errs_ge_m10[k] = errs_ge_m10.get(k, 0) + 1
    # calibration: accuracy among high-confidence predictions
    hi = [r for r in rows if r["p"] >= 0.9]
    return dict(runs=len(rows), accuracy=float(np.trace(conf) / conf.sum()), per_class=per_class,
                acc_snr_ge_m10=sum(r["pred"] == r["true"] for r in hi_rows) / max(1, len(hi_rows)),
                n_snr_ge_m10=len(hi_rows), per_class_snr_ge_m10=per_class_ge_m10,
                acc_snr_ge_0=sum(r["pred"] == r["true"] for r in ge0) / max(1, len(ge0)), n_snr_ge_0=len(ge0),
                sigcheck=os.environ.get("SIGINT_SIGCHECK") == "1",
                errors_snr_ge_m10=dict(sorted(errs_ge_m10.items(), key=lambda kv: -kv[1])),
                confusion=dict(labels=C, matrix=conf.tolist()), acc_by_snr_signals_only=bins,
                deterministic=len(outs) == 1, infer_time=timing(times),
                high_conf_share=len(hi) / len(rows),
                high_conf_acc=sum(r["true"] == r["pred"] for r in hi) / max(1, len(hi)))


# ---------------------------------------------------------------- T6 fldigi (real) RTTY + PSK31
def _fldigi_run(label, n, seed, carrier_mode):
    from sigint.fldigi_client import FldigiClient
    cl = FldigiClient()
    if not cl.ping():
        return dict(error="fldigi not reachable")
    rng = np.random.default_rng(seed + (1 if label == "rtty" else 2))
    rows = []
    for it in range(n):
        snr = float(rng.uniform(-15, 15))
        fc = float(rng.uniform(700, 2300))
        if label == "psk31":
            text = " ".join(rng.choice(["cq", "de", "test", "name", "qth", "tnx", "73", "rig", "ant"], 3)) + " " + synth.random_call(rng).lower()
            s = synth.gen_psk31_clean(text, fc)
        else:
            text = " ".join(rng.choice(["CQ", "DE", "TEST", "QTH", "RST", "599", "TU", "73", "NAME"], 4)) + " " + synth.random_call(rng)
            s = synth.gen_rtty_clean(text, fc)
        s = s / np.sqrt(np.mean(s[np.abs(s) > 0] ** 2))
        x = np.concatenate([np.zeros(6000), s, np.zeros(9000)])
        x = synth.add_awgn(x, snr, rng, sig_rms=1.0)
        if carrier_mode == "exact":
            tune = fc
        else:
            tune = decoders.estimate_carrier(x, label)
        cl.tune(label, tune, afc=True, squelch=False)
        cl.clear()
        time.sleep(0.3)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            sf.write(f.name, (x / np.abs(x).max() * 0.5).astype(np.float32), 12000, subtype="PCM_16")
        subprocess.run(["paplay", "--device=radio", f.name], check=True, timeout=60)
        os.unlink(f.name)
        time.sleep(1.2)
        hyp = cl.rx_text()
        ref = text if label == "psk31" else text.upper()
        hyp_cmp = hyp if label == "psk31" else hyp.upper()
        ed = levenshtein_semiglobal(ref, hyp_cmp)
        rows.append(dict(snr=snr, fc=fc, tune=tune, cer=ed / len(ref), ref=ref, hyp=hyp[-80:]))
    bins = {}
    for lo in range(-15, 15, 5):
        r = [x for x in rows if lo <= x["snr"] < lo + 5]
        if r:
            bins[f"{lo}..{lo+5}"] = dict(n=len(r), mean_cer=float(np.mean([x["cer"] for x in r])),
                                         perfect=sum(x["cer"] == 0 for x in r) / len(r))
    return dict(runs=n, carrier=carrier_mode, mean_cer=float(np.mean([r["cer"] for r in rows])),
                perfect_copy_rate=sum(r["cer"] == 0 for r in rows) / n,
                usable_copy_rate_cer_le_10pct=sum(r["cer"] <= 0.1 for r in rows) / n,
                by_snr=bins, carrier_err_hz=timing([abs(r["tune"] - r["fc"]) for r in rows]),
                worst=sorted(rows, key=lambda r: -r["cer"])[:3])


def t_fldigi_psk31(n, seed):
    return _fldigi_run("psk31", n, seed, "exact")


def t_fldigi_rtty(n, seed):
    return _fldigi_run("rtty", n, seed, "exact")


def t_fldigi_psk31_est(n, seed):
    return _fldigi_run("psk31", n, seed, "estimated")


def t_fldigi_rtty_est(n, seed):
    return _fldigi_run("rtty", n, seed, "estimated")


# ---------------------------------------------------------------- T7 whisper wrapper (MOCK model)
class _Seg:
    def __init__(self, text):
        self.text = text


class StubWhisper:
    """Stands in for faster_whisper.WhisperModel (weights not downloadable here).
    Records what it was given so the test can check the wrapper's contract."""

    def __init__(self, rng):
        self.rng, self.last = rng, None

    def transcribe(self, audio, **kw):
        self.last = (audio, kw)
        k = int(self.rng.integers(0, 4))
        return iter([_Seg(f" seg{i} ") for i in range(k)]), None


def t_whisper_wrapper(n, seed):
    rng = np.random.default_rng(seed)
    stub = StubWhisper(rng)
    w = decoders.WhisperDecoder(model=stub)
    fails, times = 0, []
    for it in range(n):
        L = int(rng.integers(1200, 180001))
        x = rng.normal(size=L).astype(np.float32) * 0.1
        t = time.perf_counter()
        out = w.decode(x)
        times.append(time.perf_counter() - t)
        audio, kw = stub.last
        ok = audio.dtype == np.float32 and abs(len(audio) - L * 4 / 3) <= 2 and kw.get("language") == "en"
        ok &= all(d.text == d.text.strip() and d.text for d in out)
        if not ok:
            fails += 1
    return dict(runs=n, fails=fails, mocked=True, wrapper_time=timing(times))


# ---------------------------------------------------------------- T8 WSJT-X UDP
def t_wsjtx_udp(n, seed):
    rng = np.random.default_rng(seed)
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.bind(("127.0.0.1", 0))
    rx.settimeout(1.0)
    tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rt_fail, fuzz_crash, fuzz_examples = 0, 0, []
    for it in range(n):
        d = wsjtx_udp.UdpDecode(id="WSJT-X", new=bool(rng.integers(2)), time_ms=int(rng.integers(0, 86400000)),
                                snr=int(rng.integers(-30, 30)), dt=float(rng.normal(0, 1)), df=int(rng.integers(0, 4000)),
                                mode="~", message=synth.random_ft8_message(rng) + ("" if rng.random() < .8 else " é漢"),
                                low_confidence=bool(rng.integers(2)), off_air=bool(rng.integers(2)))
        pkt = wsjtx_udp.build_decode(d, schema=int(rng.choice([2, 3])))
        tx.sendto(pkt, rx.getsockname())
        got = wsjtx_udp.parse(rx.recv(65535))
        if got != d:
            rt_fail += 1
        # fuzz: truncate, flip bytes, random garbage
        for _ in range(10):
            b = bytearray(pkt)
            op = rng.integers(3)
            if op == 0:
                b = b[: int(rng.integers(0, len(b)))]
            elif op == 1:
                for _ in range(int(rng.integers(1, 8))):
                    b[int(rng.integers(len(b)))] = int(rng.integers(256))
            else:
                b = bytearray(rng.integers(0, 256, int(rng.integers(0, 200))).astype(np.uint8).tobytes())
            try:
                wsjtx_udp.parse(bytes(b))
            except wsjtx_udp.ParseError:
                pass
            except Exception as e:
                fuzz_crash += 1
                fuzz_examples.append(f"{type(e).__name__}: {e}")
    return dict(runs=n, roundtrip_fails=rt_fail, fuzz_cases=n * 10, fuzz_unexpected_exceptions=fuzz_crash,
                fuzz_examples=fuzz_examples[:5], mocked="sender is a test encoder, not the WSJT-X GUI")


# ---------------------------------------------------------------- T9 SQLite
def t_sqlite(n, seed):
    rng = np.random.default_rng(seed)
    fails, errs, times, rows_total = 0, [], [], 0
    for it in range(n):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "t.sqlite")
            L = db.Log(path)
            nthreads = int(rng.integers(1, 9))
            per = int(rng.integers(1, 40))
            expect_dec = [0]
            lock = threading.Lock()
            errors = []

            def worker(k, s):
                r = np.random.default_rng(s)
                try:
                    for j in range(per):
                        nd = int(r.integers(0, 6))
                        decs = [decoders.Decode("FT8", r.choice(["", "CQ K1ABC FN42", "é漢字 ' \" ; DROP TABLE x;--", "x" * int(r.integers(0, 100000))]),
                                                float(r.normal()), None, float(r.uniform(0, 3000))) for _ in range(nd)]
                        t = time.perf_counter()
                        L.log_window(time.time(), "ft8", float(r.random()), r.random(6), decs)
                        with lock:
                            times.append(time.perf_counter() - t)
                            expect_dec[0] += nd
                except Exception as e:
                    errors.append(f"{type(e).__name__}: {e}")
                finally:
                    L.close()

            ths = [threading.Thread(target=worker, args=(k, int(rng.integers(1 << 30)))) for k in range(nthreads)]
            [t.start() for t in ths]
            [t.join() for t in ths]
            c = sqlite3.connect(path)
            nw = c.execute("select count(*) from windows").fetchone()[0]
            nd = c.execute("select count(*) from decodes").fetchone()[0]
            integ = c.execute("pragma integrity_check").fetchone()[0]
            fk = c.execute("pragma foreign_key_check").fetchall()
            c.close()
            rows_total += nw
            ok = not errors and nw == nthreads * per and nd == expect_dec[0] and integ == "ok" and not fk
            if not ok:
                fails += 1
                errs.append(dict(it=it, threads=nthreads, errors=errors[:2], nw=nw, want=nthreads * per))
    return dict(runs=n, fails=fails, examples=errs[:5], windows_written=rows_total, write_time=timing(times))


# ---------------------------------------------------------------- T10 Ollama client vs MOCK server
class _MockOllama(http.server.BaseHTTPRequestHandler):
    mode = "ok"

    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        m = _MockOllama.plan.pop(0) if _MockOllama.plan else "ok"
        if m == "slow":
            time.sleep(1.5)
            m = "ok"
        if m == "500":
            self.send_response(500); self.end_headers(); self.wfile.write(b'{"error":"model not loaded"}'); return
        if m == "404":
            self.send_response(404); self.end_headers(); self.wfile.write(b'{"error":"model not found"}'); return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if m == "badjson":
            self.wfile.write(b'{"response": "trunc')
        elif m == "empty":
            self.wfile.write(json.dumps({"model": body["model"], "response": "", "done": True}).encode())
        else:
            self.wfile.write(json.dumps({"model": body["model"], "response": "Heard an FT8 CQ.", "done": True}).encode())


def t_ollama_client(n, seed):
    rng = np.random.default_rng(seed)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _MockOllama)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    url = f"http://127.0.0.1:{srv.server_address[1]}"
    faults = ["ok", "500", "404", "slow", "badjson", "empty"]
    raised, wrong, times, outcomes = 0, 0, [], {}
    retries = 2
    for it in range(n):
        plan = list(rng.choice(faults, retries + 1, p=[.4, .15, .1, .15, .1, .1]))
        down = rng.random() < 0.1
        _MockOllama.plan = list(plan)
        ex = explain.Explainer(model="llama3.2:3b", url=("http://127.0.0.1:1" if down else url), timeout=1.0,
                               retries=retries, backoff=0.05)
        expected_ok = (not down) and any(p == "ok" for p in plan)
        t = time.perf_counter()
        try:
            ok, text = ex.explain("test prompt")
        except Exception:
            raised += 1
            continue
        times.append(time.perf_counter() - t)
        if ok != expected_ok:
            wrong += 1
        key = "down" if down else ("ok" if ok else text)
        outcomes[key] = outcomes.get(key, 0) + 1
    srv.shutdown()
    return dict(runs=n, raised=raised, wrong_outcome=wrong, outcomes=outcomes, call_time=timing(times),
                mocked="Ollama server is a local mock implementing POST /api/generate")


# ---------------------------------------------------------------- T11 end-to-end
def t_occupancy(n, seed):
    """Centre-frequency and bandwidth estimates vs. known truth, n per signal class."""
    rng = np.random.default_rng(seed + 77)
    out = {}
    for c in ["ft8", "cw", "rtty", "psk31", "ssb", "noise"]:
        ferr, bws, miss, times = [], [], 0, []
        snrs_missed = []
        for it in range(n):
            snr = float(rng.uniform(-20, 15))
            x, meta = synth.generate(c, rng, snr)
            t = time.perf_counter()
            fc, bw, pk = features.occupancy_for(c, x)
            times.append(time.perf_counter() - t)
            if fc is None:
                miss += 1
                snrs_missed.append(snr)
                continue
            truth = {"ft8": lambda m: m[0]["f0"] + 21.875, "cw": lambda m: m["f0"],
                     "rtty": lambda m: m["fc"], "psk31": lambda m: m["fc"]}.get(c)
            if truth:
                ferr.append(abs(fc - truth(meta)))
            bws.append(bw)
        out[c] = dict(n=n, no_signal_found=miss,
                      median_snr_when_missed=float(np.median(snrs_missed)) if snrs_missed else None,
                      freq_abs_err_hz=timing(ferr) if ferr else None,
                      within_25hz=(sum(e <= 25 for e in ferr) / len(ferr)) if ferr else None,
                      bw_hz=dict(p10=pct(bws, 10), p50=pct(bws, 50), p90=pct(bws, 90)) if bws else None,
                      time=timing(times))
    out["noise"]["false_signal_rate"] = 1 - out["noise"]["no_signal_found"] / n
    return out


def t_end_to_end(n, seed, label_mode=False):
    from sigint.model import Classifier
    from sigint.pipeline import Pipeline
    rng = np.random.default_rng(seed + 11)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _MockOllama)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    _MockOllama.plan = []
    with tempfile.TemporaryDirectory() as d:
        p = Pipeline(Classifier(MODEL), db.Log(os.path.join(d, "e2e.sqlite")),
                     explain.Explainer(url=f"http://127.0.0.1:{srv.server_address[1]}", timeout=2, retries=1),
                     decoders.WhisperDecoder(model=StubWhisper(rng)), None, label_mode=label_mode)
        prompts = []
        orig = p.explainer.explain
        p.explainer.explain = lambda pr: (prompts.append(pr), orig(pr))[1]
        rows, errors = [], []
        for it in range(n):
            c = str(rng.choice(synth.CLASSES[:p.clf.model.fc.out_features]))
            snr = float(rng.uniform(-20, 15))
            x, meta = synth.generate(c, rng, snr)
            utc = slicer.period_start(1.7e9 + it * 15.0)
            try:
                r = p.process(x, utc)
            except Exception as e:
                errors.append(traceback.format_exc()[-300:])
                continue
            ft8_ok = None
            if c == "ft8" and label_mode:
                ft8_ok = any(dd.text == meta[0]["msg"] for dd in r.decodes)
            rows.append(dict(true=c, pred=r.label, snr=snr, total=r.timings["total"], timings=r.timings,
                             ft8_ok=ft8_ok, n_dec=len(r.decodes), errors=r.errors))
        nlog = p.db._conn().execute("select count(*) from windows").fetchone()[0]
        nexp = p.db._conn().execute("select count(*) from explanations where ok=1").fetchone()[0]
        ndec = p.db._conn().execute("select count(*) from decodes").fetchone()[0]
        nfreq = p.db._conn().execute("select count(*) from windows where freq_hz is not null").fetchone()[0]
    srv.shutdown()
    stage = {k: timing([r["timings"][k] for r in rows if k in r["timings"]]) for k in
             ["spectrogram", "classify", "occupancy", "jt9", "whisper", "db", "llm", "total"]}
    ft8 = [r for r in rows if r["ft8_ok"] is not None]
    leaked = sum(any(w in pr for w in ("CQ ", "RR73", "seg0")) for pr in prompts)
    return dict(runs=n, label_mode=label_mode, crashed=len(errors), crash_examples=errors[:3],
                logged_windows=nlog, explanations_ok=nexp, decode_rows_stored=ndec,
                windows_with_freq=nfreq, prompts_containing_message_text=leaked,
                decoders_invoked=sum(any(k in r["timings"] for k in ("jt9", "whisper", "fldigi")) for r in rows),
                label_acc=sum(r["true"] == r["pred"] for r in rows) / max(1, len(rows)),
                ft8_end_to_end_decode=sum(r["ft8_ok"] for r in ft8) / max(1, len(ft8)), n_ft8=len(ft8),
                stage_time=stage, over_15s=sum(r["total"] > 15 for r in rows),
                decoder_errors=[e for r in rows for e in r["errors"]][:5],
                mocked="Ollama server mocked" + ("; whisper model mocked; fldigi not attached" if label_mode else ""))


def t_end_to_end_label(n, seed):
    return t_end_to_end(n, seed, label_mode=True)


def t_batch2_occupancy(n, seed):
    """Frequency/bandwidth estimates for the batch-2 modes (ID-only path)."""
    rng = np.random.default_rng(seed + 202)
    centre = {"ft4": lambda m: [mm["f0"] + 1.5 * 12000 / 576 for mm in m], "js8": lambda m: m["f0"] + 3.5 * 6.25,
              "wspr": lambda m: m["f0"], "jt9": lambda m: m["f0"] + 4 * 12000 / 6912}
    out = {}
    for c in synth.CLASSES[6:]:
        ferr, bws, miss = [], [], 0
        for it in range(n):
            snr = float(rng.uniform(-20, 15))
            x, meta = synth.generate(c, rng, snr)
            fc, bw, _ = features.occupancy_for(c, x)
            if fc is None:
                miss += 1
                continue
            if c in centre:
                tr = centre[c](meta)
                # a window can hold two FT4 transmissions; score against the nearer one
                ferr.append(min(abs(fc - t) for t in np.atleast_1d(tr)))
            bws.append(bw)
        out[c] = dict(n=n, no_signal_found=miss, freq_abs_err_hz=timing(ferr),
                      within_25hz=(sum(e <= 25 for e in ferr) / len(ferr)) if ferr else None,
                      bw_hz=dict(p10=pct(bws, 10), p50=pct(bws, 50), p90=pct(bws, 90)) if bws else None)
    return out


def t_tiebreak(n, seed):
    """13-class classifier with and without the RF tie-breaker (bandplan.py).
    Dial model: a planned mode is heard on one of its listed dials 80% of the time,
    else anywhere 1.8-30 MHz; unplanned modes (CW, RTTY, PSK31, SSB, noise) are put on a
    planned mode's dial 30% of the time (e.g. CW next to FT8) to test false penalties."""
    from sigint import bandplan
    from sigint.model import Classifier
    clf = Classifier(MODEL)
    C = synth.CLASSES[:clf.model.fc.out_features]
    rng = np.random.default_rng(seed + 303)
    planned = list(bandplan.DIALS_MHZ)
    rows = []
    for c in C:
        for it in range(n):
            snr = float(rng.uniform(-20, 15))
            x, _ = synth.generate(c, rng, snr)
            lab0, p0, probs = clf.predict(clf.featurize(x))
            fc, _, _ = features.occupancy_for(lab0, x)
            if c in bandplan.DIALS_MHZ and rng.random() < 0.8:
                dial = float(rng.choice(bandplan.DIALS_MHZ[c])) * 1e6
            elif c not in bandplan.DIALS_MHZ and rng.random() < 0.3:
                dial = float(rng.choice(bandplan.DIALS_MHZ[str(rng.choice(planned))])) * 1e6
            else:
                dial = float(rng.uniform(1.8e6, 30e6))
            lab1, p1, _ = bandplan.reweight(probs, C, dial, fc)
            rows.append(dict(true=c, before=lab0, after=lab1, snr=snr))
    per = {c: dict(before=sum(r["before"] == c for r in rows if r["true"] == c) / n,
                   after=sum(r["after"] == c for r in rows if r["true"] == c) / n) for c in C}
    return dict(runs=len(rows), acc_before=sum(r["true"] == r["before"] for r in rows) / len(rows),
                acc_after=sum(r["true"] == r["after"] for r in rows) / len(rows),
                fixed=sum(r["true"] == r["after"] != r["before"] for r in rows),
                broken=sum(r["true"] == r["before"] != r["after"] for r in rows), per_class=per,
                caveat="dials drawn from the same lists the tie-breaker uses: an upper bound for band-plan-following operators")


def t_oc_check(n, seed):
    """Same windows as t_classifier (same rng), plus the Olivia/Contestia trial-decode check
    (sigint/oc_check.py) on every window the classifier calls Olivia or Contestia.
    Decoded text is never kept; only the decision is recorded."""
    from sigint import oc_check
    from sigint.model import Classifier
    from sigint.fldigi_client import FldigiClient
    clf = Classifier(MODEL); cl = FldigiClient()
    if not cl.ping():
        return dict(error="fldigi not reachable")
    rng = np.random.default_rng(seed + 5_000_000)
    C = synth.CLASSES[:clf.model.fc.out_features]
    rows, t_dec = [], []
    for c in C:
        for k in range(n):
            snr = float(rng.uniform(-20, 15))
            x, _ = synth.generate(c, rng, snr)
            lab, p, _ = clf.predict(clf.featurize(x))
            after, fam = lab, None
            if lab in oc_check.FAMILIES:
                fc, bw, _ = features.occupancy_for(lab, x)
                t = time.perf_counter()
                fam, _ = oc_check.decide(cl, x, fc, bw)
                t_dec.append(time.perf_counter() - t)
                after = fam or lab
            rows.append(dict(true=c, before=lab, after=after, check=fam, snr=snr))
    def acc(rs, key):
        return sum(r[key] == r["true"] for r in rs) / max(1, len(rs))
    hi = [r for r in rows if r["snr"] >= -10]
    errs = {}
    for r in hi:
        if r["after"] != r["true"]:
            kk = f'{r["true"]}->{r["after"]}'
            errs[kk] = errs.get(kk, 0) + 1
    return dict(runs=len(rows), acc_before=acc(rows, "before"), acc_after=acc(rows, "after"),
                acc_snr_ge_m10_before=acc(hi, "before"), acc_snr_ge_m10_after=acc(hi, "after"),
                n_snr_ge_m10=len(hi), checks_run=len(t_dec),
                check_decided=sum(r["check"] is not None for r in rows),
                fixed=sum(r["after"] == r["true"] != r["before"] for r in rows),
                broken=sum(r["before"] == r["true"] != r["after"] for r in rows),
                errors_snr_ge_m10_after=dict(sorted(errs.items(), key=lambda kv: -kv[1])),
                per_class_after={c: acc([r for r in rows if r["true"] == c], "after") for c in C},
                check_time=timing(t_dec), text_stored=False)


def t_fam_check(n, seed):
    """Same windows as t_classifier (same rng), plus both fldigi trial-decode checks:
    Olivia/Contestia (sigint/oc_check.py) and MFSK/THOR (sigint/mt_check.py), each run only
    on windows the classifier puts in that family. Decoded text is never kept."""
    from sigint import oc_check, mt_check
    from sigint.model import Classifier
    from sigint.fldigi_client import FldigiClient
    clf = Classifier(MODEL); cl = FldigiClient()
    if not cl.ping():
        return dict(error="fldigi not reachable")
    rng = np.random.default_rng(seed + 5_000_000)
    C = synth.CLASSES[:clf.model.fc.out_features]
    rows, t_oc, t_mt = [], [], []
    # per-window checkpoint (decisions only, never text) so a container restart can resume
    ck = f"results/fam_check_rows_seed{seed}.json"
    done = {(r["true"], r["k"]): r for r in (json.load(open(ck)) if os.path.exists(ck) else [])}
    for c in C:
        for k in range(n):
            snr = float(rng.uniform(-20, 15))
            x, _ = synth.generate(c, rng, snr)
            if (c, k) in done:
                rows.append(done[(c, k)]); continue
            lab, p, _ = clf.predict(clf.featurize(x))
            oc = mt = None
            if lab in oc_check.FAMILIES:
                fc, bw, _ = features.occupancy_for(lab, x)
                t = time.perf_counter(); oc, _ = oc_check.decide(cl, x, fc, bw); t_oc.append(time.perf_counter() - t)
            elif lab in mt_check.FAMILIES:
                fc, bw, _ = features.occupancy_for(lab, x)
                t = time.perf_counter(); mt, _ = mt_check.decide(cl, x, fc, bw); t_mt.append(time.perf_counter() - t)
            rows.append(dict(true=c, k=k, before=lab, oc_only=oc or lab, after=oc or mt or lab,
                             oc=oc, mt=mt, snr=snr))
            if oc is not None or mt is not None or lab in oc_check.FAMILIES + mt_check.FAMILIES:
                json.dump(rows, open(ck, "w"))
    def acc(rs, key):
        return sum(r[key] == r["true"] for r in rs) / max(1, len(rs))
    hi = [r for r in rows if r["snr"] >= -10]
    errs = {}
    for r in hi:
        if r["after"] != r["true"]:
            kk = f'{r["true"]}->{r["after"]}'
            errs[kk] = errs.get(kk, 0) + 1
    mtr = [r for r in rows if r["mt"] is not None or r["before"] in mt_check.FAMILIES]
    return dict(runs=len(rows), n_snr_ge_m10=len(hi),
                acc_no_check=acc(rows, "before"), acc_oc_only=acc(rows, "oc_only"), acc_both=acc(rows, "after"),
                acc_snr_ge_m10_no_check=acc(hi, "before"), acc_snr_ge_m10_oc_only=acc(hi, "oc_only"),
                acc_snr_ge_m10_both=acc(hi, "after"),
                mt_checks_run=len(t_mt), mt_decided=sum(r["mt"] is not None for r in rows),
                mt_fixed=sum(r["after"] == r["true"] != r["oc_only"] for r in mtr),
                mt_broken=sum(r["oc_only"] == r["true"] != r["after"] for r in mtr),
                mt_fixed_snr_ge_m10=sum(r["after"] == r["true"] != r["oc_only"] for r in mtr if r["snr"] >= -10),
                mt_broken_snr_ge_m10=sum(r["oc_only"] == r["true"] != r["after"] for r in mtr if r["snr"] >= -10),
                errors_snr_ge_m10_after=dict(sorted(errs.items(), key=lambda kv: -kv[1])),
                per_class_after={c: acc([r for r in rows if r["true"] == c], "after") for c in C},
                oc_check_time=timing(t_oc), mt_check_time=timing(t_mt), text_stored=False)


def t_acf_check(n, seed):
    """Classifier alone vs classifier + periodicity check (sigint/acf.py) on every class.
    Seeds differ from stress/tune_acf.py, where the thresholds were set."""
    from sigint import acf
    from sigint.model import Classifier
    clf = Classifier(MODEL)
    C = synth.CLASSES[:clf.model.fc.out_features]
    rng = np.random.default_rng(seed + 808)
    rows, t_chk = [], []
    for c in C:
        for it in range(n):
            snr = float(rng.uniform(-20, 15))
            x, _ = synth.generate(c, rng, snr)
            lab0, p0, probs = clf.predict(clf.featurize(x))
            fc, _, _ = features.occupancy_for(lab0, x)
            t = time.perf_counter()
            lab1, _, _, chk = acf.reweight(lab0, probs, C, x, fc)
            t_chk.append(time.perf_counter() - t)
            rows.append(dict(true=c, before=lab0, after=lab1, chk=chk, snr=snr))
    per = {c: dict(before=sum(r["before"] == c for r in rows if r["true"] == c) / n,
                   after=sum(r["after"] == c for r in rows if r["true"] == c) / n)
           for c in C if c in acf.WIDE_MIL}
    return dict(runs=len(rows), acc_before=sum(r["true"] == r["before"] for r in rows) / len(rows),
                acc_after=sum(r["true"] == r["after"] for r in rows) / len(rows),
                fixed=sum(r["true"] == r["after"] != r["before"] for r in rows),
                broken=sum(r["true"] == r["before"] != r["after"] for r in rows),
                checks_run=sum(r["before"] in acf.WIDE_MIL for r in rows),
                check_named=sum(r["chk"] is not None for r in rows),
                per_class=per, check_time=timing(t_chk))


def t_batch3_occupancy(n, seed, classes=None, salt=404):
    """Centre/bandwidth for fldigi-generated modes; truth centre = spectral centroid of
    the clean (noise-free) recording after the random shift."""
    rng = np.random.default_rng(seed + salt)
    out = {}
    for c in classes or synth.CLASSES[13:21]:
        ferr, bws, miss, subs = [], [], 0, {}
        for it in range(n):
            snr = float(rng.uniform(-20, 15))
            x, meta = synth.generate(c, rng, snr)
            fc, bw, _ = features.occupancy_for(c, x)
            if fc is None:
                miss += 1
                continue
            ferr.append(abs(fc - meta.get("centre", meta.get("f0"))))
            bws.append(bw)
            subs.setdefault(meta.get("submode", c), []).append(bw)
        out[c] = dict(n=n, no_signal_found=miss, freq_abs_err_hz=timing(ferr),
                      within_25hz=(sum(e <= 25 for e in ferr) / len(ferr)) if ferr else None,
                      within_100hz=(sum(e <= 100 for e in ferr) / len(ferr)) if ferr else None,
                      bw_hz_by_submode={k: pct(v, 50) for k, v in subs.items()})
    return out


def t_batch4_occupancy(n, seed):
    """Batch 4. Truth centre: SSTV/WEFAX = nominal 1900 Hz band centre (1500-2300 Hz) plus
    mistuning, ALE = 1625 Hz (750-2500 Hz) plus mistuning, beacon = tone, SITOR-B = shift target.
    SSTV/fax energy centroid depends on picture brightness, so their centre error is not
    an accuracy figure; bandwidth is the useful number there."""
    return t_batch3_occupancy(n, seed, synth.CLASSES[21:26], salt=505)


def t_batch5_occupancy(n, seed):
    """Batch 5. Truth centre: serial PSK = 1800 Hz carrier + mistuning; 16/39-tone = mean of the
    data tones; PACTOR = midpoint of the tones (I/II) or 1500 Hz grid centre (III)."""
    return t_batch3_occupancy(n, seed, synth.CLASSES[26:], salt=606)


TESTS = dict(fam_check=t_fam_check, oc_check=t_oc_check, acf_check=t_acf_check, batch5_occupancy=t_batch5_occupancy, batch4_occupancy=t_batch4_occupancy, batch3_occupancy=t_batch3_occupancy, tiebreak=t_tiebreak, batch2_occupancy=t_batch2_occupancy, ringbuffer=t_ringbuffer, slicer=t_slicer, sqlite=t_sqlite, wsjtx_udp=t_wsjtx_udp,
             ollama_client=t_ollama_client, whisper_wrapper=t_whisper_wrapper, ft8_jt9=t_ft8_jt9,
             classifier=t_classifier, occupancy=t_occupancy, end_to_end=t_end_to_end,
             end_to_end_label=t_end_to_end_label, capture=t_capture,
             fldigi_psk31=t_fldigi_psk31, fldigi_rtty=t_fldigi_rtty,
             fldigi_psk31_est=t_fldigi_psk31_est, fldigi_rtty_est=t_fldigi_rtty_est)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("tests", nargs="*")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    for name in a.tests or list(TESTS):
        t = time.time()
        try:
            out = TESTS[name](a.n, a.seed)
        except Exception:
            out = dict(harness_error=traceback.format_exc())
        out["wall_s"] = round(time.time() - t, 1)
        with open(os.path.join(ROOT, "results", f"{name}_seed{a.seed}.json"), "w") as f:
            json.dump(out, f, indent=1, default=str)
        print(name, json.dumps({k: v for k, v in out.items() if not isinstance(v, (list, dict)) or k in ("by_snr",)}, default=str)[:600], flush=True)
