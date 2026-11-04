"""Script validation + restricted execution.

SECURITY MODEL (read this): scripts are checked statically (AST allow-list: only safe imports, no
eval/exec/open/getattr, no underscore attributes), then run with a reduced set of builtins, only
the `arise` API object (every call needs a declared AND approved permission), loop/function
step counters and a hard time limit. This blocks the common abuse paths but is NOT a hard
OS-level sandbox, which is why every script also needs your explicit approval and is
pinned to its SHA-256 hash."""
import ast, builtins, re, threading, time, types, json

MAX_SOURCE = 64 * 1024
ALLOWED_IMPORTS = {"json", "math", "re", "datetime", "time", "random", "statistics", "collections",
                   "itertools", "functools", "string", "decimal", "fractions", "textwrap",
                   "calendar", "heapq", "bisect", "operator"}
BLOCKED_NAMES = {"eval", "exec", "compile", "open", "__import__", "globals", "locals", "vars", "getattr",
                 "setattr", "delattr", "hasattr", "input", "breakpoint", "memoryview", "exit", "quit",
                 "help", "type", "dir", "super"}
PERMISSIONS = {"notify", "speak", "open_app", "open_url", "network", "storage"}
METHOD_PERMS = {"notify": "notify", "speak": "speak", "open_app": "open_app", "open_url": "open_url",
                "http_get": "network", "storage_get": "storage", "storage_set": "storage"}
FREE_METHODS = {"log", "progress", "now"}
SAFE_BUILTINS = ["abs", "all", "any", "ascii", "bin", "bool", "bytes", "callable", "chr", "dict", "divmod",
                 "enumerate", "filter", "float", "format", "frozenset", "hash", "hex", "int", "isinstance",
                 "issubclass", "iter", "len", "list", "map", "max", "min", "next", "object", "oct", "ord",
                 "pow", "range", "repr", "reversed", "round", "set", "slice", "sorted", "str", "sum",
                 "tuple", "zip", "property", "staticmethod", "classmethod", "Exception", "ValueError",
                 "TypeError", "KeyError", "IndexError", "RuntimeError", "ZeroDivisionError",
                 "AssertionError", "StopIteration", "ArithmeticError", "LookupError", "AttributeError",
                 "NotImplementedError", "TimeoutError", "PermissionError", "True", "False", "None"]


def parse_meta(source, fallback="script"):
    meta = {"name": None, "description": "", "permissions": [], "category": "General"}
    for line in source.splitlines()[:30]:
        m = re.match(r"#\s*(name|description|permissions|category)\s*:\s*(.*)$", line.strip(), re.I)
        if m:
            key, val = m.group(1).lower(), m.group(2).strip()
            meta[key] = ([p.strip().lower() for p in re.split(r"[,\s]+", val) if p.strip()]
                         if key == "permissions" else val)
    if not meta["name"]:
        try:
            doc = ast.get_docstring(ast.parse(source))
        except SyntaxError:
            doc = None
        if doc:
            meta["name"] = doc.splitlines()[0][:60]
            meta["description"] = meta["description"] or " ".join(doc.split()[:30])
    meta["name"] = (meta["name"] or fallback)[:60]
    return meta


def check_policy(source):
    """Return (issues, used_permissions, tree)."""
    issues, used = [], set()
    if len(source.encode("utf-8", "replace")) > MAX_SOURCE:
        return [f"file is larger than {MAX_SOURCE // 1024} KB"], used, None
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return [f"syntax error on line {e.lineno}: {e.msg}"], used, None
    for node in ast.walk(tree):
        ln = getattr(node, "lineno", 0)
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name not in ALLOWED_IMPORTS:
                    issues.append(f"line {ln}: import '{a.name}' is not allowed")
        elif isinstance(node, ast.ImportFrom):
            if node.level or (node.module or "") not in ALLOWED_IMPORTS:
                issues.append(f"line {ln}: import from '{node.module}' is not allowed")
        elif isinstance(node, ast.Name):
            if node.id in BLOCKED_NAMES or (node.id.startswith("__") and node.id != "__name__"):
                issues.append(f"line {ln}: use of '{node.id}' is not allowed")
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("_"):
                issues.append(f"line {ln}: access to private attribute '{node.attr}' is not allowed")
            if isinstance(node.value, ast.Name) and node.value.id == "arise":
                if node.attr in METHOD_PERMS:
                    used.add(METHOD_PERMS[node.attr])
                elif node.attr not in FREE_METHODS:
                    issues.append(f"line {ln}: unknown API 'arise.{node.attr}'")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and "__" in node.value:
            issues.append(f"line {ln}: strings containing '__' are not allowed")
        elif isinstance(node, (ast.AsyncFunctionDef, ast.Await, ast.AsyncFor, ast.AsyncWith)):
            issues.append(f"line {ln}: async code is not supported")
    return list(dict.fromkeys(issues)), used, tree


