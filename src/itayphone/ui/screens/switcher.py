"""App-switcher overlay: a deck of recent-app cards over a blurred backdrop.

Like an iPhone: each card shows a live preview (a snapshot of that screen), the
background is the screen you came from, blurred and dimmed, and the home dock
sits along the bottom. Tap a card or a dock icon to jump there; tap empty space
to dismiss. Built on demand by the app and dropped onto the root layout.
"""

from __future__ import annotations

from kivy.animation import Animation
from kivy.core.image import Image as CoreImage
from kivy.graphics import (Color, PopMatrix, PushMatrix, RoundedRectangle,
                           Translate)
from kivy.properties import NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from ..theme import (BLUE, GREEN, INDIGO, ORANGE, PURPLE, TEAL, TEXT, H, dock,
                     emoji_image)

# screen name -> (icon, Hebrew label, fallback colour when no preview yet)
_META = {
    "home": ("🏠", "בית", BLUE),
    "dialer": ("📞", "טלפון", GREEN),
    "messages": ("💬", "הודעות", BLUE),
    "contacts": ("👥", "אנשי קשר", PURPLE),
    "recents": ("🕘", "אחרונות", ORANGE),
    "camera": ("📷", "מצלמה", TEAL),
    "gallery": ("🖼️", "גלריה", PURPLE),
    "wifi": ("📶", "Wi-Fi", BLUE),
    "bluetooth": ("🔵", "בלוטות'", INDIGO),
}


class _Card(BoxLayout):
    """An app card. Tap to open it; flick it up to close it (remove from recents).

    ``lift`` translates the whole card vertically (via a canvas matrix) so it can
    follow the finger and animate away without fighting the row's layout.
    """

    lift = NumericProperty(0)

    def __init__(self, name, on_pick, on_close, **kwargs):
        super().__init__(**kwargs)
        self._name = name
        self._on_pick = on_pick
        self._on_close = on_close
        self._start = None
        with self.canvas.before:
            PushMatrix()
            self._tr = Translate(0, 0)
        with self.canvas.after:
            PopMatrix()
        self.bind(lift=lambda *_: setattr(self._tr, "y", self.lift))

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._start = (touch.x, touch.y)
            touch.grab(self)
            Animation.cancel_all(self, "lift")
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self and self._start is not None:
            self.lift = max(0.0, touch.y - self._start[1])   # follow finger up
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self and self._start is not None:
            touch.ungrab(self)
            dx = touch.x - self._start[0]
            dy = touch.y - self._start[1]
            self._start = None
            if dy > 90:                                   # flick up -> close
                anim = Animation(lift=self.height + 80, opacity=0, d=0.2,
                                 t="out_quad")
                anim.bind(on_complete=lambda *_: self._on_close(self._name, self))
                anim.start(self)
            elif abs(dx) < 12 and abs(dy) < 12:           # tap -> open
                self._on_pick(self._name)
            else:                                          # snap back
                Animation(lift=0, d=0.16, t="out_quad").start(self)
            return True
        return super().on_touch_up(touch)


def _preview(thumb_path, color):
    """A widget drawing the screen snapshot (or a flat colour) on a rounded rect."""
    w = Widget()
    tex = None
    if thumb_path:
        try:
            tex = CoreImage(thumb_path).texture
        except Exception:
            tex = None
    with w.canvas:
        if tex is not None:
            Color(1, 1, 1, 1)
            rr = RoundedRectangle(texture=tex, pos=w.pos, size=w.size, radius=[20])
        else:
            Color(*color)
            rr = RoundedRectangle(pos=w.pos, size=w.size, radius=[20])
    w.bind(pos=lambda *_: setattr(rr, "pos", w.pos),
           size=lambda *_: setattr(rr, "size", w.size))
    return w


def _card(name, thumb_path, on_pick, on_close):
    emoji_g, label, color = _META.get(name, ("📱", name, INDIGO))
    card = _Card(name, on_pick, on_close, orientation="vertical",
                 size_hint=(None, 1), width=232, spacing=6)

    head = BoxLayout(size_hint_y=None, height=30, spacing=6, padding=[6, 0])
    ic = emoji_image(emoji_g)
    ic.size_hint_x = None
    ic.width = 24
    nm = Label(text=H(label), font_size="15sp", bold=True, color=(1, 1, 1, 1),
               halign="center", valign="middle")
    nm.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
    head.add_widget(ic)
    head.add_widget(nm)
    card.add_widget(head)

    card.add_widget(_preview(thumb_path, color))
    return card


def build_switcher(order, thumbs, on_pick, on_dismiss, on_close=None,
                   bg_path=None, dock_items=None):
    overlay = FloatLayout()

    # Background: the previous screen, blurred + dimmed (or a dark fallback).
    if bg_path:
        overlay.add_widget(Image(source=bg_path, fit_mode="cover"))
    else:
        bg = Widget()
        with bg.canvas:
            Color(0.02, 0.02, 0.04, 0.96)
            br = RoundedRectangle(pos=bg.pos, size=bg.size, radius=[0])
        bg.bind(pos=lambda *_: setattr(br, "pos", bg.pos),
                size=lambda *_: setattr(br, "size", bg.size))
        overlay.add_widget(bg)

    # Tap empty space to dismiss (transparent catcher above the background).
    catch = Button(background_normal="", background_down="",
                   background_color=(0, 0, 0, 0))
    catch.bind(on_release=lambda *_: on_dismiss())
    overlay.add_widget(catch)

    title = Label(text=H("אפליקציות אחרונות"), font_size="17sp", bold=True,
                  color=TEXT, size_hint=(1, None), height=28,
                  pos_hint={"center_x": 0.5, "top": 0.94})
    overlay.add_widget(title)

    scroll = ScrollView(size_hint=(1, None), height=430, bar_width=0,
                        do_scroll_x=True, do_scroll_y=False,
                        pos_hint={"center_x": 0.5, "center_y": 0.54})
    row = BoxLayout(orientation="horizontal", size_hint=(None, 1), spacing=16,
                    padding=[20, 0])
    row.bind(minimum_width=row.setter("width"))
    for name in order:
        row.add_widget(_card(name, thumbs.get(name), on_pick, on_close))
    scroll.add_widget(row)
    overlay.add_widget(scroll)

    if dock_items:
        d = dock(dock_items)
        d.size_hint_x = 0.94
        d.pos_hint = {"center_x": 0.5, "y": 0.015}
        overlay.add_widget(d)

    return overlay
