import json, os, re, shutil, threading, time, random
from datetime import date, datetime, timedelta

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
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivy.resources import resource_add_path
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

HERE = os.path.dirname(os.path.abspath(__file__))
resource_add_path(HERE)

from arise import ai, android_api, automations, backup, finance, focus, quotes, tracking, voice
from arise import scripts as scripts_mod
from arise.adapters import get_adapter
from arise.db import DB
from arise.fitness import Fitness
from arise.security import PinGuard
from arise.storage import Store
from arise.ui_widgets import (ACCENT, MUTED, RED, Seg, ScriptCard, Bar, Icon, NavItem, Toggle, Ring, MicButton,  # noqa: F401
                              Backdrop, Smiley, SpinnerRing, Chart)
from arise.vault import Vault

GROUPS = ("home", "auto", "track", "fin", "ai", "settings")
HEALTH_KINDS = list(tracking.HEALTH_KINDS)


class SplashScreen(Screen):
    logo_source = StringProperty("")


class LockScreen(Screen):
    pass


class HomeScreen(Screen):
    pass


def short(text, n=70):
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[:n - 1] + "..."


class AriseApp(App):
    # ------------------------------------------------------------------ startup
    def build(self):
        self.title = "Arise"
        Window.clearcolor = (0, 0, 0, 1)
        Window.softinput_mode = "below_target"
        self.store = Store()
        self.guard = PinGuard(self.store)
        self.fit = Fitness(self.store)
        self.cur_sub = {"auto": "scripts", "track": "health", "fin": "watch"}
        self.group = "home"
        self.ready = False
        self.setup_mode = False
        self.paused_at = None
        self.last_active = time.time()
        self.quote = quotes.daily()
        self.cur_aid = None
        self._ai_code = None
        self._reminded = set()
        self._wide = None
        self._spacer = Widget()
        self._brand = Label(text="ARISE", bold=True, font_size=dp(20), color=ACCENT, size_hint_y=None, height=dp(64))
        self.sm = Builder.load_file(os.path.join(HERE, "ui.kv"))
        self.sm.get_screen("splash").logo_source = self.logo_path()
        Window.bind(on_touch_down=lambda *a: setattr(self, "last_active", time.time()))
        Window.bind(width=lambda *a: self.relayout())
        return self.sm

    @property
    def h(self):
        return self.sm.get_screen("home").ids

    @property
    def lk(self):
        return self.sm.get_screen("lock").ids

    def logo_path(self):
        custom = self.store.data.get("logo_path", "")
        return custom if custom and os.path.exists(custom) else os.path.join(HERE, "assets", "logo.png")

    def on_start(self):
        self.t0 = time.time()
        self.sm.get_screen("splash").ids.ring.start()
        steps = [self._init_db, self._init_services, self._init_ui]

        def run(i, dt=None):
            steps[i]()
            if i + 1 < len(steps):
                Clock.schedule_once(lambda d: run(i + 1), 0.1)
            else:
                Clock.schedule_once(lambda d: self.show_lock(), max(0.1, 1.9 - (time.time() - self.t0)))
        Clock.schedule_once(lambda d: run(0), 0.2)

    def _init_db(self):
        path = os.path.join(self.store.base, "mylife.db")
        pending = path + ".restore"
        if os.path.exists(pending):                      # a restored backup is applied before opening
            if os.path.exists(path):
                shutil.copy(path, path + ".before-restore")
            os.replace(pending, path)
        self.db = DB(path)
        self.vault = Vault(os.path.join(self.store.base, "vault.json"))

    def _init_services(self):
        self.adapter = get_adapter()
        self.scripts = scripts_mod.Scripts(self.db, self.adapter, lambda: self.store.data.get("domains", []))
        android_api.request_permissions()
        focus.sync(self.store)
        self.ready = True

    def _init_ui(self):
        self.load_ui()
        self.h.mic.start()
        self.h.smile.start_idle()
        self.h.quote_lbl.text = f"\u201c{self.quote}\u201d"
        self.relayout()
        Clock.schedule_once(lambda dt: self.fit.start_steps(), 4)
        Clock.schedule_interval(self.tick, 20)
        Clock.schedule_interval(lambda dt: self.refresh_workout(), 2)
        Clock.schedule_interval(self.rotate_quote, 9)

    # ------------------------------------------------------------------ layout / navigation
    def relayout(self):
        wide = Window.width >= dp(760)
        if wide == self._wide or not self.sm.has_screen("home"):
            return
        self._wide = wide
        ids = self.h
        shell, nav = ids.shell, ids.nav
        shell.orientation = "horizontal" if wide else "vertical"
        shell.remove_widget(nav)
        shell.add_widget(nav, index=len(shell.children) if wide else 0)
        nav.orientation = "vertical" if wide else "horizontal"
        nav.size_hint = (None, 1) if wide else (1, None)
        nav.width, nav.height = dp(104), dp(66)
        for g in GROUPS:
            it = ids["nav_" + g]
            it.size_hint = (1, None) if wide else (1, 1)
            it.height = dp(74)
        for w in (self._brand, self._spacer):
            if w.parent:
                nav.remove_widget(w)
        if wide:
            nav.add_widget(self._brand, index=len(nav.children))
            nav.add_widget(self._spacer)

    def page_for(self, group):
        return group if group in ("home", "ai", "settings") else f"{group}_{self.cur_sub[group]}"

    def goto(self, group):
        self.group = group
        for g in GROUPS:
            self.h["nav_" + g].selected = (g == group)
        self.show_page(self.page_for(group))

    def sub(self, group, key):
        self.cur_sub[group] = key
        for w in self.sm.get_screen("home").walk():
            if isinstance(w, Seg) and w.group == group:
                w.refresh(key)
        self.goto(group)

    def show_page(self, page):
        self.h.pages.current = page
        for w in self.h.pages.current_screen.walk():          # keep each page's tab bar in sync
            if isinstance(w, Seg):
                w.refresh(self.cur_sub.get(w.group))
        {"home": self.refresh_home, "auto_scripts": self.refresh_scripts, "auto_rules": self.refresh_autos,
         "auto_focus": self.refresh_focus, "auto_reply": self.refresh_access, "track_health": self.refresh_health,
         "track_habits": self.refresh_habits, "track_money": self.refresh_money, "fin_watch": self.refresh_watch,
         "fin_paper": self.refresh_paper, "settings": self.refresh_logs}.get(page, lambda: None)()

    # ------------------------------------------------------------------ security
    def show_lock(self, *_):
        if self.ready:
            self.vault.lock()
        self.setup_mode = not self.guard.has_pin()
        ids = self.lk
        ids.pin.text = ""
        ids.status.text = ""
        ids.title.text = "Create a PIN (4-8 digits)" if self.setup_mode else "Enter your PIN"
        ids.go.text = "Save PIN" if self.setup_mode else "Unlock"
        ids.dev.opacity = 0 if self.setup_mode else 1
        ids.dev.disabled = self.setup_mode
        self.sm.current = "lock"

    def submit_pin(self):
        ids, pin = self.lk, self.lk.pin.text
        if self.setup_mode:
            if not (4 <= len(pin) <= 8):
                ids.status.text = "PIN must be 4 to 8 digits"
                return
            self.guard.set_pin(pin)
            self.db.audit("pin_created")
            return self.after_auth(pin)
        ok, msg = self.guard.check(pin)
        if ok:
            self.db.audit("unlock", "PIN")
            self.after_auth(pin)
        else:
            self.db.audit("unlock_failed", f"attempt {self.guard.fails}")
            ids.status.text = msg
            ids.pin.text = ""

    def device_unlock(self):
        def done(ok):
            if ok:
                self.db.audit("unlock", "device credential (vault stays locked)")
                self.after_auth(None)
            else:
                self.lk.status.text = "Device unlock unavailable or cancelled"
        android_api.device_unlock(done)

    def after_auth(self, pin):
        self.lk.pin.text = ""
        self.last_active = time.time()
        if pin:
            self.vault.unlock(pin)
            old = self.store.data["ai"].get("key", "")
            if old:                                         # migrate any plain-text key into the vault
                self.vault.set("ai_key", old)
                self.store.data["ai"]["key"] = ""
                self.store.save()
        self.sm.current = "home"
        self.goto("home")

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
            self.db.audit("auto_lock", "session expired")
            self.show_lock()
        automations.check_schedule(self.store)
        for aid in self.scripts.due():
            if aid not in self.scripts.running:
                self.scripts.run_async(aid, None, lambda r: None)
        hm = time.strftime("%H:%M")
        for hb in self.db.q("SELECT * FROM habits WHERE archived=0 AND reminder=?", (hm,)):
            key = (hb["id"], date.today().isoformat())
            if key not in self._reminded and not self._habit_done(hb["id"]):
                self._reminded.add(key)
                try:
                    self.adapter.notify("Habit reminder", hb["name"])
                except Exception:
                    android_api.speak(f"Reminder: {hb['name']}")
        if self.sm.current == "home":
            self.h.hm_focus.text = self._stat(focus.status_text(self.store).replace("Focus: ", ""), "focus")

    def rotate_quote(self, dt):
        if self.sm.current == "home" and self.h.pages.current == "home":
            self.next_quote()

    def next_quote(self):
        self.quote = random.choice([q for q in quotes.QUOTES if q != self.quote])
        self.h.quote_lbl.text = f"\u201c{self.quote}\u201d"
        self.h.quote_lbl.opacity = 0
        Animation(opacity=1, d=0.5).start(self.h.quote_lbl)

    # ------------------------------------------------------------------ helpers
    def popup(self, title, text):
        from kivy.uix.popup import Popup
        from kivy.uix.scrollview import ScrollView
        lab = Label(text=text, font_name="RobotoMono-Regular", font_size=dp(12), size_hint_y=None,
                    halign="left", valign="top")
        lab.bind(width=lambda w, v: setattr(w, "text_size", (v, None)))
        lab.bind(texture_size=lambda w, s: setattr(w, "height", s[1] + dp(10)))
        sv = ScrollView()
        sv.add_widget(lab)
        Popup(title=title, content=sv, size_hint=(.92, .7), separator_color=ACCENT,
              background_color=(.05, .06, .06, 1)).open()

    @staticmethod
    def _stat(value, label):
        return f"[b][size={int(dp(20))}]{value}[/size][/b]\n[color=#858E89]{label}[/color]"

    def _row(self, text, widgets=(), height=52, markup=True):
        row = BoxLayout(size_hint_y=None, height=dp(height), spacing=dp(8))
        lab = Label(text=text, markup=markup, halign="left", valign="middle", font_size=dp(14))
        lab.bind(size=lambda w, s: setattr(w, "text_size", s))
        row.add_widget(lab)
        for w in widgets:
            row.add_widget(w)
        return row

    def _chip(self, text, cb, w=84):
        c = Factory.Chip(text=text, size_hint_x=None, width=dp(w), pos_hint={"center_y": .5})
        c.bind(on_release=lambda *_: cb())
        return c

    def say(self, label, text, ok=True):
        label.text = text
        label.color = (0.55, 0.95, 0.76, 1) if ok else (1, 0.5, 0.55, 1)

    # ------------------------------------------------------------------ home
    def refresh_home(self):
        if not self.ready:
            return
        name = self.store.data["profile"].get("name", "SK") or "SK"
        ids = self.h
        ids.hello.text = quotes.greeting()
        ids.hi_name.text = f"Hi {name}"
        s = tracking.health_summary(self.db, "steps", "Day")
        ids.hm_steps.text = self._stat(f"{int(s['total']):,}" if s["available"] else "--", "steps today")
        ids.hm_focus.text = self._stat(focus.status_text(self.store).replace("Focus: ", ""), "focus")
        n = self.db.one("SELECT COUNT(*) c FROM runs WHERE substr(started_at,1,10)=?", (date.today().isoformat(),))["c"]
        ids.hm_runs.text = self._stat(n, "runs today")
        box = ids.script_list
        box.clear_widgets()
        autos = self.scripts.list()
        ids.home_empty.text = "" if autos else "No automations yet. Open Automations to import your first script."
        for a in autos:
            card = ScriptCard(title=a["title"], desc=short(a["description"] or a["category"]), icon=a["icon"],
                              run_cb=self.run_card, hist_cb=self.history_card, open_cb=lambda c: self.open_script(c.aid))
            card.aid = a["id"]
            self.fill_card(card, a)
            box.add_widget(card)

    def fill_card(self, card, a=None):
        a = a or self.scripts.get(card.aid)
        last = self.scripts.last_run(a["id"])
        if not a["enabled"]:
            card.status_line, card.status_color = "Needs review and approval before it can run", list(MUTED)
            card.btn_text = "Review"
        elif last is None:
            card.status_line, card.status_color = f"Never run  |  v{a.get('active_n') or '?'}  |  {a['schedule'] or 'manual'}", list(MUTED)
            card.btn_text = "Run"
        else:
            ok = last["status"] == "success"
            card.status_line = (f"{last['started_at'][5:16]}  |  {last['status'].title()}  |  {last['duration'] or 0:.1f}s  |  "
                                f"{short(last['result'] or '', 40)}")
            card.status_color = list(ACCENT if ok else RED)
            card.btn_text = "Run"

    def run_card(self, card):
        a = self.scripts.get(card.aid)
        if not a["enabled"]:
            return self.open_script(card.aid)
        card.btn_text, card.progress = "...", 2

        def prog(p, msg):
            Clock.schedule_once(lambda dt: (setattr(card, "progress", max(2, p)),
                                            setattr(card, "status_line", f"Running... {int(p)}%  {msg}")))

        def done(res):
            def ui(dt):
                card.progress = 0
                self.fill_card(card)
                if res["status"] != "success":
                    self.popup("Run failed", str(res["text"]))
            Clock.schedule_once(ui)
        self.scripts.run_async(card.aid, prog, done)

    def history_card(self, card):
        rows = self.scripts.history(card.aid, 12)
        txt = "\n\n".join(f"{r['started_at']}  {r['status'].upper()}  {r['duration'] or 0:.1f}s\n{r['result'] or ''}"
                          + (f"\n{r['log']}" if r["log"] else "") for r in rows) or "No runs yet."
        self.popup(f"History: {card.title}", txt)

    # ------------------------------------------------------------------ automations: scripts
    def refresh_scripts(self):
        if not self.ready:
            return
        box = self.h.sc_list
        box.clear_widgets()
        for a in self.scripts.list():
            state = f"v{a['active_n']} enabled" if a["enabled"] else "needs approval"
            box.add_widget(self._row(f"[b]{a['title']}[/b]\n[color=#858E89]{a['category']}  |  {state}[/color]",
                                     [self._chip("Open", lambda i=a["id"]: self.open_script(i), 70)]))
        if not box.children:
            box.add_widget(Factory.Muted(text="No scripts yet."))

    def sc_template(self):
        self.h.sc_code.text = scripts_mod.TEMPLATE

    def sc_import_path(self):
        p = self.h.sc_path.text.strip()
        try:
            if not p.lower().endswith(".py"):
                raise ValueError("choose a .py file")
            if os.path.getsize(p) > 64 * 1024:
                raise ValueError("file is larger than 64 KB")
            src = open(p, encoding="utf-8").read()
        except Exception as e:
            self.h.sc_report.text = f"[x] Could not read the file: {e}"
            return
        self._import(os.path.basename(p), src)

    def sc_import_code(self):
        src = self.h.sc_code.text
        if not src.strip():
            self.h.sc_report.text = "[x] Paste some code first."
            return
        self._import("pasted.py", src)

    def _import(self, name, src):
        res = self.scripts.import_source(name, src)
        self.h.sc_report.text = res["text"]
        self.refresh_scripts()
        self.open_script(res["id"])

    def open_script(self, aid):
        self.cur_aid = aid
        ids, a = self.h, self.scripts.get(aid)
        lat = self.scripts.latest_version(aid)
        ids.ed_head.text = a["title"]
        ids.ed_title.text, ids.ed_desc.text, ids.ed_sched.text = a["title"], a["description"], a["schedule"]
        ids.ed_cat.values, ids.ed_cat.text = scripts_mod.CATEGORIES, a["category"]
        ids.ed_icon.values, ids.ed_icon.text = scripts_mod.ICONS, a["icon"]
        ids.ed_code.text = lat["source"]
        self.show_version(aid, lat)
        self.cur_sub["auto"] = "scripts"
        self.group = "auto"
        for g in GROUPS:
            self.h["nav_" + g].selected = (g == "auto")
        self.h.pages.current = "auto_edit"

    def show_version(self, aid, v):
        ids = self.h
        ids.ed_report.text = v["report"]
        ids.ed_diff.text = short(self.scripts.diff(aid, v["id"]), 2500) if len(self.scripts.diff(aid, v["id"])) < 2500 \
            else self.scripts.diff(aid, v["id"])[:2500] + "\n..."
        perms = json.loads(v["permissions"] or "[]")
        ids.ed_perm.text = "Permissions this version needs: " + (", ".join(perms) if perms else "none")
        ids.ed_approve.text = f"Approve v{v['n']} and enable" + (f" (grants: {', '.join(perms)})" if perms else "")
        ids.ed_approve.disabled = v["status"] not in ("tested", "approved")
        a = self.scripts.get(aid)
        box = ids.ed_versions
        box.clear_widgets()
        for ver in self.scripts.versions(aid):
            mark = "ACTIVE" if ver["id"] == a["active_version_id"] else ver["status"]
            btns = []
            if ver["approved_at"] and ver["id"] != a["active_version_id"]:
                btns.append(self._chip("Roll back", lambda i=ver["id"]: self.ed_rollback(i), 92))
            btns.append(self._chip("View", lambda i=ver["id"]: self.ed_view(i), 64))
            box.add_widget(self._row(f"v{ver['n']}  |  {mark}  |  {ver['created_at'][5:16]}", btns, 44, markup=False))

    def ed_view(self, vid):
        v = self.scripts.version(vid)
        self.h.ed_code.text = v["source"]
        self.show_version(self.cur_aid, v)

    def ed_save_meta(self):
        i = self.h
        try:
            self.scripts.update_meta(self.cur_aid, i.ed_title.text, i.ed_desc.text, i.ed_cat.text, i.ed_icon.text, i.ed_sched.text)
            self.say(i.ed_msg, "Details saved.")
            i.ed_head.text = i.ed_title.text
        except ValueError as e:
            self.say(i.ed_msg, str(e), False)

    def ed_new_version(self):
        res = self.scripts.new_version(self.cur_aid, self.h.ed_code.text)
        self.show_version(self.cur_aid, self.scripts.version(res["version_id"]))
        self.say(self.h.ed_msg, "Saved. Review the checks and changes, then approve." if res["report"]["ok"]
                 else "Saved, but the checks FAILED - it cannot be approved until they pass.", res["report"]["ok"])

    def ed_approve(self):
        lat = self.scripts.latest_version(self.cur_aid)
        try:
            self.scripts.approve(self.cur_aid, lat["id"])
            self.say(self.h.ed_msg, f"v{lat['n']} approved and enabled.")
        except ValueError as e:
            self.say(self.h.ed_msg, str(e), False)
        self.show_version(self.cur_aid, lat)

    def ed_disable(self):
        self.scripts.set_enabled(self.cur_aid, False)
        self.say(self.h.ed_msg, "Disabled.")

    def ed_rollback(self, vid):
        try:
            self.scripts.rollback(self.cur_aid, vid)
            self.say(self.h.ed_msg, "Rolled back to the selected version.")
        except ValueError as e:
            self.say(self.h.ed_msg, str(e), False)
        self.show_version(self.cur_aid, self.scripts.version(vid))

    def ed_delete(self):
        self.scripts.delete(self.cur_aid)
        self.cur_aid = None
        self.sub("auto", "scripts")

    # ------------------------------------------------------------------ automations: rules / focus / reply
    def add_auto(self):
        ids = self.h
        trig = "time" if ids.sp_trig.text == "Daily time" else "voice"
        val = ids.in_val.text.strip()
        if not val:
            return
        if trig == "time" and not focus.valid_time(val):
            ids.in_val.text, ids.in_val.hint_text = "", "Use 24h time like 07:30"
            return
        self.store.data["automations"].append({"trigger": trig, "value": val, "action": ids.sp_act.text,
                                               "param": ids.in_param.text.strip()})
        self.store.save()
        ids.in_val.text = ids.in_param.text = ""
        self.refresh_autos()

    def del_auto(self, i):
        del self.store.data["automations"][i]
        self.store.save()
        self.refresh_autos()

    def refresh_autos(self):
        box = self.h.auto_list
        box.clear_widgets()
        autos = self.store.data["automations"]
        if not autos:
            box.add_widget(Factory.Muted(text="No rules yet. Add one above."))
        for i, a in enumerate(autos):
            d = Factory.Danger(text="Delete", size_hint_x=None, width=dp(80), height=dp(40), pos_hint={"center_y": .5})
            d.bind(on_release=lambda b, i=i: self.del_auto(i))
            box.add_widget(self._row(f'{a["trigger"]}: {a["value"]}\n[color=#858E89]{a["action"]} {a["param"]}[/color]', [d]))

    def save_focus(self):
        ids, f = self.h, self.store.data["focus"]
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
        self.db.audit("focus_settings")
        self.refresh_focus()

    def start_focus(self):
        focus.start_for(self.store, max(1, int(self.h.fo_mins.text or 25)))
        self.refresh_focus()

    def stop_focus(self):
        ok, msg = focus.stop(self.store)
        self.refresh_focus()
        if not ok:
            self.h.fo_status.text = msg

    def open_accessibility(self):
        android_api.open_accessibility_settings()

    def refresh_focus(self):
        ids = self.h
        ids.fo_status.text = focus.status_text(self.store)
        ids.fo_access.text = ("Blocking service is enabled." if android_api.accessibility_enabled() else
                              "Not enabled yet. Tap below, open 'Arise Focus' and turn it on.")

    def save_autoreply(self):
        ids, ar = self.h, self.store.data["autoreply"]
        ar["enabled"] = ids.ar_enabled.active
        ar["delay_minutes"] = int(ids.ar_delay.text or 10)
        ar["message"] = ids.ar_msg.text.strip() or ar["message"]
        ar["only_contacts"] = [c.strip() for c in ids.ar_contacts.text.split(",") if c.strip()]
        ar["cooldown_minutes"] = int(ids.ar_cool.text or 60)
        self.store.save()
        self.db.audit("autoreply_settings", f"enabled={ar['enabled']}")
        self.refresh_access()

    def open_access(self):
        android_api.open_notification_access_settings()

    def refresh_access(self):
        self.h.ar_access.text = ("Notification access: granted." if android_api.notification_access_enabled() else
                                 "Notification access: not granted. Tap the button below.")

    # ------------------------------------------------------------------ tracking: health
    def refresh_health(self):
        if not self.ready:
            return
        ids, p = self.h, self.store.data["profile"]
        if android_api.ANDROID:
            tracking.sync_device_steps(self.db, self.fit.steps_today())
        s = tracking.health_summary(self.db, "steps", "Day")
        goal = max(1, int(p["step_goal"]))
        if s["available"]:
            steps = int(s["total"])
            m = tracking.__dict__  # noqa
            from arise.fitness import metrics
            mm = metrics(steps, p["height_cm"], p["weight_kg"])
            ids.steps_big.text, ids.goal_lbl.text = f"{steps:,}", f"of {goal:,} steps"
            Animation(value=min(1, steps / goal), d=0.8, t="out_cubic").start(ids.ring)
            ids.st_km.text = self._stat(f"{mm['km']:.2f}", "km (estimate)")
            ids.st_kcal.text = self._stat(int(mm["kcal"]), "kcal (estimate)")
            ids.st_min.text = self._stat(int(mm["minutes"]), "active min (est.)")
            ids.hl_src.text = "Source: " + ", ".join(s["sources"]) + ". Distance and calories are estimates from your height and weight."
        else:
            ids.steps_big.text, ids.goal_lbl.text = "--", "no step data yet"
            ids.ring.value = 0
            for k, l in (("st_km", "km"), ("st_kcal", "kcal"), ("st_min", "active min")):
                ids[k].text = self._stat("--", l)
            ids.hl_src.text = "Unavailable: this device has not reported steps. You can add entries manually below."
        kind, period = ids.hl_rkind.text, ids.hl_period.text
        if kind not in HEALTH_KINDS:
            return
        r = tracking.health_summary(self.db, kind, period)
        if not r["available"]:
            ids.hl_summary.text = f"{kind.replace('_', ' ').title()} ({period.lower()}): unavailable - no entries in this period."
        else:
            parts = [f"Average {r['average']:.1f} {r['unit']}/day-entry", f"min {r['min']:.1f}", f"max {r['max']:.1f}",
                     f"{r['days_with_data']} day(s) with data"]
            if r["total"] is not None:
                parts.insert(0, f"Total {r['total']:,.1f} {r['unit']}")
            ids.hl_summary.text = (f"{kind.replace('_', ' ').title()} ({period.lower()})\n" + "  |  ".join(parts) +
                                   "\nSources: " + ", ".join(r["sources"]))
        days = {"Day": 7, "Week": 7, "Month": 30, "Year": 365}[period]
        daily = tracking.health_daily(self.db, kind, days)
        ids.hl_chart.kind = "bar" if days <= 31 else "line"
        ids.hl_chart.unit = tracking.HEALTH_KINDS[kind][0]
        ids.hl_chart.labels = [d for d, _ in daily]
        ids.hl_chart.series = [[v for _, v in daily]]
        self.refresh_workout()

    def hl_add(self):
        ids = self.h
        try:
            tracking.add_health(self.db, ids.hl_kind.text, float(ids.hl_val.text))
            ids.hl_val.text = ""
            self.say(ids.hl_msg, "Saved with source 'manual'.")
            self.refresh_health()
        except ValueError as e:
            self.say(ids.hl_msg, f"Could not save: {e}", False)

    def toggle_workout(self):
        msg = self.fit.stop_workout() if self.fit.workout_active() else self.fit.start_workout()
        self.h.wk_hist.text = msg
        self.refresh_workout()

    def refresh_workout(self):
        if not self.ready or self.h.pages.current != "track_health":
            return
        ids, st = self.h, self.fit.workout_stats()
        if st:
            pace = f"{int(st['pace'])}:{int(st['pace'] % 1 * 60):02d} min/km" if st["pace"] else "--"
            ids.wk_lbl.text = f"{st['secs'] // 60:02d}:{st['secs'] % 60:02d}   {st['km']:.2f} km   {pace}   {int(st['kcal'])} kcal"
            ids.wk_btn.text = "Stop workout"
        else:
            ids.wk_btn.text, ids.wk_lbl.text = "Start workout", "Not running"
            last = self.store.data["workouts"][-3:]
            if last:
                ids.wk_hist.text = "Recent: " + " | ".join(f"{w['date'][5:]} {w['km']:.1f} km" for w in reversed(last))
            elif not android_api.ANDROID and not ids.wk_hist.text:
                ids.wk_hist.text = "GPS workouts work on your phone."

    # ------------------------------------------------------------------ tracking: habits
    def _habit_done(self, hid):
        return date.today().isoformat() in {r["day"] for r in self.db.q("SELECT day FROM habit_logs WHERE habit_id=?", (hid,))}

    def hb_add(self):
        ids = self.h
        try:
            tracking.add_habit(self.db, ids.hb_name.text, ids.hb_rem.text.strip())
            ids.hb_name.text = ids.hb_rem.text = ""
            self.say(ids.hb_msg, "Habit added. Reminders fire while the app is running.")
            self.refresh_habits()
        except ValueError as e:
            self.say(ids.hb_msg, str(e), False)

    def toggle_habit(self, hid, done):
        tracking.set_done(self.db, hid, date.today().isoformat(), done)
        self.refresh_habits()

    def refresh_habits(self):
        if not self.ready:
            return
        box, lines = self.h.hb_list, []
        box.clear_widgets()
        for hb in self.db.q("SELECT * FROM habits WHERE archived=0 ORDER BY id"):
            cur, best = tracking.streaks(self.db, hb["id"])
            rate = tracking.completion(self.db, hb["id"], 30)
            tg = Toggle(size_hint=(None, None), size=(dp(54), dp(30)), pos_hint={"center_y": .5})
            tg.active = self._habit_done(hb["id"])
            tg.knob = 1.0 if tg.active else 0.0
            tg.bind(active=lambda w, v, i=hb["id"]: self.toggle_habit(i, v))
            rem = f"  |  reminder {hb['reminder']}" if hb["reminder"] else ""
            box.add_widget(self._row(f"[b]{hb['name']}[/b]\n[color=#858E89]streak {cur}  |  best {best}{rem}[/color]", [tg], 56))
            lines.append(f"{hb['name']}: {rate * 100:.0f}% of the last 30 days")
        if not box.children:
            box.add_widget(Factory.Muted(text="No habits yet."))
        data = tracking.habit_week_chart(self.db)
        self.h.hb_chart.labels, self.h.hb_chart.series = [d for d, _ in data], [[v for _, v in data]]
        self.h.hb_stats.text = "\n".join(lines) or ""

    # ------------------------------------------------------------------ tracking: money
    def cur(self):
        return self.store.data.get("currency", "INR")

    def mn_add(self):
        ids = self.h
        try:
            tracking.add_txn(self.db, ids.mn_kind.text, tracking.parse_amount(ids.mn_amt.text), ids.mn_cat.text, ids.mn_note.text)
            ids.mn_amt.text = ids.mn_note.text = ""
            self.say(ids.mn_msg, "Saved.")
            self.refresh_money()
        except ValueError as e:
            self.say(ids.mn_msg, str(e), False)

    def bg_set(self):
        try:
            tracking.set_budget(self.db, self.h.bg_cat.text or "General", tracking.parse_amount(self.h.bg_lim.text))
            self.h.bg_cat.text = self.h.bg_lim.text = ""
            self.refresh_money()
        except ValueError as e:
            self.h.mn_msg.text = str(e)

    def gl_add(self):
        try:
            tracking.add_goal(self.db, self.h.gl_name.text or "Goal", tracking.parse_amount(self.h.gl_target.text))
            self.h.gl_name.text = self.h.gl_target.text = ""
            self.refresh_money()
        except ValueError as e:
            self.h.mn_msg.text = str(e)

    def gl_contribute(self, gid, cents):
        tracking.contribute_goal(self.db, gid, cents)
        self.refresh_money()

    def mn_export(self):
        path = os.path.join(self.store.base, f"money-{time.strftime('%Y%m%d-%H%M%S')}.csv")
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(tracking.export_csv(self.db))
        self.db.audit("export_csv", path)
        self.h.mn_export.text = f"Saved to {path}"

    def refresh_money(self):
        if not self.ready:
            return
        ids, c, t = self.h, self.cur(), date.today()
        s = tracking.month_summary(self.db, t.year, t.month)
        ids.mn_summary.text = (f"{s['month']}\nIncome {tracking.fmt(s['income'], c)}\nExpenses {tracking.fmt(s['expense'], c)}\n"
                               f"Savings {tracking.fmt(s['saving'], c)}\nNet cash flow {tracking.fmt(s['net'], c)}")
        cf = tracking.cashflow_months(self.db, 6)
        ids.mn_chart.labels = [m for m, _, _ in cf]
        ids.mn_chart.series = [[(i - e) / 100 for _, i, e in cf]]
        ids.mn_chart.unit = c
        box = ids.bg_list
        box.clear_widgets()
        for b in tracking.budget_status(self.db, t.year, t.month):
            bar = Bar(value=b["pct"] / 100, size_hint=(None, None), size=(dp(70), dp(8)), pos_hint={"center_y": .5},
                      color=list(RED if b["pct"] > 100 else ACCENT))
            box.add_widget(self._row(f"{b['category']}: {tracking.fmt(b['spent'], c)} / {tracking.fmt(b['limit'], c)}  ({b['pct']:.0f}%)",
                                     [bar], 40, markup=False))
        box = ids.gl_list
        box.clear_widgets()
        for g in tracking.goals(self.db):
            bar = Bar(value=g["pct"] / 100, size_hint=(None, None), size=(dp(50), dp(8)), pos_hint={"center_y": .5})
            box.add_widget(self._row(f"{g['name']}: {tracking.fmt(g['saved_cents'], c)} / {tracking.fmt(g['target_cents'], c)}",
                                     [bar, self._chip("+500", lambda i=g["id"]: self.gl_contribute(i, 50000), 56)], 44, markup=False))
        rows = self.db.q("SELECT * FROM money ORDER BY id DESC LIMIT 6")
        ids.mn_recent.text = "\n".join(f"{r['ts'][5:16]}  {r['kind']:<8} {tracking.fmt(r['cents'], c):>16}  {r['category']}" for r in rows) or "No transactions yet."

    # ------------------------------------------------------------------ finance
    def watch_symbols(self):
        return [r["symbol"] for r in self.db.q("SELECT symbol FROM watchlist ORDER BY added_at")]

    def fw_add(self):
        sym = re.sub(r"[^A-Za-z0-9.\-^=]", "", self.h.fw_sym.text).upper()
        if not sym:
            return
        self.db.x("INSERT OR IGNORE INTO watchlist(symbol,added_at) VALUES(?,?)", (sym, time.strftime("%Y-%m-%d %H:%M:%S")))
        self.h.fw_sym.text = ""
        self.refresh_watch()

    def fw_remove(self, sym):
        self.db.x("DELETE FROM watchlist WHERE symbol=?", (sym,))
        self.refresh_watch()

    def fw_refresh(self):
        syms = self.watch_symbols()
        if not syms:
            self.h.fw_msg.text = "Add a symbol first."
            return
        self.h.fw_msg.text = "Fetching prices..."

        def job():
            msgs, alerts = [], []
            for s in syms:
                try:
                    q = finance.fetch_daily(s)
                    finance.save_quote(self.db, q)
                    for a in finance.check_alerts(self.db, s, q["series"][-1][1]):
                        alerts.append(f"{s} went {a['direction']} {a['price']}")
                except Exception as e:
                    msgs.append(f"{s}: {e}")

            def ui(dt):
                self.h.fw_msg.text = "  ".join(msgs) if msgs else "Updated " + time.strftime("%H:%M:%S")
                self.refresh_watch()
                for a in alerts:
                    try:
                        self.adapter.notify("Price alert", a)
                    except Exception:
                        android_api.speak(a)
                    self.popup("Price alert", a)
            Clock.schedule_once(ui)
        threading.Thread(target=job, daemon=True).start()

    def refresh_watch(self):
        if not self.ready:
            return
        box = self.h.fw_list
        box.clear_widgets()
        for s in self.watch_symbols():
            q = finance.load_quote(self.db, s)
            if q:
                px, prev = q["series"][-1][1], q["series"][-2][1] if len(q["series"]) > 1 else None
                chg = f"  ({(px / prev - 1) * 100:+.2f}%)" if prev else ""
                col = "#59C298" if prev and px >= prev else "#E6595F"
                text = (f"[b]{s}[/b]  {px:,.2f}[color={col}]{chg}[/color]\n[color=#858E89]{q['last_date']}  |  "
                        f"{short(q['source'], 14)}  |  {q['fetched_at'][5:16]}[/color]")
            else:
                text = f"[b]{s}[/b]\n[color=#858E89]price unavailable - tap Refresh[/color]"
            box.add_widget(self._row(text, [self._chip("Open", lambda x=s: self.select_symbol(x), 62),
                                            self._chip("X", lambda x=s: self.fw_remove(x), 44)], 60))
        if not box.children:
            box.add_widget(Factory.Muted(text="Your watchlist is empty."))
        self.al_refresh()

    def analysis(self, sym):
        q = finance.load_quote(self.db, sym)
        if not q:
            return None, "No data yet. Tap Refresh prices first."
        c = [p for _, p in q["series"]]
        s20, s50, rs = finance.sma(c, 20)[-1], finance.sma(c, 50)[-1], finance.rsi(c)[-1]
        vol, dd = finance.volatility(c[-252:]), finance.max_drawdown(c[-252:])
        yr = c[-252:]
        f = lambda v, fmt="{:,.2f}": fmt.format(v) if v is not None else "unavailable"
        text = (f"Last close {c[-1]:,.2f} on {q['last_date']}\n52-week range {min(yr):,.2f} - {max(yr):,.2f}\n"
                f"SMA20 {f(s20)}  |  SMA50 {f(s50)}  |  RSI14 {f(rs, '{:.1f}')}\n"
                f"Volatility (annualised) {f(vol * 100 if vol is not None else None, '{:.1f}%')}  |  Max drawdown {dd * 100:.1f}%\n"
                f"Source: {q['source']}  |  fetched {q['fetched_at']}")
        return q, text

    def select_symbol(self, sym):
        q, text = self.analysis(sym)
        ids = self.h
        ids.fw_sel.text = f"Analysis: {sym}"
        ids.fw_info.text = text
        if q:
            tail = q["series"][-120:]
            closes = [p for _, p in q["series"]]
            ids.fw_chart.labels = [d for d, _ in tail]
            ids.fw_chart.unit = ""
            ids.fw_chart.series = [[p for _, p in tail], finance.sma(closes, 20)[-120:]]
        self.h.bt_sym.text = self.h.pp_sym.text = self.h.al_sym.text = sym

    def al_add(self):
        try:
            self.db.x("INSERT INTO alerts(symbol,direction,price) VALUES(?,?,?)",
                      (self.h.al_sym.text.strip().upper(), self.h.al_dir.text, float(self.h.al_price.text)))
            self.h.al_price.text = ""
            self.al_refresh()
        except ValueError:
            self.h.fw_msg.text = "Enter a valid price."

    def al_refresh(self):
        box = self.h.al_list
        box.clear_widgets()
        for a in self.db.q("SELECT * FROM alerts WHERE active=1"):
            box.add_widget(self._row(f"{a['symbol']} {a['direction']} {a['price']}", [
                self._chip("X", lambda i=a["id"]: (self.db.x("DELETE FROM alerts WHERE id=?", (i,)), self.al_refresh()), 44)], 40, markup=False))

    def bt_run(self):
        ids = self.h
        try:
            if ids.bt_csv.text.strip():
                series, source = finance.parse_csv_prices(ids.bt_csv.text)
                label, fetched = "your CSV", "-"
            else:
                q = finance.load_quote(self.db, ids.bt_sym.text.strip())
                if not q:
                    raise ValueError("no stored prices for that symbol - fetch it in Watchlist first")
                series, source, label, fetched = q["series"], q["source"], q["symbol"], q["fetched_at"]
            r = finance.backtest_sma(
                [p for _, p in series], int(ids.bt_fast.text), int(ids.bt_slow.text), float(ids.bt_cash.text), float(ids.bt_fee.text))
        except Exception as e:
            ids.bt_result.text = f"Cannot run: {e}"
            return
        wr = f"{r['win_rate'] * 100:.0f}%" if r["win_rate"] is not None else "n/a"
        ids.bt_result.text = (f"{label}: SMA {ids.bt_fast.text}/{ids.bt_slow.text} on {len(series)} days\n"
                              f"Strategy {r['return'] * 100:+.1f}%  |  Buy and hold {r['buy_hold_return'] * 100:+.1f}%\n"
                              f"Max drawdown {r['max_drawdown'] * 100:.1f}%  |  Trades {r['trades']}  |  Win rate {wr}\n"
                              f"Source: {source}  |  fetched {fetched}")
        ids.bt_chart.labels, ids.bt_chart.unit = [], ""
        ids.bt_chart.colors = [ACCENT, (0.55, 0.6, 0.58, 1)]
        ids.bt_chart.series = [r["equity"], r["buy_hold"]]

    def refresh_paper(self):
        if not self.ready:
            return
        prices = {s: (finance.load_quote(self.db, s) or {"series": [(0, 0)]})["series"][-1][1] for s in finance.paper_positions(self.db)}
        prices = {k: v for k, v in prices.items() if v}
        pos = finance.paper_positions(self.db)
        lines = [f"Cash {finance.paper_cash(self.db):,.2f}   Equity {finance.paper_equity(self.db, prices):,.2f}"]
        lines += [f"{s}: {p['qty']:g} @ avg {p['cost'] / p['qty']:,.2f}" for s, p in pos.items()]
        self.h.pp_state.text = "\n".join(lines)
        rows = self.db.q("SELECT * FROM paper_trades ORDER BY id DESC LIMIT 8")
        self.h.pp_trades.text = "\n".join(f"{r['ts'][5:16]} {r['side']:<4} {r['qty']:g} {r['symbol']} @ {r['price']:,.2f}" for r in rows) or "No paper trades yet."

    def pp_order(self, side):
        ids = self.h
        try:
            sym = ids.pp_sym.text.strip().upper()
            q = finance.load_quote(self.db, sym)
            if not q:
                raise ValueError("no stored price - fetch it in Watchlist first")
            finance.paper_order(self.db, sym, side, float(ids.pp_qty.text), q["series"][-1][1],
                                f"close {q['last_date']}, fetched {q['fetched_at']}",
                                self.store.data["risk"]["max_position_pct"])
            self.say(ids.pp_msg, f"{side} filled at {q['series'][-1][1]:,.2f} (close of {q['last_date']}).")
        except ValueError as e:
            self.say(ids.pp_msg, str(e), False)
        self.refresh_paper()

    def pp_reset(self):
        finance.paper_reset(self.db)
        self.refresh_paper()

    # ------------------------------------------------------------------ voice + AI assistant
    def listen(self):
        if not android_api.ANDROID:
            return self.show_answer("Voice input works on your phone. Type a command below.")
        android_api.listen(lambda t: self.process(t) if t else self.show_answer("I didn't catch that."))

    def show_answer(self, text, speak=True, code=None):
        ids = self.h
        ids.ai_answer.text = text
        ids.ai_answer.opacity = 0
        Animation(opacity=1, d=0.4).start(ids.ai_answer)
        self._ai_code = code
        ids.ai_code_btn.opacity, ids.ai_code_btn.disabled = (1, False) if code else (0, True)
        ids.ai_code_btn.height = dp(48) if code else 0
        if speak and not code:
            android_api.speak(short(text, 300))

    def ai_key(self):
        return self.vault.get("ai_key", "") or self.store.data["ai"].get("key", "")

    def process(self, text):
        text = (text or "").strip()
        if not text:
            return
        self.h.ai_heard.text = f'You: "{text}"'
        self.h.ai_typed.text = ""
        m = re.match(r"(?:run|execute|start) (.+)", text.lower())
        if m and self.ready:
            for a in self.scripts.list():
                if a["enabled"] and m.group(1).strip() in a["title"].lower():
                    self.scripts.run_async(a["id"], None, lambda r, t=a["title"]: Clock.schedule_once(
                        lambda dt: self.show_answer(f"{t}: {r['status']}. {short(r['text'], 120)}")))
                    return self.show_answer(f"Running {a['title']}...", speak=False)
        out = voice.handle(text, self.store, self.fit)
        if out is not None:
            return self.show_answer(out)
        if not self.ai_key():
            return self.show_answer("I didn't understand that. Add an AI key in Settings (unlock with your PIN) and I can answer anything.")
        self.show_answer("Thinking...", speak=False)
        threading.Thread(target=lambda: self._ai_done(ai.ask(self.store, text, key=self.ai_key())), daemon=True).start()

    def _ai_done(self, ans, code=None):
        Clock.schedule_once(lambda dt: self.show_answer(ans, code=code))

    def current_source(self):
        return self.h.ed_code.text if self.cur_aid else self.h.sc_code.text

    def ai_action(self, mode):
        ids, req = self.h, self.h.ai_typed.text.strip()
        src = self.current_source().strip()
        if mode in ("explain", "bugs", "tests", "modify") and not src:
            return self.show_answer("Open a script in Automations first (or paste code in the import box).", speak=False)
        if mode in ("generate", "modify") and not req:
            return self.show_answer("Type what the script should do (or what to change), then tap again.", speak=False)
        if not self.ai_key():
            return self.show_answer("Add your AI key in Settings first (unlock with your PIN).", speak=False)
        if mode == "summary":
            prompt = json.dumps(self.tracking_context(), indent=1)
        elif mode == "finance":
            prompt = json.dumps(self.finance_context(), indent=1)
        elif mode == "generate":
            prompt = req
        elif mode == "modify":
            prompt = f"Request: {req}\n\nScript:\n{src}"
        else:
            prompt = src + (f"\n\nFocus: {req}" if req else "")
        ids.ai_heard.text = f"Tool: {mode}"
        self.show_answer("Working...", speak=False)

        def job():
            ans = ai.ask(self.store, prompt, key=self.ai_key(), mode=mode, remember=False)
            code = ai.extract_code(ans) if mode in ("generate", "modify", "tests") else None
            self._ai_done(ans, code)
        threading.Thread(target=job, daemon=True).start()

    def ai_send_code(self):
        code = self._ai_code or ""
        if self.cur_aid and "def test_" in code and "def main" not in code:
            self.h.ed_code.text = self.h.ed_code.text.rstrip() + "\n\n\n" + code
            self.sub("auto", "scripts")
            self.open_script(self.cur_aid)
            self.h.ed_code.text += "\n\n\n" + code
        else:
            self.h.sc_code.text = code
            self.cur_aid = None
            self.sub("auto", "scripts")
        self.h.sc_report.text = "AI code loaded. It is UNTESTED: import it to run the checks, then review and approve."

    def tracking_context(self):
        t = date.today()
        out = {"note": "values missing = unavailable", "date": t.isoformat(), "health_last_7_days": {}, "habits": [], "money_this_month": {}}
        for k in HEALTH_KINDS:
            s = tracking.health_summary(self.db, k, "Week")
            out["health_last_7_days"][k] = ({"unit": s["unit"], "average": round(s["average"], 1), "total": s["total"],
                                             "days_with_data": s["days_with_data"], "sources": s["sources"]} if s["available"] else "unavailable")
        for hb in self.db.q("SELECT id,name FROM habits WHERE archived=0"):
            cur, best = tracking.streaks(self.db, hb["id"])
            out["habits"].append({"name": hb["name"], "streak": cur, "best": best, "last_30_days_pct": round(tracking.completion(self.db, hb["id"], 30) * 100)})
        s = tracking.month_summary(self.db, t.year, t.month)
        out["money_this_month"] = {"currency": self.cur(), **{k: s[k] / 100 for k in ("income", "expense", "saving", "net")},
                                   "expense_by_category": {k: v / 100 for k, v in s["by_category"].items()}}
        return out

    def finance_context(self):
        out = {"watchlist": [], "paper_account": {"cash": finance.paper_cash(self.db), "positions": finance.paper_positions(self.db)}}
        for s in self.watch_symbols():
            q = finance.load_quote(self.db, s)
            if q:
                c = [p for _, p in q["series"]]
                out["watchlist"].append({"symbol": s, "last_close": c[-1], "date": q["last_date"], "source": q["source"],
                                         "fetched_at": q["fetched_at"], "rsi14": finance.rsi(c)[-1], "sma20": finance.sma(c, 20)[-1],
                                         "annual_volatility": finance.volatility(c[-252:])})
        return out

    # ------------------------------------------------------------------ settings, backup, logs
    def load_ui(self):
        ids, d = self.h, self.store.data
        ar, f, p = d["autoreply"], d["focus"], d["profile"]
        ids.ar_enabled.active, ids.ar_delay.text, ids.ar_msg.text = ar["enabled"], str(ar["delay_minutes"]), ar["message"]
        ids.ar_contacts.text, ids.ar_cool.text = ", ".join(ar["only_contacts"]), str(ar["cooldown_minutes"])
        ids.fo_enabled.active, ids.fo_strict.active = f["enabled"], f["strict"]
        ids.fo_start.text, ids.fo_end.text = f["schedules"][0]["start"], f["schedules"][0]["end"]
        ids.fo_apps.text = ", ".join(f["blocked"])
        ids.st_name.text, ids.st_model.text, ids.st_playlist.text = p.get("name", "SK"), d["ai"]["model"], d["playlist"]
        ids.st_lock.text = str(d["autolock_seconds"])
        ids.st_contacts.text = ", ".join(f"{k}={v}" for k, v in d["contacts"].items())
        ids.st_domains.text, ids.st_cur.text = ", ".join(d["domains"]), d.get("currency", "INR")
        ids.st_h.text, ids.st_w.text, ids.st_goal.text = str(p["height_cm"]), str(p["weight_kg"]), str(p["step_goal"])
        ids.st_logo.text = d.get("logo_path", "")

    def save_settings(self):
        ids, d = self.h, self.store.data
        d["ai"]["model"] = ids.st_model.text.strip() or "gpt-4o-mini"
        d["playlist"] = ids.st_playlist.text.strip()
        d["autolock_seconds"] = int(ids.st_lock.text or 60)
        d["profile"] = {"name": ids.st_name.text.strip() or "SK", "height_cm": int(ids.st_h.text or 170),
                        "weight_kg": int(ids.st_w.text or 65), "step_goal": int(ids.st_goal.text or 8000)}
        d["currency"] = (ids.st_cur.text.strip().upper() or "INR")[:5]
        d["domains"] = [x.strip().lower() for x in ids.st_domains.text.split(",") if x.strip()]
        d["contacts"] = {k.strip().lower(): v.strip() for k, v in (p.split("=", 1) for p in ids.st_contacts.text.split(",") if "=" in p)}
        self.store.save()
        msg = "Settings saved."
        if ids.st_key.text.strip():
            if self.vault.unlocked:
                self.vault.set("ai_key", ids.st_key.text.strip())
                ids.st_key.text = ""
                msg += " AI key stored encrypted."
            else:
                msg += " AI key NOT saved: unlock with your PIN (not fingerprint) first."
        if ids.st_pin.text and 4 <= len(ids.st_pin.text) <= 8:
            self.guard.set_pin(ids.st_pin.text)
            msg += " PIN changed - lock and unlock again to re-encrypt the vault with it."
        ids.st_pin.text = ""
        self.db.audit("settings_saved")
        ids.st_keynote.text = msg

    def apply_logo(self):
        p = self.h.st_logo.text.strip()
        try:
            if not os.path.isfile(p) or os.path.getsize(p) > 5_000_000 or not p.lower().endswith((".png", ".jpg", ".jpeg")):
                raise ValueError("choose an existing PNG/JPG under 5 MB")
            dest = os.path.join(self.store.base, "custom_logo" + os.path.splitext(p)[1].lower())
            shutil.copy(p, dest)
            self.store.data["logo_path"] = dest
            self.store.save()
            self.sm.get_screen("splash").logo_source = dest
            self.h.st_logo.text = dest
            self.db.audit("logo_changed")
        except Exception as e:
            self.h.st_logo.hint_text = f"Failed: {e}"

    def backup_now(self):
        try:
            blob = backup.make_backup(self.db, self.h.bk_pass.text)
            os.makedirs(os.path.join(self.store.base, "backups"), exist_ok=True)
            path = os.path.join(self.store.base, "backups", f"arise-{time.strftime('%Y%m%d-%H%M%S')}.ariseback")
            open(path, "wb").write(blob)
            self.db.audit("backup", path)
            self.say(self.h.bk_msg, f"Encrypted backup saved: {path}")
        except ValueError as e:
            self.say(self.h.bk_msg, str(e), False)

    def restore_backup(self):
        try:
            raw = backup.read_backup(open(self.h.bk_path.text.strip(), "rb").read(), self.h.bk_pass.text)
            open(os.path.join(self.store.base, "mylife.db.restore"), "wb").write(raw)
            self.db.audit("restore_scheduled", self.h.bk_path.text.strip())
            self.say(self.h.bk_msg, "Backup verified. Close and reopen Arise to finish restoring (your current data is kept as .before-restore).")
        except Exception as e:
            self.say(self.h.bk_msg, f"Cannot restore: {e}", False)

    def refresh_logs(self):
        if not self.ready:
            return
        rows = self.db.q("SELECT * FROM audit ORDER BY id DESC LIMIT 25")
        self.h.audit_label.text = "\n".join(f"{r['ts'][5:16]}  {r['event']}  {short(r['detail'], 40)}" for r in rows) or "Nothing yet."
        self.h.log_label.text = self.store.read_log(25)


if __name__ == "__main__":
    AriseApp().run()
