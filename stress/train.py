"""Train ResNet-18 on synthetic spectrograms (CPU)."""
import sys, os, time, json, numpy as np, torch, torch.nn as nn
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sigint.model import build_model
from sigint.synth import CLASSES
torch.manual_seed(0); torch.set_num_threads(4)
TAG = sys.argv[2] if len(sys.argv) > 2 else ""
OUT = sys.argv[3] if len(sys.argv) > 3 else TAG   # output name, e.g. b5e15 for a longer run on b5 data
def load(names):
    # fill one preallocated array file by file: np.concatenate held every part plus the
    # result in RAM (about 2x the dataset), too much once batch 7 was added
    ys = [np.load(n)["y"] for n in names]
    X = None; i = 0
    for n in names:
        part = np.load(n)["X"]
        if X is None:
            X = np.empty((sum(len(y) for y in ys),) + part.shape[1:], part.dtype)
        X[i:i + len(part)] = part; i += len(part); del part
    return (torch.from_numpy(X[:, None] if X.ndim == 3 else X),
            torch.from_numpy(np.concatenate(ys)).long())
if TAG == "mc":
    Xtr, ytr = load(["data/train_mc.npz"]); Xva, yva = load(["data/val_mc.npz"])
if TAG == "mc9":   # batch 9: 48 classes + the new ones
    Xtr, ytr = load([f"data/train_mc{e}.npz" for e in ("", "_b6", "_b7", "_b8", "_b9")])
    Xva, yva = load([f"data/val_mc{e}.npz" for e in ("", "_b6", "_b7", "_b8", "_b9")])
if TAG == "mc8":   # batch 8: 43 classes + the new ones
    Xtr, ytr = load(["data/train_mc.npz", "data/train_mc_b6.npz", "data/train_mc_b7.npz", "data/train_mc_b8.npz"])
    Xva, yva = load(["data/val_mc.npz", "data/val_mc_b6.npz", "data/val_mc_b7.npz", "data/val_mc_b8.npz"])
if TAG == "mc7":   # batch 7: 38 classes + the new ones
    Xtr, ytr = load(["data/train_mc.npz", "data/train_mc_b6.npz", "data/train_mc_b7.npz"])
    Xva, yva = load(["data/val_mc.npz", "data/val_mc_b6.npz", "data/val_mc_b7.npz"])
if TAG == "mc6":   # batch 6: earlier 33 classes + the new ones
    Xtr, ytr = load(["data/train_mc.npz", "data/train_mc_b6.npz"])
    Xva, yva = load(["data/val_mc.npz", "data/val_mc_b6.npz"])
extra = {"b2": ["_b2"], "b3": ["_b2", "_b3"], "b4": ["_b2", "_b3", "_b4"], "b5": ["_b2", "_b3", "_b4", "_b5"]}.get(TAG, [])
if TAG not in ("mc", "mc6", "mc7", "mc8", "mc9"):
    Xtr, ytr = load(["data/train.npz"] + [f"data/train{e}.npz" for e in extra])
    Xva, yva = load(["data/val.npz"] + [f"data/val{e}.npz" for e in extra])
N_CLASSES = int(ytr.max()) + 1
m = build_model(N_CLASSES, Xtr.shape[1])
if os.environ.get("SIGINT_INIT"):   # fine-tune from an earlier model (round 2 of the 99% push)
    sd = torch.load(os.environ["SIGINT_INIT"])
    if sd["fc.weight"].shape[0] != N_CLASSES:   # new classes: keep the old rows, new rows random
        cur = m.state_dict()
        k = sd["fc.weight"].shape[0]
        cur["fc.weight"][:k] = sd["fc.weight"]; cur["fc.bias"][:k] = sd["fc.bias"]
        sd["fc.weight"], sd["fc.bias"] = cur["fc.weight"], cur["fc.bias"]
    m.load_state_dict(sd)
opt = torch.optim.AdamW(m.parameters(), 1e-3, weight_decay=1e-4)
EPOCHS = int(sys.argv[1]) if len(sys.argv) > 1 else 8
sched = torch.optim.lr_scheduler.OneCycleLR(opt, float(os.environ.get("SIGINT_MAXLR", 2e-3)), total_steps=EPOCHS * ((len(Xtr) + 31) // 32))
lossf = nn.CrossEntropyLoss(); hist = []
# resume after a container restart: checkpoint written at the end of every epoch
CKPT = f"data/ckpt_{OUT or 'base'}_{EPOCHS}.pt"
start = 0
if os.path.exists(CKPT):
    ck = torch.load(CKPT, weights_only=False)
    m.load_state_dict(ck["model"]); opt.load_state_dict(ck["opt"]); sched.load_state_dict(ck["sched"])
    hist, start = ck["hist"], ck["epoch"] + 1
    torch.set_rng_state(ck["rng"]); np.random.set_state(ck["np_rng"])
    print("resumed at epoch", start, flush=True)
for ep in range(start, EPOCHS):
    m.train(); perm = torch.randperm(len(Xtr)); t = time.time(); tl = 0
    for i in range(0, len(Xtr), 32):
        idx = perm[i:i + 32]; xb = Xtr[idx].float()
        # augmentation: random circular shift in frequency (signal can be anywhere) and time
        xb = torch.roll(xb, shifts=(int(np.random.randint(-20, 21)), int(np.random.randint(-60, 61))), dims=(2, 3))
        opt.zero_grad(); loss = lossf(m(xb), ytr[idx]); loss.backward(); opt.step(); sched.step(); tl += loss.item() * len(idx)
    m.eval()
    with torch.no_grad(): pred = torch.cat([m(Xva[i:i + 64].float()).argmax(1) for i in range(0, len(Xva), 64)])
    acc = (pred == yva).float().mean().item()
    hist.append(dict(epoch=ep, loss=tl / len(Xtr), val_acc=acc, sec=time.time() - t))
    print(hist[-1], flush=True)
    torch.save(dict(model=m.state_dict(), opt=opt.state_dict(), sched=sched.state_dict(), hist=hist,
                    epoch=ep, rng=torch.get_rng_state(), np_rng=np.random.get_state()), CKPT + ".tmp")
    os.replace(CKPT + ".tmp", CKPT)
torch.save(m.state_dict(), f"data/resnet18_modes{'_' + OUT if OUT else ''}.pt")
json.dump(hist, open(f"results/train_history{'_' + OUT if OUT else ''}.json", "w"), indent=1)
