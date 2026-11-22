"""Tune sigint/acf.py thresholds on windows with seeds disjoint from run_all's tests.
Usage: python stress/tune_acf.py N -> results/tune_acf.json"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sigint import synth, acf, features as feats

CL = ["stanag4285", "mil110_serial", "mil110_16tone", "mil110_39tone", "pactor3", "ssb", "mt63", "ale"]
n = int(sys.argv[1])
rng = np.random.default_rng(77_000_000)
rows = []
for c in CL:
    for i in range(n):
        snr = float(rng.uniform(-20, 15))
        x, _ = synth.generate(c, rng, snr)
        fc, _, _ = feats.occupancy_for(c, x)
        f = acf.features(x, fc if fc and 1500 < fc < 2100 else 1800.0)
        rows.append(dict(true=c, snr=snr, **f))
json.dump(rows, open("results/tune_acf.json", "w"), indent=1)
for c in CL:
    r = [x for x in rows if x["true"] == c]
    q = lambda k: np.round(np.percentile([x[k] for x in r], [10, 50, 90]), 3).tolist()
    print(c, "s4285", q("s4285"), "m110", q("m110"), "cp39", q("cp39"))
