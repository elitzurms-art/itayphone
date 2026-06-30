"""Call history (recents) — a small JSON-backed log of placed/received calls.

Mirrors the ContactStore design so it can be swapped for SQLite later without
touching call sites (add / recent / missed_unseen / mark_all_seen).
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass
class CallRecord:
    number: str
    direction: str            # "in" (received) or "out" (placed)
    timestamp: str            # ISO 8601
    answered: bool = True
    seen: bool = True         # whether the user has looked at it (for badges)

    @property
    def missed(self) -> bool:
        return self.direction == "in" and not self.answered

    @property
    def when(self) -> str:
        """Short human label, e.g. '14:05' today or '01/07 14:05' otherwise."""
        try:
            dt = datetime.fromisoformat(self.timestamp)
        except ValueError:
            return self.timestamp
        if dt.date() == datetime.now().date():
            return dt.strftime("%H:%M")
        return dt.strftime("%d/%m %H:%M")


class CallLog:
    def __init__(self, path: str, now=datetime.now) -> None:
        self.path = os.path.expanduser(path)
        self._now = now              # injectable clock (keeps tests deterministic)
        self._records: list[CallRecord] = []
        self.load()

    def load(self) -> None:
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as f:
                self._records = [CallRecord(**r) for r in json.load(f)]
        else:
            self._records = []

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in self._records], f,
                      ensure_ascii=False, indent=2)

    def add(self, number: str, direction: str, answered: bool = True) -> CallRecord:
        rec = CallRecord(
            number=number,
            direction=direction,
            timestamp=self._now().isoformat(timespec="seconds"),
            answered=answered,
            seen=(direction == "out"),   # placed calls are never "missed"
        )
        self._records.append(rec)
        self.save()
        return rec

    def recent(self, limit: int = 50) -> list[CallRecord]:
        return list(reversed(self._records))[:limit]

    def missed_unseen(self) -> int:
        return sum(1 for r in self._records if r.missed and not r.seen)

    def mark_all_seen(self) -> None:
        changed = False
        for r in self._records:
            if not r.seen:
                r.seen = True
                changed = True
        if changed:
            self.save()
