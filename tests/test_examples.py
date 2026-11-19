import glob, os
from arise.adapters import RecorderAdapter
from arise.db import DB
from arise.scripts import Scripts

EXAMPLES = sorted(glob.glob(os.path.join(os.path.dirname(os.path.dirname(__file__)), "examples", "*.py")))


def test_there_are_examples():
    assert len(EXAMPLES) >= 8


def test_every_example_passes_arise_checks():
    sc = Scripts(DB(":memory:"), RecorderAdapter())
    for f in EXAMPLES:
        r = sc.import_source(f, open(f, encoding="utf-8").read())
        assert r["report"]["ok"], f"{os.path.basename(f)}:\n{sc.format_report(r['report'])}"


def test_examples_also_pass_the_older_strict_dry_run():
    """Older app builds block every network domain during the dry run; scripts must still pass."""
    from arise import sandbox
    from arise.scripts import ScriptAPI
    for f in EXAMPLES:
        src = open(f, encoding="utf-8").read()
        meta = sandbox.parse_meta(src)
        factory = lambda: ScriptAPI(RecorderAdapter(), meta["permissions"], lambda m: None,
                                    kv=lambda *a: a[-1], domains=(), http=lambda u: "")
        bad = [t for t in sandbox.run_tests(src, factory) if not t["ok"]]
        assert not bad, f"{os.path.basename(f)}: {bad}"
