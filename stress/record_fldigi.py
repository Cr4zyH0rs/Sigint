"""Record real fldigi transmissions (fldigi's own modulators) through the PulseAudio
null sink 'radio'. fldigi transmits into the sink; parecord captures radio.monitor.

Usage: python stress/record_fldigi.py OUTDIR SECONDS_PER_MODE SEED [CLASS,CLASS...]
"""
import os, sys, time, subprocess, xmlrpc.client, numpy as np
os.environ.setdefault("XDG_RUNTIME_DIR", "/tmp/xdg")
os.environ.setdefault("PULSE_SERVER", "unix:/tmp/xdg/pulse/native")

# class -> fldigi modem names (sub-modes rotated within a take)
MODES = {
    "olivia": ["OLIVIA-8/250", "OLIVIA-16/500", "OLIVIA-32/1K", "OLIVIA-8/500"],
    "contestia": ["Cont-8/250", "Cont-16/500", "Cont-32/1K", "Cont-8/500"],
    "mfsk": ["MFSK16", "MFSK32", "MFSK8", "MFSK64"],
    "thor": ["THOR16", "THOR22", "THOR11", "THOR8"],
    "dominoex": ["DOMX11", "DOMX22", "DOMX16", "DOMEX8"],
    "mt63": ["MT63-1KL", "MT63-1KS", "MT63-500L", "MT63-2KL"],
    "hell": ["FELDHELL", "HELL80", "HELLX5", "SLOWHELL"],
    "throb": ["THROB2", "THROB1", "THROB4"],
    # batch 4: NAVTEX is SITOR-B (100 Bd FEC, 170 Hz shift) on 518/490/4209.5 kHz
    "sitorb": ["SITORB", "NAVTEX"],
    # batch 6: FSQ (speed as set in fldigi's FSQ config) and 8PSK (https://www.sigidwiki.com/wiki/FSQ ,
    # https://www.sigidwiki.com/wiki/8PSK : 0.125-1.2 kHz)
    "fsq": ["FSQ"],
    "psk8": ["8PSK125", "8PSK250", "8PSK500", "8PSK1000"],
}
WORDS = "cq de test name qth rig ant wx tnx fer qso 73 pse k hello the is sunny rst 599 op".split()


def main(outdir, secs, seed, only=None):
    rng = np.random.default_rng(seed)
    s = xmlrpc.client.ServerProxy("http://127.0.0.1:7362/")
    os.makedirs(outdir, exist_ok=True)
    for cls, names in MODES.items():
        if only and cls not in only:
            continue
        for name in names:
            dur = secs / len(names)
            fc = int(rng.uniform(800, 2000))
            path = os.path.join(outdir, f"{cls}__{name.replace('/', '_')}__{fc}.wav")
            s.main.abort(); time.sleep(0.5)
            s.modem.set_by_name(name); s.modem.set_carrier(fc)
            s.text.clear_tx()
            # plenty of text so the transmitter never idles inside the take
            txt = " ".join(rng.choice(WORDS, 400))
            s.text.add_tx(txt)
            rec = subprocess.Popen(["parecord", "--device=radio.monitor", "--rate=12000",
                                    "--channels=1", "--format=s16le", "--file-format=wav", path])
            time.sleep(0.3)
            s.main.tx()
            time.sleep(dur + 2)
            s.main.abort(); s.text.clear_tx()
            rec.terminate(); rec.wait()
            print(cls, name, fc, os.path.getsize(path), flush=True)
            time.sleep(1)


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]), int(sys.argv[3]),
         sys.argv[4].split(",") if len(sys.argv) > 4 else None)
