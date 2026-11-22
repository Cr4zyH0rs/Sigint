"""Monthly sigidwiki change monitor (user request 2026-11-22).

Fetches every page in [[Category:Signal]] from sigidwiki's Semantic MediaWiki `ask` API
(https://www.sigidwiki.com/api.php?action=ask, the same source as docs/ic7300_sigidwiki_signals.md)
with the Frequencies, Bandwidth, Modulation, Mode, ACF and Modification date properties, then
compares them with the last snapshot (data/sigidwiki_snapshot.json).

It reports:
  - signals added or removed,
  - changed listed parameters (frequency, bandwidth, modulation, mode, ACF),
  - pages edited since the last snapshot, with the ones this project models flagged (their prose
    may hold spec changes that the structured properties don't show),
  - whether each new or changed signal is receivable by the IC-7300 (0.03-74.8 MHz, <= 15 kHz,
    same rule as docs/ic7300_sigidwiki_signals.md).

It only reads sigidwiki; it never edits code. Usage:
  python stress/sigidwiki_monitor.py            # compare, write docs/sigidwiki_changes/YYYY-MM-DD.md
  python stress/sigidwiki_monitor.py --save     # ... and replace the snapshot
Needs network access to www.sigidwiki.com (cloud environment "sigint").
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAP = os.path.join(ROOT, "data", "sigidwiki_snapshot.json")
OUTDIR = os.path.join(ROOT, "docs", "sigidwiki_changes")
API = "https://www.sigidwiki.com/api.php"
PROPS = ["Frequencies", "Bandwidth", "Modulation", "Mode", "ACF", "Modification date"]
FIELDS = {"Frequencies": "freq_hz", "Bandwidth": "bw_hz", "Modulation": "modulation",
          "Mode": "mode", "ACF": "acf"}

# classifier label -> sigidwiki page(s) its generator or recordings were built from
MODELLED = {
    "ft8": ["FT8"], "cw": ["Morse Code (CW)"], "rtty": ["Radio Teletype (RTTY)"],
    "psk31": ["Phase Shift Keying (PSK)"], "ssb": ["Single Sideband Voice"],
    "ft4": ["FT4"], "js8": ["JS8"], "wspr": ["WSPR"], "jt65": ["JT65"], "jt9": ["JT9"],
    "fst4": ["FST4", "FST4W"], "q65": ["Q65"], "olivia": ["Olivia"], "contestia": ["Contestia"],
    "mfsk": ["Multi Frequency Shift Keying (MFSK)"], "thor": ["THOR"], "dominoex": ["DominoEX"],
    "mt63": ["MT63"], "hell": ["Hellschreiber"], "throb": ["THROB"],
    "sstv": ["Slow-Scan Television (SSTV)"], "wefax": ["WEFAX"],
    "ale": ["Automatic Link Establishment (2G ALE)"], "cw_beacon": ["Morse Code (CW)"],
    "sitorb": ["SITOR-B"], "stanag4285": ["STANAG 4285"],
    "mil110_serial": ["MIL-STD-188-110 Serial"],
    "mil110_16tone": ["MIL-STD-188-110 Appendix A 16-Tone"],
    "mil110_39tone": ["MIL-STD-188-110 Appendix B 39-Tone", "STANAG 4197"],
    "pactor1": ["PACTOR I"], "pactor2": ["PACTOR II"], "pactor3": ["PACTOR III"],
    "psk8": ["8PSK"], "fsq": ["FSQ"], "packet": ["PACKET"], "sitora": ["SITOR-A"],
    "ndb": ["Non-Directional Beacon (NDB)"], "selcal": ["ICAO Selcal"],
    "dsc": ["GMDSS Digital Selective Calling"], "ccir493": ["CCIR 493-4 Selcall"],
    "hfdl": ["High Frequency Data Link (HFDL)"], "msk144": ["MSK144"],
}
PAGE_TO_CLASSES: dict[str, list[str]] = {}
for _c, _ps in MODELLED.items():
    for _p in _ps:
        PAGE_TO_CLASSES.setdefault(_p, []).append(_c)


def _get(params: dict) -> dict:
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "sigint-monitor/1.0 (signal-ID research)"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))


def fetch() -> dict:
    out, offset = {}, 0
    while True:
        q = "[[Category:Signal]]" + "".join(f"|?{p}" for p in PROPS) + f"|limit=500|offset={offset}"
        r = _get(dict(action="ask", query=q, format="json"))
        for title, v in (r.get("query", {}).get("results") or {}).items():
            po = v.get("printouts", {})
            row = {"url": v.get("fullurl")}
            for p, k in FIELDS.items():
                row[k] = sorted(str(x) for x in po.get(p, []))
            md = po.get("Modification date") or []
            row["modified"] = str(md[0].get("timestamp") if md and isinstance(md[0], dict) else (md[0] if md else ""))
            out[title] = row
        nxt = r.get("query-continue-offset")
        if not nxt:
            break
        offset = nxt
        time.sleep(1)
    return out


def _num(xs):
    v = []
    for x in xs:
        try:
            v.append(float(x))
        except ValueError:
            pass
    return v


def receivable(row) -> bool:
    f, bw = _num(row.get("freq_hz", [])), _num(row.get("bw_hz", []))
    in_range = any(30e3 <= x <= 74.8e6 for x in f) or (len(f) >= 2 and min(f) <= 74.8e6 and max(f) >= 30e3)
    fits = (min(bw) <= 15000) if bw else True
    return in_range and fits


def compare(old: dict, new: dict) -> dict:
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed, edited = {}, []
    for t in sorted(set(old) & set(new)):
        d = {k: (old[t].get(k), new[t].get(k)) for k in FIELDS.values() if old[t].get(k) != new[t].get(k)}
        if d:
            changed[t] = d
        if new[t].get("modified") and new[t].get("modified") != old[t].get("modified"):
            edited.append(t)
    return dict(added=added, removed=removed, changed=changed, edited=edited)


def report(diff: dict, new: dict, old_date: str, today: str) -> str:
    L = [f"# sigidwiki changes, {old_date} to {today}", "",
         f"Source: sigidwiki Semantic MediaWiki ask API, [[Category:Signal]] ({len(new)} signals today).", ""]
    def link(t):
        u = new.get(t, {}).get("url") or "https://www.sigidwiki.com/wiki/" + urllib.parse.quote(t.replace(" ", "_"))
        tag = f" — **modelled: {', '.join(PAGE_TO_CLASSES[t])}**" if t in PAGE_TO_CLASSES else ""
        rx = "" if t not in new else (" (IC-7300 can receive)" if receivable(new[t]) else " (outside IC-7300 range)")
        return f"[{t}]({u}){rx}{tag}"
    L += [f"## New signals ({len(diff['added'])})", ""] + [f"- {link(t)}" for t in diff["added"]] + [""]
    L += [f"## Removed signals ({len(diff['removed'])})", ""] + [f"- {t}" for t in diff["removed"]] + [""]
    L += [f"## Changed listed parameters ({len(diff['changed'])})", ""]
    for t, d in diff["changed"].items():
        L.append(f"- {link(t)}")
        for k, (a, b) in d.items():
            L.append(f"  - {k}: {a} → {b}")
    L += ["", f"## Pages edited ({len(diff['edited'])}; modelled ones first)", ""]
    ed = sorted(diff["edited"], key=lambda t: (t not in PAGE_TO_CLASSES, t))
    L += [f"- {link(t)}" for t in ed] + [""]
    return "\n".join(L)


def main():
    save = "--save" in sys.argv
    new = fetch()
    today = dt.date.today().isoformat()
    if os.path.exists(SNAP):
        snap = json.load(open(SNAP))
        old, old_date = snap["signals"], snap["date"]
    else:
        old, old_date = {}, "(no snapshot)"
    diff = compare(old, new) if old else dict(added=[], removed=[], changed={}, edited=[])
    os.makedirs(OUTDIR, exist_ok=True)
    path = os.path.join(OUTDIR, f"{today}.md")
    if old:
        open(path, "w").write(report(diff, new, old_date, today))
    touched = (set(diff["changed"]) | set(diff["edited"])) & set(PAGE_TO_CLASSES)
    summary = dict(date=today, since=old_date, n_signals=len(new), added=len(diff["added"]),
                   removed=len(diff["removed"]), changed=len(diff["changed"]), edited=len(diff["edited"]),
                   modelled_pages_touched=sorted(touched),
                   new_receivable=[t for t in diff["added"] if receivable(new[t])],
                   report=os.path.relpath(path, ROOT) if old else None)
    if save or not old:
        os.makedirs(os.path.dirname(SNAP), exist_ok=True)
        json.dump(dict(date=today, source=API, signals=new), open(SNAP, "w"), indent=1, sort_keys=True)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
