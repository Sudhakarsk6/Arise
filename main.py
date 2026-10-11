import re, threading, time
from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Line
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from arise import ai, android_api, automations, focus, voice
from arise.fitness import Fitness
from arise.security import PinGuard
from arise.storage import Store

KV = '''
#:import FadeTransition kivy.uix.screenmanager.FadeTransition
#:import dp kivy.metrics.dp

<Btn@Button>:
    size_hint_y: None
    height: dp(48)
    background_normal: ''
    background_color: 0.36, 0.30, 0.85, 1

<Field@TextInput>:
    size_hint_y: None
    height: dp(44)
    multiline: False
    write_tab: False

<Lbl@Label>:
    color: 1, 1, 1, 1
    size_hint_y: None
    text_size: self.width, None
    height: self.texture_size[1] + dp(6)
    halign: 'left'

<Stat@Label>:
    markup: True
    halign: 'center'
    valign: 'middle'

<Grid@GridLayout>:
    cols: 1
    size_hint_y: None
    height: self.minimum_height
    padding: dp(12)
    spacing: dp(8)

<LockScreen>:
    name: 'lock'
    BoxLayout:
        orientation: 'vertical'
        padding: dp(30)
        spacing: dp(12)
        Widget:
        Label:
            id: logo
            text: 'ARISE'
            font_size: dp(44)
            bold: True
            size_hint_y: None
            height: dp(70)
        Label:
            id: title
            size_hint_y: None
            height: dp(30)
        Field:
            id: pin
            password: True
            input_filter: 'int'
            hint_text: 'PIN'
            halign: 'center'
            on_text_validate: app.submit_pin()
        Label:
            id: status
            color: 1, 0.5, 0.5, 1
            size_hint_y: None
            height: dp(30)
        Btn:
            id: go
            on_release: app.submit_pin()
        Btn:
            id: dev
            text: 'Use fingerprint / device lock'
            background_color: 0.2, 0.2, 0.3, 1
            on_release: app.device_unlock()
        Widget:

<HomeScreen>:
    name: 'home'
    TabbedPanel:
        do_default_tab: False
        tab_width: dp(78)
        TabbedPanelItem:
            text: 'Voice'
            BoxLayout:
                orientation: 'vertical'
                padding: dp(12)
                spacing: dp(10)
                Lbl:
                    text: 'Try: "play my playlist", "call mom", "open WhatsApp", "how many steps", "start focus for 30 minutes", or ask me anything.'
                Btn:
                    id: speak_btn
                    text: 'SPEAK'
                    height: dp(96)
                    font_size: dp(22)
                    on_release: app.listen()
                Lbl:
                    id: heard
                Lbl:
                    id: answer
                    color: 0.6, 1, 0.7, 1
                Field:
                    id: typed
                    hint_text: 'or type a command'
                    on_text_validate: app.process(self.text)
                Btn:
                    text: 'Run typed command'
                    on_release: app.process(typed.text)
                Widget:
        TabbedPanelItem:
            text: 'Sports'
            ScrollView:
                Grid:
                    FloatLayout:
                        size_hint_y: None
                        height: dp(250)
                        Ring:
                            id: ring
                            size_hint: None, None
                            size: dp(230), dp(230)
                            pos_hint: {'center_x': .5, 'center_y': .5}
                        Label:
                            id: steps_big
                            text: '0'
                            font_size: dp(42)
                            bold: True
                            pos_hint: {'center_x': .5, 'center_y': .55}
                            size_hint: None, None
                            size: dp(160), dp(60)
                        Label:
                            id: goal_lbl
                            text: 'steps'
                            color: 0.7, 0.7, 0.8, 1
                            pos_hint: {'center_x': .5, 'center_y': .4}
                            size_hint: None, None
                            size: dp(160), dp(30)
                    GridLayout:
                        cols: 3
                        size_hint_y: None
                        height: dp(70)
                        Stat:
                            id: st_km
                        Stat:
                            id: st_kcal
                        Stat:
                            id: st_min
                    Lbl:
                        text: 'Last 7 days'
                        bold: True
                    BoxLayout:
                        id: hist_box
                        orientation: 'vertical'
                        size_hint_y: None
                        height: dp(7 * 30)
                    Lbl:
                        text: 'GPS workout (run / walk / cycle)'
                        bold: True
                    Lbl:
                        id: wk_lbl
                        text: 'Not running'
                    Btn:
                        id: wk_btn
                        text: 'Start workout'
                        on_release: app.toggle_workout()
                    Lbl:
                        id: wk_hist
                        color: 0.7, 0.7, 0.8, 1
        TabbedPanelItem:
            text: 'Focus'
            ScrollView:
                Grid:
                    Lbl:
                        id: fo_status
                        font_size: dp(20)
                        bold: True
                    Lbl:
                        text: 'Block apps on a daily schedule'
                    Switch:
                        id: fo_enabled
                        size_hint_y: None
                        height: dp(40)
                    Lbl:
                        text: 'From (HH:MM, 24h)'
                    Field:
                        id: fo_start
                    Lbl:
                        text: 'Until (HH:MM, 24h). Overnight is fine, e.g. 22:00 to 06:00'
                    Field:
                        id: fo_end
                    Lbl:
                        text: 'Blocked apps (names or package ids, comma separated)'
                    Field:
                        id: fo_apps
                    Lbl:
                        text: 'Strict mode: cannot be switched off while focus is active'
                    Switch:
                        id: fo_strict
                        size_hint_y: None
                        height: dp(40)
                    Btn:
                        text: 'Save focus settings'
                        on_release: app.save_focus()
                    Lbl:
                        text: 'Quick session (minutes)'
                    Field:
                        id: fo_mins
                        text: '25'
                        input_filter: 'int'
                    Btn:
                        text: 'Start focus now'
                        background_color: 0.15, 0.6, 0.4, 1
                        on_release: app.start_focus()
                    Btn:
                        text: 'Stop focus'
                        background_color: 0.7, 0.2, 0.2, 1
                        on_release: app.stop_focus()
                    Lbl:
                        id: fo_access
                    Btn:
                        text: 'Enable blocking (Accessibility)'
                        background_color: 0.2, 0.2, 0.3, 1
                        on_release: app.open_accessibility()
        TabbedPanelItem:
            text: 'Automate'
            BoxLayout:
                orientation: 'vertical'
                padding: dp(8)
                spacing: dp(6)
                Spinner:
                    id: sp_trig
                    text: 'Voice phrase'
                    values: ['Voice phrase', 'Daily time']
                    size_hint_y: None
                    height: dp(42)
                Field:
                    id: in_val
                    hint_text: 'phrase (e.g. start my day) or time HH:MM (24h)'
                Spinner:
                    id: sp_act
                    text: 'open_app'
                    values: ['open_app', 'open_url', 'youtube_playlist', 'speak', 'send_sms', 'quiet_mode']
                    size_hint_y: None
                    height: dp(42)
                Field:
                    id: in_param
                    hint_text: 'app name / URL / text / number|text'
                Btn:
                    text: 'Add automation'
                    on_release: app.add_auto()
                ScrollView:
                    GridLayout:
                        id: auto_list
                        cols: 1
                        size_hint_y: None
                        height: self.minimum_height
                        spacing: dp(4)
        TabbedPanelItem:
            text: 'Auto-reply'
            ScrollView:
                Grid:
                    Lbl:
                        text: 'Auto-reply enabled'
                    Switch:
                        id: ar_enabled
                        size_hint_y: None
                        height: dp(40)
                    Lbl:
                        text: 'Reply if I have not opened the chat within (minutes)'
                    Field:
                        id: ar_delay
                        input_filter: 'int'
                    Lbl:
                        text: 'Message'
                    Field:
                        id: ar_msg
                    Lbl:
                        text: 'Only these contacts (comma separated, empty = everyone)'
                    Field:
                        id: ar_contacts
                    Lbl:
                        text: 'Max one reply per contact every (minutes)'
                    Field:
                        id: ar_cool
                        input_filter: 'int'
                    Btn:
                        text: 'Save auto-reply'
                        on_release: app.save_autoreply()
                    Lbl:
                        id: ar_access
                    Btn:
                        text: 'Grant notification access'
                        background_color: 0.2, 0.2, 0.3, 1
                        on_release: app.open_access()
        TabbedPanelItem:
            text: 'Log'
            BoxLayout:
                orientation: 'vertical'
                padding: dp(8)
                spacing: dp(6)
                Btn:
                    text: 'Refresh'
                    on_release: app.refresh_log()
                ScrollView:
                    Label:
                        id: log_label
                        size_hint_y: None
                        text_size: self.width, None
                        height: self.texture_size[1]
                        halign: 'left'
                        valign: 'top'
        TabbedPanelItem:
            text: 'Settings'
            ScrollView:
                Grid:
                    Lbl:
                        text: 'AI API key (stored only on this device)'
                    Field:
                        id: st_key
                        password: True
                    Lbl:
                        text: 'AI model'
                    Field:
                        id: st_model
                    Lbl:
                        text: 'YouTube playlist (link or ID)'
                    Field:
                        id: st_playlist
                    Lbl:
                        text: 'Contacts for voice calls / SMS (name=number, comma separated)'
                    Field:
                        id: st_contacts
                    Lbl:
                        text: 'Height (cm)  /  Weight (kg)  /  Daily step goal'
                    BoxLayout:
                        size_hint_y: None
                        height: dp(44)
                        spacing: dp(6)
                        Field:
                            id: st_h
                            input_filter: 'int'
                        Field:
                            id: st_w
                            input_filter: 'int'
                        Field:
                            id: st_goal
                            input_filter: 'int'
                    Lbl:
                        text: 'Auto-lock after (seconds, min 15)'
                    Field:
                        id: st_lock
                        input_filter: 'int'
                    Lbl:
                        text: 'New PIN (leave empty to keep current)'
                    Field:
                        id: st_pin
                        password: True
                        input_filter: 'int'
                    Btn:
                        text: 'Save settings'
                        on_release: app.save_settings()
                    Btn:
                        text: 'Lock now'
                        background_color: 0.7, 0.2, 0.2, 1
                        on_release: app.show_lock()

ScreenManager:
    transition: FadeTransition(duration=0.25)
    LockScreen:
    HomeScreen:
'''


