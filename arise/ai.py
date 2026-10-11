"""Chat/voice answers via the OpenAI-compatible chat API (stdlib only).
The key comes from Settings (store.data['ai']['key'])."""
import json, ssl, urllib.error, urllib.request

URL = "https://api.openai.com/v1/chat/completions"
SYSTEM = ("You are Arise, a friendly voice assistant inside a phone app. "
          "Answer in 1 to 3 short spoken-style sentences. No markdown, no lists.")
_history = []


def _ctx():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def ask(store, text):
    cfg = store.data["ai"]
    key = cfg["key"].strip()
    if not key:
        return "Add your API key in Settings to chat with me."
    _history.append({"role": "user", "content": text})
    del _history[:-8]
    body = {"model": cfg["model"] or "gpt-4o-mini", "max_tokens": 220, "temperature": 0.6,
            "messages": [{"role": "system", "content": SYSTEM}] + _history}
    req = urllib.request.Request(URL, json.dumps(body).encode(),
                                 {"Content-Type": "application/json", "Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(req, timeout=25, context=_ctx()) as r:
            ans = json.load(r)["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        _history.pop()
        return {401: "Your API key was rejected. Check it in Settings.",
                429: "The AI quota or rate limit was reached."}.get(e.code, f"AI error {e.code}.")
    except Exception as e:
        _history.pop()
        return f"I couldn't reach the AI service ({type(e).__name__})."
    _history.append({"role": "assistant", "content": ans})
    store.log("AI answered a question")
    return ans
