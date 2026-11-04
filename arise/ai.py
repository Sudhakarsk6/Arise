"""AI assistant (OpenAI-compatible chat API). The key comes from the encrypted vault, requests are
HTTPS-only and rate-limited, and obvious secrets are redacted before anything is sent."""
import json, re, ssl, urllib.error, urllib.request
from .net import RateLimiter
from . import sandbox

URL = "https://api.openai.com/v1/chat/completions"
SYSTEM = ("You are Arise, a friendly assistant inside a personal automation app. "
          "Answer in 1 to 3 short spoken-style sentences. No markdown, no lists.")

API_DOC = ("The script runs in a restricted sandbox. Rules: put header comments '# name:', '# description:', "
           "'# permissions:' (only from: " + ", ".join(sorted(sandbox.PERMISSIONS)) + "), '# category:'. "
           "Define main() that returns a short string. Allowed imports only: " + ", ".join(sorted(sandbox.ALLOWED_IMPORTS)) + ". "
           "Forbidden: open, eval, exec, getattr, type, underscore attributes, os, sys, subprocess, sockets. "
           "Available API object `arise`: log(msg), progress(pct,msg), now(), notify(title,msg), speak(text), "
           "open_app(name), open_url(url), http_get(url) (allowed domains only), storage_get(key,default), "
           "storage_set(key,value). Add small test_* functions that use assert.")
MODES = {
    "explain": "Explain this Arise Python automation in plain language: what it does, which permissions it needs, and any risks. Do not claim it works unless told it passed tests.",
    "generate": "Write ONE new Arise automation script. " + API_DOC + " Reply with a single ```python code block, then at most two sentences. State that the script is UNTESTED until the app's checks pass.",
    "modify": "Modify the given Arise script as requested. " + API_DOC + " Reply with the full updated script in one ```python block, then two sentences summarising the change. It is UNTESTED until the app's checks pass.",
    "bugs": "Review this Arise script for bugs and security problems. List concrete issues with line references. Do not claim anything works unless told it was tested.",
    "tests": "Write test_* functions (plain asserts) for this Arise script. Reply with only the test functions in one ```python block.",
    "summary": "Summarise the user's personal tracking data (JSON). Use ONLY the numbers given, say 'unavailable' for missing values, and make 3 short practical suggestions. This is not medical or financial advice.",
    "finance": "Give educational analysis of the market/portfolio data (JSON) provided. Use only the numbers given and mention their source and timestamp. Never promise profits; always note the risks.",
}
_limiter = RateLimiter(20, 60)
_history = []
SECRET = re.compile(r"(sk-[A-Za-z0-9_\-]{12,}|github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})")


def redact(text):
    return SECRET.sub("[REDACTED]", text)


def extract_code(text):
    m = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.S)
    return m.group(1).strip("\n") + "\n" if m else None


def _ctx():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def ask(store, text, key=None, mode=None, remember=True):
    cfg = store.data["ai"]
    key = (key if key is not None else cfg.get("key", "")).strip()
    if not key:
        return "Add your API key in Settings (unlock with your PIN first) to chat with me."
    if not _limiter.allow("ai"):
        return "Slow down a little: too many AI requests this minute."
    system = MODES[mode] if mode else SYSTEM
    msgs = [{"role": "system", "content": system}]
    if remember and not mode:
        _history.append({"role": "user", "content": redact(text)})
        del _history[:-8]
        msgs += _history
    else:
        msgs.append({"role": "user", "content": redact(text)})
    body = {"model": cfg.get("model") or "gpt-4o-mini", "messages": msgs,
            "max_tokens": 1100 if mode in ("generate", "modify", "tests", "bugs") else 300, "temperature": 0.4 if mode else 0.6}
    req = urllib.request.Request(URL, json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(req, timeout=45, context=_ctx()) as r:
            ans = json.load(r)["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        if remember and not mode:
            _history.pop()
        return {401: "Your API key was rejected. Check it in Settings.",
                429: "The AI quota or rate limit was reached."}.get(e.code, f"AI error {e.code}.")
    except Exception as e:
        if remember and not mode:
            _history.pop()
        return f"I couldn't reach the AI service ({type(e).__name__})."
    if remember and not mode:
        _history.append({"role": "assistant", "content": ans})
    return ans
