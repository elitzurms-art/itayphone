"""Editable home launcher: a customisable app grid like a normal Android phone.

* Long-press any icon -> **edit mode** (every icon grows an × remove badge).
* In edit mode, **drag** an icon to reorder it; drop it where you want.
* Tap the × to **remove** an app from the home screen.
* From the Apps drawer, long-press an app to **pin it** to the home screen.

The order is persisted to ``~/.itayphone/home_layout.json`` so it survives
restarts. Items are either a built-in screen (``"dialer"``) or an Android app
(``"app:<package>"``).
"""

from __future__ import annotations

import json
import os

from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label

from ..theme import (BLUE, GREEN, INDIGO, ORANGE, PURPLE, RED, TEAL, H,
                     _squircle, emoji_image)

# -- catalogue ---------------------------------------------------------------
# Built-in screens: key -> (emoji, hebrew label, colour, screen-to-go-to).
BUILTINS = {
    "dialer":   ("📞", "טלפון", GREEN, "dialer"),
    "messages": ("💬", "הודעות", BLUE, "messages"),
    "contacts": ("👥", "אנשי קשר", PURPLE, "contacts"),
    "camera":   ("📷", "מצלמה", TEAL, "camera"),
    "gallery":  ("🖼️", "גלריה", PURPLE, "gallery"),
    "apps":     ("📱", "אפליקציות", TEAL, "apps"),
    "parental": ("🔒", "הורים", INDIGO, "parental"),
    "wifi":     ("📶", "Wi-Fi", BLUE, "wifi"),
    "bluetooth": ("🔵", "בלוטות'", INDIGO, "bluetooth"),
}

# Android packages we have a nice glyph/colour for; others fall back to default.
APP_META = {
    "com.whatsapp": ("💬", "WhatsApp", GREEN),
    "org.telegram.messenger.web": ("✈️", "Telegram", INDIGO),
    "org.telegram.messenger": ("✈️", "Telegram", INDIGO),
    "com.android.chrome": ("🌐", "Chrome", ORANGE),
    "com.google.android.youtube": ("▶️", "YouTube", RED),
    "com.google.android.gm": ("✉️", "Gmail", RED),
    "com.google.android.apps.docs": ("📁", "Drive", BLUE),
    "com.bnhp.payments.paymentsapp": ("💰", "ביט", BLUE),
    "com.google.android.apps.kids.familylink": ("🔒", "Family Link", INDIGO),
    "com.android.vending": ("🛍️", "Play Store", GREEN),
}
_DEFAULT_APP = ("📱", PURPLE)

# What the home screen looks like the very first time (matches the old layout).
DEFAULT_LAYOUT = [
    "dialer", "messages", "contacts", "camera", "gallery",
    "app:com.whatsapp", "app:org.telegram.messenger.web",
    "app:com.android.chrome", "app:com.google.android.youtube",
    "app:com.bnhp.payments.paymentsapp", "apps", "parental",
]

_LAYOUT_PATH = os.path.expanduser("~/.itayphone/home_layout.json")


def load_layout() -> list[str]:
    try:
        with open(_LAYOUT_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list) and data:
            return [str(x) for x in data]
    except Exception:
        pass
    return list(DEFAULT_LAYOUT)


