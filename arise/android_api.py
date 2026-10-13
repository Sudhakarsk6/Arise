"""Platform layer. On Android it uses pyjnius; on Windows/desktop it falls back to
the browser / PowerShell speech so the same app also works as an .exe."""
import os, re, subprocess, sys, webbrowser

ANDROID = bool(os.environ.get("ANDROID_ARGUMENT"))
WINDOWS = sys.platform == "win32"
KNOWN_APPS = {
    "youtube": "com.google.android.youtube", "whatsapp": "com.whatsapp",
    "chrome": "com.android.chrome", "maps": "com.google.android.apps.maps",
    "gmail": "com.google.android.gm", "telegram": "org.telegram.messenger",
    "instagram": "com.instagram.android", "spotify": "com.spotify.music",
    "settings": "com.android.settings", "camera": "com.android.camera",
    "photos": "com.google.android.apps.photos", "play store": "com.android.vending",
    "facebook": "com.facebook.katana", "snapchat": "com.snapchat.android",
    "tiktok": "com.zhiliaoapp.musically", "x": "com.twitter.android",
    "twitter": "com.twitter.android", "netflix": "com.netflix.mediaclient",
    "reddit": "com.reddit.frontpage",
}
REQ_SPEECH, REQ_UNLOCK = 4243, 4242
_callbacks, _bound = {}, False


def _act():
    from jnius import autoclass
    return autoclass("org.kivy.android.PythonActivity").mActivity


def _view(url, package=None):
    from jnius import autoclass
    Intent, Uri = autoclass("android.content.Intent"), autoclass("android.net.Uri")
    i = Intent(Intent.ACTION_VIEW, Uri.parse(url))
    if package:
        i.setPackage(package)
    _act().startActivity(i)


def _for_result(intent, req, cb):
    """Start an activity and call cb(result_ok, intent) on the Kivy thread."""
    global _bound
    from android import activity
    from kivy.clock import Clock

    def on_result(request, result, data):
        fn = _callbacks.pop(request, None)
        if fn:
            Clock.schedule_once(lambda dt: fn(result == -1, data))

    if not _bound:
        activity.bind(on_activity_result=on_result)
        _bound = True
    _callbacks[req] = cb
    _act().startActivityForResult(intent, req)


# ---------------------------------------------------------------- actions
def open_url(url):
    if ANDROID:
        _view(url)
    else:
        webbrowser.open(url)
    return "Opening link"


def youtube_playlist(playlist):
    if not playlist:
        return "No playlist set. Add one in Settings."
    m = re.search(r"list=([\w-]+)", playlist)
    pid = m.group(1) if m else playlist.strip()
    url = f"https://www.youtube.com/playlist?list={pid}"
    if ANDROID:
        try:
            _view(url, "com.google.android.youtube")
        except Exception:
            _view(url)
    else:
        webbrowser.open(url)
    return "Opening your playlist on YouTube"


def youtube_search(query):
    from urllib.parse import quote
    url = "https://www.youtube.com/results?search_query=" + quote(query)
    if ANDROID:
        try:
            _view(url, "com.google.android.youtube")
        except Exception:
            _view(url)
    else:
        webbrowser.open(url)
    return f"Searching YouTube for {query}"


def open_app(name):
    name = name.strip().lower()
    if not ANDROID:
        try:
            if WINDOWS:
                os.startfile(name)
                return f"Opening {name}"
        except Exception:
            pass
        return f"I can't open {name} on this device"
    pm = _act().getPackageManager()
    pkg = KNOWN_APPS.get(name)
    if not pkg:
        for ai in pm.getInstalledApplications(0).toArray():
            if name in str(pm.getApplicationLabel(ai)).lower():
                pkg = ai.packageName
                break
    intent = pm.getLaunchIntentForPackage(pkg) if pkg else None
    if intent is None:
        return f"I couldn't find an app called {name}"
    _act().startActivity(intent)
    return f"Opening {name}"


def send_sms(number, text):
    if not ANDROID:
        return "Sending SMS works on your phone"
    from jnius import autoclass
    SmsManager = autoclass("android.telephony.SmsManager")
    sm = SmsManager.getDefault()
    sm.sendMultipartTextMessage(number, None, sm.divideMessage(text), None, None)
    return "Message sent"


def call(number):
    if not ANDROID:
        return "Calling works on your phone"
    from jnius import autoclass
    Intent, Uri = autoclass("android.content.Intent"), autoclass("android.net.Uri")
    uri = Uri.parse("tel:" + number)
    try:
        _act().startActivity(Intent(Intent.ACTION_CALL, uri))
    except Exception:                      # no CALL_PHONE permission -> open the dialer instead
        _act().startActivity(Intent(Intent.ACTION_DIAL, uri))
    return "Calling now"


