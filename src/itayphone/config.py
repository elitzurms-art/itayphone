"""Runtime configuration for ItayPhone."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Config:
    # SIM7600G-H over USB exposes several serial ports; ttyUSB2 is the AT
    # command port on Raspberry Pi OS (ttyUSB1 is usually the NMEA/GPS port).
    # When the modem is used through the 40-pin HAT UART instead of USB,
    # this is typically /dev/ttyAMA0 or /dev/serial0.
    serial_port: str = "/dev/ttyUSB2"
    baudrate: int = 115200

    # SIM PIN, if the SIM card is locked. None = no PIN.
    sim_pin: str | None = None

    # Where contacts / call history / photos are persisted.
    contacts_path: str = "~/.itayphone/contacts.json"
    history_path: str = "~/.itayphone/history.json"
    photos_path: str = "~/.itayphone/photos"

    log_level: str = "INFO"

    # Use the simulated modem instead of real hardware.
    mock: bool = False

    @property
    def contacts_file(self) -> str:
        return os.path.expanduser(self.contacts_path)

    @property
    def history_file(self) -> str:
        return os.path.expanduser(self.history_path)
