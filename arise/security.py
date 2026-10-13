import hashlib, hmac, secrets, time

ITER = 200_000


def _hash(pin, salt_hex):
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(salt_hex), ITER).hex()


class PinGuard:
    MAX_FAILS = 3
    LOCKOUT_S = 30

    def __init__(self, store):
        self.store = store
        self.fails = 0
        self.locked_until = 0.0

    def has_pin(self):
        return bool(self.store.data["pin_hash"])

    def set_pin(self, pin):
        salt = secrets.token_hex(16)
        self.store.data["pin_salt"] = salt
        self.store.data["pin_hash"] = _hash(pin, salt)
        self.store.save()
        self.store.log("PIN created/changed")

    def check(self, pin):
        now = time.time()
        if now < self.locked_until:
            return False, f"Too many attempts. Wait {int(self.locked_until - now)}s."
        d = self.store.data
        ok = hmac.compare_digest(_hash(pin, d["pin_salt"]), d["pin_hash"])
        if ok:
            self.fails = 0
            self.store.log("Unlocked with PIN")
            return True, ""
        self.fails += 1
        self.store.log(f"FAILED unlock attempt #{self.fails}")
        if self.fails >= self.MAX_FAILS:
            self.locked_until = now + self.LOCKOUT_S * self.fails
            return False, "Too many attempts. Locked temporarily."
        return False, f"Wrong PIN ({self.MAX_FAILS - self.fails} tries left)."
