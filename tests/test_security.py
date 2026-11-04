import pytest
from arise import vault
from arise.net import RateLimiter, get_text
from arise.security import PinGuard
from arise.storage import Store


def test_encrypt_roundtrip_and_tamper():
    k = vault.derive("1234", b"salt" * 4)
    blob = vault.encrypt_bytes(k, b"secret key")
    assert b"secret" not in blob
    assert vault.decrypt_bytes(k, blob) == b"secret key"
    bad = bytearray(blob); bad[20] ^= 1
    with pytest.raises(ValueError):
        vault.decrypt_bytes(k, bytes(bad))
    with pytest.raises(ValueError):
        vault.decrypt_bytes(vault.derive("9999", b"salt" * 4), blob)


def test_vault_lock_unlock(tmp_path):
    v = vault.Vault(str(tmp_path / "v.json"))
    v.unlock("1234")
    v.set("ai_key", "sk-test-123")
    assert "sk-test" not in open(tmp_path / "v.json").read()
    assert v.get("ai_key") == "sk-test-123"
    v.lock()
    assert v.get("ai_key") == ""
    v2 = vault.Vault(str(tmp_path / "v.json")); v2.unlock("0000")
    assert v2.get("ai_key") == ""          # wrong PIN cannot read
    v3 = vault.Vault(str(tmp_path / "v.json")); v3.unlock("1234")
    assert v3.get("ai_key") == "sk-test-123"


def test_pin_lockout(tmp_path):
    s = Store(str(tmp_path)); g = PinGuard(s); g.set_pin("4321")
    assert g.check("4321")[0]
    for _ in range(3):
        g.check("0000")
    assert "Too many" in g.check("4321")[1]


def test_rate_limiter():
    r = RateLimiter(2, 10)
    assert r.allow("a", now=0) and r.allow("a", now=1) and not r.allow("a", now=2)
    assert r.allow("a", now=11.5)


def test_http_requires_https():
    with pytest.raises(ValueError):
        get_text("http://example.com")


def test_ai_redacts_secrets_and_extracts_code():
    from arise import ai
    assert "sk-abcdefghijklmnop12" not in ai.redact("my key sk-abcdefghijklmnop12 here")
    assert "github_pat_" not in ai.redact("github_pat_11A2KUJLA0FMlyKEpBDR31_ZFs5u8PLMF0")
    assert ai.extract_code("hi\n```python\nx = 1\n```\nbye") == "x = 1\n"
    assert ai.extract_code("no code") is None


def test_ai_without_key_does_not_call_network(tmp_path):
    from arise import ai
    s = Store(str(tmp_path))
    assert "API key" in ai.ask(s, "hello", key="")


def test_backup_roundtrip_and_wrong_passphrase(tmp_path):
    from arise import backup, tracking
    from arise.db import DB
    db = DB(str(tmp_path / "a.db"))
    tracking.add_txn(db, "income", 12345, "Salary")
    blob = backup.make_backup(db, "correct horse")
    assert b"SQLite" not in blob and b"Salary" not in blob
    raw = backup.read_backup(blob, "correct horse")
    (tmp_path / "b.db").write_bytes(raw)
    assert DB(str(tmp_path / "b.db")).q("SELECT cents FROM money")[0]["cents"] == 12345
    with pytest.raises(ValueError):
        backup.read_backup(blob, "wrong passphrase")
    with pytest.raises(ValueError):
        backup.make_backup(db, "short")
