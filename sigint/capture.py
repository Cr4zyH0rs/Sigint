"""Live audio capture from the IC-7300 USB codec into a rolling buffer.

Uses sounddevice.InputStream with a callback (python-sounddevice docs,
https://python-sounddevice.readthedocs.io/en/latest/api/streams.html). The
callback runs on PortAudio's audio thread, so it only copies samples into a
preallocated ring buffer and records the ADC time of the block; everything else
happens on the consumer side.
"""
from __future__ import annotations

import threading
import time

import numpy as np


class RingBuffer:
    """Fixed-size mono float32 ring buffer that tracks absolute sample index.

    `total` counts every sample ever written, so a reader can ask for an
    absolute range [start, start+n) and learn whether it was overwritten.
    """

    def __init__(self, capacity: int):
        if capacity <= 0:
            raise ValueError("capacity must be > 0")
        self.capacity = int(capacity)
        self.buf = np.zeros(self.capacity, dtype=np.float32)
        self.total = 0
        self.lock = threading.Lock()

    def write(self, x: np.ndarray):
        x = np.asarray(x, dtype=np.float32).ravel()
        n = len(x)
        if n == 0:
            return
        with self.lock:
            if n >= self.capacity:
                x = x[-self.capacity:]
                self.total += n - self.capacity
                n = self.capacity
            i = self.total % self.capacity
            first = min(n, self.capacity - i)
            self.buf[i:i + first] = x[:first]
            if first < n:
                self.buf[:n - first] = x[first:]
            self.total += n

    def read_abs(self, start: int, n: int) -> np.ndarray | None:
        """Return samples [start, start+n) or None if not fully available."""
        with self.lock:
            if n > self.capacity or start < self.total - self.capacity or start + n > self.total:
                return None
            i = start % self.capacity
            first = min(n, self.capacity - i)
            out = np.empty(n, dtype=np.float32)
            out[:first] = self.buf[i:i + first]
            if first < n:
                out[first:] = self.buf[:n - first]
            return out


class AudioCapture:
    """Wraps sounddevice.InputStream; records (abs_index, utc_time) anchors so the
    slicer can map wall-clock UTC to sample indices."""

    def __init__(self, device=None, samplerate=48000, channels=1, seconds=60, blocksize=4800,
                 clock=time.time):
        self.device = device
        self.fs = samplerate
        self.channels = channels
        self.ring = RingBuffer(int(samplerate * seconds))
        self.blocksize = blocksize
        self.clock = clock
        self.anchor = None  # (abs_sample_index, utc_seconds) of latest block start
        self.overflows = 0
        self.stream = None

    def _callback(self, indata, frames, time_info, status):
        if status and status.input_overflow:
            self.overflows += 1
        now = self.clock()
        start_idx = self.ring.total
        mono = indata[:, 0] if indata.ndim == 2 else indata
        self.ring.write(mono)
        # time of first sample in this block ~ now - frames/fs (callback fires after block)
        self.anchor = (start_idx, now - frames / self.fs)

    def start(self):
        import sounddevice as sd  # imported lazily so tests run without PortAudio
        self.stream = sd.InputStream(device=self.device, samplerate=self.fs,
                                     channels=self.channels, dtype="float32",
                                     blocksize=self.blocksize, callback=self._callback)
        self.stream.start()

    def stop(self):
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def utc_to_index(self, utc: float) -> int | None:
        if self.anchor is None:
            return None
        idx0, t0 = self.anchor
        return int(round(idx0 + (utc - t0) * self.fs))
