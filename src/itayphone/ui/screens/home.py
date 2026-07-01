"""Home screen / launcher — iOS-style: status bar, clock/date, app grid + dock."""

from __future__ import annotations

from datetime import datetime

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from ...modem.models import NetworkStatus
from ..theme import (BLUE, GREEN, ORANGE, TEAL, H, dock, gradient_bg, set_badge)
from .launcher import LauncherGrid

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

        # -- editable launcher grid (long-press to edit, drag to reorder) -----
        self.grid = LauncherGrid(self.app, on_edit=self._on_edit)
        root.add_widget(self.grid)

        # Flexible spacer keeps the icon grid up top and the dock at the bottom.
        root.add_widget(Widget())

        # -- dock (frosted, the 4 essentials) ---------------------------------
        root.add_widget(dock([
            ("📞", GREEN, lambda: self.app.go("dialer")),
            ("💬", BLUE, lambda: self.app.go("messages")),
            ("📷", TEAL, lambda: self.app.go("camera")),
            ("🌐", ORANGE, lambda: self.app.launch_app("com.android.chrome")),
        ]))

        self.add_widget(root)

        # "Done" button — only visible while editing the home screen.
        self.done_btn = Button(
            text=H("סיום"), size_hint=(None, None), size=(78, 32),
            pos_hint={"right": 0.96, "top": 0.985}, opacity=0, disabled=True,
            background_color=(0.12, 0.12, 0.15, 0.92), font_size="15sp",
            bold=True)
        self.done_btn.bind(on_release=lambda *_: self.grid.exit_edit())
        self.add_widget(self.done_btn)

        Clock.schedule_interval(lambda dt: self._tick(), 1)
        self._tick()

    def _on_edit(self, editing: bool) -> None:
        self.done_btn.opacity = 1 if editing else 0
        self.done_btn.disabled = not editing

    def on_touch_down(self, touch):
        # While editing, a tap on empty wallpaper finishes editing.
        if getattr(self, "grid", None) is not None and self.grid.edit_mode:
            handled = super().on_touch_down(touch)
            if not handled:
                self.grid.exit_edit()
            return True
        return super().on_touch_down(touch)

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
        msg = self.grid.tile_for("messages")
        phone = self.grid.tile_for("dialer")   # Recents lives in the Phone app
        if msg:
            set_badge(msg, unread_sms)
        if phone:
            set_badge(phone, missed_calls)
