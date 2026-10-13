import os, random, threading, time
from kivy.config import Config
if not os.environ.get("ANDROID_ARGUMENT") and not os.environ.get("ARISE_TEST"):
    Config.set("graphics", "width", "1000")
    Config.set("graphics", "height", "700")
    Config.set("graphics", "minimum_width", "360")
    Config.set("graphics", "minimum_height", "560")
from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.factory import Factory
from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle
from kivy.graphics.texture import Texture
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.resources import resource_add_path
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from arise import ai, android_api, automations, focus, quotes, voice
from arise.fitness import Fitness
from arise.security import PinGuard
from arise.storage import Store

resource_add_path(os.path.dirname(os.path.abspath(__file__)))
ACCENT = (0.349, 0.761, 0.596, 1)   # #59c298
MUTED = (0.52, 0.56, 0.54, 1)
MINT = ACCENT
SOFT = (0.55, 0.90, 0.75, 1)
PAGES = ("voice", "fitness", "focus", "auto", "settings")

KV = '''
#:import FadeTransition kivy.uix.screenmanager.FadeTransition
#:import dp kivy.metrics.dp

<Lbl@Label>:
    color: .93, .94, .98, 1
    size_hint_y: None
    text_size: self.width, None
    height: self.texture_size[1] + dp(4)
    halign: 'left'
    font_size: dp(15)

<Muted@Lbl>:
    color: .52, .56, .54, 1
    font_size: dp(13)

<Title@Lbl>:
    font_size: dp(32)
    bold: True
    height: self.texture_size[1] + dp(8)

<Section@Lbl>:
    font_size: dp(17)
    bold: True

<Card@BoxLayout>:
    orientation: 'vertical'
    padding: dp(16)
    spacing: dp(10)
    size_hint_y: None
    height: self.minimum_height
    canvas.before:
        Color:
            rgba: .062, .068, .066, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(20)]
        Color:
            rgba: 1, 1, 1, .06
        Line:
            rounded_rectangle: (self.x, self.y, self.width, self.height, dp(20))
            width: 1

<Btn@Button>:
    bg: .349, .761, .596, 1
    size_hint_y: None
    height: dp(50)
    background_normal: ''
    background_down: ''
    background_color: 0, 0, 0, 0
    bold: True
    font_size: dp(15)
    color: 0, 0, 0, 1
    canvas.before:
        Color:
            rgba: self.bg
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(14)]
        Color:
            rgba: (0, 0, 0, .28) if self.state == 'down' else (0, 0, 0, 0)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(14)]

<Ghost@Btn>:
    bg: .12, .135, .13, 1
    color: 1, 1, 1, 1

<Chip@Button>:
    background_normal: ''
    background_down: ''
    background_color: 0, 0, 0, 0
    font_size: dp(13)
    color: .55, .90, .75, 1
    canvas.before:
        Color:
            rgba: .05, .15, .11, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(19)]

<Field@TextInput>:
    size_hint_y: None
    height: dp(48)
    multiline: False
    write_tab: False
    background_normal: 'assets/field_bg.png'
    background_active: 'assets/field_bg_active.png'
    border: (22, 22, 22, 22)
    background_color: 1, 1, 1, 1
    foreground_color: 1, 1, 1, 1
    hint_text_color: .45, .47, .58, 1
    cursor_color: .349, .761, .596, 1
    font_size: dp(15)
    padding: [dp(14), dp(14)]

<Pick@Spinner>:
    size_hint_y: None
    height: dp(48)
    background_normal: ''
    background_color: 0, 0, 0, 0
    color: 1, 1, 1, 1
    canvas.before:
        Color:
            rgba: .086, .098, .094, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(13)]

<Grid@GridLayout>:
    cols: 1
    size_hint_y: None
    height: self.minimum_height
    padding: max(dp(18), (self.width - dp(560)) / 2), dp(22), max(dp(18), (self.width - dp(560)) / 2), dp(24)
    spacing: dp(14)

<Page@ScrollView>:
    do_scroll_x: False
    bar_width: dp(2)

<NavItem>:
    orientation: 'vertical'
    spacing: dp(3)
    padding: dp(4)
    Icon:
        kind: root.kind
        color: root.tint
        size_hint_y: None
        height: dp(26)
    Label:
        text: root.text
        font_size: dp(11)
        color: root.tint
        size_hint_y: None
        height: dp(14)

<LockScreen>:
    name: 'lock'
    FloatLayout:
        Backdrop:
        BoxLayout:
            orientation: 'vertical'
            padding: max(dp(32), (self.width - dp(400)) / 2), dp(32)
            spacing: dp(12)
            Widget:
            Label:
                id: logo
                text: 'ARISE'
                font_size: dp(40)
                bold: True
                color: .349, .761, .596, 1
                size_hint_y: None
                height: dp(64)
            Muted:
                id: title
                halign: 'center'
            Field:
                id: pin
                password: True
                input_filter: 'int'
                hint_text: 'PIN'
                halign: 'center'
                font_size: dp(22)
                on_text_validate: app.submit_pin()
            Label:
                id: status
                color: 1, .45, .5, 1
                size_hint_y: None
                height: dp(26)
            Btn:
                id: go
                on_release: app.submit_pin()
            Ghost:
                id: dev
                text: 'Use fingerprint / device lock'
                on_release: app.device_unlock()
            Widget:

<WelcomeScreen>:
    name: 'welcome'
    FloatLayout:
        Backdrop:
        BoxLayout:
            orientation: 'vertical'
            padding: max(dp(28), (self.width - dp(460)) / 2), dp(24)
            spacing: dp(8)
            Widget:
                size_hint_y: 0.07
            Label:
                id: wl_greet
                text: 'Good evening'
                font_size: dp(17)
                color: .52, .58, .55, 1
                size_hint_y: None
                height: dp(26)
            Label:
                id: wl_hi
                text: 'Hi SK'
                markup: True
                font_size: dp(58)
                bold: True
                size_hint_y: None
                height: dp(84)
            Label:
                id: wl_welcome
                text: 'Welcome'
                font_size: dp(24)
                color: .86, .87, .95, 1
                size_hint_y: None
                height: dp(40)
            Widget:
                size_hint_y: None
                height: dp(10)
            Card:
                id: wl_qcard
                on_touch_down: app.next_quote() if self.collide_point(*args[1].pos) else None
                Label:
                    id: wl_quote
                    text: ''
                    italic: True
                    font_size: dp(20)
                    halign: 'center'
                    text_size: self.width, None
                    size_hint_y: None
                    height: self.texture_size[1] + dp(6)
                Muted:
                    text: 'tap for another'
                    halign: 'center'
                    font_size: dp(11)
            Widget:
            AnchorLayout:
                size_hint_y: None
                height: dp(150)
                Smiley:
                    id: smile
                    size_hint: None, None
                    size: dp(130), dp(130)
            Widget:
                size_hint_y: 0.05
            Btn:
                id: wl_btn
                text: "Let's go"
                height: dp(54)
                on_release: app.enter_home()

<HomeScreen>:
    name: 'home'
    BoxLayout:
        id: shell
        orientation: 'vertical'
        ScreenManager:
            id: pages
            transition: FadeTransition(duration=0.15)
            Screen:
                name: 'voice'
                Page:
                    Grid:
                        Muted:
                            id: hello
                            text: 'Good evening'
                        Title:
                            text: 'How can I help?'
                        Card:
                            Muted:
                                text: 'THOUGHT OF THE MOMENT'
                                font_size: dp(11)
                            Lbl:
                                id: quote_lbl
                                italic: True
                                font_size: dp(18)
                        AnchorLayout:
                            size_hint_y: None
                            height: dp(210)
                            MicButton:
                                id: mic
                                size_hint: None, None
                                size: dp(200), dp(200)
                                on_release: app.listen()
                        Muted:
                            text: 'Tap to speak'
                            halign: 'center'
                        BoxLayout:
                            size_hint_y: None
                            height: dp(38)
                            spacing: dp(8)
                            Chip:
                                text: 'My playlist'
                                on_release: app.process('play my playlist')
                            Chip:
                                text: 'Steps today'
                                on_release: app.process('how many steps')
                            Chip:
                                text: 'Focus 25'
                                on_release: app.process('start focus for 25 minutes')
                        Card:
                            Muted:
                                id: heard
                                text: 'Say something or type below'
                            Lbl:
                                id: answer
                                font_size: dp(17)
                                color: .55, .95, .76, 1
                        BoxLayout:
                            size_hint_y: None
                            height: dp(48)
                            spacing: dp(8)
                            Field:
                                id: typed
                                hint_text: 'Type a command or question'
                                on_text_validate: app.process(self.text)
                            Btn:
                                text: 'Send'
                                size_hint_x: None
                                width: dp(84)
                                on_release: app.process(typed.text)
            Screen:
                name: 'fitness'
                Page:
                    Grid:
                        Muted:
                            text: 'TODAY'
                        Title:
                            text: 'Fitness'
                        Card:
                            FloatLayout:
                                size_hint_y: None
                                height: dp(240)
                                Ring:
                                    id: ring
                                    size_hint: None, None
                                    size: dp(220), dp(220)
                                    pos_hint: {'center_x': .5, 'center_y': .5}
                                Label:
                                    id: steps_big
                                    text: '0'
                                    font_size: dp(44)
                                    bold: True
                                    pos_hint: {'center_x': .5, 'center_y': .56}
                                    size_hint: None, None
                                    size: dp(160), dp(60)
                                Label:
                                    id: goal_lbl
                                    text: 'steps'
                                    color: .52, .58, .55, 1
                                    pos_hint: {'center_x': .5, 'center_y': .40}
                                    size_hint: None, None
                                    size: dp(160), dp(30)
                        BoxLayout:
                            size_hint_y: None
                            height: dp(96)
                            spacing: dp(10)
                            Card:
                                size_hint_y: 1
                                Stat:
                                    id: st_km
                            Card:
                                size_hint_y: 1
                                Stat:
                                    id: st_kcal
                            Card:
                                size_hint_y: 1
                                Stat:
                                    id: st_min
                        Card:
                            Section:
                                text: 'Last 7 days'
                            BoxLayout:
                                id: hist_box
                                orientation: 'vertical'
                                size_hint_y: None
                                height: dp(7 * 34)
                        Card:
                            Section:
                                text: 'GPS workout'
                            Lbl:
                                id: wk_lbl
                                text: 'Not running'
                            Btn:
                                id: wk_btn
                                text: 'Start workout'
                                on_release: app.toggle_workout()
                            Muted:
                                id: wk_hist
            Screen:
                name: 'focus'
                Page:
                    Grid:
                        Muted:
                            text: 'STAY ON TASK'
                        Title:
                            text: 'Focus'
                        Card:
                            Lbl:
                                id: fo_status
                                font_size: dp(22)
                                bold: True
                        Card:
                            Section:
                                text: 'Daily schedule'
                            BoxLayout:
                                size_hint_y: None
                                height: dp(34)
                                Lbl:
                                    text: 'Block on schedule'
                                Toggle:
                                    id: fo_enabled
                                    size_hint: None, None
                                    size: dp(54), dp(30)
                            BoxLayout:
                                size_hint_y: None
                                height: dp(48)
                                spacing: dp(8)
                                Field:
                                    id: fo_start
                                    hint_text: 'From 09:00'
                                Field:
                                    id: fo_end
                                    hint_text: 'Until 17:00'
                            Muted:
                                text: 'Overnight works too, e.g. 22:00 to 06:00'
                            Muted:
                                text: 'Blocked apps (names or package ids)'
                            Field:
                                id: fo_apps
                            BoxLayout:
                                size_hint_y: None
                                height: dp(34)
                                Lbl:
                                    text: 'Strict mode'
                                Toggle:
                                    id: fo_strict
                                    size_hint: None, None
                                    size: dp(54), dp(30)
                            Muted:
                                text: 'Cannot be switched off while focus is active'
                            Btn:
                                text: 'Save focus settings'
                                on_release: app.save_focus()
                        Card:
                            Section:
                                text: 'Quick session'
                            BoxLayout:
                                size_hint_y: None
                                height: dp(48)
                                spacing: dp(10)
                                Field:
                                    id: fo_mins
                                    text: '25'
                                    input_filter: 'int'
                                Muted:
                                    text: 'minutes'
                                    size_hint_x: None
                                    width: dp(70)
                            BoxLayout:
                                size_hint_y: None
                                height: dp(50)
                                spacing: dp(10)
                                Btn:
                                    text: 'Start now'
                                    bg: .12, .42, .31, 1
                                    color: 1, 1, 1, 1
                                    on_release: app.start_focus()
                                Btn:
                                    text: 'Stop'
                                    bg: .75, .22, .30, 1
                                    color: 1, 1, 1, 1
                                    on_release: app.stop_focus()
                        Card:
                            Section:
                                text: 'Blocking service'
                            Muted:
                                id: fo_access
                            Ghost:
                                text: 'Enable blocking (Accessibility)'
                                on_release: app.open_accessibility()
            Screen:
                name: 'auto'
                Page:
                    Grid:
                        Muted:
                            text: 'WORK FOR YOU'
                        Title:
                            text: 'Automate'
                        Card:
                            Section:
                                text: 'New rule'
                            Pick:
                                id: sp_trig
                                text: 'Voice phrase'
                                values: ['Voice phrase', 'Daily time']
                            Field:
                                id: in_val
                                hint_text: 'phrase, or time like 07:30'
                            Pick:
                                id: sp_act
                                text: 'open_app'
                                values: ['open_app', 'open_url', 'youtube_playlist', 'speak', 'send_sms', 'quiet_mode']
                            Field:
                                id: in_param
                                hint_text: 'app name / URL / text / number|text'
                            Btn:
                                text: 'Add rule'
                                on_release: app.add_auto()
                        Card:
                            Section:
                                text: 'Your rules'
                            GridLayout:
                                id: auto_list
                                cols: 1
                                size_hint_y: None
                                height: self.minimum_height
                                spacing: dp(6)
                        Card:
                            Section:
                                text: 'Auto-reply'
                            BoxLayout:
                                size_hint_y: None
                                height: dp(34)
                                Lbl:
                                    text: 'Enabled'
                                Toggle:
                                    id: ar_enabled
                                    size_hint: None, None
                                    size: dp(54), dp(30)
                            Muted:
                                text: 'Reply if I have not opened the chat within (minutes)'
                            Field:
                                id: ar_delay
                                input_filter: 'int'
                            Muted:
                                text: 'Message'
                            Field:
                                id: ar_msg
                            Muted:
                                text: 'Only these contacts (empty = everyone)'
                            Field:
                                id: ar_contacts
                            Muted:
                                text: 'One reply per contact every (minutes)'
                            Field:
                                id: ar_cool
                                input_filter: 'int'
                            Btn:
                                text: 'Save auto-reply'
                                on_release: app.save_autoreply()
                            Muted:
                                id: ar_access
                            Ghost:
                                text: 'Grant notification access'
                                on_release: app.open_access()
            Screen:
                name: 'settings'
                Page:
                    Grid:
                        Muted:
                            text: 'MAKE IT YOURS'
                        Title:
                            text: 'Settings'
                        Card:
                            Section:
                                text: 'Profile'
                            Muted:
                                text: 'Your name'
                            Field:
                                id: st_name
                            Muted:
                                text: 'Height cm  /  Weight kg  /  Daily step goal'
                            BoxLayout:
                                size_hint_y: None
                                height: dp(48)
                                spacing: dp(8)
                                Field:
                                    id: st_h
                                    input_filter: 'int'
                                Field:
                                    id: st_w
                                    input_filter: 'int'
                                Field:
                                    id: st_goal
                                    input_filter: 'int'
                        Card:
                            Section:
                                text: 'AI and media'
                            Muted:
                                text: 'AI API key (stored only on this device)'
                            Field:
                                id: st_key
                                password: True
                            Muted:
                                text: 'AI model'
                            Field:
                                id: st_model
                            Muted:
                                text: 'YouTube playlist (link or ID)'
                            Field:
                                id: st_playlist
                            Muted:
                                text: 'Contacts (name=number, comma separated)'
                            Field:
                                id: st_contacts
                        Card:
                            Section:
                                text: 'Security'
                            Muted:
                                text: 'Auto-lock after (seconds, min 15)'
                            Field:
                                id: st_lock
                                input_filter: 'int'
                            Muted:
                                text: 'New PIN (empty keeps current)'
                            Field:
                                id: st_pin
                                password: True
                                input_filter: 'int'
                        Btn:
                            text: 'Save settings'
                            on_release: app.save_settings()
                        Btn:
                            text: 'Lock now'
                            bg: .75, .22, .30, 1
                            color: 1, 1, 1, 1
                            on_release: app.show_lock()
                        Card:
                            Section:
                                text: 'Activity log'
                            Ghost:
                                text: 'Refresh'
                                on_release: app.refresh_log()
                            Label:
                                id: log_label
                                size_hint_y: None
                                text_size: self.width, None
                                height: self.texture_size[1]
                                halign: 'left'
                                valign: 'top'
                                font_size: dp(12)
                                color: .62, .68, .65, 1
        BoxLayout:
            id: nav
            size_hint_y: None
            height: dp(66)
            padding: dp(6), dp(4)
            canvas.before:
                Color:
                    rgba: .015, .015, .015, 1
                Rectangle:
                    pos: self.pos
                    size: self.size
                Color:
                    rgba: 1, 1, 1, .07
                Line:
                    points: [self.right, self.y, self.right, self.top] if self.orientation == 'vertical' else [self.x, self.top, self.right, self.top]
            NavItem:
                id: nav_voice
                kind: 'voice'
                text: 'Voice'
                selected: True
                on_release: app.goto('voice')
            NavItem:
                id: nav_fitness
                kind: 'fitness'
                text: 'Fitness'
                on_release: app.goto('fitness')
            NavItem:
                id: nav_focus
                kind: 'focus'
                text: 'Focus'
                on_release: app.goto('focus')
            NavItem:
                id: nav_auto
                kind: 'auto'
                text: 'Automate'
                on_release: app.goto('auto')
            NavItem:
                id: nav_settings
                kind: 'settings'
                text: 'Settings'
                on_release: app.goto('settings')

<Stat@Label>:
    markup: True
    halign: 'center'
    valign: 'middle'
    color: .93, .94, .98, 1

ScreenManager:
    transition: FadeTransition(duration=0.25)
    LockScreen:
    WelcomeScreen:
    HomeScreen:
'''


