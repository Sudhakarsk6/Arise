import math
from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel
from kivy.factory import Factory
from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle
from kivy.graphics.texture import Texture
from kivy.metrics import dp
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, ObjectProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget

ACCENT = (0.349, 0.761, 0.596, 1)      # #59c298
SOFT = (0.55, 0.90, 0.75, 1)
MUTED = (0.52, 0.56, 0.54, 1)
RED = (0.90, 0.35, 0.40, 1)
LOGO_CYAN = (0.10, 0.78, 0.90, 1)
NAV_BG = (0.015, 0.015, 0.015, 1)

SEGS = {"auto": [("scripts", "Scripts"), ("rules", "Rules"), ("focus", "Focus"), ("reply", "Reply")],
        "track": [("health", "Health"), ("habits", "Habits"), ("money", "Money")],
        "fin": [("watch", "Watchlist"), ("test", "Backtest"), ("paper", "Paper")]}


def draw_icon(kind, cx, cy, size, color, bg=NAV_BG):
    """Line icons drawn on a 24x24 grid (no font/emoji needed)."""
    s = size / 24.0
    w = max(1.7 * s, 1.3)

    def P(x, y):
        return (cx + (x - 12) * s, cy + (12 - y) * s)

    def L(*pts, **kw):
        Line(points=[c for p in pts for c in P(*p)], width=w, cap="round", joint="round", **kw)

    Color(*color)
    if kind == "voice":
        RoundedRectangle(pos=P(9, 15), size=(6 * s, 12 * s), radius=[3 * s])
        Line(circle=(*P(12, 11), 6.6 * s, 90, 270), width=w, cap="round")
        L((12, 17.6), (12, 21)); L((8.6, 21), (15.4, 21))
    elif kind == "fitness":
        L((2, 12), (7, 12), (10, 5), (14, 19), (17, 12), (22, 12))
    elif kind == "focus":
        Line(circle=(*P(12, 12), 9 * s), width=w); Line(circle=(*P(12, 12), 5 * s), width=w)
        x, y = P(12, 12)
        Ellipse(pos=(x - 1.9 * s, y - 1.9 * s), size=(3.8 * s, 3.8 * s))
    elif kind in ("auto", "bolt"):
        L((13, 2), (5, 13), (11, 13), (10, 22), (19, 10), (13, 10), (13, 2))
    elif kind == "settings":
        for y, x in ((6, 8), (12, 16), (18, 10)):
            L((3, y), (21, y))
            kx, ky = P(x, y)
            Color(*bg); Ellipse(pos=(kx - 3 * s, ky - 3 * s), size=(6 * s, 6 * s))
            Color(*color); Line(circle=(kx, ky, 3 * s), width=w)
    elif kind == "home":
        L((3, 11), (12, 3), (21, 11)); L((5, 10), (5, 21), (19, 21), (19, 10)); L((10, 21), (10, 15), (14, 15), (14, 21))
    elif kind == "chart":
        L((3, 3), (3, 21), (21, 21)); L((6, 16), (10, 11), (14, 14), (20, 6))
    elif kind == "star":
        pts = []
        for i in range(10):
            r = 9.5 if i % 2 == 0 else 4.2
            a = math.pi * i / 5
            pts.append((12 + r * math.sin(a), 12.5 - r * math.cos(a)))
        L(*pts, pts[0])
    elif kind == "bell":
        Line(circle=(*P(12, 10), 6 * s, -90, 90), width=w, cap="round")
        L((6, 10), (5, 17)); L((18, 10), (19, 17)); L((4, 17), (20, 17)); L((10, 20), (14, 20))
    elif kind == "file":
        L((6, 3), (14, 3), (19, 8), (19, 21), (6, 21), (6, 3)); L((9, 13), (16, 13)); L((9, 17), (16, 17))
    elif kind == "heart":
        pts = []
        for i in range(41):
            t = 2 * math.pi * i / 40
            pts.append((12 + 0.52 * 16 * math.sin(t) ** 3,
                        10.5 - 0.52 * (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))))
        L(*pts)
    elif kind == "globe":
        Line(circle=(*P(12, 12), 9 * s), width=w)
        Line(ellipse=(*P(8, 20), 8 * s, 16 * s), width=w); L((3, 12), (21, 12))
    elif kind == "check":
        Line(circle=(*P(12, 12), 9 * s), width=w); L((7.5, 12.5), (10.5, 15.5), (16.5, 9))
    elif kind == "mail":
        Line(rectangle=(*P(3, 18), 18 * s, 12 * s), width=w); L((3, 6), (12, 13), (21, 6))