class Ring(Widget):
    """Animated circular progress (0..1)."""
    value = NumericProperty(0)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self.redraw, size=self.redraw, value=self.redraw)

    def redraw(self, *_):
        self.canvas.clear()
        cx, cy = self.center
        r = min(self.size) / 2 - dp(12)
        with self.canvas:
            Color(0.18, 0.18, 0.28, 1)
            Line(circle=(cx, cy, r), width=dp(10))
            Color(0.36, 0.92, 0.70, 1)
            if self.value > 0.005:
                Line(circle=(cx, cy, r, 0, 360 * min(self.value, 1)), width=dp(10), cap="round")


class LockScreen(Screen):
    pass


class HomeScreen(Screen):
    pass


class AriseApp(App):
    def build(self):
        self.title = "Arise"
        Window.clearcolor = (0.08, 0.08, 0.12, 1)
        self.store = Store()
        self.guard = PinGuard(self.store)
        self.fit = Fitness(self.store)
        self.paused_at = None
        self.last_active = time.time()
        self.setup_mode = False
        self.sm = Builder.load_string(KV)
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
        self.pulse(self.home.ids.speak_btn)
        self.breathe(self.lock.ids.logo)
        Clock.schedule_once(lambda dt: self.fit.start_steps(), 4)   # after permission prompt
        Clock.schedule_interval(self.tick, 20)
        Clock.schedule_interval(self.refresh_sports, 3)

    # ------------------------------------------------------------ animation helpers
    def pulse(self, btn):
        a = (Animation(background_color=(0.55, 0.45, 1, 1), d=0.9, t="in_out_sine") +
             Animation(background_color=(0.36, 0.30, 0.85, 1), d=0.9, t="in_out_sine"))
        a.repeat = True
        a.start(btn)

    def breathe(self, lbl):
        a = Animation(opacity=0.45, d=1.4, t="in_out_sine") + Animation(opacity=1, d=1.4, t="in_out_sine")
        a.repeat = True
        a.start(lbl)

    def fade_in(self, widget):
        widget.opacity = 0
        Animation(opacity=1, d=0.5, t="out_quad").start(widget)

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
        self.sm.current = "home"
        self.refresh_all()

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
        if self.sm.current == "home" and time.time() - self.last_active > self._autolock_s():
            self.show_lock()
        automations.check_schedule(self.store)
        if self.sm.current == "home":
            self.home.ids.fo_status.text = focus.status_text(self.store)

    # ------------------------------------------------------------ voice + AI
    def listen(self):
        if not android_api.ANDROID:
            self.show_answer("Voice input works on your phone. Type a command here.")
            return
        android_api.listen(lambda t: self.process(t) if t else self.show_answer("I didn't catch that."))

    def process(self, text):
        text = (text or "").strip()
        if not text:
            return
        ids = self.home.ids
        ids.heard.text = f'You: "{text}"'
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
        if self.sm.current != "home":
            return
        ids, p = self.home.ids, self.store.data["profile"]
        m = self.fit.today_metrics()
        goal = max(1, int(p["step_goal"]))
        ids.steps_big.text = f"{m['steps']:,}"
        ids.goal_lbl.text = f"of {goal:,} steps"
        Animation(value=min(1, m["steps"] / goal), d=1.0, t="out_cubic").start(ids.ring)
        ids.st_km.text = f"[b][size=22]{m['km']:.2f}[/size][/b]\nkm"
        ids.st_kcal.text = f"[b][size=22]{int(m['kcal'])}[/size][/b]\nkcal"
        ids.st_min.text = f"[b][size=22]{int(m['minutes'])}[/size][/b]\nactive min"
        if not self.fit.history():
            ids.wk_hist.text = ("Step tracking needs the Android phone app." if not android_api.ANDROID
                                else "Allow 'Physical activity' permission to count steps.")
        st = self.fit.workout_stats()
        if st:
            pace = f"{int(st['pace'])}:{int(st['pace'] % 1 * 60):02d} min/km" if st["pace"] else "--"
            ids.wk_lbl.text = (f"{st['secs'] // 60:02d}:{st['secs'] % 60:02d}   {st['km']:.2f} km   "
                               f"{pace}   {int(st['kcal'])} kcal")
            ids.wk_btn.text = "Stop workout"
        else:
            ids.wk_btn.text = "Start workout"
            last = self.store.data["workouts"][-3:]
            ids.wk_lbl.text = "Not running"
            if last:
                ids.wk_hist.text = "Recent: " + " | ".join(
                    f"{w['date'][5:]} {w['km']:.1f} km" for w in reversed(last))
        self.draw_history(goal)

    def draw_history(self, goal):
        box = self.home.ids.hist_box
        box.clear_widgets()
        for d, v in self.fit.history():
            row = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(6))
            row.add_widget(Label(text=d[5:], size_hint_x=None, width=dp(60)))
            row.add_widget(ProgressBar(max=goal, value=min(v, goal)))
            row.add_widget(Label(text=f"{v:,}", size_hint_x=None, width=dp(60)))
            box.add_widget(row)

    def toggle_workout(self):
        msg = self.fit.stop_workout() if self.fit.workout_active() else self.fit.start_workout()
        self.show_answer(msg)
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
        f["enabled"] = ids.fo_enabled.active
        f["strict"] = ids.fo_strict.active
        f["schedules"] = [{"start": s, "end": e}]
        f["blocked"] = [a.strip() for a in ids.fo_apps.text.split(",") if a.strip()]
        focus.sync(self.store)
        self.store.log("Focus settings saved")
        self.refresh_focus()

    def start_focus(self):
        mins = int(self.home.ids.fo_mins.text or 25)
        self.show_answer(focus.start_for(self.store, max(1, mins)), speak=False)
        self.refresh_focus()

    def stop_focus(self):
        self.show_answer(focus.stop(self.store)[1], speak=False)
        self.refresh_focus()

    def open_accessibility(self):
        android_api.open_accessibility_settings()

    def refresh_focus(self):
        ids = self.home.ids
        ids.fo_status.text = focus.status_text(self.store)
        ids.fo_access.text = ("Blocking service: ENABLED" if android_api.accessibility_enabled() else
                              "Blocking service: not enabled. Tap below, find 'Arise Focus' and turn it on.")

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
        for i, a in enumerate(self.store.data["automations"]):
            row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(6))
            lab = Label(text=f'{a["trigger"]}: {a["value"]}\n-> {a["action"]} {a["param"]}',
                        halign="left", valign="middle")
            lab.bind(size=lambda w, s: setattr(w, "text_size", s))
            btn = Button(text="Del", size_hint_x=None, width=dp(60))
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
        self.home.ids.ar_access.text = ("Notification access: GRANTED" if ok else
                                        "Notification access: NOT granted - tap the button below")

    # ------------------------------------------------------------ settings / log
    def save_settings(self):
        ids, d = self.home.ids, self.store.data
        d["ai"]["key"] = ids.st_key.text.strip()
        d["ai"]["model"] = ids.st_model.text.strip() or "gpt-4o-mini"
        d["playlist"] = ids.st_playlist.text.strip()
        d["autolock_seconds"] = int(ids.st_lock.text or 60)
        d["profile"] = {"height_cm": int(ids.st_h.text or 170), "weight_kg": int(ids.st_w.text or 65),
                        "step_goal": int(ids.st_goal.text or 8000)}
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
        self.show_answer("Settings saved.", speak=False)

    def refresh_log(self):
        self.home.ids.log_label.text = self.store.read_log()

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
        ids.st_key.text, ids.st_model.text = d["ai"]["key"], d["ai"]["model"]
        ids.st_playlist.text = d["playlist"]
        ids.st_lock.text = str(d["autolock_seconds"])
        ids.st_contacts.text = ", ".join(f"{k}={v}" for k, v in d["contacts"].items())
        ids.st_h.text, ids.st_w.text, ids.st_goal.text = str(p["height_cm"]), str(p["weight_kg"]), str(p["step_goal"])

    def refresh_all(self):
        self.refresh_autos()
        self.refresh_access()
        self.refresh_focus()
        self.refresh_log()
        self.refresh_sports()


if __name__ == "__main__":
    AriseApp().run()
