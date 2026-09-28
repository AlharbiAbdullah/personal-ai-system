#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""project-init's deterministic half. Rai-side only: it is never copied into a repo.

The phase files in ../phases/ say when each subcommand runs; the design is
03-rai/skills/project-init/DESIGN.md, section 6.

  preflight [<repo>] [--json]          P0: mode, stops, git facts, tier, tools, env reads,
                                       signals, vault matches. Read-only; exit 1 on a stop.
  probe [<repo>] [--json]              P1: every console script run in a scratch clone of the
                                       committed state, network off, each case in its own PID
                                       namespace (nothing it starts outlives it). Never writes
                                       the repo. Then the trunk candidates (v3.1) from a static
                                       scan: console-script modules, fan-in, settings modules,
                                       schema folders, paths a standing rule names.
  prepare [<repo>] [--python X.Y]      P4, before render, on plan/project-init: with no
         [--dry-run]                   .python-version, the pin (--python, else the first of
                                       the Dockerfile/CI versions, the requires-python floor
                                       and uv's default that builds in a scratch clone), then
                                       `uv add --dev` of ruff, ty, pytest and the project's
                                       own dev/test extras and groups, `uv lock`, `uv sync
                                       --locked`.
  render [<repo>] [--check]            P4, EXTEND: the machinery from ../templates. Hash-aware
         [--values <json>|@<file>]     (.project.toml [generated]): an unchanged render is
         [--force-file <path>]...      upgraded, a customized file gets a diff and a question.
         [--keep-file <path>]...       A run that meets a customized file writes nothing until
         [--remote github] [--offline] each one is answered with --force-file or --keep-file.
         [--agents-symlink]            Seeds (lessons.md, decisions/, team.md) are written once,
                                       when missing, and listed in [seeded]. The ruff and
                                       history-leak baselines are taken once, at adoption.
                                       Exit 1 on an unfilled placeholder, 3 on a customized
                                       file (with --check: on any drift, front door included,
                                       and a specs/tech-stack.md with no ## Trunk section).
  render [<repo>] --front-door [...]   P6: AGENTS.md and the README quickstart region, only from
                                       the commands .agent/project-init/verify.json records
                                       green (R2); same hash rules and exit codes.
  selftest [<repo>] [--start-args <s>] P5: the positive checks under timeouts (60 s; the
         [--suite-timeout <seconds>]   suite's verify and test max(600 s, twice the last run),
         [-- <project.py args>]        the release and per-signal dry-runs included), then the
                                       repo's own `project.py selftest` (the negative matrix).
                                       The happy path: --start-args, else the README's first
                                       fence, else the probe's passing row. Writes
                                       .agent/project-init/verify.json; exit 0 only when every
                                       required check and the matrix are green.
  publish [<repo>] [--remote github]   P7: the ship commit (a named pathspec, the body from
         [--repo <name>] [--dry-run]   verify.json) on plan/project-init; with --remote github
                                       the five remote steps (the repo named after the folder
                                       unless --repo names it), each recorded in
                                       .agent/project-init/publish.json so a re-run continues
                                       at the step that failed. --dry-run runs nothing.
  migrate-v2 [<repo>] [--apply]        EXTEND + v2 migrate (9-migrate.md): without --apply, the
                                       one migration prompt (each v2 item and its fate, the
                                       lessons it contradicts); writes nothing. --apply, on
                                       plan/project-init after the yes and P2: git mv
                                       .mise.toml, the v2 hooks unregistered, the deletions
                                       staged, `.claude` out of the ruff extend-exclude.
  migrate-v1 [<repo>] [--apply]        MIGRATE (9-migrate.md), after migrate-transcripts:
                                       without --apply, the v1 items and their fates; writes
                                       nothing. --apply, on plan/project-init: the legacy
                                       knowledge rendered once into specs/backlog/, the
                                       project-session hooks unregistered, accumulated_knowledge
                                       .json and the hooks git rm'd, the legacy .gitignore block
                                       removed.
  migrate-transcripts [<repo>]         MIGRATE step 1 on project_memory/{sessions,pending,
         [--archive-root <dir>]        summaries,chromadb}: quarantine (mode 700), links and
         [--quarantine-root <dir>]     archives made plain, gitleaks redaction across every
         [--name <archive folder>]     file, a clean rescan that proves it read every piece
         [--resume]                    of every file, then the archive copy. A file whose
                                       finding cannot be replaced in place is held back in
                                       .held/ (file and rule named) and the run exits 1. The
                                       decoded views live in <quarantine>/.work, removed after
                                       each scan and on SIGTERM or SIGHUP. A re-run with no
                                       store left reports this repo's quarantine (exit 1
                                       while it holds unarchived files); --resume finishes an
                                       unfinished one. Refuses git-tracked stores. Never
                                       stages in the repo.

Every call is one line, typed from the repo root:

  env -C ~ ~/.claude/skills/project-init/scripts/init.py <command> "$PWD" [flags]

`env -C ~` starts it outside the repo and "$PWD" names the repo: the shebang's `uv` is often a
mise shim, and a shim refuses to start under a repo's untrusted mise.toml.

Exit codes: 0 ok, 1 a stop, refusal or failure, 2 usage, 3 drift or a customized file,
128 + N stopped by signal N (130 SIGINT, 143 SIGTERM).
Stdlib only.
"""

from __future__ import annotations

import argparse
import ast
import bz2
import configparser
import contextlib
import datetime as dt
import difflib
import fcntl
import gzip
import hashlib
import itertools
import json
import lzma
import math
import os
import re
import secrets
import selectors
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_DIR / "templates"
STANDARD = "project-init v3"
GITLEAKS_PIN = "gitleaks@8.30.1"
MANIFEST = ".project.toml"

LOCKFILES = frozenset(
    {
        "uv.lock",
        "mise.lock",
        "poetry.lock",
        "pdm.lock",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "bun.lock",
        "bun.lockb",
        "Cargo.lock",
        "go.sum",
    }
)
# v1 kept every store under project_memory/ (the v1 project_init skill). A root-level
# sessions/ or pending/ is the project's own code, never a legacy store.
LEGACY_BASE = "project_memory"
LEGACY_NAMES = ("accumulated_knowledge.json", "sessions", "summaries", "pending", "chromadb")
TRANSCRIPT_DIRS = ("sessions", "pending", "summaries")
LEGACY_HOOKS = ".claude/hooks/project-session-*.py"
V2_STAMP = re.compile(r"(?m)^\s*Standard: project-init v2\b")
V2_NAME = "project-init v2"  # .project.toml `migrated_from` once a render met the v2 stamp
V2_CI = ".github/workflows/ci.yml"
# The v2 files the one migration prompt (9-migrate.md) hands to the v3 render. With no recorded
# hash, a render treats them as unchanged renders: the prompt was their question (R3).
V2_REPLACED = frozenset(
    {
        "mise.toml",  # the v2 .mise.toml, after its git mv
        ".claude/settings.json",
        ".env.example",
        ".editorconfig",
        "project_memory/README.md",
        V2_CI,
        ".github/CODEOWNERS",
        ".github/pull_request_template.md",
        "AGENTS.md",
    }
)
SIGNALS = ("cli", "api", "db", "ui", "deploy", "pipeline")
NO_ORDER = ("db", "api", "ui", "deploy", "pipeline")  # the order P0 prints absent signals in
RESTRICTED_SIGNALS = frozenset({"api", "deploy", "pipeline", "db"})  # probe: --help only
DISTRIBUTIONS = frozenset({"pypi", "git", "service", "none"})
PLACEHOLDER = re.compile(r"\{([A-Z][A-Z0-9_]*)\}")
CONDITIONAL = re.compile(r"\{(IF_[A-Z0-9_]+)\}")
SECRET_NAME = re.compile(r"(?:^|_)(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD|PWD|CREDENTIALS?|DSN)(?:_|$)")
# a name that ends in a unit or a pointer holds a setting about the secret, not the secret itself
KNOB_TAIL = re.compile(
    r"_(?:TIMEOUT|S|MS|SEC|SECS|SECONDS|MINUTES|LIMIT|COUNT|MAX|MIN|SIZE|TTL|LEN|LENGTH|"
    r"RETRIES|FILE|PATH|DIR|NAME|ID|HEADER|FIELD|PARAM|ENABLED)$"
)
ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
# variables the OS, the shell or the interpreter set: never part of the app's env contract
OS_ENV = frozenset(
    {
        "HOME",
        "PATH",
        "PWD",
        "OLDPWD",
        "USER",
        "USERNAME",
        "LOGNAME",
        "SHELL",
        "TERM",
        "LANG",
        "LANGUAGE",
        "TMPDIR",
        "TMP",
        "TEMP",
        "TZ",
        "EDITOR",
        "VISUAL",
        "PAGER",
        "DISPLAY",
        "WAYLAND_DISPLAY",
        "HOSTNAME",
        "COLUMNS",
        "LINES",
        "NO_COLOR",
        "FORCE_COLOR",
        "VIRTUAL_ENV",
        "SHLVL",
        "UID",
        "EUID",
        "GID",
    }
)
OS_ENV_PREFIXES = ("LC_", "XDG_", "SSH_", "PYTHON", "CONDA_", "DBUS_")
BOT = re.compile(
    r"\[bot\]|dependabot|renovate|github-actions|pre-commit-ci|noreply@anthropic\.com|"
    r"^noreply@github\.com$",
    re.IGNORECASE,
)
NOREPLY_LOGIN = re.compile(r"^(?:\d+\+)?([^@]+)@users\.noreply\.github\.com$", re.IGNORECASE)
# values that land unquoted in sh (githooks) or YAML (ci.yml)
SAFE_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]*")
TOKEN_VALUES = ("DEFAULT_BRANCH", "CI_JOB", "CI_NAME", "CHECKOUT_REF", "MISE_ACTION_REF")
# values that land inside a TOML basic string ("..."): the start command in mise.toml, which may
# be any command line (`uvicorn backend.main:app --port 8000`)
TOML_STRING_VALUES = ("ENTRY",)
NOT_IN_TOML_STRING = re.compile(r'["\\\x00-\x1f\x7f]')
# values that land inside a Markdown code span (AGENTS.md) or a fenced line (README)
CODE_SPAN_VALUES = (
    "START_EXAMPLE",
    "START_EXPECTED",
    "TEST_TAG_EXAMPLE",
    "SERVICE",  # the per-signal skills: computed from the repo's files
    "DB_CONFIG",
    "DB_DIR",
    "DEPLOY_CONFIG",
    "DEPLOY_DIR",
)
MULTILINE_VALUES = frozenset(
    {"ENV_ROWS", "TEST_TAG_SYNTAX", "TEAM_ROWS", "CODEOWNERS_ROWS", "SERVICE_COMMANDS"}
)
CONTROL = re.compile(r"[\x00-\x1f\x7f]")
# P5 writes the record P6 builds the front door from (gitignored: .agent/ is local-only)
VERIFY_JSON = ".agent/project-init/verify.json"
FRONT_DOOR = ("AGENTS.md", "README.md")
# the template each front-door file is rendered from. P6 records their hashes in the manifest
# table below, so an EXTEND audit sees a template that moved without P5's record (render --check)
FRONT_DOOR_TEMPLATES = {"AGENTS.md": "AGENTS.md", "README.md": "README-quickstart.md"}
TEMPLATE_TABLE = "front_door_templates"
# the manifest's tables in the order every render writes them, so no render's output drifts
# from another's; a table this list lacks keeps its place after them
TABLE_ORDER = ("paths", "signals", "values", "generated", "seeded", "kept", TEMPLATE_TABLE)
FROM_VERIFY = frozenset({"START_EXAMPLE", "START_EXPECTED"})  # never from --values
HUMAN_TASKS = frozenset({"approve", "merge", "abandon", "release"})  # P5 never runs them
QS_BEGIN = "<!-- project-init:quickstart:begin"
QS_END = "<!-- project-init:quickstart:end -->"
MASKED = "(masked)"  # a secret's default, as preflight shows it
TEST_TAG_SYNTAX_PY = (
    '`@pytest.mark.spec("<id>", ...)` tags a test, and a gap test also carries '
    '`@pytest.mark.xfail(strict=True, reason="<id>: <why>")`.'
)
# a secret-bearing start: through `op run` when .env exists (it resolves the op:// pointers
# there), else the plain command, so a fresh checkout with no .env still starts. mise appends
# the args after `--` to the run string: sh passes them on as "$@". OP_RUN is the TOML-escaped
# form the start task's basic string holds.
OP_RUN_SH = (
    """sh -c 'if [ -f .env ]; then exec op run --env-file .env -- "$@"; fi; """
    """exec "$@"' op-run """
)
OP_RUN = OP_RUN_SH.replace('"', '\\"')
OP_RUN_V3_DRAFT = "op run --env-file .env -- "  # what an earlier render saved: read as OP_RUN
CRASH = "Traceback (most recent call last)"
STANDARD_BLOCK = "# project-init standard"  # the header of the lines render adds to a merged file


class Refusal(Exception):
    """A refusal the user must act on: printed, exit 1."""


class UsageError(Exception):
    """A bad invocation: printed, exit 2."""


class Stopped(BaseException):
    """SIGTERM or SIGHUP (a tool's timeout, a closed terminal), raised where the process is so
    it unwinds through the same cleanup as an error. Exit 128 + the signal number."""

    def __init__(self, signum: int) -> None:
        super().__init__(signum)
        self.signum = signum

    @property
    def name(self) -> str:
        return signal.Signals(self.signum).name


# ---------------------------------------------------------------------------------------------
# processes


@dataclass
class Result:
    code: int
    out: str
    err: str


def _text(data: str | bytes | None) -> str:
    if data is None:
        return ""
    return data.decode("utf-8", "replace") if isinstance(data, bytes) else data


def run(
    argv: list[str],
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: float = 60,
    own_group: bool = False,
) -> Result:
    """Run argv (never a shell) with stdin closed. 127: not found, 124: timed out.

    own_group: argv starts a process group of its own, SIGKILLed whole when argv exits or times
    out. The probe also runs each case in a PID namespace, which reaps what left the group."""
    if own_group:
        return _run_group(argv, cwd, env, timeout)
    try:
        proc = subprocess.run(  # noqa: S603 - argv lists built here, no shell
            argv,
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return Result(127, "", f"{argv[0]}: not found")
    except subprocess.TimeoutExpired as exc:
        return Result(124, _text(exc.stdout), _text(exc.stderr))
    except OSError as exc:
        return Result(126, "", str(exc))
    return Result(proc.returncode, _text(proc.stdout), _text(proc.stderr))


OUTPUT_HEAD = 64 * 1024  # bytes kept from the start of a child's stdout, and of its stderr
OUTPUT_TAIL = 64 * 1024  # and from the end: what falls between is counted, never held


class Capped:
    """One child stream, bounded: its first and last bytes and a count of the rest. A CLI that
    prints in a loop for its whole timeout costs at most head + tail + one read of memory."""

    def __init__(self, head: int = OUTPUT_HEAD, tail: int = OUTPUT_TAIL) -> None:
        self.head_cap = head
        self.tail_cap = tail
        self.head = bytearray()
        self.tail = bytearray()
        self.dropped = 0

    def add(self, chunk: bytes) -> None:
        room = self.head_cap - len(self.head)
        if room > 0:
            self.head += chunk[:room]
            chunk = chunk[room:]
        if not chunk:
            return
        self.tail += chunk
        extra = len(self.tail) - self.tail_cap
        if extra > 0:
            del self.tail[:extra]
            self.dropped += extra

    def text(self) -> str:
        cut = f"\n[... {self.dropped} bytes not kept ...]\n".encode() if self.dropped else b""
        return _text(bytes(self.head) + cut + bytes(self.tail))


def _drain(proc: subprocess.Popen[bytes], out: Capped, err: Capped, deadline: float) -> bool:
    """Read both pipes into their caps until each closes; False when the deadline came first."""
    with selectors.DefaultSelector() as selector:
        for stream, sink in ((proc.stdout, out), (proc.stderr, err)):
            if stream is not None:
                selector.register(stream, selectors.EVENT_READ, sink)
        while selector.get_map():
            left = deadline - time.monotonic()
            if left <= 0:
                return False
            for key, _ in selector.select(left):
                chunk = os.read(key.fd, 65536)
                if chunk:
                    key.data.add(chunk)
                else:
                    selector.unregister(key.fileobj)
    return True


def _run_group(
    argv: list[str], cwd: Path | None, env: dict[str, str] | None, timeout: float
) -> Result:
    try:
        proc = subprocess.Popen(  # noqa: S603 - argv lists built here, no shell
            argv,
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except FileNotFoundError:
        return Result(127, "", f"{argv[0]}: not found")
    except OSError as exc:
        return Result(126, "", str(exc))
    out, err = Capped(), Capped()
    deadline = time.monotonic() + timeout
    finished = False
    try:
        finished = _drain(proc, out, err, deadline)
        if finished:
            try:
                proc.wait(max(0.0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                finished = False
    finally:
        # whatever argv left behind in its group (a background child, say), all of it on a
        # timeout, and all of it when this process is stopped or fails while it waits
        _kill_group(proc.pid)
        proc.wait()
        for stream in (proc.stdout, proc.stderr):
            if stream is not None:
                stream.close()
    return Result(proc.returncode if finished else 124, out.text(), err.text())


def _kill_group(pgid: int) -> None:
    """SIGKILL a process group. The id stays reserved while any member lives, so a group whose
    leader has exited still names exactly the members it left behind."""
    try:
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def git_env() -> dict[str, str]:
    """No optional locks (git status would refresh the index: P0 and P1 write nothing), no
    prompts, stable messages."""
    env = dict(os.environ)
    env.update({"GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C"})
    env.setdefault("GIT_SSH_COMMAND", "ssh -o BatchMode=yes -o ConnectTimeout=8")
    return env


def git(repo: Path, *args: str, timeout: float = 60) -> Result:
    return run(["git", "-C", str(repo), *args], env=git_env(), timeout=timeout)


def git_out(repo: Path, *args: str) -> str | None:
    result = git(repo, *args)
    return result.out.strip() if result.code == 0 else None


# ---------------------------------------------------------------------------------------------
# small readers


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def load_toml(path: Path) -> dict[str, object]:
    import tomllib  # stdlib from 3.11; imported here so ruff sorts it the same under any target

    text = read_text(path)
    if text is None:
        return {}
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return {}


def parse_toml(text: str) -> dict[str, object]:
    import tomllib

    return tomllib.loads(text)


def toml_problem(path: Path) -> str | None:
    """Why a TOML file present on disk does not parse, or None (absent files parse fine)."""
    text = read_text(path) if path.is_file() else None
    if text is None:
        return None
    try:
        parse_toml(text)
    except ValueError as exc:  # tomllib.TOMLDecodeError is a ValueError
        return str(exc)
    return None


def table(data: object, *keys: str) -> dict[str, object]:
    """data[k1][k2]... as a dict, or {} when any step is missing or not a table."""
    node = data
    for key in keys:
        if not isinstance(node, dict):
            return {}
        node = node.get(key)
    return node if isinstance(node, dict) else {}


def sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def today() -> str:
    """The local calendar date (the machine's local timezone), as YYYY-MM-DD."""
    return dt.datetime.now(dt.UTC).astimezone().date().isoformat()


def plural(count: int, noun: str) -> str:
    return f"{count} {noun}{'' if count == 1 else 's'}"


def rel_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


# ---------------------------------------------------------------------------------------------
# repo facts shared by preflight, probe and render


def project_name(root: Path) -> str:
    name = table(load_toml(root / "pyproject.toml"), "project").get("name")
    return name if isinstance(name, str) and name else root.name


def console_scripts(root: Path) -> dict[str, str]:
    scripts = table(load_toml(root / "pyproject.toml"), "project", "scripts")
    return {k: v for k, v in scripts.items() if isinstance(v, str)}


def has_commits(root: Path) -> bool:
    return git_out(root, "rev-parse", "-q", "--verify", "HEAD^{commit}") is not None


def is_git_root(root: Path) -> bool:
    return (root / ".git").exists()


def origin_url(root: Path) -> str | None:
    if not is_git_root(root):
        return None
    return git_out(root, "remote", "get-url", "origin") or None


def configured_origin(root: Path) -> str | None:
    """origin's URL as configured, before any url.<base>.insteadOf rewrite: what .project.toml
    records (`git remote get-url` prints the rewritten URL)."""
    if not is_git_root(root):
        return None
    return git_out(root, "config", "--get", "remote.origin.url") or origin_url(root)


def detect_default_branch(root: Path, manifest: dict[str, object] | None = None) -> str:
    """The manifest's, else origin/HEAD, else a conventional local branch, else the current
    branch unless it is a lane branch, else main."""
    value = (manifest or {}).get("default_branch")
    if isinstance(value, str) and value:
        return value
    if not is_git_root(root):
        return "main"
    head = git_out(root, "symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD")
    if head and head.startswith("origin/"):
        return head.removeprefix("origin/")
    for candidate in ("main", "master", "trunk", "develop"):
        if git(root, "show-ref", "-q", "--verify", f"refs/heads/{candidate}").code == 0:
            return candidate
    current = git_out(root, "symbolic-ref", "-q", "--short", "HEAD")
    lanes = ("plan/", "feat/", "fix/", "chg/", "chore/", "refactor/", "release/")
    if current and not current.startswith(lanes):
        return current
    return "main"


def _squash(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def identity_keys(name: str, email: str) -> set[str]:
    """What ties two author lines to one person: the email, the name (case and spacing
    folded), and a GitHub login, from a noreply address or from the name itself (one word, or
    two or three words run together in any order: 'John Doe' ~ 'DoeJohn')."""
    keys: set[str] = set()
    email = email.strip().lower()
    words = name.split()
    if email:
        keys.add("e:" + email)
    if words:
        keys.add("n:" + " ".join(w.lower() for w in words))
    login = NOREPLY_LOGIN.match(email)
    if login and _squash(login.group(1)):
        keys.add("l:" + _squash(login.group(1)))
    if 1 <= len(words) <= 3:
        for order in itertools.permutations(words):
            if _squash("".join(order)):
                keys.add("l:" + _squash("".join(order)))
    return keys


WEB_FLOW = "noreply@github.com"  # the committer of a commit made in GitHub's web UI
PR_MERGE = re.compile(r"\(#\d+\)\s*$|^Merge pull request #\d+")
WEB_UPLOAD = re.compile(r"^Add files via upload\b")
WEB_SAME_TIME = 60  # seconds: a web-UI commit is authored and committed at once


@dataclass
class Author:
    shown: str  # 'Name <email>' of the newest identity
    keys: set[str]
    commits: int = 0  # made with git, or a pull request GitHub merged
    web: int = 0  # made in GitHub's web UI and merging no pull request: an upload or a web edit
    uploads: int = 0  # of those, GitHub's "Add files via upload"


def author_census(root: Path) -> tuple[list[Author], int]:
    """(the people who authored the last 6 months, newest identity first; the bot commits).
    One person under several emails or spellings is one Author. A commit GitHub's web UI made
    counts apart: it shows write access, not work done with git (D9; helios's 3 uploads by a
    second account). Its committer is noreply@github.com and it was authored when committed.
    A pull request GitHub merged is work: a squash or merge commit names its number, and a
    rebased commit keeps the author date of the commit its author made with git."""
    if not is_git_root(root) or not has_commits(root):
        return [], 0
    fmt = "--format=%aN%x1f%aE%x1f%cE%x1f%at%x1f%ct%x1f%s"
    out = git_out(root, "log", "--since=6.months.ago", fmt, "HEAD") or ""
    people: list[Author] = []
    bots = 0
    for line in out.splitlines():
        name, email, committer, authored, committed, subject = [
            *line.split("\x1f", 5),
            *[""] * 5,
        ][:6]
        if not line.strip():
            continue
        if BOT.search(name) or BOT.search(email.strip()):
            bots += 1
            continue
        keys = identity_keys(name, email)
        hits = [p for p in people if p.keys & keys]
        if hits:
            person = hits[0]
            for other in hits[1:]:  # this line bridges people seen apart so far: one person
                person.keys.update(other.keys)
                person.commits += other.commits
                person.web += other.web
                person.uploads += other.uploads
                people.remove(other)
            person.keys.update(keys)
        else:
            person = Author(f"{name.strip()} <{email.strip()}>", keys)
            people.append(person)
        at_once = (
            authored.strip().isdigit()
            and committed.strip().isdigit()
            and abs(int(authored) - int(committed)) <= WEB_SAME_TIME
        )
        web_ui = committer.strip().lower() == WEB_FLOW and at_once
        if web_ui and not PR_MERGE.search(subject.strip()):
            person.web += 1
            person.uploads += bool(WEB_UPLOAD.match(subject.strip()))
        else:
            person.commits += 1
    return people, bots


def human_authors(root: Path) -> list[str]:
    """Distinct human authors of the last 6 months, as 'Name <email>', newest identity first:
    the people with a commit of their own (author_census). Bots, and people whose only commits
    were made in GitHub's web UI, do not count (D9)."""
    people, _ = author_census(root)
    return [p.shown for p in people if p.commits]


def web_only_why(person: Author) -> str:
    """Why a person with web-UI commits only is not counted, for preflight's authors line."""
    edits = person.web - person.uploads
    parts = [plural(person.uploads, "GitHub web upload")] if person.uploads else []
    parts += [plural(edits, "GitHub web edit")] if edits else []
    return ", ".join(parts) + ", no git commit"


@dataclass
class EnvRead:
    name: str
    kind: str  # knob | secret
    type: str  # str | int | float | bool
    required: bool
    default: str | None
    where: list[str] = field(default_factory=list)
    # set on a row carried over from the project's own files (its .env.example, compose, a
    # Makefile) that the code scan does not see: the row's note, in place of `read in <files>`
    source: str = ""


SKIP_DIRS = frozenset(
    {"node_modules", "__pycache__", "venv", "site-packages", "build", "dist", "tests", "test"}
)
TOOL_OWNED = frozenset({"scripts/project.py", "tests/conftest.py"})


def iter_py_files(root: Path) -> list[Path]:
    """The app's Python files: no hidden or vendored folders, no tests, no tool-owned copies."""
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith(".") and d not in SKIP_DIRS)
        for name in sorted(filenames):
            if not name.endswith(".py") or name == "conftest.py":
                continue
            if name.startswith("test_") or name.endswith("_test.py"):
                continue
            path = Path(dirpath) / name
            if rel_posix(path, root) in TOOL_OWNED:
                continue
            found.append(path)
    return found


def _is_environ(node: ast.AST) -> bool:
    """os.environ or a bare `environ`, also as a side of `env if env is not None else
    os.environ` or `env or os.environ`: a function that takes a mapping for its tests."""
    if isinstance(node, ast.IfExp):
        return _is_environ(node.body) or _is_environ(node.orelse)
    if isinstance(node, ast.BoolOp):
        return any(_is_environ(value) for value in node.values)
    if isinstance(node, ast.Attribute):
        return node.attr == "environ" and isinstance(node.value, ast.Name) and node.value.id == "os"
    return isinstance(node, ast.Name) and node.id == "environ"


def _const_str(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str | int | float | bool):
        return str(node.value)
    return None


def module_constants(tree: ast.Module) -> dict[str, tuple[str, int]]:
    """NAME -> (its string, line) for each `NAME = "text"` at a module's top level: the names an
    env read may use for its key (`HOST_ENV = "ORCA_MCP_HOST"`, then `os.environ.get(HOST_ENV)`)."""
    found: dict[str, tuple[str, int]] = {}
    for stmt in tree.body:
        target: ast.AST | None = None
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            target = stmt.targets[0]
        elif isinstance(stmt, ast.AnnAssign):
            target = stmt.target
        value = stmt.value if isinstance(stmt, ast.Assign | ast.AnnAssign) else None
        text = value.value if isinstance(value, ast.Constant) else None
        if isinstance(target, ast.Name) and isinstance(text, str):
            found[target.id] = (text, stmt.lineno)
    return found


def module_literals(tree: ast.Module) -> dict[str, str]:
    """NAME -> its value as the contract writes a default, for each `NAME = <str, number or
    bool>` at a module's top level: what an empty env read may fall back to (DEFAULT_PORT)."""
    found: dict[str, str] = {}
    for stmt in tree.body:
        target: ast.AST | None = None
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            target = stmt.targets[0]
        elif isinstance(stmt, ast.AnnAssign):
            target = stmt.target
        value = stmt.value if isinstance(stmt, ast.Assign | ast.AnnAssign) else None
        text = _settings_value(value) if isinstance(value, ast.Constant) else None
        if isinstance(target, ast.Name) and text is not None:
            found[target.id] = text
    return found


STR_METHODS = frozenset({"strip", "lstrip", "rstrip", "lower", "upper"})


def fallback_default(
    node: ast.Call, parents: dict[ast.AST, ast.AST], literals: dict[str, str]
) -> str | None:
    """The default an env read with an empty default ("" or none) really has: the literal or
    module constant it falls back to. `os.environ.get(NAME, "") or DEFAULT` (a .strip() or
    .lower() of the read too), or the same through one variable of the function: `value = <the
    read>`, then `value or DEFAULT`, or `if not value: return DEFAULT` (orca's ORCA_MCP_*).
    None when the code shows no one fallback."""

    def constant(value: ast.AST | None) -> str | None:
        if isinstance(value, ast.Name):
            return literals.get(value.id)
        return _settings_value(value) if isinstance(value, ast.Constant) else None

    def names(value: ast.AST, variable: str) -> bool:
        return isinstance(value, ast.Name) and value.id == variable

    expr: ast.AST = node
    parent = parents.get(expr)
    while (  # the read's .strip(), .lower() ...
        isinstance(parent, ast.Attribute)
        and parent.attr in STR_METHODS
        and isinstance(call := parents.get(parent), ast.Call)
        and call.func is parent
    ):
        expr, parent = call, parents.get(call)
    if isinstance(parent, ast.BoolOp) and isinstance(parent.op, ast.Or):
        return constant(parent.values[1]) if parent.values[0] is expr else None
    target = parent.targets[0] if isinstance(parent, ast.Assign) else None
    target = parent.target if isinstance(parent, ast.AnnAssign) else target
    if not isinstance(target, ast.Name) or getattr(parent, "value", None) is not expr:
        return None
    scope = parents.get(parent)
    while scope is not None and not isinstance(scope, ast.FunctionDef | ast.AsyncFunctionDef):
        scope = parents.get(scope)
    found: set[str | None] = set()
    for inner in ast.walk(scope) if scope is not None else ():
        if isinstance(inner, ast.BoolOp) and isinstance(inner.op, ast.Or):
            if names(inner.values[0], target.id):
                found.add(constant(inner.values[1]))
        elif (
            isinstance(inner, ast.If)
            and isinstance(inner.test, ast.UnaryOp)
            and isinstance(inner.test.op, ast.Not)
            and names(inner.test.operand, target.id)
            and isinstance(inner.body[0], ast.Return)
        ):
            found.add(constant(inner.body[0].value))
    return found.pop() if len(found) == 1 else None


# how an env read names its variable: (the name, the file:line that spells it out when that is
# another module's constant, else None), or None when the key is not known without running code
KeyOf = Callable[[ast.AST], tuple[str, str | None] | None]


def _literal_key(node: ast.AST) -> tuple[str, str | None] | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value, None
    return None


EnvHit = tuple[str, str | None, bool, str | None]  # name, default, required, spelled out at


def _env_hit(node: ast.AST, key_of: KeyOf = _literal_key) -> EnvHit | None:
    """(name, default, required, where another module spells the name out) when node reads one
    environment variable by a literal name, or by a module constant key_of resolves."""
    if isinstance(node, ast.Call):
        func = node.func
        getter = (
            isinstance(func, ast.Attribute)
            and func.attr in ("get", "pop", "setdefault")
            and _is_environ(func.value)
        )
        getenv = (
            isinstance(func, ast.Attribute)
            and func.attr == "getenv"
            and isinstance(func.value, ast.Name)
            and func.value.id == "os"
        ) or (isinstance(func, ast.Name) and func.id == "getenv")
        if not (getter or getenv) or not node.args:
            return None
        key = key_of(node.args[0])
        if key is None:
            return None
        default = _const_str(node.args[1]) if len(node.args) > 1 else None
        for keyword in node.keywords:
            if keyword.arg == "default":
                default = _const_str(keyword.value)
        return key[0], default, False, key[1]
    if isinstance(node, ast.Subscript) and _is_environ(node.value):
        key = key_of(node.slice)
        if key is not None:
            return key[0], None, isinstance(node.ctx, ast.Load), key[1]
    return None


def _dotted_tail(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        return _dotted_tail(node.value)
    return ""


def _settings_prefix(cls: ast.ClassDef) -> str:
    """env_prefix of a pydantic-settings class: `model_config = SettingsConfigDict(env_prefix=
    ...)` (or a dict), or the v1 `class Config: env_prefix = ...`."""
    for stmt in cls.body:
        value: ast.AST | None = None
        if isinstance(stmt, ast.Assign | ast.AnnAssign):
            targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
            if any(_dotted_tail(target) == "model_config" for target in targets):
                value = stmt.value
        elif isinstance(stmt, ast.ClassDef) and stmt.name == "Config":
            for inner in stmt.body:
                if isinstance(inner, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "env_prefix" for t in inner.targets
                ):
                    return _const_str(inner.value) or ""
        if isinstance(value, ast.Call):
            for keyword in value.keywords:
                if keyword.arg == "env_prefix":
                    return _const_str(keyword.value) or ""
        if isinstance(value, ast.Dict):
            for key, item in zip(value.keys, value.values, strict=True):
                if _const_str(key) == "env_prefix":
                    return _const_str(item) or ""
    return ""


def _settings_type(node: ast.AST) -> str | None:
    """int, float, bool or str for a field annotation (`float | None` is float); None for a
    ClassVar, which is no field."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        sides = [
            s
            for s in (node.left, node.right)
            if _dotted_tail(s) != "None" and not (isinstance(s, ast.Constant) and s.value is None)
        ]
        return _settings_type(sides[0]) if len(sides) == 1 else "str"
    if isinstance(node, ast.Constant) and node.value is None:
        return "str"
    tail = _dotted_tail(node)
    if tail == "ClassVar":
        return None
    if tail == "Optional" and isinstance(node, ast.Subscript):
        return _settings_type(node.slice)
    return tail if tail in ("int", "float", "bool", "str") else "str"


def _settings_default(value: ast.AST | None) -> tuple[str | None, str | None, bool]:
    """(default, alias, required) of a field: `= 15`, `= Field(15, alias="X")`, or none."""
    if value is None:
        return None, None, True
    if isinstance(value, ast.Call) and _dotted_tail(value.func) == "Field":
        alias = None
        default: ast.AST | None = value.args[0] if value.args else None
        factory = False
        for keyword in value.keywords:
            if keyword.arg == "default":
                default = keyword.value
            elif keyword.arg in ("alias", "validation_alias"):
                alias = _const_str(keyword.value) or alias
            elif keyword.arg == "default_factory":
                factory = True
        if default is None or (isinstance(default, ast.Constant) and default.value is Ellipsis):
            return None, alias, not factory
        return _settings_value(default), alias, False
    return _settings_value(value), None, False


def _settings_value(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, bool):
        return str(node.value).lower()
    return _const_str(node)


def settings_reads(tree: ast.AST) -> list[tuple[str, str | None, bool, str, int]]:
    """(env name, default, required, type, line) of each field of a pydantic-settings class
    (a base named ...BaseSettings): the knobs S-1 of the tech stack reads that way. The name is
    env_prefix + the field, upper case (pydantic-settings matches case-insensitively), or the
    field's alias."""
    found: list[tuple[str, str | None, bool, str, int]] = []
    for cls in ast.walk(tree):
        if not isinstance(cls, ast.ClassDef):
            continue
        if not any(_dotted_tail(base).endswith("BaseSettings") for base in cls.bases):
            continue
        prefix = _settings_prefix(cls)
        for stmt in cls.body:
            if not isinstance(stmt, ast.AnnAssign) or not isinstance(stmt.target, ast.Name):
                continue
            field_name = stmt.target.id
            if field_name.startswith("_") or field_name == "model_config":
                continue
            type_ = _settings_type(stmt.annotation)
            if type_ is None:
                continue
            default, alias, required = _settings_default(stmt.value)
            name = (alias or f"{prefix}{field_name}").upper()
            found.append((name, default, required, type_, stmt.lineno))
    return found


def is_os_env(name: str) -> bool:
    return name in OS_ENV or name.startswith(OS_ENV_PREFIXES)


def env_kind(name: str, type_: str) -> str:
    """secret: the name says it holds one and the code reads it as text. A read through int(),
    float() or bool() is a number or a switch (LLM_STREAM_TOKEN_TIMEOUT_S), and a name ending
    in a unit or a pointer (_TIMEOUT, _FILE, _HEADER) names a setting about a secret."""
    upper = name.upper()
    if type_ != "str" or KNOB_TAIL.search(upper):
        return "knob"
    return "secret" if SECRET_NAME.search(upper) else "knob"


def env_reads(root: Path) -> list[EnvRead]:
    return env_scan(root)[0]


UPPER_ENV = re.compile(r"[A-Z_][A-Z0-9_]*")  # what a constant must hold to count as a key


def imported_names(tree: ast.Module) -> dict[str, str]:
    """alias -> the name it imports, for each `from x import NAME [as alias]` of a module."""
    names: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names[alias.asname or alias.name] = alias.name
    return names


def constant_keys(
    tree: ast.Module,
    own: dict[str, tuple[str, int]],
    everywhere: dict[str, set[tuple[str, str]]],
) -> KeyOf:
    """key_of for one module: a literal, a constant of its own, or another module's constant,
    imported by name or read as `config.NAME`, when every module that defines that name gives
    it the same upper-case text. The latter also returns where the text is spelled out."""
    imported = imported_names(tree)

    def key_of(node: ast.AST) -> tuple[str, str | None] | None:
        literal = _literal_key(node)
        if literal is not None:
            return literal
        const = ""
        if isinstance(node, ast.Name):
            if node.id in own:
                text = own[node.id][0]
                return (text, None) if UPPER_ENV.fullmatch(text) else None
            const = imported.get(node.id, "")
        elif isinstance(node, ast.Attribute):
            const = node.attr
        spelled = everywhere.get(const, set())
        if not const or len({text for text, _ in spelled}) != 1:
            return None
        text, where = min(spelled)
        return (text, where) if UPPER_ENV.fullmatch(text) else None

    return key_of


def env_scan(root: Path) -> tuple[list[EnvRead], list[str]]:
    """(the app's env reads, the OS variables it reads) by a literal name (os.environ,
    os.getenv), by a module constant that holds the name (`HOST_ENV = "ORCA_MCP_HOST"`, in the
    same module or imported from another), or as a pydantic-settings field, from an AST scan:
    nothing is imported or run. A secret's default is masked: it would otherwise reach the
    preflight output and the session transcript."""
    trees: list[tuple[Path, ast.Module]] = []
    for path in iter_py_files(root):
        try:
            if path.stat().st_size > 1_000_000:
                continue
            trees.append((path, ast.parse(path.read_text(encoding="utf-8", errors="replace"))))
        except (OSError, SyntaxError, ValueError):
            continue
    constants = {path: module_constants(tree) for path, tree in trees}
    # a constant another module imports resolves when every module that defines the name agrees
    everywhere: dict[str, set[tuple[str, str]]] = {}
    for path, names in constants.items():
        for const, (text, line) in names.items():
            everywhere.setdefault(const, set()).add((text, f"{rel_posix(path, root)}:{line}"))

    found: dict[str, EnvRead] = {}
    os_names: set[str] = set()
    for path, tree in trees:
        key_of = constant_keys(tree, constants[path], everywhere)
        parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
        literals = module_literals(tree)
        hits: list[tuple[str, str | None, bool, str, str]] = []
        here = rel_posix(path, root)
        for node in ast.walk(tree):
            hit = _env_hit(node, key_of)
            if hit is None:
                continue
            name, default, required, spelled_at = hit
            if not default and isinstance(node, ast.Call):  # "" or none: what it falls back to
                default = fallback_default(node, parents, literals) or default
            parent = parents.get(node)
            kind_of = "str"
            if (
                isinstance(parent, ast.Call)
                and isinstance(parent.func, ast.Name)
                and parent.func.id in ("int", "float", "bool")
                and parent.args
                and parent.args[0] is node
            ):
                kind_of = parent.func.id
            # the notes name a file that spells the variable out: doctor greps that file for
            # it, and a read through an imported constant names only the constant
            where = spelled_at or f"{here}:{getattr(node, 'lineno', 0)}"
            hits.append((name, default, required, kind_of, where))
        for name, default, required, kind_of, lineno in settings_reads(tree):
            hits.append((name, default, required, kind_of, f"{here}:{lineno}"))
        for name, default, required, kind_of, where in hits:
            if not ENV_NAME.fullmatch(name):
                continue
            if is_os_env(name):
                os_names.add(name)
                continue
            read = found.get(name)
            if read is None:
                found[name] = EnvRead(name, "knob", kind_of, required, default, [where])
                continue
            read.where.append(where)
            read.required = read.required or required
            read.default = read.default if read.default is not None else default
            read.type = read.type if read.type != "str" else kind_of
    for read in found.values():
        read.kind = env_kind(read.name, read.type)
        if read.kind == "secret" and read.default is not None:
            read.default = MASKED
    return [found[k] for k in sorted(found)], sorted(os_names)


def one_line(value: str) -> str:
    """A value safe inside one commented line: control characters escaped."""
    if not CONTROL.search(value):
        return value
    return value.encode("unicode_escape").decode("ascii")


ENV_CONTRACT_ROW = re.compile(r"^#\s*([A-Za-z_][A-Za-z0-9_]*)\s*\|")  # as project.py reads it


def contract_blocks(text: str) -> dict[str, list[str]]:
    """The rows of an .env.example contract, by name, as written: the `# NAME | kind | ...`
    row and the `#NAME=` or `NAME=` lines right after it. The header row is no row."""
    blocks: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        match = ENV_CONTRACT_ROW.match(line)
        if match and match.group(1) != "NAME":
            current = match.group(1)
            blocks.setdefault(current, []).append(line)
            continue
        if current and re.match(rf"^#?\s*{re.escape(current)}=", line):
            blocks[current].append(line)
            continue
        current = None
    return blocks


PLAIN_ENV_LINE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")
COMPOSE_FILES = ("docker-compose*.y*ml", "compose*.y*ml")
# ${NAME}, ${NAME:-x}, ${NAME?err} or $NAME: compose reads it from the shell or .env ($$ escapes)
COMPOSE_VAR = re.compile(r"(?<!\$)\$(?:\{([A-Z_][A-Z0-9_]*)(?:[:?+-][^}]*)?\}|([A-Z_][A-Z0-9_]*))")
MAKE_OPTIONAL = re.compile(r"^([A-Z_][A-Z0-9_]*)\s*\?=")  # NAME ?= x: taken from the env when set
MAKE_SET = re.compile(r"^(?:override\s+|export\s+)?([A-Z_][A-Z0-9_]*)\s*(?::{1,3}|\+|!)?=")
MAKE_SHELL_VAR = re.compile(r"\$\$\{?([A-Z_][A-Z0-9_]*)")  # $${NAME} or $$NAME in a recipe
MAKE_BUILTINS = frozenset(
    {"MAKE", "MAKEFLAGS", "MAKECMDGOALS", "MAKEFILE_LIST", "CURDIR", "MAKELEVEL"}
)
MAKEFILES = ("GNUmakefile", "makefile", "Makefile")


def plain_env_keys(text: str) -> list[str]:
    """The names a plain .env.example sets (`NAME=value`, `export NAME=value`), in order. The
    `#NAME=` lines of a typed contract are comments, never counted."""
    names: list[str] = []
    for line in text.splitlines():
        match = PLAIN_ENV_LINE.match(line)
        if match and not line.lstrip().startswith("#") and match.group(1) not in names:
            names.append(match.group(1))
    return names


def compose_env_keys(root: Path) -> dict[str, list[str]]:
    """name -> the compose files (root and first-level folders) that interpolate it."""
    found: dict[str, list[str]] = {}
    for base in manifest_dirs(root):
        for pattern in COMPOSE_FILES:
            for path in sorted(base.glob(pattern)):
                if not path.is_file() or path.is_symlink():
                    continue
                rel = rel_posix(path, root)
                for line in (read_text(path) or "").splitlines():
                    if line.lstrip().startswith("#"):
                        continue
                    for braced, bare in COMPOSE_VAR.findall(line):
                        name = braced or bare
                        if rel not in found.setdefault(name, []):
                            found[name].append(rel)
    return found


def make_env_keys(root: Path) -> dict[str, list[str]]:
    """name -> the Makefiles that take it from the environment: `NAME ?= x`, or $${NAME} in a
    recipe. A name the Makefile sets itself (=, :=, +=) is Make's own, never the env's."""
    found: dict[str, list[str]] = {}
    for base in manifest_dirs(root):
        for name in MAKEFILES:
            path = base / name
            if not path.is_file() or path.is_symlink():
                continue
            text = read_text(path) or ""
            rel = rel_posix(path, root)
            lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith("#")]
            own = {
                m.group(1)
                for ln in lines
                if (m := MAKE_SET.match(ln)) and not MAKE_OPTIONAL.match(ln)
            }
            names = [m.group(1) for ln in lines if (m := MAKE_OPTIONAL.match(ln))]
            names += [n for ln in lines if ln.startswith("\t") for n in MAKE_SHELL_VAR.findall(ln)]
            for key in names:
                if key in own or key in MAKE_BUILTINS:
                    continue
                if rel not in found.setdefault(key, []):
                    found[key].append(rel)
    return found


def carried_env(root: Path, current: str | None, known: set[str]) -> list[EnvRead]:
    """Rows for the variables the project's own files name and the code scan does not see:
    the project's .env.example (its plain NAME=value lines), compose interpolation and the
    Makefile's environment. Adoption never drops one. Each is not required, of type str, with
    no default and a blank value (a value in the old file may be a real secret); a name that
    says it holds a secret is a secret row (an op:// pointer), any other a knob."""
    notes: dict[str, list[str]] = {}
    for name in plain_env_keys(current or ""):
        notes.setdefault(name, []).append("carried over from the project's .env.example")
    named: dict[str, list[str]] = {}
    for source in (compose_env_keys(root), make_env_keys(root)):
        for name, files in source.items():
            named.setdefault(name, []).extend(f for f in files if f not in named.get(name, []))
    for name, files in named.items():
        notes.setdefault(name, []).append("named in " + ", ".join(files[:3]))
    rows: list[EnvRead] = []
    for name in sorted(notes):
        if name in known or is_os_env(name) or not ENV_NAME.fullmatch(name):
            continue
        rows.append(
            EnvRead(name, env_kind(name, "str"), "str", False, None, source="; ".join(notes[name]))
        )
    return rows


def env_contract_rows(root: Path, reads: list[EnvRead], current: str | None) -> str:
    """{ENV_ROWS} for .env.example: the rows the file holds, as the project wrote them (a
    typed contract is edited by hand: a type, a range, a note), then a derived row for each
    read that has none, then a row for each variable the project's own files name that has
    none (carried_env). A row stays when the scan no longer sees its read (a knob read through
    a path the AST scan does not follow): render never deletes a contract row."""
    have = contract_blocks(current or "")
    fresh = [read for read in reads if read.name not in have]
    carried = carried_env(root, current, {*have, *(read.name for read in reads)})
    if not have:
        return env_rows([*reads, *carried])
    lines = [line for block in have.values() for line in block]
    if fresh or carried:
        lines += env_rows([*fresh, *carried]).splitlines()
    return "\n".join(lines)


def env_rows(reads: list[EnvRead]) -> str:
    """The typed env contract rows (.env.example): knobs commented out, secrets as op://. A
    row's `required` comes from the code: no default and no Optional (`str | None = None`
    is not required), for a secret as for a knob."""
    if not reads:
        return "# (none: the code reads no environment variable)"
    lines: list[str] = []
    for read in reads:
        # files, not lines: a line number goes stale at the first edit above it. doctor warns
        # when a named file no longer names the variable (a read moved to config.py)
        files = list(dict.fromkeys(w.rsplit(":", 1)[0] for w in read.where))
        where = read.source or "read in " + ", ".join(files[:3])
        required = "yes" if read.required and read.default is None else "no"
        if read.kind == "secret":
            lines.append(f"# {read.name} | secret | str | {required} | - | op:// pointer; {where}")
            lines.append(f"#{read.name}=op://<vault>/<item>/<field>")
            continue
        default = one_line(read.default) if read.default is not None else None
        shown = "-" if default is None else (default or '""')
        lines.append(f"# {read.name} | knob | {read.type} | {required} | {shown} | {where}")
        lines.append(f"#{read.name}={default or ''}")
    return "\n".join(lines)


def _req_name(requirement: str) -> str | None:
    match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", requirement)
    return re.sub(r"[._]+", "-", match.group(1)).lower() if match else None


def _py_deps(data: dict[str, object]) -> set[str]:
    reqs: list[object] = []
    project = table(data, "project")
    deps = project.get("dependencies")
    reqs += deps if isinstance(deps, list) else []
    for group in table(project, "optional-dependencies").values():
        reqs += group if isinstance(group, list) else []
    for group in table(data, "dependency-groups").values():
        reqs += group if isinstance(group, list) else []
    dev = table(data, "tool", "uv").get("dev-dependencies")
    reqs += dev if isinstance(dev, list) else []
    names = {_req_name(r) for r in reqs if isinstance(r, str)}
    poetry = table(data, "tool", "poetry")
    for key in ("dependencies", "dev-dependencies"):
        names |= {_req_name(k) for k in table(poetry, key)}
    return {n for n in names if n}


def _dep_signal(dep: str) -> str | None:
    if dep in ("fastapi", "flask", "django", "litestar"):
        return "api"
    if dep in ("sqlalchemy", "asyncpg", "redis") or dep.startswith("psycopg"):
        return "db"
    if dep in ("react", "svelte", "next"):
        return "ui"
    if dep in ("dagster", "prefect", "airflow", "dbt") or dep.startswith(
        ("apache-airflow", "dbt-")
    ):
        return "pipeline"
    return None


def manifest_dirs(root: Path) -> list[Path]:
    """The root and its first-level folders (monorepos keep manifests in backend/, web/)."""
    dirs = [root]
    try:
        children = sorted(root.iterdir())
    except OSError:
        return dirs
    for child in children:
        if child.is_dir() and not child.name.startswith(".") and child.name not in SKIP_DIRS:
            dirs.append(child)
    return dirs


def detect_signals(root: Path) -> dict[str, list[str]]:
    """Signals from parsed evidence only (H4): manifests, dependency names, marker files. Prose,
    authors and descriptions never count."""
    found: dict[str, list[str]] = {}

    def add(signal: str, evidence: str) -> None:
        if evidence not in found.setdefault(signal, []):
            found[signal].append(evidence)

    for base in manifest_dirs(root):
        prefix = "" if base == root else f"{rel_posix(base, root)}/"
        pyproject = base / "pyproject.toml"
        if pyproject.is_file():
            data = load_toml(pyproject)
            if table(data, "project", "scripts"):
                add("cli", f"{prefix}pyproject.toml [project.scripts]")
            for dep in sorted(_py_deps(data)):
                signal = _dep_signal(dep)
                if signal:
                    add(signal, f"{prefix}pyproject.toml: {dep}")
        for req in sorted(base.glob("requirements*.txt")):
            for line in (read_text(req) or "").splitlines():
                dep = (
                    _req_name(line)
                    if line.strip() and not line.lstrip().startswith(("#", "-"))
                    else None
                )
                signal = _dep_signal(dep) if dep else None
                if signal:
                    add(signal, f"{prefix}{req.name}: {dep}")
        package = base / "package.json"
        if package.is_file():
            try:
                data = json.loads(read_text(package) or "{}")
            except json.JSONDecodeError:
                data = {}
            for key in ("dependencies", "devDependencies"):
                deps = data.get(key) if isinstance(data, dict) else None
                for dep in sorted(deps) if isinstance(deps, dict) else []:
                    signal = _dep_signal(str(dep).lower())
                    if signal:
                        add(signal, f"{prefix}package.json: {dep}")
        for pattern in ("Dockerfile*", "docker-compose*.y*ml", "compose*.y*ml"):
            for hit in sorted(base.glob(pattern)):
                if hit.is_file():
                    add("deploy", f"{prefix}{hit.name}")
        for name in ("fly.toml", "wrangler.toml", "wrangler.json", "wrangler.jsonc"):
            if (base / name).is_file():
                add("deploy", f"{prefix}{name}")
        if (base / "k8s").is_dir():
            add("deploy", f"{prefix}k8s/")
        if (base / "alembic.ini").is_file():
            add("db", f"{prefix}alembic.ini")
        if (base / "migrations").is_dir():
            add("db", f"{prefix}migrations/")
        if (base / "dags").is_dir():
            add("pipeline", f"{prefix}dags/")
    return {s: found[s] for s in SIGNALS if s in found}


def detect_stack(root: Path) -> str:
    def one(base: Path) -> str | None:
        if (base / "pyproject.toml").is_file():
            data = load_toml(base / "pyproject.toml")
            backend = table(data, "build-system").get("build-backend")
            uv = (
                (base / "uv.lock").is_file()
                or bool(table(data, "tool", "uv"))
                or backend == "uv_build"
            )
            return "python/uv" if uv else "python"
        for marker, stack in (
            ("package.json", "node"),
            ("Cargo.toml", "rust"),
            ("go.mod", "go"),
            ("requirements.txt", "python"),
        ):
            if (base / marker).is_file():
                return stack
        return None

    top = one(root)
    if top:
        return top
    subs = [f"{s} ({rel_posix(b, root)}/)" for b in manifest_dirs(root)[1:] if (s := one(b))]
    return ", ".join(subs) if subs else "unknown"


def no_pack(root: Path) -> str:
    """`no stack pack for node`: what P0, P1, prepare and render say about a repo with code
    and no root pyproject.toml (v3 ships the Python pack only)."""
    stack = detect_stack(root)
    if stack == "unknown":
        return "no stack pack (no pyproject.toml, package.json, Cargo.toml or go.mod)"
    return f"no stack pack for {stack}"


PY_VERSION = re.compile(r"^3\.\d+(?:\.\d+)?$")
KNOWN_MINORS = tuple(f"3.{n}" for n in range(8, 16))  # what a requires-python floor is read from
SPEC_CLAUSE = re.compile(r"^\s*(~=|===|==|!=|<=|>=|<|>)\s*(\d+(?:\.\d+)*(?:\.\*)?)\s*$")
CI_PYTHON = re.compile(r"(?m)^[\s-]*python(?:-version)?\s*:\s*(.+)$")
PY_IN_TEXT = re.compile(r"(?<![\d.])(3\.\d+)(?:\.\d+)?(?![\d])")
DOCKER_PYTHON = re.compile(r"(?:^|/)python:(3\.\d+)|:python(3\.\d+)")
UV_DEFAULT = "uv's default"


@dataclass
class PyCandidate:
    version: str | None  # X.Y, or None: the interpreter uv picks by itself
    sources: list[str]


def python_pin(root: Path) -> str | None:
    """The first line of the repo's .python-version, when it has one."""
    lines = (read_text(root / ".python-version") or "").split()
    return lines[0] if lines else None


def requires_python(root: Path) -> str | None:
    value = table(load_toml(root / "pyproject.toml"), "project").get("requires-python")
    return value.strip() if isinstance(value, str) and value.strip() else None


def _vtuple(text: str) -> tuple[int, int, int]:
    parts = [int(p) for p in text.split(".") if p.isdigit()] + [0, 0, 0]
    return parts[0], parts[1], parts[2]


def _clause_ok(op: str, ver: str, v: tuple[int, int, int]) -> bool:
    if ver.endswith(".*"):
        prefix = [int(p) for p in ver[:-2].split(".")]
        same = list(v[: len(prefix)]) == prefix
        return same if op == "==" else not same if op == "!=" else True
    want = _vtuple(ver)
    if op == "~=":
        depth = max(1, len(ver.split(".")) - 1)
        return v >= want and v[:depth] == want[:depth]
    return {
        "==": v == want,
        "===": v == want,
        "!=": v != want,
        "<=": v <= want,
        ">=": v >= want,
        "<": v < want,
        ">": v > want,
    }[op]


def spec_allows(spec: str | None, minor: str) -> bool:
    """True when some release of the minor version (3.12 -> 3.12.0 ... 3.12.39) meets the
    requires-python spec: the PEP 440 comparison operators, == and != with .*, and ~=. A spec
    this cannot read allows every version: uv judges it when it syncs."""
    if not spec:
        return True
    clauses: list[tuple[str, str]] = []
    for part in spec.split(","):
        match = SPEC_CLAUSE.match(part)
        if not match:
            return True
        clauses.append((match.group(1), match.group(2)))
    major, minor_n, _ = _vtuple(minor)
    return any(
        all(_clause_ok(op, ver, (major, minor_n, patch)) for op, ver in clauses)
        for patch in range(40)
    )


def python_evidence(root: Path) -> dict[str, list[str]]:
    """X.Y -> the files that name it as the Python they run: Dockerfiles (`FROM python:3.12`,
    `uv:python3.12`) in the root and first-level folders, then the CI workflows
    (`python-version: "3.12"` or a list of them). Dockerfiles first: they are what ships."""
    found: dict[str, list[str]] = {}

    def add(version: str, source: str) -> None:
        if source not in found.setdefault(version, []):
            found[version].append(source)

    for base in manifest_dirs(root):
        prefix = "" if base == root else f"{rel_posix(base, root)}/"
        for docker in sorted(base.glob("Dockerfile*")):
            for line in (read_text(docker) or "").splitlines():
                words = [w for w in line.split() if not w.startswith("--")]
                if len(words) > 1 and words[0].upper() == "FROM":
                    match = DOCKER_PYTHON.search(words[1])
                    if match:
                        add(match.group(1) or match.group(2), f"{prefix}{docker.name}")
    workflows = root / ".github" / "workflows"
    for flow in sorted(workflows.glob("*.y*ml")) if workflows.is_dir() else []:
        for value in CI_PYTHON.findall(read_text(flow) or ""):
            for version in PY_IN_TEXT.findall(value.split("#", 1)[0]):
                add(version, f".github/workflows/{flow.name}")
    return found


def python_candidates(root: Path) -> list[PyCandidate]:
    """The Python versions P1 and P4 try, in order, on a repo with no .python-version: those
    the repo's Dockerfiles and CI run, then the requires-python floor, then uv's default. Each
    must meet requires-python. With a pin, uv honours it: one candidate, None."""
    if python_pin(root):
        return [PyCandidate(None, [".python-version"])]
    spec = requires_python(root)
    out: list[PyCandidate] = []
    for version, sources in python_evidence(root).items():
        if spec_allows(spec, version):
            out.append(PyCandidate(version, sources))
    floor = next((v for v in KNOWN_MINORS if spec and spec_allows(spec, v)), None)
    if floor:
        hit = next((c for c in out if c.version == floor), None)
        if hit:
            hit.sources.append("requires-python floor")
        else:
            out.append(PyCandidate(floor, ["requires-python floor"]))
    out.append(PyCandidate(None, [UV_DEFAULT]))
    return out


def candidates_text(candidates: list[PyCandidate]) -> str:
    return ", ".join(
        (c.version or UV_DEFAULT)
        + (f" ({', '.join(s for s in c.sources if s != UV_DEFAULT)})" if c.version else "")
        for c in candidates
    )


def venv_python(folder: Path) -> str | None:
    """X.Y of the interpreter a synced .venv holds, read from its pyvenv.cfg (never run)."""
    for line in (read_text(folder / ".venv" / "pyvenv.cfg") or "").splitlines():
        key, _, value = line.partition("=")
        if key.strip() in ("version_info", "version"):
            match = re.match(r"\s*(3\.\d+)", value)
            if match:
                return match.group(1)
    return None


def uv_failure(result: Result) -> str:
    """The cause of a failed uv run, not its last line (`hint: Build failures usually ...`):
    the first `×` or `error:` line, plus uv's `... was included because ...` hint."""
    lines = [ln.strip() for ln in (result.err or result.out).splitlines() if ln.strip()]
    cause = next((ln for ln in lines if ln.startswith(("\u00d7", "error:"))), None)
    why = next((ln for ln in lines if "was included because" in ln), None)
    text = "; ".join(p for p in (cause, why) if p)
    return one_line(text or (lines[-1] if lines else f"exit {result.code}"))[:300]


def sync_with_python(
    clone: Path, candidates: list[PyCandidate], env: dict[str, str], cwd: Path
) -> tuple[str | None, list[str]]:
    """`uv sync` of a scratch clone with each candidate in turn, a fresh .venv each time: (the
    X.Y that built, or None; each failure as `<version>: <cause>`). None as a candidate lets
    uv pick (a .python-version, else its default), and the built X.Y is read from the venv."""
    failures: list[str] = []
    for cand in candidates:
        argv = ["uv", "--directory", str(clone), "sync", "-q"]
        argv += ["--python", cand.version] if cand.version else []
        result = run(argv, cwd=cwd, env=env, timeout=900)
        if result.code == 0:
            return cand.version or venv_python(clone) or "", failures
        tried = cand.version or f"{UV_DEFAULT} ({venv_python(clone) or '?'})"
        failures.append(f"{tried}: {uv_failure(result)}")
        shutil.rmtree(clone / ".venv", ignore_errors=True)
    return None, failures


def scenario_ids(root: Path) -> list[str]:
    ids: list[str] = []
    caps = root / "specs" / "capabilities"
    for path in sorted(caps.glob("*.md")) if caps.is_dir() else []:
        for match in re.finditer(
            r"(?m)^###\s+Scenario:\s+([a-z0-9][\w-]*\.[\w.-]+)", read_text(path) or ""
        ):
            ids.append(match.group(1))
    return ids


def distribution(root: Path) -> str | None:
    """The one word under `## Distribution` in specs/tech-stack.md, when it is a known one."""
    text = read_text(root / "specs" / "tech-stack.md") or ""
    match = re.search(r"(?m)^##\s+Distribution\s*$\n((?:.*\n?)*?)(?=^##\s|\Z)", text)
    if not match:
        return None
    for line in match.group(1).splitlines():
        word = line.strip().strip("`*-").strip().split(" ")[0].lower() if line.strip() else ""
        if word and not word.startswith("<!--"):
            return word if word in DISTRIBUTIONS else None
    return None


def mission_one_liner(root: Path) -> str | None:
    """The first line under `## One-liner` in specs/mission.md (P2 settles it), or None while
    it is missing, a template placeholder or a [NEEDS CLARIFICATION] marker. It becomes the
    pyproject description (H6)."""
    text = read_text(root / "specs" / "mission.md") or ""
    match = re.search(r"(?mi)^##\s+One-liner\s*$\n((?:.*\n?)*?)(?=^#{1,6}\s|\Z)", text)
    if not match:
        return None
    for line in match.group(1).splitlines():
        value = line.strip()
        if not value or value.startswith("<!--"):
            continue
        if PLACEHOLDER.search(value) or "[NEEDS CLARIFICATION" in value or CONTROL.search(value):
            return None
        return value
    return None


# ---------------------------------------------------------------------------------------------
# P0 preflight


@dataclass
class Stop:
    id: str
    what: str
    options: list[str]


@dataclass
class Facts:
    repo: str
    name: str
    mode: str
    mode_evidence: list[str]
    has_git: bool
    commits: int
    branch: str | None
    default_branch: str
    origin: str | None
    remotes: dict[str, str]
    dead_remotes: list[str]
    upstream: str | None
    ahead: int
    behind: int
    dirty: list[str]
    untracked_lockfiles: list[str]
    authors: list[str]
    tier: str
    stack: str
    scripts: dict[str, str]
    signals: dict[str, list[str]]
    env_reads: list[EnvRead]
    tools: dict[str, str | None]
    gh: dict[str, str]
    vault: list[str]
    stops: list[Stop]
    notes: list[str]
    tool_pins: list[str] = field(default_factory=list)  # tools the repo's mise.toml pins
    author_commits: dict[str, int] = field(default_factory=dict)  # a counted author's commits
    authors_not_counted: list[str] = field(default_factory=list)  # 'Name <email>: why'
    bot_commits: int = 0
    python: dict[str, object] = field(default_factory=dict)  # pin, requires-python, candidates
    agent_tracked: int = 0  # files a tracked .agent/ holds (D7)


NON_CODE_TOP = frozenset({".git", ".claude", ".agent", ".agents", "specs", ".DS_Store"})
NON_CODE_FILES = re.compile(
    r"^(README|LICENSE|COPYING)(\..*)?$|^\.git(ignore|attributes)$|^\.editorconfig$", re.IGNORECASE
)


def has_code(root: Path) -> bool:
    """Anything beyond docs, git and agent folders. A lone .claude/ never counts (N24)."""
    for child in root.iterdir():
        if child.name in NON_CODE_TOP:
            continue
        if child.is_file() and NON_CODE_FILES.match(child.name):
            continue
        return True
    return False


def legacy_items(root: Path) -> list[str]:
    """The v1 JSON memory layout: its stores under project_memory/ and its two hooks. Only
    there: a root-level sessions/ or pending/ is the project's own code."""
    found: list[str] = []
    for name in LEGACY_NAMES:
        path = root / LEGACY_BASE / name
        if path.exists() or path.is_symlink():
            found.append(f"{LEGACY_BASE}/{name}")
    found += [rel_posix(p, root) for p in sorted(root.glob(LEGACY_HOOKS))]
    return found


def detect_mode(root: Path, git_repo: bool, commits: int) -> tuple[str, list[str]]:
    """First match wins: EXTEND, EXTEND+v2-migrate, MIGRATE, SCAFFOLD, ADOPT."""
    if (root / MANIFEST).is_file():
        return "EXTEND", [MANIFEST]
    for rel in ("project_memory/README.md", "AGENTS.md"):
        if V2_STAMP.search(read_text(root / rel) or ""):
            return "EXTEND+v2-migrate", [rel]
    legacy = legacy_items(root)
    if legacy:
        return "MIGRATE", legacy
    if not has_code(root) and (not git_repo or commits == 0):
        return "SCAFFOLD", []
    return "ADOPT", []


def git_status(root: Path) -> tuple[list[str], list[str]]:
    """(dirty paths, untracked lockfiles). Untracked lockfiles are exempt from the stop (D3)."""
    out = git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all").out
    entries = out.split("\0")
    dirty: list[str] = []
    locks: list[str] = []
    skip = False
    for entry in entries:
        if skip:
            skip = False
            continue
        if len(entry) < 4:
            continue
        code, path = entry[:2], entry[3:]
        if code[0] in "RC":
            skip = True
        if code == "??" and PurePosixPath(path).name in LOCKFILES:
            locks.append(path)
        else:
            dirty.append(path)
    return dirty, locks


def normalize_url(url: str) -> str:
    url = url.strip()
    if not url:
        return ""
    if "://" not in url and ":" in url and not url.startswith(("/", ".", "~")):
        host, _, path = url.partition(":")  # scp form: git@github.com:o/r.git
        url = f"ssh://{host}/{path}"
    if "://" in url:
        scheme_rest = url.split("://", 1)[1]
        host, _, path = scheme_rest.partition("/")
        host = host.rsplit("@", 1)[-1].lower().split(":")[0]
        path = path.rstrip("/").removesuffix(".git")
        return f"{host}/{path}"
    path = url.removeprefix("file://")
    try:
        return str(Path(path).expanduser().resolve())
    except OSError:
        return path


def is_local_url(url: str) -> bool:
    return url.startswith(("/", ".", "~", "file://"))


def url_owner(url: str) -> str | None:
    """host/owner of a hosted remote URL, lowercased (github.com/doejohn); None for a
    local folder."""
    if is_local_url(url):
        return None
    parts = normalize_url(url).lower().split("/")
    return "/".join(parts[:2]) if len(parts) >= 3 else None


def root_commits(repo: Path) -> set[str]:
    return set((git_out(repo, "rev-list", "--max-parents=0", "HEAD") or "").split())


def shared_origin(root: Path, url: str, search_roots: list[Path]) -> dict[str, str]:
    """Other local checkouts (depth 1 and 2 under each search root) that push where this one
    does: path -> "" when their origin URL is the same, or why when it differs only by the
    repo's name while the owner and the root commit are the same. GitHub redirects a renamed
    repo's old URL, so geo-context's GeoContext.git lands in orca. A fork under another
    owner shares the root commit and is not listed."""
    want = normalize_url(url)
    owner = url_owner(url)
    mine = git_out(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    my_roots: set[str] | None = None
    hits: dict[str, str] = {}
    seen: set[str] = set()
    candidates: list[Path] = []
    for base in search_roots:
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            if (child / ".git").exists():
                candidates.append(child)
                continue
            for grand in sorted(child.iterdir()) if os.access(child, os.R_OK) else []:
                if grand.is_dir() and (grand / ".git").exists():
                    candidates.append(grand)
    for other in candidates:
        try:
            resolved = str(other.resolve())
        except OSError:
            continue
        if resolved in seen or resolved == str(root.resolve()):
            continue
        seen.add(resolved)
        common = git_out(other, "rev-parse", "--path-format=absolute", "--git-common-dir")
        if common and mine and Path(common).resolve() == Path(mine).resolve():
            continue  # a worktree of this very repo
        theirs = git_out(other, "config", "--get", "remote.origin.url")
        if not theirs:
            continue
        if normalize_url(theirs) == want:
            hits[resolved] = ""
            continue
        if owner is None or url_owner(theirs) != owner:
            continue
        if my_roots is None:
            my_roots = root_commits(root)
        shared = sorted(my_roots & root_commits(other))
        if shared:
            hits[resolved] = (
                f"origin {public_url(theirs)}, same owner and root commit {shared[0][:7]}: "
                "a renamed repo's old URL, which GitHub redirects here"
            )
    return hits


def origin_root_differs(root: Path) -> bool | None:
    """True when origin's fetched refs share no root commit with HEAD; None when unknown
    (never fetched). P0 never fetches: it writes nothing."""
    refs = (
        git_out(root, "for-each-ref", "--format=%(objectname)", "refs/remotes/origin") or ""
    ).split()
    if not refs:
        return None
    theirs = set((git_out(root, "rev-list", "--max-parents=0", *refs) or "").split())
    mine = set((git_out(root, "rev-list", "--max-parents=0", "HEAD") or "").split())
    if not theirs or not mine:
        return None
    return not (theirs & mine)


def url_repo_name(url: str) -> str:
    """The last path part of a remote URL, lowercased, without .git: origin's repo name."""
    return normalize_url(url).rstrip("/").rsplit("/", 1)[-1].removesuffix(".git").lower()


def origin_owner(root: Path, url: str, others: list[str]) -> str | None:
    """The one checkout origin's repo name points at: str(root) for this one, another
    checkout's path, or None when no single checkout matches. Folder names decide first: a
    fork keeps the project name (helios-demo's pyproject says helios), not the folder name."""
    want = url_repo_name(url)
    checkouts = [str(root), *others]
    for name_of in (lambda c: Path(c).name, lambda c: project_name(Path(c))):
        hits = [c for c in checkouts if want and name_of(c).lower() == want]
        if hits:
            return hits[0] if len(hits) == 1 else None
    return None


def remote_dead(root: Path, url: str) -> bool:
    if is_local_url(url):
        path = Path(url.removeprefix("file://")).expanduser()
        if not path.is_absolute():
            path = root / path
        return not path.exists()
    return git(root, "ls-remote", "-q", "--exit-code", url, "HEAD", timeout=10).code not in (0, 2)


TOOLS = (
    ("mise", ["mise", "--version"]),
    ("uv", ["uv", "--version"]),
    ("git", ["git", "--version"]),
    ("gh", ["gh", "--version"]),
    ("gitleaks", ["gitleaks", "version"]),
    ("git-cliff", ["git-cliff", "--version"]),
)


def mise_pins(root: Path) -> list[str]:
    """The TOOLS names the repo's own mise.toml pins in [tools] (`gitleaks`,
    `aqua:orhun/git-cliff`, ...): read, never run. P0 runs tools from the home folder, where
    such a pin does not apply."""
    tools = table(load_toml(root / "mise.toml"), "tools") if (root / "mise.toml").is_file() else {}
    pins: list[str] = []
    for name, _ in TOOLS:
        if any(key == name or re.search(rf"[:/]{re.escape(name)}$", key) for key in tools):
            pins.append(name)
    return pins


def tool_versions() -> dict[str, str | None]:
    """Each tool checked by running it, never `command -v`: a shim that fails is no tool."""
    versions: dict[str, str | None] = {}
    for name, argv in TOOLS:
        result = run(argv, cwd=Path.home(), timeout=15)
        match = re.search(r"(\d+\.\d+(?:\.\d+)?)", result.out + result.err)
        versions[name] = match.group(1) if result.code == 0 and match else None
    return versions


def github_slug(url: str | None) -> str | None:
    if not url:
        return None
    norm = normalize_url(url)
    if not norm.startswith("github.com/"):
        return None
    slug = norm.removeprefix("github.com/")
    return slug if slug.count("/") == 1 else None


def gh_facts(origin: str | None, offline: bool, runnable: bool) -> dict[str, str]:
    """gh auth, plan and origin visibility. Every gh failure is tolerated and reported."""
    if offline:
        return {"status": "skipped (offline)"}
    if not runnable:
        return {"status": "not runnable"}
    facts: dict[str, str] = {}
    auth = run(["gh", "auth", "status"], timeout=15)
    facts["status"] = "logged in" if auth.code == 0 else "not logged in"
    if auth.code == 0:
        plan = run(["gh", "api", "user", "--jq", ".plan.name"], timeout=15)
        # .plan is null unless the token has the `user` scope; gh's default login lacks it
        known = plan.code == 0 and plan.out.strip()
        facts["plan"] = plan.out.strip().capitalize() if known else "unknown"
        slug = github_slug(origin)
        if slug:
            view = run(
                ["gh", "repo", "view", slug, "--json", "visibility", "--jq", ".visibility"],
                timeout=15,
            )
            facts["visibility"] = view.out.strip().lower() if view.code == 0 else "unknown"
    return facts


def vault_matches(vault: Path, name: str) -> list[str]:
    hits: list[str] = []
    for rel in (f"05-projects/kitchen/{name}", f"05-projects/active/{name}"):
        if (vault / rel).is_dir():
            hits.append(f"{rel}/")
    ideas = vault / "09-ideas"
    if (ideas / f"{name}.md").is_file():
        hits.append(f"09-ideas/{name}.md")
    word = re.compile(rf"(?m)^spawned:.*\b{re.escape(name)}\b")
    for idea in sorted(ideas.glob("*.md")) if ideas.is_dir() else []:
        rel = f"09-ideas/{idea.name}"
        if rel not in hits and word.search(read_text(idea) or ""):
            hits.append(rel)
    return hits


def python_facts(root: Path) -> dict[str, object]:
    """P0's view of the Python pin, for a repo with a root pyproject.toml: the pin, the
    requires-python spec, and with no pin the versions P1 and P4 try in order."""
    if not (root / "pyproject.toml").is_file():
        return {}
    return {
        "pin": python_pin(root),
        "requires": requires_python(root),
        "candidates": [asdict(c) for c in python_candidates(root)],
    }


def preflight(root: Path, offline: bool, vault: Path, search_roots: list[Path]) -> Facts:
    git_repo = is_git_root(root)
    commits = 0
    branch = upstream = origin = None
    remotes: dict[str, str] = {}
    dead: list[str] = []
    ahead = behind = 0
    dirty: list[str] = []
    locks: list[str] = []
    stops: list[Stop] = []
    notes: list[str] = []
    if git_repo:
        count = git_out(root, "rev-list", "--count", "HEAD")
        commits = int(count) if count and count.isdigit() else 0
        branch = git_out(root, "symbolic-ref", "-q", "--short", "HEAD")
        for remote in (git_out(root, "remote") or "").split():
            remotes[remote] = git_out(root, "remote", "get-url", remote) or ""
        origin = remotes.get("origin") or None
        for remote, url in remotes.items():
            if url and (is_local_url(url) or not offline) and remote_dead(root, url):
                dead.append(remote)
        if commits:
            upstream = git_out(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
            if upstream:
                counts = (
                    git_out(root, "rev-list", "--left-right", "--count", "@{u}...HEAD") or "0 0"
                ).split()
                behind, ahead = int(counts[0]), int(counts[1])
            dirty, locks = git_status(root)
    else:
        parent = run(["git", "-C", str(root), "rev-parse", "--show-toplevel"], env=git_env())
        if parent.code == 0:
            stops.append(
                Stop(
                    "nested",
                    f"this folder has no .git but sits inside the repo {parent.out.strip()}: "
                    "uv init and the first commit would land in that repo",
                    [
                        (
                            "Run `git init -b main` here first, then re-run (Recommended: "
                            "the project gets its own history)."
                        ),
                        "Stop, and pick a folder outside every repo.",
                    ],
                )
            )
    mode, evidence = detect_mode(root, git_repo, commits)
    people, bot_commits = author_census(root)
    authors = [p.shown for p in people if p.commits]
    tools = tool_versions()
    code = has_code(root)

    if git_repo and commits and dirty:
        shown = ", ".join(dirty[:5]) + (f" and {len(dirty) - 5} more" if len(dirty) > 5 else "")
        stops.append(
            Stop(
                "dirty",
                f"dirty tree: {shown}",
                [
                    (
                        "Stop so you can commit or stash (Recommended: init stages only its own "
                        "paths, and your edits would ride along on its branch)."
                    ),
                    "Run --plan only.",
                ],
            )
        )
    if ahead and behind:
        stops.append(
            Stop(
                "diverged",
                f"{branch} and {upstream} have diverged: {ahead} ahead, {behind} behind",
                [
                    (
                        "Stop so you can reconcile (Recommended: init branches from the default "
                        "branch as it is)."
                    ),
                    "Run --plan only.",
                ],
            )
        )
    if origin and commits:
        sharing = shared_origin(root, origin, search_roots)
        others = list(sharing)
        shown = ", ".join(f"{p} ({why})" if why else p for p, why in sharing.items())
        differs = origin_root_differs(root)
        owner = origin_owner(root, origin, others) if others else None
        if others and owner == str(root):
            # origin's name is this repo's: the other checkout is the one pointing at the
            # wrong remote (run on helios, helios-demo is the odd one out)
            notes.append(
                "another local repo also uses this origin: "
                + shown
                + "; origin's name matches this repo, so re-point that one"
            )
            others = []
        if differs or others:
            why = []
            if differs:
                why.append("origin's root commit differs from HEAD's")
            if others:
                why.append("another local repo uses the same origin: " + shown)
            if owner and owner != str(root):
                recommended = f"its origin belongs to {Path(owner).name}"
            elif others:
                recommended = (
                    f"origin's name, {url_repo_name(origin)}, matches no single checkout; "
                    "find its owner"
                )
            else:
                recommended = "origin holds another project's history"
            stops.append(
                Stop(
                    "shared-origin",
                    "; ".join(why),
                    [
                        "Treat this as its own repo and re-point origin yourself.",
                        f"Stop (Recommended: {recommended}).",
                    ],
                )
            )
        elif differs is None:
            notes.append("origin's root commit unknown: origin was never fetched")
    if code and (not git_repo or commits == 0):
        stops.append(
            Stop(
                "no-commit",
                "code with no commit" + ("" if git_repo else " and no .git"),
                [
                    (
                        "Run `git init -b main` if needed, make the first commit yourself, then "
                        "re-run (Recommended: you choose what the first commit holds)."
                    ),
                    "Stop.",
                ],
            )
        )
    if git_repo and commits == 0 and origin:
        stops.append(
            Stop(
                "empty-with-origin",
                f"no commits yet, but origin is set ({origin})",
                [
                    (
                        "Run `git remote remove origin` and re-run; after the G1 merge add it "
                        "back, push main and re-run /project-init, and EXTEND finishes the remote "
                        "steps (Recommended: init never pushes to a remote it did not create)."
                    ),
                    "Stop.",
                ],
            )
        )
    stack = detect_stack(root)
    if mode != "SCAFFOLD" and code and not (root / "pyproject.toml").is_file():
        # render refuses such a repo (plan_render): stop here, before the talk is spent on it.
        # First in the list: it decides the run, and clearing another stop only leads here
        stops.insert(
            0,
            Stop(
                "no-stack-pack",
                f"{no_pack(root)}: project-init v3 ships the Python pack only, and it "
                "needs pyproject.toml at the repo root. P4's render would refuse after the talk",
                [
                    "Stop here (Recommended: v3 ships the Python pack only).",
                    (
                        "Adopt specs/ and memory only, no gates: `git switch -c "
                        "plan/project-init`, then P2 writes the constitution and the ADRs "
                        "there, and nothing is rendered (0-preflight.md)."
                    ),
                ],
            ),
        )
    agent_tracked = len(z_split(git(root, "ls-files", "-z", "--", ".agent").out)) if commits else 0
    for base in manifest_dirs(root):
        problem = toml_problem(base / "pyproject.toml")
        if problem:
            rel = rel_posix(base / "pyproject.toml", root)
            notes.append(f"{rel} does not parse ({problem}): its scripts and signals are missing")
    older = pre_adoption_branches(root) if commits and not (root / MANIFEST).is_file() else []
    if older:
        notes.append(
            "lane-named branches from before adoption: "
            + ", ".join(older)
            + ". They are not changes: I8 skips a branch that forks before the adoption, and "
            "`mise run status` lists them"
        )
    reads, os_reads = env_scan(root)
    if os_reads:
        notes.append("OS variables read, not part of the env contract: " + ", ".join(os_reads))
    name = project_name(root)
    return Facts(
        repo=str(root),
        name=name,
        mode=mode,
        mode_evidence=evidence,
        has_git=git_repo,
        commits=commits,
        branch=branch,
        default_branch=detect_default_branch(root, load_toml(root / MANIFEST)),
        origin=origin,
        remotes=remotes,
        dead_remotes=dead,
        upstream=upstream,
        ahead=ahead,
        behind=behind,
        dirty=dirty,
        untracked_lockfiles=locks,
        authors=authors,
        tier="team" if len(authors) >= 2 else "solo",
        stack=stack,
        scripts=console_scripts(root),
        signals=detect_signals(root),
        env_reads=reads,
        tools=tools,
        gh=gh_facts(origin, offline, tools.get("gh") is not None),
        vault=vault_matches(vault, name),
        stops=stops,
        notes=notes,
        tool_pins=mise_pins(root),
        author_commits={p.shown: p.commits for p in people if p.commits},
        authors_not_counted=[f"{p.shown}: {web_only_why(p)}" for p in people if not p.commits],
        bot_commits=bot_commits,
        python=python_facts(root),
        agent_tracked=agent_tracked,
    )


LANE_PREFIXES = ("feat", "chg", "fix", "chore", "refactor", "plan")  # project.py's LANES


def pre_adoption_branches(root: Path) -> list[str]:
    """Local branches under a lane prefix that the default branch lacks, in a repo project-init
    has not adopted yet; the adoption's own plan/project-init left out. project.py's I8 skips
    them once the adoption lands, since they fork before it (an old feat/ branch, a v2
    chore/project-init). A merged one never counted, so it is not listed."""
    default = detect_default_branch(root)
    refs = git(
        root,
        "for-each-ref",
        "--format=%(refname:short)",
        f"--no-merged=refs/heads/{default}",
        *(f"refs/heads/{p}/" for p in LANE_PREFIXES),
    )
    return [ref for ref in refs.out.split() if ref != "plan/project-init"] if refs.code == 0 else []


def label(name: str) -> str:
    return f"{name} {'.' * max(1, 12 - len(name))} "


INDENT = " " * 14


def python_line(py: dict[str, object]) -> str:
    """P0's python row: the pin, or with none the versions P1 and P4 try (python_candidates)."""
    req = f" (requires-python {py['requires']})" if py.get("requires") else ""
    if py.get("pin"):
        return f".python-version {py['pin']}{req}"
    raw = py.get("candidates")
    cands = [
        PyCandidate(c.get("version"), list(c.get("sources") or []))
        for c in (raw if isinstance(raw, list) else [])
        if isinstance(c, dict)
    ]
    return (
        f"no .python-version{req}: P1 and P4 try {candidates_text(cands)}; P4 pins the first "
        "that builds (init.py prepare)"
    )


def _person(shown: str) -> str:
    return shown.rsplit(" <", 1)[0] or shown


def authors_explained(f: Facts) -> list[str]:
    """How the authors line counted (D9): who counts, with their commits, and who does not
    (web-UI commits only, bots) with why. A second human needs a commit of their own."""
    lines: list[str] = []
    ranked = sorted(f.author_commits.items(), key=lambda kv: -kv[1])
    if ranked:
        shown = [f"{_person(who)} ({plural(n, 'commit')})" for who, n in ranked[:3]]
        more = f" and {len(ranked) - 3} more" if len(ranked) > 3 else ""
        lines.append("counted: " + ", ".join(shown) + more)
    parts = []
    for entry in f.authors_not_counted[:3]:
        who, _, why = entry.rpartition(": ")
        parts.append(f"{_person(who)} ({why})")
    if len(f.authors_not_counted) > 3:
        parts.append(f"{len(f.authors_not_counted) - 3} more with web-UI commits only")
    if f.bot_commits:
        parts.append(plural(f.bot_commits, "bot commit"))
    if parts:
        lines.append("not counted (web-UI commits only and bots, D9): " + "; ".join(parts))
    return lines


def format_preflight(f: Facts) -> str:
    if not f.has_git:
        git_desc = "no .git"
    else:
        noun = "commit" if f.commits == 1 else "commits"
        parts = [f"{f.branch or '(detached)'}, {f.commits} {noun}"]
        if f.origin and is_local_url(f.origin):
            parts.append(f"origin {f.origin} (a local folder: render refuses to record it)")
        else:
            parts.append(f"origin {f.origin}" if f.origin else "no origin")
        if f.upstream and (f.ahead or f.behind):
            parts.append(f"{f.ahead} ahead, {f.behind} behind {f.upstream}")
        if f.untracked_lockfiles:
            parts.append(
                "untracked: " + ", ".join(f.untracked_lockfiles) + " (lockfile: will commit)"
            )
        git_desc = ", ".join(parts)
    lines = [label("mode") + f.mode.ljust(16) + " git ..... " + git_desc]
    if f.mode_evidence:  # what set an EXTEND or MIGRATE mode, the legacy stores and hooks named
        lines.append(label("evidence") + ", ".join(f.mode_evidence))
    if f.mode == "EXTEND+v2-migrate":
        lines.append(
            label("migrate")
            + "after P1: init.py migrate-v2 prints the one prompt, each v2 file with its fate"
        )

    stack = f.stack
    if f.scripts:
        stack += ", cli (" + ", ".join(f"{k} = {v}" for k, v in f.scripts.items()) + ")"
    present = [s for s in SIGNALS if s in f.signals]
    absent = [s for s in NO_ORDER if s not in f.signals]
    sig = ", ".join(present) if present else "none"
    if absent and present:
        sig += "; no " + "/".join(absent)
    lines.append(label("stack") + stack.ljust(45) + " signals .. " + sig)

    ok: list[str] = []
    missing: list[str] = []
    for name, _ in TOOLS:
        version = f.tools.get(name)
        if version is None:
            missing.append(name)
            continue
        text = f"{name} {version}"
        if name == "gh":
            plan = f.gh.get("plan")
            if plan and plan != "unknown":
                text += f" ({plan})"
            elif plan:
                text += " (logged in; plan unknown: the token lacks the user scope)"
            elif f.gh.get("status") == "not logged in":
                text += " (not logged in)"
        ok.append(text)
    tools = ", ".join(ok)
    in_repo = [m for m in missing if m in f.tool_pins]  # EXTEND: the repo's mise.toml pins it
    pinned = [m for m in missing if m in ("gitleaks", "git-cliff") and m not in in_repo]
    other = [m for m in missing if m not in pinned and m not in in_repo]
    if in_repo:
        tools += (
            "; " + ", ".join(in_repo) + " pinned in mise.toml (run through `mise x --`; "
            "not on PATH outside the repo)"
        )
    if pinned:
        tools += "; " + ", ".join(pinned) + " not runnable (pinned in P4)"
    if other:
        tools += "; " + ", ".join(other) + " not runnable (install it)"
    lines.append(label("tools") + tools)
    if f.vault:
        lines.append(label("vault") + " | ".join(f.vault))
    else:
        lines.append(label("vault") + f"no kitchen/active/idea named {f.name}")
    if f.python:
        lines.append(label("python") + python_line(f.python))

    count = len(f.authors)
    lines.append(
        label("authors") + f"{count} human{'s' if count != 1 else ''} in 6 months: {f.tier} tier"
    )
    lines += [INDENT + line for line in authors_explained(f)]
    if f.agent_tracked:
        lines.append(
            label(".agent/")
            + f"tracked ({plural(f.agent_tracked, 'file')}): P2 reads it as intake, then P4 runs "
            "`git rm -r -q --cached .agent` (D7); the files stay on disk, and the rendered "
            ".gitignore keeps .agent/ local"
        )
    if f.env_reads:
        rows = []
        for read in f.env_reads:
            detail = read.type
            if read.default is not None:
                detail += f", default {one_line(read.default) or chr(34) * 2}"
            rows.append(f"{read.name} ({read.kind}, {detail}; {read.where[0]})")
        lines.append(label("env") + ("\n" + INDENT).join(rows))
    extra = {k: v for k, v in f.remotes.items() if k != "origin"}
    if extra or f.dead_remotes:
        rows = [
            f"{k} {v}" + (" (dead)" if k in f.dead_remotes else "") for k, v in f.remotes.items()
        ]
        lines.append(label("remotes") + " | ".join(rows) + "  (only origin counts)")
    if f.gh.get("visibility"):
        lines.append(label("github") + f"{github_slug(f.origin)} is {f.gh['visibility']}")
    for note in f.notes:
        lines.append(label("note") + note)
    if not f.stops:
        lines.append(label("stops") + "none")
    for stop in f.stops:
        lines.append(label("STOP") + stop.what)
        for i, option in enumerate(stop.options, 1):
            lines.append(f"{INDENT}{i}. {option}")
    return "\n".join(lines)


def cmd_preflight(args: argparse.Namespace) -> int:
    root = repo_root(args.repo)
    roots = [Path(p).expanduser() for p in args.search_root] or [
        Path.home() / "projects",
        Path.home() / "work",
    ]
    facts = preflight(root, args.offline, Path(args.vault).expanduser(), roots)
    if args.json:
        print(json.dumps(asdict(facts), indent=2))
    else:
        print(format_preflight(facts))
    return 1 if facts.stops else 0


# ---------------------------------------------------------------------------------------------
# P1 probe


@dataclass
class ProbeRow:
    script: str
    args: list[str]
    env: dict[str, str]
    source: str  # readme | given | fallback | no-args | help | bad-input | env
    exit: int
    outcome: str  # pass | crash (a traceback) | timeout | error | missing
    reason: str
    stdout: str


# The UI surface (v3.1, design C.2): what kind of proof the repo's changes will owe, from its
# declared runtime dependencies. The framework lists are project.py's, read from its source,
# so the approve warning (C.3) and this line never disagree.
PROJECT_PY = TEMPLATES / "scripts" / "project.py"
UI_LISTS = {"WEB_UI_FRAMEWORKS": "web", "TUI_FRAMEWORKS": "terminal"}
SURFACES = {  # kind -> (what the evidence line calls it, the proof it gets)
    "web": ("a web UI", "proof by screenshot and video"),
    "terminal": ("a terminal UI", "proof by terminal recordings"),
}


@dataclass(frozen=True)
class Surface:
    kind: str  # web | terminal | cli (console scripts only) | none
    evidence: str
    setup: str  # the `mise run proof -- setup <kind>` its captures need, or ""


def ui_frameworks() -> dict[str, str]:
    """Framework name -> web | terminal, from project.py's WEB_UI_FRAMEWORKS and
    TUI_FRAMEWORKS assignments (an AST read: project.py is never imported)."""
    found: dict[str, str] = {}
    for node in ast.parse(read_text(PROJECT_PY) or "").body:
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1):
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id in UI_LISTS:
            for leaf in ast.walk(node.value):
                if isinstance(leaf, ast.Constant) and isinstance(leaf.value, str):
                    found[leaf.value] = UI_LISTS[target.id]
    return found


def ui_surface(root: Path) -> Surface:
    """The repo's surface: a web UI or a TUI framework among the runtime dependencies
    ([project] dependencies and extras), else its console scripts, else none."""
    project = table(load_toml(root / "pyproject.toml"), "project")
    reqs = project.get("dependencies")
    reqs = list(reqs) if isinstance(reqs, list) else []
    for group in table(project, "optional-dependencies").values():
        reqs += group if isinstance(group, list) else []
    names = sorted({n for r in reqs if isinstance(r, str) and (n := _req_name(r))})
    kinds = ui_frameworks()
    for kind, (what, _) in SURFACES.items():
        if hits := [name for name in names if kinds.get(name) == kind]:
            evidence = f"{what}: {', '.join(hits)} in pyproject.toml"
            return Surface(kind, evidence, f"mise run proof -- setup {kind}")
    if scripts := sorted(console_scripts(root)):
        return Surface("cli", f"console scripts only: {', '.join(scripts)}", "")
    return Surface("none", "no UI framework and no console script", "")


def surface_line(surface: Surface) -> str:
    """The probe report's surface line: the evidence, and the setup P7's punch list names."""
    if surface.kind in SURFACES:
        proof = SURFACES[surface.kind][1]
        return label("surface") + f"{surface.evidence}; {proof} (P7: {surface.setup})"
    needs = "run, which needs" if surface.kind == "cli" else "run, http or log, which need"
    return label("surface") + f"{surface.evidence or 'not read'}; proof by {needs} no setup"


@dataclass
class ProbeReport:
    status: str  # ran | skipped | unprobed
    reason: str
    happy: list[str]
    happy_source: str
    restricted: bool
    rows: list[ProbeRow]
    untouched: bool
    passes: int = 0
    crashes: int = 0
    timeouts: int = 0
    python: str = ""  # with no .python-version: the X.Y the clone built with (P4 pins it)
    python_failures: list[str] = field(default_factory=list)  # `<version>: <cause>` tried first
    service: list[str] = field(default_factory=list)  # the service-shaped signals, with evidence
    trunk: list[TrunkRow] = field(default_factory=list)  # static, so set whatever the status
    surface: Surface = field(default_factory=lambda: Surface("none", "", ""))  # static too


FENCE = re.compile(r"^\s*(```|~~~)")
# each case: no network, and a PID namespace of its own. When the case's first process exits,
# the kernel kills everything still in the namespace: a background child, a double fork, a
# child in a new session. --kill-child: the namespace also dies with unshare itself.
JAIL = ("unshare", "-rn", "--pid", "--fork", "--kill-child")
ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
SHELL_OPS = frozenset({"&&", "||", "|", ";", ">", ">>", "<"})


def readme_invocations(
    text: str, script: str, entry: str | None
) -> list[tuple[dict[str, str], list[str]]]:
    """Happy paths from README fences: `[VAR=x] [uv run [opts]] <script> <args>`, and
    `mise run start -- <args>` for the entry script."""
    found: list[tuple[dict[str, str], list[str]]] = []
    inside = False
    for line in text.splitlines():
        if FENCE.match(line):
            inside = not inside
            continue
        if not inside:
            continue
        try:
            tokens = shlex.split(line.strip().removeprefix("$ ").removeprefix("> "), comments=True)
        except ValueError:
            continue
        env: dict[str, str] = {}
        while tokens and ASSIGN.match(tokens[0]):
            key, _, value = tokens.pop(0).partition("=")
            env[key] = value
        args: list[str] | None = None
        if tokens[:3] == ["mise", "run", "start"] and script == entry:
            rest = tokens[3:]
            args = rest[1:] if rest[:1] == ["--"] else rest
        else:
            if tokens[:2] == ["uv", "run"]:
                tokens = tokens[2:]
                while tokens and tokens[0].startswith("-"):
                    tokens.pop(0)
            if tokens and tokens[0] == script:
                args = tokens[1:]
        if args is None:
            continue
        for i, token in enumerate(args):
            if token in SHELL_OPS:
                args = args[:i]
                break
        if (env, args) not in found:
            found.append((env, args))
    return found


def crash_reason(stderr: str) -> str:
    for line in reversed(stderr.strip().splitlines()):
        match = re.match(r"^([A-Za-z_][\w.]*)(?::|$)", line.strip())
        if match and not line.startswith(" "):
            return match.group(1).rsplit(".", 1)[-1]
    return "traceback"


def repo_state(root: Path) -> tuple[str, str]:
    head = git_out(root, "rev-parse", "-q", "--verify", "HEAD") or ""
    status = git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all").out
    return head, status


def probe(root: Path, given: list[list[str]], keep: bool) -> ProbeReport:
    """The P1 report: the sandboxed runs, the trunk candidates and the UI surface. The last two
    come from a static scan, so a probe that cannot run anything still lists them."""
    trunk = trunk_candidates(root)
    report = run_probe(root, given, keep)
    report.trunk = trunk
    report.surface = ui_surface(root)
    return report


def run_probe(root: Path, given: list[list[str]], keep: bool) -> ProbeReport:
    empty = ProbeReport("skipped", "", [], "", False, [], True)
    if not is_git_root(root) or not has_commits(root):
        empty.reason = "no commits: nothing committed to probe"
        return empty
    if run([*JAIL, "true"], timeout=15).code != 0:
        empty.reason = (
            "no user namespaces (unshare -rn --pid --fork failed): the network cannot be cut "
            "and a case's children cannot be reaped"
        )
        return empty
    before = repo_state(root)
    tmp = Path(tempfile.mkdtemp(prefix="project-init-probe-"))
    try:
        report = _probe_in(root, tmp, given)
    finally:
        if keep:
            print(f"probe: scratch kept at {tmp}", file=sys.stderr)
        else:
            shutil.rmtree(tmp, ignore_errors=True)
    report.untouched = repo_state(root) == before
    return report


def _probe_in(root: Path, tmp: Path, given: list[list[str]]) -> ProbeReport:
    clone = tmp / "probe"
    home = tmp / "home"
    home.mkdir()
    result = run(
        ["git", "clone", "--no-local", "-q", str(root), str(clone)], env=git_env(), timeout=300
    )
    if result.code != 0:
        return ProbeReport(
            "unprobed", f"git clone failed: {result.err.strip()[-200:]}", [], "", False, [], True
        )
    if not (clone / "pyproject.toml").is_file():
        return ProbeReport(
            "unprobed",
            f"{no_pack(clone)}: the probe runs Python console scripts ([project.scripts]) only",
            [],
            "",
            False,
            [],
            True,
        )
    signals = detect_signals(clone)
    service = [
        f"{s}: {', '.join(signals[s])}" for s in SIGNALS if s in RESTRICTED_SIGNALS & set(signals)
    ]
    restricted = bool(service)
    scripts = console_scripts(clone)
    if not scripts:
        report = ProbeReport(
            "skipped", "no console scripts ([project.scripts])", [], "", restricted, [], True
        )
        report.service = service
        return report
    env = {
        k: v for k, v in os.environ.items() if k not in ("VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT")
    }
    # cwd outside the clone: a mise shim must not read the clone's (untrusted) mise config. With
    # no .python-version, each candidate in turn: the X.Y that builds is the one P4 pins
    pinned = python_pin(clone) is not None
    built, failures = sync_with_python(clone, python_candidates(clone), env, tmp)
    if built is None:
        return ProbeReport(
            "unprobed",
            "uv sync failed in the clean clone: " + " | ".join(failures),
            [],
            "",
            restricted,
            [],
            True,
            python_failures=failures,
            service=service,
        )
    cache = run(["uv", "cache", "dir"], cwd=tmp, env=env, timeout=30).out.strip()
    reads = env_reads(clone)
    readme = read_text(clone / "README.md") or ""
    entry = next(iter(scripts))
    venv_bin = clone / ".venv" / "bin"
    base_env = {
        "PATH": f"{venv_bin}:/usr/local/bin:/usr/bin:/bin",
        "HOME": str(home),
        "LANG": "C.UTF-8",
    }
    if cache:
        base_env["UV_CACHE_DIR"] = cache
    rows: list[ProbeRow] = []
    primary: list[str] = []
    primary_source = ""
    for script in scripts:
        cases: list[tuple[dict[str, str], list[str], str]] = []
        if restricted:
            cases.append(({}, ["--help"], "help"))
        else:
            happy: list[tuple[dict[str, str], list[str]]]
            if given:
                happy = [({}, g) for g in given]
                source = "given"
            else:
                happy = readme_invocations(readme, script, entry)
                source = "readme"
                if not happy:
                    happy = [({}, ["100"])]
                    source = "fallback"
            plain = next((args for env_, args in happy if not env_), happy[0][1])
            if script == entry:
                primary, primary_source = plain, source
            cases += [(e, a, source) for e, a in happy]
            for args, why in (([], "no-args"), (["--help"], "help"), (["abc"], "bad-input")):
                if not any(not e and a == args for e, a, _ in cases):
                    cases.append(({}, args, why))
            for read in reads:
                for value in ("", "abc"):
                    cases.append(({read.name: value}, plain, "env"))
        for case_env, args, source in cases:
            rows.append(
                _run_case(clone, venv_bin / script, script, base_env, case_env, args, source)
            )
    report = ProbeReport("ran", "", primary, primary_source, restricted, rows, True)
    report.python = "" if pinned else built
    report.python_failures = failures
    report.service = service
    report.passes = sum(r.outcome == "pass" for r in rows)
    report.crashes = sum(r.outcome == "crash" for r in rows)
    report.timeouts = sum(r.outcome == "timeout" for r in rows)
    return report


def _run_case(
    clone: Path,
    exe: Path,
    script: str,
    base_env: dict[str, str],
    case_env: dict[str, str],
    args: list[str],
    source: str,
) -> ProbeRow:
    if not exe.exists():
        return ProbeRow(script, args, case_env, source, 127, "missing", "not installed", "")
    assigns = [f"{k}={v}" for k, v in {**base_env, **case_env}.items()]
    # -k 2: a script that ignores SIGTERM gets SIGKILL 2s later. JAIL's PID namespace reaps
    # whatever the script started when timeout (its first process) exits, and the own process
    # group lets the outer 30s limit kill unshare, which takes the namespace with it.
    argv = [*JAIL, "env", "-i", *assigns, "timeout", "-k", "2", "10", str(exe), *args]
    result = run(argv, cwd=clone, timeout=30, own_group=True)
    first = next((ln.strip() for ln in result.out.splitlines() if ln.strip()), "")[:100]
    if CRASH in result.err:
        return ProbeRow(
            script, args, case_env, source, result.code, "crash", crash_reason(result.err), first
        )
    # 124: timed out; 137 or -9: `timeout -k` had to SIGKILL the process group (itself included)
    if result.code in (124, 137, -signal.SIGKILL):
        return ProbeRow(script, args, case_env, source, result.code, "timeout", "timeout", first)
    if result.code == 0:
        return ProbeRow(script, args, case_env, source, 0, "pass", "", first)
    last = next((ln.strip() for ln in reversed(result.err.splitlines()) if ln.strip()), "")[:100]
    return ProbeRow(script, args, case_env, source, result.code, "error", last, first)


# curl -f exits 22 on an HTTP error, so the exit column is the check; no body is assumed
HEALTH_ROW = "| curl -fsS http://localhost:<port>/health | 0 | | |"


def probe_notes(report: ProbeReport) -> list[str]:
    """The lines after the probe's own: the Python the clone built with when the repo pins
    none, and for a service-shaped repo that the probe says little about it (orca, helios)."""
    lines: list[str] = []
    if report.python:
        tried = (
            f"; tried first: {' | '.join(report.python_failures)}" if report.python_failures else ""
        )
        lines.append(
            label("python") + f"no .python-version: {report.python} built the clone; P4 pins it "
            f"(init.py prepare --python {report.python}){tried}"
        )
    if report.service:
        names = ", ".join(s.split(":", 1)[0] for s in report.service)
        if report.status == "ran":
            why = f"the {names} signals limit it to --help, which never reaches the running service"
        elif report.status == "skipped":
            why = f"the {names} signals mark a service, and with no console script nothing ran"
        else:
            why = f"the {names} signals mark a service, and nothing ran (above)"
        lines.append(label("service") + f"little signal for a service: {why}")
        lines.append(
            INDENT + "P2: suggest the service's health check as the Run-it row of the first feat "
            f"change (validation.md `## Run it`), e.g. `{HEALTH_ROW}`"
        )
    return lines


def format_probe(report: ProbeReport) -> str:
    if report.status != "ran":
        return "\n".join(
            [
                label("probe") + f"{report.status}: {report.reason}",
                *probe_notes(report),
                surface_line(report.surface),
                *trunk_lines(report.trunk),
            ]
        )
    lines = [label("probe") + "(scratch clone, network off)"]
    scripts = sorted({r.script for r in report.rows})
    many = len(scripts) > 1
    first_traceback = True

    def guessed(row: ProbeRow) -> str:
        return f" ({HAPPY_WORDS['fallback']})" if row.source == "fallback" else ""

    def outcome(row: ProbeRow) -> str:
        nonlocal first_traceback
        if row.outcome == "crash":  # the first one says what the exception names are from
            text = row.reason + (" traceback" if first_traceback else "")
            first_traceback = False
        elif row.outcome == "timeout":
            text = "timeout (killed after 10 s)"
        elif row.outcome == "missing":
            text = "not installed"
        else:
            text = f'exit {row.exit} "{row.reason}"'
        return text + guessed(row)

    def call(row: ProbeRow) -> str:
        prefix = "".join(f"{k}={shlex.quote(v) if v else chr(34) * 2} " for k, v in row.env.items())
        return prefix + " ".join([row.script, *(shlex.quote(a) for a in row.args)])

    for row in report.rows:
        if row.outcome == "pass":
            lines.append(f'{INDENT}{call(row)} -> "{row.stdout}" exit 0{guessed(row)}')
    for script in scripts:
        bad = [
            r
            for r in report.rows
            if r.script == script and r.outcome != "pass" and r.source != "env"
        ]
        if bad:
            lines.append(INDENT + " | ".join(f"{call(r)} -> {outcome(r)}" for r in bad))
        env_rows_ = [
            r
            for r in report.rows
            if r.script == script and r.outcome != "pass" and r.source == "env"
        ]
        if env_rows_:
            parts = []
            for r in env_rows_:
                key, value = next(iter(r.env.items()))
                shown = f"{key}={value}" if value else f'{key}=""'
                parts.append(f"{script}: {shown}" if many else shown)
                parts[-1] += f" -> {outcome(r)}"
            lines.append(INDENT + " | ".join(parts))
    tail = f"{report.passes} pass, {report.crashes} crash{'es' if report.crashes != 1 else ''}"
    if report.timeouts:
        tail += f", {report.timeouts} timeout{'s' if report.timeouts != 1 else ''}"
    if report.happy_source == "fallback":
        tail += "; no README fence names a happy path, so 100 stood in for one"
    if report.restricted:
        tail += "; service-shaped signals: --help only"
    tail += "; repo untouched" if report.untouched else "; REPO CHANGED DURING THE PROBE"
    lines.append(INDENT + tail)
    static = [surface_line(report.surface), *trunk_lines(report.trunk)]
    return "\n".join([*lines, *probe_notes(report), *static])


def cmd_probe(args: argparse.Namespace) -> int:
    root = repo_root(args.repo)
    given = [shlex.split(a) for a in args.args]
    report = probe(root, given, args.keep)
    if args.json:
        print(json.dumps(asdict(report), indent=2))
    else:
        print(format_probe(report))
    return 0 if report.untouched else 1


# ---------------------------------------------------------------------------------------------
# P1 probe: trunk candidates (v3.1, design A.2). A static scan: no project code runs, and the
# repo is only read. P2 asks about them, and EXTEND proposes them to a v3.0 repo (render --check)


@dataclass(frozen=True)
class TrunkRow:
    glob: str  # gitignore-style, from the repo root: a file, or `<folder>/**`
    why: str


TECH_STACK = "specs/tech-stack.md"
TRUNK_HEADING = "Trunk"
FAN_IN_FLOOR = 3  # the importers a trunk module needs at the least, whatever the package's size
FAN_IN_SHARE = 0.25  # and at least this share of its package's modules,
FAN_IN_CAP = 10  # capped: orca's core/config.py has 38 importers, under 25% of its package
SHARED_SETTINGS = 2  # importers outside its folder that make a config.py found by name trunk
SRC_ROOT = "src"  # the src layout's import root: never a package, even with an __init__.py
SETTINGS_WORDS = ("config", "settings")
SCHEMA_FOLDERS = {
    "migrations": "migrations: schema changes reach every row",
    "alembic": "alembic migrations: schema changes reach every row",
    "schema": "the schema: every row follows it",
}
SQL_FOLDER = "SQL files: schema changes reach every row"
READ_IN = re.compile(r"\bread in ([^;]+)")  # the notes of an env contract row (env_rows)
RULE_ID = re.compile(r"^\s*-\s*(S-\d+)\b")
# A standing rule names the env contract, the docs and the specs as often as code: only code and
# schema paths become trunk candidates, and never under these top folders.
RULE_CODE_SUFFIXES = (".py", ".pyi", ".pyx", ".sql", ".graphql", ".gql", ".proto", ".prisma")
RULE_SKIPPED_FOLDERS = ("specs", "project_memory", "proof", "docs")
CODE_SPAN = re.compile(r"`([^`\s]+)`")
PROJECT_VERSION = re.compile(r'(?m)^VERSION = "([^"]+)"')


def trunk_candidates(root: Path) -> list[TrunkRow]:
    """What P1 proposes for the `## Trunk` section of specs/tech-stack.md, each with its why:
    the module each console script runs, the modules with high fan-in, the settings modules,
    the migration and schema folders, and the paths a standing rule S-n names. By kind, then
    by path. A path found twice is one row with both reasons, and a path inside a folder row
    is left out."""
    files = repo_files(root)
    modules = [rel for rel in files if app_module(rel)]
    graph = import_graph(root, modules)
    found = [
        *entry_candidates(root),
        *fan_in_candidates(graph),
        *settings_candidates(root, modules, graph),
        *schema_candidates(files),
        *rule_candidates(root, set(files)),
    ]
    reasons: dict[str, list[str]] = {}
    for glob, why in found:
        if why not in reasons.setdefault(glob, []):
            reasons[glob].append(why)
    folders = [glob.removesuffix("/**") for glob in reasons if glob.endswith("/**")]
    return [
        TrunkRow(glob, "; ".join(why))
        for glob, why in reasons.items()
        if not any(
            glob != f"{folder}/**" and _inside(glob.removesuffix("/**"), [folder])
            for folder in folders
        )
    ]


def repo_files(root: Path) -> list[str]:
    """The repo's files, repo-relative and sorted: what git tracks, or every file when root is
    no git repo. Hidden folders, build output, installed packages and virtualenvs are left out
    either way."""
    if is_git_root(root):
        names = z_split(git(root, "ls-files", "-z").out)
    else:
        names = []
        for dirpath, dirnames, filenames in os.walk(root):
            here = Path(dirpath)
            dirnames[:] = sorted(d for d in dirnames if collectable(here, d))
            names += [rel_posix(here / name, root) for name in filenames]
    return sorted(
        name
        for name in names
        if not any(p.startswith(".") or p in CODE_SKIP for p in PurePosixPath(name).parts[:-1])
    )


def app_module(rel: str) -> bool:
    """A Python module of the app: no test, no conftest.py, no tool-owned copy."""
    path = PurePosixPath(rel)
    return (
        path.suffix == ".py"
        and not is_test_file(path.name)
        and path.name != "conftest.py"
        and not any(part in TEST_DIR_NAMES for part in path.parts[:-1])
        and rel not in TOOL_OWNED
    )


def parse_module(path: Path) -> ast.Module | None:
    """The module's AST, or None for a file too big, unreadable or not Python 3."""
    try:
        if path.stat().st_size > 1_000_000:
            return None
        return ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError, ValueError):
        return None


def entry_candidates(root: Path) -> list[tuple[str, str]]:
    """The module each console script of [project.scripts] runs."""
    commands: dict[str, list[str]] = {}
    for name, target in console_scripts(root).items():
        path = module_file(root, target.partition(":")[0].strip())
        if path is not None:
            named = f"the {name} command ({target.strip()})"
            commands.setdefault(rel_posix(path, root), []).append(named)
    return [
        (rel, "the entrypoint of " + " and ".join(named)) for rel, named in sorted(commands.items())
    ]


def top_packages(modules: list[str]) -> dict[str, list[str]]:
    """Each top-level package (a folder with an __init__.py and no ancestor folder that has
    one) and every module under it, its subpackages' included. A folder with no __init__.py
    inside a package is a namespace folder of that package, never a new top. The root src/
    is the import root even when it holds an __init__.py (orca tracks a stray one)."""
    inits = {
        str(PurePosixPath(m).parent) for m in modules if PurePosixPath(m).name == "__init__.py"
    } - {SRC_ROOT}
    tops = sorted(
        d
        for d in inits
        if d != "." and not any(str(up) in inits for up in PurePosixPath(d).parents)
    )
    return {top: [m for m in modules if m.startswith(top + "/")] for top in tops}


def dotted_name(rel: str, base: str) -> str:
    """src/shop/db.py, its package's parent being src -> shop.db; an __init__.py is its
    package."""
    path = PurePosixPath(rel)
    parts = list((path if base == "." else path.relative_to(base)).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def known_prefix(dotted: str, known: set[str]) -> str:
    """The longest leading part of a dotted name that is a known module, or ""."""
    parts = dotted.split(".")
    for end in range(len(parts), 0, -1):
        if ".".join(parts[:end]) in known:
            return ".".join(parts[:end])
    return ""


def import_targets(tree: ast.Module, name: str, package: bool, known: set[str]) -> set[str]:
    """The known modules a module's imports name. `from a import b` names a.b when that is a
    module, else a; `import a.b.c` names its longest known prefix. A relative import resolves
    from the module's own package, and one that climbs past the top names nothing."""
    here = name.split(".") if package else name.split(".")[:-1]
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found |= {known_prefix(alias.name, known) for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            if node.level > len(here):
                continue
            parts = here[: len(here) - node.level + 1] if node.level else []
            base = ".".join([*parts, *([node.module] if node.module else [])])
            for alias in node.names:
                full = f"{base}.{alias.name}" if base else alias.name
                found.add(full if full in known else known_prefix(base, known))
    return (found & known) - {name}


@dataclass
class ImportGraph:
    """Who imports whom inside each top-level package, by an AST scan. Only a package's own
    modules are importers: a test, a script or a migration outside it is not."""

    importers: dict[str, set[str]]  # module -> the modules of its package that import it
    package: dict[str, str]  # module -> its top-level package folder
    size: dict[str, int]  # top-level package folder -> its module count


def import_graph(root: Path, modules: list[str]) -> ImportGraph:
    """A module under the root src/ is known by its src-layout name (orca.core.config) and by
    the name a repo that imports through src uses (src.orca.core.config)."""
    graph = ImportGraph({}, {}, {})
    for top, members in top_packages(modules).items():
        base = str(PurePosixPath(top).parent)
        names = {rel: dotted_name(rel, base) for rel in members}
        where = {name: rel for rel, name in names.items()}
        if base == SRC_ROOT:
            where |= {f"{SRC_ROOT}.{name}": rel for rel, name in names.items()}
        graph.size[top] = len(members)
        for rel, name in names.items():
            graph.package[rel] = top
            tree = parse_module(root / rel)
            package = PurePosixPath(rel).name == "__init__.py"
            for target in import_targets(tree, name, package, set(where)) if tree else set():
                if where[target] != rel:
                    graph.importers.setdefault(where[target], set()).add(rel)
    return graph


def fan_in_candidates(graph: ImportGraph) -> list[tuple[str, str]]:
    """Modules imported by at least max(3, min(ceil(25% of the package's modules), 10)) other
    modules of the same package. The cap keeps a big package's shared module in: 25% of
    orca's modules is more than the 38 that import its core/config.py."""
    rows: list[tuple[str, str]] = []
    for rel, who in graph.importers.items():
        top = graph.package[rel]
        size = graph.size[top]
        need = max(FAN_IN_FLOOR, min(math.ceil(FAN_IN_SHARE * size), FAN_IN_CAP))
        if len(who) >= need:
            others = f"{size - 1} other modules in {PurePosixPath(top).name}"
            rows.append((rel, f"imported by {len(who)} of {others}"))
    return sorted(rows)


def contract_readers(text: str) -> dict[str, list[str]]:
    """file -> the env names whose .env.example row says `read in <file>, ...` (env_rows)."""
    found: dict[str, list[str]] = {}
    for name, block in contract_blocks(text).items():
        cells = block[0].split("|", 5)
        match = READ_IN.search(cells[-1]) if len(cells) == 6 else None
        for rel in match.group(1).split(",") if match else []:
            rel = rel.strip()
            if rel and name not in found.setdefault(rel, []):
                found[rel].append(name)
    return found


def settings_module(root: Path, rel: str) -> bool:
    """Named like a settings module (config, settings), or holding a pydantic-settings class."""
    path = PurePosixPath(rel)
    stem = (path.parent.name if path.name == "__init__.py" else path.stem).lower()
    if any(word in stem for word in SETTINGS_WORDS):
        return True
    tree = parse_module(root / rel)
    return tree is not None and any(
        isinstance(node, ast.ClassDef)
        and any(_dotted_tail(base).endswith("Settings") for base in node.bases)
        for node in ast.walk(tree)
    )


def shared_settings(rel: str, graph: ImportGraph) -> bool:
    """A config.py or settings.py found by name is trunk at its package's root (outside every
    package: at the repo root, a flat layout's), or when 2 modules outside its own folder
    import it. A per-source config that only its own folder reads (orca's 10
    sources/<name>/config.py) is leaf."""
    folder = str(PurePosixPath(rel).parent)
    if folder == graph.package.get(rel, "."):
        return True
    outside = [who for who in graph.importers.get(rel, set()) if not _inside(who, [folder])]
    return len(outside) >= SHARED_SETTINGS


def settings_candidates(
    root: Path, modules: list[str], graph: ImportGraph
) -> list[tuple[str, str]]:
    """The settings modules. With an env contract, the ones its `read in` notes name. With none
    (an adoption's P1 runs before render writes it), config.py and settings.py by name, where
    shared_settings says the package shares them."""
    readers = contract_readers(read_text(root / ".env.example") or "")
    if not readers:
        return [
            (rel, "settings, by its file name")
            for rel in modules
            if PurePosixPath(rel).stem in SETTINGS_WORDS and shared_settings(rel, graph)
        ]
    rows: list[tuple[str, str]] = []
    for rel, names in sorted(readers.items()):
        if rel in modules and settings_module(root, rel):
            shown = ", ".join(names[:3]) + (f" and {len(names) - 3} more" if len(names) > 3 else "")
            rows.append((rel, f"settings read from the env: {shown}"))
    return rows


def schema_candidates(files: list[str]) -> list[tuple[str, str]]:
    """Migration and schema folders anywhere outside the tests, and top-level folders that hold
    SQL files, each as `<folder>/**`."""
    found: dict[str, str] = {}
    for rel in files:
        parts = PurePosixPath(rel).parts
        for i, part in enumerate(parts[:-1]):
            if part in TEST_DIR_NAMES:
                break
            if part in SCHEMA_FOLDERS:
                found.setdefault("/".join(parts[: i + 1]) + "/**", SCHEMA_FOLDERS[part])
                break
        else:
            if len(parts) == 2 and parts[1].endswith(".sql"):
                found.setdefault(f"{parts[0]}/**", SQL_FOLDER)
    return sorted(found.items())


def section_body(text: str, heading: str) -> str:
    """The lines under `## <heading>`, up to the next `## ` (as project.py's section_text)."""
    lines: list[str] = []
    inside = False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line[3:].strip() == heading
            continue
        if inside:
            lines.append(line)
    return "\n".join(lines)


def has_trunk_section(text: str) -> bool:
    return any(
        line.startswith("## ") and line[3:].strip() == TRUNK_HEADING for line in text.splitlines()
    )


def rule_candidates(root: Path, files: set[str]) -> list[tuple[str, str]]:
    """Each code or schema path a standing rule S-n of specs/tech-stack.md names in a code span,
    when the repo has it: a file as itself, a folder that holds such a file as `<folder>/**`.
    The env contract, docs, specs/, project_memory/ and proof/ are never candidates, although
    rules name them often (`.env.example` as trunk would put every flag change on trunk)."""
    rows: list[tuple[str, str]] = []
    for line in section_body(read_text(root / TECH_STACK) or "", "Standing rules").splitlines():
        rule = RULE_ID.match(line)
        if rule is None:
            continue
        why = f"named by standing rule {rule.group(1)}"
        for span in CODE_SPAN.findall(line):
            path = PurePosixPath(span)
            rel = path.as_posix().removeprefix("./")
            if path.is_absolute() or ".." in path.parts or rel == ".":
                continue
            if PurePosixPath(rel).parts[0] in RULE_SKIPPED_FOLDERS:
                continue
            if rel in files:
                if rel.endswith(RULE_CODE_SUFFIXES):
                    rows.append((rel, why))
            elif any(f.startswith(rel + "/") and f.endswith(RULE_CODE_SUFFIXES) for f in files):
                rows.append((f"{rel}/**", why))
    return sorted(rows)


def trunk_lines(rows: list[TrunkRow]) -> list[str]:
    """The probe report's Trunk block, each row in the section's own format (design A.1)."""
    if not rows:
        return [
            label("trunk") + "no candidates (a static scan found no console script, fan-in "
            "module, settings module or schema folder): P2 writes the ## Trunk section empty"
        ]
    head = (
        label("trunk") + f"{plural(len(rows), 'candidate')} for ## {TRUNK_HEADING} in "
        f"{TECH_STACK} (a static scan: no code ran)"
    )
    return [head, *(f"{INDENT}- {row.glob}: {row.why}" for row in rows)]


def trunk_upgrade(root: Path) -> list[str]:
    """The v3.1 EXTEND item (8-extend.md): specs/tech-stack.md has no `## Trunk` section. The
    first line says so, and the rest are the candidates P2 proposes, as section lines. [] when
    the section is there, or when there is no tech-stack.md yet (P2 writes it from the
    template, the section included). The section is product text: render never writes it."""
    text = read_text(root / TECH_STACK)
    if text is None or has_trunk_section(text):
        return []
    lead = f"{TECH_STACK} has no ## {TRUNK_HEADING} section"
    version = PROJECT_VERSION.search(read_text(root / "scripts" / "project.py") or "")
    if version and version.group(1).startswith("3.0."):
        lead = f"v3.1 upgrade: {lead}, and scripts/project.py is {version.group(1)}"
    lead += ". Until it has one, every path counts as leaf."
    rows = trunk_candidates(root)
    if not rows:
        return [
            f"{lead} P2 writes it empty on the plan/ branch: the static scan found no candidate"
        ]
    return [
        f"{lead} P2 proposes it on the plan/ branch from {plural(len(rows), 'candidate')}:",
        *(f"- {row.glob}: {row.why}" for row in rows),
    ]


def print_trunk(lines: list[str]) -> None:
    if lines:
        print(label("trunk") + lines[0])
        for line in lines[1:]:
            print(INDENT + line)


# ---------------------------------------------------------------------------------------------
# P4 prepare: the Python pin and the dev dependencies, before render and before any test run


TEST_EXTRAS = ("dev", "test", "tests", "testing")  # extras and groups that hold test deps
STANDARD_DEV = ("ruff", "ty", "pytest")


def _requirements(value: object) -> list[str]:
    """The PEP 508 strings of a dependency list ({include-group = ...} tables left out)."""
    if not isinstance(value, list):
        return []
    return [r.strip() for r in value if isinstance(r, str) and r.strip()]


def _group_key(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()  # PEP 735 normalizes group names


def group_requirements(
    groups: dict[str, object], name: str, seen: set[str] | None = None
) -> list[str]:
    """The PEP 508 strings of a [dependency-groups] group, its {include-group = ...} tables
    followed (PEP 735), each group once."""
    seen = set() if seen is None else seen
    key = _group_key(name)
    if key in seen:
        return []
    seen.add(key)
    value = next((v for k, v in groups.items() if _group_key(k) == key), None)
    out: list[str] = []
    for item in value if isinstance(value, list) else []:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
        elif isinstance(item, dict) and isinstance(item.get("include-group"), str):
            out += group_requirements(groups, str(item["include-group"]), seen)
    return out


def synced_groups(data: dict[str, object]) -> list[str]:
    """The groups `uv sync` installs: dev, or uv's default-groups ("all": every group)."""
    groups = table(data, "dependency-groups")
    wanted = table(data, "tool", "uv").get("default-groups")
    if wanted == "all":
        return [str(k) for k in groups]
    if isinstance(wanted, list):
        return [str(g) for g in wanted if isinstance(g, str)]
    return ["dev"]


def dev_additions(root: Path) -> list[tuple[str, str]]:
    """(requirement, where it comes from) for `uv add --dev`: the project's own test
    dependencies, from the dev and test extras of [project.optional-dependencies] and the test
    groups of [dependency-groups], then the standard's ruff, ty and pytest. `uv sync`, and so
    `mise install`, CI and prove-red, installs the dev group only (or uv's default-groups): a
    test dependency kept anywhere else never reaches `mise run test` (helios: pytest-asyncio
    in the dev extra, 290 tests failed). A name `uv sync` installs already is left alone, a
    group the dev group includes among them. An extra that names the project itself
    (`app[test]`) is followed one level."""
    data = load_toml(root / "pyproject.toml")
    own = _req_name(str(table(data, "project").get("name") or ""))
    extras = table(data, "project", "optional-dependencies")
    groups = table(data, "dependency-groups")
    seen: set[str] = set()
    listed = [r for g in synced_groups(data) for r in group_requirements(groups, g, seen)]
    listed += _requirements(table(data, "tool", "uv").get("dev-dependencies"))
    have = {_req_name(r) for r in listed}
    wanted: dict[str, tuple[str, str]] = {}

    def take(req: str, source: str, follow: bool) -> None:
        name = _req_name(req)
        if not name or name in have or name in wanted:
            return
        if name != own:
            wanted[name] = (req, source)
            return
        inner = re.search(r"\[([^\]]*)\]", req) if follow else None
        for extra in (e.strip() for e in (inner.group(1).split(",") if inner else [])):
            for sub in _requirements(extras.get(extra)):
                take(sub, f"[project.optional-dependencies] {extra}", False)

    for key in TEST_EXTRAS:
        for req in _requirements(extras.get(key)):
            take(req, f"[project.optional-dependencies] {key}", True)
        if key != "dev":
            for req in group_requirements(groups, key):
                take(req, f"[dependency-groups] {key}", True)
    for name in STANDARD_DEV:
        take(name, "the standard", False)
    return list(wanted.values())


def uv_env() -> dict[str, str]:
    """This environment without a virtualenv of its own: uv works on the repo's .venv."""
    return {
        k: v for k, v in os.environ.items() if k not in ("VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT")
    }


def pin_by_build(root: Path, env: dict[str, str]) -> tuple[str | None, list[str], list[str]]:
    """(the X.Y that builds the committed state, each failure first, the candidate's sources):
    python_candidates tried in turn with `uv sync` in a scratch clone, as P1 does. The repo
    and its own .venv are never touched."""
    tmp = Path(tempfile.mkdtemp(prefix="project-init-pin-"))
    try:
        clone = tmp / "clone"
        done = run(
            ["git", "clone", "--no-local", "-q", str(root), str(clone)], env=git_env(), timeout=300
        )
        if done.code != 0:
            return None, [f"git clone failed: {one_line(done.err.strip())[-200:]}"], []
        candidates = python_candidates(clone)
        built, failures = sync_with_python(clone, candidates, env, tmp)
        hit = next((c for c in candidates if c.version == built), None)
        return built, failures, hit.sources if hit else [UV_DEFAULT]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def uv_in(root: Path, *args: str, env: dict[str, str]) -> Result:
    """uv on the repo, started from the home folder: a mise shim refuses to run under the repo's
    own mise.toml while it is untrusted (SKILL.md, scripts/init.py)."""
    return run(["uv", "--directory", str(root), *args], cwd=Path.home(), env=env, timeout=900)


def cmd_prepare(args: argparse.Namespace) -> int:
    root = repo_root(args.repo)
    if not (root / "pyproject.toml").is_file():
        raise Refusal(
            f"prepare refused: {no_pack(root)}; P0 stops such a repo "
            "(v3 ships the Python pack only)"
        )
    problem = toml_problem(root / "pyproject.toml")
    if problem:
        raise Refusal(f"pyproject.toml does not parse ({problem}); fix it, then re-run")
    if is_git_root(root) and has_commits(root):
        default = detect_default_branch(root, load_toml(root / MANIFEST))
        if git_out(root, "symbolic-ref", "-q", "--short", "HEAD") == default:
            raise Refusal(
                f"prepare refused: HEAD is on {default}. P4 changes pyproject.toml and uv.lock on "
                "plan/project-init: `git switch -c plan/project-init` first"
            )
    wanted = args.python
    if wanted is not None and not PY_VERSION.match(wanted):
        raise UsageError(f"--python {wanted!r}: give a version such as 3.12")
    pin = python_pin(root)
    spec = requires_python(root)
    if wanted and pin and wanted != pin:
        raise UsageError(f"--python {wanted}: the repo pins {pin} in .python-version already")
    if wanted and not pin and not spec_allows(spec, wanted):
        raise UsageError(f"--python {wanted}: requires-python {spec} does not allow it")
    adds = dev_additions(root)
    sources = ", ".join(dict.fromkeys(source for _, source in adds))
    add = ["add", "--dev", "-q", *(req for req, _ in adds)]
    env = uv_env()

    if args.dry_run:
        print(f"prepare --dry-run: {project_name(root)}; nothing runs")
        if pin:
            print(label("python") + f".python-version {pin} (the repo's own; kept)")
        elif wanted:
            print(label("python") + f"write .python-version {wanted} (--python)")
        else:
            print(
                label("python") + f"try {candidates_text(python_candidates(root))} in a scratch "
                "clone; write the first that builds to .python-version"
            )
        shown = shlex.join(["uv", *add[:2], *add[3:]]) if adds else "nothing to add"
        print(label("dev deps") + shown + (f" ({sources})" if adds else ""))
        print(label("lock") + "uv lock --check, else uv lock")
        print(label("sync") + "uv sync --locked")
        return 0

    if pin:  # 1. the pin, before any uv add or sync
        print(label("python") + f".python-version {pin} (the repo's own)")
    else:
        if wanted:
            version, how = wanted, "--python"
        else:
            built, failures, found_in = pin_by_build(root, env)
            if not built:
                raise Refusal(
                    "prepare: no Python version builds the committed state ("
                    + " | ".join(failures)
                    + "). Fix the build, or pass --python X.Y; nothing written"
                )
            tried = f"; failed first: {' | '.join(failures)}" if failures else ""
            version, how = built, f"it builds; from {', '.join(found_in)}{tried}"
        install(root, ".python-version", f"{version}\n".encode(), 0o644)
        print(label("python") + f".python-version {version} written ({how})")
    if adds:  # 2. the dev group: the standard's tools and the project's own test deps
        result = uv_in(root, *add, env=env)
        if result.code != 0:
            raise Refusal(f"prepare: uv add --dev failed: {uv_failure(result)}")
        print(label("dev deps") + shlex.join(["uv", *add[:2], *add[3:]]) + f" ({sources})")
    else:
        print(label("dev deps") + "the dev group already holds them")
    if uv_in(root, "lock", "--check", "-q", env=env).code == 0:  # 3. D3: the lock ships in P7
        print(label("lock") + "uv.lock is current")
    else:
        result = uv_in(root, "lock", "-q", env=env)
        if result.code != 0:
            raise Refusal(f"prepare: uv lock failed: {uv_failure(result)}")
        print(label("lock") + "uv.lock written (uv lock)")
    result = uv_in(root, "sync", "--locked", "-q", env=env)  # 4. the venv render's baselines use
    if result.code != 0:
        raise Refusal(f"prepare: uv sync --locked failed: {uv_failure(result)}. P4 stops here")
    print(label("sync") + f"uv sync --locked: .venv on Python {venv_python(root) or '?'}")
    return 0


# ---------------------------------------------------------------------------------------------
# TOML text editing (stdlib has a reader only): merge pyproject-additions key by key


@dataclass
class TomlTable:
    name: tuple[str, ...]
    header: int  # line index of the header, -1 for the root
    end: int  # exclusive: the next header line or len(lines)
    last: int  # last line of the last key/value, or the header
    keys: dict[str, tuple[int, int]]  # key -> (first line, last line) of the value


def _split_key(raw: str) -> tuple[str, ...]:
    parts: list[str] = []
    for token in re.findall(r'"(?:[^"\\]|\\.)*"|\'[^\']*\'|[^.\s]+', raw):
        parts.append(token[1:-1] if token[:1] in "\"'" else token)
    return tuple(parts)


def scan_toml(lines: list[str]) -> tuple[list[bool], list[int | None]]:
    """(top, comment column) per line: top = the line starts outside any value or string."""
    top: list[bool] = []
    comments: list[int | None] = []
    depth = 0
    in_ml: str | None = None
    for line in lines:
        top.append(depth == 0 and in_ml is None)
        comment: int | None = None
        i = 0
        while i < len(line):
            if in_ml:
                if in_ml == '"""' and line[i] == "\\":
                    i += 2
                    continue
                if line.startswith(in_ml, i):
                    i += 3
                    in_ml = None
                    continue
                i += 1
                continue
            ch = line[i]
            if ch == "#":
                comment = i
                break
            if line.startswith('"""', i) or line.startswith("'''", i):
                in_ml = line[i : i + 3]
                i += 3
                continue
            if ch in "\"'":
                j = i + 1
                while j < len(line) and line[j] != ch:
                    j += 2 if ch == '"' and line[j] == "\\" else 1
                i = j + 1
                continue
            if ch in "[{":
                depth += 1
            elif ch in "]}":
                depth -= 1
            i += 1
        comments.append(comment)
    return top, comments


HEADER = re.compile(r"^\s*\[(\[)?\s*([^\[\]]+?)\s*\](\])?\s*(#.*)?$")
KEYLINE = re.compile(
    r"""^\s*((?:"(?:[^"\\]|\\.)*"|'[^']*'|[A-Za-z0-9_.-]+)(?:\s*\.\s*(?:"(?:[^"\\]|\\.)*"|'[^']*'|[A-Za-z0-9_-]+))*)\s*="""
)


def toml_tables(lines: list[str]) -> list[TomlTable]:
    top, _ = scan_toml(lines)
    tables = [TomlTable((), -1, len(lines), -1, {})]
    current = tables[0]
    i = 0
    while i < len(lines):
        if not top[i]:
            i += 1
            continue
        header = HEADER.match(lines[i])
        if header:
            current.end = i
            name = _split_key(header.group(2))
            if header.group(1):  # [[array.of.tables]]: kept apart from a [table] of that name
                name = ("[[", *name)
            current = TomlTable(name, i, len(lines), i, {})
            tables.append(current)
            i += 1
            continue
        key = KEYLINE.match(lines[i])
        if key:
            j = i + 1
            while j < len(lines) and not top[j]:
                j += 1
            current.keys[".".join(_split_key(key.group(1)))] = (i, j - 1)
            current.last = j - 1
            i = j
            continue
        i += 1
    return tables


def toml_str(value: str) -> str:
    out = ['"']
    for ch in value:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\r":
            out.append("\\r")
        elif ord(ch) < 0x20 or ord(ch) == 0x7F:
            out.append(f"\\u{ord(ch):04x}")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def toml_key(key: str) -> str:
    return key if re.fullmatch(r"[A-Za-z0-9_-]+", key) else toml_str(key)


def toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return repr(value)
    if isinstance(value, str):
        return toml_str(value)
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, list):
        return "[" + ", ".join(toml_value(v) for v in value) + "]"
    if isinstance(value, dict):
        inner = ", ".join(f"{toml_key(str(k))} = {toml_value(v)}" for k, v in value.items())
        return "{ " + inner + " }" if inner else "{}"
    raise TypeError(f"cannot write {type(value).__name__} to TOML")


def _format_list(key_text: str, items: list[object], indent: str = "  ") -> list[str]:
    one = f"{key_text} = {toml_value(items)}"
    if len(one) <= 100:
        return [one]
    return [f"{key_text} = ["] + [f"{indent}{toml_value(v)}," for v in items] + ["]"]


def split_lines(text: str) -> tuple[list[str], str]:
    """(lines without their endings, the file's newline: the more common of \\r\\n and \\n).
    Only those two end a line; str.splitlines() would also split inside a TOML string that holds
    U+2028 or a form feed."""
    crlf = text.count("\r\n")
    nl = "\r\n" if crlf and crlf >= text.count("\n") - crlf else "\n"
    lines = text.replace("\r\n", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines, nl


def _comment_block(lines: list[str], index: int) -> list[str]:
    """The contiguous comment lines directly above lines[index]."""
    start = index
    while start > 0 and lines[start - 1].lstrip().startswith("#"):
        start -= 1
    return lines[start:index]


def _addopts_missing(current: str, wanted: str) -> list[str]:
    have = shlex.split(current)
    want = shlex.split(wanted)
    missing: list[str] = []
    i = 0
    while i < len(want):
        flag = want[i]
        if flag in ("-p", "-m", "-k", "-W", "-o") and i + 1 < len(want):
            pair = [flag, want[i + 1]]
            present = any(have[j : j + 2] == pair for j in range(len(have)))
            present = present or f"{flag}{want[i + 1]}" in have
            missing += [] if present else pair
            i += 2
            continue
        if flag not in have:
            missing.append(flag)
        i += 1
    return missing


PYTEST_INI = ("tool", "pytest", "ini_options")
PYTEST_NATIVE = ("tool", "pytest")


def _marker_name(marker: str) -> str:
    return re.split(r"[:(]", marker, maxsplit=1)[0].strip()


def merge_pyproject(current: str, additions: str, description: str | None) -> str:
    """pyproject-additions, merged key by key: a scalar the project sets is kept, a list gains
    the items it lacks (markers by name), pytest addopts gains the flags it lacks, and
    [tool.git-cliff] is replaced whole. Raises Refusal when a key sits where text edits cannot
    reach it (inline tables, dotted keys) or when the project's file does not parse."""
    try:
        cur = parse_toml(current)
    except ValueError as exc:
        raise Refusal(f"pyproject.toml does not parse ({exc}); fix it, then re-run") from exc
    add = parse_toml(additions)
    lines, newline = split_lines(current)
    tlines, _ = split_lines(additions)
    tables = {t.name: t for t in toml_tables(lines)}
    ttables = toml_tables(tlines)
    _, tcomments = scan_toml(tlines)
    edits: list[tuple[int, int, list[str]]] = []
    appended: list[str] = []
    problems: list[str] = []

    def rewrite(t: TomlTable, key: str, new_value_lines: list[str]) -> None:
        first, last = t.keys[key]
        _, comments = scan_toml(lines)
        col = comments[last]
        tail = lines[last][col:] if col is not None else ""  # the comment after the value
        new = list(new_value_lines)
        if tail:
            new[-1] = f"{new[-1]}   {tail.strip()}"
        indent = re.match(r"^\s*", lines[first])
        new[0] = (indent.group(0) if indent else "") + new[0].lstrip()
        edits.append((first, last + 1, new))

    def append_items(t: TomlTable, key: str, items: list[object], note: str = "") -> None:
        """Add items to an array where it is written, keeping its layout, quoting and
        comments: before the `]` of a one-line array, or as new lines above a `]` that closes a
        multi-line one (in the indent of its items). note: the template line's comment, which
        replaces a one-line array's own comment when the array now holds just the template's
        items (the old comment explains only the items it had)."""
        first, last = t.keys[key]
        _, comments = scan_toml(lines)

        def code(i: int) -> str:
            col = comments[i]
            return (lines[i] if col is None else lines[i][:col]).rstrip()

        shown = [toml_value(v) for v in items]
        if first == last and code(first).endswith("]"):
            head = code(first)[:-1].rstrip()
            joiner = "" if head.endswith("[") else " " if head.endswith(",") else ", "
            rest = lines[first][len(code(first)) :]
            col = comments[first]
            if note and col is not None:
                rest = lines[first][len(code(first)) : col] + note
            edits.append((first, first + 1, [f"{head}{joiner}{', '.join(shown)}]{rest}"]))
            return
        if first < last and code(last).lstrip().startswith("]"):
            body = [i for i in range(first + 1, last) if code(i).strip()]
            indent = re.match(r"^\s*", lines[body[0]]) if body else None
            pad = indent.group(0) if indent else "    "
            prev = body[-1] if body else first
            if not code(prev).endswith((",", "[")):
                fixed = code(prev) + "," + lines[prev][len(code(prev)) :]
                edits.append((prev, prev + 1, [fixed]))
            edits.append((last, last, [f"{pad}{item}," for item in shown]))
            return
        existing = table(cur, *t.name).get(key)
        whole = [*existing, *items] if isinstance(existing, list) else list(items)
        rewrite(t, key, _format_list(toml_key(key), whole))

    # pytest 9 reads native TOML from [tool.pytest] and refuses to start when [tool.pytest] and
    # [tool.pytest.ini_options] are both set: a project already on the native table gets the
    # template's pytest keys there, as native lists, and never an ini_options table
    pytest_have = table(cur, *PYTEST_NATIVE)
    native = sorted(k for k in pytest_have if k != "ini_options")
    if native and "ini_options" in pytest_have:
        raise Refusal(
            "pyproject.toml sets both [tool.pytest] (native) and [tool.pytest.ini_options]; "
            "pytest 9 refuses to start with both. Move one into the other, then re-run"
        )

    for ttable in ttables:
        name = ttable.name
        if not name or name[:2] == ("tool", "git-cliff"):
            continue
        wanted = table(add, *name)
        as_native = name == PYTEST_INI and bool(native)
        if as_native:
            name = PYTEST_NATIVE
            wanted = {
                k: shlex.split(v) if k == "addopts" and isinstance(v, str) else v
                for k, v in wanted.items()
            }
        have = table(cur, *name)
        target = tables.get(name)
        if as_native and target is None:
            problems.append(
                "[tool.pytest] is written as dotted keys: add addopts and the spec marker to it "
                "by hand"
            )
            continue
        missing_lines: list[str] = []
        for key, (tfirst, tlast) in ttable.keys.items():
            value = wanted.get(key)
            if key not in have:
                if as_native:  # the template's lines are INI strings: write the native form
                    missing_lines += (
                        _format_list(toml_key(key), value)
                        if isinstance(value, list)
                        else [f"{toml_key(key)} = {toml_value(value)}"]
                    )
                    continue
                missing_lines += _comment_block(tlines, tfirst) + tlines[tfirst : tlast + 1]
                continue
            existing = have[key]
            key_text = toml_key(key)
            if target is None or key not in target.keys:
                if (
                    isinstance(value, list)
                    and isinstance(existing, list)
                    and any(v not in existing for v in value)
                ):
                    problems.append(f"[{'.'.join(name)}] {key}: add {value} by hand")
                continue
            if name in (PYTEST_INI, PYTEST_NATIVE) and key == "addopts":
                items = value if isinstance(value, list) else []
                want = value if isinstance(value, str) else shlex.join(str(v) for v in items)
                if isinstance(existing, str):
                    try:
                        have_items: list[object] = list(shlex.split(existing))
                    except ValueError:
                        where = ".".join(name)
                        problems.append(f"[{where}] addopts {existing!r} does not split")
                        continue
                if isinstance(existing, str) and as_native:
                    # pytest 9 reads a native addopts as a list only ("expects a list for type
                    # 'args'"): the string becomes that list, plus the flags it lacks
                    extra = _addopts_missing(existing, want)
                    rewrite(target, key, _format_list(key_text, [*have_items, *extra]))
                elif isinstance(existing, str):
                    extra = _addopts_missing(existing, want)
                    if extra:
                        rewrite(
                            target, key, [f"{key_text} = {toml_str(' '.join([existing, *extra]))}"]
                        )
                elif isinstance(existing, list):
                    extra = _addopts_missing(shlex.join(str(x) for x in existing), want)
                    if extra:
                        append_items(target, key, list(extra))
                continue
            if key == "markers" and isinstance(value, list) and isinstance(existing, str):
                # markers written as one string of lines (INI style): a list of those lines,
                # plus the markers it lacks; a native table always gets the list (pytest 9)
                have_markers: list[object] = [m.strip() for m in existing.splitlines() if m.strip()]
                names = {_marker_name(str(m)) for m in have_markers}
                extra_items = [v for v in value if _marker_name(str(v)) not in names]
                if extra_items or as_native:
                    rewrite(target, key, _format_list(key_text, [*have_markers, *extra_items]))
                continue
            if isinstance(value, list) and isinstance(existing, list):
                if key == "markers":
                    names = {_marker_name(str(m)) for m in existing}
                    extra_items = [v for v in value if _marker_name(str(v)) not in names]
                else:
                    extra_items = [v for v in value if v not in existing]
                if extra_items:
                    col = tcomments[tlast]
                    standard = all(v in value for v in existing)  # now the template's list
                    note = tlines[tlast][col:].strip() if col is not None and standard else ""
                    append_items(target, key, extra_items, note)
        if not missing_lines:
            continue
        if target is not None:
            at = target.last + 1
            if name == RUFF_IGNORES:  # a new row goes above the baseline, never into it
                at = next(
                    (
                        i
                        for i in range(target.header + 1, target.last + 1)
                        if lines[i].lstrip().startswith("#") and BASELINE_MARK in lines[i]
                    ),
                    at,
                )
            edits.append((at, at, missing_lines))
        else:
            above = _comment_block(tlines, ttable.header)
            appended += ["", *above, tlines[ttable.header], *missing_lines]

    if description is not None:
        project = tables.get(("project",))
        if project is None:
            problems.append("[project] is missing: cannot set the description")
        elif "description" in project.keys:
            rewrite(project, "description", [f"description = {toml_str(description)}"])
        else:
            edits.append(
                (project.last + 1, project.last + 1, [f"description = {toml_str(description)}"])
            )

    want_cliff = table(add, "tool", "git-cliff")
    if want_cliff and table(cur, "tool", "git-cliff") != want_cliff:
        mine = [t for t in tables.values() if t.name[:2] == ("tool", "git-cliff")]
        for index, t in enumerate(mine):
            start = t.header
            if index == 0:
                start -= len(_comment_block(lines, t.header))
            stop = t.last + 1
            while stop < t.end and not lines[stop].strip():
                stop += 1
            edits.append((start, stop, []))
        theirs = [t for t in ttables if t.name[:2] == ("tool", "git-cliff")]
        start = theirs[0].header - len(_comment_block(tlines, theirs[0].header))
        appended += ["", *tlines[start : theirs[-1].last + 1]]

    if problems:
        raise Refusal("pyproject.toml: " + "; ".join(problems))
    for start, stop, new in sorted(edits, key=lambda e: (e[0], e[1]), reverse=True):
        lines[start:stop] = new
    while appended and lines and not lines[-1].strip() and not appended[0].strip():
        appended.pop(0)
    text = newline.join(lines + appended).rstrip("\r\n") + newline
    try:
        parse_toml(text)
    except ValueError as exc:
        raise Refusal(f"pyproject.toml: the merge would not parse ({exc}); merge by hand") from exc
    return text


def merge_lines(current: str | None, template: str, gitignore: bool) -> str:
    """Append the template's missing entries (a trailing / does not matter). For .gitignore,
    appending `.env.*` also appends `!.env.example` after it, so the contract stays tracked."""
    if current is None:
        return template
    have = {
        ln.strip().rstrip("/")
        for ln in current.splitlines()
        if ln.strip() and not ln.lstrip().startswith("#")
    }
    entries = [
        ln.strip() for ln in template.splitlines() if ln.strip() and not ln.lstrip().startswith("#")
    ]
    missing = [e for e in entries if e.rstrip("/") not in have]
    if gitignore and ".env.*" in missing and "!.env.example" not in missing:
        missing.insert(missing.index(".env.*") + 1, "!.env.example")
    if not missing:
        return current
    lines, nl = split_lines(current)  # a CRLF file gets CRLF lines
    header = next((i for i, ln in enumerate(lines) if ln.startswith(STANDARD_BLOCK)), None)
    if header is not None:
        # the block is there already (a line was deleted from it, and --force-file restores
        # it): the entry goes back at the end of that block, under the one header
        end = header + 1
        while end < len(lines) and lines[end].strip():
            end += 1
        lines[end:end] = missing
        return nl.join(lines) + nl
    out = current if not current or current.endswith("\n") else current + nl
    if out.strip():
        out += nl
    return out + nl.join([STANDARD_BLOCK, *missing]) + nl


# ---------------------------------------------------------------------------------------------
# P4 render


@dataclass
class Planned:
    dest: str
    # text | copy | lines | pyproject | region (README.md's quickstart region) | seed (written
    # once, when missing, then the project's own: [seeded], never [generated]) | link (a
    # symlink render owns; content is its target)
    kind: str
    source: str
    content: bytes
    mode: int
    current: bytes | None = None
    status: str = ""
    link: str | None = None  # the target when dest is a symlink: read through, never written
    # what [generated] records for dest, and the same measure of what is on disk now: the whole
    # file's sha256, except for a region, whose hash covers the tool-owned region only
    record: str = ""
    current_record: str | None = None

    def __post_init__(self) -> None:
        if not self.record:
            self.record = sha256(self.content)
        if self.kind != "region" and self.current is not None and self.current_record is None:
            self.current_record = sha256(self.current)


MERGED_KINDS = frozenset({"lines", "pyproject", "env"})
# merged into the project's own file without asking the first time: nothing of the project's is
# dropped. The env contract is not among them: a project's own .env.example is asked about.
FIRST_MERGE_SAFE = frozenset({"lines", "pyproject"})
HELD_STATUSES = frozenset({"customized", "symlink"})  # left alone unless --force-file
AGENTS_LINK = (".agents/skills/sdd", "../../.claude/skills/sdd")  # (dest, target), --agents-symlink


@dataclass
class Target:
    source: str  # a path under TEMPLATES, or a label when content is given
    dest: str
    kind: str
    mode: int
    content: bytes | None = None  # computed content: no template file is read


def template_targets(
    ci_file: str | None, tier: str = "solo", plugin: str = "tests/conftest.py"
) -> list[Target]:
    """The files render plans from ../templates, before the ones computed from the repo (the
    history-scan and lint-debt seeds, the per-signal skills, the .agents link). plugin: where
    the spec plugin goes (spec_plugin_dest)."""
    # AGENTS.md and the README quickstart are the front door: P6 renders them (--front-door)
    targets = [
        Target("mise.python.toml", "mise.toml", "text", 0o644),
        Target("settings.json", ".claude/settings.json", "copy", 0o644),
        Target("env.example", ".env.example", "env", 0o644),  # rows kept as the project wrote them
        Target("gitignore-extra", ".gitignore", "lines", 0o644),
        Target("gitattributes", ".gitattributes", "lines", 0o644),
        Target("editorconfig", ".editorconfig", "copy", 0o644),
        Target("gitleaks.toml", ".gitleaks.toml", "copy", 0o644),
        Target("scripts/project.py", "scripts/project.py", "copy", 0o755),
        Target("tests/conftest.py", plugin, "copy", 0o644),
        Target("project_memory/README.md", "project_memory/README.md", "text", 0o644),
        Target("project_memory/lessons.md", "project_memory/lessons.md", "seed", 0o644),
        Target("project_memory/decisions/.gitkeep", DECISIONS_KEEP, "seed", 0o644),
        Target("pyproject-additions.toml", "pyproject.toml", "pyproject", 0o644),
        Target("specs-README.md", "specs/README.md", "text", 0o644),
    ]
    if tier == "team":  # D9: the team tier only
        targets += [
            Target("team.md", "project_memory/team.md", "seed", 0o644),
            Target("CODEOWNERS.tmpl", ".github/CODEOWNERS", "text", 0o644),
            Target("pull_request_template.md", ".github/pull_request_template.md", "copy", 0o644),
        ]
    if ci_file:
        targets.append(Target("ci.yml", f".github/workflows/{ci_file}", "text", 0o644))
    for hook in sorted((TEMPLATES / "githooks").iterdir()):
        if hook.is_file():
            kind = "text" if PLACEHOLDER.search(read_text(hook) or "") else "copy"
            targets.append(Target(f"githooks/{hook.name}", f".githooks/{hook.name}", kind, 0o755))
    sdd = TEMPLATES / "skills" / "sdd"
    for path in sorted(sdd.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            rel = rel_posix(path, sdd)
            targets.append(Target(f"skills/sdd/{rel}", f".claude/skills/sdd/{rel}", "copy", 0o644))
    return targets


DECISIONS_DIR = "project_memory/decisions"
DECISIONS_KEEP = f"{DECISIONS_DIR}/.gitkeep"


def seed_satisfied(root: Path, dest: str) -> bool:
    """A seed is written only when nothing stands in for it: the file itself, or for the
    decisions/ placeholder, any file in that folder (the first ADR makes it redundant)."""
    path = root / dest
    if dest == DECISIONS_KEEP:
        folder = path.parent
        return folder.is_dir() and any(folder.iterdir())
    return path.exists() or path.is_symlink()


# ---------------------------------------------------------------------------------------------
# the team tier (D9): team.md seed, CODEOWNERS generated from its Ownership table

OWNER = re.compile(r"@[A-Za-z0-9][A-Za-z0-9-]*(?:/[A-Za-z0-9._-]+)?|[^@\s<>()]+@[^@\s<>()]+\.\w+")
OWNED_PATH = re.compile(r"[^\s{}<>`|]+")
NO_OWNER = "(the lead's @login)"


def team_values(root: Path) -> dict[str, str]:
    """TEAM_ROWS and LEAD_OWNER for the team.md seed: the human authors of the last 6 months,
    the one running project-init (git user.email) as Lead, else the newest author. A login is
    filled only where a noreply address names it; the rest is the human's to fill."""
    me = (git_out(root, "config", "--get", "user.email") or "").strip().lower()
    people: list[tuple[str, str, str | None]] = []
    for shown in human_authors(root):
        match = re.match(r"^(.*) <([^<>]*)>$", shown)
        name, email = (match.group(1), match.group(2)) if match else (shown, "")
        login = NOREPLY_LOGIN.match(email.strip().lower())
        people.append((name, email.strip().lower(), login.group(1) if login else None))
    lead = next((i for i, person in enumerate(people) if me and person[1] == me), 0)
    if people:  # the Lead's row first, the Contributors after it in author order
        people.insert(0, people.pop(lead))
    rows: list[str] = []
    for i, (name, _, login) in enumerate(people):
        cell = one_line(name).replace("|", "\\|")
        rows.append(
            f"| {cell} | {'Lead' if i == 0 else 'Contributor'} | "
            f"{'@' + login if login else '(unknown)'} |"
        )
    lead_login = people[0][2] if people else None
    return {
        "TEAM_ROWS": "\n".join(rows) or "| (you) | Lead | (unknown) |",
        "LEAD_OWNER": f"@{lead_login}" if lead_login else NO_OWNER,
    }


def ownership(text: str) -> list[tuple[str, list[str]]]:
    """(path, owners) from team.md's Ownership table: rows whose path is one CODEOWNERS
    pattern and that name at least one owner (@login, @org/team or an email)."""
    rows: list[tuple[str, list[str]]] = []
    section = False
    header: list[str] | None = None
    for line in text.splitlines():
        heading = re.match(r"^\s{0,3}#{1,6}\s+(.*)$", line)
        if heading:
            section = heading.group(1).strip().lower().startswith("ownership")
            header = None
            continue
        stripped = line.strip()
        if not section or not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if all(re.fullmatch(r":?-+:?", c) for c in cells if c):
            continue
        at_path = next((i for i, c in enumerate(header) if c == "path"), None)
        at_owner = next((i for i, c in enumerate(header) if c.startswith("owner")), None)
        if at_path is None or at_owner is None or max(at_path, at_owner) >= len(cells):
            continue
        path = cells[at_path].strip("` ")
        owners = [
            t for t in re.split(r"[\s,]+", cells[at_owner].replace("`", "")) if OWNER.fullmatch(t)
        ]
        if OWNED_PATH.fullmatch(path) and owners:
            rows.append((path, owners))
    return rows


def codeowners_rows(team_text: str) -> str:
    rows = [f"{path} {' '.join(owners)}" for path, owners in ownership(team_text)]
    if rows:
        return "\n".join(rows)
    return (
        "# No owner yet: fill the Ownership table in project_memory/team.md, then re-run "
        "project-init."
    )


# ---------------------------------------------------------------------------------------------
# per-signal skills: only with file evidence, each with the dry-run P5 runs (design 6.P4)


@dataclass
class SignalSkill:
    name: str  # its folder under .claude/skills/; never plain `run` (the bundled /run)
    template: str  # its folder under templates/skills-per-signal/
    values: dict[str, str]
    command: str  # the dry-run, as P5 records it
    argv: list[str]  # "{TMP}" stands for a scratch folder P5 makes and removes
    cwd: str  # the repo-relative folder the dry-run runs in


def _evidence_dir(evidence: str) -> str:
    """The folder an evidence string names ("backend/pyproject.toml: fastapi" -> "backend")."""
    where = evidence.split(":", 1)[0].split(" ", 1)[0]
    return where.rsplit("/", 1)[0] if "/" in where.rstrip("/") else ""


# the programs that start a server: what the run-<name> skill names when `start` is a stub
SERVER_PROGRAMS = frozenset(
    {"uvicorn", "gunicorn", "hypercorn", "granian", "daphne", "dagster-webserver", "dagster-daemon"}
)
SERVER_SUBCOMMANDS = {"fastapi": ("run", "dev"), "flask": ("run",), "litestar": ("run",)}
SERVER_SUBCOMMANDS |= {"streamlit": ("run",), "dagster": ("dev",)}
RUNNERS = (("uv", "run"), ("poetry", "run"), ("pipenv", "run"), ("pdm", "run"), ("hatch", "run"))


def launches_server(command: str) -> bool:
    """True when one of the shell commands in command starts a server: uvicorn and its kin, a
    framework's run or dev, `python -m <pkg>.server|api|app|web`, `manage.py runserver`, also
    behind `uv run`. Words inside an echo or a compose service name never count."""
    for part in re.split(r"&&|\|\||;|\|", command):
        try:
            tokens = shlex.split(part)
        except ValueError:
            tokens = part.split()
        while tokens and (ASSIGN.match(tokens[0]) or tokens[0] in ("exec", "env", "@", "-")):
            tokens = tokens[1:]
        for runner in RUNNERS:
            if tuple(tokens[:2]) == runner:
                tokens = tokens[2:]
                while tokens and tokens[0].startswith("-"):
                    tokens = tokens[1:]
        if not tokens:
            continue
        program, rest = PurePosixPath(tokens[0].lstrip("@-")).name, tokens[1:]
        if program in SERVER_PROGRAMS:
            return True
        if rest[:1] and rest[0] in SERVER_SUBCOMMANDS.get(program, ()):
            return True
        if program in ("python", "python3") and "-m" in rest[:-1]:
            module = rest[rest.index("-m") + 1]
            if re.search(r"server|api|app|web", module):
                return True
        if program in ("python", "python3") and rest[:1] and rest[0].endswith("manage.py"):
            return "runserver" in rest
    return False


MAKE_TARGET = re.compile(r"^([A-Za-z0-9_.-]+)\s*:(?!=)")
SERVICE_COMMANDS_MAX = 8


def module_file(root: Path, module: str) -> Path | None:
    """The file of a dotted module in the repo: src/ layout, flat layout, or a package."""
    rel = module.replace(".", "/")
    for candidate in (f"src/{rel}.py", f"{rel}.py", f"src/{rel}/__init__.py", f"{rel}/__init__.py"):
        path = root / candidate
        if path.is_file() and not path.is_symlink():
            return path
    return None


def start_is_stub(root: Path, entry: str | None) -> bool:
    """True when the start command is a console script whose function only prints (its usage,
    a list of the real commands) and returns: orca's `orca` prints how to start its three
    services and exits 0. A function that calls anything but print, or branches, is no stub."""
    target = console_scripts(root).get(entry or "")
    if not target or ":" not in target:
        return False
    module, _, attr = target.partition(":")
    path = module_file(root, module.strip())
    try:
        tree = ast.parse(path.read_text(encoding="utf-8")) if path else None
    except (OSError, SyntaxError, ValueError):
        return False
    func = next(
        (
            node
            for node in (tree.body if tree else [])
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
            and node.name == attr.strip()
        ),
        None,
    )
    if func is None:
        return False
    body = func.body
    if body and isinstance(body[0], ast.Expr) and _literal_key(body[0].value) is not None:
        body = body[1:]  # the docstring
    printed = False
    for stmt in body:
        if isinstance(stmt, ast.Pass):
            continue
        if isinstance(stmt, ast.Return) and (
            stmt.value is None or isinstance(stmt.value, ast.Constant)
        ):
            continue
        call = stmt.value if isinstance(stmt, ast.Expr) else None
        if isinstance(call, ast.Call) and _dotted_tail(call.func) in ("print", "write"):
            printed = True
            continue
        return False
    return printed


def _compose_command(value: str, block: list[str]) -> str | None:
    """A compose `command:` as one shell line: a flow list, a block list or a plain string."""
    value = value.split(" #", 1)[0].strip()
    items: list[str] = []
    if value.startswith("["):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = [part.strip().strip("'\"") for part in value.strip("[]").split(",")]
        items = [str(item) for item in parsed] if isinstance(parsed, list) else []
    elif value:
        return value.strip("'\"")
    else:
        items = [item.strip().strip("'\"") for item in block]
    return shlex.join(items) if items else None


def compose_commands(path: Path) -> list[tuple[str, str]]:
    """(service, command) for each service of a compose file that sets `command:`."""
    found: list[tuple[str, str]] = []
    lines = (read_text(path) or "").splitlines()
    in_services = False
    service: str | None = None
    service_indent: int | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if indent == 0:
            in_services = stripped.startswith("services:")
            service, service_indent = None, None
            continue
        if not in_services:
            continue
        key = re.match(r"^([A-Za-z0-9_.-]+):\s*(?:#.*)?$", stripped)
        if key and (service_indent is None or indent <= service_indent):
            service, service_indent = key.group(1), indent
            continue
        if service is None or not stripped.startswith("command:"):
            continue
        block: list[str] = []
        for later in lines[index + 1 :]:
            if not later.strip().startswith("- ") or len(later) - len(later.lstrip()) <= indent:
                break
            block.append(later.strip()[2:])
        command = _compose_command(stripped[len("command:") :], block)
        if command:
            found.append((service, command))
    return found


def service_commands(root: Path, entry: str | None) -> list[tuple[str, str]]:
    """(command, where) for each command in the repo's compose files, Makefiles and console
    scripts that starts a server (launches_server)."""
    found: list[tuple[str, str]] = []
    for base in manifest_dirs(root):
        for pattern in COMPOSE_FILES:
            for path in sorted(base.glob(pattern)):
                if path.is_file() and not path.is_symlink():
                    rel = rel_posix(path, root)
                    for service, command in compose_commands(path):
                        if launches_server(command):
                            found.append((command, f"{rel}, service `{service}`"))
        for name in MAKEFILES:
            path = base / name
            if not path.is_file() or path.is_symlink():
                continue
            rel = rel_posix(path, root)
            target = None
            for line in (read_text(path) or "").splitlines():
                match = MAKE_TARGET.match(line)
                if match:
                    target = match.group(1)
                elif line.startswith("\t") and target and launches_server(line.strip()):
                    command = line.strip().lstrip("@-").strip()
                    found.append((command, f"{rel}, target `{target}`"))
    for name, value in console_scripts(root).items():
        if name != entry and re.search(r"server|api|app|web|serve", value):
            found.append((f"uv run --locked {name}", f"pyproject.toml [project.scripts]: {value}"))
    seen: set[str] = set()
    shown: list[tuple[str, str]] = []
    for command, where in found:
        if command in seen or "`" in command or CONTROL.search(command):
            continue
        seen.add(command)
        shown.append((command, where))
    return shown[:SERVICE_COMMANDS_MAX]


def run_skill_values(root: Path, slug: str, entry: str | None) -> dict[str, str]:
    """The run-<name> skill's text: what `mise run start` does, and, when start is a stub that
    prints usage and exits, the real service commands the repo names instead."""
    # render writes the skill before P5 runs: it says what P5 checks, never that it passed
    help_line = (
        "project-init's selftest runs `mise run start -- --help` and fails unless it exits 0"
    )
    if not start_is_stub(root, entry):
        line = f"`mise run start` starts it, and arguments go after `--`. {help_line}."
        return {"SERVICE": slug, "START_LINE": line, "SERVICE_COMMANDS": ""}
    line = (
        f"`mise run start` runs `{entry}`, which prints its usage and exits: it does not start "
        f"the service. {help_line}, which proves only that usage text."
    )
    commands = service_commands(root, entry)
    if commands:
        rows = "\n".join(f"- `{command}` ({where})" for command, where in commands)
        more = (
            "\n\nThe service commands this repo names (project-init found them in its files "
            "and never ran them; a compose command runs inside its container):\n\n" + rows
        )
    else:
        more = (
            "\n\nNo compose `command:`, Makefile recipe or console script in this repo runs a "
            "server project-init knows (uvicorn, gunicorn, `dagster dev`, `python -m <pkg>.server`,"
            " ...): the README says how the service starts."
        )
    return {"SERVICE": slug, "START_LINE": line, "SERVICE_COMMANDS": more}


def signal_skills(root: Path, entry: str | None = None) -> tuple[list[SignalSkill], list[str]]:
    """The per-signal skills this repo's files justify, and a note for each signal that gets
    none because no dry-run exists for its evidence. entry: the start command's program, which
    the run-<name> skill checks for a stub."""
    signals = detect_signals(root)
    skills: list[SignalSkill] = []
    notes: list[str] = []
    if "api" in signals:  # a service: run-<name>, verified by its start command's --help
        folder = _evidence_dir(signals["api"][0])
        slug = re.sub(r"[^a-z0-9]+", "-", (folder or project_name(root)).lower()).strip("-")
        slug = slug or "app"
        argv = ["mise", "run", "start", "--", "--help"]
        values = run_skill_values(root, slug, entry)
        skills.append(
            SignalSkill(f"run-{slug}", "run-service", values, shlex.join(argv), argv, ".")
        )
        if values["SERVICE_COMMANDS"]:
            notes.append(
                f"run-{slug}: `mise run start` runs {entry}, which only prints its usage; the "
                "skill says so and names the service commands the repo's files hold"
            )
    alembic = next((b for b in manifest_dirs(root) if (b / "alembic.ini").is_file()), None)
    if alembic is not None:
        where = "" if alembic == root else rel_posix(alembic, root)
        argv = ["mise", "x", "--", "uv", "run", "--locked", "alembic", "heads"]
        values = {"DB_CONFIG": f"{where}/alembic.ini" if where else "alembic.ini"}
        values["DB_DIR"] = f"{where}/" if where else "./"
        skills.append(
            SignalSkill("db", "db", values, "uv run --locked alembic heads", argv, where or ".")
        )
    elif "db" in signals:
        notes.append(
            "no db skill: no alembic.ini, so no dry-run to prove one (" + signals["db"][0] + ")"
        )
    wrangler = next(
        (
            (b, n)
            for b in manifest_dirs(root)
            for n in ("wrangler.toml", "wrangler.json", "wrangler.jsonc")
            if (b / n).is_file()
        ),
        None,
    )
    if wrangler is not None:
        base, config = wrangler
        where = "" if base == root else rel_posix(base, root)
        argv = ["npx", "--no-install", "wrangler", "deploy", "--dry-run", "--outdir", "{TMP}"]
        values = {"DEPLOY_CONFIG": f"{where}/{config}" if where else config}
        values["DEPLOY_DIR"] = f"{where}/" if where else "./"
        command = "npx --no-install wrangler deploy --dry-run --outdir $TMPDIR/wrangler"
        skills.append(SignalSkill("deploy", "deploy", values, command, argv, where or "."))
    elif "deploy" in signals:
        notes.append(
            "no deploy skill: only wrangler has a dry-run project-init can prove ("
            + ", ".join(signals["deploy"])
            + ")"
        )
    return skills, notes


# ---------------------------------------------------------------------------------------------
# brownfield baselines, taken once at adoption: ruff lint debt (N3) and history leaks


BASELINE_MARK = "project-init baseline: shrink only"
RUFF_IGNORES = ("tool", "ruff", "lint", "per-file-ignores")


def toml_dump(data: dict[str, object]) -> str:
    """A plain TOML document: scalars and arrays first, then one [table] per nested dict."""
    lines: list[str] = []

    def emit(prefix: list[str], body: dict[str, object]) -> None:
        leaves = {k: v for k, v in body.items() if not isinstance(v, dict)}
        subs = {k: v for k, v in body.items() if isinstance(v, dict)}
        if prefix and (leaves or not subs):
            lines.append("[" + ".".join(toml_key(p) for p in prefix) + "]")
        lines.extend(f"{toml_key(k)} = {toml_value(v)}" for k, v in leaves.items())
        for key, value in subs.items():
            emit([*prefix, key], value)

    emit([], data)
    return "\n".join(lines) + "\n"


def ruff_debt(root: Path, merged: str) -> tuple[dict[str, list[str]] | None, str]:
    """(file -> codes, summary) from `ruff check --output-format json` under the config the
    render writes, or (None, why) when it cannot run. The venv's ruff, from the `uv sync` P4
    runs before render; --no-cache, so --check writes nothing."""
    own = [n for n in ("ruff.toml", ".ruff.toml") if (root / n).is_file()]
    if own:
        return None, f"skipped: the project's ruff config is {own[0]}; add the baseline there"
    ruff = root / ".venv" / "bin" / "ruff"
    if not os.access(ruff, os.X_OK):
        return None, "skipped: no .venv/bin/ruff yet (P4 runs `uv sync` before render)"
    config = table(parse_toml(merged), "tool", "ruff")
    with tempfile.TemporaryDirectory(prefix="project-init-ruff-") as tmp:
        cfg = Path(tmp) / "ruff.toml"  # relative paths in a --config file resolve from the cwd
        cfg.write_text(toml_dump(config), encoding="utf-8")
        result = run(
            [str(ruff), "check", "--config", str(cfg), "--output-format", "json"]
            + ["--exit-zero", "--no-cache", "."],
            cwd=root,
            timeout=600,
        )
    if result.code != 0:
        last = (result.err.strip().splitlines() or ["?"])[-1][:200]
        return None, f"skipped: ruff check failed (exit {result.code}: {last})"
    try:
        data = json.loads(result.out or "[]")
    except json.JSONDecodeError as exc:
        return None, f"skipped: ruff's JSON did not parse ({exc})"
    found: dict[str, set[str]] = {}
    count = 0
    for item in data if isinstance(data, list) else []:
        code = item.get("code") if isinstance(item, dict) else None
        filename = item.get("filename") if isinstance(item, dict) else None
        if not isinstance(code, str) or not code or not isinstance(filename, str):
            continue  # a syntax error has no code: nothing to ignore
        try:
            rel = Path(filename).resolve().relative_to(root).as_posix()
        except ValueError:
            continue
        found.setdefault(rel, set()).add(code)
        count += 1
    if not found:
        return {}, "none: ruff check is clean"
    summary = f"{plural(count, 'finding')} in {plural(len(found), 'file')}"
    return {k: sorted(found[k]) for k in sorted(found)}, summary


def with_baseline(additions: str, debt: dict[str, list[str]]) -> str:
    """The pyproject additions with the lint debt as per-file-ignores rows, at the end of that
    table under the mark doctor checks (it fails when the block grows). A file at the repo root
    gets a `./` key (ruff_exclude_path): ruff matches a key with no folder against every file's
    name, so a bare `conftest.py` row would exempt each conftest.py in the repo."""
    if not debt:
        return additions
    lines, nl = split_lines(additions)
    ignores = next(t for t in toml_tables(lines) if t.name == RUFF_IGNORES)
    rows = [
        f"# {BASELINE_MARK}. The lint debt found at adoption (N3): fix a file's findings,",
        "# then delete its row. doctor fails when this block grows.",
    ]
    for path, codes in debt.items():
        rows += _format_list(toml_str(ruff_exclude_path(path)), list(codes), indent="    ")
    lines[ignores.last + 1 : ignores.last + 1] = rows
    return nl.join(lines) + nl


TY_BASELINE_MARK = "project-init ty baseline: shrink only"  # never contains BASELINE_MARK


def ty_debt(root: Path) -> tuple[list[str] | None, str]:
    """(the files ty flags, summary) from `ty check --output-format gitlab`, run the way
    `mise run types` runs it (the project's own config), or (None, why) when it cannot run.
    The venv's ty, from the `uv sync` P4 runs before render. ty 0.0.x exits 1 on a warning
    too, so every file with a diagnostic counts."""
    if (root / "ty.toml").is_file():
        return None, "skipped: the project's ty config is ty.toml; add the exclude there"
    ty = root / ".venv" / "bin" / "ty"
    if not os.access(ty, os.X_OK):
        return None, "skipped: no .venv/bin/ty yet (P4 runs `uv sync` before render)"
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT", "TY_OUTPUT_FORMAT")
    }
    result = run(
        [str(ty), "check", "--output-format", "gitlab", "--no-progress"],
        cwd=root,
        env=env,
        timeout=600,
    )
    if result.code == 0:
        return [], "none: ty check is clean"
    last = (result.err.strip().splitlines() or ["?"])[-1][:200]
    if result.code != 1:
        return None, f"skipped: ty check failed (exit {result.code}: {last})"
    try:
        data = json.loads(result.out or "[]")
    except json.JSONDecodeError as exc:
        return None, f"skipped: ty's JSON did not parse ({exc})"
    found: dict[str, int] = {}
    for item in data if isinstance(data, list) else []:
        where = item.get("location") if isinstance(item, dict) else None
        path = where.get("path") if isinstance(where, dict) else None
        if not isinstance(path, str) or not path:
            continue
        full = Path(os.path.normpath(root / path))
        if not full.is_relative_to(root) or full == root:
            continue
        rel = full.relative_to(root).as_posix()
        found[rel] = found.get(rel, 0) + 1
    if not found:
        return None, f"skipped: ty check exited 1 and named no file in the repo ({last})"
    summary = f"{plural(sum(found.values()), 'diagnostic')} in {plural(len(found), 'file')}"
    return sorted(found), summary


def with_ty_baseline(additions: str, files: list[str]) -> str:
    """The pyproject additions plus a [tool.ty.src] exclude of the files ty flagged at
    adoption, under its shrink-only mark, placed before [tool.pytest.ini_options]. ty has no
    per-file ignore (design Risk 8), so a flagged file leaves `ty check` whole."""
    if not files:
        return additions
    lines, nl = split_lines(additions)
    pytest_table = next(t for t in toml_tables(lines) if t.name == PYTEST_INI)
    at = pytest_table.header - len(_comment_block(lines, pytest_table.header))
    block = [
        "[tool.ty.src]",
        f"# {TY_BASELINE_MARK}. The type debt found at adoption (Risk 8): ty has no",
        "# per-file ignore, so each file below is left out of `ty check` whole. Fix a file's",
        "# diagnostics, then delete its line.",
        *_format_list("exclude", list(files), indent="    "),
        "",
    ]
    lines[at:at] = block
    return nl.join(lines) + nl


def ty_backlog_text(summary: str, files: list[str]) -> bytes:
    """The one backlog item for the type debt, in the backlog format of specs/README.md."""
    shown = files[:10]
    more = f", and {len(files) - len(shown)} more" if len(files) > len(shown) else ""
    lines = [
        "---",
        "status: open                                    # open | scheduled",
        "roadmap:                                        # the roadmap slug, once scheduled",
        "---",
        (
            "<!-- backlog item: an idea, spike finding or abandoned change that is not being "
            "built now. Deleted when its work starts or a replan drops it. No line cap. -->"
        ),
        "# Shrink the ty baseline",
        "",
        "## What",
        (
            f"The type debt found at adoption, {summary}, is left out of `ty check` by "
            f"`[tool.ty.src] exclude` in pyproject.toml, under `# {TY_BASELINE_MARK}`. Fix a "
            "file's diagnostics, then delete its line."
        ),
        "",
        "## Why",
        (
            "New files meet ty from day one. ty has no per-file ignore, so an excluded file is "
            "not checked at all until its line goes (design Risk 8)."
        ),
        "",
        "## Notes",
        "Excluded files: " + ", ".join(f"`{f}`" for f in shown) + more + ".",
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def history_leaks(root: Path, rules: bytes) -> tuple[list[str] | None, str]:
    """The fingerprints (commit:file:rule:line, never a value) of what the rendered leak rules
    find in git history, or (None, why) when gitleaks cannot run."""
    if not has_commits(root):
        return [], "none: no commits yet"
    argv = gitleaks_argv()
    if argv is None:
        return None, "skipped: gitleaks is not runnable (neither `gitleaks` nor `mise x`)"
    with tempfile.TemporaryDirectory(prefix="project-init-history-") as tmp:
        work = Path(tmp)  # the cwd: a .gitleaksignore of the repo's own must not apply
        (work / "gitleaks.toml").write_bytes(rules)
        report = work / "report.json"
        result = run(
            [*argv, "git", str(root), "-c", str(work / "gitleaks.toml"), "-f", "json"]
            + ["-r", str(report), "--redact", "--no-banner", "--exit-code", "3"]
            + ["--log-level", "error"],
            cwd=work,
            timeout=1800,
        )
        if result.code not in (0, 3):
            last = (result.err.strip().splitlines() or ["?"])[-1][:200]
            return None, f"skipped: gitleaks git failed (exit {result.code}: {last})"
        try:
            data = json.loads(report.read_text(encoding="utf-8") or "[]")
        except (OSError, json.JSONDecodeError) as exc:
            return None, f"skipped: the gitleaks report did not parse ({exc})"
    prints = sorted(
        {
            f["Fingerprint"]
            for f in (data if isinstance(data, list) else [])
            if isinstance(f, dict) and isinstance(f.get("Fingerprint"), str)
        }
    )
    if not prints:
        return [], "none: history is clean"
    return prints, f"{plural(len(prints), 'finding')} in history (.gitleaksignore)"


# the leak rules .gitleaks.toml adds for text that names the vault or a home folder: a finding
# of theirs is a path in a committed file, never a secret, and there is nothing to rotate
PATH_RULES = {"personal-path": "vault paths", "personal-home-path": "home folders"}
PATH_RULES |= {"wiki-link": "wiki-links"}


def fingerprint_rules(prints: list[str]) -> dict[str, int]:
    """rule -> findings, from commit:file:rule:line fingerprints (a file may hold a colon)."""
    counts: dict[str, int] = {}
    for fingerprint in prints:
        parts = fingerprint.rsplit(":", 2)
        if len(parts) == 3:
            counts[parts[1]] = counts.get(parts[1], 0) + 1
    return counts


def secret_rules(prints: list[str]) -> dict[str, int]:
    """The findings of rules that match secrets (every rule but PATH_RULES)."""
    return {r: n for r, n in fingerprint_rules(prints).items() if r not in PATH_RULES}


def leaks_note(prints: list[str]) -> str:
    """What render says about the history findings: rotate only when a secret rule hit."""
    counts = fingerprint_rules(prints)
    shown = ", ".join(f"{rule} {n}" for rule, n in sorted(counts.items()))
    head = (
        f"history already holds {plural(len(prints), 'finding')} of the leak rules ({shown}): "
        "each is fingerprinted in .gitleaksignore (rule and file, never a value); "
    )
    secrets_found = secret_rules(prints)
    paths = sum(n for r, n in counts.items() if r in PATH_RULES)
    kinds = [words for rule, words in PATH_RULES.items() if rule in counts]
    what = " and ".join([", ".join(kinds[:-1]), kinds[-1]] if len(kinds) > 1 else kinds)
    if not secrets_found:
        return head + f"they are {what} in committed files, not secrets: nothing to rotate"
    rules = ", ".join(sorted(secrets_found))
    tail = f"; the other {paths} are {what}, not secrets" if paths else ""
    return head + f"rotate the secrets among them (punch list: the {rules} findings){tail}"


def gitleaksignore_text(prints: list[str]) -> bytes:
    if secret_rules(prints):
        what = "# Each line is commit:file:rule:line, never a value. Rotate the secrets among them;"
    else:
        what = "# Each line is commit:file:rule:line: a vault or home path, not a secret;"
    head = [
        f"# project-init: what the leak rules found in git history at adoption ({today()}).",
        what,
        "# a line only goes away, and a new finding never joins this list (it fails verify).",
    ]
    return ("\n".join([*head, *prints]) + "\n").encode("utf-8")


def debt_backlog_text(summary: str, debt: dict[str, list[str]]) -> bytes:
    """The one backlog item for the lint debt (N3), in the backlog format of specs/README.md."""
    counts: dict[str, int] = {}
    for codes in debt.values():
        for code in codes:
            counts[code] = counts.get(code, 0) + 1
    top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
    lines = [
        "---",
        "status: open                                    # open | scheduled",
        "roadmap:                                        # the roadmap slug, once scheduled",
        "---",
        (
            "<!-- backlog item: an idea, spike finding or abandoned change that is not being "
            "built now. Deleted when its work starts or a replan drops it. No line cap. -->"
        ),
        "# Shrink the ruff baseline",
        "",
        "## What",
        (
            f"The lint debt found at adoption, {summary}, is ignored per file in pyproject.toml "
            f"under `# {BASELINE_MARK}`. Fix a file's findings, then delete its row."
        ),
        "",
        "## Why",
        "New code meets the full rule set from day one; doctor fails if the baseline grows (N3).",
        "",
        "## Notes",
        "Most common codes (files): " + ", ".join(f"{c} ({n})" for c, n in top) + ".",
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def fill(text: str, values: dict[str, str], flags: dict[str, bool | None]) -> tuple[str, set[str]]:
    """Conditional lines first ({IF_X}: dropped when false, the marker and an emptied trailing
    comment removed when true), then every {UPPER_SNAKE} token in one pass."""
    unfilled: set[str] = set()
    out: list[str] = []
    for line in text.splitlines(keepends=True):
        marks = CONDITIONAL.findall(line)
        if marks:
            keep = True
            for mark in marks:
                state = flags.get(mark)
                if state is None:
                    unfilled.add(mark)
                keep = keep and bool(state)
            if not keep:
                continue
            ending = "\n" if line.endswith("\n") else ""
            body = CONDITIONAL.sub("", line.rstrip("\n"))
            body = re.sub(r"\s*#\s*$", "", body)
            line = body + ending
        out.append(line)

    def swap(match: re.Match[str]) -> str:
        name = match.group(1)
        if name in values:
            return values[name]
        unfilled.add(name)
        return match.group(0)

    return PLACEHOLDER.sub(swap, "".join(out)), unfilled


def own_ci(root: Path, generated: dict[str, str], v2: bool) -> bool:
    """True when the repo already runs its own CI: project-init then adds sdd.yml, job sdd."""
    workflows = root / ".github" / "workflows"
    if not workflows.is_dir():
        return False
    for path in workflows.iterdir():
        if path.suffix not in (".yml", ".yaml") or not path.is_file():
            continue
        rel = rel_posix(path, root)
        if rel in generated:
            continue
        if path.name == "sdd.yml":
            continue
        if path.name == "ci.yml" and v2:
            continue  # the v2 project-init CI: the v3 render replaces it (9-migrate.md)
        return True
    return False


def workflow_push_branches(text: str) -> list[str] | None:
    """The `on: push: branches:` list of a GitHub Actions workflow, from its text (stdlib has
    no YAML reader): an inline `[a, b]` or a block list. None when push has no branch filter."""
    lines = [re.sub(r"\s+#.*$", "", ln).rstrip() for ln in text.splitlines()]

    def indent(line: str) -> int:
        return len(line) - len(line.lstrip())

    def block(start: int, parent: int) -> list[int]:
        rows = []
        for i in range(start, len(lines)):
            if not lines[i].strip():
                continue
            if indent(lines[i]) <= parent:
                break
            rows.append(i)
        return rows

    def key_at(rows: list[int], key: str) -> int | None:
        return next((i for i in rows if re.match(rf"^\s*[\"']?{key}[\"']?\s*:", lines[i])), None)

    top = key_at([i for i, ln in enumerate(lines) if ln.strip() and not indent(ln)], "on")
    if top is None or lines[top].split(":", 1)[1].strip():
        return None
    push = key_at(block(top + 1, 0), "push")
    if push is None:
        return None
    rows = block(push + 1, indent(lines[push]))
    at = key_at(rows, "branches")
    if at is None:
        return None
    rest = lines[at].split(":", 1)[1].strip()
    if rest.startswith("["):
        items = rest.strip("[]").split(",")
    else:
        items = [lines[i].strip().removeprefix("-") for i in block(at + 1, indent(lines[at]))]
    return [item.strip().strip("\"'") for item in items if item.strip()]


def ci_audit(root: Path, default: str, owned: set[str]) -> list[str]:
    """H15 in EXTEND: each workflow render does not own (the project's own CI, or a v2 one
    left behind) must run on the default branch and name no branch that is gone, such as a
    `master` renamed away. The files render owns are checked by their hash."""
    folder = root / ".github" / "workflows"
    if not folder.is_dir():
        return []
    found: list[str] = []
    for path in sorted(folder.iterdir()):
        rel = rel_posix(path, root)
        if path.suffix not in (".yml", ".yaml") or not path.is_file() or rel in owned:
            continue
        branches = workflow_push_branches(read_text(path) or "")
        if not branches:
            continue
        why: list[str] = []
        if default not in branches and not any(any(c in b for c in "*?[!") for b in branches):
            why.append(f"it never runs on {default}")
        gone = [
            b
            for b in branches
            if not any(c in b for c in "*?[!")
            and git(root, "show-ref", "-q", "--verify", f"refs/heads/{b}").code != 0
            and git(root, "show-ref", "-q", "--verify", f"refs/remotes/origin/{b}").code != 0
        ]
        if gone:
            why.append(f"{', '.join(gone)} is no branch here")
        if why:
            found.append(
                f"{rel}: push branches [{', '.join(branches)}], default branch {default}: "
                f"{'; '.join(why)} (H15)"
            )
    return found


def gh_major(repo: str) -> str | None:
    result = run(["gh", "api", f"repos/{repo}/releases/latest", "--jq", ".tag_name"], timeout=15)
    match = re.match(r"^(v\d+)", result.out.strip()) if result.code == 0 else None
    return match.group(1) if match else None


def load_values(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    text = raw
    if raw.startswith("@"):
        loaded = read_text(Path(raw[1:]).expanduser())
        if loaded is None:
            raise UsageError(f"--values: cannot read {raw[1:]}")
        text = loaded
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise UsageError(f"--values: not JSON ({exc})") from exc
    if not isinstance(data, dict):
        raise UsageError("--values: expected a JSON object of NAME: value")
    values: dict[str, str] = {}
    for key, value in data.items():
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", str(key)):
            raise UsageError(f"--values: {key!r} is not an UPPER_SNAKE name")
        if not isinstance(value, str):
            raise UsageError(f"--values: {key} must be a JSON string, not {json.dumps(value)}")
        if key in FROM_VERIFY:
            raise UsageError(
                f"--values: {key} comes from {VERIFY_JSON} (the happy path P5 ran green), "
                "never from --values; re-run init.py selftest [--start-args ...]"
            )
        values[str(key)] = value
    return values


# the pytest configs pytest reads at the repo root, in its own order: the first that
# configures pytest wins (pytest.ini always does; the others only with a pytest section)
PYTEST_CONFIGS = (
    ("pytest.ini", "pytest"),
    (".pytest.ini", "pytest"),
    ("pyproject.toml", ""),
    ("tox.ini", "pytest"),
    ("setup.cfg", "tool:pytest"),
)
PLUGIN_DEFAULT = "tests/conftest.py"  # the spec plugin's home when every test sits in tests/
TEST_DIR_NAMES = ("tests", "test")
CODE_SKIP = frozenset({"__pycache__", "node_modules", "venv", "site-packages", "build", "dist"})


def _split_args(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    if isinstance(value, str):
        try:
            return shlex.split(value)
        except ValueError:
            return value.split()
    return []


def pytest_testpaths(root: Path) -> list[str]:
    """The testpaths of the config pytest reads at the repo root (PYTEST_CONFIGS); [] when it
    sets none, so pytest collects from the root."""
    for name, section in PYTEST_CONFIGS:
        path = root / name
        if not path.is_file():
            continue
        if name == "pyproject.toml":
            data = load_toml(path)
            native = {k: v for k, v in table(data, *PYTEST_NATIVE).items() if k != "ini_options"}
            ini = table(data, *PYTEST_INI)
            if native or ini:
                return _split_args((native or ini).get("testpaths"))
            continue
        parser = configparser.ConfigParser(interpolation=None)
        try:
            parser.read_string(read_text(path) or "")
        except configparser.Error:
            if name.endswith("pytest.ini"):
                return []
            continue
        if parser.has_section(section):
            return _split_args(parser.get(section, "testpaths", fallback=""))
        if name.endswith("pytest.ini"):
            return []  # pytest.ini is the config even without a [pytest] section
    return []


def _inside(rel: str, roots: list[str]) -> bool:
    return any(rel == r or rel.startswith(r.rstrip("/") + "/") for r in roots)


def testpath_folders(root: Path, testpaths: list[str]) -> list[str]:
    """The repo-relative folders pytest collects from: the ones the testpaths name, globs
    expanded ("" for the root). A project that sets no testpaths gets [""]: a plain `pytest`
    run collects every test under the root."""
    found: list[str] = []
    for pattern in testpaths or ["."]:
        clean = pattern.strip().rstrip("/") or "."
        if PurePosixPath(clean).is_absolute() or ".." in PurePosixPath(clean).parts:
            continue
        hits = sorted(root.glob(clean)) if any(c in clean for c in "*?[") else [root / clean]
        for hit in hits:
            if hit.is_dir() and not hit.is_symlink():
                rel = rel_posix(hit, root)
                found.append("" if rel == "." else rel)
    return list(dict.fromkeys(found))


def is_test_file(name: str) -> bool:
    """A file pytest collects by its default python_files: test_*.py or *_test.py."""
    return name.endswith(".py") and (name.startswith("test_") or name.endswith("_test.py"))


def collectable(parent: Path, name: str) -> bool:
    """A folder pytest recurses into by its defaults: no dot folder, no build output or
    installed packages, no virtualenv."""
    return (
        not name.startswith(".")
        and name not in CODE_SKIP
        and not (parent / name / "pyvenv.cfg").is_file()
    )


def test_folders(root: Path, folder: str) -> list[str]:
    """The outermost tests/ or test/ folders under folder that hold a test_*.py or *_test.py
    (the repo root itself never counts, whatever its checkout is named)."""

    def holds_tests(path: Path) -> bool:
        return any(is_test_file(name) for _, _, names in os.walk(path) for name in names)

    found: list[str] = []
    for dirpath, dirnames, _ in os.walk(root / folder if folder else root):
        here = Path(dirpath)
        dirnames[:] = sorted(d for d in dirnames if collectable(here, d))
        if here != root and here.name in TEST_DIR_NAMES and holds_tests(here):
            found.append(rel_posix(here, root))
            dirnames[:] = []
    return found


def src_roots(root: Path, testpaths: list[str] | None = None) -> list[str]:
    """[paths] src: src/, else the top-level packages, else the code beside the tests (helios
    keeps its packages and modules in backend/, next to backend/tests): each folder or module
    under a test folder's parent that git tracks Python in, the tests left out. With no
    testpaths, or a testpath at the root, the test folders are the tests/ folders found under
    the root. D4's `Spec:` rule and prove-red's swap to the old code read them."""
    if (root / "src").is_dir():
        return ["src"]
    pkgs = [
        p.name
        for p in sorted(root.iterdir())
        if p.is_dir() and (p / "__init__.py").is_file() and p.name not in TEST_DIR_NAMES
    ]
    if pkgs:
        return pkgs
    folders = [
        found
        for folder in testpath_folders(root, testpaths or [])
        for found in ([folder] if folder else test_folders(root, ""))
    ]
    tracked = z_split(git(root, "ls-files", "-z", "--", "*.py").out) if is_git_root(root) else []
    dirs: list[str] = []
    files: list[str] = []
    for parent in dict.fromkeys(str(PurePosixPath(f).parent) for f in folders if f):
        if parent == ".":
            continue
        for rel in tracked:
            if not rel.startswith(parent + "/") or _inside(rel, folders):
                continue
            head = rel[len(parent) + 1 :].split("/", 1)
            if len(head) == 1:  # a module beside the tests: main.py, never a conftest.py
                if head[0] != "conftest.py" and f"{parent}/{head[0]}" not in files:
                    files.append(f"{parent}/{head[0]}")
                continue
            name = head[0]
            if name.startswith(".") or name in CODE_SKIP or name in TEST_DIR_NAMES:
                continue
            if f"{parent}/{name}" not in dirs:
                dirs.append(f"{parent}/{name}")
    return sorted(dirs) + sorted(files) or ["src"]  # folders first: selftest writes in the first


def test_roots(root: Path, testpaths: list[str], src: list[str]) -> list[str]:
    """[paths] tests: the project's real testpaths. A project that sets none has pytest collect
    from the root, so its test roots are the tests/ folders found there (top-level ones first),
    and "tests" when there are none yet. A testpath at or inside a source root (orca's
    src/orca) counts by the tests/ folders inside it: the whole package as a test root would
    make every source edit a test edit (I7)."""
    found: list[str] = []
    for folder in testpath_folders(root, testpaths):
        if not folder:
            found += sorted(test_folders(root, folder), key=lambda f: f.count("/"))
        elif _inside(folder, src):
            found += test_folders(root, folder)
        else:
            found.append(folder)
    unique = list(dict.fromkeys(found))
    outer = [f for f in unique if not any(f != o and _inside(f, [o]) for o in unique)]
    return outer or ["tests"]


def loose_tests(root: Path, testpaths: list[str], tests: list[str]) -> list[str]:
    """The test files pytest collects outside every test root: a test_*.py beside the code or
    at the root. [paths] tests names folders only, but the spec plugin has to reach these
    too, or their scenario tests record `notrun`."""
    found: list[str] = []
    for folder in testpath_folders(root, testpaths):
        if folder and _inside(folder, tests):
            continue
        for dirpath, dirnames, names in os.walk(root / folder if folder else root):
            here = Path(dirpath)
            rel = rel_posix(here, root)
            prefix = "" if rel == "." else f"{rel}/"
            dirnames[:] = sorted(
                d for d in dirnames if collectable(here, d) and not _inside(prefix + d, tests)
            )
            found += [prefix + n for n in sorted(names) if is_test_file(n)]
    return list(dict.fromkeys(found))


def _some(items: list[str]) -> str:
    return ", ".join(items[:3]) + (f" and {len(items) - 3} more" if len(items) > 3 else "")


def spec_plugin_dest(
    root: Path,
    tests: list[str],
    src: list[str],
    generated: dict[str, str],
    loose: list[str] | None = None,
) -> tuple[str, str | None]:
    """(where render writes the spec plugin, why when not tests/conftest.py). pytest loads a
    conftest.py only for the tests under its folder. So the plugin goes in tests/conftest.py
    when tests/ holds every test root and loose test file and that conftest.py is free
    (absent, or the plugin a render wrote). Otherwise it goes in the deepest folder above them
    all whose conftest.py is free and that no source root holds (prove-red swaps those for
    the old code): backend/ for helios's backend/tests, whose own conftest.py stays, and the
    root for tests colocated in src/ or a project that owns tests/conftest.py."""
    template = (TEMPLATES / PLUGIN_DEFAULT).read_bytes()

    def free(dest: str) -> bool:
        path = root / dest
        ours = dest in generated or (path.is_file() and path.read_bytes() == template)
        return not path.is_symlink() and (not path.exists() or ours)

    files = [f for f in loose or [] if not _inside(f, tests)]
    reach = list(dict.fromkeys([*tests, *files])) or ["tests"]
    folders = [PurePosixPath(f).parent.as_posix() if f in files else f for f in reach]
    common: list[str] = []
    for column in zip(*(PurePosixPath(f).parts for f in folders), strict=False):
        if len(set(column)) != 1:
            break
        common.append(column[0])
    candidates = [  # deepest first; a folder inside a source root never carries it
        f"{folder}/conftest.py" if folder else "conftest.py"
        for folder in ("/".join(common[:depth]) for depth in range(len(common), -1, -1))
        if not (folder and _inside(folder, src))
    ]
    if PLUGIN_DEFAULT in candidates and free(PLUGIN_DEFAULT):
        return PLUGIN_DEFAULT, None
    outside = [f for f in reach if not _inside(f, ["tests"])]
    for dest in (c for c in candidates if free(c)):
        folder = PurePosixPath(dest).parent.as_posix()
        where = "the repo root" if folder == "." else f"{folder}/"
        why = (
            f"the tests in {_some(outside)} reach outside tests/"
            if outside
            else f"{PLUGIN_DEFAULT} is the project's own"
        )
        return dest, (
            f"spec plugin: {dest}, since {why} and pytest loads a conftest.py only for the tests "
            f"under its folder ({where} holds them all)"
        )
    taken = [c for c in candidates if not free(c)]
    if not free(PLUGIN_DEFAULT):
        owned = ", ".join(dict.fromkeys([*taken, PLUGIN_DEFAULT]))
        return PLUGIN_DEFAULT, (
            f"spec plugin: every conftest.py that could carry it to the tests is the project's "
            f"own ({owned}). render asks before it writes over {PLUGIN_DEFAULT}: --force-file "
            "replaces that file's fixtures, and --keep-file installs no plugin, so verify fails "
            "`no test results` once a scenario exists. Free one first: fold its fixtures into "
            "the conftest.py above it, delete it, and re-run render"
        )
    return PLUGIN_DEFAULT, (
        f"spec plugin: {PLUGIN_DEFAULT}, which pytest loads only for the tests under tests/. "
        f"The tests in {_some(outside)} never load it: every folder above them all holds "
        f"the project's own conftest.py ({', '.join(taken)}). A scenario test there records "
        "`notrun`, and check fails it: keep scenario tests under tests/"
    )


def ruff_exclude_path(dest: str) -> str:
    """The ruff pattern for one file, an exclude entry or a per-file-ignores key: `./conftest.py`
    for the root (a bare `conftest.py` would match every conftest.py in the repo)."""
    return dest if "/" in dest else f"./{dest}"


TEST_LINT_ROW = '"tests/**" = '  # the template's per-file-ignores row for the tests


def test_lint_keys(tests: list[str], loose: list[str] | None = None) -> list[str]:
    """The ruff per-file-ignores keys that cover the tests: each [paths] tests root, and the
    test_*.py or *_test.py files of each folder that holds a loose test. `./` anchors a root
    pattern: ruff matches a pattern with no folder against every file's name."""
    keys = [f"{PurePosixPath(t).as_posix()}/**" for t in tests]
    for rel in loose or []:
        if _inside(rel, tests):
            continue
        path = PurePosixPath(rel)
        form = "test_*.py" if path.name.startswith("test_") else "*_test.py"
        folder = path.parent.as_posix()
        keys.append(f"./{form}" if folder == "." else f"{folder}/{form}")
    return list(dict.fromkeys(keys)) or ["tests/**"]


def pyproject_additions(
    plugin: str, tests: list[str] | None = None, loose: list[str] | None = None
) -> str:
    """The pyproject additions with the spec plugin's path in the ruff extend-exclude, and the
    tests' per-file-ignores row once per test_lint_keys key (helios's backend/tests/**): a row
    fixed to tests/** would fail every assert in a test elsewhere at pre-commit."""
    text = (TEMPLATES / "pyproject-additions.toml").read_text(encoding="utf-8")
    text = text.replace(f'"{PLUGIN_DEFAULT}"', toml_str(ruff_exclude_path(plugin)), 1)
    keys = test_lint_keys(tests or ["tests"], loose)
    lines, nl = split_lines(text)
    at = next(i for i, line in enumerate(lines) if line.startswith(TEST_LINT_ROW))
    rest = lines[at][len(TEST_LINT_ROW) :]  # the codes, then the comment for the first row
    value = rest.split("#", 1)[0].rstrip()
    lines[at : at + 1] = [
        f"{toml_str(key)} = {rest if i == 0 else value}" for i, key in enumerate(keys)
    ]
    return nl.join(lines) + nl


def emit_manifest(data: dict[str, object]) -> str:
    lines = [
        "# project-init manifest (init.py render). Tool-owned: re-run project-init to change it.",
        "# [generated] holds the sha256 of every file render wrote; EXTEND compares against it.",
    ]
    scalars = {k: v for k, v in data.items() if not isinstance(v, dict)}
    rank = {name: i for i, name in enumerate(TABLE_ORDER)}
    tables = dict(
        sorted(
            ((k, v) for k, v in data.items() if isinstance(v, dict)),
            key=lambda kv: rank.get(kv[0], len(rank)),
        )
    )
    lines += [f"{toml_key(k)} = {toml_value(v)}" for k, v in scalars.items()]

    def emit(prefix: list[str], body: dict[str, object]) -> None:
        lines.append("")
        lines.append("[" + ".".join(toml_key(p) for p in prefix) + "]")
        subs: dict[str, dict[str, object]] = {}
        for key, value in body.items():
            if isinstance(value, dict):
                subs[key] = value
            else:
                lines.append(f"{toml_key(key)} = {toml_value(value)}")
        for key, value in subs.items():
            emit([*prefix, key], value)

    for key, value in tables.items():
        emit([key], value)
    return "\n".join(lines) + "\n"


@dataclass
class RenderPlan:
    root: Path
    planned: list[Planned]
    manifest_text: str
    manifest_current: str | None
    unfilled: dict[str, list[str]]
    context: str
    # the front-door files P6 recorded, as (status, dest, why): judged by hash (front_door_audit)
    audit: list[tuple[str, str, str]] = field(default_factory=list)
    notes: list[tuple[str, str]] = field(default_factory=list)  # (label, text), printed first
    ci: list[str] = field(default_factory=list)  # CI files render does not own that drifted (H15)
    recorded: dict[str, str] = field(default_factory=dict)  # [generated] as .project.toml has it
    trunk: list[str] = field(default_factory=list)  # no Trunk section yet: trunk_upgrade (v3.1)


CLONE_VALUES = ("CLONE_URL", "CLONE_DIR")
CLONE_SAFE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._~:/@+%=-]*")


def public_url(url: str) -> str:
    """A remote URL with any user:password@ taken out of it: what a README may print."""
    return re.sub(r"^([A-Za-z][A-Za-z0-9+.-]*://)[^/@]*@", r"\1", url.strip())


def url_tail(url: str) -> str:
    """The folder `git clone <url>` makes: the URL's last part without .git, its case kept."""
    return re.split(r"[/:]", url.strip().rstrip("/"))[-1].removesuffix(".git")


def unsafe_values(values: dict[str, str]) -> list[str]:
    """Values that would break out of their spot: a branch or ref unquoted in sh or YAML, a
    quote in the TOML string of the start command, a backtick in a Markdown code span, a
    newline in a one-line comment."""
    bad: list[str] = []
    for key in sorted(values):
        value = values[key]
        if key in TOKEN_VALUES and not SAFE_TOKEN.fullmatch(value):
            bad.append(
                f"{key} {value!r}: letters, digits and . _ / - only, starting with a letter or "
                "digit (it lands unquoted in sh and in YAML)"
            )
        elif key in TOML_STRING_VALUES and (not value.strip() or NOT_IN_TOML_STRING.search(value)):
            bad.append(
                f'{key} {value!r}: a non-empty command line without " or \\ or control '
                "characters (it lands inside a TOML string in mise.toml)"
            )
        elif key in CODE_SPAN_VALUES and ("`" in value or CONTROL.search(value)):
            bad.append(f"{key}: one line without a backtick (it lands in a Markdown code span)")
        elif key == "OP_RUN" and value not in ("", OP_RUN):
            bad.append(f"OP_RUN {value!r}: only {OP_RUN_V3_DRAFT!r} or empty")
        elif key in CLONE_VALUES and not CLONE_SAFE.fullmatch(value):
            bad.append(
                f"{key} {value!r}: a plain URL or folder name (it lands in the README "
                "quickstart's clone line)"
            )
        elif key == "ENV_ROWS":
            if any(ln.strip() and not ln.startswith("#") for ln in value.splitlines()):
                bad.append("ENV_ROWS: every line must be a comment (start with #)")
        elif key not in MULTILINE_VALUES and CONTROL.search(value):
            bad.append(f"{key}: one line, no control characters")
    return bad


def leaves_repo(root: Path, rel: str) -> bool:
    """True when writing rel would go through a folder (or a dangling link) outside the repo."""
    probe = (root / rel).parent
    while probe != root and not probe.exists() and not probe.is_symlink():
        probe = probe.parent
    return not probe.resolve().is_relative_to(root.resolve())


def plan_render(
    root: Path,
    cli_values: dict[str, str],
    remote: str | None,
    offline: bool,
    agents_link: bool = False,
    check: bool = False,
) -> RenderPlan:
    """What render would write. check (render --check writes nothing): a local-folder origin is
    a finding, and the audit goes on as if there were no origin."""
    if not (root / "pyproject.toml").is_file():
        raise Refusal(
            f"{no_pack(root)}: render knows Python (pyproject.toml) only, and "
            "templates/stacks/ holds no other pack yet (P0 stops such a repo before the talk)"
        )
    for rel in ("pyproject.toml", MANIFEST):
        problem = toml_problem(root / rel)
        if problem:
            raise Refusal(f"{rel} does not parse ({problem}); fix it, then re-run")
    manifest = load_toml(root / MANIFEST)
    generated, kept, persisted = manifest_tables(manifest)
    given = {**persisted, **cli_values}
    # H6: the description is the mission one-liner, one source. A DESCRIPTION value (--values,
    # or one an older render saved) stands in only while specs/mission.md has none.
    description = mission_one_liner(root) or given.get("DESCRIPTION")
    v2 = bool(V2_STAMP.search(read_text(root / "project_memory" / "README.md") or ""))
    migrating = v2 or manifest.get("migrated_from") == V2_NAME

    origin = origin_url(root)
    saved_origin = manifest.get("origin_url")
    if isinstance(saved_origin, str) and is_local_url(saved_origin):
        saved_origin = None  # an older render recorded a folder path: drop it (see below)
    origin_value = saved_origin if isinstance(saved_origin, str) and saved_origin else origin or ""
    origin_note = ""
    if is_local_url(origin_value) and check:
        origin_note = (
            f"origin is a local folder ({origin_value}): audited as if there were none. A "
            "writing render refuses it; remove it (`git remote remove origin`) or point origin "
            "at the hosted repo first"
        )
        origin, origin_value = "", ""
    elif is_local_url(origin_value):
        # .project.toml is tracked: a folder path names this machine (a home path is a leak),
        # and merge could not open a pull request on it anyway
        raise Refusal(
            f"render refused: origin is a local folder ({origin_value}), and .project.toml "
            "records origin_url in a tracked file. Remove it (`git remote remove origin`) or "
            "point origin at the hosted repo, then re-run. Nothing written"
        )
    # the CI template is GitHub Actions: a local-path or other-host origin gets none
    github = bool(github_slug(origin) or github_slug(origin_value)) or remote == "github"
    ci_job = given.get("CI_JOB") or ("sdd" if own_ci(root, generated, migrating) else "verify")
    ci_file = None
    if github:
        ci_file = "sdd.yml" if ci_job == "sdd" else "ci.yml"
    elif ".github/workflows/sdd.yml" in generated:
        ci_file = "sdd.yml"  # rendered once: kept, and never mistaken for the project's own CI
    elif V2_CI in generated or (migrating and (root / V2_CI).is_file()):
        ci_file = "ci.yml"  # in place of the v2 ci.yml, remote or not (9-migrate.md)

    tier_saved = manifest.get("tier")
    tier = given.get("TIER") or (tier_saved if isinstance(tier_saved, str) and tier_saved else None)
    tier = tier or ("team" if len(human_authors(root)) >= 2 else "solo")
    if tier not in ("solo", "team"):
        raise UsageError(f"TIER must be solo or team, not {tier!r}")
    dist = given.get("DISTRIBUTION") or distribution(root)
    if dist is not None and dist not in DISTRIBUTIONS:
        raise UsageError(f"DISTRIBUTION must be one of {sorted(DISTRIBUTIONS)}, not {dist!r}")

    values: dict[str, str] = {}
    values["NAME"] = project_name(root)
    values["DEFAULT_BRANCH"] = detect_default_branch(root, manifest)
    scripts = console_scripts(root)
    if scripts:
        values["ENTRY"] = next(iter(scripts))
    env_file = root / ".env.example"
    current_env = read_text(env_file) if env_file.is_file() and not env_file.is_symlink() else None
    values["ENV_ROWS"] = env_contract_rows(root, env_reads(root), current_env)
    values["TEST_TAG_SYNTAX"] = TEST_TAG_SYNTAX_PY
    ids = scenario_ids(root)
    if ids:
        values["TEST_TAG_EXAMPLE"] = f'@pytest.mark.spec("{ids[0]}")'
    values["CI_JOB"] = ci_job
    values.update(given)
    # the workflow's name: sdd.yml sits beside the repo's own CI (helios's ci.yml is `CI`)
    values["CI_NAME"] = "sdd" if ci_file == "sdd.yml" else "ci"
    rows = values.get("ENV_ROWS", "")
    values["OP_RUN"] = given.get(
        "OP_RUN", OP_RUN if re.search(r"(?m)^#\s*\S+\s*\|\s*secret\s*\|", rows) else ""
    )
    if values["OP_RUN"] == OP_RUN_V3_DRAFT:  # --values names op run: the .env-guarded form
        values["OP_RUN"] = OP_RUN
    skills, notes = signal_skills(root, values.get("ENTRY"))
    for skill in skills:  # computed from the repo's files, never from --values
        values.update(skill.values)
    saved_paths = table(manifest, "paths")
    testpaths = pytest_testpaths(root)
    src = src_roots(root, testpaths)
    paths: dict[str, object] = saved_paths or {
        "src": src,
        "tests": test_roots(root, testpaths, src),
    }
    tests = _split_args(paths.get("tests"))
    loose = loose_tests(root, testpaths, tests)
    plugin, plugin_note = spec_plugin_dest(
        root, tests, _split_args(paths.get("src")), generated, loose
    )
    if plugin_note:
        notes.append(plugin_note)
    for dest in sorted(generated):
        if dest.endswith("conftest.py") and dest != plugin and (root / dest).is_file():
            notes.append(
                f"{dest} is the spec plugin an earlier render wrote; it now lives in {plugin}: "
                f"`git rm {dest}`, or pytest loads it twice where both apply"
            )
    team_text = None
    if tier == "team":
        values.update(team_values(root))
        on_disk = root / "project_memory" / "team.md"
        if on_disk.is_file() and not on_disk.is_symlink():
            team_text = read_text(on_disk) or ""
        else:
            team_text = fill((TEMPLATES / "team.md").read_text(encoding="utf-8"), values, {})[0]
        values["CODEOWNERS_ROWS"] = codeowners_rows(team_text)
    bad = unsafe_values(values)
    if bad:
        raise Refusal("render refused, unsafe values (nothing written):\n  " + "\n  ".join(bad))
    if ci_file and not offline:
        for key, repo in (
            ("CHECKOUT_REF", "actions/checkout"),
            ("MISE_ACTION_REF", "jdx/mise-action"),
        ):
            if key not in values:
                major = gh_major(repo)
                if major and SAFE_TOKEN.fullmatch(major):
                    values[key] = major
    flags: dict[str, bool | None] = {
        "IF_RELEASE": None if dist is None else dist in ("pypi", "git", "service"),
        "IF_TEAM": tier == "team",
    }

    # adoption-time baselines: taken once (a manifest key says so), never recomputed, because a
    # recompute would absorb new debt or a new leak instead of failing on it
    extra: list[Target] = []
    saved_ruff = manifest.get("ruff_baseline")
    ruff_due = not isinstance(saved_ruff, str) or saved_ruff.startswith("skipped")
    saved_leaks = manifest.get("gitleaks_baseline")
    leaks_due = not isinstance(saved_leaks, str) or saved_leaks.startswith("skipped")
    baselines: dict[str, str] = {}
    if leaks_due:
        prints, baselines["gitleaks_baseline"] = history_leaks(
            root, (TEMPLATES / "gitleaks.toml").read_bytes()
        )
        if prints:
            extra.append(
                Target(
                    "history scan", ".gitleaksignore", "seed", 0o644, gitleaksignore_text(prints)
                )
            )
            notes.append(leaks_note(prints))
        elif prints is None:
            notes.append(f"history scan {baselines['gitleaks_baseline']}; the next render retries")
    debt: dict[str, list[str]] | None = None
    if ruff_due:  # under the config this render writes: the merge without the baseline
        pyproject = root / "pyproject.toml"
        mine = utf8("pyproject.toml", pyproject.read_bytes() if pyproject.is_file() else None)
        merged = merge_pyproject(mine or "", pyproject_additions(plugin, tests, loose), description)
        debt, baselines["ruff_baseline"] = ruff_debt(root, merged)
        if debt:
            summary = baselines["ruff_baseline"]
            backlog = f"specs/backlog/{today()}-ruff-baseline.md"
            extra.append(
                Target("lint debt", backlog, "seed", 0o644, debt_backlog_text(summary, debt))
            )
            notes.append(
                f"ruff baseline: {summary} ignored per file under `# {BASELINE_MARK}`, plus "
                "one backlog item (N3)"
            )
        elif debt is None:
            notes.append(f"ruff baseline {baselines['ruff_baseline']}; the next render retries")
    saved_ty = manifest.get("ty_baseline")
    types: list[str] | None = None
    if not isinstance(saved_ty, str) or saved_ty.startswith("skipped"):
        types, baselines["ty_baseline"] = ty_debt(root)
        if types:
            summary = baselines["ty_baseline"]
            backlog = f"specs/backlog/{today()}-ty-baseline.md"
            extra.append(
                Target("type debt", backlog, "seed", 0o644, ty_backlog_text(summary, types))
            )
            notes.append(
                f"ty baseline: {summary}, left out of `ty check` by [tool.ty.src] exclude under "
                f"`# {TY_BASELINE_MARK}`, plus one backlog item (Risk 8)"
            )
        elif types is None:
            notes.append(f"ty baseline {baselines['ty_baseline']}; the next render retries")
    for skill in skills:
        base = TEMPLATES / "skills-per-signal" / skill.template
        for path in sorted(base.rglob("*")):
            if path.is_file():
                rel = rel_posix(path, base)
                extra.append(
                    Target(
                        rel_posix(path, TEMPLATES),
                        f".claude/skills/{skill.name}/{rel}",
                        "text",
                        0o644,
                    )
                )
    saved_link = manifest.get("agents_symlink") is True
    if agents_link or saved_link:
        extra.append(
            Target("--agents-symlink", AGENTS_LINK[0], "link", 0o777, AGENTS_LINK[1].encode())
        )

    planned: list[Planned] = []
    unfilled: dict[str, list[str]] = {}
    for spec in [*template_targets(ci_file, tier, plugin), *extra]:
        dest, kind = spec.dest, spec.kind
        if kind == "seed" and seed_satisfied(root, dest):
            continue  # the project's own file (or, for decisions/, its first ADR) stands in
        raw = spec.content if spec.content is not None else (TEMPLATES / spec.source).read_bytes()
        target = root / dest
        if leaves_repo(root, dest):
            raise Refusal(f"{dest}: its folder resolves outside the repo; nothing written")
        link = None
        if target.is_symlink():
            try:
                link = os.readlink(target)
            except OSError:
                link = "?"
        elif target.exists() and not target.is_file():
            raise Refusal(f"{dest} exists and is not a file; move it aside, then re-run")
        # through a symlink the file is read (merges and diffs need it), never written
        current = target.read_bytes() if target.is_file() and kind != "link" else None
        if kind in ("link", "copy") or spec.content is not None:
            content = raw  # byte for byte: a link target, a copied file, computed content
        elif kind in ("text", "seed", "env"):
            text, missing = fill(raw.decode("utf-8"), values, flags)
            for name in missing:
                unfilled.setdefault(name, []).append(dest)
            content = text.encode("utf-8")
        elif kind == "lines":
            text = merge_lines(utf8(dest, current), raw.decode("utf-8"), dest == ".gitignore")
            content = text.encode("utf-8")
        else:
            additions = with_ty_baseline(
                with_baseline(pyproject_additions(plugin, tests, loose), debt or {}), types or []
            )
            text = merge_pyproject(utf8(dest, current) or "", additions, description)
            if "Add your description here" in text:
                unfilled.setdefault("DESCRIPTION", []).append(dest)
            content = text.encode("utf-8")
        planned.append(Planned(dest, kind, spec.source, content, spec.mode, current, link=link))

    for item in planned:
        item.status = plan_status(root, item, generated.get(item.dest), kept.get(item.dest))
        if migrating:
            item.status = v2_status(item, generated.get(item.dest))

    new_generated = next_generated(planned, generated)
    for dest in FRONT_DOOR:  # P6 wrote these; this render leaves them and their hashes alone
        if dest in generated and dest not in new_generated:
            new_generated[dest] = generated[dest]
    saved_since = manifest.get("audit_since")
    slug = github_slug(origin_value)
    data: dict[str, object] = {
        "standard": STANDARD,
        "default_branch": values["DEFAULT_BRANCH"],
        "origin_url": origin_value,
        "audit_since": saved_since if isinstance(saved_since, str) else today(),
        "tier": tier,
        "server_protection": server_protection(
            manifest,
            given,
            github,
            lambda: protection_state(slug, values["DEFAULT_BRANCH"], root) if slug else None,
            offline,
        ),
    }
    for key in ("ruff_baseline", "ty_baseline", "gitleaks_baseline"):
        saved = manifest.get(key)
        data[key] = baselines.get(key) or (saved if isinstance(saved, str) else "")
    if agents_link or saved_link:
        data["agents_symlink"] = True
    if migrating:
        data["migrated_from"] = V2_NAME  # P6 needs it: this render replaces the v2 stamp
    for key, value in manifest.items():
        if key not in data and not isinstance(value, dict):
            data[key] = value
    data["paths"] = paths
    data["signals"] = {k: ", ".join(v) for k, v in detect_signals(root).items()}
    if given:
        data["values"] = dict(sorted(given.items()))
    data["generated"] = dict(sorted(new_generated.items(), key=lambda kv: kv[0]))
    seeded = {k: v for k, v in table(manifest, "seeded").items() if isinstance(v, str)}
    for item in planned:
        if item.kind == "seed":
            seeded[item.dest] = today()
    if seeded:
        data["seeded"] = dict(sorted(seeded.items()))
    if kept:
        data["kept"] = kept
    for key, value in manifest.items():
        if key not in data and isinstance(value, dict):
            data[key] = value
    manifest_current = read_text(root / MANIFEST) if (root / MANIFEST).is_file() else None
    context = (
        f"{values['NAME']} ({detect_stack(root)}), default branch {values['DEFAULT_BRANCH']}, "
        f"{tier} tier, distribution {dist or 'unknown'}, "
        + (f"CI {ci_file} (job {ci_job})" if ci_file else "no CI (no GitHub origin)")
    )
    plan = RenderPlan(root, planned, emit_manifest(data), manifest_current, unfilled, context)
    plan.audit = front_door_audit(root, generated, kept, text_table(manifest, TEMPLATE_TABLE))
    plan.recorded = generated
    owned = {p.dest for p in planned} | set(generated)
    plan.ci = ci_audit(root, values["DEFAULT_BRANCH"], owned)
    plan.trunk = trunk_upgrade(root)
    if tier == "team" and team_text is not None and not ownership(team_text):
        notes.append(
            "CODEOWNERS names no owner yet: fill the Ownership table in project_memory/team.md, "
            "then re-run render (punch list)"
        )
    plan.notes = [("note", n) for n in notes]
    if origin_note:
        plan.notes.insert(0, ("origin", origin_note))
    return plan


SERVER_AUTO = ("none:", "pending:")  # server_protection values render recomputes every run


def server_protection(
    manifest: dict[str, object],
    given: dict[str, str],
    github: bool,
    probe: Callable[[], str | None] | None = None,
    offline: bool = False,
) -> str:
    """The server rules state (.project.toml). P7 and EXTEND record what they find
    (`unavailable: Free private`, `applied: ...`), and render keeps it: recorded once, never
    retried. Until then render asks GitHub for an origin that exists (probe, never offline):
    a Free private repo is recorded as unavailable; otherwise it says why there are none yet."""
    saved = manifest.get("server_protection")
    if given.get("SERVER_PROTECTION"):
        return given["SERVER_PROTECTION"]
    if isinstance(saved, str) and saved and not saved.startswith(SERVER_AUTO):
        return saved
    if not github:
        return "none: no GitHub remote"
    found = probe() if probe is not None and not offline else None
    return found or SERVER_PENDING


def utf8(dest: str, data: bytes | None) -> str | None:
    """A merged file's text. A file that is not UTF-8 is refused: merging it would garble it."""
    try:
        return None if data is None else data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Refusal(f"{dest} is not UTF-8 ({exc}); fix it, then re-run") from exc


def manifest_tables(
    manifest: dict[str, object],
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """(generated, kept, values) from .project.toml. A START_* value a v3 draft saved there is
    dropped: those come from verify.json only."""
    generated = {k: v for k, v in table(manifest, "generated").items() if isinstance(v, str)}
    kept = {k: v for k, v in table(manifest, "kept").items() if isinstance(v, str)}
    values = {
        k: v
        for k, v in table(manifest, "values").items()
        if isinstance(v, str) and k not in FROM_VERIFY
    }
    return generated, kept, values


def next_generated(planned: list[Planned], generated: dict[str, str]) -> dict[str, object]:
    """[generated] after a render that writes every planned file it may write. A held or kept
    file keeps its recorded hash, and so does a merged file that matches its merge: the lines
    the project added since are its own, and a later template change asks before it re-merges."""
    new: dict[str, object] = {}
    for item in planned:
        if item.kind == "seed":  # the project's file once written: [seeded] lists it
            continue
        recorded = generated.get(item.dest)
        held = item.status in (*HELD_STATUSES, "kept")
        if held or (item.status == "ok" and item.kind in MERGED_KINDS and recorded):
            if recorded:
                new[item.dest] = recorded
            continue
        new[item.dest] = item.record
    return new


def v2_status(item: Planned, recorded: str | None) -> str:
    """A v2 file the migration prompt covered (V2_REPLACED), never rendered by v3 yet: its
    customized status becomes upgrade, since the approved prompt was its question (R3)."""
    if item.status == "customized" and recorded is None and item.dest in V2_REPLACED:
        return "upgrade"
    return item.status


def plan_status(root: Path, item: Planned, recorded: str | None, kept: str | None) -> str:
    """ok: matches the render. upgrade: unchanged since the last render (its recorded hash),
    or a merged file or README region render has never touched. customized: changed by hand
    since (for a merged file: the merge would re-add or change what the project removed or
    edited; for the README: its region was edited or removed). symlink: never written through.
    kept: customized or a symlink, and --keep-file declined this very render."""
    if item.kind == "link":  # render's own symlink: right when it names the planned target
        if item.link is None:
            return "missing"
        if item.link == item.content.decode("utf-8"):
            return "ok"
        return "kept" if kept == item.record else "customized"
    if item.link is not None:
        return "kept" if kept == item.record else "symlink"
    if item.current is None:
        return "missing"
    exec_ok = bool((root / item.dest).stat().st_mode & 0o100) == bool(item.mode & 0o100)
    if item.current == item.content:
        return "ok" if exec_ok else "upgrade"
    if item.kind in FIRST_MERGE_SAFE and recorded is None:
        return "upgrade"  # the first merge into the project's own .gitignore or pyproject.toml
    if item.kind == "region" and item.current_record is None and recorded is None:
        return "upgrade"  # the first quickstart region in the project's own README
    if item.current_record is not None and recorded == item.current_record:
        return "upgrade"
    if kept == item.record:
        return "kept"
    return "customized"


def unified(item: Planned) -> str:
    """The diff of a file render writes: from yours to the render."""
    ours = (item.current or b"").decode("utf-8", "replace").splitlines(keepends=True)
    theirs = item.content.decode("utf-8", "replace").splitlines(keepends=True)
    diff = difflib.unified_diff(ours, theirs, f"a/{item.dest} (yours)", f"b/{item.dest} (render)")
    return "".join(line if line.endswith("\n") else line + "\n" for line in diff)


def question_diff(item: Planned) -> str:
    """The diff a keep-or-take question shows for a customized file: from the render to yours,
    so your own lines are `+`, as in render --check's diff of a front-door edit."""
    theirs = item.content.decode("utf-8", "replace").splitlines(keepends=True)
    ours = (item.current or b"").decode("utf-8", "replace").splitlines(keepends=True)
    diff = difflib.unified_diff(theirs, ours, f"a/{item.dest} (render)", f"b/{item.dest} (yours)")
    return "".join(line if line.endswith("\n") else line + "\n" for line in diff)


def install(root: Path, rel: str, data: bytes, mode: int) -> None:
    """install -D: parents created, a temp file in the target folder, then an atomic rename.
    Refuses a path that would leave the repo through a symlinked folder."""
    dest = root / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.parent.resolve().is_relative_to(root.resolve()):
        raise Refusal(f"{rel}: its folder resolves outside the repo; not written")
    fd, tmp = tempfile.mkstemp(dir=dest.parent, prefix=f".{dest.name}.")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.chmod(tmp, mode)
        os.replace(tmp, dest)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def put(root: Path, item: Planned) -> None:
    if item.kind == "link":
        install_link(root, item.dest, item.content.decode("utf-8"))
    else:
        install(root, item.dest, item.content, item.mode)


def install_link(root: Path, rel: str, target: str) -> None:
    """A symlink made next to dest under a temp name, then renamed over it: never half made."""
    dest = root / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.parent.resolve().is_relative_to(root.resolve()):
        raise Refusal(f"{rel}: its folder resolves outside the repo; not written")
    tmp = dest.parent / f".{dest.name}.{secrets.token_hex(6)}"
    os.symlink(target, tmp)
    try:
        os.replace(tmp, dest)
    except OSError as exc:
        tmp.unlink(missing_ok=True)
        raise Refusal(f"{rel}: {exc}; move it aside, then re-run") from exc


def cmd_render(args: argparse.Namespace) -> int:
    root = repo_root(args.repo)
    values = load_values(args.values)
    if args.front_door:
        if args.remote or args.agents_symlink:
            raise UsageError(
                "--remote and --agents-symlink belong to the machinery render (P4), "
                "not --front-door"
            )
        plan = plan_front_door(root, values)
    else:
        plan = plan_render(
            root, values, args.remote, args.offline, args.agents_symlink, check=args.check
        )
    if plan.unfilled:
        print("render: refused, placeholders left unfilled (nothing written):")
        for name in sorted(plan.unfilled):
            where = ", ".join(sorted(set(plan.unfilled[name])))
            print(f"  {name:<18} in {where}{UNFILLED_HINTS.get(name, '')}")
        print('  pass them with --values \'{"NAME": "value", ...}\' (or @file.json)')
        return 1
    dests = {p.dest for p in plan.planned}
    forced = {normalize_rel(p) for p in args.force_file}
    keep = {normalize_rel(p) for p in args.keep_file}
    unknown = sorted((forced | keep) - dests)
    if unknown:
        shown = [
            f"{u} (a front-door file: add --front-door)"
            if u in FRONT_DOOR and not args.front_door
            else u
            for u in unknown
        ]
        raise UsageError(f"{', '.join(shown)}: not a file this render writes")
    print(label("render") + plan.context)
    for tag, note in plan.notes:
        print(label(tag) + note)
    if args.check:
        return report_check(plan)

    # R3: a customized file is a question, and a render with an open question writes nothing:
    # no half-upgraded machinery, and no [values] saved for files that were never written
    left = [
        p
        for p in plan.planned
        if p.status in HELD_STATUSES and p.dest not in forced and p.dest not in keep
    ]
    if left:
        for item in left:
            if item.status == "symlink":
                why = f"a symlink to {item.link}: never written through, diff below"
            else:
                why = "not overwritten (changed since the last render), diff below"
            print(f"  {item.status:<20} {item.dest}: {why}")
            print(question_diff(item), end="")
        waiting = [p.dest for p in plan.planned if p.status in ("missing", "upgrade")]
        if waiting:
            print(f"  {'waiting':<20} {', '.join(waiting)}")
        names = " ".join(f"--force-file {i.dest}" for i in left)
        again = "render --front-door" if args.front_door else "render with the same --values"
        print(
            f"render: {len(left)} customized file(s), nothing written. Answer each, then re-run "
            f"{again}: take the render with {names} (a symlink is replaced by a file), or keep "
            "yours with --keep-file <path>"
        )
        return 3

    wrote: list[str] = []
    kept_now: dict[str, str] = {}
    for item in plan.planned:
        status = item.status
        if item.dest in forced and status in (*HELD_STATUSES, "kept"):
            put(root, item)  # a symlink is replaced, not followed
            item.status = "forced"
            wrote.append(item.dest)
            print(f"  {'forced (render)':<20} {item.dest}")
            continue
        if item.dest in keep and status in HELD_STATUSES:
            kept_now[item.dest] = item.record
            item.status = "kept"
            continue
        if status in ("missing", "upgrade"):
            put(root, item)
            wrote.append(item.dest)
            print(f"  {status:<20} {item.dest}")
            if item.kind == "region":  # the project's own README: show what changed in it
                print(unified(item), end="")
    if forced or kept_now:
        manifest = parse_toml(plan.manifest_text)
        generated = table(manifest, "generated")
        kept = {k: v for k, v in table(manifest, "kept").items() if k not in forced}
        for item in plan.planned:
            if item.status == "forced":
                generated[item.dest] = item.record
        kept.update(kept_now)
        manifest.pop("kept", None)
        if kept:
            manifest["kept"] = dict(sorted(kept.items(), key=lambda kv: kv[0]))
        manifest["generated"] = dict(sorted(generated.items(), key=lambda kv: kv[0]))
        text = emit_manifest(manifest)
    else:
        text = plan.manifest_text
    manifest_written = text != plan.manifest_current
    if manifest_written:
        install(root, MANIFEST, text.encode("utf-8"), 0o644)
        count = len(table(parse_toml(text), "generated"))
        print(f"  {'written':<20} {MANIFEST} ([generated] holds {count} hashes)")
    for item in plan.planned:
        if item.status == "kept":
            print(f"  {'kept (yours)':<20} {item.dest}")
    for finding in plan.ci:  # a file render does not own: listed, never rewritten
        print(label("ci") + finding)
    print_trunk(plan.trunk)  # product text: P2 writes the section, render only reminds
    if wrote:
        print(f"render: {len(wrote)} change(s)")
    elif manifest_written:  # a [kept] row, a new hash: tracked, so it ships like any change
        print(f"render: 1 change ({MANIFEST} only: it is tracked, so it ships like any change)")
    else:
        print("render: 0 changes")
    return 0


UNFILLED_HINTS = {
    "DESCRIPTION": "  (specs/mission.md has no one-liner under `## One-liner` yet: P2 writes it)",
    "IF_RELEASE": "  (set DISTRIBUTION: pypi|git|service|none)",
    "ENTRY": '  (no [project.scripts]: the start command, e.g. "uvicorn app.main:app")',
    "TEST_TAG_EXAMPLE": "  (no scenario in specs/capabilities/ yet: P2 writes one)",
}


def report_check(plan: RenderPlan) -> int:
    """render --check: every planned file and every front-door file P6 recorded, compared with
    what a render would write (or, for the front door without --front-door, with its recorded
    hash). Writes nothing."""
    manifest_changes = plan.manifest_text != plan.manifest_current
    drift = [p for p in plan.planned if p.status not in ("ok", "kept")]
    for item in plan.planned:
        if item.status != "ok":
            print(f"  {item.status:<11} {item.dest}")
    for status, dest, why in plan.audit:
        if status != "ok":
            how = f": {why}" if why else ", by its recorded hash"
            print(f"  {status:<11} {dest}  (front door{how})")
            if status == "customized":
                print(front_door_diff(plan.root, dest, plan.recorded.get(dest)), end="")
    for finding in plan.ci:
        print(f"  {'ci':<11} {finding}")
    print_trunk(plan.trunk)
    if manifest_changes:
        print(f"  {'missing' if plan.manifest_current is None else 'upgrade':<11} {MANIFEST}")
    for item in drift:
        if item.status in HELD_STATUSES:
            print(question_diff(item), end="")
        elif item.kind == "region":
            print(unified(item), end="")
    matched = sum(p.status in ("ok", "kept") for p in plan.planned)
    matched += sum(status in ("ok", "kept") for status, _, _ in plan.audit)
    count = len(drift) + sum(status not in ("ok", "kept") for status, _, _ in plan.audit)
    count += len(plan.ci) + (1 if manifest_changes else 0) + (1 if plan.trunk else 0)
    total = len(plan.planned) + len(plan.audit)
    # the files can all match while this clone runs no git gate: a fresh clone has none until
    # `mise install` (its postinstall runs `hook install`). doctor checks the rest (8-extend.md)
    hooks = git_out(plan.root, "config", "--get", "core.hooksPath")
    gates_off = (plan.root / ".githooks").is_dir() and hooks != ".githooks"
    if gates_off:
        print(
            label("gates")
            + f"core.hooksPath is {hooks or 'unset'}, not .githooks: the git gates are off in "
            "this clone. Run `mise trust && mise install`, then `mise run doctor`"
        )
    tail = "; the git gates are off here" if gates_off else ""
    print(f"render --check: {count} drift ({matched} of {total} files match){tail}")
    return 3 if count else 0


# ---------------------------------------------------------------------------------------------
# P6 front door: AGENTS.md and the README quickstart region, from what P5 ran green


def region_bounds(lines: list[str]) -> tuple[int, int] | None:
    """(begin, end) line indexes of the README's tool-owned quickstart region, markers
    included. The begin marker carries a note for readers, so only its prefix is matched."""
    begin = next((i for i, ln in enumerate(lines) if ln.lstrip().startswith(QS_BEGIN)), None)
    if begin is None:
        return None
    end = next((i for i in range(begin + 1, len(lines)) if lines[i].strip() == QS_END), None)
    if end is None:
        raise Refusal(f"README.md: a `{QS_BEGIN}` line with no `{QS_END}` after it; fix it by hand")
    return begin, end


def region_text(lines: list[str]) -> str:
    return "\n".join(lines) + "\n"


def after_first_paragraph(lines: list[str]) -> int:
    """The index just past the README's first paragraph: the first run of non-blank lines that
    is not a heading (a fenced block counts whole). With none, just past the first heading."""
    first_heading: int | None = None
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if re.match(r"^\s{0,3}#{1,6}(\s|$)", line):
            first_heading = i if first_heading is None else first_heading
            i += 1
            continue
        inside = False
        while i < len(lines) and (inside or lines[i].strip()):
            if FENCE.match(lines[i]):
                inside = not inside
            i += 1
        return i
    return first_heading + 1 if first_heading is not None else len(lines)


def readme_with_region(
    current: str | None, block: str, name: str, pitch: str | None, v2_quickstart: bool = False
) -> tuple[str, str | None]:
    """(the README with block as its quickstart region, the region it holds now or None). The
    region is replaced where it is; a README without one gets it after its first paragraph; no
    README, or an empty one (`uv init` writes one), gets a new one: the name, the one-liner, the
    quickstart. v2_quickstart (a v2 migration): the `## Quickstart` section project-init v2
    wrote is the region's place, and the region replaces it whole (9-migrate.md)."""
    block_lines, _ = split_lines(block)
    if current is None or not current.strip():
        head = [f"# {name}", ""] + ([pitch, ""] if pitch else [])
        return region_text(head + block_lines), None
    lines, newline = split_lines(current)
    bounds = region_bounds(lines)
    if bounds:
        begin, end = bounds
        now: str | None = region_text(lines[begin : end + 1])
        new = lines[:begin] + block_lines + lines[end + 1 :]
    elif v2_quickstart and (section := quickstart_section(lines)):
        now = None
        start, stop = section
        tail = lines[stop:]
        while tail and not tail[0].strip():
            tail.pop(0)
        new = lines[:start] + block_lines + ([""] + tail if tail else [])
    else:
        now = None
        at = after_first_paragraph(lines)
        head, tail = lines[:at], lines[at:]
        while head and not head[-1].strip():
            head.pop()
        while tail and not tail[0].strip():
            tail.pop(0)
        new = head + ([""] if head else []) + block_lines + ([""] + tail if tail else [])
    return newline.join(new) + newline, now


def quickstart_section(lines: list[str]) -> tuple[int, int] | None:
    """(first line, end) of a `Quickstart` section: its heading up to the next heading of the
    same or a higher level, or the end. Headings inside a fence do not count."""
    inside = False
    start: int | None = None
    level = 0
    for i, line in enumerate(lines):
        if FENCE.match(line):
            inside = not inside
            continue
        if inside:
            continue
        match = re.match(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$", line)
        if not match:
            continue
        if start is None:
            if match.group(2).strip().lower() == "quickstart":
                start, level = i, len(match.group(1))
        elif len(match.group(1)) <= level:
            return start, i
    return (start, len(lines)) if start is not None else None


def pad_start_line(template: str, example: str, expected: str) -> str:
    """The quickstart's `{START_EXAMPLE}  # {START_EXPECTED}` line, its comment lined up with
    the comments above it, and dropped when the happy path printed nothing."""
    lines = template.split("\n")
    marks = [ln.index(" # ") + 1 for ln in lines if " # " in ln and "{START_" not in ln]
    column = marks[-1] if marks else 32
    for i, line in enumerate(lines):
        if re.fullmatch(r"\{START_EXAMPLE\}\s+#\s*\{START_EXPECTED\}\s*", line):
            if not expected:
                lines[i] = example
            elif len(example) < column - 1:
                lines[i] = f"{example.ljust(column - 1)} # {expected}"
            else:
                lines[i] = f"{example}  # {expected}"
    return "\n".join(lines)


MISE_COMMAND = re.compile(r"\bmise (install|tasks ls|run ([A-Za-z0-9_.:-]+))")


def named_commands(text: str) -> set[str]:
    """The mise commands a front-door text names, as verify.json keys (`mise run <task>`)."""
    found: set[str] = set()
    for match in MISE_COMMAND.finditer(text):
        found.add(f"mise run {match.group(2)}" if match.group(2) else f"mise {match.group(1)}")
    return found


FINGERPRINTED = ("mise.toml", "pyproject.toml", "uv.lock", "scripts/project.py", ".env")


def verify_fingerprint(root: Path) -> str:
    """What the commands P5 ran depend on: the toolchain and gate files, the local .env that
    mise loads into every task, and every file under the src roots. A verify.json from before
    a change to one of them is stale, and P6 refuses it."""
    rels = list(FINGERPRINTED)
    saved = table(load_toml(root / MANIFEST), "paths").get("src")
    for base in saved if isinstance(saved, list) else src_roots(root, pytest_testpaths(root)):
        folder = root / str(base)
        if folder.is_file():  # a module source root: helios's backend/main.py
            rels.append(rel_posix(folder, root))
        for dirpath, dirnames, filenames in os.walk(folder) if folder.is_dir() else []:
            dirnames[:] = sorted(d for d in dirnames if d != "__pycache__" and d[:1] != ".")
            rels += [
                rel_posix(Path(dirpath) / name, root)
                for name in sorted(filenames)
                if not name.endswith((".pyc", ".pyo"))
            ]
    digest = hashlib.sha256()
    for rel in rels:
        path = root / rel
        data = path.read_bytes() if path.is_file() else b""
        digest.update(f"{rel}\0{sha256(data)}\0".encode())
    return "sha256:" + digest.hexdigest()


def load_verify(root: Path, who: str = "front door") -> dict[str, object]:
    """verify.json when it is P5's record for the files as they are and P5 was green. who:
    the front door (P6) or publish (P7), for the refusal's wording."""
    path = root / VERIFY_JSON
    text = read_text(path) if path.is_file() and not path.is_symlink() else None
    need = (
        "P6 quotes only commands P5 ran green"
        if who == "front door"
        else "the ship commit's body holds P5's real results (N21)"
    )
    then = "P6" if who == "front door" else "P7"
    if text is None:
        raise Refusal(f"{who} refused: no {VERIFY_JSON}. {need}: run init.py selftest first (P5)")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise Refusal(f"{VERIFY_JSON} is not JSON ({exc}); re-run init.py selftest") from exc
    checks = data.get("checks") if isinstance(data, dict) else None
    start = data.get("start") if isinstance(data, dict) else None
    if not isinstance(checks, list) or not isinstance(start, dict):
        raise Refusal(f"{VERIFY_JSON} is not a P5 record; re-run init.py selftest")
    if data.get("fingerprint") != verify_fingerprint(root):
        raise Refusal(
            f"{who} refused: {VERIFY_JSON} is stale (mise.toml, pyproject.toml, uv.lock, "
            "scripts/project.py, .env or a file under the src roots changed since P5 ran); "
            "re-run init.py selftest"
        )
    if data.get("green") is not True:
        red = [
            str(c.get("name"))
            for c in checks
            if isinstance(c, dict) and c.get("required") and not c.get("green")
        ]
        matrix = data.get("matrix")
        if not (isinstance(matrix, dict) and matrix.get("green")):
            red.append("the negative matrix (project.py selftest)")
        raise Refusal(
            f"{who} refused: P5 is not green (" + ", ".join(red or ["unknown"]) + "); fix "
            f"the cause, re-run init.py selftest, then {then}"
        )
    if not (isinstance(start.get("command"), str) and start.get("green") is True):
        raise Refusal(f"{who} refused: {VERIFY_JSON} records no green happy path")
    return data


MD_REFERENCE = re.compile(r"`([^`\s]+\.md)`|\]\(([^)\s#]+\.md)(?:#[^)\s]*)?\)")


def readme_audit(root: Path, text: str) -> list[str]:
    """Fenced commands outside the quickstart region that name a mise task, a console script,
    a make target or a repo file that does not exist, and prose that names a Markdown file
    the repo lacks (a v2 README's `ONBOARDING.md`). Listed for the human, never rewritten."""
    tasks = set(table(load_toml(root / "mise.toml"), "tasks"))
    scripts = set(console_scripts(root))
    makefile = read_text(root / "Makefile") or ""
    lines, _ = split_lines(text)
    bounds = None
    try:
        bounds = region_bounds(lines)
    except Refusal:
        bounds = None
    stale: list[str] = []
    inside = False
    for i, line in enumerate(lines):
        if bounds and bounds[0] <= i <= bounds[1]:
            continue
        if FENCE.match(line):
            inside = not inside
            continue
        if not inside:
            for match in MD_REFERENCE.finditer(line):
                ref = match.group(1) or match.group(2)
                if "://" in ref or (root / ref.removeprefix("./")).exists():
                    continue
                why = f"stale reference, fix it by hand: `{ref}` (no such file)"
                if why not in stale:
                    stale.append(why)
            continue
        for words in subcommands(line):
            why = stale_command(root, words, tasks, scripts, makefile)
            if why and f"stale command, fix it by hand: {why}" not in stale:
                stale.append(f"stale command, fix it by hand: {why}")
    return stale


COMMAND_SEPARATORS = frozenset({"&&", "||", ";", "|", "&", "|&"})
REDIRECTS = frozenset({">", ">>", "<", ">&", "<&", "&>", "&>>", ">|"})


def subcommands(line: str) -> list[list[str]]:
    """The simple commands of one fenced shell line: `make setup && make doctor` is two. Leading
    VAR=x assignments are dropped, and a redirection ends its command's words."""
    lexer = shlex.shlex(line.strip().removeprefix("$ "), posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        return []
    found: list[list[str]] = []
    words: list[str] = []
    redirected = False
    for token in [*tokens, "&&"]:
        if token in COMMAND_SEPARATORS:
            while words and ASSIGN.match(words[0]):
                words.pop(0)
            if words:
                found.append(words)
            words, redirected = [], False
        elif token in REDIRECTS or redirected:
            redirected = True
        else:
            words.append(token)
    return found


def stale_command(
    root: Path, words: list[str], tasks: set[str], scripts: set[str], makefile: str
) -> str | None:
    """Why one simple command is stale, shown whole (cut at 60 characters), or None."""
    shown = " ".join(words)
    shown = shown if len(shown) <= 60 else shown[:57] + "..."
    if words[:2] == ["mise", "run"] and len(words) > 2 and words[2] not in tasks:
        return f"`{shown}` (no mise task {words[2]})"
    if words[:2] == ["uv", "run"]:
        rest = words[2:]
        while rest and rest[0].startswith("-"):
            rest.pop(0)
        if rest:
            name = rest[0]
            venv = root / ".venv" / "bin" / name
            known = name in scripts or name in ("python", "python3") or venv.exists()
            if not known and not (root / name).exists():
                return f"`{shown}` (no console script or file {name})"
    if words[0] == "make" and len(words) > 1 and not words[1].startswith("-"):
        if not makefile:
            return f"`{shown}` (no Makefile)"
        if not re.search(rf"(?m)^{re.escape(words[1])}\s*:", makefile):
            return f"`{shown}` (no make target {words[1]})"
    if words[0].startswith(("./", "scripts/")) and not (root / words[0]).exists():
        return f"`{shown}` (no file {words[0]})"
    return None


def plan_front_door(root: Path, cli_values: dict[str, str]) -> RenderPlan:
    """P6: AGENTS.md and the README quickstart region, filled from verify.json (P5's green
    record) and checked against it: a mise command the text names that P5 did not run green
    refuses the render (R2)."""
    if toml_problem(root / MANIFEST) or not (root / MANIFEST).is_file():
        raise Refusal(f"no readable {MANIFEST}: P6 comes after P4 (init.py render) and P5")
    manifest = load_toml(root / MANIFEST)
    generated, kept, persisted = manifest_tables(manifest)
    given = {**persisted, **cli_values}
    migrated = manifest.get("migrated_from") == V2_NAME
    record = load_verify(root)
    start = table(record, "start")
    values: dict[str, str] = {"NAME": project_name(root)}
    ids = scenario_ids(root)
    if ids:
        values["TEST_TAG_EXAMPLE"] = f'@pytest.mark.spec("{ids[0]}")'
    values.update(given)
    values["START_EXAMPLE"] = str(start.get("command"))
    values["START_EXPECTED"] = one_line(str(start.get("output") or ""))
    recorded_origin = manifest.get("origin_url")
    hosted = isinstance(recorded_origin, str) and bool(recorded_origin.strip())
    hosted = hosted and not is_local_url(str(recorded_origin))
    if hosted:  # H31: a clone line only with a remote; P7 renders the region again after create
        values["CLONE_URL"] = public_url(str(recorded_origin))
        values["CLONE_DIR"] = url_tail(str(recorded_origin))
    flags: dict[str, bool | None] = {"IF_REMOTE": hosted}
    bad = unsafe_values(values)
    if bad:
        raise Refusal("render refused, unsafe values (nothing written):\n  " + "\n  ".join(bad))

    planned: list[Planned] = []
    unfilled: dict[str, list[str]] = {}
    agents, missing = fill((TEMPLATES / "AGENTS.md").read_text(encoding="utf-8"), values, {})
    for name in missing:
        unfilled.setdefault(name, []).append("AGENTS.md")
    quick = pad_start_line(
        (TEMPLATES / "README-quickstart.md").read_text(encoding="utf-8"),
        values["START_EXAMPLE"],
        values["START_EXPECTED"],
    )
    block, missing = fill(quick, values, flags)
    for name in missing:
        unfilled.setdefault(name, []).append("README.md")

    for dest in FRONT_DOOR:
        if leaves_repo(root, dest):
            raise Refusal(f"{dest}: its folder resolves outside the repo; nothing written")
        target = root / dest
        link = os.readlink(target) if target.is_symlink() else None
        if target.exists() and not target.is_file():
            raise Refusal(f"{dest} exists and is not a file; move it aside, then re-run")
        current = target.read_bytes() if target.is_file() else None
        mode = (target.stat().st_mode & 0o777) if current is not None else 0o644
        if dest == "AGENTS.md":
            planned.append(
                Planned(dest, "text", "AGENTS.md", agents.encode(), mode, current, link=link)
            )
            continue
        description = table(load_toml(root / "pyproject.toml"), "project").get("description")
        pitch = description if isinstance(description, str) else None
        pitch = None if pitch in (None, "", "Add your description here") else pitch
        new, now = readme_with_region(
            utf8(dest, current), block, values["NAME"], pitch, v2_quickstart=migrated
        )
        block_record = sha256(region_text(split_lines(block)[0]).encode())
        planned.append(
            Planned(
                dest,
                "region",
                "README-quickstart.md",
                new.encode(),
                mode,
                current,
                link=link,
                record=block_record,
                current_record=None if now is None else sha256(now.encode()),
            )
        )

    named = named_commands(agents) | named_commands(block)
    checks = record.get("checks")
    rows = checks if isinstance(checks, list) else []
    green = {str(c.get("key")) for c in rows if isinstance(c, dict) and c.get("green")}
    unproven = sorted(named - green - {f"mise run {t}" for t in HUMAN_TASKS})
    if unproven and not unfilled:
        raise Refusal(
            "front door refused: no green record in verify.json for "
            + ", ".join(f"`{c}`" for c in unproven)
            + " (R2). Go back to P5: re-run init.py selftest, never around it"
        )

    for item in planned:
        item.status = plan_status(root, item, generated.get(item.dest), kept.get(item.dest))
        if migrated:
            item.status = v2_status(item, generated.get(item.dest))
    data: dict[str, object] = dict(manifest)
    new_generated: dict[str, object] = dict(generated)
    for item in planned:
        if item.status not in (*HELD_STATUSES, "kept"):
            new_generated[item.dest] = item.record
    data.pop("values", None)
    data.pop("generated", None)
    seeded_table = data.pop("seeded", None)
    kept_table = data.pop("kept", None)
    if given:
        data["values"] = dict(sorted(given.items()))
    data["generated"] = dict(sorted(new_generated.items(), key=lambda kv: kv[0]))
    if seeded_table:
        data["seeded"] = seeded_table
    if kept_table:
        data["kept"] = kept_table
    # the templates this render is made from: a render that writes has an answer for every
    # file (written, ok, kept or forced), so each one now stands on the current template
    data[TEMPLATE_TABLE] = front_door_template_hashes()
    manifest_current = read_text(root / MANIFEST)
    context = (
        f"front door for {values['NAME']}: {values['START_EXAMPLE']}"
        + (f' -> "{values["START_EXPECTED"]}"' if values["START_EXPECTED"] else "")
        + f" (P5 record of {record.get('at', '?')})"
    )
    plan = RenderPlan(root, planned, emit_manifest(data), manifest_current, unfilled, context)
    readme = next(p for p in planned if p.dest == "README.md")
    if readme.current is not None:
        # the README as this render leaves it: a v2 `## Quickstart` it replaces is gone from
        # it, so its make lines and ONBOARDING.md pointer are not listed as the human's to fix.
        # Outside the region, a kept or held README reads the same as the rendered one.
        stale = readme_audit(root, readme.content.decode("utf-8", "replace"))
        plan.notes = [("readme", s) for s in stale]
    return plan


def front_door_template_hashes() -> dict[str, str]:
    """dest -> the sha256 of the template it is rendered from, as this skill has it now."""
    return {
        dest: sha256((TEMPLATES / source).read_bytes())
        for dest, source in FRONT_DOOR_TEMPLATES.items()
    }


def text_table(data: dict[str, object], name: str) -> dict[str, str]:
    return {k: v for k, v in table(data, name).items() if isinstance(v, str)}


def front_door_audit(
    root: Path, generated: dict[str, str], kept: dict[str, str], rendered_from: dict[str, str]
) -> list[tuple[str, str, str]]:
    """(status, dest, why) for each front-door file P6 recorded. The machinery render cannot
    re-render them without verify.json, so it judges two hashes. The file's own recorded hash
    shows an edit. The template's hash P6 recorded (TEMPLATE_TABLE) shows a template that
    moved since: an untouched file is then an upgrade, and a kept one is asked about again,
    as a kept machinery file is when its render changes. A file with no template hash on
    record counts as moved: nothing says it stands on the current template."""
    now_templates = front_door_template_hashes()
    rows: list[tuple[str, str, str]] = []
    for dest in FRONT_DOOR:
        recorded = generated.get(dest)
        if recorded is None:
            continue
        moved = rendered_from.get(dest) != now_templates[dest]
        unknown = dest not in rendered_from  # a manifest from before TEMPLATE_TABLE
        fresh = TEMPLATE_UNKNOWN if unknown else TEMPLATE_MOVED
        ask = KEPT_UNKNOWN if unknown else KEPT_MOVED
        path = root / dest
        if path.is_symlink():
            if dest in kept and not moved:
                rows.append(("kept", dest, ""))
            else:
                rows.append(("symlink", dest, ask if dest in kept else ""))
            continue
        if not path.is_file():
            rows.append(("missing", dest, ""))
            continue
        data = path.read_bytes()
        now: str | None = sha256(data)
        if dest == "README.md":
            lines, _ = split_lines(data.decode("utf-8", "replace"))
            try:
                bounds = region_bounds(lines)
            except Refusal:
                bounds = (0, -1)  # a broken region: not what P6 wrote
            region = region_text(lines[bounds[0] : bounds[1] + 1]) if bounds else None
            now = None if region is None else sha256(region.encode())
        if now == recorded:
            rows.append(("upgrade", dest, fresh) if moved else ("ok", dest, ""))
        elif dest in kept:
            rows.append(("customized", dest, ask) if moved else ("kept", dest, ""))
        else:
            rows.append(("missing" if now is None else "customized", dest, ""))
    return rows


TEMPLATE_MOVED = "its template changed since P6 rendered it: P6 renders it again"
TEMPLATE_UNKNOWN = (
    "no template hash on record, so it may be behind its template: P6 renders it again"
)
KEPT_MOVED = "kept, and its template changed since: P6 asks again, keep yours or take the render"
KEPT_UNKNOWN = "kept, with no template hash on record: P6 asks again, keep yours or take the render"


def front_door_measure(dest: str, data: bytes) -> str | None:
    """What [generated] records for a front-door file: the whole AGENTS.md, and only the
    quickstart region of README.md (None when it has none)."""
    if dest != "README.md":
        return sha256(data)
    lines, _ = split_lines(data.decode("utf-8", "replace"))
    try:
        bounds = region_bounds(lines)
    except Refusal:
        return None
    return sha256(region_text(lines[bounds[0] : bounds[1] + 1]).encode()) if bounds else None


def front_door_part(dest: str, data: bytes) -> str:
    """The part of a front-door file a customization is judged on (the README: its region)."""
    text = data.decode("utf-8", "replace")
    if dest != "README.md":
        return text
    lines, _ = split_lines(text)
    try:
        bounds = region_bounds(lines)
    except Refusal:
        return text
    return region_text(lines[bounds[0] : bounds[1] + 1]) if bounds else ""


def front_door_diff(root: Path, dest: str, recorded: str | None) -> str:
    """render --check on a customized front-door file (EXTEND's audit): the diff from the
    version P6 wrote, found in history by its recorded hash, to the file as it is. That is the
    edit the keep-or-take question is about; P6 shows the new render's diff when it runs."""
    path = root / dest
    if recorded is None or not path.is_file():
        return ""
    now = path.read_bytes()
    commits = git(root, "log", "--format=%H", "-n", "50", "--", dest).out.split()
    for commit in commits:
        shown = git(root, "show", f"{commit}:{dest}")
        if shown.code != 0:
            continue
        then = shown.out.encode("utf-8")
        if front_door_measure(dest, then) != recorded:
            continue
        ours = front_door_part(dest, then).splitlines(keepends=True)
        theirs = front_door_part(dest, now).splitlines(keepends=True)
        diff = difflib.unified_diff(
            ours, theirs, f"a/{dest} (as P6 wrote it, {commit[:10]})", f"b/{dest} (yours)"
        )
        return "".join(line if line.endswith("\n") else line + "\n" for line in diff)
    return (
        f"  (the {dest} P6 wrote is not in this branch's last 50 commits of it: P6 shows the "
        "diff, render --front-door)\n"
    )


def normalize_rel(path: str) -> str:
    rel = PurePosixPath(path.strip())
    if rel.is_absolute() or ".." in rel.parts:
        raise UsageError(f"{path}: give a path relative to the repo root")
    return rel.as_posix().removeprefix("./")


# ---------------------------------------------------------------------------------------------
# P7 publish: the ship commit, then (--remote github, D2) the remote steps


SHIP_SUBJECT = f"chore(init): {STANDARD}"
SHIP_UPGRADE = f"{SHIP_SUBJECT} upgrade"  # EXTEND: the default branch has a manifest
SHIPPED_LOCKFILES = ("uv.lock", "mise.lock")  # D3: committed in the init commit
PYTHON_PIN = ".python-version"  # prepare writes it when the repo pins none (P4)
PUBLISH_JSON = ".agent/project-init/publish.json"  # the remote steps done so far (local only)
REMOTE_STEPS = ("create", "push-default", "record", "push-branch", "settings")
SERVER_PENDING = "pending: EXTEND applies server rules after the first green CI run (N2, N23)"
SERVER_FREE = "unavailable: Free private"
# the name part never starts with "-": gh would read `--push` or `--public` as its own flag
REPO_NAME = re.compile(r"^(?:[A-Za-z0-9][A-Za-z0-9-]*/)?[A-Za-z0-9._][A-Za-z0-9._-]*$")
GAP_HEADING = re.compile(r"(?m)^###\s+Scenario:\s+\S+.*\[gap\b")


def z_split(text: str | None) -> list[str]:
    return [part for part in (text or "").split("\0") if part]


def ship_paths(root: Path, manifest: dict[str, object]) -> list[str]:
    """The ship commit's pathspec (N14: named paths, never -A): the manifest, every [generated]
    and [seeded] path, the constitution (specs/), the ADRs (project_memory/decisions/: P2's
    and P9's, which replace the .gitkeep seed), the test roots, the lockfiles and the Python
    pin prepare wrote. Only paths on disk or in the index are named (a tracked path gone from
    disk stages its deletion)."""
    tests = table(manifest, "paths").get("tests")
    wanted = [
        MANIFEST,
        *table(manifest, "generated"),
        *table(manifest, "seeded"),
        "specs",
        DECISIONS_DIR,
        *([str(t) for t in tests] if isinstance(tests, list) else ["tests"]),
        *SHIPPED_LOCKFILES,
        PYTHON_PIN,
    ]
    tracked = z_split(git(root, "ls-files", "-z").out)
    paths: list[str] = []
    for rel in dict.fromkeys(normalize_rel(str(p)) for p in wanted):
        on_disk = (root / rel).exists() or (root / rel).is_symlink()
        in_index = any(t == rel or t.startswith(rel + "/") for t in tracked)
        if on_disk or in_index:
            paths.append(rel)
    return paths


def ship_subject(root: Path, default: str) -> str:
    """`chore(init): project-init v3` for the first run; `... upgrade` for EXTEND, whose
    default branch already holds a .project.toml."""
    has = git(root, "cat-file", "-e", f"refs/heads/{default}:{MANIFEST}").code == 0
    return SHIP_UPGRADE if has else SHIP_SUBJECT


def not_staged(root: Path, paths: list[str]) -> list[str]:
    """Untracked files outside the ship pathspec: never added, listed for the human. The
    dry run shows them before anything is staged, the real run after."""
    others = z_split(git(root, "ls-files", "-z", "--others", "--exclude-standard").out)
    inside = (
        set(
            z_split(git(root, "ls-files", "-z", "--others", "--exclude-standard", "--", *paths).out)
        )
        if paths
        else set()
    )
    return [rel for rel in others if rel not in inside]


def staged_changes(root: Path) -> list[str]:
    """`git diff --cached --name-status` as `X  path` lines (renames as `R  old -> new`)."""
    parts = z_split(git(root, "diff", "--cached", "--name-status", "-z").out)
    lines: list[str] = []
    i = 0
    while i < len(parts):
        status = parts[i]
        if status[:1] in ("R", "C") and i + 2 < len(parts):
            lines.append(f"{status[:1]}  {parts[i + 1]} -> {parts[i + 2]}")
            i += 3
        elif i + 1 < len(parts):
            lines.append(f"{status[:1]}  {parts[i + 1]}")
            i += 2
        else:
            i += 1
    return lines


def render_notes(root: Path, default: str, manifest: dict[str, object]) -> list[str]:
    """What this ship does to the rendered files, against the .project.toml the default
    branch holds: for an EXTEND upgrade, the files it upgrades, adds or stops rendering; for
    every run, a file kept as the project wrote it (a new or changed [kept] row) and a kept
    file now taken from the render. G1's reviewer, and main's history after the squash, then
    read why the upgrade happened and which render was declined, not a bare manifest diff."""
    generated = {k: v for k, v in table(manifest, "generated").items() if isinstance(v, str)}
    kept = {k: v for k, v in table(manifest, "kept").items() if isinstance(v, str)}
    shown = git(root, "show", f"refs/heads/{default}:{MANIFEST}")
    try:
        before = parse_toml(shown.out) if shown.code == 0 else {}
    except ValueError:
        before = {}
    was = {k: v for k, v in table(before, "generated").items() if isinstance(v, str)}
    was_kept = {k: v for k, v in table(before, "kept").items() if isinstance(v, str)}
    lines: list[str] = []
    if was:  # EXTEND: the first adoption adds every file, and its file list says so already
        for what, names in (
            ("Upgraded to the current render", [k for k in generated if k in was]),
            ("Added", [k for k in generated if k not in was]),
            ("No longer rendered", [k for k in was if k not in generated]),
        ):
            names = sorted(n for n in names if generated.get(n) != was.get(n))
            if names:
                lines.append(f"{what}: {', '.join(names)}.")
    newly = sorted(k for k, v in kept.items() if was_kept.get(k) != v)
    if newly:
        lines.append(
            f"Kept as the project wrote it: {', '.join(newly)}. The new render was declined; "
            "the [kept] row in .project.toml asks again when its template changes."
        )
    taken = sorted(k for k in was_kept if k not in kept)
    if taken:
        lines.append(f"Taken from the render (kept before): {', '.join(taken)}.")
    return lines


def ship_body(
    root: Path, record: dict[str, object], manifest: dict[str, object], default: str
) -> str:
    """The ship commit's body (N21): P5's real results from verify.json, the probe gaps the
    capabilities carry, the adoption baselines, and what the render changed or kept
    (render_notes). Nothing here is typed by hand."""
    raw = record.get("checks")
    checks = [c for c in raw if isinstance(c, dict)] if isinstance(raw, list) else []
    green = sum(1 for c in checks if c.get("green"))
    matrix = table(record, "matrix")
    lines = [
        (
            f"P5 selftest ({record.get('at')}): verify.json green, {green} of {len(checks)} "
            f"checks green, the negative matrix exit {matrix.get('exit')}."
        ),
    ]
    for check in checks:
        state = "green" if check.get("green") else f"not green (exit {check.get('exit')})"
        optional = "" if check.get("required") else ", not required"
        lines.append(f"- {check.get('name')}: {state}{optional}")
    start = table(record, "start")
    if start.get("command"):
        shown = f' -> "{one_line(str(start.get("output")))}"' if start.get("output") else ""
        lines.append(f"Happy path: {start.get('command')}{shown}.")
    caps = root / "specs" / "capabilities"
    gaps = sum(
        len(GAP_HEADING.findall(read_text(path) or ""))
        for path in (sorted(caps.glob("*.md")) if caps.is_dir() else [])
    )
    lines.append(
        f"Probe gaps: {gaps} [gap] scenario(s) in specs/capabilities/."
        if gaps
        else "Probe gaps: none."
    )
    for key, what in (
        ("ruff_baseline", "ruff baseline"),
        ("ty_baseline", "ty baseline"),
        ("gitleaks_baseline", "history scan"),
    ):
        value = manifest.get(key)
        if isinstance(value, str) and value:
            lines.append(f"{what[:1].upper()}{what[1:]}: {value}.")
    lines += render_notes(root, default, manifest)
    return "\n".join(lines) + "\n"


def set_manifest_scalars(root: Path, updates: dict[str, str]) -> bool:
    """Top-level `key = "value"` lines of .project.toml set in place (inserted before the
    first table when missing); every other line untouched. True when the file changed."""
    path = root / MANIFEST
    text = read_text(path) or ""
    lines, newline = split_lines(text)
    first_table = next((i for i, ln in enumerate(lines) if ln.lstrip().startswith("[")), len(lines))
    changed = False
    for key, value in updates.items():
        want = f"{toml_key(key)} = {toml_value(value)}"
        for i in range(first_table):
            if re.match(rf"^{re.escape(key)}\s*=", lines[i]):
                if lines[i] != want:
                    lines[i] = want
                    changed = True
                break
        else:
            lines.insert(first_table, want)
            first_table += 1
            changed = True
    if changed:
        new = newline.join(lines) + newline
        parse_toml(new)
        install(root, MANIFEST, new.encode("utf-8"), path.stat().st_mode & 0o777)
    return changed


def steps_done(state: dict[str, object]) -> list[str]:
    done = state.get("done")
    return [str(step) for step in done] if isinstance(done, list) else []


def load_publish_state(root: Path) -> dict[str, object]:
    try:
        data = json.loads((root / PUBLISH_JSON).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_publish_state(root: Path, state: dict[str, object]) -> None:
    install(root, PUBLISH_JSON, (json.dumps(state, indent=2) + "\n").encode("utf-8"), 0o644)


SECRET_ROW = re.compile(r"^#\s*([A-Za-z_]\w*)\s*\|\s*secret\s*\|", re.MULTILINE)


def contract_secrets(contract: str) -> list[str]:
    """The names of the secret rows of an env contract. The template's kind legend names
    op:// too, and it is no secret of this project."""
    return list(dict.fromkeys(SECRET_ROW.findall(contract)))


def publish_punch_list(root: Path, manifest: dict[str, object], remote: bool) -> list[str]:
    """The human-only items P7 can see from here (the rest is Rai's, from the session)."""
    items: list[str] = []
    branch = run(["git", "config", "--global", "--get", "init.defaultBranch"], timeout=10)
    if branch.out.strip() != "main":
        items.append("git config --global init.defaultBranch main")
    secrets = contract_secrets(read_text(root / ".env.example") or "")
    if secrets:
        items.append(
            f"the 1Password items behind the {plural(len(secrets), 'secret')} in .env.example "
            f"({', '.join(secrets)})"
        )
    if remote:
        items.append(f"server rules: {manifest.get('server_protection') or SERVER_PENDING}")
    surface = ui_surface(root)
    if surface.setup:
        items.append(f"{surface.setup} ({surface.evidence}): the capture tools for its proof")
    ignored = read_text(root / ".gitleaksignore")
    found = secret_rules(
        [ln.strip() for ln in (ignored or "").splitlines() if ln.strip() and ln[:1] != "#"]
    )
    if found:
        rules = ", ".join(f"{rule} {n}" for rule, n in sorted(found.items()))
        items.append(
            f"rotate the secrets .gitleaksignore fingerprints ({rules}; rule and file, never "
            "values)"
        )
    readme = read_text(root / "README.md")
    stale = readme_audit(root, readme) if readme is not None else []
    if stale:
        items.append(
            "README.md: fix by hand what P6 listed as stale (prose is never rewritten): "
            + "; ".join(s.split(": ", 1)[1] for s in stale)
        )
    if NO_OWNER in (read_text(root / ".github" / "CODEOWNERS") or ""):
        items.append("fill the Ownership table in project_memory/team.md, then re-run render")
    qroot = Path.home() / ".local" / "state" / "project-init" / "quarantine"
    for folder, state in earlier_quarantines(root, qroot, repo_display_name(root)):
        if state.get("state") in ("archived", "held"):
            held = state.get("held")
            first = f"; first look at its {HELD}/" if isinstance(held, dict) and held else ""
            items.append(f"delete {folder} after you confirm the archive{first}")
    return items


def remote_plan(
    repo: str, description: str | None, default: str, branch: str
) -> list[tuple[str, str]]:
    """(step, the command it runs) for the five remote steps. The default branch is pushed
    before record: record asks GitHub about that branch's protection, so the branch must be
    there, and record amends only the ship commit on the branch, which goes up after it."""
    create = ["gh", "repo", "create", repo, "--private", "--source", ".", "--remote", "origin"]
    if description:
        create += ["-d", description]
    return [
        ("create", shlex.join(create)),
        ("push-default", shlex.join(["git", "push", "-u", "origin", default])),
        (
            "record",
            (
                f"origin_url and server_protection (gh api repos/<owner>/{repo}/branches/"
                f"{default}/protection) written to {MANIFEST}, and the README quickstart "
                f"rendered again with its clone line; git add -- {MANIFEST} README.md; "
                "git commit --amend --no-edit"
            ),
        ),
        ("push-branch", shlex.join(["git", "push", "-u", "origin", branch])),
        (
            "settings",
            shlex.join(
                [
                    "gh",
                    "repo",
                    "edit",
                    "--default-branch",
                    default,
                    "--delete-branch-on-merge",
                    "--enable-squash-merge",
                ]
            ),
        ),
    ]


def protection_state(slug: str, branch: str, cwd: Path | None = None) -> str | None:
    """What GitHub says about server rules on a branch: SERVER_FREE when its protection API
    answers 403 'Upgrade to GitHub Pro' (a private repo on the Free plan has none, so the
    state is recorded once and never retried), else None: rules are possible, or the answer
    is unclear, and the state stays pending. `gh api user` cannot tell: its plan needs the
    `user` scope, which gh's default login lacks."""
    result = run(["gh", "api", f"repos/{slug}/branches/{branch}/protection"], cwd=cwd, timeout=30)
    if result.code != 0 and re.search(r"(?i)upgrade to github pro", result.out + result.err):
        return SERVER_FREE
    return None


def refresh_quickstart(root: Path) -> str | None:
    """P7 once it created the remote: the README quickstart region rendered again, now with its
    clone line (H31), and its [generated] hash updated. Only while the region is still the one
    P6 wrote (a region the human kept is theirs). What changed, or None."""
    plan = plan_front_door(root, {})
    readme = next(p for p in plan.planned if p.dest == "README.md")
    if readme.status not in ("missing", "upgrade"):
        return None
    put(root, readme)
    manifest = load_toml(root / MANIFEST)
    generated = {k: v for k, v in table(manifest, "generated").items() if isinstance(v, str)}
    generated["README.md"] = readme.record
    manifest["generated"] = dict(sorted(generated.items(), key=lambda kv: kv[0]))
    install(root, MANIFEST, emit_manifest(manifest).encode("utf-8"), 0o644)
    return "quickstart region rendered again: it opens with the clone line"


class StepFailed(Exception):
    def __init__(self, step: str, result: Result) -> None:
        detail = one_line((result.err or result.out).strip()[-400:])
        super().__init__(f"exit {result.code}: {detail}")
        self.step = step


def run_remote_steps(
    root: Path, steps: list[tuple[str, str]], state: dict[str, object], default: str, branch: str
) -> None:
    """The remote steps not yet in state["done"], each recorded as soon as it succeeds, so a
    re-run after a failure picks up at the step that failed (create never runs twice)."""
    done = steps_done(state)
    env = git_env()
    name_of = dict(steps)
    for step, _ in steps:
        if step in done:
            continue
        if step == "create":
            result = run(shlex.split(name_of["create"]), cwd=root, env=env, timeout=120)
            if result.code != 0:
                raise StepFailed(step, result)
            state["origin"] = origin_url(root) or ""
        elif step == "record":
            origin = configured_origin(root) or ""
            slug = github_slug(origin)
            server = (protection_state(slug, default, root) if slug else None) or SERVER_PENDING
            changed = set_manifest_scalars(
                root, {"origin_url": origin, "server_protection": server}
            )
            try:
                readme = refresh_quickstart(root)
            except Refusal as exc:
                raise StepFailed(step, Result(1, "", f"README quickstart: {exc}")) from exc
            if changed or readme:
                for argv in (
                    ["add", "--", MANIFEST, *(["README.md"] if readme else [])],
                    ["commit", "--amend", "--no-edit", "--quiet"],
                ):
                    result = git(root, *argv, timeout=900)
                    if result.code != 0:
                        raise StepFailed(step, result)
            if readme:
                print(label("README.md") + readme)
        elif step == "push-default":
            result = git(root, "push", "-u", "origin", default, timeout=300)
            if result.code != 0:
                raise StepFailed(step, result)
        elif step == "push-branch":
            result = git(root, "push", "-u", "origin", branch, timeout=300)
            if result.code != 0:
                raise StepFailed(step, result)
        else:
            result = run(shlex.split(name_of["settings"]), cwd=root, env=env, timeout=120)
            if result.code != 0:
                raise StepFailed(step, result)
        done.append(step)
        state["done"] = done
        save_publish_state(root, state)
        print(label(step) + "ok")


def cmd_publish(args: argparse.Namespace) -> int:
    root = repo_root(args.repo)
    if not is_git_root(root) or not has_commits(root):
        raise Refusal("publish: not a git repo with a commit")
    manifest = load_toml(root / MANIFEST)
    default = detect_default_branch(root, manifest)
    branch = git_out(root, "symbolic-ref", "-q", "--short", "HEAD")
    if not branch:
        raise Refusal("publish refused: HEAD is detached; switch to plan/project-init")
    if branch == default:
        raise Refusal(
            f"publish refused: HEAD is on {default}. The ship commit goes on plan/project-init "
            "(EXTEND: its own branch), and G1 merges it"
        )
    if toml_problem(root / MANIFEST) or not (root / MANIFEST).is_file():
        raise Refusal(f"publish refused: no readable {MANIFEST}; P7 comes after P4, P5 and P6")
    generated, _, _ = manifest_tables(manifest)
    if "AGENTS.md" not in generated:
        raise Refusal(
            "publish refused: P6 has not run (AGENTS.md is not in .project.toml [generated]); "
            "run render --front-door first"
        )
    record = load_verify(root, "publish")
    ahead_text = git_out(root, "rev-list", "--count", f"refs/heads/{default}..HEAD")
    if ahead_text is None:
        raise Refusal(f"publish refused: no local {default} branch to ship against")
    ahead = int(ahead_text)
    subject = ship_subject(root, default)
    head_subject = git_out(root, "log", "-1", "--format=%s") or ""
    shipped = ahead == 1 and head_subject == subject
    if ahead and not shipped:
        raise Refusal(
            f"publish refused: {branch} holds {plural(ahead, 'commit')} beyond {default}; P7 "
            f"makes one ship commit ({subject}) on top of {default}"
        )
    paths = ship_paths(root, manifest)
    # an ignored path would make `git add` fail; the standard commits every one of them
    check = git(root, "-c", "core.quotePath=false", "check-ignore", "--", *paths)
    ignored = check.out.splitlines() if check.code == 0 else []
    name = project_name(root)
    description = table(load_toml(root / "pyproject.toml"), "project").get("description")
    pitch = description if isinstance(description, str) and description else None
    origin = origin_url(root)
    state = load_publish_state(root)
    ours = bool(origin) and state.get("origin") == origin  # a publish of ours created it
    remote = args.remote == "github" and (not origin or ours)
    # the GitHub repo is named after the folder, not the distribution: --repo overrides it
    repo_name = args.repo_name or root.name
    if remote and (not REPO_NAME.match(repo_name) or repo_name.rsplit("/", 1)[-1] in (".", "..")):
        raise UsageError(
            f"{repo_name!r} is not a GitHub repo name: pass --repo <name> (letters, digits, "
            ". _ -, not starting with -, optionally <owner>/<name>)"
        )
    steps = remote_plan(repo_name, pitch, default, branch) if remote else []
    body = ship_body(root, record, manifest, default)
    agent = z_split(git(root, "ls-files", "-z", "--", ".agent").out)  # D7: never shipped tracked
    untrack = (
        f".agent/ is still tracked ({plural(len(agent), 'file')}). D7: P2 read it as intake; "
        "run `git rm -r -q --cached .agent` (P4), then re-run publish"
    )

    if args.dry_run:
        print(f"publish --dry-run: {name} on {branch}; nothing runs")
        print(label("stage") + f"git add -- <{plural(len(paths), 'path')}>, then git add -u:")
        would = git(root, "add", "--dry-run", "--", *paths).out.splitlines()
        would += git(root, "add", "--dry-run", "-u").out.splitlines()
        pending = [*staged_changes(root), *dict.fromkeys(would)]
        for line in pending:
            print(INDENT + line)
        if ignored:
            print(label("IGNORED") + "publish refuses until .gitignore stops ignoring:")
            for rel in ignored:
                print(INDENT + rel)
        if agent:
            print(label("D7") + "publish refuses: " + untrack)
        left = not_staged(root, paths)
        if left:
            print(label("not staged") + "not project-init's; stage them by hand if they belong:")
            for rel in left:
                print(INDENT + rel)
        if shipped and not pending:  # the real run leaves the one ship commit as it is
            head = git_out(root, "rev-parse", "--short", "HEAD")
            print(label("commit") + f"{subject} (already: {head}; nothing new, no amend)")
        elif not pending:
            print(label("commit") + "nothing to commit: publish would refuse (did P4 run?)")
        else:
            verb = "amend" if shipped else "commit"
            print(label(verb) + f"{subject} (on {branch})")
            for line in body.splitlines():
                print(INDENT + line)
        if steps:
            print(label("remote") + "the P7 remote sequence (D2: a private GitHub repo):")
            done = steps_done(state) if ours else []
            for i, (step, command) in enumerate(steps, 1):
                print(f"  {i}. {command}" + ("  (done)" if step in done else ""))
            print(
                f"  no --push on create: {default} goes first, and pre-push lets it through "
                f"while origin lacks {default} (N10)"
            )
        elif origin:
            print(label("remote") + f"origin already set ({origin}); EXTEND takes the remote steps")
        else:
            print(
                label("remote")
                + "none (local only)"
                + ("" if args.remote else "; --remote github adds one")
            )
        return 0

    if agent:
        raise Refusal(f"publish refused: {untrack}. Nothing staged")
    if ignored:
        raise Refusal(
            "publish refused: .gitignore ignores paths the ship commit needs ("
            + ", ".join(ignored)
            + "); un-ignore them, then re-run. Nothing staged"
        )
    auth = run(["gh", "auth", "status"], cwd=root, timeout=30) if remote and not origin else None
    if auth is not None and auth.code != 0:
        why = "gh is not installed" if auth.code == 127 else "gh is not logged in (`gh auth login`)"
        raise Refusal(f"publish refused: {why}; nothing staged (punch list)")
    for argv in (["add", "--", *paths], ["add", "-u"]):
        result = git(root, *argv, timeout=300)
        if result.code != 0:
            raise Refusal(f"publish: git {argv[0]} failed: {result.err.strip()[-300:]}")
    changes = staged_changes(root)
    if not changes and not shipped:
        raise Refusal("publish refused: nothing to commit (did P4 run?)")
    if changes:
        print(label("staged") + f"{plural(len(changes), 'change')} (pathspec, never -A):")
        for line in changes:
            print(INDENT + line)
    left = not_staged(root, paths)
    if left:
        print(label("not staged") + "not project-init's; stage them by hand if they belong:")
        for rel in left:
            print(INDENT + rel)
    if not changes:
        head = git_out(root, "rev-parse", "--short", "HEAD")
        print(label("committed") + f"{branch}: {subject} (already: {head}; nothing new)")
    else:
        message = f"{subject}\n\n{body}"
        argv = ["commit", "--amend", "--quiet", "-F"] if shipped else ["commit", "--quiet", "-F"]
        fd, message_file = tempfile.mkstemp(prefix="project-init-ship-", suffix=".txt")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(message)
            result = git(root, *argv, message_file, timeout=900)
        finally:
            Path(message_file).unlink(missing_ok=True)
        if result.code != 0:
            sys.stdout.flush()
            print((result.out + result.err).strip()[-2000:], file=sys.stderr)
            raise Refusal(
                "publish: the commit was refused (the repo's hooks name why, above). The "
                "changes stay staged: fix them, then re-run publish"
            )
        locked = any(line.endswith("  uv.lock") for line in changes)
        verb = " (amended)" if shipped else ""
        lock_note = " (uv.lock included)" if locked else ""
        print(label("committed") + f"{branch}: {subject}{verb}{lock_note}")

    if steps:
        try:
            run_remote_steps(root, steps, state, default, branch)
        except StepFailed as exc:
            number = [s for s, _ in steps].index(exc.step) + 1
            half = (
                f" The GitHub repo exists: re-run publish --remote github to continue from step "
                f"{number}."
                if exc.step != "create"
                else " Never re-run gh repo create blindly: check `gh repo view` first, and "
                "delete a half-made repo by hand (the token has no delete_repo scope)."
            )
            raise Refusal(
                f"publish: remote step {number} ({exc.step}) failed ({exc}).{half}"
            ) from exc
        manifest = load_toml(root / MANIFEST)
        print(
            label("remote")
            + f"{configured_origin(root)} (private; {manifest.get('server_protection')})"
        )
    elif origin:
        print(label("remote") + f"origin already set ({origin}); EXTEND takes the remote steps")
    else:
        print(label("remote") + "none (local only)")
    print(label("next") + "review, then `! mise run merge`; then /clear before the first /sdd")
    items = publish_punch_list(root, manifest, remote=bool(steps))
    for i, item in enumerate(items):
        print((label("punch list") if i == 0 else INDENT) + item)
    return 0


# ---------------------------------------------------------------------------------------------
# EXTEND + v2 migrate: the one migration prompt, then the approved moves and deletions (P9)


@dataclass
class V2Item:
    path: str
    action: str  # mv | rm | adr | keep | render | hooks | solo
    fate: str


V2_FATES: tuple[tuple[str, str, str], ...] = (
    (".mise.toml", "mv", "git mv to mise.toml; the P4 render drops the python pin"),
    ("project_memory/facts.md", "rm", "P2 intake (tech-stack, mission glossary), then deleted"),
    (
        "project_memory/decisions.md",
        "adr",
        "each D-NNN becomes decisions/<date>-<slug>.md with aliases: [D-NNN] (P2), then deleted",
    ),
    ("project_memory/lessons.md", "keep", "kept, unchanged"),
    ("project_memory/log.md", "rm", "deleted (D5)"),
    ("docs/spec.md", "rm", "P2 intake, then deleted"),
    ("Makefile", "rm", "deleted"),
    ("scripts/doctor.sh", "rm", "deleted"),
    ("scripts/verify.sh", "rm", "deleted"),
    ("scripts/git-hooks", "rm", "deleted"),
    ("ONBOARDING.md", "rm", "deleted"),
    (".claude/hooks", "hooks", "unregistered from the settings files, then deleted"),
    (".claude/skills/run", "rm", "deleted"),
    (".claude/skills/verify", "rm", "deleted"),
    (".claude/skills/release", "rm", "deleted"),
    (".mcp.json", "rm", "deleted"),
    (".claude/settings.json", "render", "re-rendered (P4)"),
    (".github/CODEOWNERS", "solo", "deleted in the solo tier (D9)"),
    (".github/pull_request_template.md", "solo", "deleted in the solo tier (D9)"),
    ("project_memory/team.md", "solo", "deleted in the solo tier (D9)"),
    (
        "project_memory/.gitattributes",
        "rm",
        "deleted; the root .gitattributes carries the union-merge line",
    ),
    ("AGENTS.md", "render", "P2 intake, then replaced by the v3 render (P6)"),
    ("project_memory/README.md", "render", "replaced by the v3 render (P4)"),
    (".env.example", "render", "replaced by the v3 render (P4)"),
    (".editorconfig", "render", "replaced by the v3 render (P4)"),
    (V2_CI, "render", "replaced by the v3 render: job verify, push branch = the default (P4)"),
    ("CHANGELOG.md", "keep", "kept; the G1 merge regenerates it from history"),
    ("tests/test_smoke.py", "keep", "kept: product code, not v2 machinery"),
)
# what a v2 lesson may name that this migration removes or reverses
V2_LESSON_TERMS = (
    ".claude/hooks",
    "extend-exclude",
    "Makefile",
    "make setup",
    "make doctor",
    "make verify",
    "scripts/doctor.sh",
    "scripts/verify.sh",
    "scripts/git-hooks",
    "ONBOARDING.md",
    "log.md",
    "facts.md",
    "decisions.md",
    ".mise.toml",
)
# v2 commands the migration replaces with a v3 task of the same name that judges differently:
# a lesson that names one bare states v2 behaviour ("doctor fails on set-but-empty", while v3's
# `mise run doctor` reads an empty value as unset: H17)
V2_LESSON_WORDS = ("doctor",)
DECISION_ID = re.compile(r"(?m)^##\s+(D-\d+)\b")


def v2_items(root: Path) -> list[V2Item]:
    """Each v2 item this repo has, with its fate from 9-migrate.md, in the table's order."""
    tier = "team" if len(human_authors(root)) >= 2 else "solo"
    tracked = z_split(git(root, "ls-files", "-z").out)
    items: list[V2Item] = []
    for path, action, fate in V2_FATES:
        present = (root / path).exists() or any(
            t == path or t.startswith(path + "/") for t in tracked
        )
        if not present:
            continue
        if action == "solo" and tier == "team":
            if path.startswith(".github"):
                action, fate = "render", "re-rendered (team tier)"
            else:
                action, fate = "keep", "kept (team tier)"
        items.append(V2Item(path, action, fate))
    readme = read_text(root / "README.md")
    if readme is not None and quickstart_section(split_lines(readme)[0]):
        items.append(
            V2Item("README.md ## Quickstart", "render", "replaced by the v3 quickstart region (P6)")
        )
    if ".claude" in ruff_extend_exclude(read_text(root / "pyproject.toml") or ""):
        items.append(
            V2Item(
                "pyproject.toml extend-exclude .claude",
                "exclude",
                "removed; the P4 render adds the two tool-owned files",
            )
        )
    return items


def ruff_extend_exclude(text: str) -> list[str]:
    try:
        value = table(parse_toml(text), "tool", "ruff").get("extend-exclude")
    except ValueError:
        return []
    return [str(v) for v in value] if isinstance(value, list) else []


RETIRED = re.compile(r"(?i)^retired:\s*")


def lesson_heading(title: str) -> str:
    """A lesson title without its `<date> | ` prefix: what a retiring entry's
    `Retired: <old title>` names, with or without the old date."""
    head, sep, rest = title.partition("|")
    named = rest if sep and re.fullmatch(r"\s*\d{4}-\d{2}-\d{2}\s*", head) else title
    return " ".join(named.split())


def stale_v2_lessons(root: Path) -> list[tuple[str, list[str]]]:
    """(title, terms) of each lesson that names what the migration removes or reverses and
    has no retiring entry yet. The lessons stay unchanged (union-merged, append-only); P2
    appends `## <date> | Retired: <old title>` for each, and neither that entry nor the lesson
    it retires is listed again."""
    text = read_text(root / "project_memory" / "lessons.md") or ""
    lessons: list[tuple[str, str]] = []
    retired: set[str] = set()
    for block in re.split(r"(?m)^(?=##\s)", text):
        if not block.startswith("##"):
            continue
        title = block.splitlines()[0].lstrip("#").strip()
        heading = lesson_heading(title)
        if RETIRED.match(heading):
            retired.add(lesson_heading(RETIRED.sub("", heading)).casefold())
            continue
        lessons.append((title, block))
    found: list[tuple[str, list[str]]] = []
    for title, block in lessons:
        terms = [term for term in V2_LESSON_TERMS if term in block]
        terms += [
            word
            for word in V2_LESSON_WORDS
            if re.search(rf"\b{word}\b", block) and not any(word in term for term in terms)
        ]
        if terms and lesson_heading(title).casefold() not in retired:
            found.append((title, terms))
    return found


def adr_aliases(root: Path) -> set[str]:
    """The D-NNN ids the ADRs in project_memory/decisions/ carry in their `aliases:`."""
    ids: set[str] = set()
    folder = root / DECISIONS_DIR
    if not folder.is_dir():
        return ids
    for path in sorted(folder.glob("*.md")):
        text = read_text(path) or ""
        match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
        front = match.group(1) if match else ""
        aliases = re.search(r"(?ms)^aliases:(.*?)(?=^\S|\Z)", front)
        if aliases:
            ids.update(re.findall(r"\bD-\d+\b", aliases.group(1)))
    return ids


def drop_claude_exclude(text: str) -> str | None:
    """pyproject.toml without the v2 `.claude` entry in [tool.ruff] extend-exclude (the line
    goes when nothing else is left in it), or None when the entry is not there."""
    if ".claude" not in ruff_extend_exclude(text):
        return None
    lines, newline = split_lines(text)
    ruff = next((t for t in toml_tables(lines) if t.name == ("tool", "ruff")), None)
    if ruff is None or "extend-exclude" not in ruff.keys:
        raise Refusal(
            "pyproject.toml: [tool.ruff] extend-exclude is written as a dotted key; remove the "
            "`.claude` entry there, then re-run"
        )
    first, last = ruff.keys["extend-exclude"]
    rest = [v for v in ruff_extend_exclude(text) if v != ".claude"]
    new = [f"extend-exclude = [{', '.join(toml_value(v) for v in rest)}]"] if rest else []
    return newline.join(lines[:first] + new + lines[last + 1 :]) + newline


def unregister_v2_hooks(root: Path, marker: str = ".claude/hooks/") -> list[str]:
    """The settings files that registered a hook command naming marker (v2: any .claude/hooks/
    script; v1: the project-session-*.py pair), rewritten without those entries. A hook whose
    script is gone exits 2, and Claude Code reads that as a block of every Bash call, so they
    go before the scripts do."""
    changed: list[str] = []
    for rel in (".claude/settings.json", ".claude/settings.local.json"):
        path = root / rel
        text = read_text(path) if path.is_file() and not path.is_symlink() else None
        if text is None or marker not in text:
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise Refusal(f"{rel} is not JSON ({exc}); fix it, then re-run") from exc
        hooks = data.get("hooks") if isinstance(data, dict) else None
        if not isinstance(hooks, dict):
            continue
        for event in list(hooks):
            groups = hooks[event] if isinstance(hooks[event], list) else []
            kept = []
            for group in groups:
                inner = group.get("hooks", []) if isinstance(group, dict) else []
                inner = [
                    h
                    for h in inner
                    if not (isinstance(h, dict) and marker in str(h.get("command", "")))
                ]
                if inner:
                    kept.append({**group, "hooks": inner})
            if kept:
                hooks[event] = kept
            else:
                del hooks[event]
        if not hooks:
            del data["hooks"]
        install(root, rel, (json.dumps(data, indent=2) + "\n").encode("utf-8"), 0o644)
        changed.append(rel)
    return changed


def cmd_migrate_v2(args: argparse.Namespace) -> int:
    root = repo_root(args.repo)
    if not is_git_root(root) or not has_commits(root):
        raise Refusal("migrate-v2: not a git repo with a commit")
    stamped = any(
        V2_STAMP.search(read_text(root / rel) or "")
        for rel in ("project_memory/README.md", "AGENTS.md")
    )
    items = v2_items(root)
    lessons = stale_v2_lessons(root)
    todo = [i for i in items if i.action in ("mv", "rm", "adr", "hooks", "solo", "exclude")]
    if not args.apply:
        if not stamped:
            raise Refusal("migrate-v2: no `Standard: project-init v2` stamp; not a v2 repo")
        print(label("migrate") + f"project-init v2 -> v3, {plural(len(items), 'item')}:")
        width = max((len(i.path) for i in items), default=0)
        for item in items:
            print(f"  {item.path.ljust(width)}  {item.fate}")
        for title, terms in lessons:
            print(
                label("lesson") + f'"{title}" names what this migration removes or replaces '
                f"({', '.join(terms)}): kept; P2 appends a lesson that retires it"
            )
        print("1. Apply all (Recommended: every fate above is the approved v3 home)")
        print("2. Stop")
        print(
            label("next")
            + "on a yes: P2, then `git switch -c plan/project-init` and init.py migrate-v2 --apply"
        )
        return 0

    manifest = load_toml(root / MANIFEST)
    default = detect_default_branch(root, manifest)
    branch = git_out(root, "symbolic-ref", "-q", "--short", "HEAD")
    if not branch or branch == default:
        raise Refusal(
            f"migrate-v2 --apply refused: HEAD is {branch or 'detached'}; the moves land on "
            "plan/project-init (git switch -c plan/project-init first). Nothing changed"
        )
    if not todo:
        print("migrate-v2: nothing left to apply")
        return 0
    decisions = read_text(root / "project_memory" / "decisions.md") or ""
    missing = sorted(set(DECISION_ID.findall(decisions)) - adr_aliases(root))
    if missing:
        raise Refusal(
            "migrate-v2 --apply refused: no ADR in project_memory/decisions/ carries "
            f"aliases: [{', '.join(missing)}]. P2 writes them from decisions.md first. Nothing "
            "changed"
        )
    if any(i.action == "mv" for i in todo) and (root / "mise.toml").exists():
        raise Refusal(
            "migrate-v2 --apply refused: both .mise.toml and mise.toml exist; keep one, then "
            "re-run. Nothing changed"
        )
    for item in todo:
        if item.action == "mv":
            moved = git(root, "mv", "--", ".mise.toml", "mise.toml")
            if moved.code != 0:
                raise Refusal(f"migrate-v2: git mv .mise.toml failed: {moved.err.strip()}")
            print(f"  {'moved':<12} .mise.toml -> mise.toml")
        elif item.action == "exclude":
            text = read_text(root / "pyproject.toml") or ""
            new = drop_claude_exclude(text)
            if new is not None:
                install(root, "pyproject.toml", new.encode("utf-8"), 0o644)
                print(f"  {'edited':<12} pyproject.toml: `.claude` left [tool.ruff] extend-exclude")
    for rel in unregister_v2_hooks(root):
        print(f"  {'edited':<12} {rel}: the .claude/hooks/ entries are gone")
    gone = [i.path for i in todo if i.action in ("rm", "adr", "hooks", "solo")]
    tracked = z_split(git(root, "ls-files", "-z", "--", *gone).out) if gone else []
    if tracked:
        removed = git(root, "rm", "-r", "-q", "--", *gone_tracked(gone, tracked))
        if removed.code != 0:
            raise Refusal(f"migrate-v2: git rm failed: {removed.err.strip()[-300:]}")
    for rel in gone:
        if (root / rel).exists():
            print(f"  {'left':<12} {rel} (untracked files: not project-init's to delete)")
        else:
            print(f"  {'deleted':<12} {rel}")
    for title, _ in lessons:  # only the ones P2 has not retired yet
        print(
            label("lesson") + f'"{title}" stays, and no lesson retires it yet: append '
            f"`## <date> | Retired: {lesson_heading(title)}` (P2, 9-migrate.md)"
        )
    print(label("next") + "init.py render (P4): the v2 files the prompt covered render as upgrades")
    return 0


def gone_tracked(gone: list[str], tracked: list[str]) -> list[str]:
    """The paths of gone that git tracks (a file, or a folder with tracked files)."""
    return [p for p in gone if any(t == p or t.startswith(p + "/") for t in tracked)]


# ---------------------------------------------------------------------------------------------
# MIGRATE (v1 JSON layout): the moves P4 applies after the transcript step (9-migrate.md)


LEGACY_KNOWLEDGE = f"{LEGACY_BASE}/accumulated_knowledge.json"
KNOWLEDGE_REPORT = "legacy-knowledge.md"  # specs/backlog/<date>-legacy-knowledge.md
# the v1 block in .gitignore (helios): its comment lines, the four store folders and the
# negation that kept accumulated_knowledge.json tracked. migrate-v1 --apply removes them
V1_IGNORE_COMMENTS = frozenset(
    {"# Project Memory (personal, not shared)", "# Keep the structure and accumulated knowledge"}
)
V1_IGNORE_LINE = re.compile(
    r"^/?project_memory/(?:pending|sessions|chromadb|summaries)(?:/|/\*{1,2})?$"
    r"|^!/?project_memory/accumulated_knowledge\.json$"
)
# the knowledge sections, in the order the report lists them; other list-valued keys follow
KNOWLEDGE_SECTIONS = (
    ("decisions", "Decisions"),
    ("patterns", "Patterns"),
    ("gotchas", "Gotchas"),
    ("technical_learnings", "Technical learnings"),
    ("open_threads", "Open threads"),
    ("dependencies", "Dependencies"),
)
KNOWLEDGE_SKIPPED = ("recent_files", "tags_index")  # file lists and tags, not knowledge
VAULT_PATH = re.compile(
    r"(?:~[A-Za-z0-9._-]*|\$HOME|\$\{HOME\})/helm\b\S*|(?<![/\w])helm/0[0-9]-\S*"
)
HOME_PATH = re.compile(r"(?<![\w.-])/(?:home|Users)/[A-Za-z][A-Za-z0-9._-]*")
WIKI_LINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")


def sanitize(text: str) -> tuple[str, int]:
    """text for a tracked doc (2-talk.md, Sanitize): a vault path becomes `<vault path>`, a
    home folder `~`, a [[wiki-link]] its words. The leak rules would refuse the commit
    otherwise. Returns the count of changes."""
    text, vault = VAULT_PATH.subn("<vault path>", text)
    text, home = HOME_PATH.subn("~", text)
    text, links = WIKI_LINK.subn(lambda m: m.group(2) or m.group(1), text)
    return text, vault + home + links


def _knowledge_line(item: object) -> str | None:
    """One report line for a knowledge entry: a string as it is, a decision as `<date>: <what>.
    Why: <rationale>` (dated by `date`, else `decided`), any other mapping as key: value."""
    if isinstance(item, str):
        text = item
    elif isinstance(item, dict):
        date = item.get("date") or item.get("decided")
        what = next(
            (item[k] for k in ("decision", "what", "title", "text", "summary") if item.get(k)),
            None,
        )
        why = item.get("rationale") or item.get("why")
        if what is not None:
            text = f"{date}: {what}" if date else str(what)
            text += f". Why: {why}" if why else ""
        else:
            text = "; ".join(f"{k}: {v}" for k, v in item.items() if v not in (None, "", []))
    else:
        text = str(item) if item not in (None, "") else ""
    text = " ".join(str(text).split())
    return text or None


def knowledge_report(data: dict[str, object], snapshot: str) -> tuple[str, int, dict[str, int]]:
    """(the backlog report, sanitized count, entries per section) for accumulated_knowledge."""
    sections: list[tuple[str, list[str]]] = []
    named = dict(KNOWLEDGE_SECTIONS)
    keys = [k for k, _ in KNOWLEDGE_SECTIONS] + sorted(
        k for k, v in data.items() if k not in named and isinstance(v, list | dict)
    )
    for key in keys:
        if key in KNOWLEDGE_SKIPPED or key not in data:
            continue
        value = data[key]
        lines: list[str] = []
        if isinstance(value, dict):  # dependencies: {added: {name: date}, removed: [...]}
            for sub, items in value.items():
                if isinstance(items, dict):
                    items = [f"{k} ({v})" if v not in (None, "") else k for k, v in items.items()]
                for item in items if isinstance(items, list) else [items]:
                    line = _knowledge_line(item)
                    if line:
                        lines.append(f"{sub}: {line}")
        elif isinstance(value, list):
            lines = [line for item in value if (line := _knowledge_line(item))]
        if lines:
            sections.append((named.get(key) or key.replace("_", " ").capitalize(), lines))
    counts = {title: len(lines) for title, lines in sections}
    listed = ", ".join(f"{n} {title.lower()}" for title, n in counts.items()) or "no entries"
    skipped = [k for k in KNOWLEDGE_SKIPPED if k in data]
    out = [
        "---",
        "status: open                                    # open | scheduled",
        "roadmap:                                        # the roadmap slug, once scheduled",
        "---",
        (
            "<!-- backlog item: an idea, spike finding or abandoned change that is not being "
            "built now. Deleted when its work starts or a replan drops it. No line cap. -->"
        ),
        "# Review the legacy knowledge",
        "",
        f"> Snapshot {snapshot} of `{LEGACY_KNOWLEDGE}`, unreviewed.",
        "",
        "## What",
        (
            f"The v1 memory's accumulated knowledge, rendered once when the JSON store was "
            f"retired: {listed}. None of it is reviewed; P2 read the JSON as intake. Turn a line "
            "that still holds into an ADR in `project_memory/decisions/`, a lesson, a scenario "
            "or a roadmap item, then delete the line. Delete this file when nothing is left."
        ),
        "",
        "## Why",
        (
            "The JSON store is gone with the v1 layout. Its content must not be lost, and it "
            "must not be trusted unread: some of it is stale."
        ),
        "",
        "## Notes",
    ]
    if skipped:
        out.append(f"Left out: {', '.join(skipped)} (file lists and tags, not knowledge).")
    for title, lines in sections:
        out += ["", f"### {title} ({len(lines)})", *(f"- [ ] {line}" for line in lines)]
    text, changed = sanitize("\n".join(out) + "\n")
    return text, changed, counts


def knowledge_snapshot(root: Path, data: dict[str, object]) -> tuple[str, str]:
    """(date, where from) of the knowledge snapshot: the JSON's last commit, else its own
    last_updated, else the file's mtime. A clone's mtime is the clone's date, so it is last."""
    committed = git_out(root, "log", "-1", "--format=%cs", "--", LEGACY_KNOWLEDGE)
    if committed:
        return committed, "its last commit"
    updated = data.get("last_updated")
    if isinstance(updated, str) and re.match(r"^\d{4}-\d{2}-\d{2}", updated):
        return updated[:10], "its last_updated field"
    stamp = (root / LEGACY_KNOWLEDGE).stat().st_mtime
    return dt.datetime.fromtimestamp(stamp, dt.UTC).date().isoformat(), "the file's mtime"


def v1_ignore_lines(text: str) -> list[int]:
    """The indexes of the v1 block's lines in a .gitignore text."""
    return [
        i
        for i, line in enumerate(text.splitlines())
        if line.strip() in V1_IGNORE_COMMENTS or V1_IGNORE_LINE.match(line.strip())
    ]


def drop_lines(text: str, drop: list[int]) -> str:
    """text without the lines at drop, and without the extra blank lines that leaves."""
    lines, newline = split_lines(text)
    gone = set(drop)
    kept = [line for i, line in enumerate(lines) if i not in gone]
    out: list[str] = []
    for line in kept:
        if not line.strip() and out and not out[-1].strip():
            continue
        out.append(line)
    return newline.join(out).strip("\r\n") + newline


def v1_items(root: Path) -> list[V2Item]:
    """Each v1 item this repo has, with its fate (9-migrate.md)."""
    items: list[V2Item] = []
    for name in (*TRANSCRIPT_DIRS, "chromadb"):
        rel = f"{LEGACY_BASE}/{name}"
        if (root / rel).exists() or (root / rel).is_symlink():
            items.append(
                V2Item(rel, "transcripts", "migrate-transcripts: quarantine, redact, archive")
            )
    if (root / LEGACY_KNOWLEDGE).is_file():
        items.append(
            V2Item(
                LEGACY_KNOWLEDGE,
                "knowledge",
                f"rendered once into specs/backlog/<date>-{KNOWLEDGE_REPORT} (P2 intake), then "
                "git rm'd",
            )
        )
    for hook in sorted(root.glob(LEGACY_HOOKS)):
        items.append(
            V2Item(
                rel_posix(hook, root),
                "hooks",
                "unregistered from the settings files that name it, then git rm'd",
            )
        )
    ignore = read_text(root / ".gitignore") or ""
    if v1_ignore_lines(ignore):
        items.append(
            V2Item(
                ".gitignore v1 block",
                "gitignore",
                "its lines removed, once the stores left the repo; render adds the standard lines",
            )
        )
    return items


def cmd_migrate_v1(args: argparse.Namespace) -> int:
    root = repo_root(args.repo)
    if not is_git_root(root) or not has_commits(root):
        raise Refusal("migrate-v1: not a git repo with a commit")
    items = v1_items(root)
    if not args.apply:
        if not items:
            raise Refusal("migrate-v1: no v1 layout here (9-migrate.md); nothing to migrate")
        print(label("migrate") + f"v1 JSON memory -> v3, {plural(len(items), 'item')}:")
        width = max(len(i.path) for i in items)
        for item in items:
            print(f"  {item.path.ljust(width)}  {item.fate}")
        print("1. Apply all (Recommended: every fate above is the approved v3 home)")
        print("2. Stop")
        print(
            label("next")
            + "on a yes: init.py migrate-transcripts first, then P2, then `git switch -c "
            "plan/project-init` and init.py migrate-v1 --apply"
        )
        return 0

    manifest = load_toml(root / MANIFEST)
    default = detect_default_branch(root, manifest)
    branch = git_out(root, "symbolic-ref", "-q", "--short", "HEAD")
    if not branch or branch == default:
        raise Refusal(
            f"migrate-v1 --apply refused: HEAD is {branch or 'detached'}; the moves land on "
            "plan/project-init (git switch -c plan/project-init first). Nothing changed"
        )
    stores = [i.path for i in items if i.action == "transcripts"]
    if stores:
        raise Refusal(
            f"migrate-v1 --apply refused: {', '.join(stores)} still in the repo. Run init.py "
            "migrate-transcripts first: the .gitignore block keeps them out of git until they "
            "move. Nothing changed"
        )
    todo = [i for i in items if i.action in ("knowledge", "hooks", "gitignore")]
    if not todo:
        print("migrate-v1: nothing left to apply")
        return 0
    knowledge = root / LEGACY_KNOWLEDGE
    if knowledge.is_file():
        try:
            data = json.loads(knowledge.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise Refusal(
                f"migrate-v1 --apply refused: {LEGACY_KNOWLEDGE} does not parse ({exc}). "
                "Nothing changed"
            ) from exc
        if not isinstance(data, dict):
            raise Refusal(
                f"migrate-v1 --apply refused: {LEGACY_KNOWLEDGE} is not a JSON object. "
                "Nothing changed"
            )
        backlog = root / "specs" / "backlog"
        done = sorted(backlog.glob(f"*-{KNOWLEDGE_REPORT}")) if backlog.is_dir() else []
        if done:
            print(f"  {'kept':<12} {rel_posix(done[0], root)} (rendered by an earlier run)")
        else:
            snapshot, source = knowledge_snapshot(root, data)
            text, sanitized, counts = knowledge_report(data, snapshot)
            rel = f"specs/backlog/{today()}-{KNOWLEDGE_REPORT}"
            install(root, rel, text.encode("utf-8"), 0o644)
            shown = ", ".join(f"{n} {t.lower()}" for t, n in counts.items()) or "no entries"
            print(f"  {'written':<12} {rel}: {shown}; snapshot {snapshot}, from {source}")
            if sanitized:
                print(
                    f"  {'sanitized':<12} {plural(sanitized, 'vault or home path')} and "
                    "wiki-links replaced (the leak rules would refuse them)"
                )
    for rel in unregister_v2_hooks(root, "project-session-"):
        print(f"  {'edited':<12} {rel}: the project-session hook entries are gone")
    gone = [i.path for i in todo if i.action in ("knowledge", "hooks")]
    tracked = z_split(git(root, "ls-files", "-z", "--", *gone).out) if gone else []
    if tracked:
        removed = git(root, "rm", "-q", "--", *gone_tracked(gone, tracked))
        if removed.code != 0:
            raise Refusal(f"migrate-v1: git rm failed: {removed.err.strip()[-300:]}")
    for rel in gone:
        if (root / rel).exists():
            print(f"  {'left':<12} {rel} (untracked: delete it by hand once P2 read it)")
        else:
            print(f"  {'deleted':<12} {rel}")
    ignore = read_text(root / ".gitignore")
    drop = v1_ignore_lines(ignore or "")
    if ignore is not None and drop:
        install(root, ".gitignore", drop_lines(ignore, drop).encode("utf-8"), 0o644)
        print(f"  {'edited':<12} .gitignore: the {plural(len(drop), 'line')} of the v1 block")
    print(label("next") + "init.py prepare, then render (P4): render adds the standard lines")
    return 0


# ---------------------------------------------------------------------------------------------
# MIGRATE step 1: transcripts


def gitleaks_argv() -> list[str] | None:
    if run(["gitleaks", "version"], cwd=Path.home(), timeout=20).code == 0:
        return ["gitleaks"]
    pinned = ["mise", "x", GITLEAKS_PIN, "--", "gitleaks"]
    if run([*pinned, "version"], cwd=Path.home(), timeout=300).code == 0:
        return pinned
    return None


def gitleaks_scan(argv: list[str], target: Path, work: Path) -> list[dict[str, object]]:
    """`gitleaks dir <target> -f json`: the findings, Secret included. Raises on a scan error.
    gitleaks runs in a process group of its own, killed whole if this process stops."""
    config = work / "gitleaks.toml"
    config.write_text("[extend]\nuseDefault = true\n", encoding="utf-8")
    report = work / "report.json"
    report.unlink(missing_ok=True)
    result = run(
        [
            *argv,
            "dir",
            str(target),
            "-c",
            str(config),
            "-f",
            "json",
            "-r",
            str(report),
            "--no-banner",
            "--exit-code",
            "3",
            "--log-level",
            "error",
        ],
        cwd=work,
        timeout=1800,
        own_group=True,
    )
    if result.code not in (0, 3):
        raise Refusal(f"gitleaks failed (exit {result.code}): {result.err.strip()[-300:]}")
    try:
        data = json.loads(report.read_text(encoding="utf-8") or "[]")
    except (OSError, json.JSONDecodeError) as exc:
        raise Refusal(f"gitleaks report unreadable: {exc}") from exc
    findings = [f for f in data if isinstance(f, dict)] if isinstance(data, list) else []
    if result.code == 3 and not findings:
        raise Refusal("gitleaks reported leaks but its report is empty")
    return findings


MAX_TRANSCRIPT = 256 * 1024 * 1024
HELD = ".held"  # inside the quarantine: kept for a human, never scanned into the archive
WORK = ".work"  # inside the quarantine: the views while a run scans; removed when it ends
LOCK = "project-init-migrate.lock"  # inside the quarantine: flocked while a run works in it
JSON_SUFFIXES = frozenset({".json", ".jsonl", ".ndjson"})
COMPRESSED_SUFFIXES = frozenset({".gz", ".bz2", ".xz"})
ALLOW_MARK = "gitleaks:allow"  # an inline allow comment would silence a finding on its line


@dataclass
class Prepared:
    materialized: list[str] = field(default_factory=list)
    decompressed: list[str] = field(default_factory=list)
    originals: list[str] = field(default_factory=list)  # packed files whose content is archived


def write_private(path: Path, data: bytes) -> None:
    """A new file (never through a link, never into a hard-linked inode), mode 600."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def decompress(path: Path) -> bytes | None:
    """The content of a .gz, .bz2 or .xz file, or None when it is corrupt or too big."""
    suffix = path.suffix.lower()
    try:
        if suffix == ".gz":
            with gzip.open(path, "rb") as handle:
                data = handle.read(MAX_TRANSCRIPT + 1)
        elif suffix == ".bz2":
            with bz2.open(path, "rb") as handle:
                data = handle.read(MAX_TRANSCRIPT + 1)
        else:
            with lzma.open(path, "rb") as handle:
                data = handle.read(MAX_TRANSCRIPT + 1)
    except (OSError, EOFError, ValueError, lzma.LZMAError):
        return None
    return data if len(data) <= MAX_TRANSCRIPT else None


def looks_binary(data: bytes) -> bool:
    return b"\0" in data[:8192]


def free_name(path: Path) -> Path:
    """path, or path with a -2, -3 ... before its suffix when that name is taken."""
    candidate = path
    n = 2
    while candidate.exists() or candidate.is_symlink():
        candidate = path.with_name(f"{path.stem}-{n}{path.suffix}")
        n += 1
    return candidate


def prepare_archive_set(
    quarantine: Path, rels: list[str], hold_back: Callable[[str, str], None]
) -> Prepared:
    """Make the archive set plain text files only, before any scan. gitleaks never follows a
    link and never opens a compressed file, so either would reach the archive unscanned. A
    link to a regular file becomes a copy of it; a .gz, .bz2 or .xz file is decompressed next
    to itself (the packed original moves to <quarantine>/.held); anything else that is not
    plain text (a folder link, a broken link, a binary) goes to hold_back(file, why), which
    records it and moves it there, never archived. A second pass over a set it already made
    plain (--resume) changes nothing."""
    prepared = Prepared()

    def hold(path: Path, why: str) -> None:
        hold_back(rel_posix(path, quarantine), why)

    entries: list[Path] = []
    for rel in rels:
        for dirpath, dirnames, filenames in os.walk(quarantine / rel):  # never follows links
            dirnames.sort()
            entries += [Path(dirpath) / name for name in [*dirnames, *sorted(filenames)]]
    for path in entries:
        if path.is_symlink():
            data = None
            try:
                if path.is_file() and path.stat().st_size <= MAX_TRANSCRIPT:
                    data = path.read_bytes()
            except OSError:
                data = None
            if data is None:
                hold(path, "a link to a folder, to nothing, or to a file over 256 MB")
                continue
            path.unlink()
            write_private(path, data)
            prepared.materialized.append(rel_posix(path, quarantine))
        elif path.is_dir():
            continue
        elif not path.is_file():
            hold(path, "not a regular file (a fifo, a socket or a device)")
            continue
        if path.suffix.lower() in COMPRESSED_SUFFIXES:
            data = decompress(path)
            if data is None or looks_binary(data):
                hold(path, "packed, and its content is corrupt, over 256 MB or binary")
                continue
            out = free_name(path.with_suffix(""))
            write_private(out, data)
            prepared.decompressed.append(rel_posix(out, quarantine))
            prepared.originals.append(hold_file(quarantine, rel_posix(path, quarantine)))
            continue
        with path.open("rb") as handle:
            head = handle.read(8192)
        if looks_binary(head):
            hold(path, "binary (a NUL byte in its first 8 KB)")
    return prepared


def hold_file(quarantine: Path, rel: str) -> str:
    """Move one file of the archive set into <quarantine>/.held: kept for a human, never
    archived."""
    dest = quarantine / HELD / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    os.rename(quarantine / rel, dest)
    return rel


def archive_files(quarantine: Path, rels: list[str]) -> list[Path]:
    files: list[Path] = []
    for rel in rels:
        for dirpath, dirnames, filenames in os.walk(quarantine / rel):
            dirnames.sort()
            files += [Path(dirpath) / name for name in sorted(filenames)]
    return files


def json_strings(text: str) -> str | None:
    """Every string in a JSON or JSON Lines text, unescaped, one per line (lines that do not
    parse stay as they are); None when nothing parses. A transcript escapes quotes and
    newlines, which hides `api_key = "..."` and PEM blocks from gitleaks."""
    docs: list[object] = []
    out: list[str] = []
    try:
        docs.append(json.loads(text))
    except (ValueError, RecursionError):
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                docs.append(json.loads(line))
            except (ValueError, RecursionError):
                out.append(line)
    if not docs:
        return None
    stack = docs
    while stack:
        node = stack.pop()
        if isinstance(node, str):
            out.append(node)
        elif isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value, str):
                    out.append(f"{key}: {value}")  # keeps `"api_key": "..."` one match
                else:
                    out.append(str(key))
                    stack.append(value)
        elif isinstance(node, list):
            stack.extend(node)
    return "\n".join(out)


# gitleaks skips a file whose first bytes look like a binary format (%PDF, {\\rtf, MZ, %!,
# `ustar` at 257, `CD001` at 32769: file signatures, some at an offset). Every view therefore
# starts with a line of spaces (no signature at offset 0) and ends with a canary, a fresh fake
# key: a view whose canary gitleaks does not report was never read. Its file then gets views
# whose line of spaces reaches past the last offset gitleaks checks, and a file gitleaks skips
# even then is held back. Spaces, never newlines: gitleaks indexes every newline of what it
# reads, and 40,960 of them in each view of 5,000 small transcripts took it 77 seconds.
VIEW_HEAD = " " * 63 + "\n"
VIEW_PAD = " " * 40959 + "\n"
CANARY_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
# gitleaks 8.30 reads a file in chunks: 100,000 bytes, then a peek of up to 25,000 more that
# stops at a blank line, then about every 28.7 KB. A secret that straddles a cut is never
# reported, and a transcript line (one JSON object) has no blank line in reach. So a view is
# cut into pieces well under the first chunk (pad + piece + canary < 82 KB), each overlapping
# the one before: a match up to PIECE_OVERLAP bytes long sits whole in at least one piece.
PIECE_BYTES = 40 * 1024
PIECE_OVERLAP = 12 * 1024


def entropy(text: str) -> float:
    """Shannon entropy in bits per character, as gitleaks measures a secret."""
    size = len(text)
    return -sum(n / size * math.log2(n / size) for n in (text.count(c) for c in set(text)))


# gitleaks' default config drops a secret its global allowlist matches, `(?i)^true|false|null$`
# (read as three alternatives), and an AWS key ending in EXAMPLE: a canary must dodge all four.
DEFAULT_ALLOWED = re.compile(r"(?i)^true|false|null$|example$")


def canary() -> str:
    """A fresh fake AWS access key id that gitleaks' default aws-access-token rule reports."""
    while True:
        token = "AKIA" + "".join(secrets.choice(CANARY_ALPHABET) for _ in range(16))
        if entropy(token) >= 3.5 and not DEFAULT_ALLOWED.search(token):
            return token


def pieces(body: bytes) -> list[bytes]:
    """body cut into PIECE_BYTES slices that overlap by PIECE_OVERLAP (one slice when short)."""
    if len(body) <= PIECE_BYTES:
        return [body]
    step = PIECE_BYTES - PIECE_OVERLAP
    cuts: list[bytes] = []
    start = 0
    while True:
        cuts.append(body[start : start + PIECE_BYTES])
        if start + PIECE_BYTES >= len(body):
            return cuts
        start += step


def build_views(
    quarantine: Path, files: list[Path], views: Path, head: str
) -> dict[str, tuple[str, str]]:
    """Neutral-named text files per archived file (JSON decoded, inline allow comments
    defused), so no path allowlist and no escaping hides a secret; each starts with head and
    ends with a canary; cut into overlapping pieces so no chunk cut hides a secret. A view costs
    its piece plus about 90 bytes. view name -> (archived file, its canary)."""
    if views.exists():
        shutil.rmtree(views)
    views.mkdir(mode=0o700)
    lead = head.encode("utf-8")
    names: dict[str, tuple[str, str]] = {}
    for i, path in enumerate(files):
        text = path.read_text(encoding="utf-8", errors="replace")
        decoded = json_strings(text) if path.suffix.lower() in JSON_SUFFIXES else None
        body = (text if decoded is None else decoded).replace(ALLOW_MARK, "gitleaks-allow-defused")
        for j, piece in enumerate(pieces(body.encode("utf-8"))):
            view = views / f"{i:06d}-{j:05d}.txt"
            token = canary()
            view.write_bytes(lead + piece + f"\n{token}\n".encode())
            names[view.name] = (rel_posix(path, quarantine), token)
    return names


@dataclass
class Leak:
    secret: str
    rule: str
    file: str | None  # the quarantine-relative file it was reported in, when known


def scan_views(
    argv: list[str], quarantine: Path, files: list[Path], work: Path, head: str
) -> tuple[list[Leak], set[str]]:
    """One gitleaks pass over views of files: (the leaks, the files a view of which gitleaks
    did not read). The views are deleted as soon as gitleaks is done with them."""
    folder = work / "views"
    views = build_views(quarantine, files, folder, head)
    canaries = {token: name for name, (_, token) in views.items()}
    read: set[str] = set()
    leaks: list[Leak] = []
    try:
        findings = gitleaks_scan(argv, folder, work)
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    for finding in findings:
        secret = finding.get("Secret")
        name = Path(str(finding.get("File") or "")).name
        if not isinstance(secret, str) or not secret:
            continue
        if secret in canaries:
            if canaries[secret] == name:
                read.add(name)
            continue
        rel = views[name][0] if name in views else None
        leaks.append(Leak(secret, str(finding.get("RuleID") or "unknown-rule"), rel))
    return leaks, {rel for name, (rel, _) in views.items() if name not in read}


def scan_quarantine(
    argv: list[str], quarantine: Path, rels: list[str], work: Path
) -> tuple[list[Leak], list[str]]:
    """gitleaks over each archived store as it is (the design's scan), then over the views,
    then over padded views of any file whose view it skipped: (the leaks, the archived files
    it read no view of). Only the archive set is scanned: .held/ and the binary chromadb/ stay
    out of it."""
    leaks: list[Leak] = []
    base = os.path.abspath(quarantine)
    for rel in rels:
        target = quarantine / rel
        if not target.is_dir():
            continue
        for finding in gitleaks_scan(argv, target, work):
            secret = finding.get("Secret")
            if not isinstance(secret, str) or not secret:
                continue
            where = os.path.normpath(os.path.join(str(work), str(finding.get("File") or "")))
            where_rel = os.path.relpath(where, base) if where.startswith(base + os.sep) else None
            leaks.append(Leak(secret, str(finding.get("RuleID") or "unknown-rule"), where_rel))
    files = archive_files(quarantine, rels)
    found, unread = scan_views(argv, quarantine, files, work, VIEW_HEAD)
    leaks += found
    if unread:  # a file signature at an offset past the head: views padded past every offset
        again = [path for path in files if rel_posix(path, quarantine) in unread]
        found, unread = scan_views(argv, quarantine, again, work, VIEW_PAD)
        leaks += found
    return leaks, sorted(unread)


def secret_forms(secret: str) -> set[bytes]:
    """The secret as written raw, JSON-escaped (ASCII or not) and with escaped slashes."""
    forms = {secret, json.dumps(secret)[1:-1], json.dumps(secret, ensure_ascii=False)[1:-1]}
    forms |= {form.replace("/", "\\/") for form in forms}
    return {form.encode("utf-8") for form in forms if form}


def written_in(path: Path, secret: str) -> bool:
    """True when the secret sits in the file in a form redact() can replace. gitleaks also
    reports what it found by decoding (base64, hex, percent-encoding): that Secret is not in
    the file as written, and no replacement in place can remove it."""
    try:
        data = path.read_bytes()
    except OSError:
        return False
    return any(form in data for form in secret_forms(secret))


def redact(
    leaks: list[Leak],
    quarantine: Path,
    rels: list[str],
    journal: Callable[[list[tuple[str, str]]], None],
) -> tuple[list[tuple[str, str]], set[str]]:
    """Every distinct Secret any scan reported, replaced with REDACTED:<rule-id> in every
    archived file and in each file it was reported in, in each of its written forms: a key
    gitleaks saw in one transcript is redacted where it sits unseen (JSON-escaped) in another.
    Returns (rule, file) for each file a secret was replaced in, and the secrets replaced.

    A read-only pass first hands journal() every (rule, file) about to be rewritten. Once a
    file is rewritten no rescan finds its secret again, so a run stopped mid-redaction would
    otherwise lose that file from the rotation list."""
    rules: dict[str, str] = {}
    targets = set(archive_files(quarantine, rels))
    for leak in leaks:
        rules.setdefault(leak.secret, leak.rule)
        if leak.file:
            targets.add(quarantine / leak.file)
    swaps = sorted(
        ((form, rule, secret) for secret, rule in rules.items() for form in secret_forms(secret)),
        key=lambda swap: len(swap[0]),
        reverse=True,
    )
    files = [p for p in sorted(targets) if not p.is_symlink() and p.is_file()]
    ahead: list[tuple[str, str]] = []
    for path in files:
        data = path.read_bytes()
        for form, rule, _ in swaps:
            pair = (rule, rel_posix(path, quarantine))
            if form in data and pair not in ahead:
                ahead.append(pair)
    journal(ahead)
    rotation: list[tuple[str, str]] = []
    replaced: set[str] = set()
    for path in files:
        data = path.read_bytes()
        new = data
        for form, rule, secret in swaps:
            if form in new:
                new = new.replace(form, f"REDACTED:{rule}".encode())
                replaced.add(secret)
                pair = (rule, rel_posix(path, quarantine))
                if pair not in rotation:
                    rotation.append(pair)
        if new != data:
            write_private(path, new)
    return rotation, replaced


def repo_display_name(root: Path) -> str:
    origin = origin_url(root)
    if origin:
        tail = normalize_url(origin).rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
        if tail:
            return tail
    return project_name(root)


def forbidden_home(path: Path) -> str | None:
    """A quarantine must sit outside every repo and Syncthing folder."""
    for parent in [path, *path.parents]:
        if (parent / ".git").exists():
            return f"{parent} is a git repo"
        if (parent / ".stfolder").exists():
            return f"{parent} is a Syncthing folder"
    return None


def holds_files(folder: Path) -> bool:
    """Any file or link under folder (empty folders do not count)."""
    if not folder.is_dir():
        return folder.exists() or folder.is_symlink()
    for dirpath, dirnames, filenames in os.walk(folder):
        if filenames or any((Path(dirpath) / d).is_symlink() for d in dirnames):
            return True
    return False


def not_plain(folder: Path) -> list[str]:
    """Links and special files under folder: none may reach the archive."""
    bad: list[str] = []
    for dirpath, dirnames, filenames in os.walk(folder):
        for name in [*dirnames, *filenames]:
            path = Path(dirpath) / name
            if path.is_symlink() or not (path.is_dir() or path.is_file()):
                bad.append(rel_posix(path, folder))
    return bad


LEGACY_STORES = (*TRANSCRIPT_DIRS, "chromadb")


def legacy_dirs(root: Path) -> list[str]:
    """The v1 stores migrate-transcripts moves: project_memory/{sessions,pending,summaries,
    chromadb}, whichever exist (in a repo, or in a quarantine)."""
    found: list[str] = []
    for name in LEGACY_STORES:
        path = root / LEGACY_BASE / name
        if path.is_symlink() or path.is_dir():
            found.append(f"{LEGACY_BASE}/{name}")
    return found


def migrate_refusals(root: Path, items: list[str], name: str) -> None:
    """Everything that stops the move, checked before anything moves."""
    if not name.strip() or "/" in name or name.startswith(".") or CONTROL.search(name):
        raise UsageError(f"--name {name!r}: give one plain folder name for the archive")
    links = [rel for rel in items if (root / rel).is_symlink()]
    if links:
        shown = ", ".join(f"{rel} -> {os.readlink(root / rel)}" for rel in links)
        raise Refusal(
            f"{shown}: a linked store; nothing moved. Replace the link with the folder itself "
            "(or delete it), then re-run"
        )
    if is_git_root(root):
        tracked = (git_out(root, "ls-files", "--", *items) or "").splitlines()
        if tracked:
            more = f" and {len(tracked) - 3} more" if len(tracked) > 3 else ""
            raise Refusal(
                f"git tracks files in the legacy stores ({', '.join(tracked[:3])}{more}); nothing "
                "moved. v1 gitignored them, so git history already holds these transcripts: "
                "rotate what they leaked, `git rm -r --cached` them in their own commit (a "
                "history rewrite is a separate decision), then re-run"
            )


def make_private_dirs(path: Path) -> None:
    """mkdir -p, each folder it creates mode 700. A folder that exists keeps its mode: it is
    the user's (an existing --quarantine-root, /tmp)."""
    missing: list[Path] = []
    probe = path
    while not probe.exists() and not probe.is_symlink():
        missing.append(probe)
        probe = probe.parent
    for folder in reversed(missing):
        folder.mkdir(mode=0o700)
        os.chmod(folder, 0o700)  # mkdir's mode passes through the umask


def make_quarantine(qroot: Path, name: str) -> Path:
    """A new mode-700 folder <qroot>/<name>-<date>[-n], created by this run."""
    stamp = today()
    try:
        make_private_dirs(qroot)
        n = 1
        while True:
            quarantine = qroot / (f"{name}-{stamp}" if n == 1 else f"{name}-{stamp}-{n}")
            try:
                quarantine.mkdir(mode=0o700)  # never an existing folder: FileExistsError
                break
            except FileExistsError:
                n += 1
        os.chmod(quarantine, 0o700)
    except OSError as exc:
        raise Refusal(f"quarantine refused: {exc}; nothing moved") from exc
    return quarantine


# What a quarantine holds and how its run ended, so a re-run can say so instead of "nothing
# moved" while transcripts sit unarchived in it, and --resume can finish it.
MIGRATE_STATE = "project-init-migrate.json"
# moving: a run started and never recorded an end (killed, or still running: see its lock).
# failed: a run ended without writing the archive. Either one --resume finishes.
UNFINISHED = frozenset({"moving", "failed"})


def save_state(quarantine: Path, **fields: object) -> None:
    path = quarantine / MIGRATE_STATE
    try:
        state = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, json.JSONDecodeError):
        state = {}
    state.update(fields, at=dt.datetime.now(dt.UTC).astimezone().isoformat(timespec="seconds"))
    write_private(path, (json.dumps(state, indent=2) + "\n").encode("utf-8"))


def journaled_rotation(quarantine: Path) -> list[tuple[str, str]]:
    """The (rule, file) pairs an earlier run of this quarantine recorded under `rotate`."""
    try:
        state = json.loads((quarantine / MIGRATE_STATE).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    saved = state.get("rotate") if isinstance(state, dict) else None
    pairs = [
        (str(pair[0]), str(pair[1]))
        for pair in (saved if isinstance(saved, list) else [])
        if isinstance(pair, list) and len(pair) == 2
    ]
    return list(dict.fromkeys(pairs))


def take_lock(quarantine: Path, create: bool) -> int | None:
    """An exclusive flock on the quarantine's lock file, held while a run works in it: the
    kernel drops it when the process ends, even on SIGKILL. Returns the open descriptor (close
    it to release), -1 when there is no lock file to take and create is False, None while
    another run holds it."""
    flags = os.O_RDWR | os.O_NOFOLLOW | (os.O_CREAT if create else 0)
    try:
        fd = os.open(quarantine / LOCK, flags, 0o600)
    except FileNotFoundError:
        return -1
    except OSError as exc:  # a link or a folder in its place: someone else's file
        raise Refusal(f"{quarantine / LOCK}: {exc.strerror}; move it aside, then re-run") from exc
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        return None
    return fd


def release_lock(fd: int | None) -> None:
    if fd is not None and fd >= 0:
        os.close(fd)


def clear_work(quarantine: Path) -> bool:
    """Remove what a killed run left in <quarantine>/.work (decoded views of the transcripts).
    Call it only while holding the quarantine's lock. True when something was removed."""
    work = quarantine / WORK
    if work.is_symlink():
        work.unlink()
        return True
    if work.exists():
        shutil.rmtree(work)
        return True
    return False


@contextlib.contextmanager
def stop_signals() -> Iterator[None]:
    """SIGTERM and SIGHUP raise Stopped where the process is, so the run's own cleanup runs
    (the work folder removed, the quarantine's state saved). A second signal is ignored while
    that cleanup runs; SIGINT raises KeyboardInterrupt as always."""
    watched = (signal.SIGTERM, signal.SIGHUP)

    def stop(signum: int, _frame: object) -> None:
        for sig in watched:
            signal.signal(sig, signal.SIG_IGN)
        raise Stopped(signum)

    before = {sig: signal.signal(sig, stop) for sig in watched}
    try:
        yield
    finally:
        for sig, handler in before.items():
            signal.signal(sig, handler)


def stop_reason(exc: BaseException) -> str:
    if isinstance(exc, Stopped):
        return f"stopped by {exc.name}"
    if isinstance(exc, KeyboardInterrupt):
        return "stopped by SIGINT"
    return f"the run stopped ({type(exc).__name__}: {one_line(str(exc))[:200]})"


def resume_command(root: Path) -> str:
    here = os.path.abspath(__file__)
    home = str(Path.home())
    shown = "~" + here[len(home) :] if here.startswith(home + os.sep) else shlex.quote(here)
    return f"env -C ~ {shown} migrate-transcripts {shlex.quote(str(root))} --resume"


def earlier_quarantines(root: Path, qroot: Path, name: str) -> list[tuple[Path, dict[str, object]]]:
    """This repo's quarantines under qroot: its state file names the repo, or (a quarantine
    with no readable state) the folder carries the archive name and a date."""
    found: list[tuple[Path, dict[str, object]]] = []
    pattern = re.compile(rf"^{re.escape(name)}-\d{{4}}-\d{{2}}-\d{{2}}(?:-\d+)?$")
    try:
        children = sorted(p for p in qroot.iterdir() if p.is_dir() and not p.is_symlink())
    except OSError:
        return found
    for folder in children:
        state: dict[str, object] = {}
        try:
            loaded = json.loads((folder / MIGRATE_STATE).read_text(encoding="utf-8"))
            state = loaded if isinstance(loaded, dict) else {}
        except (OSError, json.JSONDecodeError):
            state = {}
        if state.get("repo") == str(root) or (not state and pattern.match(folder.name)):
            found.append((folder, state))
    return found


def report_earlier(root: Path, earlier: list[tuple[Path, dict[str, object]]]) -> int:
    """The re-run with no legacy store left: 0 when there is no quarantine, or every one of
    this repo's was archived whole; 1 while one holds files that were never archived. A work
    folder a killed run left behind is removed here (it holds decoded transcripts)."""
    if not earlier:
        print(
            "migrate-transcripts: no project_memory/{sessions,pending,summaries,chromadb}/ here "
            "and no quarantine of this repo; nothing moved"
        )
        return 0
    code = 0
    for folder, state in earlier:
        lock = take_lock(folder, create=False)
        if lock is None:
            code = 1
            print(label("RUNNING") + f"{folder}: a migrate run is working in it right now")
            continue
        try:
            cleared = clear_work(folder)
        finally:
            release_lock(lock)
        outcome = state.get("state")
        held = state.get("held")
        if outcome == "archived":
            print(
                label("done")
                + f"{folder}: archived to {state.get('archive')}; delete the quarantine after "
                "you confirm the archive (punch list)"
            )
        elif outcome == "held" and isinstance(held, dict):
            code = 1
            print(
                label("HELD")
                + f"{folder}: archived to {state.get('archive')} except {len(held)} file(s) "
                f"never archived, in {folder / HELD}:"
            )
            for rel, why in held.items():
                print(f"{INDENT}{rel}: {why}")
        elif outcome in UNFINISHED:
            code = 1
            why = state.get("why") if outcome == "failed" else None
            ended = str(why) if why else "the run never recorded an end (killed, or a crash)"
            print(
                label("FAILED" if why else "UNFINISHED")
                + f"{folder}: {ended}; nothing was archived"
            )
            print(INDENT + f"finish it: {resume_command(root)}")
        else:
            code = 1
            print(label("UNKNOWN") + f"{folder}: no finished run recorded; look inside it")
        if cleared:
            print(INDENT + f"removed its leftover {WORK}/ (decoded views of the transcripts)")
    print(
        "migrate-transcripts: the stores already moved out of the repo"
        + ("" if code == 0 else "; transcripts above were never archived, see the lines above")
    )
    return code


def move_stores(root: Path, quarantine: Path, items: list[str]) -> None:
    """Move each store from the repo into the quarantine. Raises Refusal when a move fails,
    after recording in the quarantine's state what did move."""
    moved: list[str] = []
    try:
        for rel in items:
            dest = quarantine / rel
            if dest.exists() or dest.is_symlink():
                raise Refusal(
                    f"{rel} is both in the repo and in {quarantine}: an interrupted move left "
                    "part of it on each side. Merge the two copies by hand, then re-run --resume"
                )
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(root / rel), str(dest))
            moved.append(rel)
    except OSError as exc:
        save_state(quarantine, state="failed", why=f"the move failed ({exc})")
        if not moved and not holds_files(quarantine / LEGACY_BASE):
            raise Refusal(f"quarantine failed ({exc}); nothing moved") from exc
        raise Refusal(
            f"quarantine failed ({exc}) after moving {', '.join(moved) or 'part of a store'} "
            f"into {quarantine}; the rest stayed in the repo. Nothing was archived. Finish it: "
            f"{resume_command(root)}"
        ) from exc


def cmd_migrate(args: argparse.Namespace) -> int:
    root = repo_root(args.repo)
    name = args.name or repo_display_name(root)
    items = legacy_dirs(root)
    qroot = Path(args.quarantine_root).expanduser().resolve()
    earlier = earlier_quarantines(root, qroot, name)
    unfinished = [(folder, state) for folder, state in earlier if state.get("state") in UNFINISHED]
    if args.resume:
        return resume_migrate(args, root, name, items, unfinished)
    if not items:
        return report_earlier(root, earlier)
    if unfinished:
        folder, state = unfinished[-1]
        raise Refusal(
            f"{folder} holds an unfinished migrate of this repo (state {state.get('state')}); "
            f"nothing moved. Finish it, which also moves {', '.join(items)} there: "
            f"{resume_command(root)} (or delete that folder first)"
        )
    migrate_refusals(root, items, name)
    archive = Path(args.archive_root).expanduser().resolve() / name
    why = forbidden_home(qroot)
    if why:
        raise Refusal(
            f"quarantine refused: {why} (it must sit outside every repo and synced folder)"
        )
    if holds_files(archive):
        raise Refusal(f"{archive} already holds files; nothing moved (never overwritten)")
    argv = gitleaks_argv()
    if argv is None:
        raise Refusal(
            "gitleaks is not runnable (neither `gitleaks` nor `mise x gitleaks`); nothing moved"
        )

    with stop_signals():
        quarantine = make_quarantine(qroot, name)
        lock = take_lock(quarantine, create=True)
        try:
            save_state(
                quarantine, repo=str(root), archive=str(archive), state="moving", stores=items
            )
            try:
                move_stores(root, quarantine, items)
            except Refusal:
                if not holds_files(quarantine / LEGACY_BASE):  # nothing moved: this run's own
                    release_lock(lock)
                    lock = None
                    shutil.rmtree(quarantine, ignore_errors=True)
                raise
            except BaseException as exc:  # a signal between two stores
                why = f"{stop_reason(exc)} during the move"
                save_state(quarantine, state="failed", why=why)
                sys.stdout.flush()
                print(
                    f"migrate-transcripts: {why}; finish it: {resume_command(root)}",
                    file=sys.stderr,
                )
                raise
            print(label("quarantine") + f"{quarantine} (mode 700): " + ", ".join(items))
            return run_quarantine(root, quarantine, archive, argv, {})
        finally:
            release_lock(lock)


def resume_migrate(
    args: argparse.Namespace,
    root: Path,
    name: str,
    items: list[str],
    unfinished: list[tuple[Path, dict[str, object]]],
) -> int:
    """--resume: finish this repo's unfinished quarantine. Whatever store is still in the repo
    moves in first; then the same steps as a fresh run, on what the quarantine holds."""
    if not unfinished:
        raise Refusal(
            "--resume: no unfinished migrate of this repo under the quarantine root; nothing to "
            "resume (run it without --resume)"
        )
    if len(unfinished) > 1:
        shown = ", ".join(str(folder) for folder, _ in unfinished)
        raise Refusal(f"--resume: several unfinished quarantines of this repo ({shown}): keep one")
    quarantine, state = unfinished[0]
    recorded = state.get("archive")
    archive = (
        Path(recorded)
        if isinstance(recorded, str) and recorded
        else Path(args.archive_root).expanduser().resolve() / name
    )
    with stop_signals():
        lock = take_lock(quarantine, create=True)
        if lock is None:
            raise Refusal(f"{quarantine}: another migrate run is working in it; let it finish")
        try:
            if holds_files(archive):
                raise Refusal(
                    f"{archive} already holds files (an earlier archive copy); nothing moved. "
                    "Delete it, then re-run --resume"
                )
            if items:
                migrate_refusals(root, items, name)
            argv = gitleaks_argv()
            if argv is None:
                raise Refusal(
                    "gitleaks is not runnable (neither `gitleaks` nor `mise x gitleaks`); "
                    "nothing moved"
                )
            if clear_work(quarantine):
                print(label("cleared") + f"{quarantine / WORK} (views a stopped run left)")
            save_state(quarantine, state="moving", why=None, resumed=True)
            move_stores(root, quarantine, items)
            stores = legacy_dirs(quarantine)
            save_state(quarantine, stores=stores)
            print(
                label("resume")
                + f"{quarantine}: "
                + ", ".join(stores)
                + (f" ({', '.join(items)} moved in now)" if items else "")
            )
            saved = state.get("held")
            held = {
                str(rel): str(why)
                for rel, why in (saved.items() if isinstance(saved, dict) else [])
                if os.path.lexists(quarantine / HELD / str(rel))  # a held link may be broken
            }
            return run_quarantine(root, quarantine, archive, argv, held)
        finally:
            release_lock(lock)


def run_quarantine(
    root: Path, quarantine: Path, archive: Path, argv: list[str], held: dict[str, str]
) -> int:
    """migrate_quarantine, with the stop recorded: a signal or an error leaves the state
    `failed`, names the reason, and says how to finish."""
    try:
        return migrate_quarantine(quarantine, archive, argv, held)
    except BaseException as exc:
        why = stop_reason(exc)
        save_state(quarantine, state="failed", why=why)
        sys.stdout.flush()
        print(
            f"migrate-transcripts: {why}; nothing was archived. The stores stay in {quarantine} "
            f"(its {WORK}/ removed). Finish it: {resume_command(root)}",
            file=sys.stderr,
        )
        raise


def migrate_quarantine(
    quarantine: Path, archive: Path, argv: list[str], held_before: dict[str, str]
) -> int:
    """Steps 2 to 4 on a filled quarantine: plain text only, redaction until a clean rescan,
    the archive copy. A file whose finding cannot be replaced in place is held back with its
    rule named; the rest is archived; the run exits 1 while anything is held. The views live
    in <quarantine>/.work and never outlive the run (a signal included)."""
    items = legacy_dirs(quarantine)
    archived = [rel for rel in items if PurePosixPath(rel).name in TRANSCRIPT_DIRS]
    held = dict(held_before)  # file -> why: never archived (exit 1)
    # what a stopped run already redacted or held: no rescan finds those secrets again
    earlier = journaled_rotation(quarantine)
    rotation: list[tuple[str, str]] = list(earlier)

    def journal(pairs: list[tuple[str, str]]) -> None:
        save_state(quarantine, rotate=[list(p) for p in dict.fromkeys([*rotation, *pairs])])

    def hold(rel: str, why: str, rule: str | None = None) -> None:
        """Hold one archived file back. The state records it (and its rule on the rotation
        list) before it moves into .held/: a held file is never scanned again, so a run
        stopped between the two would otherwise lose it from the rotation list."""
        if rel in held or not os.path.lexists(quarantine / rel):
            return
        held[rel] = why
        if rule is not None and (rule, rel) not in rotation:
            rotation.append((rule, rel))
        save_state(quarantine, held=held, rotate=[list(p) for p in rotation])
        hold_file(quarantine, rel)

    prepared = prepare_archive_set(quarantine, archived, hold)
    if prepared.materialized:
        print(label("links") + "copied in place of the link: " + ", ".join(prepared.materialized))
    if prepared.decompressed:
        print(label("unpacked") + ", ".join(prepared.decompressed))
    if prepared.originals:
        print(
            label("originals")
            + f"packed originals kept in {HELD}/: "
            + ", ".join(prepared.originals)
        )
    save_state(quarantine, held=held)
    work = quarantine / WORK
    clear_work(quarantine)
    work.mkdir(mode=0o700)
    secrets_seen: set[str] = set()
    replaced: set[str] = set()
    rewritten: set[str] = set()
    rounds = 0
    try:
        leaks, unread = scan_quarantine(argv, quarantine, archived, work)
        # a round redacts; from the third on, whatever is still reported is held instead
        while (leaks or unread) and rounds < MIGRATE_ROUNDS:
            for rel in unread:  # gitleaks would not read it even as a padded view
                hold(rel, "gitleaks did not read it (a binary file signature): never scanned")
            last_chance = rounds >= MIGRATE_ROUNDS - 2
            for leak in leaks:
                if not leak.file:
                    continue
                if leak.file not in held and not written_in(quarantine / leak.file, leak.secret):
                    hold(
                        leak.file,
                        f"{leak.rule}: found only in a decoded form (base64, hex or an escape), "
                        "so the value is not in the file to replace",
                        leak.rule,
                    )
                elif leak.file not in held and last_chance:
                    why = f"{leak.rule}: still reported after {rounds} redaction(s)"
                    hold(leak.file, why, leak.rule)
                elif leak.file in held and (leak.rule, leak.file) not in rotation:
                    rotation.append((leak.rule, leak.file))  # a second rule, or an unread file
                    journal([])
            secrets_seen |= {leak.secret for leak in leaks}
            pairs, done = redact(leaks, quarantine, archived, journal)
            replaced |= done
            rewritten |= {rel for _, rel in pairs}
            for pair in pairs:
                if pair not in rotation:
                    rotation.append(pair)
            journal([])
            leaks, unread = scan_quarantine(argv, quarantine, archived, work)
            rounds += 1
    finally:
        shutil.rmtree(work, ignore_errors=True)
    if held:
        print(label("held back") + f"never archived, kept in {quarantine / HELD}:")
        for rel, why in held.items():
            print(f"{INDENT}{rel}: {why}")
    if leaks or unread:
        found = sorted({(leak.rule, leak.file or "(file unknown)") for leak in leaks})
        print(
            label("FAIL")
            + f"the rescan still reports {len(leaks)} finding(s) and {len(unread)} unread "
            "file(s): archive NOT written"
        )
        for rule, rel in found:
            print(f"{INDENT}{rule}  {rel}")
        for rel in unread:
            print(f"{INDENT}unread  {rel}")
        print(INDENT + f"the quarantine stays at {quarantine}")
        save_state(quarantine, state="failed", why="the rescan was not clean", held=held)
        return 1
    files = sorted(rewritten - set(held))
    before = {rel for _, rel in earlier} - rewritten - set(held)
    only_held = secrets_seen - replaced
    print(
        label("redacted")
        + f"{len(replaced)} distinct secret value(s) replaced with REDACTED:<rule-id> in "
        f"{len(files)} file(s) (raw and JSON-escaped, wherever written)"
        + (f"; {len(only_held)} more found only in held-back file(s)" if only_held else "")
        + (f"; {len(before)} more file(s) redacted by the run that stopped" if before else "")
        + "; rescan clean (exit 0), every archived file read"
    )
    for rel in archived:
        bad = not_plain(quarantine / rel)
        if bad:
            print(label("FAIL") + f"{rel} still holds links or special files: {', '.join(bad)}")
            print(INDENT + f"archive NOT written; the quarantine stays at {quarantine}")
            save_state(quarantine, state="failed", why=f"{rel} holds links", held=held)
            return 1
    try:
        for rel in archived:
            # empty folders from an earlier run may be there; holds_files() proved no file is
            shutil.copytree(quarantine / rel, archive / rel, symlinks=True, dirs_exist_ok=True)
    except (OSError, shutil.Error) as exc:
        print(label("FAIL") + f"the archive copy failed ({exc}); {archive} is incomplete")
        print(INDENT + f"the redacted set stays in {quarantine}: delete {archive}, then re-run")
        save_state(quarantine, state="failed", why=f"the archive copy failed ({exc})", held=held)
        return 1
    print(
        label("archive")
        + f"{archive}: "
        + ", ".join(archived)
        + (
            "  (chromadb/ stays in quarantine: a binary store)"
            if len(archived) < len(items)
            else ""
        )
        + (f"; {len(held)} file(s) held back, see above" if held else "")
    )
    if rotation:
        print(label("rotate") + "rule and file only, never values:")
        for rule, rel in rotation:
            print(f"{INDENT}{rule}  {rel}" + ("  (held back)" if rel in held else ""))
    print(label("punch") + f"delete {quarantine} after you confirm the archive")
    if held:
        print(INDENT + f"first look at {quarantine / HELD}: those files were never archived")
    print(INDENT + "nothing was staged in the repo; the legacy .gitignore block is untouched")
    save_state(quarantine, state="held" if held else "archived", why=None, held=held)
    return 1 if held else 0


MIGRATE_ROUNDS = 4


# ---------------------------------------------------------------------------------------------
# P5 selftest: the positive checks, the negative matrix, verify.json


CHECK_TIMEOUT = 60  # every P5 command (design P5), except:
INSTALL_TIMEOUT = 600  # `mise install` on a cold cache downloads uv, gitleaks and git-cliff
# `mise run verify` and `mise run test` run the whole test suite: helios's 1523 tests take
# 150-200 s. They get max(SUITE_TIMEOUT, twice the slowest suite run the last verify.json
# recorded), or --suite-timeout
SUITE_TIMEOUT = 600
SUITE_TASKS = (["mise", "run", "verify"], ["mise", "run", "test"])


@dataclass
class Check:
    name: str  # the command as the front door would quote it
    key: str  # what P6 matches a named command against: `mise run <task>`, `mise install`
    argv: list[str]
    required: bool  # False: recorded, never fails P5 (`start -- --help` may be a [gap] input)
    exit: int = 0
    green: bool = False
    seconds: float = 0.0
    output: str = ""  # the first non-empty stdout line
    tail: str = ""  # the last output lines, when it is not green
    cwd: str = "."  # the repo-relative folder it runs in
    timeout: int = CHECK_TIMEOUT  # seconds; see run_check


def start_command(args: list[str]) -> str:
    return "mise run start" + (f" -- {shlex.join(args)}" if args else "")


def repo_distribution(root: Path) -> str | None:
    """The distribution render used: its saved DISTRIBUTION value, else tech-stack.md's."""
    saved = table(load_toml(root / MANIFEST), "values").get("DISTRIBUTION")
    return saved if isinstance(saved, str) and saved else distribution(root)


def positive_checks(
    root: Path, start_args: list[str], scratch: Path, suite: int = SUITE_TIMEOUT
) -> list[Check]:
    """P5's positive checks, in order: setup, doctor, the gate, every other command the
    generated files name (`-- --help` where running it would write), the leak rules over the
    uncommitted text, the release dry-runs of a distributable project, the dry-run of each
    per-signal skill render wrote, then the happy path. Builds go to scratch, never the repo."""
    checks = [
        Check("mise install", "mise install", ["mise", "install"], True),
        Check("mise run doctor", "mise run doctor", ["mise", "run", "doctor"], True),
        Check("mise run verify", "mise run verify", ["mise", "run", "verify"], True),
        Check("mise tasks ls", "mise tasks ls", ["mise", "tasks", "ls"], True),
        Check("mise run status", "mise run status", ["mise", "run", "status"], True),
    ]
    for task in ("change", "backlog", "tdd", "proof"):
        argv = ["mise", "run", task, "--", "--help"]
        checks.append(Check(f"mise run {task} -- --help", f"mise run {task}", argv, True))
    help_argv = ["mise", "run", "start", "--", "--help"]
    start_help = Check("mise run start -- --help", "mise run start", help_argv, False)
    checks.append(start_help)
    for rel in ("specs", ".claude", "project_memory"):
        if (root / rel).exists():
            argv = ["mise", "x", "--", "gitleaks", "dir", "--no-banner", "--redact"]
            argv += ["-c", ".gitleaks.toml", rel]
            checks.append(Check(f"gitleaks dir {rel}", f"gitleaks dir {rel}", argv, True))
    if repo_distribution(root) in ("pypi", "git"):  # the release task's own dry-runs
        for name, argv in (
            (
                "uv version --bump patch --dry-run",
                ["uv", "version", "--bump", "patch", "--dry-run"],
            ),
            ("git cliff --bumped-version", ["git-cliff", "--bumped-version"]),
            ("uv build -o $TMPDIR", ["uv", "build", "-o", str(scratch / "dist")]),
        ):
            key = "uv build" if name.startswith("uv build") else name
            checks.append(Check(name, key, ["mise", "x", "--", *argv], True))
    skills, _ = signal_skills(root)
    for skill in skills:
        if not (root / ".claude" / "skills" / skill.name / "SKILL.md").is_file():
            continue  # render did not write it: nothing claims its commands work
        if skill.argv == help_argv:  # run-<name> quotes `start -- --help`: now it must pass
            start_help.required = True
            continue
        argv = [str(scratch / skill.name) if a == "{TMP}" else a for a in skill.argv]
        checks.append(Check(skill.command, f"skill {skill.name}", argv, True, cwd=skill.cwd))
    happy = ["mise", "run", "start", *(["--", *start_args] if start_args else [])]
    if happy == help_argv:  # the happy path is `start -- --help`: one row, the last, required
        checks.remove(start_help)
    checks.append(Check(start_command(start_args), "mise run start", happy, True))
    for check in checks:
        if check.argv[:2] == ["mise", "install"]:
            check.timeout = INSTALL_TIMEOUT
        elif is_suite(check):
            check.timeout = suite
    return checks


def is_suite(check: Check) -> bool:
    return check.argv[:3] in SUITE_TASKS


def suite_timeout(root: Path, given: int | None) -> tuple[int, str]:
    """(seconds, why) for the checks that run the whole test suite: --suite-timeout, else
    max(SUITE_TIMEOUT, twice the slowest suite check the last verify.json recorded)."""
    if given:
        return given, "--suite-timeout"
    last = 0.0
    try:
        data = json.loads(read_text(root / VERIFY_JSON) or "{}")
    except json.JSONDecodeError:
        data = {}
    checks = data.get("checks") if isinstance(data, dict) else None
    for check in checks if isinstance(checks, list) else []:
        argv = check.get("argv") if isinstance(check, dict) else None
        seconds = check.get("seconds") if isinstance(check, dict) else None
        if isinstance(argv, list) and argv[:3] in SUITE_TASKS and isinstance(seconds, int | float):
            last = max(last, float(seconds))
    if last * 2 > SUITE_TIMEOUT:
        return math.ceil(last * 2), f"twice the {last:.0f} s the last run took"
    shown = f"; the last run took {last:.0f} s" if last >= 1 else ""
    return SUITE_TIMEOUT, f"the floor{shown}"


def run_check(root: Path, check: Check, env: dict[str, str]) -> None:
    timeout = check.timeout
    began = time.monotonic()
    # own group: a timeout (a server that never exits, say) kills mise and all it started. The
    # output kept is bounded (head and tail), so a flood costs no memory.
    result = run(check.argv, cwd=root / check.cwd, env=env, timeout=timeout, own_group=True)
    check.seconds = round(time.monotonic() - began, 1)
    check.exit = result.code
    check.green = result.code == 0
    check.output = next((ln.strip() for ln in result.out.splitlines() if ln.strip()), "")[:200]
    if not check.green:
        lines = [ln for ln in (result.err + "\n" + result.out).splitlines() if ln.strip()]
        check.tail = " | ".join(lines[-3:])[-300:]
        if result.code == 124:
            check.tail = f"timed out after {timeout} s"
            if is_suite(check):
                check.tail += ": the suite needs longer; re-run with --suite-timeout <seconds>"


# the probe's pass rows, best first. No args beats the guessed `100` (fallback): a CLI that
# runs bare needs no made-up argument, and the guess stands in only when a bare run fails.
HAPPY_SOURCES = ("readme", "given", "no-args", "fallback", "help")
# how the `happy args` line names each source: the words P1 prints for the same row
HAPPY_WORDS = {
    "readme": "a README fence",
    "given": "the args given to the probe",
    "no-args": "a bare run",
    "fallback": "guessed args: no README fence",
    "help": "--help",
}


def default_start_args(root: Path) -> tuple[list[str], str]:
    """(the happy path's args, where they came from) when --start-args names none: the entry
    script's first README fence, else the probe's best passing row (HAPPY_SOURCES), else none."""
    scripts = console_scripts(root)
    if not scripts:
        return [], "no console script: no args"
    entry = next(iter(scripts))
    found = readme_invocations(read_text(root / "README.md") or "", entry, entry)
    fenced = next((args for env, args in found if not env), None)
    if fenced is not None:
        return fenced, "the README's first fence"
    report = probe(root, [], keep=False)
    if report.status != "ran":
        return [], f"no README fence, and the probe {report.status} ({report.reason}): no args"
    passing = [r for r in report.rows if r.script == entry and r.outcome == "pass" and not r.env]
    for source in HAPPY_SOURCES:
        row = next((r for r in passing if r.source == source), None)
        if row is not None:
            return row.args, f"the probe's pass row ({HAPPY_WORDS[source]})"
    return [], "no README fence and no probe pass row: no args"


def report_check_line(check: Check) -> None:
    if check.green:
        state = "ok"
    elif check.required:
        state = "FAIL"
    else:
        state = "gap"
    detail = f" (exit {check.exit}, {check.seconds:.1f} s)" if not check.green else ""
    note = "; not required: a [gap] input may crash" if state == "gap" else ""
    tail = f": {check.tail}" if check.tail and state == "FAIL" else ""
    where = f" (in {check.cwd}/)" if check.cwd != "." else ""
    print(f"  {state:<5} {check.name}{where}{detail}{note}{tail}")


def cmd_selftest(args: argparse.Namespace) -> int:
    root = repo_root(args.repo)
    if not (root / "scripts" / "project.py").is_file():
        raise Refusal("selftest: scripts/project.py is missing; run render first")
    extra = [a for a in args.rest if a != "--"]
    # `uv` is often a mise shim, and a shim refuses to run under an untrusted mise.toml
    shim = run(["uv", "--version"], cwd=root, timeout=60)
    if shim.code != 0 and "not trusted" in shim.err:
        print(
            f"selftest: mise does not trust {root / 'mise.toml'} yet, so the uv shim will not "
            f"run. Run `mise trust` in {root} first (P4 does), then re-run.",
            file=sys.stderr,
        )
        return 1
    if args.start_args is None:
        start_args, source = default_start_args(root)
    else:
        try:
            start_args = shlex.split(args.start_args)
        except ValueError as exc:
            raise UsageError(f"--start-args: {exc}") from exc
        source = "--start-args"
    env = {k: v for k, v in os.environ.items() if k not in ("VIRTUAL_ENV",)}
    suite, why = suite_timeout(root, args.suite_timeout)
    scratch = Path(tempfile.mkdtemp(prefix="project-init-selftest-"))
    try:
        checks = positive_checks(root, start_args, scratch, suite)
        print(label("positive") + f"{len(checks)} checks in {root}")
        print(
            label("timeouts")
            + f"{CHECK_TIMEOUT} s per check; mise install {INSTALL_TIMEOUT} s; mise run verify "
            f"and test {suite} s ({why}): they run the whole test suite"
        )
        print(label("happy args") + f"{shlex.join(start_args) or '(none)'}, from {source}")
        for check in checks:
            run_check(root, check, env)
            report_check_line(check)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    happy = checks[-1]
    if happy.green:
        shown = f' -> "{happy.output}"' if happy.output else " (no output)"
        print(label("happy path") + happy.name + shown)
    else:
        print(
            label("happy path") + f"{happy.name} is not green: pass one that works with "
            "--start-args '<args>' (the probe's pass row)"
        )

    argv = ["uv", "run", "--script", "scripts/project.py", "selftest", *extra]
    print(label("matrix") + shlex.join(argv))
    sys.stdout.flush()
    try:
        matrix = subprocess.run(argv, cwd=root, check=False).returncode  # noqa: S603 - fixed argv
    except FileNotFoundError:
        print("selftest: uv not found", file=sys.stderr)
        matrix = 127
    positive_green = all(c.green for c in checks if c.required)
    record = {
        "standard": STANDARD,
        "at": dt.datetime.now(dt.UTC).astimezone().isoformat(timespec="seconds"),
        "fingerprint": verify_fingerprint(root),
        "checks": [asdict(c) for c in checks],
        "start": {
            "args": start_args,
            "command": happy.name,
            "output": happy.output,
            "green": happy.green,
        },
        "matrix": {"argv": argv, "exit": matrix, "green": matrix == 0},
        "green": positive_green and matrix == 0,
    }
    install(root, VERIFY_JSON, (json.dumps(record, indent=2) + "\n").encode("utf-8"), 0o644)
    red = sum(1 for c in checks if c.required and not c.green)
    verdict = "green" if record["green"] else "NOT green"
    print(
        label("verify")
        + f"{VERIFY_JSON}: {verdict} ({sum(c.green for c in checks)} of {len(checks)} checks "
        f"green, {red} required failed; matrix exit {matrix})"
    )
    if matrix != 0:
        return matrix
    return 0 if positive_green else 1


# ---------------------------------------------------------------------------------------------
# CLI


def positive_seconds(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError:
        value = 0
    if value <= 0:
        raise argparse.ArgumentTypeError(f"{raw!r}: a whole number of seconds above 0")
    return value


def repo_root(raw: str) -> Path:
    root = Path(raw).expanduser()
    if not root.is_dir():
        raise UsageError(f"{raw}: not a folder")
    return root.resolve()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="init.py", description=__doc__.splitlines()[0] if __doc__ else None
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("preflight", help="P0: read-only facts, mode and stops")
    p.add_argument("repo", nargs="?", default=".")
    p.add_argument("--json", action="store_true")
    p.add_argument("--offline", action="store_true", help="no gh calls, no ls-remote")
    p.add_argument("--vault", default=str(Path.home() / "helm"), help="read-only vault root")
    p.add_argument("--search-root", action="append", default=[], help="where other checkouts live")
    p.set_defaults(func=cmd_preflight)

    p = sub.add_parser(
        "probe", help="P1: entrypoints in a scratch clone, network off; the trunk candidates"
    )
    p.add_argument("repo", nargs="?", default=".")
    p.add_argument("--json", action="store_true")
    p.add_argument("--args", action="append", default=[], help="a happy-path argument string")
    p.add_argument("--keep", action="store_true", help="keep the scratch clone")
    p.set_defaults(func=cmd_probe)

    p = sub.add_parser(
        "prepare", help="P4, before render: the Python pin, the dev group, the lock, the venv"
    )
    p.add_argument("repo", nargs="?", default=".")
    p.add_argument(
        "--python",
        help="the X.Y to pin when the repo has no .python-version (the one P1 reported built)",
    )
    p.add_argument("--dry-run", action="store_true", help="print what would run; run nothing")
    p.set_defaults(func=cmd_prepare)

    p = sub.add_parser("render", help="P4/EXTEND machinery, or P6 --front-door; hash-aware")
    p.add_argument("repo", nargs="?", default=".")
    p.add_argument("--check", action="store_true", help="report drift, write nothing")
    p.add_argument("--values", help="JSON object of placeholder values, or @file.json")
    p.add_argument("--force-file", action="append", default=[], help="take the render for it")
    p.add_argument(
        "--keep-file",
        action="append",
        default=[],
        help="keep yours; ask again when the template moves",
    )
    p.add_argument("--remote", choices=["github"], help="CI for a remote P7 will create")
    p.add_argument("--offline", action="store_true", help="no gh api for the CI action refs")
    p.add_argument(
        "--agents-symlink",
        action="store_true",
        help="also .agents/skills/sdd -> ../../.claude/skills/sdd (kept on later renders)",
    )
    p.add_argument(
        "--front-door",
        action="store_true",
        help=f"P6: AGENTS.md and the README quickstart, from {VERIFY_JSON}",
    )
    p.set_defaults(func=cmd_render)

    p = sub.add_parser("publish", help="P7: the ship commit, then the remote steps")
    p.add_argument("repo", nargs="?", default=".")
    p.add_argument(
        "--remote",
        choices=["github"],
        help="also create the private GitHub repo and push (D2); only when there is no origin",
    )
    p.add_argument(
        "--repo",
        dest="repo_name",
        help="the GitHub repo --remote github creates (default: the folder's name)",
    )
    p.add_argument("--dry-run", action="store_true", help="print what would run; run nothing")
    p.set_defaults(func=cmd_publish)

    p = sub.add_parser(
        "migrate-v2", help="EXTEND + v2 migrate: the one prompt, then the moves (--apply)"
    )
    p.add_argument("repo", nargs="?", default=".")
    p.add_argument(
        "--apply",
        action="store_true",
        help="on plan/project-init, after the yes and P2: git mv, the deletions, the edits",
    )
    p.set_defaults(func=cmd_migrate_v2)

    p = sub.add_parser("migrate-transcripts", help="MIGRATE: quarantine, redact, archive")
    p.add_argument("repo", nargs="?", default=".")
    p.add_argument(
        "--archive-root", default=str(Path.home() / "helm" / "13-archive" / "historical-sessions")
    )
    p.add_argument(
        "--quarantine-root",
        default=str(Path.home() / ".local" / "state" / "project-init" / "quarantine"),
    )
    p.add_argument(
        "--name", help="archive folder name (default: origin's repo name, else the project name)"
    )
    p.add_argument(
        "--resume",
        action="store_true",
        help="finish this repo's unfinished quarantine (a stopped or failed run)",
    )
    p.set_defaults(func=cmd_migrate)

    p = sub.add_parser(
        "migrate-v1",
        help="MIGRATE: the v1 prompt, or with --apply the P4 moves (legacy knowledge, hooks)",
    )
    p.add_argument("repo", nargs="?", default=".")
    p.add_argument(
        "--apply",
        action="store_true",
        help=(
            "on plan/project-init, after migrate-transcripts: render the legacy knowledge "
            "report, unregister and git rm the hooks, git rm the JSON, drop the .gitignore block"
        ),
    )
    p.set_defaults(func=cmd_migrate_v1)

    p = sub.add_parser("selftest", help="P5: positive checks, then the negative matrix")
    p.add_argument("repo", nargs="?", default=".")
    p.add_argument(
        "--start-args",
        help=(
            "the happy path's arguments, as one string (default: the README's first fence, "
            "else the probe's passing row)"
        ),
    )
    p.add_argument(
        "--suite-timeout",
        type=positive_seconds,
        metavar="SECONDS",
        help=(
            f"the timeout of `mise run verify` and `mise run test`, which run the whole suite "
            f"(default: max({SUITE_TIMEOUT}, twice the last run's time))"
        ),
    )
    p.add_argument("rest", nargs="*", help="after --: arguments for project.py selftest")
    p.set_defaults(func=cmd_selftest)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except UsageError as exc:
        return fail(str(exc), 2)
    except Refusal as exc:
        return fail(str(exc), 1)
    except Stopped as exc:
        return fail(f"stopped by {exc.name}", 128 + exc.signum)
    except KeyboardInterrupt:
        return fail("interrupted", 130)


def fail(message: str, code: int) -> int:
    """Why the command stopped, on stderr, after everything it printed on stdout."""
    sys.stdout.flush()
    print(f"init.py: {message}", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