# ------------------------------------------------------------------ drawing helpers
def draw_icon(kind, cx, cy, size, color, bg=(0.015, 0.015, 0.015, 1)):
    """Draw a simple line icon into the current canvas context."""
    s = size / 24.0
    w = max(1.7 * s, 1.3)

    def P(x, y):
        return (cx + (x - 12) * s, cy + (12 - y) * s)

    Color(*color)
    if kind == "voice":
        RoundedRectangle(pos=P(9, 15), size=(6 * s, 12 * s), radius=[3 * s])
        Line(circle=(*P(12, 11), 6.6 * s, 90, 270), width=w, cap="round")
        Line(points=[*P(12, 17.6), *P(12, 21)], width=w, cap="round")
        Line(points=[*P(8.6, 21), *P(15.4, 21)], width=w, cap="round")
    elif kind == "fitness":
        Line(points=[*P(2, 12), *P(7, 12), *P(10, 5), *P(14, 19), *P(17, 12), *P(22, 12)],
             width=w, joint="round", cap="round")
    elif kind == "focus":
        Line(circle=(*P(12, 12), 9 * s), width=w)
        Line(circle=(*P(12, 12), 5 * s), width=w)
        x, y = P(12, 12)
        Ellipse(pos=(x - 1.9 * s, y - 1.9 * s), size=(3.8 * s, 3.8 * s))
    elif kind == "auto":
        Line(points=[*P(13, 2), *P(5, 13), *P(11, 13), *P(10, 22), *P(19, 10), *P(13, 10), *P(13, 2)],
             width=w, joint="round")
    elif kind == "settings":
        for y, x in ((6, 8), (12, 16), (18, 10)):
            Line(points=[*P(3, y), *P(21, y)], width=w, cap="round")
            kx, ky = P(x, y)
            Color(*bg)
            Ellipse(pos=(kx - 3 * s, ky - 3 * s), size=(6 * s, 6 * s))
            Color(*color)
            Line(circle=(kx, ky, 3 * s), width=w)


