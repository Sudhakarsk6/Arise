"""Ready-made scripts shipped inside the app (the files in the examples/ folder)."""
import glob, os
from . import sandbox

DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
NETWORK_HOSTS = ("open-meteo.com", "frankfurter.app", "coingecko.com", "wikipedia.org")


def load():
    out = []
    for path in sorted(glob.glob(os.path.join(DIR, "*.py"))):
        try:
            src = open(path, encoding="utf-8").read()
        except OSError:
            continue
        m = sandbox.parse_meta(src, os.path.basename(path)[:-3])
        hosts = sorted({w for line in src.splitlines() if line.startswith("# NOTE:") for w in line.replace(",", " ").split()
                        if "." in w and not w.endswith(".") and w.count(".") >= 1 and any(h in w for h in NETWORK_HOSTS)})
        out.append({"file": os.path.basename(path), "label": f"{m['category']}: {m['name']}", "name": m["name"],
                    "description": m["description"], "permissions": m["permissions"], "hosts": hosts, "source": src})
    out.sort(key=lambda e: e["label"])
    return out
