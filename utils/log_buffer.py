"""Capture stdout/stderr into a ring buffer for the web log viewer."""

import sys
import threading
from collections import deque
from datetime import datetime

MAX_LOG_LINES = 300

_lock = threading.Lock()
_buffer: deque = deque(maxlen=MAX_LOG_LINES)
_next_id = 0
_installed = False


def _infer_level(line: str) -> str:
    if "[ERROR]" in line or "Error" in line or "Traceback" in line:
        return "error"
    if "[WARN]" in line:
        return "warn"
    if "[TARGET]" in line or "found person" in line:
        return "target"
    if "[INIT]" in line or "[OK]" in line or "INFO:" in line:
        return "info"
    if "[SHUTDOWN]" in line or "[EXIT]" in line or "[STOP]" in line:
        return "muted"
    return "log"


def _append_line(line: str):
    global _next_id
    line = line.rstrip()
    if not line:
        return
    now = datetime.now()
    ts = now.strftime("%H:%M:%S:") + f"{now.microsecond // 1000:03d}"
    with _lock:
        _next_id += 1
        _buffer.append(
            {
                "id": _next_id,
                "t": ts,
                "level": _infer_level(line),
                "msg": line,
            }
        )


class _TeeWriter:
    def __init__(self, original):
        self._original = original

    def write(self, data):
        self._original.write(data)
        if not data:
            return
        # Handle partial lines and bursts without newlines
        text = data if isinstance(data, str) else data.decode("utf-8", errors="replace")
        for part in text.splitlines():
            if part.strip():
                _append_line(part)

    def flush(self):
        self._original.flush()

    def isatty(self):
        return getattr(self._original, "isatty", lambda: False)()


def install_log_capture():
    global _installed
    if _installed:
        return
    sys.stdout = _TeeWriter(sys.stdout)
    sys.stderr = _TeeWriter(sys.stderr)
    _installed = True
    _append_line("[INIT] Log capture enabled for web viewer")


def get_logs(after_id: int = 0) -> list[dict]:
    with _lock:
        if after_id <= 0:
            return list(_buffer)
        return [e for e in _buffer if e["id"] > after_id]
