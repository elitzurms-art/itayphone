"""Global theme for ItayPhone — Hebrew (RTL) + Android-style (Material) look.

Three jobs:

* **Hebrew text** — Kivy's SDL2 text backend renders glyphs in *logical* order
  and does no bidi, so Hebrew comes out reversed. :func:`H` runs the unicode
  bidi algorithm (``python-bidi``) to produce *visual* order, and we register a
  Hebrew-capable font as the default. Wrap every user-facing string in ``H(...)``.
* **Palette + Kivy rules** — :func:`apply_theme` loads class rules that restyle
  every Button / Label / TextInput app-wide (flat rounded Material surfaces).
* **Reusable widgets** — :func:`top_bar` (Material app bar) and :class:`AppTile`
  (launcher squircle icon) so the screens stay short.
"""

from __future__ import annotations

import os

from bidi.algorithm import get_display

# A Hebrew + symbol capable font bundled inside the package, so Android (which
# has none of the Windows/Pi font paths below) still renders Hebrew correctly.
_BUNDLED_REG = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            "assets", "fonts", "DejaVuSans.ttf")
_BUNDLED_BOLD = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                             "assets", "fonts", "DejaVuSans-Bold.ttf")

# --- palette (Material 3 / Pixel dark) -------------------------------------
BG_TOP = (0.05, 0.06, 0.11)        # wallpaper gradient (top)
BG_BOTTOM = (0.02, 0.02, 0.05)     # wallpaper gradient (bottom)
BG = (0.04, 0.05, 0.08, 1)         # flat window background fallback
SURFACE = (0.13, 0.15, 0.20, 1)    # cards / default button surface
SURFACE_HI = (0.18, 0.21, 0.27, 1) # raised surface (keypad keys, list rows)
TEXT = (0.94, 0.95, 0.97, 1)
MUTED = (0.62, 0.66, 0.73, 1)

# Accent colours for launcher tiles / actions.
GREEN = (0.18, 0.69, 0.40, 1)
RED = (0.90, 0.30, 0.34, 1)
BLUE = (0.23, 0.55, 0.96, 1)
PURPLE = (0.58, 0.42, 0.92, 1)
ORANGE = (0.97, 0.57, 0.22, 1)
TEAL = (0.10, 0.67, 0.63, 1)
INDIGO = (0.38, 0.47, 0.93, 1)
PRIMARY = BLUE

