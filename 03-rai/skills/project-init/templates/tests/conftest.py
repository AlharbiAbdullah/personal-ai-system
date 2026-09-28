"""Scenario linkage for pytest (the process: specs/README.md, "Tests and commits").

- Registers the marker: @pytest.mark.spec("cli.no-args") names the scenario ids a test proves.
- --spec <id> (repeatable, or comma-separated) runs only the tests linked to those ids.
- Every run writes .cache/spec-results.json at the repo root: per id, the linked test nodes and
  their outcome (passed | failed | error | xfailed | xpassed | skipped | notrun), the exception
  type of a failure, what the test body raised and whether the test's own code raised it
  (raised_in), the xfail and skip markers, collection errors, and the blob id of every file
  outside specs/, proof/ and .cache/. `scripts/project.py check` and
  `status` read it: check refuses results when any of those files changed since the run, and
  a gap test whose body never ran or failed for another reason than an assertion (xfail
  run=False, a failing fixture, a pytest.xfail() or pytest.fail() call, an AttributeError from
  a typo), since fixing the gap could never turn such a test into a red XPASS. A gap test that
  xfails on the crash itself names its type: xfail(strict=True, raises=IndexError, ...).
- A run that left any test out (--spec, -k, -m, --ignore, -c, an -o that is not a strictness
  switch, a path argument, -x, ...) is marked partial, so check never mistakes it for the
  whole suite. --collect-only writes nothing.
Written by project-init and hash-tracked in .project.toml; a local edit shows as drift.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path

import pytest

RESULTS = Path(".cache") / "spec-results.json"
FORMAT = 3
XPASS_STRICT = "[XPASS(strict)]"
NOT_TEST_INPUTS = ("specs/", ".cache/", "proof/")  # edits here never change a test outcome
# git settings for tree_files: `ls-files -m` checks every tracked file against its full stat
# data (content when racy), never through an fsmonitor or a cache a local config could leave
# stale. scripts/project.py passes the same ones.
FULL_STAT = (
    *("-c", "core.fsmonitor=false"),
    *("-c", "core.untrackedCache=false"),
    *("-c", "core.checkStat=default"),
    *("-c", "core.trustctime=true"),
)
# -o keys that only make a run stricter when set true. pytest 9 turns --strict-markers and
# --strict-config into -o strict_markers=true and -o strict_config=true.
STRICTNESS_KEYS = frozenset(
    {
        "strict",
        "strict_config",
        "strict_markers",
        "strict_xfail",
        "xfail_strict",
        "strict_parametrization_ids",
    }
)
TRUE_VALUES = ("y", "yes", "t", "true", "on", "1")  # what pytest reads as true

_state: dict[str, object] = {}


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--spec",
        action="append",
        default=[],
        metavar="ID",
        help="run only tests linked to these scenario ids (repeatable or comma-separated)",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "spec(*ids): scenario ids this test proves")
    _state.clear()
    _state.update(
        nodes={},
        collect_errors=[],
        bad_tags=[],
        deselected=0,
        dropped=0,
        collected=0,
        exc={},
    )


def _count(key: str) -> int:
    value = _state.get(key, 0)
    return value if isinstance(value, int) else 0


def _wanted(config: pytest.Config) -> set[str]:
    values = config.getoption("--spec") or []
    return {part for value in values for part in re.split(r"[,\s]+", value) if part}


def _ids(item: pytest.Item) -> tuple[list[str], str | None]:
    """The ids a test is linked to, and a problem with its spec markers if any."""
    ids: list[str] = []
    problem = None
    for mark in item.iter_markers("spec"):
        if not mark.args or mark.kwargs:
            problem = 'use @pytest.mark.spec("<cap>.<slug>", ...) with ids only'
        for arg in mark.args:
            if isinstance(arg, str) and arg:
                if arg not in ids:
                    ids.append(arg)
            else:
                problem = f"spec ids are strings, got {arg!r}"
    return ids, problem


def _ini(config: pytest.Config, *names: str) -> object:
    for name in names:
        try:
            value = config.getini(name)
        except ValueError:
            continue
        if value is not None:
            return value
    return None


def _xfail(item: pytest.Item) -> dict[str, object] | None:
    """The nearest xfail marker as {strict, run, reason, conditional}, resolved like pytest."""
    for mark in item.iter_markers("xfail"):
        strict = mark.kwargs.get("strict")
        if strict is None:
            strict = _ini(item.config, "strict_xfail", "xfail_strict", "strict")
        conditional = bool(mark.args) or "condition" in mark.kwargs
        reason = str(mark.kwargs.get("reason", ""))
        run = bool(mark.kwargs.get("run", True))
        return {
            "strict": bool(strict),
            "run": run,
            "reason": reason,
            "conditional": conditional,
            "raises": _type_names(mark.kwargs.get("raises")),
        }
    return None


def _type_names(raises: object) -> list[str]:
    """Names of the exception types an xfail(raises=...) accepts: a type, a tuple of types, or
    a matcher object that lists them in expected_exceptions."""
    if raises is None:
        return []
    kinds = getattr(raises, "expected_exceptions", raises)
    kinds = kinds if isinstance(kinds, tuple) else (kinds,)
    return [kind.__name__ if isinstance(kind, type) else repr(kind) for kind in kinds]


def _skip_marked(item: pytest.Item) -> bool:
    return any(True for _ in item.iter_markers("skip")) or any(
        True for _ in item.iter_markers("skipif")
    )


@pytest.hookimpl(wrapper=True)
def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> Generator[None, None, None]:
    """Counts tests another plugin dropped without reporting them deselected, then applies
    --spec last, after every other plugin."""
    before, reported = len(items), _count("deselected")
    result = yield
    dropped = before - len(items) - (_count("deselected") - reported)
    if dropped > 0:
        _state["dropped"] = dropped
    wanted = _wanted(config)
    if wanted:
        keep = [item for item in items if set(_ids(item)[0]) & wanted]
        drop = [item for item in items if not set(_ids(item)[0]) & wanted]
        if drop:
            config.hook.pytest_deselected(items=drop)
            items[:] = keep
    return result


def pytest_deselected(items: list[pytest.Item]) -> None:
    _state["deselected"] = _count("deselected") + len(items)


def pytest_collection_finish(session: pytest.Session) -> None:
    nodes: dict[str, dict[str, object]] = {}
    bad: list[dict[str, str]] = []
    for item in session.items:
        ids, problem = _ids(item)
        if problem:
            bad.append({"node": item.nodeid, "problem": problem})
        if ids:
            nodes[item.nodeid] = {
                "ids": ids,
                "outcome": "notrun",
                "xfail": _xfail(item),
                "skip": _skip_marked(item),
                "body": None,  # what the test function raised: None = it never ran, "" = nothing
                "raised_in": "",  # "test": the test's own code raised it; "code": anything else
                "crash": "",
                "exc": "",
            }
    _state.update(nodes=nodes, bad_tags=bad, collected=len(session.items))


def _last_error_line(text: str) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    for line in reversed(lines):
        if line.startswith("E "):
            return line[1:].strip()[:300]
    return (lines[-1].strip() if lines else "")[:300]


def pytest_exception_interact(
    node: pytest.Item | pytest.Collector,
    call: pytest.CallInfo[object],
    report: pytest.TestReport | pytest.CollectReport,
) -> None:
    """Record the exception type: pytest calls this for real failures, never for skip/xfail."""
    if call.excinfo is None:
        return
    error = call.excinfo.value
    if isinstance(error, pytest.Collector.CollectError) and error.__cause__ is not None:
        error = error.__cause__  # the import or syntax error behind a failed module
    name = type(error).__name__
    nodes = _state.get("nodes")
    if isinstance(report, pytest.CollectReport):
        exc = _state.get("exc")
        if isinstance(exc, dict):
            exc[report.nodeid or "."] = name
    elif isinstance(nodes, dict) and node.nodeid in nodes and not nodes[node.nodeid]["exc"]:
        nodes[node.nodeid]["exc"] = name


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> Generator[None, pytest.TestReport, pytest.TestReport]:
    """Record what the test body raised. A gap test must fail in its body, on an assertion (or
    on the crash its xfail(raises=...) names): an xfail that comes from run=False, a failing
    fixture, a pytest.xfail() or pytest.fail() call, or an unrelated error never turns into an
    XPASS when the gap is fixed."""
    report = yield
    nodes = _state.get("nodes")
    if call.when == "call" and isinstance(nodes, dict) and item.nodeid in nodes:
        nodes[item.nodeid]["body"] = _body(call)
        nodes[item.nodeid]["raised_in"] = _raised_in(item, call)
    return report


def _raised_in(item: pytest.Item, call: pytest.CallInfo[None]) -> str:
    """Whose code raised what the body let out: "test" when the innermost frame inside the
    repo (the virtualenv left out) is a file of the test's own suite folder, such as an
    IndexError from `r.stdout.splitlines()[0]` on empty output; "code" otherwise; "" when the
    body raised nothing. A test-side exception proves nothing about the code under test."""
    if call.excinfo is None:
        return ""
    root = item.config.rootpath.resolve()
    try:
        own = item.path.resolve().relative_to(root)
    except ValueError:
        return "code"
    suite = root / _suite_folder(own)
    for entry in reversed(call.excinfo.traceback):
        where = Path(str(entry.path)).resolve()
        if not where.is_relative_to(root) or where.is_relative_to(root / ".venv"):
            continue  # the stdlib, a dependency: look further out, for the repo's own frame
        return "test" if where == suite or where.is_relative_to(suite) else "code"
    return "code"


def _suite_folder(own: Path) -> Path:
    """The suite folder of a test file (repo-relative): its outermost tests/ or test/ folder,
    so backend/tests/unit/test_x.py belongs to backend/tests, not to the whole backend/ with
    the code beside it; else the file's first folder."""
    for depth, part in enumerate(own.parts[:-1]):
        if part in ("tests", "test"):
            return Path(*own.parts[: depth + 1])
    return Path(own.parts[0])


