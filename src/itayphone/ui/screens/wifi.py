"""Wi-Fi screen: on/off switch, scan for networks, and connect (with password).

Scans and connects block for several seconds (nmcli rescan / association), so
they run on a daemon thread and hand the result back to the Kivy thread via
``Clock.schedule_once`` — the UI never freezes.
"""

from __future__ import annotations

import threading

from kivy.clock import Clock
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen
from kivy.uix.switch import Switch
from kivy.uix.textinput import TextInput

from ..theme import (BLUE, GREEN, MUTED, SURFACE, SURFACE_HI, TEXT, H,
                     emoji_image, gradient_bg, top_bar)


class _Row(ButtonBehavior, BoxLayout):
    pass


def _bars(signal: int) -> str:
    n = min(4, max(1, round(signal / 25)))
    return "●" * n + "○" * (4 - n)


class WifiScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._busy = False
        self._suspend_switch = False
        gradient_bg(self)

        root = BoxLayout(orientation="vertical")
        root.add_widget(top_bar("Wi-Fi", lambda: self.app.go("home")))

        # Header: on/off switch + a scan button.
        header = BoxLayout(size_hint_y=None, height=56, padding=[14, 6], spacing=10)
        self.switch = Switch(active=True, size_hint_x=None, width=80)
        self.switch.bind(active=self._on_switch)
        self.scan_btn = Button(text=H("סרוק"), size_hint_x=None, width=96,
                               background_color=BLUE)
        self.scan_btn.bind(on_release=lambda *_: self.start_scan())
        lbl = Label(text="Wi-Fi", bold=True, font_size="19sp", halign="right",
                    valign="middle")
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
        on = self.app.system.wifi_enabled()
        self._suspend_switch = True
        self.switch.active = on
        self._suspend_switch = False
        if on:
            self.start_scan()
        else:
            self._show_off()

    def _show_off(self) -> None:
        self.list.clear_widgets()
        self.status.text = H("Wi-Fi כבוי")

    # -- switch ------------------------------------------------------------
    def _on_switch(self, _w, value):
        if self._suspend_switch:
            return

        def work():
            self.app.system.set_wifi(value)
            Clock.schedule_once(lambda *_:
                                self.start_scan() if value else self._show_off())
        self.status.text = H("מפעיל…" if value else "מכבה…")
        threading.Thread(target=work, daemon=True).start()

    # -- scanning ----------------------------------------------------------
    def start_scan(self) -> None:
        if self._busy or not self.switch.active:
            return
        self._busy = True
        self.status.text = H("סורק רשתות…")

        def work():
            nets = self.app.system.wifi_scan()
            Clock.schedule_once(lambda *_: self._populate(nets))
        threading.Thread(target=work, daemon=True).start()

    def _populate(self, nets) -> None:
        self._busy = False
        self.list.clear_widgets()
        if not nets:
            self.status.text = H("לא נמצאו רשתות")
            return
        self.status.text = H(f"{len(nets)} רשתות")
        for net in nets:
            self.list.add_widget(self._row(net))

    def _row(self, net) -> _Row:
        from kivy.graphics import Color, RoundedRectangle
        row = _Row(size_hint_y=None, height=58, spacing=8, padding=[14, 6])
        row.bind(on_release=lambda *_: self._select(net))
        with row.canvas.before:
            Color(*(GREEN if net["active"] else SURFACE_HI))
            r = RoundedRectangle(pos=row.pos, size=row.size, radius=[14])
        row.bind(pos=lambda *_: setattr(r, "pos", row.pos),
                 size=lambda *_: setattr(r, "size", row.size))

        sig = Label(text=_bars(net["signal"]), size_hint_x=0.2, color=TEXT,
                    font_size="15sp")
        if net["secure"]:
            lock = emoji_image("🔒")
            lock.size_hint_x = 0.12
        else:
            from kivy.uix.widget import Widget
            lock = Widget(size_hint_x=0.12)
        mark = "✓ " if net["active"] else ""
        name = Label(text=mark + net["ssid"], color=TEXT, halign="right",
                     valign="middle", bold=net["active"])
        name.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
        row.add_widget(sig)
        row.add_widget(lock)
        row.add_widget(name)
        return row

    # -- connecting --------------------------------------------------------
    def _select(self, net) -> None:
        if net["active"]:
            self.status.text = H(f"מחובר ל-{net['ssid']}")
            return
        if net["secure"]:
            self._ask_password(net)
        else:
            self._connect(net["ssid"], "")

    def _ask_password(self, net) -> None:
        box = BoxLayout(orientation="vertical", spacing=10, padding=12)
        box.add_widget(Label(text=H(f"סיסמה ל-{net['ssid']}"), size_hint_y=None,
                             height=30))
        field = TextInput(password=True, multiline=False, size_hint_y=None,
                          height=46, font_size="18sp")
        box.add_widget(field)
        btns = BoxLayout(size_hint_y=None, height=48, spacing=10)
        ok = Button(text=H("התחבר"), background_color=GREEN)
        cancel = Button(text=H("ביטול"), background_color=SURFACE)
        btns.add_widget(cancel)
        btns.add_widget(ok)
        box.add_widget(btns)
        popup = Popup(title="Wi-Fi", content=box, size_hint=(0.86, None),
                      height=240, title_align="center")
        cancel.bind(on_release=popup.dismiss)

        def go(*_):
            popup.dismiss()
            self._connect(net["ssid"], field.text)
        ok.bind(on_release=go)
        field.bind(on_text_validate=go)
        popup.open()

    def _connect(self, ssid: str, password: str) -> None:
        if self._busy:
            return
        self._busy = True
        self.status.text = H(f"מתחבר ל-{ssid}…")

        def work():
            ok = self.app.system.wifi_connect(ssid, password)
            nets = self.app.system.wifi_scan() if ok else []

            def done(*_):
                self._busy = False
                if ok:
                    self._populate(nets)
                    self.status.text = H(f"מחובר ל-{ssid}")
                else:
                    self.status.text = H(f"החיבור ל-{ssid} נכשל")
            Clock.schedule_once(done)
        threading.Thread(target=work, daemon=True).start()
