import os, sys
from .base import Adapter, RecorderAdapter, Unsupported


def get_adapter():
    if os.environ.get("ANDROID_ARGUMENT"):
        from .android import AndroidAdapter
        return AndroidAdapter()
    if sys.platform == "win32":
        from .desktop import WindowsAdapter
        return WindowsAdapter()
    if sys.platform == "darwin":
        from .desktop import MacAdapter
        return MacAdapter()
    if sys.platform.startswith("linux"):
        from .desktop import LinuxAdapter
        return LinuxAdapter()
    from .ios import IOSAdapter
    return IOSAdapter()
