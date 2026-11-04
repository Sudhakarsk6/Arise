import pytest
from arise import sandbox
from arise.adapters import RecorderAdapter
from arise.scripts import ScriptAPI


def api(perms=(), domains=()):
    return ScriptAPI(RecorderAdapter(), perms, lambda m: None, kv=lambda *a: a[-1], domains=domains, http=lambda u: "hi")


def test_runs_simple_script():
    r = sandbox.execute("def main():\n    return sum(range(5))", api())
    assert r["ok"] and r["result"] == "10"


@pytest.mark.parametrize("src", [
    "import os\n", "import subprocess\n", "from socket import socket\n", "import sys\n",
    "open('/etc/passwd')\n", "eval('1+1')\n", "exec('x=1')\n", "__import__('os')\n",
    "getattr(1, 'real')\n", "x = ().__class__.__bases__\n", "x = 'a'.__class__\n",
    "s = '{0.__class__}'.format(1)\n", "import json\njson._default_encoder\n",
    "def f():\n    return type(1)\n", "x = globals()\n",
])
def test_blocked_code(src):
    issues, _, _ = sandbox.check_policy(src)
    assert issues, f"should be blocked: {src!r}"


def test_module_escape_hatches_removed():
    r = sandbox.execute("import json\ndef main():\n    return json.codecs.open('x')", api())
    assert not r["ok"]
    r = sandbox.execute("import random\ndef main():\n    return random.os.getcwd()", api())
    assert not r["ok"]


def test_infinite_loop_is_stopped():
    r = sandbox.execute("def main():\n    while True:\n        pass", api(), timeout=1)
    assert not r["ok"] and ("time limit" in r["error"] or "too many steps" in r["error"])


def test_sleep_respects_limit():
    r = sandbox.execute("import time\ndef main():\n    time.sleep(100)", api(), timeout=1)
    assert not r["ok"]


def test_permissions_enforced_at_runtime():
    r = sandbox.execute("def main():\n    arise.open_url('https://x.org')", api())
    assert not r["ok"] and "not approved" in r["error"]
    r = sandbox.execute("def main():\n    return arise.open_url('https://x.org')", api({"open_url"}))
    assert r["ok"]
    r = sandbox.execute("def main():\n    arise.open_url('file:///etc/passwd')", api({"open_url"}))
    assert not r["ok"]


def test_network_allowlist():
    src = "def main():\n    return arise.http_get('https://good.com/x')"
    assert not sandbox.execute(src, api({"network"}))["ok"]
    assert sandbox.execute(src, api({"network"}, {"good.com"}))["result"] == "hi"


def test_errors_do_not_crash_and_report_line():
    r = sandbox.execute("def main():\n    x = 1\n    return 1/0", api())
    assert not r["ok"] and "line 3" in r["error"] and "ZeroDivisionError" in r["error"]


def test_print_captured_and_classes_work():
    r = sandbox.execute("class A:\n    def v(self):\n        return 3\ndef main():\n    print('hello')\n    return A().v()", api())
    assert r["ok"] and r["result"] == "3" and "hello" in r["log"]


def test_meta_parsing():
    m = sandbox.parse_meta("# name: X\n# description: D\n# permissions: notify, speak\n# category: Health\n")
    assert m["name"] == "X" and m["permissions"] == ["notify", "speak"] and m["category"] == "Health"
    assert sandbox.parse_meta('"""Doc title\nmore"""\n')["name"] == "Doc title"


def test_size_limit():
    assert sandbox.check_policy("x=1\n" * 40000)[0]
