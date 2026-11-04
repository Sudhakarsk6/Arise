from .base import Adapter
from .. import android_api as api


class AndroidAdapter(Adapter):
    name = "android"

    def notify(self, title, message):
        try:
            from plyer import notification
            notification.notify(title=title, message=message, app_name="Arise", timeout=8)
            return "notification sent"
        except Exception:
            api.speak(f"{title}. {message}")
            return "spoken (notification unavailable)"

    def speak(self, text):
        api.speak(text)
        return "spoken"

    def open_url(self, url):
        return api.open_url(url)

    def open_app(self, name):
        return api.open_app(name)
