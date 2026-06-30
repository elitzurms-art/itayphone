"""Parental controls store — a parent PIN + a set of blocked app packages.

Tiny JSON-backed store (like the contacts one). A blocked app can only be
opened after entering the parent PIN; the PIN also guards the controls screen
itself, so the child can't just un-block things.
"""

from __future__ import annotations

import json
import os


class ParentalStore:
    def __init__(self, path: str) -> None:
        self.path = os.path.expanduser(path)
        self.pin: str | None = None
        self.blocked: set[str] = set()
        self.load()

    def load(self) -> None:
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            self.pin = data.get("pin") or None
            self.blocked = set(data.get("blocked", []))
        except Exception:
            self.pin = None
            self.blocked = set()

    def save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({"pin": self.pin, "blocked": sorted(self.blocked)}, f)
        except Exception:
            pass

    # -- PIN ---------------------------------------------------------------
    @property
    def has_pin(self) -> bool:
        return bool(self.pin)

    def set_pin(self, pin: str) -> None:
        self.pin = pin or None
        self.save()

    def check_pin(self, pin: str) -> bool:
        return self.has_pin and pin == self.pin

    # -- blocking ----------------------------------------------------------
    def is_blocked(self, package: str) -> bool:
        return package in self.blocked

    def set_blocked(self, package: str, blocked: bool) -> None:
        if blocked:
            self.blocked.add(package)
        else:
            self.blocked.discard(package)
        self.save()