class Icon(Widget):
    kind = StringProperty("voice")
    color = ListProperty([1, 1, 1, 1])

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self.draw, size=self.draw, kind=self.draw, color=self.draw)

    def draw(self, *_):
        self.canvas.clear()
        with self.canvas:
            draw_icon(self.kind, self.center_x, self.center_y, min(self.size), self.color)


class NavItem(ButtonBehavior, BoxLayout):
    kind = StringProperty("voice")
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
        k = self.knob
        off, on = (0.19, 0.21, 0.20), ACCENT[:3]
        with self.canvas:
            Color(*[off[i] + (on[i] - off[i]) * k for i in range(3)], 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[self.height / 2])
            Color(1, 1, 1, 1)
            d = self.height - dp(6)
            Ellipse(pos=(self.x + dp(3) + k * (self.width - self.height), self.y + dp(3)), size=(d, d))


class Bar(Widget):
    value = NumericProperty(0)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self.draw, size=self.draw, value=self.draw)

    def draw(self, *_):
        self.canvas.clear()
        with self.canvas:
            Color(0.12, 0.14, 0.13, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[self.height / 2])
            if self.value > 0.01:
                Color(*MINT)
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
            Color(*MINT)
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
            Color(*ACCENT[:3], 1)
            Ellipse(pos=(cx - r, cy - r), size=(2 * r, 2 * r))
            draw_icon("voice", cx, cy, r * 1.0, (0, 0, 0, 1), bg=ACCENT)


