# Custom PyInstaller hook: the stock Kivy hook crashes on the 'kivy.garden' namespace package.
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hiddenimports = collect_submodules(
    "kivy", filter=lambda n: not n.startswith("kivy.garden") and ".tests" not in n and not n.startswith("kivy.tools"))
datas = collect_data_files("kivy")
binaries = []
for modname in ("kivy_deps.sdl2", "kivy_deps.glew", "kivy_deps.angle"):
    try:
        mod = __import__(modname, fromlist=["dep_bins"])
        for d in mod.dep_bins:
            for f in os.listdir(d):
                binaries.append((os.path.join(d, f), "."))
    except Exception:
        pass
