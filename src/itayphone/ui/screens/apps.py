"""Apps drawer — every Android (Waydroid) app installed, listed dynamically.

Unlike the curated home grid, this screen enumerates whatever is actually
installed (via ``waydroid app list``) so newly-installed apps — Gmail, Drive,
anything from the Play Store — show up on their own without code changes.
"""

from __future__ import annotations

from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen

from ..theme import (BLUE, GREEN, INDIGO, ORANGE, PURPLE, RED, TEAL, H,
                     gradient_bg, ios_icon, top_bar)

# A nice glyph + colour for the apps we know; everything else gets a default.
_KNOWN = {
    "com.whatsapp": ("💬", GREEN),
    "org.telegram.messenger.web": ("✈️", INDIGO),
    "org.telegram.messenger": ("✈️", INDIGO),
    "com.android.chrome": ("🌐", ORANGE),
    "com.google.android.youtube": ("▶️", RED),
    "com.google.android.gm": ("✉️", RED),
    "com.google.android.apps.docs": ("📁", BLUE),
    "com.bnhp.payments.paymentsapp": ("💰", BLUE),
    "com.google.android.apps.kids.familylink": ("🔒", INDIGO),
    "com.android.vending": ("🛍️", GREEN),
    "com.google.android.gms": ("⚙️", TEAL),
}
_DEFAULT = ("📱", PURPLE)


class AppsScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        gradient_bg(self)

        root = BoxLayout(orientation="vertical")
        root.add_widget(top_bar("אפליקציות", lambda: self.app.go("home")))

        scroll = ScrollView()
        self.grid = GridLayout(cols=4, spacing=[10, 16], padding=[8, 12, 8, 12],
                               size_hint_y=None, row_default_height=96,
                               row_force_default=True)
        self.grid.bind(minimum_height=self.grid.setter("height"))
        scroll.add_widget(self.grid)
        root.add_widget(scroll)

        self.empty = Label(text=H("אין אפליקציות אנדרואיד מותקנות"),
                           color=(1, 1, 1, 0.7), font_size="16sp")
        self.add_widget(root)

    def on_pre_enter(self, *_):
        # Re-enumerate every time, so Play-Store installs appear immediately.
        self.reload()

    def reload(self) -> None:
        self.grid.clear_widgets()
        try:
            apps = self.app.waydroid.list_apps()
        except Exception:
            apps = []
        if not apps:
            self.grid.add_widget(self.empty)
            return
        if self.empty.parent:
            self.empty.parent.remove_widget(self.empty)
        for a in sorted(apps, key=lambda x: x.name.lower()):
            glyph, colour = _KNOWN.get(a.package, _DEFAULT)
            pkg = a.package
            st = {"long": False}
            tile = ios_icon(glyph, a.name, colour,
                            (lambda p=pkg, s=st: self._tap(p, s)))
            self._attach_longpress(tile.icon, pkg, st)
            self.grid.add_widget(tile)

    def _tap(self, package: str, st: dict) -> None:
        # A long-press already pinned it; don't also launch.
        if st["long"]:
            st["long"] = False
            return
        self.app.launch_app(package)

    def _attach_longpress(self, btn, package: str, st: dict) -> None:
        """Long-press an app icon to pin it to the home screen."""
        ev = {"e": None}

        def on_state(_w, value):
            if value == "down":
                st["long"] = False
                ev["e"] = Clock.schedule_once(
                    lambda *_: self._pin(package, st), 0.5)
            elif ev["e"]:
                ev["e"].cancel()
                ev["e"] = None
        btn.bind(state=on_state)

    def _pin(self, package: str, st: dict) -> None:
        st["long"] = True
        self.app.pin_to_home(package)
