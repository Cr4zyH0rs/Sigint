"""Collect signature scores on training-split windows (seed 77, not the test seed) and pick
thresholds for sigint/signature.py that maximise accuracy at SNR >= -10 dB (ties: all SNR).
Usage: SIGINT_FEATS=mc SIGINT_FLDIGI_SPLIT=train SIGINT_MODEL=... python stress/tune_signature.py N"""
import json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sigint import synth, signature as sg
from sigint.model import Classifier

n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
rows_f = "results/signature_tune_rows.json"
clf = Classifier(os.environ["SIGINT_MODEL"])
C = synth.CLASSES[:clf.model.fc.out_features]
rng = np.random.default_rng(77)
rows = json.load(open(rows_f)) if os.path.exists(rows_f) else []
done = len(rows)
t0 = time.time()
k = 0
for c in C:
    for i in range(n):
        snr = float(rng.uniform(-20, 15))
        x, _ = synth.generate(c, rng, snr)
        k += 1
        if k <= done:
            continue
        lab, p, probs = clf.predict(clf.featurize(x))
        top = [int(j) for j in np.argsort(-probs)[:4]]
        rows.append(dict(true=c, snr=snr, top=[C[j] for j in top], ptop=[float(probs[j]) for j in top],
                         scores={m: float(f(x)) for m, f in sg.SCORES.items()}))
        if k % 200 == 0:
            json.dump(rows, open(rows_f, "w")); print(k, round(time.time() - t0), flush=True)
json.dump(rows, open(rows_f, "w"))

def apply(r, th):
    for c in r["top"]:
        if c in th and r["scores"][c] < th[c]:
            continue
        return c
    return r["top"][0]

def acc(th, lo=-10):
    rr = [r for r in rows if r["snr"] >= lo]
    return sum(apply(r, th) == r["true"] for r in rr) / len(rr)

grid = {"wwv": np.round(np.arange(0, 30.1, 0.5), 2), "dtmf": np.arange(0, 60, 2), "hamdrm": np.round(np.arange(1, 6.01, 0.1), 2)}
base = acc({})
th = {"wwv": 0.0, "dtmf": 0, "hamdrm": 1.0}
for _ in range(3):                     # coordinate ascent
    for m in grid:
        # most windows right at all SNRs, without losing any accuracy at SNR >= -10 dB
        ok = [v for v in grid[m] if acc({**th, m: float(v)}) >= base - 1e-9]
        best = max(ok, key=lambda v: (acc({**th, m: float(v)}, -99), -abs(float(v))))
        th[m] = float(best)
res = dict(thresholds=th, acc_ge_m10_without=acc({}), acc_ge_m10_with=acc(th), acc_all_without=acc({}, -99),
           acc_all_with=acc(th, -99), acc_ge_0_without=acc({}, 0), acc_ge_0_with=acc(th, 0), n=len(rows))
# pass rates of the true classes
for m in th:
    tr = [r for r in rows if r["true"] == m]
    res[f"{m}_true_pass_ge_m10"] = np.mean([r["scores"][m] >= th[m] for r in tr if r["snr"] >= -10]).item()
    res[f"{m}_true_pass_all"] = np.mean([r["scores"][m] >= th[m] for r in tr]).item()
    fp = [r for r in rows if r["top"][0] == m and r["true"] != m]
    res[f"{m}_false_labels_blocked"] = f"{sum(r['scores'][m] < th[m] for r in fp)}/{len(fp)}"
json.dump({k: v for k, v in th.items()}, open("data/signature_thresholds.json", "w"))
json.dump(res, open("results/signature_tune.json", "w"), indent=1)
print(json.dumps(res, indent=1))