def _body(call: pytest.CallInfo[None]) -> str:
    """What the test body raised: "" for nothing, "DID NOT RAISE" for a pytest.raises that saw
    no exception, else the exception type name ("Failed" is a pytest.fail() call)."""
    if call.excinfo is None:
        return ""
    name = call.excinfo.typename
    if name == "Failed" and str(call.excinfo.value).startswith("DID NOT RAISE"):
        return "DID NOT RAISE"
    return name


def pytest_collectreport(report: pytest.CollectReport) -> None:
    if report.failed:
        errors = _state.get("collect_errors")
        exc = _state.get("exc")
        if isinstance(errors, list):
            node = report.nodeid or "."
            name = exc.get(node, "") if isinstance(exc, dict) else ""
            errors.append(
                {
                    "node": node,
                    "error": _last_error_line(report.longreprtext),
                    "exc": name,
                }
            )


def _phase_outcome(report: pytest.TestReport) -> str | None:
    """Outcome of one phase; None when a setup or teardown phase simply passed."""
    xfailed = hasattr(report, "wasxfail")
    if report.when == "call":
        if report.passed:
            return "xpassed" if xfailed else "passed"
        if report.skipped:
            return "xfailed" if xfailed else "skipped"
        longrepr = report.longrepr
        if isinstance(longrepr, str) and longrepr.startswith(XPASS_STRICT):
            return "xpassed"
        return "failed"
    if report.passed:
        return None
    if report.skipped:
        return "xfailed" if xfailed else "skipped"
    return "error"