# ---------------------------------------------------------------- speech out
_tts, _tts_ready, _tts_queue, _tts_init = None, False, [], None


def _speak_android(text):
    global _tts, _tts_ready, _tts_init
    from jnius import autoclass, PythonJavaClass, java_method
    TTS = autoclass("android.speech.tts.TextToSpeech")

    def say(t):
        try:
            _tts.speak(t, TTS.QUEUE_FLUSH, None, "arise")
        except Exception:
            _tts.speak(t, TTS.QUEUE_FLUSH, None)

    if _tts_ready:
        return say(text)
    _tts_queue.append(text)
    if _tts is None:
        class OnInit(PythonJavaClass):
            __javainterfaces__ = ["android/speech/tts/TextToSpeech$OnInitListener"]
            __javacontext__ = "app"

            @java_method("(I)V")
            def onInit(self, status):
                global _tts_ready
                if status == 0:
                    _tts_ready = True
                    while _tts_queue:
                        say(_tts_queue.pop(0))
        _tts_init = OnInit()               # keep a reference so it isn't garbage collected
        _tts = TTS(_act(), _tts_init)


def speak(text):
    try:
        if ANDROID:
            _speak_android(text)
        elif WINDOWS:
            safe = text.replace("'", " ").replace('"', " ")
            subprocess.Popen(
                ["powershell", "-NoProfile", "-Command",
                 "Add-Type -AssemblyName System.Speech; "
                 f"(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{safe}')"],
                creationflags=0x08000000)
        else:
            print("[speak]", text)
    except Exception as e:
        print("speak failed:", e)


def set_media_volume(fraction):
    if not ANDROID:
        return
    from jnius import autoclass
    Context, AM = autoclass("android.content.Context"), autoclass("android.media.AudioManager")
    am = _act().getSystemService(Context.AUDIO_SERVICE)
    mx = am.getStreamMaxVolume(AM.STREAM_MUSIC)
    am.setStreamVolume(AM.STREAM_MUSIC, int(mx * fraction), 0)


# ---------------------------------------------------------------- voice in + auth
def listen(cb):
    """Show Google's speech dialog; cb(text or None)."""
    if not ANDROID:
        return cb(None)
    from jnius import autoclass
    Intent, RI = autoclass("android.content.Intent"), autoclass("android.speech.RecognizerIntent")
    i = Intent(RI.ACTION_RECOGNIZE_SPEECH)
    i.putExtra(RI.EXTRA_LANGUAGE_MODEL, RI.LANGUAGE_MODEL_FREE_FORM)
    i.putExtra(RI.EXTRA_PROMPT, "Say a command for Arise")

    def done(ok, data):
        text = None
        if ok and data is not None:
            res = data.getStringArrayListExtra(RI.EXTRA_RESULTS)
            if res and res.size() > 0:
                text = str(res.get(0))
        cb(text)
    try:
        _for_result(i, REQ_SPEECH, done)
    except Exception as e:
        print("speech error", e)
        cb(None)


def device_unlock(cb):
    """Fingerprint / face / device PIN via the system. cb(bool)."""
    if not ANDROID:
        return cb(False)
    from jnius import autoclass
    Context = autoclass("android.content.Context")
    km = _act().getSystemService(Context.KEYGUARD_SERVICE)
    if not km.isDeviceSecure():
        return cb(False)
    intent = km.createConfirmDeviceCredentialIntent("Arise", "Unlock Arise")
    if intent is None:
        return cb(False)
    _for_result(intent, REQ_UNLOCK, lambda ok, d: cb(ok))


# ---------------------------------------------------------------- permissions / settings
def request_permissions():
    if not ANDROID:
        return
    from android.permissions import request_permissions as rp
    rp(["android.permission.SEND_SMS", "android.permission.CALL_PHONE",
        "android.permission.ACTIVITY_RECOGNITION",
        "android.permission.ACCESS_FINE_LOCATION", "android.permission.ACCESS_COARSE_LOCATION"])


def _secure(name):
    from jnius import autoclass
    Secure = autoclass("android.provider.Settings$Secure")
    return str(Secure.getString(_act().getContentResolver(), name) or "")


def notification_access_enabled():
    return ANDROID and str(_act().getPackageName()) in _secure("enabled_notification_listeners")


def accessibility_enabled():
    return ANDROID and "FocusService" in _secure("enabled_accessibility_services")


def _open_settings(action):
    if not ANDROID:
        return
    from jnius import autoclass
    _act().startActivity(autoclass("android.content.Intent")(action))


def open_notification_access_settings():
    _open_settings("android.settings.ACTION_NOTIFICATION_LISTENER_SETTINGS")


def open_accessibility_settings():
    _open_settings("android.settings.ACCESSIBILITY_SETTINGS")
