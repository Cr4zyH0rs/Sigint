"""Generate synthetic spectrogram datasets: train (seeded 0..), test (seeded 10**6..)."""
import sys, os, time, numpy as np
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sigint import synth, features

MC = os.environ.get("SIGINT_FEATS") == "mc"

def one(args):
    label, seed, snr = args
    rng = np.random.default_rng(seed)
    x, meta = synth.generate(label, rng, snr)
    return features.spectrogram_mc(x).astype(np.float16) if MC else features.spectrogram(x)

def build(n_per_class, seed0, snr_lo, snr_hi, out, classes=None):
    jobs, ys, snrs = [], [], []
    rng = np.random.default_rng(seed0)
    for c in (classes or synth.CLASSES):
        ci = synth.CLASSES.index(c)
        for k in range(n_per_class):
            snr = float(rng.uniform(snr_lo, snr_hi))
            jobs.append((c, seed0 + ci * 100000 + k, snr)); ys.append(ci); snrs.append(snr)
    t = time.time()
    # fill a preallocated array (a list + np.stack needed 2x the dataset in RAM and was
    # OOM-killed once the fldigi takes grew 5x)
    X = None
    with Pool(4) as p:
        for i, s in enumerate(p.imap(one, jobs, chunksize=8)):
            if X is None:
                X = np.empty((len(jobs),) + s.shape, s.dtype)
            X[i] = s
    np.savez_compressed(out, X=X, y=np.array(ys), snr=np.array(snrs))
    print(out, X.shape, f"{time.time()-t:.1f}s", flush=True)

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    if len(sys.argv) > 2 and sys.argv[2] == "mc":
        # all classes, 3-channel features (SIGINT_FEATS=mc), float16, SNR -16..+15 dB
        os.environ["SIGINT_FLDIGI_SPLIT"] = "train"
        build(n, 9, -16, 15, "data/train_mc.npz")
        build(100, 9 * 10**7, -16, 15, "data/val_mc.npz")
    elif len(sys.argv) > 2 and sys.argv[2] == "mc9":
        os.environ["SIGINT_FLDIGI_SPLIT"] = "train"
        new = synth.CLASSES[48:]
        build(n, 11, -16, 15, "data/train_mc_b9.npz", new)
        build(100, 11 * 10**7, -16, 15, "data/val_mc_b9.npz", new)
    elif len(sys.argv) > 2 and sys.argv[2] == "mc8":
        os.environ["SIGINT_FLDIGI_SPLIT"] = "train"
        new = synth.CLASSES[43:]
        build(n, 10, -16, 15, "data/train_mc_b8.npz", new)
        build(100, 10 * 10**7, -16, 15, "data/val_mc_b8.npz", new)
    elif len(sys.argv) > 2 and sys.argv[2] == "mc7":
        os.environ["SIGINT_FLDIGI_SPLIT"] = "train"
        new = synth.CLASSES[38:]
        build(n, 9, -16, 15, "data/train_mc_b7.npz", new)
        build(100, 9 * 10**7, -16, 15, "data/val_mc_b7.npz", new)
    elif len(sys.argv) > 2 and sys.argv[2] == "mc6":
        # batch 6 classes only, 3-channel; appended to train_mc/val_mc at training time
        os.environ["SIGINT_FLDIGI_SPLIT"] = "train"
        new = synth.CLASSES[33:]
        build(n, 9, -16, 15, "data/train_mc_b6.npz", new)
        build(100, 9 * 10**7, -16, 15, "data/val_mc_b6.npz", new)
    elif len(sys.argv) > 2 and sys.argv[2] == "batch5":
        new = synth.CLASSES[26:]
        build(n, 5, -20, 15, "data/train_b5.npz", new)
        build(100, 5 * 10**7, -20, 15, "data/val_b5.npz", new)
    elif len(sys.argv) > 2 and sys.argv[2] == "batch4":
        new = synth.CLASSES[21:26]
        os.environ["SIGINT_FLDIGI_SPLIT"] = "train"
        build(n, 4, -20, 15, "data/train_b4.npz", new)
        build(100, 4 * 10**7, -20, 15, "data/val_b4.npz", new)
    elif len(sys.argv) > 2 and sys.argv[2] == "batch3":
        new = synth.CLASSES[13:21]
        os.environ["SIGINT_FLDIGI_SPLIT"] = "train"
        build(n, 3, -20, 15, "data/train_b3.npz", new)
        build(100, 3 * 10**7, -20, 15, "data/val_b3.npz", new)
    elif len(sys.argv) > 2 and sys.argv[2] == "batch2":
        new = synth.CLASSES[6:]
        build(n, 2, -20, 15, "data/train_b2.npz", new)
        build(100, 2 * 10**7, -20, 15, "data/val_b2.npz", new)
    else:
        build(n, 1, -20, 15, "data/train.npz")
        build(100, 10**7, -20, 15, "data/val.npz")
