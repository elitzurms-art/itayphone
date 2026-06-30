"""Data models for the modem layer."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CallState(Enum):
    IDLE = "idle"
    DIALING = "dialing"      # we placed a call, waiting for the other side
    INCOMING = "incoming"    # the phone is ringing (RING / +CLIP)
    ACTIVE = "active"        # call connected
    ENDED = "ended"


@dataclass
class SMS:
    index: int               # storage index on the modem
    sender: str              # phone number
    timestamp: str           # raw modem timestamp string
    text: str
    unread: bool = True


@dataclass
class NetworkStatus:
    registered: bool = False
    operator: str = ""
    # Signal strength in dBm (derived from AT+CSQ). None if unknown.
    signal_dbm: int | None = None
    # Access technology, e.g. "LTE", "WCDMA", "GSM".
    technology: str = ""

    @property
    def bars(self) -> int:
        """Map signal strength to a 0-4 bar indicator for the UI."""
        if self.signal_dbm is None:
            return 0
        if self.signal_dbm >= -70:
            return 4
        if self.signal_dbm >= -85:
            return 3
        if self.signal_dbm >= -100:
            return 2
        if self.signal_dbm >= -110:
            return 1
        return 0
