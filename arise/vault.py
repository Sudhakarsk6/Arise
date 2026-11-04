"""Encrypted secret storage (API keys) + encrypted backups.
AES-256-CTR (pure-python `pyaes`) with an HMAC-SHA256 tag (encrypt-then-MAC).
The key is derived from your PIN with PBKDF2 and only exists in memory while unlocked."""
import base64, hashlib, hmac, json, os, secrets
import pyaes

ITER = 200_000


def derive(pin, salt):
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, ITER, dklen=64)


def encrypt_bytes(key, data):
    nonce = secrets.token_bytes(16)
    ctr = pyaes.Counter(initial_value=int.from_bytes(nonce, "big"))
    ct = pyaes.AESModeOfOperationCTR(key[:32], counter=ctr).encrypt(data)
    mac = hmac.new(key[32:], nonce + ct, hashlib.sha256).digest()
    return nonce + ct + mac


def decrypt_bytes(key, blob):
    if len(blob) < 48:
        raise ValueError("data too short")
    nonce, ct, mac = blob[:16], blob[16:-32], blob[-32:]
    if not hmac.compare_digest(mac, hmac.new(key[32:], nonce + ct, hashlib.sha256).digest()):
        raise ValueError("wrong PIN or corrupted data")
    ctr = pyaes.Counter(initial_value=int.from_bytes(nonce, "big"))
    return pyaes.AESModeOfOperationCTR(key[:32], counter=ctr).decrypt(ct)


class Vault:
    def __init__(self, path):
        self.path = path
        self.key = None

    def _read(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"salt": secrets.token_hex(16), "items": {}}

    def _write(self, data):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, self.path)

    @property
    def unlocked(self):
        return self.key is not None

    def unlock(self, pin):
        data = self._read()
        if not os.path.exists(self.path):
            self._write(data)
        self.key = derive(pin, bytes.fromhex(data["salt"]) + b"vault")
        return True

    def lock(self):
        self.key = None

    def set(self, name, value):
        if not self.unlocked:
            raise PermissionError("vault is locked")
        data = self._read()
        data["items"][name] = base64.b64encode(encrypt_bytes(self.key, value.encode())).decode()
        self._write(data)

    def get(self, name, default=""):
        if not self.unlocked:
            return default
        blob = self._read()["items"].get(name)
        if not blob:
            return default
        try:
            return decrypt_bytes(self.key, base64.b64decode(blob)).decode()
        except ValueError:
            return default

    def delete(self, name):
        data = self._read()
        data["items"].pop(name, None)
        self._write(data)
