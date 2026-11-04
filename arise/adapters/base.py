class Unsupported(Exception):
    pass


class Adapter:
    """Platform adapter used by automations. Every method returns a short human-readable result."""
    name = "base"

    def notify(self, title, message):
        raise Unsupported(f"notifications are not supported on {self.name}")

    def speak(self, text):
        raise Unsupported(f"speech is not supported on {self.name}")

    def open_url(self, url):
        raise Unsupported(f"opening links is not supported on {self.name}")

    def open_app(self, name):
        raise Unsupported(f"opening apps is not supported on {self.name}")


class RecorderAdapter(Adapter):
    """Used for tests / dry runs: records calls, performs no side effects."""
    name = "dry-run"

    def __init__(self):
        self.calls = []

    def _rec(self, what, *args):
        self.calls.append((what,) + args)
        return f"[dry-run] {what}"

    def notify(self, title, message):
        return self._rec("notify", title, message)

    def speak(self, text):
        return self._rec("speak", text)

    def open_url(self, url):
        return self._rec("open_url", url)

    def open_app(self, name):
        return self._rec("open_app", name)