def save_layout(layout: list[str]) -> None:
    try:
        os.makedirs(os.path.dirname(_LAYOUT_PATH), exist_ok=True)
        with open(_LAYOUT_PATH, "w", encoding="utf-8") as f:
            json.dump(layout, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def resolve(key: str, app) -> tuple:
    """key -> (emoji, label, colour, on_launch). Robust to unknown keys."""
    if key.startswith("app:"):
        pkg = key[4:]
        if pkg in APP_META:
            emoji, label, colour = APP_META[pkg]
        else:
            emoji, colour = _DEFAULT_APP
            label = _app_label(app, pkg)
        return emoji, label, colour, (lambda: app.launch_app(pkg))
    emoji, label, colour, screen = BUILTINS.get(
        key, ("📱", key, PURPLE, "home"))
    return emoji, label, colour, (lambda: app.go(screen))


def _app_label(app, pkg: str) -> str:
    try:
        for a in app.waydroid.list_apps():
            if a.package == pkg:
                return a.name
    except Exception:
        pass
    return pkg.rsplit(".", 1)[-1]


# -- tile --------------------------------------------------------------------
class _Tile(BoxLayout):
    """One home icon: coloured squircle + emoji + caption, with edit affordances."""

    LONG_PRESS = 0.45
    SLOP = 14

    def __init__(self, grid, key, emoji, label, colour, **kw):
        super().__init__(orientation="vertical", spacing=3, padding=[2, 4],
                         **kw)
        self.grid = grid
        self.key = key
        self._down = None
        self._moved = False
        self._lp_ev = None

        # Reuse the proven, reliably-centred squircle from the theme instead of
        # hand-placing the icon (which raced the layout and drifted off-centre).
        holder = _squircle(emoji, colour, lambda: None, 62)
        self.holder = holder
        btn = holder.btn

        # unread/missed badge (top-right) — kept for phone/messages
        self.badge = Label(text="", font_size="12sp", bold=True,
                           size_hint=(None, None), size=(24, 24),
                           color=(1, 1, 1, 1), opacity=0)
        with self.badge.canvas.before:
            Color(*RED)
            self.badge._bg = RoundedRectangle(radius=[12])
        self.badge.bind(pos=lambda *_: setattr(self.badge._bg, "pos", self.badge.pos),
                        size=lambda *_: setattr(self.badge._bg, "size", self.badge.size))
        holder.add_widget(self.badge)

        # remove (×) badge (top-left) — only visible in edit mode
        self.rm = Label(text="×", font_size="20sp", bold=True,
                        size_hint=(None, None), size=(26, 26),
                        color=(1, 1, 1, 1), opacity=0)
        with self.rm.canvas.before:
            Color(0.1, 0.1, 0.12, 1)
            self.rm._bg = RoundedRectangle(radius=[13])
        self.rm.bind(pos=lambda *_: setattr(self.rm._bg, "pos", self.rm.pos),
                     size=lambda *_: setattr(self.rm._bg, "size", self.rm.size))
        holder.add_widget(self.rm)

        # Pin the badges to the (reliably-centred) icon button's corners.
        def _badges(*_):
            self.badge.center_x = btn.right - 2
            self.badge.center_y = btn.top - 2
            self.rm.center_x = btn.x + 2
            self.rm.center_y = btn.top - 2
        btn.bind(pos=_badges, size=_badges)

        self.add_widget(holder)
        self.cap = Label(text=H(label), font_size="12sp", bold=True,
                         size_hint_y=None, height=18, color=(1, 1, 1, 1))
        self.add_widget(self.cap)
        Clock.schedule_once(lambda *_: _badges(), 0)

    def set_edit(self, editing: bool) -> None:
        self.rm.opacity = 1 if editing else 0
        self.opacity = 1

    # -- touch -----------------------------------------------------------
    def on_touch_down(self, touch):
        if not self.holder.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        # In edit mode a tap on the × removes the app.
        if self.grid.edit_mode and self.rm.collide_point(*touch.pos):
            self.grid.remove(self)
            return True
        self._down = (touch.x, touch.y)
        self._moved = False
        touch.grab(self)
        self._lp_ev = Clock.schedule_once(self._long_press, self.LONG_PRESS)
        return True

    def _long_press(self, *_):
        if not self.grid.edit_mode:
            self.grid.enter_edit()

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return super().on_touch_move(touch)
        if self._down and (abs(touch.x - self._down[0])
                           + abs(touch.y - self._down[1])) > self.SLOP:
            self._moved = True
            if self._lp_ev:
                self._lp_ev.cancel()
                self._lp_ev = None
            if self.grid.edit_mode:
                self.grid.drag(self, touch)
        return True

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return super().on_touch_up(touch)
        touch.ungrab(self)
        if self._lp_ev:
            self._lp_ev.cancel()
            self._lp_ev = None
        if self.grid.edit_mode and self.grid.dragging:
            self.grid.drop(self, touch)
        elif not self._moved and not self.grid.edit_mode:
            self.on_launch()
        return True


# -- grid --------------------------------------------------------------------
class LauncherGrid(GridLayout):
    """A reorderable, editable grid of home icons."""

    def __init__(self, app, on_edit=None, **kw):
        super().__init__(cols=4, spacing=[10, 16], padding=[2, 12, 2, 6],
                         size_hint_y=None, row_default_height=96,
                         row_force_default=True, **kw)
        self.app = app
        self.on_edit = on_edit
        self.edit_mode = False
        self.dragging = False
        self._ghost = None
        self._drag_tile = None
        self.layout = load_layout()
        self.tiles: list[_Tile] = []
        self.bind(minimum_height=self.setter("height"))
        self.rebuild()

    def tile_for(self, key: str):
        for t in self.tiles:
            if t.key == key:
                return t
        return None

    def rebuild(self) -> None:
        self.clear_widgets()
        self.tiles = []
        for key in self.layout:
            emoji, label, colour, launch = resolve(key, self.app)
            t = _Tile(self, key, emoji, label, colour)
            t.on_launch = launch
            t.set_edit(self.edit_mode)
            self.add_widget(t)
            self.tiles.append(t)

    # -- edit mode -------------------------------------------------------
    def enter_edit(self) -> None:
        self.edit_mode = True
        for t in self.tiles:
            t.set_edit(True)
        if self.on_edit:
            self.on_edit(True)

    def exit_edit(self) -> None:
        self.edit_mode = False
        for t in self.tiles:
            t.set_edit(False)
        if self.on_edit:
            self.on_edit(False)

    def remove(self, tile: _Tile) -> None:
        if tile.key in self.layout:
            self.layout.remove(tile.key)
            save_layout(self.layout)
            self.rebuild()

    def add_app(self, package: str) -> bool:
        """Pin an Android app to the home screen (returns False if already there)."""
        key = f"app:{package}"
        if key in self.layout:
            return False
        self.layout.append(key)
        save_layout(self.layout)
        self.rebuild()
        return True

    # -- drag to reorder -------------------------------------------------
    def drag(self, tile: _Tile, touch) -> None:
        screen = self.parent
        while screen is not None and not hasattr(screen, "add_widget"):
            screen = screen.parent
        if not self.dragging:
            self.dragging = True
            self._drag_tile = tile
            tile.opacity = 0.25
            emoji, label, colour, _ = resolve(tile.key, self.app)
            self._ghost = FloatLayout(size_hint=(None, None), size=(62, 62))
            with self._ghost.canvas:
                Color(*colour)
                self._ghost._sq = RoundedRectangle(size=(62, 62), radius=[14])
            gi = emoji_image(emoji)
            gi.size_hint = (None, None); gi.size = (40, 40); gi.center = (31, 31)
            self._ghost.add_widget(gi)
            self.get_root_window().add_widget(self._ghost)
        self._ghost.center = touch.pos
        self._ghost._sq.pos = (self._ghost.x, self._ghost.y)

    def drop(self, tile: _Tile, touch) -> None:
        if not self.dragging:
            return
        # nearest tile slot to the drop point (window coords)
        best, bestd = None, 1e18
        for i, t in enumerate(self.tiles):
            cx, cy = t.to_window(t.center_x, t.center_y)
            d = (cx - touch.x) ** 2 + (cy - touch.y) ** 2
            if d < bestd:
                bestd, best = d, i
        src = self.tiles.index(self._drag_tile)
        item = self.layout.pop(src)
        self.layout.insert(best, item)
        save_layout(self.layout)
        # cleanup
        if self._ghost is not None:
            self.get_root_window().remove_widget(self._ghost)
            self._ghost = None
        self.dragging = False
        self._drag_tile = None
        self.rebuild()