class Icon(Widget):
    kind = StringProperty("bolt")
    color = ListProperty([1, 1, 1, 1])

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self.draw, size=self.draw, kind=self.draw, color=self.draw)

    def draw(self, *_):
        self.canvas.clear()
        with self.canvas:
            draw_icon(self.kind, self.center_x, self.center_y, min(self.size), self.color)


class NavItem(ButtonBehavior, BoxLayout):
    kind = StringProperty("home")
    text = StringProperty("")
    selected = BooleanProperty(False)
    tint = ListProperty(list(MUTED))

    def on_selected(self, *_):
        Animation(tint=list(ACCENT if self.selected else MUTED), d=0.2).start(self)


class Toggle(ButtonBehavior, Widget):
    active = BooleanProperty(False)
    knob = NumericProperty(0.0)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self.draw, size=self.draw, knob=self.draw)
        self.draw()

    def on_active(self, *_):
        Animation(knob=1.0 if self.active else 0.0, d=0.18, t="out_quad").start(self)

    def on_release(self):
        self.active = not self.active

    def draw(self, *_):
        self.canvas.clear()
        k, off = self.knob, (0.19, 0.21, 0.20)
        with self.canvas:
            Color(*[off[i] + (ACCENT[i] - off[i]) * k for i in range(3)], 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[self.height / 2])
            Color(1, 1, 1, 1)
            d = self.height - dp(6)
            Ellipse(pos=(self.x + dp(3) + k * (self.width - self.height), self.y + dp(3)), size=(d, d))


class Bar(Widget):
    value = NumericProperty(0)
    color = ListProperty(list(ACCENT))

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self.draw, size=self.draw, value=self.draw, color=self.draw)

    def draw(self, *_):
        self.canvas.clear()
        with self.canvas:
            Color(0.12, 0.14, 0.13, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[self.height / 2])
            if self.value > 0.01:
                Color(*self.color)
                RoundedRectangle(pos=self.pos, size=(max(self.height, self.width * min(self.value, 1)), self.height),
                                 radius=[self.height / 2])


class Ring(Widget):
    value = NumericProperty(0)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self.redraw, size=self.redraw, value=self.redraw)

    def redraw(self, *_):
        self.canvas.clear()
        cx, cy = self.center
        r = min(self.size) / 2 - dp(12)
        with self.canvas:
            Color(0.12, 0.14, 0.13, 1)
            Line(circle=(cx, cy, r), width=dp(11))
            Color(*ACCENT)
            if self.value > 0.005:
                Line(circle=(cx, cy, r, 0, 360 * min(self.value, 1)), width=dp(11), cap="round")


class MicButton(ButtonBehavior, Widget):
    pulse = NumericProperty(0)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self.draw, size=self.draw, pulse=self.draw, state=self.draw)

    def start(self):
        a = Animation(pulse=1, d=1.8, t="out_quad") + Animation(pulse=0, d=0.01)
        a.repeat = True
        a.start(self)

    def draw(self, *_):
        self.canvas.clear()
        cx, cy = self.center
        r = min(self.size) / 2 * 0.52 * (0.95 if self.state == "down" else 1)
        with self.canvas:
            Color(*ACCENT[:3], 0.40 * (1 - self.pulse))
            rr = r * (1 + 0.85 * self.pulse)
            Ellipse(pos=(cx - rr, cy - rr), size=(2 * rr, 2 * rr))
            Color(*ACCENT[:3], 0.16)
            Ellipse(pos=(cx - r * 1.32, cy - r * 1.32), size=(r * 2.64, r * 2.64))
            Color(*ACCENT)
            Ellipse(pos=(cx - r, cy - r), size=(2 * r, 2 * r))
            draw_icon("voice", cx, cy, r, (0, 0, 0, 1), bg=ACCENT)


