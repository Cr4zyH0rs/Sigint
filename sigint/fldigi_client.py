"""Thin fldigi XML-RPC client.

fldigi exposes an XML-RPC server on 127.0.0.1:7362 by default. Method names used
here (modem.set_by_name, modem.set_carrier, main.set_afc, main.set_squelch,
text.get_rx_length, text.get_rx, text.clear_rx) are listed by fldigi's own
`fldigi.list` call and documented at
http://www.w1hkj.com/FldigiHelp/xmlrpc_control_page.html
"""
from __future__ import annotations

import socket
import time
import xmlrpc.client

MODEM_NAMES = {"rtty": "RTTY", "psk31": "BPSK31"}


class _TimeoutTransport(xmlrpc.client.Transport):
    def __init__(self, timeout: float):
        super().__init__()
        self._timeout = timeout

    def make_connection(self, host):
        conn = super().make_connection(host)
        conn.timeout = self._timeout
        return conn


class FldigiClient:
    def __init__(self, host="127.0.0.1", port=7362, timeout=5.0):
        self.url = f"http://{host}:{port}/"
        self.proxy = xmlrpc.client.ServerProxy(self.url, transport=_TimeoutTransport(timeout),
                                               allow_none=True)

    def ping(self) -> str | None:
        try:
            return self.proxy.fldigi.version()
        except (OSError, xmlrpc.client.Error, socket.timeout):
            return None

    def tune(self, label: str, carrier_hz: float | None = None, afc=True, squelch=False):
        mode = MODEM_NAMES[label]
        if self.proxy.modem.get_name() != mode:
            self.proxy.modem.set_by_name(mode)
        if carrier_hz is not None:
            self.proxy.modem.set_carrier(int(round(carrier_hz)))
        self.proxy.main.set_afc(bool(afc))
        self.proxy.main.set_squelch(bool(squelch))

    def clear(self):
        self.proxy.text.clear_rx()

    def rx_text(self) -> str:
        n = self.proxy.text.get_rx_length()
        if n <= 0:
            return ""
        data = self.proxy.text.get_rx(0, n)
        raw = data.data if isinstance(data, xmlrpc.client.Binary) else data
        if isinstance(raw, bytes):
            return raw.decode("utf-8", "replace")
        return str(raw)

    def read_after(self, seconds: float) -> str:
        time.sleep(seconds)
        return self.rx_text()
