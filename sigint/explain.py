"""Ask a local LLM, via Ollama's REST API, to explain a window's results.

Endpoint: POST /api/generate with {"model", "prompt", "stream": false}; the reply
is one JSON object whose "response" field holds the text
(https://github.com/ollama/ollama/blob/main/docs/api.md#generate-a-completion).
Default server address is http://localhost:11434.
"""
from __future__ import annotations

import json
import time

import requests

PROMPT = """You are helping an amateur radio operator. In one short paragraph, explain
what was heard in this 15-second window. Do not invent callsigns or text that are
not in the data.

Window start (UTC): {utc}
Classifier: {label} (confidence {conf:.2f})
Decodes:
{decodes}
"""


PROMPT_ID = """You are helping an amateur radio operator. In two or three sentences, say
what kind of signal this probably is, what it is typically used for, and how sure
the classifier is. Use only the data below; do not guess at message content.

Window start (UTC): {utc}
Classifier: {label} (confidence {conf:.2f})
Audio offset: {freq}  Occupied bandwidth: {bw}  Peak over noise floor: {snr}
"""


def build_prompt_id(utc_iso, label, conf, freq_hz, bw_hz, snr_db) -> str:
    fmt = lambda v, u: "unknown" if v is None else f"{v:.0f} {u}"
    return PROMPT_ID.format(utc=utc_iso, label=label, conf=conf, freq=fmt(freq_hz, "Hz"),
                            bw=fmt(bw_hz, "Hz"), snr=fmt(snr_db, "dB"))


def build_prompt(utc_iso, label, conf, decodes) -> str:
    lines = "\n".join(f"- [{d.mode}] {d.text}" + (f" (SNR {d.snr:+.0f} dB)" if d.snr is not None else "")
                      for d in decodes) or "- (none)"
    return PROMPT.format(utc=utc_iso, label=label, conf=conf, decodes=lines)


class Explainer:
    def __init__(self, model="llama3.2:3b", url="http://localhost:11434", timeout=60.0,
                 retries=2, backoff=0.5, session=None):
        self.model, self.url, self.timeout = model, url.rstrip("/"), timeout
        self.retries, self.backoff = retries, backoff
        self.session = session or requests.Session()

    def explain(self, prompt: str) -> tuple[bool, str]:
        """Return (ok, text). Never raises: the pipeline must keep running if the LLM is down."""
        last = ""
        for attempt in range(self.retries + 1):
            try:
                r = self.session.post(f"{self.url}/api/generate",
                                      json={"model": self.model, "prompt": prompt, "stream": False,
                                            "options": {"temperature": 0.2}},
                                      timeout=self.timeout)
                if r.status_code != 200:
                    last = f"HTTP {r.status_code}"
                else:
                    body = r.json()
                    text = body.get("response")
                    if isinstance(text, str) and text.strip():
                        return True, text.strip()
                    last = "empty response"
            except requests.Timeout:
                last = "timeout"
            except (requests.ConnectionError, json.JSONDecodeError, ValueError) as e:
                last = type(e).__name__
            if attempt < self.retries:
                time.sleep(self.backoff * (2 ** attempt))
        return False, f"LLM unavailable ({last})"
