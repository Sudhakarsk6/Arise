"""Steps (Android step-counter sensor via Java StepTracker), distance, calories,
active minutes, 7-day history and GPS workouts."""
import math, time
from . import android_api as api


def metrics(steps, height_cm=170, weight_kg=65):
    stride_m = height_cm * 0.415 / 100          # common stride estimate
    km = steps * stride_m / 1000
    return {"steps": steps, "km": km, "kcal": km * weight_kg * 0.9, "minutes": steps / 100}


def _hav(a, b):
    R = 6371.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


class Fitness:
    def __init__(self, store):
        self.store, self.w = store, None

    # ---- steps
    def start_steps(self):
        if not api.ANDROID:
            return
        try:
            from jnius import autoclass
            autoclass("org.arise.service.StepTracker").start(api._act())
        except Exception as e:
            self.store.log(f"step tracker error: {e}")

    def steps_today(self):
        if not api.ANDROID:
            return 0
        try:
            from jnius import autoclass
            return int(autoclass("org.arise.service.StepTracker").todaySteps())
        except Exception:
            return 0

    def history(self, days=7):
        if not api.ANDROID:
            return []
        try:
            from jnius import autoclass
            raw = str(autoclass("org.arise.service.StepTracker").history(days))
            return [(d, int(v)) for d, v in (x.split(":") for x in raw.split(",") if x)]
        except Exception:
            return []

    def today_metrics(self):
        p = self.store.data["profile"]
        return metrics(self.steps_today(), p["height_cm"], p["weight_kg"])

    def summary(self):
        m = self.today_metrics()
        if not api.ANDROID:
            return "Step tracking works on your phone."
        return (f"You have walked {m['steps']} steps today, about {m['km']:.1f} kilometres, "
                f"burning around {int(m['kcal'])} calories.")

    # ---- GPS workout
    def workout_active(self):
        return self.w is not None

    def start_workout(self):
        if not api.ANDROID:
            return "GPS workouts work on your phone."
        try:
            from plyer import gps
            self.w = {"t0": time.time(), "km": 0.0, "last": None}
            gps.configure(on_location=self._loc)
            gps.start(minTime=1000, minDistance=3)
        except Exception as e:
            self.w = None
            return f"GPS unavailable: {e}"
        self.store.log("Workout started")
        return "Workout started."

    def _loc(self, **kw):                      # called from a plyer thread
        w = self.w
        if not w or kw.get("accuracy", 0) > 50:
            return
        pt = (kw["lat"], kw["lon"])
        if w["last"]:
            d = _hav(w["last"], pt)
            if d < 0.2:                        # ignore GPS jumps
                w["km"] += d
        w["last"] = pt

    def workout_stats(self):
        w = self.w
        if not w:
            return None
        secs = int(time.time() - w["t0"])
        pace = (secs / 60) / w["km"] if w["km"] > 0.01 else 0
        kcal = w["km"] * self.store.data["profile"]["weight_kg"]
        return {"secs": secs, "km": w["km"], "pace": pace, "kcal": kcal}

    def stop_workout(self):
        st = self.workout_stats()
        try:
            from plyer import gps
            gps.stop()
        except Exception:
            pass
        self.w = None
        if st:
            self.store.data["workouts"] = (self.store.data["workouts"] + [
                {"date": time.strftime("%Y-%m-%d %H:%M"), **st}])[-50:]
            self.store.save()
            self.store.log(f"Workout saved: {st['km']:.2f} km in {st['secs'] // 60} min")
            return f"Workout finished. {st['km']:.2f} kilometres in {st['secs'] // 60} minutes."
        return "No workout running."
