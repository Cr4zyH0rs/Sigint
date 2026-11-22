"""Collect trial-decode features (scores/counts only, never text) for Olivia/Contestia windows.
Usage: python stress/tune_oc.py N SEED OUT.json"""
import json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sigint import synth, features, oc_check
from sigint.fldigi_client import FldigiClient
n, seed, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
cl = FldigiClient(); rng = np.random.default_rng(seed); rows = []
for i in range(n):
    c = ["olivia", "contestia"][i % 2]
    snr = float(rng.uniform(-10, 15))
    x, m = synth.generate(c, rng, snr)
    fc, bw, _ = features.occupancy_for(c, x)
    fam, sc = oc_check.decide(cl, x, fc, bw)
    rows.append(dict(true=c, sub=m["submode"], snr=snr, bw=bw, fam=fam, scores=sc))
    json.dump(rows, open(out, "w"), indent=1)
    print(i, c, fam, flush=True)