def _crash(report: pytest.TestReport) -> str:
    longrepr = report.longrepr
    if isinstance(longrepr, str):
        return longrepr[:300]
    reprcrash = getattr(longrepr, "reprcrash", None)
    message = getattr(reprcrash, "message", "")
    if isinstance(message, str) and message:
        return message.splitlines()[0][:300]
    return _last_error_line(report.longreprtext)


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    nodes = _state.get("nodes")
    if not isinstance(nodes, dict) or report.nodeid not in nodes:
        return
    info = nodes[report.nodeid]
    outcome = _phase_outcome(report)
    if outcome is None:
        return
    if report.when == "teardown" and info["outcome"] not in ("passed", "xpassed"):
        return  # a teardown error never hides the call outcome
    info["outcome"] = outcome
    if outcome in ("failed", "error", "xpassed") and not report.passed:
        info["crash"] = _crash(report)


def _suite_roots(config: pytest.Config) -> list[Path]:
    """What a full run covers: the testpaths from the config, or else the whole rootdir."""
    root = config.rootpath
    roots: list[Path] = []
    for pattern in config.getini("testpaths") or []:
        roots.extend(sorted(root.glob(str(pattern))) or [root / str(pattern)])
    return [path.resolve() for path in roots] or [root.resolve()]


def _uncovered(config: pytest.Config) -> list[str]:
    """Suite roots that no path argument covers: running `pytest tests/more`, or pytest from a
    subfolder, leaves the rest of the suite out. `file::test` arguments cover nothing."""
    if config.args_source == pytest.Config.ArgsSource.TESTPATHS:
        return []
    base = config.invocation_params.dir
    given = [(base / arg).resolve() for arg in config.args if "::" not in arg]
    missed = [
        root
        for root in _suite_roots(config)
        if not any(root == path or root.is_relative_to(path) for path in given)
    ]
    if not missed:
        return []
    shown = [arg if "::" in arg else _relative(base / arg, config) for arg in config.args]
    return [f"selected {' '.join(shown)}"]


