"""App-switcher overlay: a deck of recent-app cards over a blurred backdrop.

Like an iPhone: each card shows a live preview (a snapshot of that screen), the
background is the screen you came from (blurred + dimmed), and the home dock
sits along the bottom. Tap a card to jump there; **flick a card up to close it**
(remove it from recents); drag sideways to scroll the deck; tap empty space to
dismiss.

The deck does its own touch handling (a custom carousel) instead of a
ScrollView, so a vertical flick-to-close never fights a horizontal scroll —
the dominant axis of the first move decides pan vs. close.
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
    "parental": ("🔒", "הורים", INDIGO),
}

CARD_W = 232


class _Card(BoxLayout):
    """An app card (header + rounded preview). ``lift`` translates it vertically
    via a canvas matrix so the deck can move it with the finger / animate it
    away without fighting the row layout."""

    lift = NumericProperty(0)

    def __init__(self, name, **kwargs):
        super().__init__(orientation="vertical", size_hint=(None, 1),
                         width=CARD_W, spacing=6, **kwargs)
        self._name = name
        with self.canvas.before:
            PushMatrix()
            self._tr = Translate(0, 0)
        with self.canvas.after:
            PopMatrix()
        self.bind(lift=lambda *_: setattr(self._tr, "y", self.lift))


def _preview(thumb_path, color):
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


def _card(name, thumb_path):
    emoji_g, label, color = _META.get(name, ("📱", name, INDIGO))
    card = _Card(name)
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


class _Deck(FloatLayout):
    """Custom horizontal carousel: pan to scroll, flick a card up to close it."""

    def __init__(self, names, thumbs, on_pick, on_close, on_dismiss, **kwargs):
        super().__init__(**kwargs)
        self._on_pick = on_pick
        self._on_close = on_close
        self._on_dismiss = on_dismiss
        self.row = BoxLayout(orientation="horizontal", size_hint=(None, 1),
                             spacing=16, padding=[20, 0])
        self.row.bind(minimum_width=self.row.setter("width"))
        for n in names:
            self.row.add_widget(_card(n, thumbs.get(n)))
        self.add_widget(self.row)
        self._mode = None
        self._card = None
        self._sx = self._sy = self._rowx0 = 0
        self.bind(size=self._reposition, pos=self._reposition)

    def _reposition(self, *_):
        self.row.y = self.y
        self.row.height = self.height
        self.row.x = self._clampx(self.row.x)

    def _clampx(self, x):
        if self.row.width <= self.width:
            return self.x
        return max(self.x + self.width - self.row.width, min(self.x, x))

    def _card_at(self, touch):
        for c in self.row.children:
            if c.collide_point(*touch.pos):
                return c
        return None

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        self._mode = None
        self._card = self._card_at(touch)
        self._sx, self._sy = touch.x, touch.y
        self._rowx0 = self.row.x
        touch.grab(self)
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return super().on_touch_move(touch)
        dx, dy = touch.x - self._sx, touch.y - self._sy
        if self._mode is None and (abs(dx) > 8 or abs(dy) > 8):
            # dominant axis of the first move decides: sideways pan vs. card flick
            self._mode = "pan" if abs(dx) >= abs(dy) else "lift"
        if self._mode == "pan":
            self.row.x = self._clampx(self._rowx0 + dx)
        elif self._mode == "lift" and self._card is not None:
            self._card.lift = max(0.0, dy)
        return True

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return super().on_touch_up(touch)
        touch.ungrab(self)
        dx, dy = touch.x - self._sx, touch.y - self._sy
        mode, card = self._mode, self._card
        self._mode = self._card = None
        if mode == "lift" and card is not None:
            if dy > 80:                                    # flick up -> close
                anim = Animation(lift=card.height + 80, opacity=0, d=0.18,
                                 t="out_quad")
                anim.bind(on_complete=lambda *_, c=card: self._close(c))
                anim.start(card)
            else:
                Animation(lift=0, d=0.16, t="out_quad").start(card)
        elif mode is None and abs(dx) < 12 and abs(dy) < 12:
            if card is not None:
                self._on_pick(card._name)                  # tap a card -> open
            else:
                self._on_dismiss()                         # tap empty -> dismiss
        return True

    def _close(self, card):
        self.row.remove_widget(card)
        self.row.x = self._clampx(self.row.x)
        self._on_close(card._name)


def build_switcher(order, thumbs, on_pick, on_dismiss, on_close=None,
                   bg_path=None, dock_items=None):
    overlay = FloatLayout()

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

    # Tapping the dimmed background dismisses (the deck handles its own area).
    catch = Button(background_normal="", background_down="",
                   background_color=(0, 0, 0, 0))
    catch.bind(on_release=lambda *_: on_dismiss())
    overlay.add_widget(catch)

    title = Label(text=H("אפליקציות אחרונות"), font_size="17sp", bold=True,
                  color=TEXT, size_hint=(1, None), height=28,
                  pos_hint={"center_x": 0.5, "top": 0.94})
    overlay.add_widget(title)

    deck = _Deck(order, thumbs, on_pick, on_close or (lambda *_: None),
                 on_dismiss, size_hint=(1, None), height=430,
                 pos_hint={"center_x": 0.5, "center_y": 0.54})
    overlay.add_widget(deck)

    if dock_items:
        d = dock(dock_items)
        d.size_hint_x = 0.94
        d.pos_hint = {"center_x": 0.5, "y": 0.015}
        overlay.add_widget(d)

    return overlay
