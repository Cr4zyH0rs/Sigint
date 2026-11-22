"""SQLite log (Python stdlib sqlite3, https://docs.python.org/3/library/sqlite3.html).

WAL journal mode lets readers (the LLM step, a dashboard) run while the
pipeline writes (https://www.sqlite.org/wal.html). busy_timeout makes a writer
wait instead of failing with "database is locked" (https://www.sqlite.org/c3ref/busy_timeout.html).
"""
from __future__ import annotations

import json
import sqlite3
import threading

SCHEMA = """
CREATE TABLE IF NOT EXISTS windows(
  id INTEGER PRIMARY KEY,
  utc_start REAL NOT NULL,
  label TEXT NOT NULL,
  confidence REAL,
  probs TEXT,
  freq_hz REAL,      -- audio offset of signal centre (add dial freq for RF)
  bw_hz REAL,        -- estimated occupied bandwidth
  snr_db REAL,       -- spectral peak over median floor (rough)
  dial_hz REAL       -- rig dial frequency if known (CAT), else NULL
);
CREATE TABLE IF NOT EXISTS decodes(
  id INTEGER PRIMARY KEY,
  window_id INTEGER NOT NULL REFERENCES windows(id),
  mode TEXT, text TEXT, snr REAL, dt REAL, freq REAL
);
CREATE TABLE IF NOT EXISTS explanations(
  id INTEGER PRIMARY KEY,
  window_id INTEGER NOT NULL REFERENCES windows(id),
  model TEXT, text TEXT, ok INTEGER
);
CREATE INDEX IF NOT EXISTS ix_windows_utc ON windows(utc_start);
"""


class Log:
    def __init__(self, path: str):
        self.path = path
        self._local = threading.local()
        c = self._conn()
        c.executescript(SCHEMA)
        c.commit()

    def _conn(self) -> sqlite3.Connection:
        c = getattr(self._local, "c", None)
        if c is None:
            c = sqlite3.connect(self.path, timeout=30.0)
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA busy_timeout=30000")
            c.execute("PRAGMA foreign_keys=ON")
            self._local.c = c
        return c

    def log_window(self, utc_start, label, confidence, probs, decodes=(), freq_hz=None,
                   bw_hz=None, snr_db=None, dial_hz=None) -> int:
        c = self._conn()
        with c:  # one transaction per window: all-or-nothing
            cur = c.execute("INSERT INTO windows(utc_start,label,confidence,probs,freq_hz,bw_hz,"
                            "snr_db,dial_hz) VALUES(?,?,?,?,?,?,?,?)",
                            (float(utc_start), label, float(confidence),
                             json.dumps([float(p) for p in probs]), freq_hz, bw_hz, snr_db,
                             dial_hz))
            wid = cur.lastrowid
            if decodes:  # only in the opt-in labeling mode
                c.executemany("INSERT INTO decodes(window_id,mode,text,snr,dt,freq) VALUES(?,?,?,?,?,?)",
                              [(wid, d.mode, d.text, d.snr, d.dt, d.freq) for d in decodes])
        return wid

    def log_explanation(self, window_id, model, text, ok):
        c = self._conn()
        with c:
            c.execute("INSERT INTO explanations(window_id,model,text,ok) VALUES(?,?,?,?)",
                      (window_id, model, text, int(ok)))

    def recent(self, n=20):
        c = self._conn()
        rows = c.execute("""SELECT w.id, w.utc_start, w.label, w.confidence,
                                   group_concat(d.text, ' | ')
                            FROM windows w LEFT JOIN decodes d ON d.window_id=w.id
                            GROUP BY w.id ORDER BY w.id DESC LIMIT ?""", (n,)).fetchall()
        return rows

    def close(self):
        c = getattr(self._local, "c", None)
        if c is not None:
            c.close()
            self._local.c = None