class Backdrop(Widget):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.tex = Texture.create(size=(1, 2), colorfmt="rgb")
        self.tex.blit_buffer(bytes([0, 0, 0, 9, 34, 26]), colorfmt="rgb", bufferfmt="ubyte")
        self.tex.mag_filter = "linear"
        self.bind(pos=self.draw, size=self.draw)

    def draw(self, *_):
        self.canvas.clear()
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(texture=self.tex, pos=self.pos, size=self.size)
            for ox, oy, col, base in ((0.92, 0.94, ACCENT[:3], 0.60), (0.05, 0.12, (0.10, 0.52, 0.42), 0.45)):
                cx, cy = self.x + self.width * ox, self.y + self.height * oy
                for i in range(9):
                    r = self.width * base * (1 - (i + 1) / 9 * 0.88)
                    Color(*col, 0.03)
                    Ellipse(pos=(cx - r, cy - r), size=(2 * r, 2 * r))


class Smiley(Widget):
    blink = NumericProperty(1)
    bob = NumericProperty(0)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self.draw, size=self.draw, blink=self.draw, bob=self.draw)

    def draw(self, *_):
        self.canvas.clear()
        cx, cy = self.center_x, self.center_y + self.bob * dp(4)
        r = min(self.size) / 2 - dp(6)
        ex, ey, h = r * 0.38, cy + r * 0.22, r * 0.17 * self.blink
        with self.canvas:
            Color(*ACCENT[:3], 0.14)
            Ellipse(pos=(cx - r * 1.2, cy - r * 1.2), size=(r * 2.4, r * 2.4))
            Color(*SOFT)
            Line(circle=(cx, cy, r), width=dp(2))
            Line(points=[cx - ex, ey - h, cx - ex, ey + h], width=dp(2.6), cap="round")
            Line(points=[cx + ex, ey - h, cx + ex, ey + h], width=dp(2.6), cap="round")
            Line(circle=(cx, cy, r * 0.56, 128, 232), width=dp(2.6), cap="round")

    def start_idle(self):
        Animation.cancel_all(self)
        f = Animation(bob=1, d=1.7, t="in_out_sine") + Animation(bob=-1, d=1.7, t="in_out_sine")
        f.repeat = True
        f.start(self)
        b = Animation(d=3.0) + Animation(blink=0, d=0.08) + Animation(blink=1, d=0.12)
        b.repeat = True
        b.start(self)


class SpinnerRing(Widget):
    """Smooth loading ring drawn around the logo on the splash screen."""
    angle = NumericProperty(0)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self.draw, size=self.draw, angle=self.draw)

    def start(self):
        a = Animation(angle=360, d=1.4, t="in_out_sine") + Animation(angle=0, d=0.001)
        a.repeat = True
        a.start(self)

    def draw(self, *_):
        self.canvas.clear()
        cx, cy, r = *self.center, min(self.size) / 2 - dp(4)
        with self.canvas:
            Color(*LOGO_CYAN[:3], 0.16)
            Line(circle=(cx, cy, r), width=dp(3.5))
            Color(*LOGO_CYAN)
            Line(circle=(cx, cy, r, self.angle, self.angle + 110), width=dp(3.5), cap="round")


