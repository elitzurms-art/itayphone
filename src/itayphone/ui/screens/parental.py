"""Parental controls — a PIN-locked screen to allow/block apps for the child.

First use sets a parent PIN; after that the PIN is required both to open this
screen and to launch any app the parent has blocked. The child can't reach the
controls (or un-block apps) without the PIN.
"""

from __future__ import annotations

from kivy.graphics import Color, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen
from kivy.uix.switch import Switch
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from ..theme import (GREEN, MUTED, SURFACE, SURFACE_HI, TEXT, H, gradient_bg,
                     top_bar)
from ...waydroid import FEATURED


class ParentalScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        gradient_bg(self)
        root = BoxLayout(orientation="vertical")
        root.add_widget(top_bar("הרשאות הורים", lambda: self.app.go("home")))
        self.body = BoxLayout(orientation="vertical", padding=16, spacing=12)
        root.add_widget(self.body)
        self.add_widget(root)

    def on_pre_enter(self, *args):
        self._show_lock()           # always re-lock when (re)entering

    # -- PIN gate ----------------------------------------------------------
    def _show_lock(self) -> None:
        self.body.clear_widgets()
        store = self.app.parental
        first = not store.has_pin
        self.body.add_widget(Label(
            text=H("הגדר קוד הורים חדש" if first else "הזן קוד הורים"),
            size_hint_y=None, height=42, color=TEXT, font_size="19sp", bold=True))
        field = TextInput(password=True, multiline=False, input_filter="int",
                          font_size="28sp", halign="center", size_hint_y=None,
                          height=62)
        self.body.add_widget(field)
        status = Label(text="", size_hint_y=None, height=24, color=MUTED,
                       font_size="13sp")
        self.body.add_widget(status)
        btn = Button(text=H("שמור קוד" if first else "כניסה"), size_hint_y=None,
                     height=56, background_color=GREEN)
        self.body.add_widget(btn)
        self.body.add_widget(Widget())   # push everything up

        def submit(*_):
            pin = field.text.strip()
            if first:
                if len(pin) < 4:
                    status.text = H("הקוד חייב להיות לפחות 4 ספרות")
                    return
                store.set_pin(pin)
                self._show_controls()
            elif store.check_pin(pin):
                self._show_controls()
            else:
                status.text = H("קוד שגוי")
                field.text = ""
        btn.bind(on_release=submit)
        field.bind(on_text_validate=submit)

    # -- controls ----------------------------------------------------------
    def _show_controls(self) -> None:
        self.body.clear_widgets()
        store = self.app.parental
        self.body.add_widget(Label(text=H("אפליקציות מותרות"), size_hint_y=None,
                                   height=32, color=TEXT, font_size="18sp",
                                   bold=True))
        self.body.add_widget(Label(
            text=H("כבה כדי לחסום — תידרש להזין קוד כדי לפתוח"), size_hint_y=None,
            height=22, color=MUTED, font_size="12sp"))
        scroll = ScrollView()
        lst = BoxLayout(orientation="vertical", size_hint_y=None, spacing=8,
                        padding=[0, 6])
        lst.bind(minimum_height=lst.setter("height"))
        for name, pkg in FEATURED:
            lst.add_widget(self._row(name, pkg, store))
        scroll.add_widget(lst)
        self.body.add_widget(scroll)
        change = Button(text=H("שנה קוד הורים"), size_hint_y=None, height=50,
                        background_color=SURFACE)
        change.bind(on_release=lambda *_: self._change_pin())
        self.body.add_widget(change)

    def _row(self, name, pkg, store):
        row = BoxLayout(size_hint_y=None, height=58, spacing=10, padding=[12, 6])
        with row.canvas.before:
            Color(*SURFACE_HI)
            r = RoundedRectangle(pos=row.pos, size=row.size, radius=[14])
        row.bind(pos=lambda *_: setattr(r, "pos", row.pos),
                 size=lambda *_: setattr(r, "size", row.size))
        sw = Switch(active=not store.is_blocked(pkg), size_hint_x=None, width=84)
        sw.bind(active=lambda _w, val, p=pkg: store.set_blocked(p, not val))
        lbl = Label(text=H(name), color=TEXT, halign="right", valign="middle")
        lbl.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
        row.add_widget(sw)
        row.add_widget(lbl)
        return row

    def _change_pin(self) -> None:
        self.app.parental.set_pin(None)   # forget it -> the lock asks for a new one
        self._show_lock()
