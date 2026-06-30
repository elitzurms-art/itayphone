"""The Kivy application: wires modem + contacts + history + camera + waydroid
to the screens.

Modem URCs arrive on a background reader thread; Kivy widgets must only be
touched on the main thread, so every modem callback is bounced through
``Clock.schedule_once`` before it updates the UI.

All call actions funnel through ``place_call`` / ``answer_call`` /
``end_call`` so history logging and screen transitions live in one place.
"""

from __future__ import annotations

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager, SlideTransition

from ..contacts import ContactStore
from ..history import CallLog
from ..modem.models import SMS
from .screens.bluetooth import BluetoothScreen
from .screens.call import CallScreen
from .screens.camera import CameraScreen
from .screens.contacts import ContactsScreen
from .screens.dialer import DialerScreen
from .screens.gallery import GalleryScreen
from .screens.home import HomeScreen
from .screens.messages import MessagesScreen
from .screens.recents import RecentsScreen
from .screens.wifi import WifiScreen
from .theme import (BLUE, GREEN, INDIGO, ORANGE, PURPLE, TEAL, H, apply_theme,
                    control_center, home_bar)


class ItayPhoneApp(App):
    def __init__(self, modem, contacts: ContactStore, history: CallLog,
                 camera, waydroid, photos_dir: str = "~/.itayphone/photos",
                 system=None, **kwargs):
        super().__init__(**kwargs)
        self.title = "ItayPhone"
        self.modem = modem
        self.contacts = contacts
        self.history = history
        self.camera = camera
        self.waydroid = waydroid
        self.photos_dir = photos_dir
        if system is None:
            from ..system import build_system
            system = build_system(mock=True)
        self.system = system
        self.sm: ScreenManager | None = None
        self._incoming_rec = None   # in-progress incoming call's history record
        self.android = None         # set on Android: routes calls/SMS to the OS
        # Navigation history for the iPhone-style home-bar app switching.
        self._hist = ["home"]
        self._hist_idx = 0
        self._last_back = 0.0       # time of the last "previous app" swipe
        self._switcher = None       # the app-switcher overlay, when open
        self._thumbs = {}           # screen name -> last snapshot png path

    def build(self):
        apply_theme()
        self.sm = ScreenManager(transition=SlideTransition(duration=0.15))
        for screen in (
            HomeScreen(name="home", app=self),
            DialerScreen(name="dialer", app=self),
            CallScreen(name="call", app=self),
            MessagesScreen(name="messages", app=self),
            ContactsScreen(name="contacts", app=self),
            RecentsScreen(name="recents", app=self),
            CameraScreen(name="camera", app=self),
            GalleryScreen(name="gallery", app=self),
            WifiScreen(name="wifi", app=self),
            BluetoothScreen(name="bluetooth", app=self),
        ):
            self.sm.add_widget(screen)

        self.modem.on_incoming_call = self._on_incoming_call
        self.modem.on_call_connected = self._on_call_connected
        self.modem.on_call_ended = self._on_call_ended
        self.modem.on_new_sms = self._on_new_sms

        Clock.schedule_interval(lambda dt: self._refresh_status(), 10)
        Clock.schedule_once(lambda dt: self._refresh_status(), 0.5)
        Clock.schedule_once(lambda dt: self.refresh_badges(), 0.5)
        # Round the actual OS window (real transparent corners) on Windows.
        Clock.schedule_once(lambda dt: self._round_window(), 0.6)

        # The screen manager fills the whole window (content reaches the bottom
        # edge — no docked bar). The home indicator is added later as a thin
        # transparent overlay so nothing reads as a black bar at the bottom.
        app_box = BoxLayout(orientation="vertical", spacing=0)
        app_box.add_widget(self.sm)

        # Control Center: swipe down from the top edge for quick actions.
        from kivy.uix.floatlayout import FloatLayout
        root = FloatLayout()
        root.add_widget(app_box)
        # (glyph, label, callback, is_on) — is_on is a state getter for toggle
        # tiles (they light up blue when active) or None for action tiles.
        self.cc = control_center([
            ("📸", "צילום מסך", self.take_screenshot, None),
            ("✈️", "טיסה", self._toggle_airplane, lambda: self._airplane),
            ("🔦", "פנס", self._toggle_flash, lambda: self._flash),
            ("📶", "Wi-Fi", lambda: self.go("wifi"), None),
            ("🔵", "בלוטות'", lambda: self.go("bluetooth"), None),
            ("🔋", "חיסכון סוללה", self._toggle_battery,
             lambda: self._battery_saver),
            ("🌙", "תאורת לילה", self._toggle_night, lambda: self._night),
        ])
        root.add_widget(self.cc)

        # Full-screen tint overlays, ABOVE everything so they darken the whole
        # UI (status bar + Control Center included). Plain Widgets that draw a
        # translucent rectangle and never consume touches, so the app stays
        # interactive underneath. Opacity is animated 0<->1 by the toggles.
        self._night_tint = self._tint_overlay((0.15, 0.07, 0.0))   # warm + dark
        self._batt_tint = self._tint_overlay((0.0, 0.0, 0.0))       # neutral dim
        root.add_widget(self._night_tint)
        root.add_widget(self._batt_tint)

        # Phone look: black rounded corners + punch-hole camera, on top of all.
        from .theme import device_frame
        root.add_widget(device_frame())

        # iPhone-style gesture home indicator (thin transparent pill) floating
        # over the very bottom of every screen — replaces the old bar.
        root.add_widget(home_bar(
            on_home=self.go_home,
            on_recents=self.open_app_switcher,
            on_prev=self.nav_prev_app,
            on_next=self.nav_next_app,
        ))

        self._root = root
        self._airplane = False
        self._flash = False
        self._wifi = True
        self._bt = False
        self._battery_saver = False
        self._night = False
        self._normal_transition = self.sm.transition.duration
        return root

    def _tint_overlay(self, rgb):
        """A touch-transparent full-screen tint at *rgb*; opacity starts at 0."""
        from kivy.graphics import Color, Rectangle
        from kivy.uix.widget import Widget

        w = Widget(opacity=0)
        with w.canvas:
            Color(rgb[0], rgb[1], rgb[2], 0.42)
            rect = Rectangle(pos=w.pos, size=w.size)
        w.bind(pos=lambda *_: setattr(rect, "pos", w.pos),
               size=lambda *_: setattr(rect, "size", w.size))
        return w

    def go(self, screen_name: str) -> None:
        if not self.sm:
            return
        # Record forward navigation in history (drop any "forward" entries),
        # snapshotting the screen we're leaving for the app-switcher preview.
        if screen_name != self.sm.current:
            self._capture_thumb(self.sm.current)
            del self._hist[self._hist_idx + 1:]
            self._hist.append(screen_name)
            self._hist_idx = len(self._hist) - 1
        self.sm.transition.direction = "left"
        self.sm.current = screen_name

    def _capture_thumb(self, name: str) -> None:
        """Snapshot screen *name* to a png for the app-switcher preview."""
        import os
        try:
            d = os.path.expanduser("~/.itayphone/cache")
            os.makedirs(d, exist_ok=True)
            path = os.path.join(d, f"thumb_{name}.png")
            self.sm.get_screen(name).export_to_png(path)
            self._thumbs[name] = path
        except Exception:
            pass

    def _blurred_bg(self) -> str | None:
        """The current screen, blurred + dimmed, as a backdrop for the switcher."""
        import os
        src = self._thumbs.get(self.sm.current)
        if not src:
            return None
        try:
            from PIL import Image as PImage, ImageEnhance, ImageFilter
            out = os.path.join(os.path.dirname(src), "switcher_bg.png")
            im = PImage.open(src).convert("RGB")
            # Blur a downscaled copy — far cheaper and visually identical once
            # it's stretched back up, so the switcher opens without a hitch.
            w, h = im.size
            small = im.resize((max(1, w // 4), max(1, h // 4)))
            small = small.filter(ImageFilter.GaussianBlur(6))
            small = ImageEnhance.Brightness(small).enhance(0.5)
            small.save(out)
            return out
        except Exception:
            return None

    # -- iPhone-style home-bar app switching -------------------------------
    def nav_prev_app(self) -> None:
        """Swipe right on the home bar: go to the previous app."""
        import time
        if self._switcher is not None:
            return
        if self._hist_idx > 0:
            self._hist_idx -= 1
            self._last_back = time.time()
            self.sm.transition.direction = "right"
            self.sm.current = self._hist[self._hist_idx]

    def nav_next_app(self) -> None:
        """Swipe left: reverse a recent right-swipe (forward), else nothing."""
        import time
        if self._switcher is not None:
            return
        if time.time() - self._last_back < 10 and \
                self._hist_idx < len(self._hist) - 1:
            self._hist_idx += 1
            self.sm.transition.direction = "left"
            self.sm.current = self._hist[self._hist_idx]

    def go_home(self) -> None:
        self._close_switcher()
        self.go("home")

    def open_app_switcher(self) -> None:
        """Slow swipe up: a horizontal deck of recent apps (iPhone-like)."""
        if self._switcher is not None:
            return
        from .screens.switcher import build_switcher
        self._capture_thumb(self.sm.current)   # fresh preview of where we are
        bg = self._blurred_bg()
        # Recent apps, newest first — excluding Home (it's a swipe away) and the
        # transient call screen.
        seen, order = set(), []
        for name in reversed(self._hist):
            if name not in seen and name not in ("call", "home"):
                seen.add(name)
                order.append(name)

        def pick(name):
            self._close_switcher()
            self.go(name)

        def dock_go(name):
            self._close_switcher()
            self.go(name)

        def dock_chrome():
            self._close_switcher()
            self.waydroid.launch("com.android.chrome")

        # The same four apps as the home-screen dock.
        dock_items = [
            ("📞", GREEN, lambda: dock_go("dialer")),
            ("💬", BLUE, lambda: dock_go("messages")),
            ("📷", TEAL, lambda: dock_go("camera")),
            ("🌐", ORANGE, dock_chrome),
        ]
        self._switcher = build_switcher(order, self._thumbs, pick,
                                        self._close_switcher,
                                        on_close=self._switcher_close,
                                        bg_path=bg, dock_items=dock_items)
        # Smooth fade + slight rise-in instead of popping in abruptly.
        from kivy.animation import Animation
        self._switcher.opacity = 0
        self._root.add_widget(self._switcher)
        Animation(opacity=1, d=0.16, t="out_quad").start(self._switcher)

    def _switcher_close(self, name, card) -> None:
        """Flick-up to close an app: drop it from recents + remove its card."""
        self._hist = [n for n in self._hist if n != name]
        if not self._hist:
            self._hist = ["home"]
        self._hist_idx = min(self._hist_idx, len(self._hist) - 1)
        self._thumbs.pop(name, None)
        if card.parent is not None:
            card.parent.remove_widget(card)

    def _close_switcher(self, *_) -> None:
        if self._switcher is not None:
            self._root.remove_widget(self._switcher)
            self._switcher = None

    def _round_window(self) -> None:
        """Give the borderless window real rounded corners on Windows by
        clipping its shape (SetWindowRgn). No-op elsewhere."""
        import sys
        if sys.platform != "win32":
            return
        try:
            import ctypes
            from ctypes import wintypes

            from kivy.core.window import Window
            # Kivy's own HWND. (FindWindowW/GetForegroundWindow grabbed the WRONG
            # window — VS Code etc. — so the region clipped nothing useful and
            # the phone window's top looked cut.)
            info = Window.get_window_info()
            hwnd = getattr(info, "window", None)
            if not hwnd:
                return
            user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
            # Physical client-area pixels (differs from Window.width under DPI).
            rect = wintypes.RECT()
            user32.GetClientRect(hwnd, ctypes.byref(rect))
            w = rect.right - rect.left
            h = rect.bottom - rect.top
            if w < 10 or h < 10:
                return
            radius = max(16, round(w * 22 / 360))  # ~22 logical px, DPI-scaled
            rgn = gdi32.CreateRoundRectRgn(0, 0, w + 1, h + 1,
                                           radius * 2, radius * 2)
            user32.SetWindowRgn(hwnd, rgn, True)
        except Exception:
            pass

    # -- Control Center actions -------------------------------------------
    def take_screenshot(self) -> None:
        import os
        from datetime import datetime

        out_dir = os.path.expanduser("~/.itayphone/screenshots")
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(
            out_dir, datetime.now().strftime("shot_%Y%m%d_%H%M%S.png"))

        # Capture after the Control Center has finished sliding away.
        def _cap(_dt):
            self.sm.export_to_png(path)
            self._toast(f"צילום מסך נשמר:\n{os.path.basename(path)}")
        Clock.schedule_once(_cap, 0.35)

    def _refresh_all(self) -> None:
        self._refresh_status()
        self.refresh_badges()
        self._toast("רוענן")

    def _toggle_airplane(self) -> None:
        self._airplane = not self._airplane
        self._toast("מצב טיסה פעיל" if self._airplane else "מצב טיסה כבוי")

    def _toggle_flash(self) -> None:
        self._flash = not self._flash
        if hasattr(self.system, "set_flashlight"):   # real torch on Android
            self.system.set_flashlight(self._flash)
        self._toast("פנס דולק" if self._flash else "פנס כבוי")

    def _toggle_night(self) -> None:
        self._night = not self._night
        self._fade(self._night_tint, self._night)
        self._toast("תאורת לילה פעילה" if self._night else "תאורת לילה כבויה")

    def _toggle_battery(self) -> None:
        self._battery_saver = not self._battery_saver
        on = self._battery_saver
        # Dim the screen, slow the screen transitions, and throttle the frame
        # rate — a lower FPS genuinely draws less power and makes motion calmer.
        self._fade(self._batt_tint, on)
        self.sm.transition.duration = 0.5 if on else self._normal_transition
        self._set_fps(15 if on else 60)
        self._toast("חיסכון בסוללה פעיל" if on else "חיסכון בסוללה כבוי")

    def _fade(self, widget, on: bool) -> None:
        from kivy.animation import Animation
        Animation.cancel_all(widget, "opacity")
        Animation(opacity=1 if on else 0, d=0.3, t="out_quad").start(widget)

    def _set_fps(self, fps: int) -> None:
        from kivy.clock import Clock as _Clock
        try:
            _Clock._max_fps = float(fps)
        except Exception:
            pass

    def _toast(self, text: str) -> None:
        """Brief frosted message near the bottom, auto-dismissed."""
        from kivy.graphics import Color, RoundedRectangle
        from kivy.uix.label import Label

        lbl = Label(text=H(text), markup=False, halign="center",
                    valign="middle", color=(1, 1, 1, 1), font_size="15sp",
                    size_hint=(None, None), size=(280, 64),
                    pos_hint={"center_x": 0.5, "y": 0.12})
        lbl.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
        with lbl.canvas.before:
            Color(0.05, 0.06, 0.09, 0.92)
            r = RoundedRectangle(pos=lbl.pos, size=lbl.size, radius=[18])
        lbl.bind(pos=lambda *_: setattr(r, "pos", lbl.pos),
                 size=lambda *_: setattr(r, "size", lbl.size))
        self._root.add_widget(lbl)

        from kivy.animation import Animation
        anim = Animation(opacity=1, d=0.15) + Animation(opacity=1, d=1.4) \
            + Animation(opacity=0, d=0.4)
        anim.bind(on_complete=lambda *a: self._root.remove_widget(lbl))
        anim.start(lbl)

    # -- call actions (single place that logs + drives the call screen) ----
    def place_call(self, number: str) -> None:
        self.history.add(number, "out", answered=True)
        self.refresh_badges()
        if self.android is not None:        # let the OS phone app place the call
            self.android.call(number)
            return
        self.modem.dial(number)
        self._show_call(self.contacts.display_name(number), "מחייג…")

    def answer_call(self) -> None:
        self.modem.answer()
        if self._incoming_rec is not None:
            self._incoming_rec.answered = True
            self.history.save()
            self._incoming_rec = None
        name = self.contacts.display_name(
            self.sm.get_screen("dialer")._active_number)
        self._show_call(name, "מתחבר…")
        self.sm.get_screen("call").set_active()
        self.refresh_badges()

    def end_call(self) -> None:
        self.modem.hangup()
        self._incoming_rec = None
        self.sm.get_screen("call").stop()
        Clock.schedule_once(lambda dt: self.go("home"), 0.6)

    def dial_from_ui(self, number: str) -> None:
        self.go("dialer")
        self.sm.get_screen("dialer").dial_number(number)

    def compose_to(self, number: str) -> None:
        self.sm.get_screen("messages").prefill(number)
        self.go("messages")

    def _show_call(self, name: str, status: str) -> None:
        self.sm.get_screen("call").start(name, status)
        self.go("call")

    # -- modem callbacks (always re-dispatched to the main thread) ---------
    def _on_incoming_call(self, number: str) -> None:
        Clock.schedule_once(lambda dt: self._show_incoming(number))

    def _on_call_connected(self) -> None:
        Clock.schedule_once(lambda dt: self.sm.get_screen("call").set_active())

    def _on_call_ended(self) -> None:
        Clock.schedule_once(lambda dt: self._show_call_ended())

    def _on_new_sms(self, sms: SMS) -> None:
        Clock.schedule_once(lambda dt: self._show_new_sms(sms))

    # -- UI reactions ------------------------------------------------------
    def _show_incoming(self, number: str) -> None:
        # Log as missed up front; answer_call() flips it to answered.
        self._incoming_rec = self.history.add(number, "in", answered=False)
        name = self.contacts.display_name(number)
        self.sm.get_screen("dialer").show_incoming(name, number)
        self.go("dialer")
        self.refresh_badges()

    def _show_call_ended(self) -> None:
        self.sm.get_screen("call").stop()
        self.sm.get_screen("dialer").show_idle()
        self._incoming_rec = None
        Clock.schedule_once(lambda dt: self.go("home"), 0.6)
        self.refresh_badges()

    def _show_new_sms(self, sms: SMS) -> None:
        self.sm.get_screen("messages").add_message(sms)
        self.refresh_badges()

    def _refresh_status(self) -> None:
        status = self.modem.network_status()
        self.sm.get_screen("home").update_status(status)

    def refresh_badges(self) -> None:
        try:
            unread = len(self.modem.list_sms("REC UNREAD"))
        except Exception:
            unread = 0
        missed = self.history.missed_unseen()
        self.sm.get_screen("home").update_badges(unread, missed)
