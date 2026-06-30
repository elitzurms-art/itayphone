"""Messages screen: list received SMS, compose and send (chat-bubble style)."""

from __future__ import annotations

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen
from kivy.uix.textinput import TextInput

from ...modem.models import SMS
from ..theme import (BLUE, MUTED, SURFACE_HI, TEXT, SYM, H, gradient_bg,
                     top_bar)


class MessagesScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        gradient_bg(self)

        root = BoxLayout(orientation="vertical")
        root.add_widget(top_bar("הודעות", lambda: self.app.go("home")))

        scroll = ScrollView()
        self.list = BoxLayout(orientation="vertical", size_hint_y=None, spacing=8,
                              padding=10)
        self.list.bind(minimum_height=self.list.setter("height"))
        scroll.add_widget(self.list)
        root.add_widget(scroll)

        compose = BoxLayout(size_hint_y=None, height=64, spacing=6,
                            padding=[8, 6])
        self.to = TextInput(hint_text=H("מספר"), size_hint_x=0.3, multiline=False)
        self.body = TextInput(hint_text=H("הודעה"), multiline=False)
        # RTL send: arrow points left (toward the start of the line).
        send = Button(text="◀", size_hint_x=0.18, font_name=SYM,
                      font_size="20sp", background_color=BLUE)
        send.bind(on_release=lambda *_: self._send())
        # RTL: recipient on the right, send button on the left.
        compose.add_widget(send)
        compose.add_widget(self.body)
        compose.add_widget(self.to)
        root.add_widget(compose)

        self.add_widget(root)

    def on_pre_enter(self, *args):
        self.reload()

    def prefill(self, number: str) -> None:
        """Pre-fill the recipient field (used when composing from contacts)."""
        self.to.text = number
        self.body.text = ""

    def reload(self) -> None:
        self.list.clear_widgets()
        msgs = self.app.modem.list_sms()
        if not msgs:
            empty = Label(text=H("אין הודעות"), color=MUTED, size_hint_y=None,
                          height=60)
            self.list.add_widget(empty)
            return
        for sms in msgs:
            self.add_message(sms)

    def add_message(self, sms: SMS) -> None:
        who = self.app.contacts.display_name(sms.sender)
        bubble = BoxLayout(orientation="vertical", size_hint_y=None, height=82,
                           padding=[16, 10], spacing=2)
        from kivy.graphics import Color, RoundedRectangle
        with bubble.canvas.before:
            Color(*SURFACE_HI)
            r = RoundedRectangle(pos=bubble.pos, size=bubble.size, radius=[18])
        bubble.bind(pos=lambda *_: setattr(r, "pos", bubble.pos),
                    size=lambda *_: setattr(r, "size", bubble.size))

        name = Label(text=H(who), bold=True, color=BLUE, halign="right",
                     valign="middle", size_hint_y=0.42, font_size="15sp")
        name.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
        body = Label(text=H(sms.text), color=TEXT, halign="right",
                     valign="top", size_hint_y=0.58, font_size="16sp")
        body.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
        bubble.add_widget(name)
        bubble.add_widget(body)
        self.list.add_widget(bubble)

    def _send(self) -> None:
        number, text = self.to.text.strip(), self.body.text.strip()
        if number and text:
            self.app.modem.send_sms(number, text)
            self.body.text = ""
