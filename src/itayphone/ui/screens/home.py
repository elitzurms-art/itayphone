"""Home screen / launcher — iOS-style: status bar, clock/date, app grid + dock."""

from __future__ import annotations

from datetime import datetime

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from ...modem.models import NetworkStatus
from ..theme import (BLUE, GREEN, INDIGO, ORANGE, PURPLE, TEAL, H, dock,
                     gradient_bg, ios_icon, set_badge)

_WEEKDAYS = ["יום שני", "יום שלישי", "יום רביעי", "יום חמישי", "יום שישי",
             "שבת", "יום ראשון"]
_MONTHS = ["ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני", "יולי", "אוגוסט",
           "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"]

WHITE = (1, 1, 1, 1)


class HomeScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        # Bright iOS-style wallpaper gradient (blue -> indigo).
        gradient_bg(self, top=(0.26, 0.49, 0.93), bottom=(0.30, 0.22, 0.62))

        root = BoxLayout(orientation="vertical", padding=[16, 10, 16, 12],
                         spacing=4)

        # -- iOS status bar: time on the left, signal/battery on the right ----
        status_bar = BoxLayout(size_hint_y=None, height=24, spacing=6)
        self.sb_time = Label(text="9:41", font_size="15sp", bold=True,
                             color=WHITE, halign="left", size_hint_x=0.5)
        self.sb_time.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
        self.signal = Label(text="●●●●  100%", font_size="14sp", color=WHITE,
                            halign="right", size_hint_x=0.5)
        self.signal.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
        status_bar.add_widget(self.sb_time)
        status_bar.add_widget(self.signal)
        root.add_widget(status_bar)

        # -- big clock + date widget (left-aligned, like iOS) -----------------
        widget = BoxLayout(orientation="vertical", size_hint_y=None, height=104,
                           padding=[4, 10, 4, 0])
        self.clock = Label(text="--:--", font_size="50sp", bold=True,
                           color=WHITE, halign="left", valign="middle")
        self.clock.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
        self.date = Label(text="", font_size="17sp", color=(1, 1, 1, 0.9),
                          halign="left", valign="top")
        self.date.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
        widget.add_widget(self.clock)
        widget.add_widget(self.date)
        root.add_widget(widget)

        # -- app grid (iOS rounded icons, 4 columns) --------------------------
        grid = GridLayout(cols=4, spacing=[10, 16], padding=[2, 12, 2, 6],
                          size_hint_y=None, row_default_height=96,
                          row_force_default=True)
        grid.bind(minimum_height=grid.setter("height"))
        self.tile_phone = ios_icon("📞", "טלפון", GREEN,
                                   lambda: self.app.go("dialer"))
        self.tile_messages = ios_icon("💬", "הודעות", BLUE,
                                      lambda: self.app.go("messages"))
        self.tile_contacts = ios_icon("👥", "אנשי קשר", PURPLE,
                                      lambda: self.app.go("contacts"))
        self.tile_camera = ios_icon("📷", "מצלמה", TEAL,
                                    lambda: self.app.go("camera"))
        self.tile_gallery = ios_icon("🖼️", "גלריה", PURPLE,
                                     lambda: self.app.go("gallery"))
        # Android (Waydroid) apps live as first-class home tiles.
        self.tile_whatsapp = ios_icon(
            "💬", "WhatsApp", GREEN,
            lambda: self.app.waydroid.launch("com.whatsapp"))
        self.tile_telegram = ios_icon(
            "✈️", "Telegram", INDIGO,
            lambda: self.app.waydroid.launch("org.telegram.messenger"))
        self.tile_chrome = ios_icon(
            "🌐", "Chrome", ORANGE,
            lambda: self.app.waydroid.launch("com.android.chrome"))
        for t in (self.tile_phone, self.tile_messages, self.tile_contacts,
                  self.tile_camera, self.tile_gallery, self.tile_whatsapp,
                  self.tile_telegram, self.tile_chrome):
            grid.add_widget(t)
        root.add_widget(grid)

        # Flexible spacer keeps the icon grid up top and the dock at the bottom.
        root.add_widget(Widget())

        # -- dock (frosted, the 4 essentials) ---------------------------------
        root.add_widget(dock([
            ("📞", GREEN, lambda: self.app.go("dialer")),
            ("💬", BLUE, lambda: self.app.go("messages")),
            ("📷", TEAL, lambda: self.app.go("camera")),
            ("🌐", ORANGE, lambda: self.app.waydroid.launch("com.android.chrome")),
        ]))

        self.add_widget(root)

        Clock.schedule_interval(lambda dt: self._tick(), 1)
        self._tick()

    def _tick(self) -> None:
        now = datetime.now()
        self.clock.text = now.strftime("%H:%M")
        self.sb_time.text = now.strftime("%H:%M")
        weekday = _WEEKDAYS[now.weekday()]
        self.date.text = H(f"{weekday}, {now.day} ב{_MONTHS[now.month - 1]}")

    def update_status(self, status: NetworkStatus) -> None:
        bars = "●" * status.bars + "○" * (4 - status.bars)
        operator = status.operator or "אין רשת"
        self.signal.text = f"{bars}  " + H(operator) + "  100%"

    def update_badges(self, unread_sms: int, missed_calls: int) -> None:
        set_badge(self.tile_messages, unread_sms)
        # Recents lives inside the Phone app now, so missed calls badge it.
        set_badge(self.tile_phone, missed_calls)
