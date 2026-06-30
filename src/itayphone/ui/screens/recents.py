"""Recents — call history, living inside the Phone app (stock-dialer styling).

Same black background, header and bottom tab row as the dialer, so Keypad /
Recents / Contacts feel like one phone app. Tapping a row calls that number
back. Reached from the dialer's "אחרונות" tab (there is no separate home icon).
"""

from __future__ import annotations

from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen

from ..theme import MUTED, RED, SURFACE_HI, TEXT, H

GREY = (0.62, 0.64, 0.68, 1)
WHITE = (0.96, 0.96, 0.98, 1)

# Direction/answered -> arrow glyph (present in the text font).
_GLYPH = {
    ("out", True): "↗",    # outgoing
    ("in", True): "↙",     # answered incoming
    ("in", False): "↙",    # missed (shown in red)
}


class _Row(ButtonBehavior, BoxLayout):
    """A horizontal row that lays out its children *and* is tappable."""


class _Tab(ButtonBehavior, Label):
    """A transparent bottom-tab button."""


class RecentsScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app

        # Solid black background, matching the dialer.
        with self.canvas.before:
            Color(0, 0, 0, 1)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *_: setattr(self._bg, "pos", self.pos),
                  size=lambda *_: setattr(self._bg, "size", self.size))

        root = BoxLayout(orientation="vertical", padding=[0, 40, 0, 6])

        # -- header: "אחרונות" on the right (RTL) -----------------------------
        header = BoxLayout(size_hint_y=None, height=50, padding=[18, 2])
        title = Label(text=H("אחרונות"), bold=True, font_size="22sp", color=WHITE,
                      halign="right", valign="middle")
        title.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
        header.add_widget(title)
        root.add_widget(header)

        # -- list -------------------------------------------------------------
        scroll = ScrollView()
        self.list = BoxLayout(orientation="vertical", size_hint_y=None, spacing=6,
                              padding=[12, 6])
        self.list.bind(minimum_height=self.list.setter("height"))
        scroll.add_widget(self.list)
        root.add_widget(scroll)

        # -- bottom tabs (same as the dialer; "אחרונות" active) ---------------
        tabs = BoxLayout(size_hint_y=None, height=50)
        contacts = _Tab(text=H("אנשי קשר"), color=GREY, font_size="14sp")
        contacts.bind(on_release=lambda *_: self.app.go("contacts"))
        active = _Tab(text=H("אחרונות"), color=WHITE, bold=True, font_size="14sp")
        keypad = _Tab(text=H("מקשים"), color=GREY, font_size="14sp")
        keypad.bind(on_release=lambda *_: self.app.go("dialer"))
        # RTL: Keypad on the right.
        tabs.add_widget(contacts)
        tabs.add_widget(active)
        tabs.add_widget(keypad)
        root.add_widget(tabs)

        self.add_widget(root)

    def on_pre_enter(self, *args):
        self.reload()
        # Viewing recents clears the "missed" badge.
        self.app.history.mark_all_seen()
        self.app.refresh_badges()

    def reload(self) -> None:
        self.list.clear_widgets()
        records = self.app.history.recent()
        if not records:
            self.list.add_widget(Label(text=H("אין שיחות אחרונות"), color=MUTED,
                                       size_hint_y=None, height=60))
            return
        for rec in records:
            self.list.add_widget(self._row(rec))

    def _row(self, rec) -> _Row:
        who = self.app.contacts.display_name(rec.number)
        glyph = _GLYPH.get((rec.direction, rec.answered), "")
        color = RED if rec.missed else TEXT

        row = _Row(size_hint_y=None, height=58, spacing=8, padding=[12, 6])
        row.bind(on_release=lambda _, n=rec.number: self.app.dial_from_ui(n))
        with row.canvas.before:
            Color(*SURFACE_HI)
            r = RoundedRectangle(pos=row.pos, size=row.size, radius=[14])
        row.bind(pos=lambda *_: setattr(r, "pos", row.pos),
                 size=lambda *_: setattr(r, "size", row.size))

        when = Label(text=str(rec.when), font_size="12sp", color=MUTED,
                     halign="left", valign="middle", size_hint_x=0.35)
        when.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
        name = Label(text=H(who), color=color, halign="right", valign="middle")
        name.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
        icon = Label(text=glyph, size_hint_x=0.14, bold=True, color=color,
                     font_size="24sp")
        # RTL: glyph + name on the right, timestamp on the left.
        row.add_widget(when)
        row.add_widget(name)
        row.add_widget(icon)
        return row