class _Instrument(ast.NodeTransformer):
    """Insert a step/time check at the start of every loop body and function body."""

    @staticmethod
    def _tick():
        return ast.Expr(ast.Call(ast.Name("__tick__", ast.Load()), [], []))

    def _wrap(self, node):
        self.generic_visit(node)
        node.body.insert(0, self._tick())
        return node

    visit_For = visit_While = visit_FunctionDef = _wrap


def _safe_module(mod, tick_state):
    ns = {k: getattr(mod, k) for k in dir(mod)
          if not k.startswith("_") and not isinstance(getattr(mod, k), types.ModuleType)}
    if mod.__name__ == "time":
        def sleep(seconds):
            end = time.monotonic() + max(0.0, min(float(seconds), 30.0))
            while time.monotonic() < end:
                tick_state["tick"]()
                time.sleep(0.05)
        ns["sleep"] = sleep
    return types.SimpleNamespace(**ns)


def _namespace(api, state, log):
    def tick():
        state["steps"] += 1
        if state["steps"] > 5_000_000:
            raise TimeoutError("script used too many steps")
        if time.monotonic() > state["deadline"]:
            raise TimeoutError(f"script exceeded the {state['timeout']:.0f}s time limit")
    state["tick"] = tick
    cache = {}

    def _import(name, globals=None, locals=None, fromlist=(), level=0):
        if name not in ALLOWED_IMPORTS or level:
            raise ImportError(f"import '{name}' is not allowed")
        if name not in cache:
            cache[name] = _safe_module(__import__(name), state)
        return cache[name]

    def _print(*args, **kw):
        if sum(len(x) for x in log) < 20000:
            log.append(" ".join(str(a) for a in args))

    safe = {n: getattr(builtins, n) for n in SAFE_BUILTINS if hasattr(builtins, n)}
    safe.update({"__build_class__": builtins.__build_class__, "__import__": _import, "print": _print})
    return {"__builtins__": safe, "__name__": "__arise_script__", "arise": api, "__tick__": tick}


def _to_text(v):
    if v is None:
        return "Done"
    if isinstance(v, str):
        return v[:2000]
    try:
        return json.dumps(v, default=str)[:2000]
    except Exception:
        return str(v)[:2000]


def _where(exc):
    tb, line = exc.__traceback__, None
    while tb:
        if tb.tb_frame.f_code.co_filename == "<arise-script>":
            line = tb.tb_lineno
        tb = tb.tb_next
    return f"line {line}: " if line else ""


def _run(code, api, entry, timeout, call=None):
    state = {"steps": 0, "timeout": timeout, "deadline": time.monotonic() + timeout}
    log, box = [], {}
    ns = _namespace(api, state, log)

    def job():
        try:
            exec(code, ns)
            if call:
                box["value"] = call(ns)
            else:
                fn = ns.get(entry)
                box["value"] = fn() if callable(fn) else None
        except BaseException as e:           # report everything, never crash the app
            box["error"] = f"{_where(e)}{type(e).__name__}: {e}"

    t0 = time.monotonic()
    t = threading.Thread(target=job, daemon=True)
    t.start()
    t.join(timeout + 1.5)
    dur = time.monotonic() - t0
    if t.is_alive():
        return {"ok": False, "error": f"script exceeded the {timeout:.0f}s time limit", "log": "\n".join(log), "duration": dur}
    if "error" in box:
        return {"ok": False, "error": box["error"], "log": "\n".join(log), "duration": dur}
    return {"ok": True, "result": _to_text(box.get("value")), "log": "\n".join(log), "duration": dur}


def execute(source, api, entry="main", timeout=20.0):
    issues, _, tree = check_policy(source)
    if issues:
        return {"ok": False, "error": "; ".join(issues[:3]), "log": "", "duration": 0.0}
    tree = ast.fix_missing_locations(_Instrument().visit(tree))
    return _run(compile(tree, "<arise-script>", "exec"), api, entry, timeout)


def run_tests(source, api_factory, timeout=5.0):
    """Run built-in smoke test + every top-level `def test_*()` with a dry-run API."""
    issues, _, tree = check_policy(source)
    if issues:
        return [{"name": "policy check", "ok": False, "message": "; ".join(issues[:3])}]
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
    has_main = any(isinstance(n, ast.FunctionDef) and n.name == "main" for n in tree.body)
    code = compile(ast.fix_missing_locations(_Instrument().visit(tree)), "<arise-script>", "exec")
    out = []
    if has_main:
        r = _run(code, api_factory(), "main", timeout)
        out.append({"name": "dry-run main()", "ok": r["ok"], "message": r.get("error", "completed")})
    else:
        out.append({"name": "dry-run main()", "ok": False, "message": "script must define main()"})
    for n in names:
        r = _run(code, api_factory(), n, timeout)
        out.append({"name": n, "ok": r["ok"], "message": r.get("error", "passed")})
    return out
