"""Parse WSJT-X UDP "Decode" (type 2) datagrams.

Format from WSJT-X source Network/NetworkMessage.hpp: Qt QDataStream, big-endian,
magic 0xadbccbda, schema number, message type, then fields. Decode (type 2):
  Id(utf8) New(bool) Time(QTime=quint32 ms since midnight) snr(qint32)
  DeltaTime(double) DeltaFrequency(quint32) Mode(utf8) Message(utf8)
  LowConfidence(bool) OffAir(bool)
A Qt utf8 string is quint32 length + bytes, with 0xffffffff meaning null.
WSJT-X sends to 127.0.0.1:2237 by default (Settings > Reporting > UDP Server).
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

MAGIC = 0xADBCCBDA


class ParseError(ValueError):
    pass


class _Reader:
    def __init__(self, b: bytes):
        self.b, self.i = b, 0

    def take(self, n):
        if self.i + n > len(self.b):
            raise ParseError("truncated")
        v = self.b[self.i:self.i + n]
        self.i += n
        return v

    def u32(self):
        return struct.unpack(">I", self.take(4))[0]

    def i32(self):
        return struct.unpack(">i", self.take(4))[0]

    def f64(self):
        return struct.unpack(">d", self.take(8))[0]

    def boolean(self):
        return self.take(1) != b"\x00"

    def utf8(self):
        n = self.u32()
        if n == 0xFFFFFFFF:
            return None
        if n > len(self.b):
            raise ParseError("string length exceeds datagram")
        return self.take(n).decode("utf-8", "replace")


@dataclass
class UdpDecode:
    id: str
    new: bool
    time_ms: int
    snr: int
    dt: float
    df: int
    mode: str
    message: str
    low_confidence: bool
    off_air: bool


def parse(datagram: bytes):
    r = _Reader(datagram)
    if r.u32() != MAGIC:
        raise ParseError("bad magic")
    schema = r.u32()
    if schema < 2:
        raise ParseError(f"unsupported schema {schema}")
    mtype = r.u32()
    if mtype != 2:
        return None  # not a Decode; caller ignores Heartbeat, Status, etc.
    d = UdpDecode(r.utf8() or "", r.boolean(), r.u32(), r.i32(), r.f64(), r.u32(),
                  r.utf8() or "", r.utf8() or "", False, False)
    # LowConfidence / OffAir were added later; tolerate their absence
    if r.i < len(datagram):
        d.low_confidence = r.boolean()
    if r.i < len(datagram):
        d.off_air = r.boolean()
    return d


def _qstr(s):
    if s is None:
        return struct.pack(">I", 0xFFFFFFFF)
    b = s.encode("utf-8")
    return struct.pack(">I", len(b)) + b


def build_decode(d: UdpDecode, schema=2) -> bytes:
    """Encoder used only by the tests to produce datagrams."""
    return (struct.pack(">III", MAGIC, schema, 2) + _qstr(d.id) + bytes([d.new])
            + struct.pack(">Ii", d.time_ms, d.snr) + struct.pack(">d", d.dt)
            + struct.pack(">I", d.df) + _qstr(d.mode) + _qstr(d.message)
            + bytes([d.low_confidence, d.off_air]))
