"""Camera screen: live preview placeholder + capture to a photo file.

A real Kivy preview would bind picamera2 frames to a Texture; for the first
milestone the screen drives capture and shows the last saved path, which is
enough to validate the camera backend end-to-end (mock and real).
"""

from __future__ import annotations

import os

from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

from ..theme import MUTED, TEAL, H, gradient_bg, mixed, top_bar


class _Thumb(ButtonBehavior, Image):
    """Last-photo thumbnail; tap it to open the gallery."""


class CameraScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        gradient_bg(self)

        root = BoxLayout(orientation="vertical")
        root.add_widget(top_bar("מצלמה", self._leave))

        self.preview = Label(text=H("תצוגה מקדימה"), halign="center",
                             valign="middle", font_size="26sp")
        root.add_widget(self.preview)

        self.thumb = _Thumb(size_hint_y=0.25)
        self.thumb.bind(on_release=lambda *_: self.app.go("gallery"))
        root.add_widget(self.thumb)

        self.shutter = Button(text=mixed("📸", "צלם"), markup=True,
                              size_hint_y=None, height=72, font_size="22sp",
                              background_color=TEAL)
        self.shutter.bind(on_release=lambda *_: self._capture())
        root.add_widget(self.shutter)

        self.add_widget(root)

    def on_pre_enter(self, *args):
        if self.app.camera.available():
            self.app.camera.start_preview()
            self.preview.text = H("● שידור חי")
        else:
            self.preview.text = H("לא זוהתה מצלמה")

    def _capture(self) -> None:
        if not self.app.camera.available():
            return
        path = self.app.camera.capture(self.app.photos_dir)
        # Show the captured image as a thumbnail (real backend writes a JPEG).
        if os.path.getsize(path) > 64:
            self.thumb.source = path
            self.thumb.reload()
        self.preview.text = H(f"נשמר:\n{os.path.basename(path)}")

    def _leave(self, *args) -> None:
        self.app.camera.stop_preview()
        self.app.go("home")
