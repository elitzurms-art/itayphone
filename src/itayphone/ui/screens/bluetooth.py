"""Bluetooth screen: on/off switch, scan for devices, tap to connect/disconnect.

bluez scanning blocks for a few seconds and pairing/connecting longer, so both
run on a daemon thread and report back through ``Clock.schedule_once``.
"""

from __future__ import annotations

import threading

from kivy.clock import Clock
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen
from kivy.uix.switch import Switch

from ..theme import (INDIGO, MUTED, GREEN, SURFACE_HI, TEXT, H, gradient_bg,
                     top_bar)


class _Row(ButtonBehavior, BoxLayout):
    pass


class BluetoothScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._busy = False
        self._suspend_switch = False
        gradient_bg(self)

        root = BoxLayout(orientation="vertical")
        root.add_widget(top_bar("בלוטות'", lambda: self.app.go("home")))

        header = BoxLayout(size_hint_y=None, height=56, padding=[14, 6], spacing=10)
        self.switch = Switch(active=True, size_hint_x=None, width=80)
        self.switch.bind(active=self._on_switch)
        self.scan_btn = Button(text=H("סרוק"), size_hint_x=None, width=96,
                               background_color=INDIGO)
        self.scan_btn.bind(on_release=lambda *_: self.start_scan())
        lbl = Label(text=H("בלוטות'"), bold=True, font_size="19sp",
                    halign="right", valign="middle")
        lbl.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
        header.add_widget(self.scan_btn)
        header.add_widget(lbl)
        header.add_widget(self.switch)
        root.add_widget(header)

        self.status = Label(text="", size_hint_y=None, height=24, color=MUTED,
                            font_size="13sp")
        root.add_widget(self.status)

        scroll = ScrollView()
        self.list = BoxLayout(orientation="vertical", size_hint_y=None, spacing=6,
                              padding=10)
        self.list.bind(minimum_height=self.list.setter("height"))
        scroll.add_widget(self.list)
        root.add_widget(scroll)

        self.add_widget(root)

    # -- lifecycle ---------------------------------------------------------
    def on_pre_enter(self, *args):
        on = self.app.system.bt_powered()
        self._suspend_switch = True
        self.switch.active = on
        self._suspend_switch = False
        if on:
            self._refresh()           # show known devices immediately
            self.start_scan()
        else:
            self._show_off()

    def _show_off(self) -> None:
        self.list.clear_widgets()
        self.status.text = H("בלוטות' כבוי")

    # -- switch ------------------------------------------------------------
    def _on_switch(self, _w, value):
        if self._suspend_switch:
            return

        def work():
            self.app.system.set_bluetooth(value)
            Clock.schedule_once(lambda *_:
                                self.start_scan() if value else self._show_off())
        self.status.text = H("מפעיל…" if value else "מכבה…")
        threading.Thread(target=work, daemon=True).start()

    # -- scanning ----------------------------------------------------------
    def start_scan(self) -> None:
        if self._busy or not self.switch.active:
            return
        self._busy = True
        self.status.text = H("סורק מכשירים…")

        def work():
            self.app.system.bt_scan(6)
            devs = self.app.system.bt_list()
            Clock.schedule_once(lambda *_: self._populate(devs))
        threading.Thread(target=work, daemon=True).start()

    def _refresh(self) -> None:
        self._populate(self.app.system.bt_list())

    def _populate(self, devs) -> None:
        self._busy = False
        self.list.clear_widgets()
        if not devs:
            self.status.text = H("לא נמצאו מכשירים")
            return
        self.status.text = H(f"{len(devs)} מכשירים")
        for dev in devs:
            self.list.add_widget(self._row(dev))

    def _row(self, dev) -> _Row:
        from kivy.graphics import Color, RoundedRectangle
        row = _Row(size_hint_y=None, height=58, spacing=8, padding=[14, 6])
        row.bind(on_release=lambda *_: self._toggle_device(dev))
        with row.canvas.before:
            Color(*(GREEN if dev["connected"] else SURFACE_HI))
            r = RoundedRectangle(pos=row.pos, size=row.size, radius=[14])
        row.bind(pos=lambda *_: setattr(r, "pos", row.pos),
                 size=lambda *_: setattr(r, "size", row.size))

        state = Label(text=H("מחובר") if dev["connected"] else "",
                      size_hint_x=0.3, color=TEXT, font_size="13sp",
                      halign="left", valign="middle")
        state.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
        name = Label(text=dev["name"], color=TEXT, halign="right",
                     valign="middle", bold=dev["connected"])
        name.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
        row.add_widget(state)
        row.add_widget(name)
        return row

    # -- connect / disconnect ---------------------------------------------
    def _toggle_device(self, dev) -> None:
        if self._busy:
            return
        self._busy = True
        connect = not dev["connected"]
        verb = "מתחבר ל" if connect else "מנתק מ"
        self.status.text = H(f"{verb}-{dev['name']}…")

        def work():
            if connect:
                ok = self.app.system.bt_connect(dev["mac"])
            else:
                ok = self.app.system.bt_disconnect(dev["mac"])
            devs = self.app.system.bt_list()

            def done(*_):
                self._populate(devs)
                if ok:
                    self.status.text = H(
                        f"{'מחובר ל' if connect else 'נותק מ'}-{dev['name']}")
                else:
                    self.status.text = H(f"הפעולה עם {dev['name']} נכשלה")
            Clock.schedule_once(done)
        threading.Thread(target=work, daemon=True).start()