def _relative(path: Path, config: pytest.Config) -> str:
    try:
        return path.resolve().relative_to(config.rootpath.resolve()).as_posix() or "."
    except ValueError:
        return str(path)


def _loosening_overrides(overrides: list[str]) -> list[str]:
    """Keys of the -o overrides that could change what runs or how it is judged: everything
    except a strictness switch set true (it can only turn a pass into a failure)."""
    keys: set[str] = set()
    for entry in overrides:
        key, _, value = str(entry).partition("=")
        key = key.strip()
        if key in STRICTNESS_KEYS and value.strip().lower() in TRUE_VALUES:
            continue
        keys.add(key)
    return sorted(keys)


def _partial(session: pytest.Session, exitstatus: int) -> list[str]:
    """Why this run is not the whole suite as committed; empty for a complete run.

    Options count wherever they come from (command line, PYTEST_ADDOPTS or addopts): a folder
    the suite must never collect goes in norecursedirs, not --ignore. A -c config file, or an
    -o override other than a strictness switch set true, makes the run partial, since
    collection rules (testpaths, python_files, ...) and xfail strictness live in the ini
    settings.
    """
    config = session.config
    option = config.option
    reasons: list[str] = []
    if _wanted(config):
        reasons.append("--spec")
    if option.keyword:
        reasons.append("-k")
    if option.markexpr:
        reasons.append("-m")
    if keys := _loosening_overrides(getattr(option, "override_ini", None) or []):
        reasons.append(f"-o {','.join(keys)}")
    for flag, dest in (
        ("-c", "inifilename"),
        ("--rootdir", "rootdir"),
        ("--ignore", "ignore"),
        ("--ignore-glob", "ignore_glob"),
        ("--lf", "lf"),
        ("--sw", "stepwise"),
        ("--runxfail", "runxfail"),
        ("--setup-only", "setuponly"),
        ("--setup-plan", "setupplan"),
    ):
        if getattr(option, dest, None):
            reasons.append(flag)
    if deselected := _count("deselected"):
        reasons.append(f"{deselected} deselected")
    if dropped := _count("dropped"):
        reasons.append(f"{dropped} dropped by a plugin")
    reasons.extend(_uncovered(config))
    if session.shouldfail or session.shouldstop:
        reasons.append("stopped early")
    if exitstatus == pytest.ExitCode.INTERRUPTED:
        reasons.append("interrupted")
    return reasons


