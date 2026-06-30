"""Dialer screen: keypad + place call + incoming-call (ringing) view.

Styled after the stock Android dialer: black background, label-only keys (big
digit + small letters, no key background), a round green call button, and a
bottom tab row (Keypad / Recents / Contacts).

Once a call is placed or answered the app switches to the dedicated CallScreen;
this screen only handles dialling and the ringing state. Call actions go through
the app so history logging lives in one place.
"""

from __future__ import annotations

from kivy.graphics import Color, Ellipse, Rectangle
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from ..theme import GREEN, SYM, H, emoji_image

# Keypad: digit + its letters, like a real phone keypad.
_KEYS = [
    ("1", ""), ("2", "ABC"), ("3", "DEF"),
    ("4", "GHI"), ("5", "JKL"), ("6", "MNO"),
    ("7", "PQRS"), ("8", "TUV"), ("9", "WXYZ"),
    ("*", ""), ("0", "+"), ("#", ""),
]

GREY = (0.62, 0.64, 0.68, 1)
WHITE = (0.96, 0.96, 0.98, 1)


class _Key(ButtonBehavior, Label):
    """A transparent, tappable keypad key (no Button background)."""


class _Tab(ButtonBehavior, Label):
    """A transparent bottom-tab button."""


class _Circle(ButtonBehavior, Widget):
    """A round, coloured, tappable button (the call action)."""

    def __init__(self, color=GREEN, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*color)
            self._e = Ellipse(pos=self.pos, size=self.size)
        self.bind(pos=lambda *_: setattr(self._e, "pos", self.pos),
                  size=lambda *_: setattr(self._e, "size", self.size))


class DialerScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._active_number = ""

        # Solid black background (stock-Android dialer look).
        with self.canvas.before:
            Color(0, 0, 0, 1)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *_: setattr(self._bg, "pos", self.pos),
                  size=lambda *_: setattr(self._bg, "size", self.size))

        # Top padding = safe area below the camera punch-hole / rounded corners.
        root = BoxLayout(orientation="vertical", padding=[0, 40, 0, 6])

        # -- header: "טלפון" on the right, ⋮ on the left (RTL) -----------------
        header = BoxLayout(size_hint_y=None, height=50, padding=[18, 2])
        menu = Label(text="⋮", font_name=SYM, font_size="24sp", color=WHITE,
                     size_hint_x=None, width=40)
        title = Label(text=H("טלפון"), bold=True, font_size="22sp", color=WHITE,
                      halign="right", valign="middle")
        title.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
        header.add_widget(menu)
        header.add_widget(title)
        root.add_widget(header)

        # -- dialled number + backspace --------------------------------------
        disp_row = BoxLayout(size_hint_y=None, height=70, padding=[18, 0])
        self.del_btn = _Key(text="⌫", font_name=SYM, font_size="26sp",
                            color=WHITE, size_hint_x=None, width=54, opacity=0)
        self.del_btn.bind(on_release=lambda *_: self._backspace())
        self.display = Label(text="", font_size="34sp", bold=True, color=WHITE,
                             halign="center", valign="middle")
        self.display.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
        disp_row.add_widget(self.del_btn)
        disp_row.add_widget(self.display)
        root.add_widget(disp_row)

        # -- keypad (transparent label keys) ---------------------------------
        keypad = GridLayout(cols=3, padding=[26, 0, 26, 0], spacing=[0, 2])
        for digit, letters in _KEYS:
            txt = f"[size=33sp][b]{digit}[/b][/size]"
            if letters:
                txt += f"\n[size=11sp][color=9aa0ab]{letters}[/color][/size]"
            k = _Key(text=txt, markup=True, halign="center", valign="middle",
                     color=WHITE)
            k.bind(on_release=lambda _, d=digit: self._press(d))
            keypad.add_widget(k)
        root.add_widget(keypad)

        # -- round green call button -----------------------------------------
        call_area = FloatLayout(size_hint_y=None, height=98)
        self.call_btn = _Circle(size_hint=(None, None), size=(66, 66),
                                pos_hint={"center_x": 0.5, "center_y": 0.55})
        icon = emoji_image("📞")
        icon.size_hint = (None, None)
        icon.size = (34, 34)
        icon.pos_hint = {"center_x": 0.5, "center_y": 0.55}
        call_area.add_widget(self.call_btn)
        call_area.add_widget(icon)
        root.add_widget(call_area)

        # -- bottom tabs ------------------------------------------------------
        tabs = BoxLayout(size_hint_y=None, height=50)
        contacts = _Tab(text=H("אנשי קשר"), color=GREY, font_size="14sp")
        contacts.bind(on_release=lambda *_: self.app.go("contacts"))
        recents = _Tab(text=H("אחרונות"), color=GREY, font_size="14sp")
        recents.bind(on_release=lambda *_: self.app.go("recents"))
        self.tab_keypad = _Tab(text=H("מקשים"), color=WHITE, bold=True,
                               font_size="14sp")
        # RTL: Keypad (active) on the right.
        tabs.add_widget(contacts)
        tabs.add_widget(recents)
        tabs.add_widget(self.tab_keypad)
        root.add_widget(tabs)

        self.add_widget(root)
        self.show_idle()

    # -- keypad ------------------------------------------------------------
    def _press(self, key: str) -> None:
        self.display.text += key
        self.del_btn.opacity = 1

    def _backspace(self) -> None:
        self.display.text = self.display.text[:-1]
        if not self.display.text:
            self.del_btn.opacity = 0

    # -- entry points ------------------------------------------------------
    def dial_number(self, number: str) -> None:
        """Called by the app to place a call (e.g. from contacts/recents)."""
        self.display.text = number
        self._call()

    def _call(self) -> None:
        number = self.display.text.strip()
        if number:
            self.app.place_call(number)

    # -- button states -----------------------------------------------------
    def _rebind(self, handler) -> None:
        self.call_btn.unbind(on_release=self._h_call)
        self.call_btn.unbind(on_release=self._h_answer)
        self.call_btn.bind(on_release=handler)

    def _h_call(self, *_):
        self._call()

    def _h_answer(self, *_):
        self.app.answer_call()

    def show_incoming(self, name: str, number: str) -> None:
        self._active_number = number
        self.display.text = H("שיחה נכנסת") + "\n" + H(name)
        self.del_btn.opacity = 0
        self._rebind(self._h_answer)

    def show_idle(self) -> None:
        self._active_number = ""
        self.display.text = ""
        self.del_btn.opacity = 0
        self._rebind(self._h_call)
