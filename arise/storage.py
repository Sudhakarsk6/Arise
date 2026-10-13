"""JSON settings + activity log. The same files are read by the native
notification listener (Java), so keep the file names in sync."""
import json, os, time

DEFAULTS = {
    "pin_hash": "", "pin_salt": "",
    "playlist": "",
    "autolock_seconds": 60,
    "contacts": {},          # name -> phone number (for "send message to mom ...")
    "ai": {"key": "", "model": "gpt-4o-mini"},   # key is typed by you in Settings, never shipped
    "profile": {"name": "SK", "height_cm": 170, "weight_kg": 65, "step_goal": 8000},
    "focus": {"enabled": False, "strict": False,
              "schedules": [{"start": "09:00", "end": "17:00"}],
              "blocked": ["instagram", "youtube", "facebook", "snapchat", "tiktok", "x", "netflix", "reddit"],
              "blocked_packages": [], "until_ms": 0},
    "workouts": [],
    "automations": [],       # {"trigger": "voice|time", "value": str, "action": str, "param": str}
    "autoreply": {
        "enabled": False,
        "delay_minutes": 10,
        "message": "I'm busy right now and will reply soon. (Auto-reply from Arise)",
        "only_contacts": [],  # empty = everyone
        "cooldown_minutes": 60,
        "packages": ["com.whatsapp", "org.telegram.messenger",
                     "com.google.android.apps.messaging"],
    },
}


def data_dir():
    if os.environ.get("ANDROID_ARGUMENT"):
        from jnius import autoclass
        act = autoclass("org.kivy.android.PythonActivity").mActivity
        return act.getFilesDir().getAbsolutePath()   # same dir the Java service uses
    d = os.path.join(os.path.expanduser("~"), ".arise")
    os.makedirs(d, exist_ok=True)
    return d


class Store:
    def __init__(self, base=None):
        self.base = base or data_dir()
        self.cfg_path = os.path.join(self.base, "arise_config.json")
        self.log_path = os.path.join(self.base, "arise_log.txt")
        self.data = json.loads(json.dumps(DEFAULTS))
        try:
            with open(self.cfg_path, encoding="utf-8") as f:
                self._merge(self.data, json.load(f))
        except Exception:
            pass

    @staticmethod
    def _merge(dst, src):
        for k, v in src.items():
            if isinstance(v, dict) and isinstance(dst.get(k), dict) and k != "contacts":
                Store._merge(dst[k], v)
            else:
                dst[k] = v

    def save(self):
        tmp = self.cfg_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)
        os.replace(tmp, self.cfg_path)

    def log(self, msg):
        line = time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n"
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line)

    def read_log(self, n=60):
        try:
            with open(self.log_path, encoding="utf-8") as f:
                lines = f.readlines()[-n:]
            return "".join(reversed(lines)) or "No activity yet."
        except FileNotFoundError:
            return "No activity yet."