# Candidate Hebrew-capable fonts: Windows (dev) first, then Raspberry Pi OS,
# then the bundled font + Android system fonts (for the packaged APK).
_FONT_CANDIDATES = [
    (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\segoeuib.ttf"),
    (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/truetype/noto/NotoSansHebrew-Regular.ttf", None),
    (_BUNDLED_REG, _BUNDLED_BOLD),
    ("/system/fonts/NotoSansHebrew-Regular.ttf", None),
]

FONT = "Heb"      # default text font (Hebrew-capable)
EMOJI = "Emoji"   # colour-emoji font for app icons (📞 💬 …)
SYM = "Sym"       # monochrome symbol font for UI glyphs (⌫ ➤ …)

# Candidate emoji/symbol fonts: colour emoji first, then monochrome symbols,
# then the Linux/Noto fallbacks for the Raspberry Pi.
_EMOJI_CANDIDATES = [
    r"C:\Windows\Fonts\seguiemj.ttf",   # Segoe UI Emoji (colour)
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
    "/system/fonts/NotoColorEmoji.ttf",                 # Android colour emoji
    "/usr/share/fonts/truetype/ancient-scripts/Symbola_hint.ttf",
]

# Monochrome symbol font: glyphs like ⌫ ➤ that the colour-emoji font lacks.
_SYM_CANDIDATES = [
    r"C:\Windows\Fonts\seguisym.ttf",   # Segoe UI Symbol
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    _BUNDLED_REG,                                        # bundled (Android)
    "/usr/share/fonts/truetype/ancient-scripts/Symbola_hint.ttf",
]


def H(text: str) -> str:
    """Return *text* reordered for visual (RTL) display, line by line.

    Apply to any string containing Hebrew before handing it to a Kivy widget.
    Markup strings must NOT be passed through here (the bidi pass would scramble
    the tags) — build those from already-``H``'d pieces instead.
    """
    return "\n".join(get_display(line) for line in text.split("\n"))


def emoji(glyph: str) -> str:
    """Wrap *glyph* so it renders with the emoji font inside a markup label."""
    return f"[font={EMOJI}]{glyph}[/font]"


def mixed(glyph: str, hebrew: str) -> str:
    """Hebrew caption for a button (the emoji glyph is dropped).

    Inline colour-emoji can't be scaled by the text backend on Linux (bitmap
    font), so action buttons use Hebrew text + colour instead. Kept as a helper
    so call sites stay tidy; *glyph* is ignored.
    """
    return H(hebrew)


def _register_font() -> None:
    import os

    from kivy.core.text import LabelBase

    for regular, bold in _FONT_CANDIDATES:
        if os.path.exists(regular):
            kw = {"fn_regular": regular}
            if bold and os.path.exists(bold):
                kw["fn_bold"] = bold
            LabelBase.register(name=FONT, **kw)
            # Make it the default so widgets that don't set font_name get Hebrew.
            LabelBase.register(name="Roboto", **kw)
            break

    global _EMOJI_FILE
    for emoji_font in _EMOJI_CANDIDATES:
        if os.path.exists(emoji_font):
            LabelBase.register(name=EMOJI, fn_regular=emoji_font)
            _EMOJI_FILE = emoji_font
            break

    for sym in _SYM_CANDIDATES:
        if os.path.exists(sym):
            LabelBase.register(name=SYM, fn_regular=sym)
            return


# Resolved emoji font file (for Pillow rendering). Set by _register_font.
_EMOJI_FILE = None
_EMOJI_TEX_CACHE = {}


def _emoji_texture(glyph: str):
    """Render *glyph* to an RGBA Kivy texture via Pillow, cached.

    Kivy's SDL2 text backend can't scale bitmap colour-emoji fonts (Noto Color
    Emoji on Linux renders at a fixed ~109px strike, blowing up the layout).
    Pillow renders the glyph to a real image we can scale freely. Vector emoji
    fonts (Segoe UI Emoji on Windows) load at any size directly.
    """
    if glyph in _EMOJI_TEX_CACHE:
        return _EMOJI_TEX_CACHE[glyph]
    import io

    from kivy.core.image import Image as CoreImage
    from PIL import Image as PImage, ImageDraw, ImageFont

    target = 96
    try:
        font = ImageFont.truetype(_EMOJI_FILE, target)
        render = target
    except OSError:
        render = 109                      # nearest bitmap strike (Noto)
        font = ImageFont.truetype(_EMOJI_FILE, render)
    img = PImage.new("RGBA", (render, render), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((render / 2, render / 2), glyph, font=font,
                             anchor="mm", embedded_color=True)
    if render != target:
        img = img.resize((target, target), PImage.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="png")
    buf.seek(0)
    tex = CoreImage(buf, ext="png").texture
    _EMOJI_TEX_CACHE[glyph] = tex
    return tex


def emoji_image(glyph: str):
    """A Kivy Image of *glyph*, scalable to any widget size (color emoji)."""
    from kivy.uix.image import Image

    return Image(texture=_emoji_texture(glyph), fit_mode="contain")


_MONO_TEX_CACHE = {}


def _mono_texture(glyph: str, rgb):
    """Render *glyph* as a flat single-colour silhouette (a monochrome icon).

    Uses the colour-emoji glyph's *shape* (its alpha channel) but throws away
    its colours, painting the whole shape in *rgb*. Turns any emoji into a clean
    black-and-white-style icon for the quick-settings tiles.
    """
    key = (glyph, rgb)
    if key in _MONO_TEX_CACHE:
        return _MONO_TEX_CACHE[key]
    import io

    from kivy.core.image import Image as CoreImage
    from PIL import Image as PImage, ImageDraw, ImageFont

    target = 96
    try:
        font = ImageFont.truetype(_EMOJI_FILE, target)
        render = target
    except OSError:
        render = 109
        font = ImageFont.truetype(_EMOJI_FILE, render)
    base = PImage.new("RGBA", (render, render), (0, 0, 0, 0))
    ImageDraw.Draw(base).text((render / 2, render / 2), glyph, font=font,
                              anchor="mm", embedded_color=True)
    alpha = base.split()[3]
    r, g, b = (int(c * 255) for c in rgb[:3])
    solid = PImage.new("RGBA", base.size, (r, g, b, 0))
    solid.putalpha(alpha)
    if render != target:
        solid = solid.resize((target, target), PImage.LANCZOS)
    buf = io.BytesIO()
    solid.save(buf, format="png")
    buf.seek(0)
    tex = CoreImage(buf, ext="png").texture
    _MONO_TEX_CACHE[key] = tex
    return tex


def mono_icon_image(glyph: str, rgb=(1, 1, 1)):
    """A Kivy Image of *glyph* as a flat *rgb* silhouette (monochrome icon)."""
    from kivy.uix.image import Image

    return Image(texture=_mono_texture(glyph, rgb), fit_mode="contain")


def device_frame(cam_r=13, cam_top=13):
    """A top overlay drawing only a punch-hole camera dot at the top centre.

    The rounded corners are NOT drawn here: on Windows the window itself is
    clipped to a rounded shape (real transparent corners), and we don't want
    opaque black corners on Linux. Touch-transparent (a plain Widget with no
    children), so it never blocks the UI underneath.
    """
    from kivy.core.window import Window
    from kivy.graphics import Color, Rectangle
    from kivy.uix.widget import Widget

    frame = Widget(size_hint=(None, None))

    def _render(*_):
        import io

        from kivy.core.image import Image as CoreImage
        from PIL import Image as PImage, ImageDraw
        w, h = int(Window.width), int(Window.height)
        if w < 10 or h < 10:
            return
        # Fully transparent, with just the black punch-hole camera at the top.
        img = PImage.new("RGBA", (w, h), (0, 0, 0, 0))
        cx = w // 2
        ImageDraw.Draw(img).ellipse(
            [cx - cam_r, cam_top, cx + cam_r, cam_top + 2 * cam_r],
            fill=(0, 0, 0, 255))
        buf = io.BytesIO()
        img.save(buf, "png")
        buf.seek(0)
        tex = CoreImage(buf, ext="png").texture
        frame.canvas.clear()
        with frame.canvas:
            Color(1, 1, 1, 1)
            Rectangle(texture=tex, pos=(0, 0), size=(w, h))
        frame.size = (w, h)
        frame.pos = (0, 0)

    Window.bind(size=lambda *_: _render())
    _render()
    return frame


def _vgrad_texture(top, bottom, h: int = 256):
    """A 1×h vertical gradient texture from *top* to *bottom* rgb."""
    from kivy.graphics.texture import Texture

    tex = Texture.create(size=(1, h), colorfmt="rgba")
    buf = bytearray()
    for i in range(h):
        t = i / (h - 1)
        for c in range(3):
            buf.append(int((top[c] * (1 - t) + bottom[c] * t) * 255))
        buf.append(255)
    tex.blit_buffer(bytes(buf), colorfmt="rgba", bufferfmt="ubyte")
    tex.wrap = "clamp_to_edge"
    return tex


def gradient_bg(widget, top=BG_TOP, bottom=BG_BOTTOM) -> None:
    """Paint a vertical wallpaper gradient behind *widget* (tracks resize)."""
    from kivy.graphics import Color, Rectangle

    tex = _vgrad_texture(top, bottom)
    with widget.canvas.before:
        Color(1, 1, 1, 1)
        rect = Rectangle(pos=widget.pos, size=widget.size, texture=tex)

    def _sync(*_):
        rect.pos = widget.pos
        rect.size = widget.size

    widget.bind(pos=_sync, size=_sync)


_KV = """
<Button>:
    background_normal: ''
    background_down: ''
    background_color: 0, 0, 0, 0
    color: 0.96, 0.96, 0.98, 1
    font_name: 'Heb'
    font_size: '19sp'
    canvas.before:
        Color:
            rgba: ((0.13, 0.15, 0.20, 1) if self.background_color[:3] == [0, 0, 0] else self.background_color) if self.state == 'normal' else (0.09, 0.10, 0.13, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [22,]

<Label>:
    color: 0.93, 0.94, 0.97, 1
    font_name: 'Heb'

<TextInput>:
    background_normal: ''
    background_active: ''
    background_color: 0.13, 0.15, 0.20, 1
    foreground_color: 0.95, 0.95, 0.97, 1
    cursor_color: 0.23, 0.55, 0.96, 1
    hint_text_color: 0.5, 0.54, 0.6, 1
    font_name: 'Heb'
    font_size: '17sp'
    padding: [14, 14, 14, 14]
"""


def apply_theme() -> None:
    from kivy.core.window import Window
    from kivy.lang import Builder

    _register_font()
    Window.clearcolor = BG
    Builder.load_string(_KV)


# --- reusable Android-style widgets ----------------------------------------
def top_bar(title: str, on_back) -> "object":
    """A Material top app bar: centred Hebrew *title* + a back arrow (RTL).

    In a right-to-left UI the "up/back" affordance sits on the right and points
    right, so the arrow lives on the right edge of the bar.
    """
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button
    from kivy.uix.label import Label
    from kivy.uix.widget import Widget

    # Title is right-aligned (RTL) so the centred camera punch-hole never sits on
    # it; the tall top padding keeps the row clear of the rounded corners.
    bar = BoxLayout(size_hint_y=None, height=92, padding=[12, 40, 14, 6],
                    spacing=6)
    back = Button(text="→", size_hint_x=None, width=46, font_size="26sp",
                  background_color=SURFACE_HI)
    back.bind(on_release=lambda *_: on_back())
    bar.add_widget(back)
    lbl = Label(text=H(title), font_size="21sp", bold=True, halign="right",
                valign="middle")
    lbl.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
    bar.add_widget(lbl)
    return bar


class AppTile:
    """Factory for a launcher tile: a coloured squircle icon + Hebrew caption.

    Returns a vertical container; the icon Button and an (initially hidden)
    badge are exposed as attributes on it so the launcher can update counts.
    """

    @staticmethod
    def build(emoji: str, caption: str, color, on_press):
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.button import Button
        from kivy.uix.floatlayout import FloatLayout
        from kivy.uix.label import Label

        box = BoxLayout(orientation="vertical", spacing=6,
                        padding=[6, 10, 6, 10])

        holder = FloatLayout(size_hint_y=0.72)
        icon = Button(text=emoji, font_size="34sp", font_name=EMOJI,
                      background_color=color, size_hint=(None, None))
        icon.bind(on_release=lambda *_: on_press())

        def _square(*_):
            s = min(holder.width, holder.height)
            icon.size = (s, s)
            icon.center = holder.center
        holder.bind(size=_square, pos=_square)

        badge = Label(text="", font_size="13sp", bold=True, markup=True,
                      size_hint=(None, None), size=(26, 26),
                      color=(1, 1, 1, 1), opacity=0)
        from kivy.graphics import Color, Ellipse
        with badge.canvas.before:
            badge._bg_color = Color(*RED)
            badge._bg = Ellipse(pos=badge.pos, size=badge.size)
        badge.bind(pos=lambda *_: setattr(badge._bg, "pos", badge.pos),
                   size=lambda *_: setattr(badge._bg, "size", badge.size))

        def _badge_pos(*_):
            # top-left corner of the icon (RTL: the "leading" outer corner)
            badge.center_x = icon.x + 6
            badge.center_y = icon.top - 6
        icon.bind(pos=_badge_pos, size=_badge_pos)

        holder.add_widget(icon)
        holder.add_widget(badge)
        box.add_widget(holder)

        cap = Label(text=H(caption), font_size="14sp", size_hint_y=0.28,
                    color=TEXT)
        box.add_widget(cap)

        box.icon = icon
        box.badge = badge
        return box


def set_badge(tile, count: int) -> None:
    """Show/hide the red count badge on an :class:`AppTile` container."""
    if count > 0:
        tile.badge.text = str(count) if count < 100 else "99+"
        tile.badge.opacity = 1
    else:
        tile.badge.opacity = 0


# --- iOS-style launcher pieces ---------------------------------------------
def frost(widget, alpha: float = 0.20, radius: int = 28, rgb=(1, 1, 1)) -> None:
    """Draw a translucent frosted rounded panel behind *widget* (tracks resize)."""
    from kivy.graphics import Color, RoundedRectangle

    with widget.canvas.before:
        Color(rgb[0], rgb[1], rgb[2], alpha)
        rect = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[radius])
    widget.bind(pos=lambda *_: setattr(rect, "pos", widget.pos),
                size=lambda *_: setattr(rect, "size", widget.size))


def _squircle(emoji: str, color, on_press, size: int = 62):
    """A fixed-size rounded app icon (coloured tile + scalable emoji image).

    Returns the holder; the background Button is exposed as ``.btn``. The emoji
    is an overlaid Image (so it scales correctly even with bitmap emoji fonts);
    the Image doesn't consume touches, so the Button behind it still fires.
    """
    from kivy.uix.button import Button
    from kivy.uix.floatlayout import FloatLayout

    holder = FloatLayout()
    btn = Button(background_color=color, size_hint=(None, None),
                 size=(size, size))
    btn.bind(on_release=lambda *_: on_press())
    img = emoji_image(emoji)
    img.size_hint = (None, None)
    img.size = (int(size * 0.62), int(size * 0.62))

    def _centre(*_):
        btn.center = holder.center
        img.center = holder.center
    holder.bind(size=_centre, pos=_centre)
    holder.add_widget(btn)
    holder.add_widget(img)
    holder.btn = btn
    return holder


def icon_button(emoji: str, color, on_press, size: int = 56):
    """A standalone tappable rounded emoji icon (for action buttons / rows)."""
    return _squircle(emoji, color, on_press, size)


def ios_icon(emoji: str, caption: str, color, on_press,
             caption_color=(1, 1, 1, 1), size: int = 62):
    """An iOS home-screen app: rounded icon + small caption below + badge.

    Exposes ``.icon`` (the Button), ``.badge`` and ``.caption`` for updates.
    """
    from kivy.graphics import Color, Ellipse
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.label import Label

    box = BoxLayout(orientation="vertical", spacing=3, padding=[2, 4])
    holder = _squircle(emoji, color, on_press, size)
    icon = holder.btn

    badge = Label(text="", font_size="12sp", bold=True, size_hint=(None, None),
                  size=(24, 24), color=(1, 1, 1, 1), opacity=0)
    with badge.canvas.before:
        Color(*RED)
        badge._bg = Ellipse(pos=badge.pos, size=badge.size)
    badge.bind(pos=lambda *_: setattr(badge._bg, "pos", badge.pos),
               size=lambda *_: setattr(badge._bg, "size", badge.size))

    def _badge_pos(*_):
        badge.center_x = icon.right - 4   # iOS badge: top-right corner
        badge.center_y = icon.top - 4
    icon.bind(pos=_badge_pos, size=_badge_pos)
    holder.add_widget(badge)

    box.add_widget(holder)
    cap = Label(text=H(caption), font_size="12sp", bold=True, size_hint_y=None,
                height=18, color=caption_color)
    box.add_widget(cap)

    box.icon = icon
    box.badge = badge
    box.caption = cap
    return box


def dock(items):
    """A frosted bottom dock of bare rounded icons. *items*: (emoji, color, cb)."""
    from kivy.uix.boxlayout import BoxLayout

    bar = BoxLayout(size_hint_y=None, height=92, padding=[14, 12], spacing=12)
    frost(bar, alpha=0.22, radius=32, rgb=(0.95, 0.96, 1.0))
    for emoji_g, color, cb in items:
        bar.add_widget(_squircle(emoji_g, color, cb, size=60))
    return bar


def control_center(items):
    """A swipe-down-from-the-top Control Center overlay (iOS-style).

    *items*: list of (emoji, label, color, callback). Returns a full-screen
    FloatLayout overlay to place on top of the app; it passes touches through
    to the app except a thin grab strip at the very top. Exposes ``.open()``
    and ``.close()``.
    """
    from kivy.animation import Animation
    from kivy.graphics import Color, Ellipse, Rectangle, RoundedRectangle
    from kivy.uix.behaviors import ButtonBehavior
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.gridlayout import GridLayout
    from kivy.uix.label import Label

    from kivy.core.window import Window
    from kivy.uix.floatlayout import FloatLayout
    from kivy.uix.widget import Widget

    rows = max(1, (len(items) + 2) // 3)
    PANEL_H = 92 + rows * 104   # padding + handle + each icon row (no title)
    # Pin the overlay to the window size directly — relying on the parent
    # FloatLayout to stretch it proved unreliable (stayed 100×100 on the Pi).
    overlay = FloatLayout(size_hint=(None, None))

    def _fit(*_):
        overlay.size = Window.size
        overlay.pos = (0, 0)
    Window.bind(size=_fit)
    _fit()

    state = {"open": False, "drag": None}

    # Dim backdrop — a plain Widget (NOT a Button): a disabled Button swallows
    # every touch on the whole screen, which blocked the app's icons. Closing
    # by tapping the backdrop is handled in _down instead. Opacity is animated.
    dim = Widget(size_hint=(1, 1), opacity=0)
    with dim.canvas:
        Color(0, 0, 0, 0.45)
        _dimr = Rectangle(pos=dim.pos, size=dim.size)
    dim.bind(pos=lambda *_: setattr(_dimr, "pos", dim.pos),
             size=lambda *_: setattr(_dimr, "size", dim.size))
    overlay.add_widget(dim)

    # Sliding panel.
    panel = BoxLayout(orientation="vertical", size_hint=(1, None),
                      height=PANEL_H, padding=[18, 16, 18, 22], spacing=12)
    with panel.canvas.before:
        Color(0.07, 0.08, 0.12, 0.98)
        _pbg = RoundedRectangle(radius=[0, 0, 30, 30])
    panel.bind(pos=lambda *_: setattr(_pbg, "pos", panel.pos),
               size=lambda *_: setattr(_pbg, "size", panel.size))

    grid = GridLayout(cols=3, spacing=10)
    panel.add_widget(grid)

    # Monochrome tiles that light up blue when active, like a phone's quick
    # settings. *items*: (glyph, label, callback, is_on) — is_on is a getter
    # returning the current toggle state, or None for one-shot action tiles.
    OFF_RGBA = (1, 1, 1, 0.15)        # translucent → reads grey on the dark panel
    ON_RGBA = (0.23, 0.55, 0.96, 1)   # blue active state
    tiles = []

    class _TileBtn(ButtonBehavior, Widget):
        pass

    def _make_tile(glyph, label, cb, getter):
        box = BoxLayout(orientation="vertical", spacing=4, padding=[2, 6])
        area = FloatLayout(size_hint_y=0.72)
        circle = _TileBtn(size_hint=(None, None))
        with circle.canvas.before:
            # Start OFF; refresh_tiles() (on open) sets the real state. Avoids
            # calling the getter before the app's flags exist at build time.
            col = Color(*OFF_RGBA)
            ell = Ellipse(pos=circle.pos, size=circle.size)
        circle.bind(pos=lambda *_: setattr(ell, "pos", circle.pos),
                    size=lambda *_: setattr(ell, "size", circle.size))
        icon = mono_icon_image(glyph)            # white silhouette icon
        icon.size_hint = (None, None)

        def _layout(*_):
            s = min(area.width, area.height)
            circle.size = (s, s)
            circle.center = area.center
            icon.size = (s * 0.5, s * 0.5)
            icon.center = area.center
        area.bind(size=_layout, pos=_layout)
        area.add_widget(circle)
        area.add_widget(icon)
        box.add_widget(area)

        cap = Label(text=H(label), font_size="12sp", bold=True,
                    size_hint_y=None, height=18, color=(1, 1, 1, 1))
        box.add_widget(cap)

        def _press(*_):
            if getter is None:        # action tile: run and dismiss
                close()
                cb()
            else:                     # toggle tile: flip, recolour, stay open
                cb()
                col.rgba = ON_RGBA if getter() else OFF_RGBA
        circle.bind(on_release=_press)

        box._col = col
        box._getter = getter
        tiles.append(box)
        return box

    for glyph, label, cb, getter in items:
        grid.add_widget(_make_tile(glyph, label, cb, getter))

    def refresh_tiles():
        for t in tiles:
            if t._getter is not None:
                t._col.rgba = ON_RGBA if t._getter() else OFF_RGBA

    # Drag handle at the bottom — the affordance to pull the panel back up.
    handle = FloatLayout(size_hint_y=None, height=24)
    pill = Widget(size_hint=(None, None), size=(120, 5),
                  pos_hint={"center_x": 0.5, "center_y": 0.5})
    with pill.canvas:
        Color(0.7, 0.73, 0.8, 0.9)
        _hp = RoundedRectangle(pos=pill.pos, size=pill.size, radius=[3])
    pill.bind(pos=lambda *_: setattr(_hp, "pos", pill.pos),
              size=lambda *_: setattr(_hp, "size", pill.size))
    handle.add_widget(pill)
    panel.add_widget(handle)

    overlay.add_widget(panel)

    def _place(*_):
        panel.x = overlay.x
        # Re-anchor the panel whenever the overlay is resized/moved, honouring
        # the open/closed state (parked above the top edge, or pulled down).
        panel.y = (overlay.top - PANEL_H) if state["open"] else overlay.top
    overlay.bind(pos=_place, size=_place)
    _place()

    GRAB = 26  # px-tall strip at the very top edge that starts an open-drag

    def _apply(frac):
        """Position the panel + backdrop for an open fraction in [0, 1]."""
        frac = 0.0 if frac < 0 else 1.0 if frac > 1 else frac
        panel.y = overlay.top - PANEL_H * frac
        dim.opacity = frac

    def open():
        state["open"] = True
        refresh_tiles()              # reflect current toggle states
        Animation.cancel_all(panel, "y")
        Animation.cancel_all(dim, "opacity")
        Animation(opacity=1, d=0.18, t="out_quad").start(dim)
        Animation(y=overlay.top - PANEL_H, d=0.18, t="out_quad").start(panel)

    def close():
        state["open"] = False
        Animation.cancel_all(panel, "y")
        Animation.cancel_all(dim, "opacity")
        Animation(opacity=0, d=0.16).start(dim)
        Animation(y=overlay.top, d=0.16, t="out_quad").start(panel)

    # --- finger-following drag -------------------------------------------
    # Opening: grab the thin strip at the top and the panel tracks the finger
    # 1:1. Closing: drag up from the handle pill, or tap the dimmed backdrop.
    # A release past the half-way mark snaps open, otherwise snaps closed.
    def _down(_w, touch):
        if not state["open"]:
            if touch.y >= overlay.top - GRAB:
                state["drag"] = True
                touch.grab(overlay)
                Animation.cancel_all(panel, "y")
                Animation.cancel_all(dim, "opacity")
                return True
            return False               # pass through to the app
        if handle.collide_point(*touch.pos):
            state["drag"] = True
            touch.grab(overlay)
            Animation.cancel_all(panel, "y")
            Animation.cancel_all(dim, "opacity")
            return True
        if not panel.collide_point(*touch.pos):
            close()                    # tapped the dimmed area below the panel
            return True
        return False                   # taps on the buttons fall through

    def _move(_w, touch):
        if state["drag"] and touch.grab_current is overlay:
            _apply((overlay.top - touch.y) / PANEL_H)
            return True
        return False

    def _up(_w, touch):
        if state["drag"] and touch.grab_current is overlay:
            touch.ungrab(overlay)
            state["drag"] = None
            (open if (overlay.top - touch.y) > PANEL_H * 0.5 else close)()
            return True
        return False

    overlay.bind(on_touch_down=_down, on_touch_move=_move, on_touch_up=_up)
    overlay.open = open
    overlay.close = close
    overlay.refresh = refresh_tiles
    return overlay


def home_bar(on_home, on_recents=None, on_prev=None, on_next=None):
    """iPhone-style gesture home indicator: a transparent strip + thin pill.

    The pill follows the finger while dragging (you see it move), and the
    gesture on release decides the action:

    * **Swipe up fast** (a flick) -> Home.
    * **Swipe up slow** (a deliberate drag) -> the app switcher / recents.
    * **Swipe right** -> the previous app (the last one you were in).
    * **Swipe left** -> reverses a recent right-swipe (forward), else nothing.

    Docked as a bottom OVERLAY on the root layout. ``on_recents`` / ``on_prev``
    / ``on_next`` are optional; without them only the Home flick is active.
    """
    import time

    from kivy.animation import Animation
    from kivy.graphics import Color, RoundedRectangle
    from kivy.uix.floatlayout import FloatLayout
    from kivy.uix.widget import Widget

    bar = FloatLayout(size_hint_y=None, height=24)

    # The pill — drawn on its own canvas, repositioned manually so we can lift
    # it with the finger. No background strip, so nothing reads as a black bar.
    pill = Widget(size_hint=(None, None), size=(128, 5))
    with pill.canvas:
        Color(0.86, 0.88, 0.93, 0.55)
        pill_rect = RoundedRectangle(pos=pill.pos, size=pill.size, radius=[3])
    pill.bind(pos=lambda *_: setattr(pill_rect, "pos", pill.pos),
              size=lambda *_: setattr(pill_rect, "size", pill.size))
    bar.add_widget(pill)

    base = {"y": 0.0}

    def _place(*_):
        pill.center_x = bar.center_x
        if st["x0"] is None:           # don't fight an in-progress drag
            pill.y = bar.y + 8
            base["y"] = pill.y
    st = {"x0": None, "y0": 0.0, "t0": 0.0}
    bar.bind(pos=_place, size=_place)

    FAST = 850          # px/sec above which an up-swipe counts as a flick (Home)
    H_THRESH = 46       # px of horizontal travel to count as a left/right swipe
    V_THRESH = 26       # px of upward travel to count as an up-swipe

    def _down(_w, touch):
        if bar.collide_point(*touch.pos):
            st["x0"], st["y0"], st["t0"] = touch.x, touch.y, time.time()
            touch.grab(bar)
            Animation.cancel_all(pill, "y")
            return True
        return False

    def _move(_w, touch):
        if touch.grab_current is bar and st["x0"] is not None:
            dy = touch.y - st["y0"]
            pill.y = base["y"] + max(0.0, min(dy, 90)) * 0.6   # lift with finger
            return True
        return False

    def _up(_w, touch):
        if touch.grab_current is bar and st["x0"] is not None:
            touch.ungrab(bar)
            dx, dy = touch.x - st["x0"], touch.y - st["y0"]
            dt = max(1e-3, time.time() - st["t0"])
            st["x0"] = None
            Animation(y=base["y"], d=0.18, t="out_quad").start(pill)
            if abs(dx) > abs(dy) and abs(dx) > H_THRESH:
                if dx > 0:                       # swipe right -> previous app
                    (on_prev or on_home)()
                elif on_next:                    # swipe left -> forward
                    on_next()
            elif dy > V_THRESH:
                if dy / dt > FAST or on_recents is None:
                    on_home()                    # fast flick up -> Home
                else:
                    on_recents()                 # slow drag up -> app switcher
            return True
        return False

    bar.bind(on_touch_down=_down, on_touch_move=_move, on_touch_up=_up)
    return bar
