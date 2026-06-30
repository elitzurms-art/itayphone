"""Active-call screen: caller name, live duration timer, mute / hang up."""

from __future__ import annotations

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

from ..theme import MUTED, RED, SURFACE_HI, H, emoji_image, gradient_bg, mixed


class CallScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._seconds = 0
        self._timer = None
        self._muted = False
        gradient_bg(self)

        root = BoxLayout(orientation="vertical", padding=24, spacing=10)

        # Big round avatar placeholder (scalable emoji image).
        self.avatar = emoji_image("👤")
        self.avatar.size_hint_y = 0.34
        root.add_widget(self.avatar)
        self.who = Label(text="", font_size="32sp", bold=True, size_hint_y=0.16)
        self.status = Label(text="", font_size="20sp", color=MUTED,
                            size_hint_y=0.12)
        root.add_widget(self.who)
        root.add_widget(self.status)

        controls = BoxLayout(size_hint_y=0.34, spacing=14, padding=[10, 14])
        self.mute_btn = Button(text=mixed("🔇", "השתק"), markup=True,
                               background_color=SURFACE_HI)
        self.mute_btn.bind(on_release=lambda *_: self._toggle_mute())
        hang = Button(text=mixed("📵", "נתק"), markup=True, background_color=RED)
        hang.bind(on_release=lambda *_: self.app.end_call())
        controls.add_widget(self.mute_btn)
        controls.add_widget(hang)
        root.add_widget(controls)

        self.add_widget(root)

    # -- lifecycle ---------------------------------------------------------
    def start(self, name: str, status: str) -> None:
        """Show a call in a not-yet-connected state (מחייג… / מצלצל…)."""
        self.who.text = H(name) if name else ""
        self.status.text = H(status)
        self._reset_timer()
        self._set_muted(False)

    def set_active(self) -> None:
        """Connected: switch the status line to a running mm:ss timer."""
        self._seconds = 0
        self.status.text = "00:00"
        if self._timer is None:
            self._timer = Clock.schedule_interval(self._tick, 1)

    def stop(self) -> None:
        self._reset_timer()
        self.status.text = H("השיחה הסתיימה")

    # -- internals ---------------------------------------------------------
    def _tick(self, _dt) -> None:
        self._seconds += 1
        self.status.text = f"{self._seconds // 60:02d}:{self._seconds % 60:02d}"

    def _reset_timer(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        self._seconds = 0

    def _toggle_mute(self) -> None:
        self._set_muted(not self._muted)
        self.app.modem.set_mute(self._muted)

    def _set_muted(self, muted: bool) -> None:
        self._muted = muted
        self.mute_btn.text = (mixed("🔊", "בטל השתקה") if muted
                              else mixed("🔇", "השתק"))