class Chart(Widget):
    """Interactive bar/line chart. Touch or drag to read a value. None values are skipped (gaps)."""
    kind = StringProperty("bar")
    series = ListProperty([])
    labels = ListProperty([])
    unit = StringProperty("")
    colors = ListProperty([])
    sel = NumericProperty(-1)

    def __init__(self, **kw):
        super().__init__(**kw)
        for p in ("pos", "size", "kind", "series", "labels", "sel", "colors"):
            self.bind(**{p: self.draw})

    def _text(self, text, x, y, color=MUTED, size=11, align="left"):
        lab = CoreLabel(text=text, font_size=dp(size))
        lab.refresh()
        tex = lab.texture
        Color(*color)
        Rectangle(texture=tex, pos=(x - (tex.width if align == "right" else 0), y), size=tex.size)

    def _geom(self):
        pl, pr, pt, pb = dp(8), dp(8), dp(24), dp(20)
        return self.x + pl, self.y + pb, self.width - pl - pr, self.height - pt - pb

    @staticmethod
    def _fmt(v):
        return f"{v:,.0f}" if abs(v) >= 100 else f"{v:,.2f}".rstrip("0").rstrip(".")

    def draw(self, *_):
        self.canvas.clear()
        x0, y0, w, h = self._geom()
        vals = [v for s in self.series for v in s if v is not None]
        with self.canvas:
            if not vals or w <= 0 or h <= 0:
                self._text("No data yet", self.center_x - dp(30), self.center_y)
                return
            vmax = max(vals + ([0] if self.kind == "bar" else []))
            vmin = min(vals + ([0] if self.kind == "bar" else []))
            if vmax == vmin:
                vmax, vmin = vmax + 1, vmin - (1 if self.kind == "line" else 0)
            Y = lambda v: y0 + (v - vmin) / (vmax - vmin) * h
            Color(1, 1, 1, 0.06)
            for i in range(4):
                Line(points=[x0, y0 + h * i / 3, x0 + w, y0 + h * i / 3], width=1)
            n = max(len(s) for s in self.series)
            cols = list(self.colors) or [ACCENT, (0.55, 0.6, 0.58, 1)]
            if self.kind == "bar":
                slot = w / n
                bw = slot * 0.62
                for i, v in enumerate(self.series[0]):
                    if v is None:
                        continue
                    base, top = Y(0), Y(v)
                    Color(*(cols[0] if v >= 0 else RED), 1 if i != self.sel else 0.7)
                    Rectangle(pos=(x0 + i * slot + (slot - bw) / 2, min(base, top)), size=(bw, max(abs(top - base), dp(1.5))))
            else:
                for si, s in enumerate(self.series):
                    Color(*cols[si % len(cols)])
                    pts = []
                    for i, v in enumerate(s):
                        if v is None:
                            if len(pts) >= 4:
                                Line(points=pts, width=dp(1.8), joint="round")
                            pts = []
                            continue
                        pts += [x0 + i * w / max(n - 1, 1), Y(v)]
                    if len(pts) >= 4:
                        Line(points=pts, width=dp(1.8), joint="round")
                    if len(pts) >= 2:
                        Ellipse(pos=(pts[-2] - dp(3), pts[-1] - dp(3)), size=(dp(6), dp(6)))
            if self.labels:
                self._text(str(self.labels[0])[-5:], x0, self.y + dp(3))
                self._text(str(self.labels[-1])[-5:], x0 + w, self.y + dp(3), align="right")
            if 0 <= self.sel < n:
                sx = x0 + (self.sel + 0.5) * w / n if self.kind == "bar" else x0 + self.sel * w / max(n - 1, 1)
                Color(1, 1, 1, 0.35)
                Line(points=[sx, y0, sx, y0 + h], width=1)
                parts = [self._fmt(s[self.sel]) for s in self.series if self.sel < len(s) and s[self.sel] is not None]
                lab = str(self.labels[self.sel]) if self.sel < len(self.labels) else ""
                self._text(f"{lab}   {' / '.join(parts) if parts else 'unavailable'} {self.unit}".strip(),
                           x0, self.top - dp(18), color=(1, 1, 1, 1), size=12)

    def _pick(self, touch):
        x0, _, w, _ = self._geom()
        n = max((len(s) for s in self.series), default=0)
        if not n:
            return
        i = int((touch.x - x0) / (w / n)) if self.kind == "bar" else round((touch.x - x0) / (w / max(n - 1, 1)))
        self.sel = max(0, min(n - 1, i))

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            self._pick(touch)
            return True

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            self._pick(touch)
            return True

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            return True


class Seg(BoxLayout):
    """Segmented control for a navigation group (auto / track / fin)."""
    group = StringProperty("")

    def __init__(self, **kw):
        super().__init__(**kw)
        self.btns = {}
        Clock.schedule_once(self.build)

    def build(self, *_):
        app = App.get_running_app()
        for key, label in SEGS.get(self.group, []):
            b = Factory.SegBtn(text=label)
            b.bind(on_release=lambda w, k=key: app.sub(self.group, k))
            self.btns[key] = b
            self.add_widget(b)
        self.refresh(app.cur_sub.get(self.group))

    def refresh(self, current):
        for k, b in self.btns.items():
            b.active = (k == current)


class ScriptCard(BoxLayout):
    title = StringProperty("")
    desc = StringProperty("")
    icon = StringProperty("bolt")
    status_line = StringProperty("")
    btn_text = StringProperty("Run")
    progress = NumericProperty(0)
    status_color = ListProperty(list(MUTED))
    run_cb = ObjectProperty(None, allownone=True)
    hist_cb = ObjectProperty(None, allownone=True)
    open_cb = ObjectProperty(None, allownone=True)