def _git(root: Path, *args: str, stdin: bytes | None = None) -> bytes | None:
    try:
        proc = subprocess.run(  # noqa: S603
            ["git", *args],  # noqa: S607
            cwd=root,
            input=stdin,
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    return proc.stdout if proc.returncode == 0 else None


def tree_files(root: Path) -> dict[str, str] | None:
    """path -> blob id of each file git sees outside specs/, proof/ and .cache/, as it is on
    disk now: tracked files and untracked files that are not ignored. None outside a git work tree.
    A tracked file keeps its index blob id only when git compares it with the disk by its full
    stat data: one marked assume-unchanged or skip-worktree (git never looks at it) is hashed
    from the disk, and no fsmonitor, untracked cache or looser stat setting is trusted.
    scripts/project.py holds the same function; check compares its map with this one and
    refuses the results when they differ (a file changed after the tests ran)."""
    index = _git(root, *FULL_STAT, "ls-files", "-s", "-v", "-z")
    changed = _git(root, *FULL_STAT, "ls-files", "-z", "-m", "-d", "-o", "--exclude-standard")
    if index is None or changed is None:
        return None
    files: dict[str, str] = {}
    unwatched: list[str] = []
    for entry in index.decode("utf-8", "surrogateescape").split("\0"):
        meta, _, path = entry.partition("\t")
        if not path:
            continue
        tag, _mode, blob = meta.split()[:3]
        files[path] = blob
        if tag != "H":  # h: assume-unchanged, S or s: skip-worktree, M: unmerged
            unwatched.append(path)
    regular: list[str] = []
    listed = changed.decode("utf-8", "surrogateescape").split("\0")
    for path in dict.fromkeys([*listed, *unwatched]):
        if not path:
            continue
        files.pop(path, None)
        full = root / path
        if full.is_symlink():
            files[path] = "link:" + os.readlink(full)
        elif full.is_file():
            regular.append(path)
    if regular:
        request = "".join(f"{path}\n" for path in regular).encode("utf-8", "surrogateescape")
        out = _git(root, "hash-object", "--stdin-paths", stdin=request)
        hashes = out.decode().split() if out is not None else []
        if len(hashes) != len(regular):
            return None
        files.update(zip(regular, hashes, strict=True))
    return {p: h for p, h in sorted(files.items()) if not p.startswith(NOT_TEST_INPUTS)}


def _repo_root(config: pytest.Config) -> Path | None:
    out = _git(config.rootpath, "rev-parse", "--show-toplevel")
    return Path(out.decode().strip()) if out else None


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    config = session.config
    if config.option.collectonly or hasattr(config, "workerinput"):
        return
    nodes = _state.get("nodes")
    if not isinstance(nodes, dict):
        return
    by_id: dict[str, list[dict[str, str]]] = {}
    for node, info in sorted(nodes.items()):
        for spec_id in info["ids"]:
            by_id.setdefault(spec_id, []).append({"node": node, "outcome": info["outcome"]})
    partial = _partial(session, int(exitstatus))
    repo = _repo_root(config)
    data = {
        "format": FORMAT,
        "finished": datetime.now(UTC).isoformat(timespec="seconds"),
        "complete": not partial,
        "partial": partial,
        "exitstatus": int(exitstatus),
        "collected": _state.get("collected", 0),
        "ids": dict(sorted(by_id.items())),
        "nodes": dict(sorted(nodes.items())),
        "collect_errors": _state.get("collect_errors", []),
        "bad_tags": _state.get("bad_tags", []),
        "files": tree_files(repo) if repo else None,
    }
    path = (repo or config.rootpath) / RESULTS
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)
