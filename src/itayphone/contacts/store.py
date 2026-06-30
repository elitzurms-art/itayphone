"""Simple JSON-backed contact store.

Kept deliberately tiny for the first milestone; can be swapped for SQLite
later without changing the call sites (add/all/find/by_number/remove).
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass


@dataclass
class Contact:
    name: str
    number: str


class ContactStore:
    def __init__(self, path: str) -> None:
        self.path = os.path.expanduser(path)
        self._contacts: list[Contact] = []
        self.load()

    def load(self) -> None:
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as f:
                self._contacts = [Contact(**c) for c in json.load(f)]
        else:
            self._contacts = []

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump([asdict(c) for c in self._contacts], f,
                      ensure_ascii=False, indent=2)

    def all(self) -> list[Contact]:
        return sorted(self._contacts, key=lambda c: c.name.lower())

    def add(self, name: str, number: str) -> Contact:
        contact = Contact(name=name, number=number)
        self._contacts.append(contact)
        self.save()
        return contact

    def remove(self, number: str) -> None:
        self._contacts = [c for c in self._contacts if c.number != number]
        self.save()

    def by_number(self, number: str) -> Contact | None:
        return next((c for c in self._contacts if c.number == number), None)

    def find(self, query: str) -> list[Contact]:
        q = query.lower()
        return [c for c in self._contacts
                if q in c.name.lower() or q in c.number]

    def display_name(self, number: str) -> str:
        """Return the contact name for a number, or the number itself."""
        contact = self.by_number(number)
        return contact.name if contact else number