class Backdrop(Widget):
    """Vertical gradient plus soft glow orbs."""

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
            for (ox, oy, col, base) in ((0.92, 0.94, ACCENT[:3], 0.60), (0.05, 0.12, (0.10, 0.52, 0.42), 0.45)):
                cx, cy = self.x + self.width * ox, self.y + self.height * oy
                for i in range(9):
                    f = (i + 1) / 9
                    r = self.width * base * (1 - f * 0.88)
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
        cx, cy = self.center_x, self.center_y + self.bob * dp(7)
        r = min(self.size) / 2 - dp(8)
        ex, ey, h = r * 0.38, cy + r * 0.22, r * 0.17 * self.blink
        with self.canvas:
            Color(*ACCENT[:3], 0.14)
            Ellipse(pos=(cx - r * 1.22, cy - r * 1.22), size=(r * 2.44, r * 2.44))
            Color(*SOFT)
            Line(circle=(cx, cy, r), width=dp(2.4))
            Line(points=[cx - ex, ey - h, cx - ex, ey + h], width=dp(3.2), cap="round")
            Line(points=[cx + ex, ey - h, cx + ex, ey + h], width=dp(3.2), cap="round")
            Line(circle=(cx, cy, r * 0.56, 128, 232), width=dp(3.2), cap="round")

    def start_idle(self):
        Animation.cancel_all(self)
        f = Animation(bob=1, d=1.7, t="in_out_sine") + Animation(bob=-1, d=1.7, t="in_out_sine")
        f.repeat = True
        f.start(self)
        b = Animation(d=3.0) + Animation(blink=0, d=0.08) + Animation(blink=1, d=0.12)
        b.repeat = True
        b.start(self)


