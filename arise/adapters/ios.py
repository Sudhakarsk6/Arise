from .base import Adapter


class IOSAdapter(Adapter):
    """iOS does not allow apps to control other apps or run arbitrary automations in the background.
    Everything raises Unsupported (with an explanation) until Shortcuts integration is added."""
    name = "ios"
