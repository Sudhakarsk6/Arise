"""Where am I? Android last-known location (needs the Location permission) with a manual fallback."""
import json
import os
from . import net


def android_location():
    if not os.environ.get("ANDROID_ARGUMENT"):
        return None
    try:
        from jnius import autoclass
        act = autoclass("org.kivy.android.PythonActivity").mActivity
        lm = act.getSystemService("location")
        best = None
        for provider in ("gps", "network", "passive"):
            loc = lm.getLastKnownLocation(provider)
            if loc is not None and (best is None or loc.getTime() > best.getTime()):
                best = loc
        return (best.getLatitude(), best.getLongitude()) if best else None
    except Exception:
        return None


def current(store):
    """-> (lat, lon, source) or None. Manual city from Settings is the fallback."""
    got = android_location()
    if got:
        return got[0], got[1], "device location"
    m = store.data.get("location", {})
    if m.get("lat") is not None and m.get("lon") is not None:
        return float(m["lat"]), float(m["lon"]), "saved location"
    return None


def place_name(lat, lon, getter=net.get_text):
    """City, state via OpenStreetMap Nominatim (reverse geocoding)."""
    d = json.loads(getter(f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&zoom=10&lat={lat:.4f}&lon={lon:.4f}"))
    a = d.get("address") or {}
    city = a.get("city") or a.get("town") or a.get("village") or a.get("suburb") or a.get("state_district") or a.get("county")
    parts = [p for p in (city, a.get("state")) if p]
    if not parts:
        raise ValueError("no place name")
    return ", ".join(parts)
