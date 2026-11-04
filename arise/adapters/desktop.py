import os, shutil, subprocess, sys, webbrowser
from .base import Adapter, Unsupported


class _Desktop(Adapter):
    def open_url(self, url):
        webbrowser.open(url)
        return "opened in browser"

    def notify(self, title, message):
        try:
            from plyer import notification
            notification.notify(title=title, message=message, app_name="Arise", timeout=8)
            return "notification sent"
        except Exception as e:
            raise Unsupported(f"notifications unavailable: {e}")


class WindowsAdapter(_Desktop):
    name = "windows"

    def speak(self, text):
        safe = "".join(c for c in text if c.isalnum() or c in " .,!?-")
        subprocess.Popen(["powershell", "-NoProfile", "-Command",
                          "Add-Type -AssemblyName System.Speech; "
                          f"(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{safe}')"],
                         creationflags=0x08000000)
        return "spoken"

    def open_app(self, name):
        os.startfile(name)
        return f"opened {name}"


class MacAdapter(_Desktop):
    name = "macos"

    def speak(self, text):
        subprocess.Popen(["say", text])
        return "spoken"

    def open_app(self, name):
        subprocess.Popen(["open", "-a", name])
        return f"opened {name}"


class LinuxAdapter(_Desktop):
    name = "linux"

    def speak(self, text):
        exe = shutil.which("spd-say") or shutil.which("espeak")
        if not exe:
            raise Unsupported("install speech-dispatcher or espeak for speech")
        subprocess.Popen([exe, text])
        return "spoken"

    def open_app(self, name):
        exe = shutil.which(name)
        if not exe:
            raise Unsupported(f"program '{name}' not found")
        subprocess.Popen([exe])
        return f"opened {name}"
