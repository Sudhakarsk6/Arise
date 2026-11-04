"""Encrypted, portable backups of the database (passphrase based, AES-256 + HMAC)."""
import os, secrets, sqlite3, tempfile
from .vault import decrypt_bytes, derive, encrypt_bytes

MAGIC = b"ARBK1"


def make_backup(db, passphrase):
    if len(passphrase) < 6:
        raise ValueError("use a passphrase of at least 6 characters")
    fd, tmp = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        dst = sqlite3.connect(tmp)
        with db.lock:
            db.conn.backup(dst)
        dst.close()
        raw = open(tmp, "rb").read()
    finally:
        os.remove(tmp)
    salt = secrets.token_bytes(16)
    return MAGIC + salt + encrypt_bytes(derive(passphrase, salt), raw)


def read_backup(data, passphrase):
    if not data.startswith(MAGIC):
        raise ValueError("not an Arise backup file")
    raw = decrypt_bytes(derive(passphrase, data[5:21]), data[21:])
    if not raw.startswith(b"SQLite format 3"):
        raise ValueError("backup content is not a database")
    return raw
