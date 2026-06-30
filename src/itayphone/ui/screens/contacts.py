"""Contacts — list / add / call / message, in the Phone app's stock styling.

Same black background, header and bottom tab row as the dialer and recents, so
Keypad / Recents / Contacts read as one phone app. Still reachable from its own
home-screen icon as well.
"""

from __future__ import annotations

from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen
from kivy.uix.textinput import TextInput

from ..theme import (BLUE, GREEN, MUTED, SURFACE_HI, TEXT, H, icon_button)

GREY = (0.62, 0.64, 0.68, 1)
WHITE = (0.96, 0.96, 0.98, 1)


class _Tab(ButtonBehavior, Label):
    """A transparent bottom-tab button."""


class ContactsScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app

        # Solid black background, matching the dialer / recents.
        with self.canvas.before:
            Color(0, 0, 0, 1)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *_: setattr(self._bg, "pos", self.pos),
                  size=lambda *_: setattr(self._bg, "size", self.size))

        root = BoxLayout(orientation="vertical", padding=[0, 40, 0, 6])

        # -- header: "אנשי קשר" on the right (RTL) ----------------------------
        header = BoxLayout(size_hint_y=None, height=50, padding=[18, 2])
        title = Label(text=H("אנשי קשר"), bold=True, font_size="22sp",
                      color=WHITE, halign="right", valign="middle")
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

        # -- add-contact row --------------------------------------------------
        add_row = BoxLayout(size_hint_y=None, height=60, spacing=6,
                            padding=[12, 6])
        # NB: avoid the attribute name `name` — Kivy's Screen already owns it.
        self.name_input = TextInput(hint_text=H("שם"), multiline=False)
        self.number_input = TextInput(hint_text=H("מספר"), multiline=False,
                                      size_hint_x=0.5)
        add_btn = Button(text="+", size_hint_x=0.18, font_size="30sp",
                         bold=True, background_color=GREEN)
        add_btn.bind(on_release=lambda *_: self._add())
        # RTL: name on the right, then number, add button on the left.
        add_row.add_widget(add_btn)
        add_row.add_widget(self.number_input)
        add_row.add_widget(self.name_input)
        root.add_widget(add_row)

        # -- bottom tabs ("אנשי קשר" active) ----------------------------------
        tabs = BoxLayout(size_hint_y=None, height=50)
        active = _Tab(text=H("אנשי קשר"), color=WHITE, bold=True, font_size="14sp")
        recents = _Tab(text=H("אחרונות"), color=GREY, font_size="14sp")
        recents.bind(on_release=lambda *_: self.app.go("recents"))
        keypad = _Tab(text=H("מקשים"), color=GREY, font_size="14sp")
        keypad.bind(on_release=lambda *_: self.app.go("dialer"))
        # RTL: Keypad on the right.
        tabs.add_widget(active)
        tabs.add_widget(recents)
        tabs.add_widget(keypad)
        root.add_widget(tabs)

        self.add_widget(root)

    def on_pre_enter(self, *args):
        self.reload()

    def reload(self) -> None:
        self.list.clear_widgets()
        contacts = self.app.contacts.all()
        if not contacts:
            self.list.add_widget(Label(text=H("אין אנשי קשר"), color=MUTED,
                                       size_hint_y=None, height=60))
            return
        for c in contacts:
            self.list.add_widget(self._row(c.name, c.number))

    def _row(self, name: str, number: str) -> BoxLayout:
        row = BoxLayout(size_hint_y=None, height=68, spacing=6, padding=[10, 8])
        with row.canvas.before:
            Color(*SURFACE_HI)
            r = RoundedRectangle(pos=row.pos, size=row.size, radius=[14])
        row.bind(pos=lambda *_: setattr(r, "pos", row.pos),
                 size=lambda *_: setattr(r, "size", row.size))

        msg = icon_button("💬", BLUE,
                          lambda: self.app.compose_to(number), size=50)
        msg.size_hint_x = 0.16
        call = icon_button("📞", GREEN,
                           lambda: self.app.dial_from_ui(number), size=50)
        call.size_hint_x = 0.16

        info = BoxLayout(orientation="vertical", padding=[12, 4])
        name_lbl = Label(text=H(name), bold=True, color=TEXT, halign="right",
                         valign="middle", size_hint_y=0.55, font_size="17sp")
        name_lbl.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
        num_lbl = Label(text=number, color=MUTED, halign="right",
                        valign="middle", size_hint_y=0.45, font_size="13sp")
        num_lbl.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
        info.add_widget(name_lbl)
        info.add_widget(num_lbl)
        # RTL: name/number on the right, action buttons on the left.
        row.add_widget(msg)
        row.add_widget(call)
        row.add_widget(info)
        return row

    def _add(self) -> None:
        name = self.name_input.text.strip()
        number = self.number_input.text.strip()
        if name and number:
            self.app.contacts.add(name, number)
            self.name_input.text = self.number_input.text = ""
            self.reload()