class LockScreen(Screen):
    pass


class WelcomeScreen(Screen):
    def _items(self):
        i = self.ids
        return [i.wl_greet, i.wl_hi, i.wl_welcome, i.wl_qcard, i.smile, i.wl_btn]

    def on_pre_enter(self, *a):
        app = App.get_running_app()
        name = app.store.data["profile"].get("name", "SK") or "SK"
        self.ids.wl_greet.text = quotes.greeting()
        self.ids.wl_hi.text = f"Hi [color=#59C298]{name}[/color]"
        self.ids.wl_quote.text = f"\u201c{app.quote}\u201d"
        for w in self._items():
            w.opacity = 0

    def on_enter(self, *a):
        for n, w in enumerate(self._items()):
            Clock.schedule_once(lambda dt, w=w: Animation(opacity=1, d=0.6, t="out_quad").start(w), n * 0.2)
        self.ids.smile.start_idle()


class HomeScreen(Screen):
    pass


class AriseApp(App):
    def build(self):
        self.title = "Arise"
        Window.clearcolor = (0, 0, 0, 1)
        Window.softinput_mode = "below_target"
        self.store = Store()
        self.guard = PinGuard(self.store)
        self.fit = Fitness(self.store)
        self.paused_at = None
        self.last_active = time.time()
        self.setup_mode = False
        self.welcomed = False
        self.quote = quotes.daily()
        self.sm = Builder.load_string(KV)
        self._wide = None
        self._spacer = Widget()
        self._brand = Label(text='ARISE', bold=True, font_size=dp(20), color=ACCENT, size_hint_y=None, height=dp(64))
        Window.bind(width=lambda *a: self.relayout())
        Window.bind(on_touch_down=lambda *a: setattr(self, "last_active", time.time()))
        return self.sm

    @property
    def home(self):
        return self.sm.get_screen("home")

    @property
    def lock(self):
        return self.sm.get_screen("lock")

    def on_start(self):
        android_api.request_permissions()
        focus.sync(self.store)
        self.load_ui()
        self.show_lock()
        self.home.ids.mic.start()
        self.relayout()
        self.home.ids.quote_lbl.text = f"\u201c{self.quote}\u201d"
        a = Animation(opacity=0.5, d=1.4, t="in_out_sine") + Animation(opacity=1, d=1.4, t="in_out_sine")
        a.repeat = True
        a.start(self.lock.ids.logo)
        Clock.schedule_once(lambda dt: self.fit.start_steps(), 4)
        Clock.schedule_interval(self.tick, 20)
        Clock.schedule_interval(self.refresh_sports, 3)
        Clock.schedule_interval(self.rotate_quote, 8)

    # ------------------------------------------------------------ helpers
    def fade_in(self, widget):
        widget.opacity = 0
        Animation(opacity=1, d=0.5, t="out_quad").start(widget)

    def next_quote(self):
        self.quote = random.choice([q for q in quotes.QUOTES if q != self.quote])
        for lbl in (self.sm.get_screen("welcome").ids.wl_quote, self.home.ids.quote_lbl):
            lbl.text = f"\u201c{self.quote}\u201d"
            self.fade_in(lbl)

    def rotate_quote(self, dt):
        if self.sm.current == "welcome" or (self.sm.current == "home" and self.home.ids.pages.current == "voice"):
            self.next_quote()

    def relayout(self):
        """Phone: bottom bar. Wide window (.exe / tablet): side rail."""
        wide = Window.width >= dp(760)
        if wide == self._wide:
            return
        self._wide = wide
        ids = self.home.ids
        shell, nav = ids.shell, ids.nav
        shell.orientation = "horizontal" if wide else "vertical"
        shell.remove_widget(nav)
        shell.add_widget(nav, index=len(shell.children) if wide else 0)
        nav.orientation = "vertical" if wide else "horizontal"
        nav.size_hint = (None, 1) if wide else (1, None)
        nav.width, nav.height = dp(104), dp(66)
        nav.padding = (dp(8), dp(10)) if wide else (dp(6), dp(4))
        for n in PAGES:
            it = ids["nav_" + n]
            it.size_hint = (1, None) if wide else (1, 1)
            it.height = dp(74)
        for w in (self._brand, self._spacer):
            if w.parent:
                nav.remove_widget(w)
        if wide:
            nav.add_widget(self._brand, index=len(nav.children))
            nav.add_widget(self._spacer)

    def goto(self, page):
        ids = self.home.ids
        if ids.pages.current == page:
            return
        ids.pages.current = page
        for n in PAGES:
            ids["nav_" + n].selected = (n == page)
        {"fitness": self.refresh_sports, "focus": self.refresh_focus,
         "auto": self.refresh_access, "settings": self.refresh_log}.get(page, lambda: None)()

    # ------------------------------------------------------------ security
    def show_lock(self, *_):
        self.setup_mode = not self.guard.has_pin()
        ids = self.lock.ids
        ids.pin.text = ""
        ids.status.text = ""
        ids.title.text = "Create a PIN (4-8 digits)" if self.setup_mode else "Enter your PIN"
        ids.go.text = "Save PIN" if self.setup_mode else "Unlock"
        ids.dev.opacity = 0 if self.setup_mode else 1
        ids.dev.disabled = self.setup_mode
        self.sm.current = "lock"

    def submit_pin(self):
        ids = self.lock.ids
        pin = ids.pin.text
        if self.setup_mode:
            if not (4 <= len(pin) <= 8):
                ids.status.text = "PIN must be 4 to 8 digits"
                return
            self.guard.set_pin(pin)
            return self.unlock()
        ok, msg = self.guard.check(pin)
        if ok:
            self.unlock()
        else:
            ids.status.text = msg
            ids.pin.text = ""

    def device_unlock(self):
        def done(ok):
            if ok:
                self.store.log("Unlocked with device credential")
                self.unlock()
            else:
                self.lock.ids.status.text = "Device unlock unavailable or cancelled"
        android_api.device_unlock(done)

    def unlock(self):
        self.lock.ids.pin.text = ""
        self.last_active = time.time()
        if not self.welcomed:
            self.welcomed = True
            self.sm.current = "welcome"
        else:
            self.sm.current = "home"
        self.refresh_all()

    def enter_home(self):
        self.last_active = time.time()
        self.sm.current = "home"

    def _autolock_s(self):
        return max(15, int(self.store.data.get("autolock_seconds", 60)))

    def on_pause(self):
        self.paused_at = time.time()
        return True

    def on_resume(self):
        if self.paused_at and time.time() - self.paused_at > self._autolock_s():
            self.show_lock()
        self.paused_at = None
        self.fit.start_steps()

    def tick(self, dt):
        if self.sm.current in ("home", "welcome") and time.time() - self.last_active > self._autolock_s():
            self.show_lock()
        automations.check_schedule(self.store)
        if self.sm.current == "home":
            self.home.ids.fo_status.text = focus.status_text(self.store)

    # ------------------------------------------------------------ voice + AI
    def listen(self):
        if not android_api.ANDROID:
            self.show_answer("Voice input works on your phone. Type a command below.")
            return
        android_api.listen(lambda t: self.process(t) if t else self.show_answer("I didn't catch that."))

    def process(self, text):
        text = (text or "").strip()
        if not text:
            return
        ids = self.home.ids
        ids.heard.text = f'You said: "{text}"'
        ids.typed.text = ""
        out = voice.handle(text, self.store, self.fit)
        if out is not None:
            return self.show_answer(out)
        if self.store.data["ai"]["key"].strip():
            self.show_answer("Thinking...", speak=False)
            threading.Thread(target=self._ask_ai, args=(text,), daemon=True).start()
        else:
            self.show_answer("Sorry, I didn't understand. Add an API key in Settings and I can answer anything.")

    def _ask_ai(self, text):
        ans = ai.ask(self.store, text)
        Clock.schedule_once(lambda dt: self.show_answer(ans))

    def show_answer(self, text, speak=True):
        lbl = self.home.ids.answer
        lbl.text = text
        self.fade_in(lbl)
        if speak:
            android_api.speak(text)

    # ------------------------------------------------------------ sports
    def refresh_sports(self, dt=None):
        if self.sm.current != "home" or self.home.ids.pages.current != "fitness":
            return
        ids, p = self.home.ids, self.store.data["profile"]
        m = self.fit.today_metrics()
        goal = max(1, int(p["step_goal"]))
        ids.steps_big.text = f"{m['steps']:,}"
        ids.goal_lbl.text = f"of {goal:,} steps"
        Animation(value=min(1, m["steps"] / goal), d=1.0, t="out_cubic").start(ids.ring)
        ids.st_km.text = f"[b][size={int(dp(22))}]{m['km']:.2f}[/size][/b]\n[color=#858E89]km[/color]"
        ids.st_kcal.text = f"[b][size={int(dp(22))}]{int(m['kcal'])}[/size][/b]\n[color=#858E89]kcal[/color]"
        ids.st_min.text = f"[b][size={int(dp(22))}]{int(m['minutes'])}[/size][/b]\n[color=#858E89]active min[/color]"
        st = self.fit.workout_stats()
        if st:
            pace = f"{int(st['pace'])}:{int(st['pace'] % 1 * 60):02d} min/km" if st["pace"] else "--"
            ids.wk_lbl.text = (f"{st['secs'] // 60:02d}:{st['secs'] % 60:02d}   {st['km']:.2f} km   "
                               f"{pace}   {int(st['kcal'])} kcal")
            ids.wk_btn.text = "Stop workout"
        else:
            ids.wk_btn.text = "Start workout"
            ids.wk_lbl.text = "Not running"
            last = self.store.data["workouts"][-3:]
            ids.wk_hist.text = ("Recent: " + " | ".join(f"{w['date'][5:]} {w['km']:.1f} km" for w in reversed(last))
                                if last else ("Step tracking needs the Android app." if not android_api.ANDROID
                                              else "Allow 'Physical activity' permission to count steps."))
        self.draw_history(goal)

    def draw_history(self, goal):
        box = self.home.ids.hist_box
        box.clear_widgets()
        hist = self.fit.history()
        if not hist and not android_api.ANDROID:
            return
        for d, v in hist:
            row = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(10))
            row.add_widget(Label(text=d[5:], size_hint_x=None, width=dp(52), color=MUTED, font_size=dp(12)))
            row.add_widget(Bar(value=v / goal, size_hint_y=None, height=dp(10), pos_hint={"center_y": .5}))
            row.add_widget(Label(text=f"{v:,}", size_hint_x=None, width=dp(58), font_size=dp(12)))
            box.add_widget(row)

    def toggle_workout(self):
        msg = self.fit.stop_workout() if self.fit.workout_active() else self.fit.start_workout()
        self.show_answer(msg, speak=False)
        self.refresh_sports()

    # ------------------------------------------------------------ focus
    def save_focus(self):
        ids, f = self.home.ids, self.store.data["focus"]
        if f["strict"] and focus.is_active(self.store):
            ids.fo_status.text = "Strict mode: locked until focus ends"
            return
        s, e = ids.fo_start.text.strip(), ids.fo_end.text.strip()
        if not (focus.valid_time(s) and focus.valid_time(e)):
            ids.fo_status.text = "Use 24h times like 09:00"
            return
        f["enabled"], f["strict"] = ids.fo_enabled.active, ids.fo_strict.active
        f["schedules"] = [{"start": s, "end": e}]
        f["blocked"] = [a.strip() for a in ids.fo_apps.text.split(",") if a.strip()]
        focus.sync(self.store)
        self.store.log("Focus settings saved")
        self.refresh_focus()

    def start_focus(self):
        mins = int(self.home.ids.fo_mins.text or 25)
        focus.start_for(self.store, max(1, mins))
        self.refresh_focus()

    def stop_focus(self):
        ok, msg = focus.stop(self.store)
        self.refresh_focus()
        if not ok:
            self.home.ids.fo_status.text = msg

    def open_accessibility(self):
        android_api.open_accessibility_settings()

    def refresh_focus(self):
        ids = self.home.ids
        ids.fo_status.text = focus.status_text(self.store)
        ids.fo_access.text = ("Blocking service is enabled." if android_api.accessibility_enabled() else
                              "Not enabled yet. Tap below, open 'Arise Focus' and turn it on.")

    # ------------------------------------------------------------ automations
    def add_auto(self):
        ids = self.home.ids
        trig = "time" if ids.sp_trig.text == "Daily time" else "voice"
        val = ids.in_val.text.strip()
        if not val:
            return
        if trig == "time" and not focus.valid_time(val):
            ids.in_val.text = ""
            ids.in_val.hint_text = "Use 24h time like 07:30"
            return
        self.store.data["automations"].append(
            {"trigger": trig, "value": val, "action": ids.sp_act.text, "param": ids.in_param.text.strip()})
        self.store.save()
        ids.in_val.text = ids.in_param.text = ""
        self.refresh_autos()

    def del_auto(self, i):
        del self.store.data["automations"][i]
        self.store.save()
        self.refresh_autos()

    def refresh_autos(self):
        box = self.home.ids.auto_list
        box.clear_widgets()
        autos = self.store.data["automations"]
        if not autos:
            box.add_widget(Factory.Muted(text="No rules yet. Add one above."))
        for i, a in enumerate(autos):
            row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
            lab = Label(text=f'{a["trigger"]}: {a["value"]}\n[color=#858E89]{a["action"]} {a["param"]}[/color]',
                        markup=True, halign="left", valign="middle", font_size=dp(14))
            lab.bind(size=lambda w, s: setattr(w, "text_size", s))
            btn = Factory.Btn(text="Delete", size_hint_x=None, width=dp(80), height=dp(40), bg=(.75, .22, .30, 1), color=(1, 1, 1, 1),
                              pos_hint={"center_y": .5})
            btn.bind(on_release=lambda b, i=i: self.del_auto(i))
            row.add_widget(lab)
            row.add_widget(btn)
            box.add_widget(row)

    # ------------------------------------------------------------ auto-reply
    def save_autoreply(self):
        ids, ar = self.home.ids, self.store.data["autoreply"]
        ar["enabled"] = ids.ar_enabled.active
        ar["delay_minutes"] = int(ids.ar_delay.text or 10)
        ar["message"] = ids.ar_msg.text.strip() or ar["message"]
        ar["only_contacts"] = [c.strip() for c in ids.ar_contacts.text.split(",") if c.strip()]
        ar["cooldown_minutes"] = int(ids.ar_cool.text or 60)
        self.store.save()
        self.store.log("Auto-reply settings saved (enabled=%s)" % ar["enabled"])
        self.refresh_access()

    def open_access(self):
        android_api.open_notification_access_settings()

    def refresh_access(self):
        ok = android_api.notification_access_enabled()
        self.home.ids.ar_access.text = ("Notification access: granted." if ok else
                                        "Notification access: not granted. Tap the button below.")

    # ------------------------------------------------------------ settings / log
    def save_settings(self):
        ids, d = self.home.ids, self.store.data
        d["ai"]["key"] = ids.st_key.text.strip()
        d["ai"]["model"] = ids.st_model.text.strip() or "gpt-4o-mini"
        d["playlist"] = ids.st_playlist.text.strip()
        d["autolock_seconds"] = int(ids.st_lock.text or 60)
        d["profile"] = {"name": ids.st_name.text.strip() or "SK", "height_cm": int(ids.st_h.text or 170),
                        "weight_kg": int(ids.st_w.text or 65), "step_goal": int(ids.st_goal.text or 8000)}
        contacts = {}
        for part in ids.st_contacts.text.split(","):
            if "=" in part:
                k, v = part.split("=", 1)
                contacts[k.strip().lower()] = v.strip()
        d["contacts"] = contacts
        self.store.save()
        if ids.st_pin.text and 4 <= len(ids.st_pin.text) <= 8:
            self.guard.set_pin(ids.st_pin.text)
        ids.st_pin.text = ""
        self.refresh_hello()
        self.store.log("Settings saved")

    def refresh_log(self):
        self.home.ids.log_label.text = self.store.read_log()

    def refresh_hello(self):
        name = self.store.data["profile"].get("name", "SK") or "SK"
        self.home.ids.hello.text = f"{quotes.greeting()}, {name}"

    def load_ui(self):
        ids, d = self.home.ids, self.store.data
        ar, f, p = d["autoreply"], d["focus"], d["profile"]
        ids.ar_enabled.active = ar["enabled"]
        ids.ar_delay.text = str(ar["delay_minutes"])
        ids.ar_msg.text = ar["message"]
        ids.ar_contacts.text = ", ".join(ar["only_contacts"])
        ids.ar_cool.text = str(ar["cooldown_minutes"])
        ids.fo_enabled.active, ids.fo_strict.active = f["enabled"], f["strict"]
        ids.fo_start.text, ids.fo_end.text = f["schedules"][0]["start"], f["schedules"][0]["end"]
        ids.fo_apps.text = ", ".join(f["blocked"])
        ids.st_name.text = p.get("name", "SK")
        ids.st_key.text, ids.st_model.text = d["ai"]["key"], d["ai"]["model"]
        ids.st_playlist.text = d["playlist"]
        ids.st_lock.text = str(d["autolock_seconds"])
        ids.st_contacts.text = ", ".join(f"{k}={v}" for k, v in d["contacts"].items())
        ids.st_h.text, ids.st_w.text, ids.st_goal.text = str(p["height_cm"]), str(p["weight_kg"]), str(p["step_goal"])
        self.refresh_hello()

    def refresh_all(self):
        self.refresh_autos()
        self.refresh_access()
        self.refresh_focus()
        self.refresh_log()
        self.refresh_hello()


if __name__ == "__main__":
    AriseApp().run()
