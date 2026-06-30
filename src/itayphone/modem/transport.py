"""Low-level AT command transport for the SIM7600.

`ATTransport` owns the serial port and a background reader thread. The reader
separates two kinds of lines coming from the modem:

* **Command responses** — lines that belong to a command we just sent, ending
  in a final result code (``OK`` / ``ERROR`` / ``+CME ERROR: ...``).
* **URCs** (Unsolicited Result Codes) — events the modem pushes on its own:
  ``RING``, ``+CLIP``, ``+CMTI`` (new SMS), ``NO CARRIER``, etc. These are
  dispatched to ``urc_callback`` instead of being returned to a command.

`MockTransport` implements the same interface without hardware, so the rest of
the stack (and the tests) can run on a laptop before the parts arrive.
"""

from __future__ import annotations

import queue
import threading
import time
from typing import Callable, Iterable

try:  # pyserial is optional in --mock mode
    import serial
except ImportError:  # pragma: no cover - exercised only without pyserial
    serial = None

# Prefixes / exact lines the modem emits unsolicited. Anything starting with
# one of these (when not part of a pending command) is treated as a URC.
URC_PREFIXES: tuple[str, ...] = (
    "RING",
    "NO CARRIER",
    "+CLIP:",
    "+CMTI:",     # new SMS stored: +CMTI: "SM",<index>
    "+CMT:",      # new SMS delivered directly
    "+CREG:",
    "+CEREG:",
    "VOICE CALL:",
)

_FINAL_OK = ("OK",)
_FINAL_ERROR = ("ERROR", "+CME ERROR:", "+CMS ERROR:")

UrcCallback = Callable[[str], None]


class ATError(RuntimeError):
    """Raised when a command returns an ERROR final result code."""


class ATTimeout(RuntimeError):
    """Raised when a command does not complete within its timeout."""


class ATTransport:
    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        timeout: float = 0.5,
        urc_callback: UrcCallback | None = None,
    ) -> None:
        if serial is None:
            raise RuntimeError(
                "pyserial is not installed; use MockTransport or `pip install pyserial`"
            )
        self._port = port
        self._baudrate = baudrate
        self._timeout = timeout
        self.urc_callback = urc_callback

        self._serial: "serial.Serial | None" = None
        self._responses: "queue.Queue[str]" = queue.Queue()
        self._reader: threading.Thread | None = None
        self._running = threading.Event()
        self._write_lock = threading.Lock()

    # -- lifecycle ---------------------------------------------------------
    def open(self) -> None:
        self._serial = serial.Serial(self._port, self._baudrate, timeout=self._timeout)
        self._running.set()
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    def close(self) -> None:
        self._running.clear()
        if self._reader:
            self._reader.join(timeout=2.0)
        if self._serial:
            self._serial.close()
            self._serial = None

    # -- reading -----------------------------------------------------------
    def _read_loop(self) -> None:
        assert self._serial is not None
        while self._running.is_set():
            try:
                raw = self._serial.readline()
            except Exception:  # serial error -> stop
                break
            if not raw:
                continue
            line = raw.decode(errors="replace").strip()
            if not line:
                continue
            self._dispatch(line)

    def _dispatch(self, line: str) -> None:
        if _is_urc(line):
            if self.urc_callback:
                # Run the callback off the reader thread is the caller's job;
                # keep dispatch cheap and non-blocking here.
                self.urc_callback(line)
            return
        self._responses.put(line)

    # -- writing -----------------------------------------------------------
    def send(self, command: str, timeout: float = 5.0) -> list[str]:
        """Send an AT command and return its informational response lines.

        Lines containing the final ``OK`` are consumed; ``ERROR`` raises
        :class:`ATError`; exceeding ``timeout`` raises :class:`ATTimeout`.
        """
        assert self._serial is not None, "transport not open"
        with self._write_lock:
            _drain(self._responses)
            self._serial.write((command + "\r\n").encode())
            return self._collect(command, timeout)

    def _collect(self, command: str, timeout: float) -> list[str]:
        deadline = time.monotonic() + timeout
        lines: list[str] = []
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ATTimeout(f"timeout waiting for response to {command!r}")
            try:
                line = self._responses.get(timeout=remaining)
            except queue.Empty:
                raise ATTimeout(f"timeout waiting for response to {command!r}")
            if line == command:  # command echo
                continue
            if line in _FINAL_OK:
                return lines
            if any(line.startswith(p) for p in _FINAL_ERROR):
                raise ATError(f"{command!r} -> {line}")
            lines.append(line)


class MockTransport:
    """Drop-in fake for :class:`ATTransport` used by tests and ``--mock``.

    Canned responses are keyed by command prefix. URCs can be injected at
    runtime with :meth:`inject_urc` to simulate incoming calls / SMS.
    """

    def __init__(self, urc_callback: UrcCallback | None = None) -> None:
        self.urc_callback = urc_callback
        self.sent: list[str] = []
        self._responses: dict[str, list[str]] = {
            "AT": [],
            "ATE0": [],
            "AT+CMGF=1": [],
            "AT+CSQ": ["+CSQ: 24,99"],            # ~-65 dBm, good
            "AT+COPS?": ['+COPS: 0,0,"Partner IL",7'],  # 7 = LTE
            "AT+CREG?": ["+CREG: 0,1"],
            "AT+CEREG?": ["+CEREG: 0,1"],
        }

    def open(self) -> None:  # noqa: D401 - interface parity
        pass

    def close(self) -> None:
        pass

    def set_response(self, command: str, lines: Iterable[str]) -> None:
        self._responses[command] = list(lines)

    def inject_urc(self, line: str) -> None:
        if self.urc_callback:
            self.urc_callback(line)

    def send(self, command: str, timeout: float = 5.0) -> list[str]:
        self.sent.append(command)
        # Exact match first, then prefix match (e.g. ATD<number>;).
        if command in self._responses:
            return list(self._responses[command])
        for prefix, lines in self._responses.items():
            if command.startswith(prefix):
                return list(lines)
        return []  # unknown command -> behave like a bare OK


def _is_urc(line: str) -> bool:
    return any(line.startswith(p) for p in URC_PREFIXES)


def _drain(q: "queue.Queue[str]") -> None:
    try:
        while True:
            q.get_nowait()
    except queue.Empty:
        pass
