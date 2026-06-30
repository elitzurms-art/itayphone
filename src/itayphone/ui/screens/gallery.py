"""Gallery: a thumbnail grid of captured photos + screenshots, tap to enlarge.

Scans the photo directory (camera captures) and the screenshots directory,
newest first, and shows each as a cropped square thumbnail. Tapping one opens
it full-screen; tap again to close. Placeholder/mock files (a few bytes) are
skipped so they don't show as broken images.
"""

from __future__ import annotations

import os

from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen

from ..theme import MUTED, RED, SURFACE, H, gradient_bg, top_bar

_EXTS = (".jpg", ".jpeg", ".png")
_SCREENSHOTS = "~/.itayphone/screenshots"


class _Thumb(ButtonBehavior, Image):
    """A tappable image (thumbnail or the full-screen view)."""


class GalleryScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        gradient_bg(self)

        root = BoxLayout(orientation="vertical")
        root.add_widget(top_bar("גלריה", lambda: self.app.go("home")))

        self.status = Label(text="", size_hint_y=None, height=26, color=MUTED,
                            font_size="13sp")
        root.add_widget(self.status)

        scroll = ScrollView()
        self.grid = GridLayout(cols=3, spacing=6, padding=8, size_hint_y=None,
                               row_default_height=118, row_force_default=True)
        self.grid.bind(minimum_height=self.grid.setter("height"))
        scroll.add_widget(self.grid)
        root.add_widget(scroll)

        self.add_widget(root)

    def on_pre_enter(self, *args):
        self.reload()

    def _photo_paths(self) -> list[str]:
        dirs = [self.app.photos_dir, _SCREENSHOTS]
        paths: list[str] = []
        for d in dirs:
            d = os.path.expanduser(d)
            if not os.path.isdir(d):
                continue
            for fn in os.listdir(d):
                if not fn.lower().endswith(_EXTS):
                    continue
                p = os.path.join(d, fn)
                try:
                    if os.path.getsize(p) > 64:   # skip mock placeholders
                        paths.append(p)
                except OSError:
                    pass
        paths.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        return paths

    def reload(self) -> None:
        self.grid.clear_widgets()
        paths = self._photo_paths()
        if not paths:
            self.status.text = H("אין תמונות עדיין")
            return
        self.status.text = H(f"{len(paths)} תמונות")
        for p in paths:
            thumb = _Thumb(source=p, fit_mode="cover", size_hint_y=None,
                           height=118)
            thumb.bind(on_release=lambda _, path=p: self._open(path))
            self.grid.add_widget(thumb)

    def _open(self, path: str) -> None:
        view = ModalView(size_hint=(0.96, 0.9), background_color=(0, 0, 0, 0.97),
                         background="", overlay_color=(0, 0, 0, 0.85))
        layout = FloatLayout()
        # Tap the photo itself to close.
        full = _Thumb(source=path, fit_mode="contain")
        full.bind(on_release=lambda *_: view.dismiss())
        layout.add_widget(full)
        # Delete button, top corner (sits above the photo so it gets the tap).
        delete = Button(text=H("מחק"), size_hint=(None, None), size=(108, 46),
                        pos_hint={"x": 0.04, "top": 0.98}, background_color=RED,
                        font_size="18sp", bold=True)
        delete.bind(on_release=lambda *_: self._confirm_delete(path, view))
        layout.add_widget(delete)
        view.add_widget(layout)
        view.open()

    def _confirm_delete(self, path: str, view) -> None:
        box = BoxLayout(orientation="vertical", spacing=10, padding=14)
        box.add_widget(Label(text=H("למחוק את התמונה?"), size_hint_y=None,
                             height=40, font_size="18sp"))
        btns = BoxLayout(size_hint_y=None, height=50, spacing=10)
        cancel = Button(text=H("ביטול"), background_color=SURFACE)
        confirm = Button(text=H("מחק"), background_color=RED, bold=True)
        btns.add_widget(cancel)
        btns.add_widget(confirm)
        box.add_widget(btns)
        popup = Popup(title="מחיקה", content=box, size_hint=(0.82, None),
                      height=180, title_align="center")
        cancel.bind(on_release=popup.dismiss)

        def do(*_):
            popup.dismiss()
            try:
                os.remove(path)
            except OSError:
                pass
            view.dismiss()
            self.reload()
        confirm.bind(on_release=do)
        popup.open()
