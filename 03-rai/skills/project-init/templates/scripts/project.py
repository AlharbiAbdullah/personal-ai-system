#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""This repo's one script: spec checks, status, TDD proofs, git gates, and the lifecycle.

The process it enforces is written once, in specs/README.md. Run it through mise:
  mise run spec-check            -> check          (after `mise run test`)
  mise run status [-- --change]  -> status
  mise run change -- <slug>      -> change         (then /sdd talk)
  mise run tdd -- red <ids>      -> tdd red        (then minimal code, then tdd green)
  mise run prove-red             -> prove-red      (merge runs it; CI on pull requests)
  mise run proof -- <verb>       -> proof          (what a reviewer looks at; validate)
  ! mise run approve | merge | abandon | release   (human gates: a person types them)

Subcommands:
  check  [--change <slug>] [--strict]   scenario grammar, scenario <-> test trace (I3),
                                        change-folder lint (I13, I17, I21, I22), the trunk
                                        map, lane rules on the branch diff (I1, I2, I5, I7,
                                        I11), doc commands (I15), caps
  status [--change] [--merge] [--audit] where this branch stands and what comes next; --merge
                                        is the Definition of Done, read-only; --audit warns
                                        for default-branch commits without Merged-By
  change <slug> [--lane] [--hotfix] [--parallel]
                                        a lane branch (feat: plus its change folder), one open
                                        change at a time (I8)
  backlog <topic> [--spike]             specs/backlog/<date>-<slug>.md (--spike: scratch tree)
  approve                               G2: lint, status approved, Spec-Approved: commit
  merge [--branch] [--attest] [--read-trunk] [--gate-change] [--reapprove] [--title]
        [--allow <id> --reason] [--without-ci <why>] [--dry-run]
                                        G1/G3: the Definition of Done (the proof bundle too),
                                        the close commit, then
                                        a squash onto the default branch (Merged-By): locally,
                                        or through a pull request once the checks that gate it
                                        pass, then the default branch synced to its merge
  abandon <why>                         tag abandoned/<slug>, backlog report, branch deleted
  doctor                                tools, git gates, env contract and flags, the trunk
                                        map, repo rules, audit
  release <bump> [--dry-run]            by specs/tech-stack.md's Distribution
  tdd red|green <ids>                   red: every new or changed test of each id fails for
                                        the right reason (AssertionError, NotImplementedError,
                                        DID NOT RAISE); green: every recorded red id now passes
  prove-red [--base <ref>]              the tests of new and changed scenarios fail on the old
                                        code; guards (flag-off ones too) pass there, gaps
                                        xfail, no test vanished
  hook pre-commit|commit-msg|pre-push   the git gates; .githooks/<name> calls these (the fourth
                                        hook, reference-transaction, is sh and guards main)
  hook install                          the local git config the gates need, and the main
                                        guard's record of the default branch (mise install)
  hook session-start|pre-bash           Claude Code's hooks (.claude/settings.json), hook JSON on
                                        stdin: the derived session block (3 KB at most), and the
                                        Bash guard (exit 2 blocks); from another worktree, they
                                        run that worktree's own scripts/project.py
  selftest [--keep]                     every gate case, run for real in a scratch clone with a
                                        bare origin, then the Claude hooks' cases (mise run
                                        selftest)
  proof run|log|http|shot|video|tape|attach|confidence|tests|show|setup
                                        the proof bundle: each capture one commit under
                                        proof/<date>-<slug>/, indexed by its README.md (I23 I24)

Written by project-init. Stdlib only. It is a gate file: merge asks for --gate-change.
"""

from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import html
import json
import math
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import datetime
from itertools import pairwise
from pathlib import Path, PurePosixPath

VERSION = "3.1.0"

SPECS = "specs"
CAPS_DIR = "specs/capabilities"
CHANGES_DIR = "specs/changes"
MISSION = "specs/mission.md"
ROADMAP = "specs/roadmap.md"
TECH_STACK = "specs/tech-stack.md"
PROCESS = "specs/README.md"
CHANGELOG = "CHANGELOG.md"
RESULTS = ".cache/spec-results.json"
RESULTS_FORMAT = 3
NOT_TEST_INPUTS = ("specs/", ".cache/", "proof/")  # edits here never change a test outcome
# git settings for tree_files: `ls-files -m` checks every tracked file against its full stat
# data (content when racy), never through an fsmonitor or a cache a local config could leave
# stale. tests/conftest.py passes the same ones.
FULL_STAT = (
    *("-c", "core.fsmonitor=false"),
    *("-c", "core.untrackedCache=false"),
    *("-c", "core.checkStat=default"),
    *("-c", "core.trustctime=true"),
)

LANES = ("feat", "chg", "fix", "chore", "refactor", "plan")
SPEC_LANES = ("feat", "chg", "fix", "plan")
FROZEN_SPEC_LANES = ("chore", "refactor", "release")  # never touch specs/capabilities/
TOOL_TRAILER = (
    "Merged-By",
    "mise run merge",
)  # written only by merge, abandon and release
INIT_BRANCH = "plan/project-init"

ID_RE = re.compile(r"^[a-z][a-z0-9-]*\.[a-z0-9][a-z0-9-]*$")
SLUG = r"[a-z0-9][a-z0-9-]*"
H1_RE = re.compile(r"^# Capability: (\S+)\s*$")
REQ_RE = re.compile(r"^## Requirement: (.+?)\s*$")
SCEN_RE = re.compile(r"^### Scenario: (\S+)(.*)$")
SCEN_HEADING_RE = re.compile(r"^[ \t]*#{1,6}[ \t]+Scenario:")
SCEN_TAG_RE = re.compile(r"\s*\[(gap|flag-off): ([^\]]*)\]")  # after a scenario's ID
ENV_NAME_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")  # a flag: in Rollback, a [flag-off: <ENV_NAME>]
STEP_RE = re.compile(r"^- (GIVEN|WHEN|THEN|AND)\s+\S")
LOOSE_STEP_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(?:GIVEN|WHEN|THEN|AND)\b")
HEADING_RE = re.compile(r"^[ \t]*#{1,6}(?:[ \t]|$)")
SETEXT_RE = re.compile(r"^(?:=+|-+)$")
FENCE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})(.*)$")
SHALL_RE = re.compile(r"\bSHALL\b")
NEEDS_RE = re.compile(r"\[\s*NEEDS\s+CLARIFICATION", re.IGNORECASE)
MARKER_RE = re.compile(r"\[\s*NEEDS\s+CLARIFICATION[^\]]*\]?", re.IGNORECASE)
PLACEHOLDER_RE = re.compile(r"\{[A-Z][A-Z0-9_]*\}")
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
ROADMAP_ITEM_RE = re.compile(rf"^- \[([ xX])\] ({SLUG})(?::|\s|$)")
# A branch slug launch-<slug> launches the roadmap item <slug> (design D.2): its merge appends
# ` (launched <date>)` to that item. An item whose title holds `(launched` is launched.
LAUNCH_PREFIX = "launch-"
LAUNCHED_MARK = "(launched"
LAUNCHED_RE = re.compile(r" \(launched \d{4}-\d{2}-\d{2}\)")
CHANGE_DIR_RE = re.compile(rf"^\d{{4}}-\d{{2}}-\d{{2}}-({SLUG})$")
GROUP_RE = re.compile(r"^## G(\d+) (.+?) \| (.+?) \| risk: (low|high) \| parallel: (yes|no)\s*$")
GROUPISH_RE = re.compile(r"\bG\d+\b[^|]*\|")  # a group header written some other way
REVIEW_ROW_RE = re.compile(r"^- (.+?)\s+->\s+(.+?)\s*$")
TITLE_RE = re.compile(
    r"^(feat|change|fix|perf|refactor|build|ci|docs|test|chore|spec|style|revert)"
    r"(\([^()\s]+\))?!?: \S"
)
# `mise run X` or `mise r X`, past flags and a quote. A task name ends in a word character, so
# sentence punctuation ("mise run verify.") stays out.
MISE_RUN_RE = re.compile(
    r"\bmise\s+(?:run|r)\s+(?:--?[A-Za-z][\w-]*(?:=\S*)?\s+)*[\"']?"
    r"([A-Za-z0-9_](?:[A-Za-z0-9_:.-]*[A-Za-z0-9_])?)"
)
STATUSES = ("draft", "approved", "done")

# TDD (specs/README.md, "Tests and commits"). A red test fails in its body on an assertion, on
# the NotImplementedError of a stub, or on a pytest.raises that saw nothing: those fail for the
# reason the missing behaviour gives. A red on a name or a module the code does not have yet
# (an ImportError, a NameError, `module 'x' has no attribute 'y'`), on a SyntaxError, or in a
# fixture says the code is absent, not that it behaves wrongly. Any other exception the body
# lets out was raised by code that exists (the ValueError a fix/ regression test meets): that is
# red too, since the old code misbehaves on the scenario.
TDD_DIR = ".agent/tdd"
RIGHT_REDS = ("AssertionError", "NotImplementedError", "DID NOT RAISE")
WRONG_REDS = (
    "ImportError",
    "ModuleNotFoundError",
    "NameError",
    "UnboundLocalError",
    "SyntaxError",
    "IndentationError",
    "TabError",
)
MISSING_ATTR_RE = re.compile(r"^AttributeError: module '[^']+' has no attribute ")
STUB_HINT = "add a stub that raises NotImplementedError"
TEST_SIDE_HINT = (
    "the test's own code raised it, which says nothing about the code under test; assert on "
    "what the command prints or returns instead"
)
PYTEST_TIMEOUT = 900  # seconds for one pytest run inside tdd or prove-red
REASON_CAP = 120  # a Red: trailer holds one short line
# Environment that would point a child uv, pytest or git at the wrong tree or change what runs.
SCRUB_ENV = (
    "VIRTUAL_ENV",
    "UV_PROJECT_ENVIRONMENT",
    "PYTEST_ADDOPTS",
    "PYTEST_PLUGINS",
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_COMMON_DIR",
    "GIT_OBJECT_DIRECTORY",
    "GIT_PREFIX",
)
REQ_NAME_RE = re.compile(r"^\s*([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)")

# CHANGELOG.md as merge writes it: git-cliff under the [tool.git-cliff] config project-init
# renders. A title's type picks the group (a `!` puts it under Removed); other types get no
# line. On a lane without a change folder, the lane bounds the group (specs/README.md, lane
# table): chore/ and plan/ get no line, refactor/ only a perf one.
TITLE_PARTS_RE = re.compile(r"^(\w+)(?:\(([^()\s]+)\))?(!)?: (.+)$")
CLIFF_GROUPS = {"feat": "Added", "change": "Changed", "fix": "Fixed", "perf": "Performance"}
BREAKING_GROUP = "Removed"
LANE_CHANGELOG_GROUPS = {
    "chg": ("Changed", "Removed"),
    "fix": ("Fixed",),
    "refactor": ("Performance",),
}
UNRELEASED = "## [Unreleased]"

# Size caps (specs/README.md, "Size caps"): passing one is a warning, never an error.
LINE_CAPS = {"requirements.md": 120, "plan.md": 100, "validation.md": 60}
CAPABILITY_CAP = 300
AGENTS_CAP = 40
MEMORY_README_CAP_BYTES = 1024
REVIEW_FOCUS_CAP = 5
HUMAN_CHECKS_CAP = 3

MISE_CONFIGS = (
    "mise.toml",
    ".mise.toml",
    "mise/config.toml",
    ".mise/config.toml",
    ".config/mise.toml",
    ".config/mise/config.toml",
)
MISE_TASK_DIRS = (
    "mise-tasks",
    ".mise-tasks",
    "mise/tasks",
    ".mise/tasks",
    ".config/mise/tasks",
)
DOCS_WITH_COMMANDS = ("AGENTS.md", "README.md", PROCESS)


class UsageError(Exception):
    """A problem the user fixes by calling the script differently; exit 2."""


# ---------------------------------------------------------------- git


def run_git(
    root: Path, *args: str, stdin: bytes | None = None
) -> subprocess.CompletedProcess[bytes]:
    """Run git with a fixed argv (no shell). Every git call in this script goes through here."""
    return subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=root,
        input=stdin,
        capture_output=True,
        check=False,
    )


def git(root: Path, *args: str) -> str | None:
    """stdout of a git command, or None when it fails."""
    proc = run_git(root, *args)
    if proc.returncode != 0:
        return None
    return proc.stdout.decode("utf-8", "replace")


def git_lines(root: Path, *args: str) -> list[str]:
    out = git(root, *args)
    return [line for line in (out or "").splitlines() if line]


def read_blobs(root: Path, ref: str, paths: list[str]) -> dict[str, str]:
    """Contents of paths at ref, in one `git cat-file --batch`; missing paths are left out."""
    if not paths:
        return {}
    request = "".join(f"{ref}:{path}\n" for path in paths).encode()
    out = run_git(root, "cat-file", "--batch", stdin=request).stdout
    blobs: dict[str, str] = {}
    pos = 0
    for path in paths:
        end = out.find(b"\n", pos)
        if end < 0:
            break
        header = out[pos:end].decode("utf-8", "replace").split()
        pos = end + 1
        if len(header) == 3 and header[1] == "blob":
            size = int(header[2])
            blobs[path] = out[pos : pos + size].decode("utf-8", "replace")
            pos += size + 1
    return blobs


TRAILERS_FORMAT = "--format=%(trailers:only,unfold)%x00"


def commit_trailers(root: Path, *revs: str) -> list[str]:
    """The trailer block of each commit git log lists for revs, as git itself parses it: only
    the message's last paragraph, and only when it is made of trailers. A subject such as
    `spec: reword cli.no-args` or a prose line that starts with `Spec:` is never a trailer."""
    out = git(root, "log", TRAILERS_FORMAT, *revs) or ""
    return [block.strip("\n") for block in out.split("\0") if block.strip()]


def trailer_values(trailers: str, key: str) -> list[str]:
    """The values of one key in a trailer block from commit_trailers(). Never pass a whole
    commit message: its subject and body lines would be read as trailers too."""
    prefix = key.lower() + ":"
    return [
        line.split(":", 1)[1].strip()
        for line in trailers.splitlines()
        if line.lower().startswith(prefix)
    ]


# ---------------------------------------------------------------- repo context


@dataclass
class Context:
    """Where we are: repo root, default branch, current branch and its merge-base."""

    root: Path
    name: str
    default: str
    branch: str | None
    head: str | None
    default_ref: str | None
    base: str | None  # merge-base with the default branch; None on it (or when unknown)

    @property
    def on_default(self) -> bool:
        return self.branch == self.default

    @property
    def lane(self) -> str | None:
        if not self.branch or "/" not in self.branch:
            return None
        prefix = self.branch.split("/", 1)[0]
        return prefix if prefix in (*LANES, "release") else None

    @property
    def slug(self) -> str | None:
        if not self.lane or not self.branch:
            return None
        return re.sub(r"--g\d+$", "", self.branch.split("/", 1)[1])


def find_root(start: Path) -> Path | None:
    out = git(start, "rev-parse", "--show-toplevel")
    return Path(out.strip()) if out else None


def parse_toml(text: str) -> dict[str, object]:
    """tomllib.loads; it raises ValueError (tomllib.TOMLDecodeError) on bad TOML. The import
    lives here so the import block sorts the same under any ruff target: tomllib is stdlib
    from Python 3.11, and ruff's default target (3.10) files it as third-party."""
    import tomllib

    return tomllib.loads(text)


def load_toml(path: Path) -> dict[str, object]:
    try:
        return parse_toml(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:  # ValueError: bad TOML, or bytes that are not UTF-8
        raise UsageError(f"{path.name}: {exc}") from exc


def project_name(root: Path) -> str:
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        project = load_toml(pyproject).get("project")
        if isinstance(project, dict) and isinstance(project.get("name"), str):
            return str(project["name"])
    return root.name


def load_context(root: Path) -> Context:
    config = load_toml(root / ".project.toml") if (root / ".project.toml").is_file() else {}
    default = config.get("default_branch")
    default = default if isinstance(default, str) and default else "main"
    out = git(root, "symbolic-ref", "-q", "--short", "HEAD")
    branch = out.strip() if out else None
    # GitHub's variables name the branch and its base only in CI: set by hand, they would move
    # the base under the branch and empty its diff.
    ci = os.environ.get("GITHUB_ACTIONS") == "true"
    if branch is None and ci:  # detached: CI checks out a PR merge commit
        branch = os.environ.get("GITHUB_HEAD_REF") or os.environ.get("GITHUB_REF_NAME") or None
    out = git(root, "rev-parse", "-q", "--verify", "HEAD^{commit}")
    head = out.strip() if out else None
    target = (os.environ.get("GITHUB_BASE_REF") if ci else None) or default
    if target == branch:  # a branch is never its own base
        target = default
    default_ref = None
    for ref in (f"refs/heads/{target}", f"refs/remotes/origin/{target}"):
        if git(root, "rev-parse", "-q", "--verify", f"{ref}^{{commit}}"):
            default_ref = ref
            break
    base = None
    if head and default_ref and branch != default:
        out = git(root, "merge-base", "HEAD", default_ref)
        base = out.strip() if out else None
    return Context(root, project_name(root), default, branch, head, default_ref, base)


def project_paths(root: Path) -> tuple[list[str], list[str]]:
    """(source roots, test roots) from .project.toml [paths]: prove-red swaps the source roots
    for the old code, and I7 counts the files under the test roots as tests, with a test_*.py
    or conftest.py beside the code (in_tests)."""
    config = load_toml(root / ".project.toml") if (root / ".project.toml").is_file() else {}
    return config_paths(config)


def committed_paths(
    root: Path, refs: tuple[str, ...] = ("HEAD", "")
) -> tuple[list[str], list[str]]:
    """[paths] as commits hold them: the roots each ref's .project.toml names, together ("" is
    the index). The git hooks read HEAD's and the staged one: a hook never reads the working
    tree's copy (an unstaged edit would steer it), and a commit that edits [paths] is held to the
    old roots and the new ones. prove-red reads HEAD's and the merge-base's."""
    src: list[str] = []
    tests: list[str] = []
    for ref in refs:
        text = read_blobs(root, ref, [".project.toml"]).get(".project.toml")
        try:
            config = parse_toml(text) if text else {}
        except ValueError as exc:
            where = ref[:10] if ref and ref != "HEAD" else ref or "the index"
            raise UsageError(f".project.toml in {where}: {exc}") from exc
        more_src, more_tests = config_paths(config)
        src += [r for r in more_src if r not in src]
        tests += [r for r in more_tests if r not in tests]
    return src, tests


def config_paths(config: dict[str, object]) -> tuple[list[str], list[str]]:
    """(source roots, test roots) from a parsed .project.toml; src and tests by default."""
    table = config.get("paths")
    paths = table if isinstance(table, dict) else {}

    def roots(key: str, default: str) -> list[str]:
        value = paths.get(key)
        values = [value] if isinstance(value, str) else value if isinstance(value, list) else []
        found: list[str] = []
        for item in values:
            if not isinstance(item, str):
                continue
            rel = PurePosixPath(item.strip())
            if rel.is_absolute() or ".." in rel.parts or str(rel) in ("", "."):
                raise UsageError(f".project.toml: [paths] {key} must name folders in the repo")
            found.append(rel.as_posix())
        return found or [default]

    return roots("src", "src"), roots("tests", "tests")


# ---------------------------------------------------------------- findings


@dataclass
class Report:
    lines: list[tuple[str, str]] = field(default_factory=list)

    def fail(self, text: str) -> None:
        self.lines.append(("FAIL", text))

    def warn(self, text: str) -> None:
        self.lines.append(("warn", text))

    def pend(self, text: str) -> None:
        self.lines.append(("pend", text))

    def note(self, text: str) -> None:
        """Something a human looks at, never a problem (merge lists it)."""
        self.lines.append(("note", text))

    def ok(self, text: str) -> None:
        self.lines.append(("ok", text))

    def count(self, level: str) -> int:
        return sum(1 for lvl, _ in self.lines if lvl == level)

    @property
    def errors(self) -> int:
        return self.count("FAIL")

    def print(self) -> None:
        for level, text in self.lines:
            print(f"{level:<5} {text}")


# ---------------------------------------------------------------- markdown helpers


def indent_of(line: str) -> int:
    expanded = line.expandtabs(4)
    return len(expanded) - len(expanded.lstrip())


@dataclass
class Block:
    """An open fenced code block or HTML comment: markdown hides lines until it closes."""

    kind: str  # "fence" | "comment"
    line: int
    indent: int
    marker: str = ""  # the fence's opening run, e.g. ```

    def closes(self, line: str) -> bool:
        if self.kind == "comment":
            return "-->" in line
        run = line.strip()
        return bool(run) and set(run) == {self.marker[0]} and len(run) >= len(self.marker)

    def outdented(self, line: str) -> bool:
        """A line left of the opener: inside a list item, markdown ends the block there."""
        return bool(line.strip()) and indent_of(line) < self.indent


def open_fence(line: str, number: int) -> Block | None:
    match = FENCE_RE.match(line)
    if not match or (match.group(1)[0] == "`" and "`" in match.group(2)):
        return None  # ``` followed by more backticks on the line is inline code, not a fence
    return Block("fence", number, indent_of(line), match.group(1))


def strip_comments(line: str) -> tuple[str, bool]:
    """line without its HTML comments, and whether a comment block stays open after it.

    As in markdown: a line that starts with `<!--` and does not close it opens a block that
    hides every line up to the one holding `-->`. A `<!--` later in a line that does not close
    on it stays literal text (markdown could hide only the rest of its paragraph, and a list
    item or heading on the next line always shows).
    """
    if line.lstrip().startswith("<!--") and line.find("-->", line.find("<!--") + 2) < 0:
        return "", True
    visible: list[str] = []
    while (start := line.find("<!--")) >= 0:
        end = line.find("-->", start + 2)  # `<!-->` is a whole (empty) comment
        if end < 0:
            break
        visible.append(line[:start])
        line = line[end + 3 :]
    visible.append(line)
    return "".join(visible), False


def prose_lines(text: str, *, hide_comments: bool = True) -> list[tuple[int, str]]:
    """(line number, line) as a markdown reader sees them: fenced code left out, inline code
    spans blanked, and HTML comments (on one line or across many, see strip_comments) cut out.
    A roadmap item or a Review focus row inside a comment therefore does not count.
    hide_comments=False keeps the comment text, for searches where hidden text must count."""
    out: list[tuple[int, str]] = []
    fence: Block | None = None
    in_comment = False
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw
        if in_comment:
            end = line.find("-->")
            if end < 0:
                continue
            in_comment = False
            line = line[end + 3 :]
        else:
            if fence is not None:
                if fence.closes(line):
                    fence = None
                    continue
                if not fence.outdented(line):
                    continue
                fence = None  # read the outdented line as prose, as markdown does
            if fence := open_fence(line, number):
                continue
        line = INLINE_CODE_RE.sub("``", line)
        if hide_comments:
            line, in_comment = strip_comments(line)
        out.append((number, line))
    return out


def shown_line(lines: list[str], number: int) -> str:
    """Line `number` (1-based, as prose_lines counts) as written, for display and records:
    inline code kept (prose_lines blanks it to ``), HTML comments cut."""
    raw = lines[number - 1] if 0 < number <= len(lines) else ""
    return strip_comments(raw)[0].strip()


def yaml_scalar(raw: str) -> str:
    """The value of a one-line YAML scalar: quoted strings unescaped, `# comments` dropped."""
    value = raw.strip()
    if value.startswith("#"):
        return ""  # `key:   # comment` is an empty value
    if value.startswith('"'):
        chars: list[str] = []
        escaped = False
        for char in value[1:]:
            if escaped:
                chars.append({"n": "\n", "t": "\t"}.get(char, char))
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                break
            else:
                chars.append(char)
        return "".join(chars)
    if value.startswith("'"):
        end = value.find("'", 1)
        while end > 0 and value[end : end + 2] == "''":
            end = value.find("'", end + 2)
        return value[1:end].replace("''", "'") if end > 0 else value[1:]
    return re.split(r"\s#", value, maxsplit=1)[0].strip()


def frontmatter(text: str) -> tuple[dict[str, str], str | None]:
    """Keys of a leading `---` block, and a problem when the block is malformed."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, "no frontmatter (a leading --- block)"
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields, None
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if not sep:
            return fields, f"frontmatter line is not 'key: value': {line.strip()}"
        fields[key.strip()] = yaml_scalar(value)
    return fields, "frontmatter has no closing ---"


# ---------------------------------------------------------------- capabilities


@dataclass
class Scenario:
    id: str
    path: str
    line: int
    gap: str | None
    block: str  # normalized header + steps, compared across refs to find MODIFIED
    flag_off: str | None = None  # [flag-off: <ENV>]: pins the old behaviour with the flag off


@dataclass
class _Req:
    title: str
    line: int
    text: list[str] = field(default_factory=list)
    scenarios: int = 0


@dataclass
class _Scen:
    id: str
    line: int
    gap: str | None
    header: str
    flag_off: str | None = None
    steps: list[str] = field(default_factory=list)
    body: list[str] = field(default_factory=list)


def scenario_tags(sid: str, rest: str) -> tuple[dict[str, str], str | None]:
    """The tags after a scenario ID, and a problem: `[gap: <roadmap-slug>]` marks known-broken
    behaviour, `[flag-off: <ENV_NAME>]` a guard that pins the old behaviour with that flag off.
    A scenario carries one or the other, each at most once."""
    tags: dict[str, str] = {}
    text = rest.rstrip()
    unknown = (
        f"unknown tag after {sid}: '{rest.strip()}' (only [gap: <slug>] and [flag-off: <ENV_NAME>])"
    )
    pos = 0
    while pos < len(text):
        match = SCEN_TAG_RE.match(text, pos)
        if match is None or match.group(1) in tags:
            return {}, unknown
        kind, value = match.group(1), match.group(2).strip()
        valid = re.fullmatch(SLUG, value) if kind == "gap" else ENV_NAME_RE.match(value)
        if not valid:
            return {}, unknown
        tags[kind] = value
        pos = match.end()
    if len(tags) > 1:
        return {}, f"scenario {sid} has a [gap] and a [flag-off] tag; it is one or the other"
    return tags, None


def parse_capability(path: str, text: str, report: Report | None) -> list[Scenario]:
    """Scenarios of one capability file; grammar problems go to report (None: parse only).

    Simple line rules, but where markdown would show a reader something this parser does not
    see (an indented heading, a block that markdown ends early), the line FAILs instead.
    """
    cap = PurePosixPath(path).stem
    scenarios: list[Scenario] = []
    seen_h1 = False
    req: _Req | None = None
    scen: _Scen | None = None
    block: Block | None = None  # an open fence or comment

    def fail(number: int, message: str) -> None:
        if report is not None:
            report.fail(f"{path}:{number}: {message}")

    def after_comment(number: int, line: str) -> None:
        if line.partition("-->")[2].strip():
            fail(number, "text after '-->' on a comment line; markdown shows it raw")

    def close_scenario() -> None:
        nonlocal scen
        if scen is None:
            return
        order = [("GIVEN", "WHEN", "THEN").index(s) for s in scen.steps if s != "AND"]
        if "WHEN" not in scen.steps or "THEN" not in scen.steps:
            fail(scen.line, f"scenario {scen.id} needs WHEN and THEN bullets")
        elif order != sorted(order) or scen.steps[0] == "AND":
            fail(scen.line, f"scenario {scen.id}: bullets go GIVEN, WHEN, THEN")
        normalized = "\n".join([scen.header, *scen.body])
        scenarios.append(Scenario(scen.id, path, scen.line, scen.gap, normalized, scen.flag_off))
        scen = None

    def close_requirement() -> None:
        nonlocal req
        close_scenario()
        if req is None:
            return
        shall = len(SHALL_RE.findall(" ".join(req.text)))
        if shall != 1:
            fail(
                req.line,
                f"requirement '{req.title}' needs exactly one SHALL sentence (found {shall})",
            )
        if not req.scenarios:
            fail(req.line, f"requirement '{req.title}' has no scenario")
        req = None

    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        stripped = line.strip()
        if block is not None:
            if block.closes(line):
                if block.kind == "comment":
                    after_comment(number, line)
                elif scen is not None:
                    scen.body.append(stripped)
                block = None
                continue
            if not block.outdented(line):
                if block.kind == "fence" and scen is not None:
                    scen.body.append(line)
                continue
            fail(
                number,
                f"line sits left of the {block.kind} opened on line {block.line}, so markdown "
                f"ends the {block.kind} here; indent it, or close the {block.kind} first",
            )
            block = None
        if stripped.startswith("<!--"):
            if "-->" in stripped:
                after_comment(number, stripped)
            else:
                block = Block("comment", number, indent_of(line))
            continue
        if fence := open_fence(line, number):
            block = fence
            if scen is None:
                fail(number, "code blocks belong inside a scenario (literal I/O only)")
            else:
                scen.body.append(stripped)
            continue
        if not stripped:
            continue
        if line.startswith("#") or HEADING_RE.match(line):
            if line != line.lstrip():
                fail(
                    number,
                    f"heading '{stripped}' is indented; headings start at column 1 "
                    "(literal output goes in a ``` fence)",
                )
            if match := H1_RE.match(stripped):
                if seen_h1:
                    fail(number, "only one '# Capability:' heading per file")
                elif match.group(1) != cap:
                    fail(
                        number,
                        f"heading names '{match.group(1)}', the file is '{cap}.md'",
                    )
                seen_h1 = True
            elif match := REQ_RE.match(stripped):
                close_requirement()
                req = _Req(match.group(1), number)
            elif match := SCEN_RE.match(stripped):
                close_scenario()
                sid, rest = match.group(1), match.group(2)
                tags, problem = scenario_tags(sid, rest)
                if problem:
                    fail(number, problem)
                gap, flag_off = tags.get("gap"), tags.get("flag-off")
                if not ID_RE.match(sid):
                    fail(
                        number,
                        f"scenario id '{sid}' must match <cap>.<slug> in lowercase",
                    )
                elif sid.split(".", 1)[0] != cap:
                    fail(number, f"scenario id '{sid}' must start with '{cap}.'")
                if req is None:
                    fail(number, f"scenario {sid} sits outside a '## Requirement:'")
                else:
                    req.scenarios += 1
                header = f"### Scenario: {sid}" + (f" [gap: {gap}]" if gap else "")
                header += f" [flag-off: {flag_off}]" if flag_off else ""
                scen = _Scen(sid, number, gap, header, flag_off)
            else:
                fail(number, f"unexpected heading '{stripped}'")
            continue
        if "Scenario:" in INLINE_CODE_RE.sub("``", stripped):
            fail(
                number,
                "'Scenario:' outside a heading; a scenario starts '### Scenario: <id>'",
            )
        if SETEXT_RE.match(stripped):
            fail(
                number,
                "a line of only '-' or '=' makes the line above a heading; drop it",
            )
        if scen is not None:
            if step := STEP_RE.match(line):
                scen.steps.append(step.group(1))
            elif not line.startswith("  "):
                fail(
                    number,
                    f"scenario {scen.id}: lines are '- GIVEN/WHEN/THEN/AND ...' bullets",
                )
            scen.body.append(" ".join(stripped.split()))
        elif req is not None:
            if LOOSE_STEP_RE.match(line):
                fail(
                    number,
                    "GIVEN/WHEN/THEN bullets belong under a '### Scenario: <id>' heading",
                )
            req.text.append(stripped)
        else:
            fail(
                number,
                "text outside a requirement (capability files hold requirements only)",
            )
    close_requirement()
    if block is not None:
        what = "code fence" if block.kind == "fence" else "comment"
        fail(block.line, f"{what} is never closed; markdown hides the rest of the file")
    if not seen_h1:
        fail(1, f"missing '# Capability: {cap}' heading")
    return scenarios


def capability_files(root: Path) -> tuple[list[str], list[str]]:
    """(capability files, stray markdown files): capabilities are specs/capabilities/<cap>.md,
    one level deep. A stray file (a subfolder, another suffix) is never parsed, so it FAILs."""
    folder = root / CAPS_DIR
    if not folder.is_dir():
        return [], []
    paths: list[str] = []
    strays: list[str] = []
    for path in sorted(folder.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if path.parent == folder and path.suffix == ".md":
            paths.append(rel)
        elif path.suffix.lower() in (".md", ".markdown"):
            strays.append(rel)
    return paths, strays


def load_scenarios(texts: dict[str, str], report: Report | None) -> dict[str, Scenario]:
    scenarios: dict[str, Scenario] = {}
    for path, text in sorted(texts.items()):
        for scenario in parse_capability(path, text, report):
            if scenario.id in scenarios and report is not None:
                first = scenarios[scenario.id]
                report.fail(
                    f"{scenario.id}: duplicate id ({first.path}:{first.line}, "
                    f"{scenario.path}:{scenario.line})"
                )
            scenarios.setdefault(scenario.id, scenario)
    return scenarios


def scenarios_at(root: Path, ref: str) -> dict[str, Scenario]:
    """The scenarios committed at ref, or staged in the index when ref is "" (grammar problems
    ignored: check reports those). An unborn HEAD has none."""
    if ref:
        listing = git_lines(root, "ls-tree", "-r", "--name-only", ref, "--", CAPS_DIR)
    else:
        listing = git_lines(root, "ls-files", "--", CAPS_DIR)
    paths = [
        p for p in listing if PurePosixPath(p).parent.as_posix() == CAPS_DIR and p.endswith(".md")
    ]
    return load_scenarios(read_blobs(root, ref, paths), None)


def roadmap_items(text: str) -> dict[str, bool]:
    """Roadmap slug -> ticked."""
    items: dict[str, bool] = {}
    for _, line in prose_lines(text):
        if match := ROADMAP_ITEM_RE.match(line.strip()):
            items[match.group(2)] = match.group(1) != " "
    return items


# ---------------------------------------------------------------- the trunk map

# `## Trunk` in specs/tech-stack.md names the paths whose diff a human reads at merge (specs/README.md,
# "Tech stack"): one `- <glob>: <why>` per line. A path no entry matches is leaf, tests included.
TRUNK_HEADING_RE = re.compile(r"^## Trunk(?:\s|\(|$)")


def glob_segment(part: str) -> str:
    """One path segment of a glob as a regex: `*` any run and `?` one character, both short of
    `/`; `[...]` a class (`[!...]` negated); a backslash quotes the next character."""
    out: list[str] = []
    index = 0
    while index < len(part):
        char = part[index]
        end = part.find("]", index + 2) if char == "[" else -1
        if char == "*":
            while part[index + 1 : index + 2] == "*":
                index += 1
            out.append("[^/]*")
        elif char == "?":
            out.append("[^/]")
        elif char == "\\" and index + 1 < len(part):
            index += 1
            out.append(re.escape(part[index]))
        elif end > 0:
            body = part[index + 1 : end]
            negate = body[:1] in ("!", "^")
            chars = "".join(c if c == "-" else re.escape(c) for c in (body[1:] if negate else body))
            out.append(f"[^/{chars}]" if negate else f"[{chars}]")
            index = end
        else:
            out.append(re.escape(char))
        index += 1
    return "".join(out)


def glob_regex(glob: str) -> re.Pattern[str]:
    """A gitignore-style glob as a regex over repo-relative posix paths, anchored at the repo
    root: `**` as a whole segment spans any number of folders (`**/x`, `a/**/x`, `a/**`), a
    trailing `/` names a folder and everything in it, and a leading `/` changes nothing. Unlike
    gitignore, a glob without a `/` never matches a basename further down: `config.py` is the
    root's own file."""
    text = glob.strip().removeprefix("./").lstrip("/")
    if text.endswith("/"):
        text += "**"
    parts = text.split("/")
    out: list[str] = []
    for index, part in enumerate(parts):
        last = index == len(parts) - 1
        if part == "**":
            out.append(".*" if last else "(?:[^/]+/)*")
        else:
            out.append(glob_segment(part) + ("" if last else "/"))
    return re.compile("".join(out))


@dataclass
class TrunkEntry:
    """One `- <glob>: <why>` line of the Trunk section."""

    glob: str
    why: str
    line: int
    pattern: re.Pattern[str] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        self.pattern = glob_regex(self.glob)

    def matches(self, path: str) -> bool:
        return self.pattern.fullmatch(path) is not None


@dataclass
class TrunkMap:
    """The Trunk section of a tech-stack.md: its entries, its grammar problems, and whether the
    file has the section at all (without one every path is leaf, and doctor warns)."""

    entries: list[TrunkEntry] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    found: bool = False

    def entry_for(self, path: str) -> TrunkEntry | None:
        return next((entry for entry in self.entries if entry.matches(path)), None)


def trunk_map(text: str | None) -> TrunkMap:
    """The `## Trunk` section of a specs/tech-stack.md text. Blank lines, comments and fenced
    blocks are skipped; a line of another shape, an empty why, or a glob that leaves the repo
    is a problem (check FAILs it)."""
    trunk = TrunkMap()
    if text is None:
        return trunk
    raw_lines = text.splitlines()
    inside = False
    for number, line in prose_lines(text):
        stripped = line.strip()
        if HEADING_RE.match(line):
            inside = TRUNK_HEADING_RE.match(stripped) is not None
            trunk.found = trunk.found or inside
            continue
        if not inside or not stripped:
            continue
        written = shown_line(raw_lines, number)  # `code` kept
        where = f"{TECH_STACK}:{number}"
        glob, colon, why = written.removeprefix("- ").partition(":")
        glob = glob.strip().strip("`").strip()
        parts = PurePosixPath(glob.lstrip("/")).parts
        if placeholder := PLACEHOLDER_RE.search(written):  # the template's line, unfilled
            trunk.problems.append(
                f"{where}: a Trunk line holds the placeholder {placeholder.group(0)}: write the "
                "entries talk settled, '- <glob>: <why>', or leave the section empty"
            )
        elif not written.startswith("- ") or not colon or not glob or len(glob.split()) > 1:
            trunk.problems.append(
                f"{where}: a Trunk line is '- <glob>: <why>', not '{snippet(written)}'"
            )
        elif not why.strip():
            trunk.problems.append(
                f"{where}: trunk entry '{glob}' needs its why: what makes it trunk"
            )
        elif ".." in parts:
            trunk.problems.append(f"{where}: trunk entry '{glob}' must name paths inside the repo")
        else:
            trunk.entries.append(TrunkEntry(glob, why.strip(), number))
    return trunk


def trunk_at(root: Path, ref: str | None = None) -> TrunkMap:
    """trunk_map() of specs/tech-stack.md at ref, or in the working tree when ref is None."""
    if ref is None:
        return trunk_map(read_text(root / TECH_STACK))
    return trunk_map(read_blobs(root, ref, [TECH_STACK]).get(TECH_STACK))


# ---------------------------------------------------------------- change folders


@dataclass
class Group:
    number: int
    name: str
    ids: list[str]
    risk: str
    parallel: str
    files: list[str] = field(default_factory=list)  # its Files: line, notes like (NEW) cut


@dataclass
class Change:
    name: str
    path: str
    fields: dict[str, str]
    groups: list[Group] = field(default_factory=list)
    review_ids: list[str] = field(default_factory=list)
    human_checks: list[str] = field(default_factory=list)
    proof_rows: list[ProofRow] = field(default_factory=list)  # validation.md's ## Proof

    @property
    def status(self) -> str:
        return self.fields.get("status", "")

    @property
    def slug(self) -> str:
        match = CHANGE_DIR_RE.match(self.name)
        return match.group(1) if match else self.name

    @property
    def roadmap(self) -> str:
        """The roadmap item this change builds: its `roadmap:` field, else its own slug."""
        return self.fields.get("roadmap") or self.slug


def decode(data: bytes) -> tuple[str, str | None]:
    """The text of a file's bytes, and a problem when they are not UTF-8. Bad bytes read as
    U+FFFD, so every other check still sees the rest of the file."""
    try:
        return data.decode("utf-8"), None
    except UnicodeDecodeError as exc:
        line = data.count(b"\n", 0, exc.start) + 1
        problem = f"not UTF-8 (byte 0x{data[exc.start]:02x} on line {line}); save it as UTF-8"
        return data.decode("utf-8", "replace"), problem


def read_text(path: Path) -> str | None:
    """A file's text, or None when there is no such file. encoding_problems() FAILs a file
    that is not UTF-8; reading it here as None would switch its checks off."""
    try:
        return decode(path.read_bytes())[0]
    except OSError:
        return None


def encoding_problems(root: Path) -> list[str]:
    """'<path>: not UTF-8' for each markdown file check reads (specs/, AGENTS.md, README.md)."""
    folder = root / SPECS
    paths = sorted(folder.rglob("*.md")) if folder.is_dir() else []
    paths += [root / name for name in ("AGENTS.md", "README.md")]
    problems: list[str] = []
    for path in paths:
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if problem := decode(data)[1]:
            problems.append(f"{path.relative_to(root).as_posix()}: {problem}")
    return problems


def load_changes(root: Path) -> dict[str, Change]:
    changes: dict[str, Change] = {}
    folder = root / CHANGES_DIR
    if not folder.is_dir():
        return changes
    for sub in sorted(p for p in folder.iterdir() if p.is_dir()):
        text = read_text(sub / "requirements.md") or ""
        fields, _ = frontmatter(text)
        change = Change(sub.name, f"{CHANGES_DIR}/{sub.name}", fields)
        change.groups = parse_groups(read_text(sub / "plan.md") or "", None, "")
        changes[sub.name] = change
    return changes


def find_change(changes: dict[str, Change], slug: str) -> Change | None:
    if slug in changes:
        return changes[slug]
    matches = [c for c in changes.values() if c.slug == slug]
    live = [c for c in matches if c.status != "done"]
    return (live or matches or [None])[0]


def group_files(line: str) -> list[str]:
    """The paths of a `Files:` line: comma-separated, each note in parentheses such as `(NEW)`
    cut, backticks dropped."""
    listed = re.sub(r"\s*\([^()]*\)", "", line[len("Files:") :])
    return [item.strip().strip("`").strip() for item in listed.split(",") if item.strip("` ")]


def parse_groups(text: str, report: Report | None, path: str) -> list[Group]:
    groups: list[Group] = []
    has_files: dict[int, bool] = {}
    raw_lines = text.splitlines()
    for number, line in prose_lines(text):
        if line.startswith("## "):
            match = GROUP_RE.match(line)
            if not match:
                if report is not None:
                    report.fail(
                        f"{path}:{number}: a group header is "
                        "'## G<n> <name> | <ids> | risk: low|high | parallel: yes|no'"
                    )
                continue
            ids = [i for i in re.split(r"[,\s]+", match.group(3)) if i]
            group = Group(int(match.group(1)), match.group(2), ids, match.group(4), match.group(5))
            groups.append(group)
            has_files[group.number] = False
        elif line.startswith("Files:") and groups:
            has_files[groups[-1].number] = bool(line[len("Files:") :].strip())
            groups[-1].files += group_files(shown_line(raw_lines, number))  # `code` kept
    if report is not None:
        for index, group in enumerate(groups, 1):
            if group.number != index:
                report.fail(
                    f"{path}: groups are numbered G1, G2, ... in order (found G{group.number})"
                )
                break
        for group in groups:
            if not has_files.get(group.number):
                report.fail(f"{path}: G{group.number} needs a 'Files:' line")
    return groups


# `## Rollback` in requirements.md: how the change is undone after merge (specs/README.md, "Change
# folder"). revert: a revert of the squash is enough; flag: the new behaviour runs only with that
# environment variable on; one-way: what cannot be undone.
ROLLBACK_KINDS = ("revert", "flag", "one-way")
ROLLBACK_FORMS = "revert: <why> | flag: <ENV_NAME> | one-way: <what>"
ROLLBACK_HEADING_RE = re.compile(r"^## Rollback(?:\s|\(|$)")
ROLLBACK_NEEDS = {
    "revert": "its why: why a revert of the squash is enough",
    "flag": "the flag's environment variable, e.g. APP_FLAG_SAVE_CARD",
    "one-way": "what cannot be undone",
}


@dataclass
class Rollback:
    kind: str  # revert | flag | one-way
    value: str  # why a revert is enough, the flag's variable, or what cannot be undone
    line: int

    def __str__(self) -> str:
        return f"{self.kind}: {self.value}"


def rollback_section(text: str) -> tuple[Rollback | None, list[tuple[int, str]], bool]:
    """(the Rollback line, its problems as (line, text), whether requirements.md has the
    section). The section holds exactly one line, `- ` allowed in front; comments and blank
    lines are skipped. A line with an unfilled template placeholder is the placeholder check's."""
    raw_lines = text.splitlines()
    heading = 0
    inside = False
    lines: list[tuple[int, str]] = []
    for number, line in prose_lines(text):
        if HEADING_RE.match(line):
            inside = ROLLBACK_HEADING_RE.match(line.strip()) is not None
            heading = heading or (number if inside else 0)
        elif inside and line.strip():
            lines.append((number, shown_line(raw_lines, number)))
    if not heading:
        return None, [], False
    if len(lines) != 1:
        count = str(len(lines)) if lines else "none"
        problem = f"## Rollback holds exactly one line: {ROLLBACK_FORMS} (found {count})"
        return None, [(heading, problem)], True
    number, written = lines[0]
    if PLACEHOLDER_RE.search(written):
        return None, [], True
    kind, colon, value = written.removeprefix("- ").partition(":")
    kind, value = kind.strip(), value.strip()
    if not colon or kind not in ROLLBACK_KINDS:
        problem = (
            "a Rollback line is 'revert: <why>', 'flag: <ENV_NAME>' or 'one-way: <what>', not "
            f"'{snippet(written)}'"
        )
        return None, [(number, problem)], True
    if not value:
        return None, [(number, f"{kind}: needs {ROLLBACK_NEEDS[kind]}")], True
    if kind == "flag" and not ENV_NAME_RE.match(value):
        problem = f"flag: names an environment variable in capitals, not '{value}'"
        return None, [(number, problem)], True
    return Rollback(kind, value, number), [], True


def change_rollback(root: Path, change: Change, ref: str | None = None) -> Rollback | None:
    """The change's Rollback line, from the working tree, or at ref."""
    req = f"{change.path}/requirements.md"
    text = read_text(root / req) if ref is None else read_blobs(root, ref, [req]).get(req)
    return rollback_section(text or "")[0]


def lint_rollback(
    root: Path,
    rollback: Rollback,
    groups: list[Group],
    scenarios: dict[str, Scenario],
    where: str,
    report: Report,
) -> None:
    """I21 and I22: what each Rollback line needs. revert cannot undo a service change that
    touches trunk; one-way needs a risk: high group to hold the one-way work; flag needs its
    row of kind flag in .env.example and a [flag-off] scenario that pins the old behaviour."""
    if rollback.kind == "revert" and distribution(root) == "service":
        trunk = trunk_at(root)
        for path in (path for group in groups for path in group.files):
            if entry := trunk.entry_for(path):
                report.fail(
                    f"{where}: I21: revert: cannot undo a service change that touches trunk "
                    f"({path}: {entry.why}); say flag: <ENV_NAME> or one-way: <what>"
                )
                break
    elif rollback.kind == "one-way" and not any(group.risk == "high" for group in groups):
        report.fail(
            f"{where}: I21: one-way: needs a risk: high group in plan.md; put the one-way work "
            "there"
        )
    elif rollback.kind == "flag":
        env = rollback.value
        rows = env_contract(read_text(root / ".env.example") or "")[0]
        if not any(row.name == env and row.kind == "flag" for row in rows):
            report.fail(
                f"{where}: I22: flag: {env} needs a row of kind flag in .env.example: "
                f"# {env} | flag | bool | no | 0 | <what it turns on>"
            )
        if not any(scenario.flag_off == env for scenario in scenarios.values()):
            report.fail(
                f"{where}: I22: flag: {env} needs a [flag-off: {env}] scenario that pins the old "
                "behaviour with the flag off"
            )


def lint_change(root: Path, change: Change, scenarios: dict[str, Scenario], report: Report) -> None:
    """Change-folder grammar (specs/README.md, "Change folder"); I13 on Review focus; I17, a
    group whose Files: are trunk is risk: high; I21 and I22 on the Rollback line."""
    folder = root / change.path
    rollback: Rollback | None = None
    groups: list[Group] = []
    for name in ("requirements.md", "plan.md", "validation.md"):
        if not (folder / name).is_file():
            report.fail(f"{change.path}/{name}: missing")
    for name, cap in LINE_CAPS.items():
        text = read_text(folder / name)
        if text is not None and len(text.splitlines()) > cap:
            report.warn(f"{change.path}/{name}: {len(text.splitlines())} lines (cap {cap})")
        for number, line in prose_lines(text or ""):
            if placeholder := PLACEHOLDER_RE.search(line):
                report.fail(
                    f"{change.path}/{name}:{number}: unfilled placeholder {placeholder.group(0)}"
                )

    req_text = read_text(folder / "requirements.md")
    if req_text is not None:
        fields, problem = frontmatter(req_text)
        where = f"{change.path}/requirements.md"
        if problem:
            report.fail(f"{where}: {problem}")
        for key in ("change", "lane", "status", "roadmap", "title"):
            if not fields.get(key):
                report.fail(f"{where}: frontmatter needs '{key}'")
        if fields.get("change") and fields["change"] != change.name:
            report.fail(f"{where}: change is '{fields['change']}', the folder is '{change.name}'")
        if not CHANGE_DIR_RE.match(change.name):
            report.fail(f"{change.path}: folder name must be <date>-<slug>")
        if fields.get("lane") and fields["lane"] != "feat":
            report.fail(f"{where}: lane is '{fields['lane']}'; change folders are feat only")
        if fields.get("status") and fields["status"] not in STATUSES:
            report.fail(f"{where}: status must be draft, approved or done")
        if fields.get("roadmap") and not re.fullmatch(SLUG, fields["roadmap"]):
            report.fail(f"{where}: roadmap must be a slug")
        if fields.get("title") and not TITLE_RE.match(fields["title"]):
            report.fail(
                f"{where}: title must be a conventional commit subject, e.g. 'feat(cli): ...'"
            )
        headings = {line.strip() for _, line in prose_lines(req_text)}
        for section in ("## Why", "## Scope", "## Decisions", "## Context"):
            if section not in headings:
                report.fail(f"{where}: missing section '{section}'")
        rollback, problems, found = rollback_section(req_text)
        missing = f"{where}: I21: missing section '## Rollback' (one line: {ROLLBACK_FORMS})"
        if not found and fields.get("status") in ("approved", "done"):
            report.warn(f"{missing}; a change approved before v3.1 may lack it")
        elif not found:
            report.fail(missing)
        for number, problem in problems:
            report.fail(f"{where}:{number}: I21: {problem}")

    plan_text = read_text(folder / "plan.md")
    if plan_text is not None:
        where = f"{change.path}/plan.md"
        groups = parse_groups(plan_text, report, where)
        if not groups:
            report.fail(f"{where}: no groups (## G1 <name> | <ids> | risk: low | parallel: no)")
        seen: set[str] = set()
        for group in groups:
            if not group.ids:
                report.fail(f"{where}: G{group.number} lists no scenario ids")
            for sid in group.ids:
                if sid not in scenarios:
                    report.fail(f"{where}: G{group.number} names unknown id {sid}")
                elif sid in seen:
                    report.warn(f"{where}: {sid} appears in more than one group")
                seen.add(sid)
        lint_trunk_groups(groups, trunk_at(root), where, report)
    if rollback is not None:
        where = f"{change.path}/requirements.md"
        lint_rollback(root, rollback, groups, scenarios, where, report)

    val_text = read_text(folder / "validation.md")
    if val_text is not None:
        lint_validation(change, val_text, scenarios, report)
        lint_proof_ui(root, change, report)


def lint_proof_ui(root: Path, change: Change, report: Report) -> None:
    """Design C.3: a repo whose runtime dependencies hold a known web or TUI framework has a UI,
    and a change with no screenshot, video or terminal row in ## Proof gets a warning, so the
    human sees the gap before approving."""
    stack = stack_at(root, None)
    if isinstance(stack, str) or any(row.kind in PROOF_VISIBLE for row in change.proof_rows):
        return
    for key, where in sorted(stack.items()):
        kind, _, name = key.rpartition(" ")
        if kind == "runtime dependency" and name in UI_FRAMEWORKS:
            report.warn(
                f"{change.path}/validation.md: the repo has a UI ({name} in {where}), and ## Proof "
                "has no screenshot, video or terminal row: add one for the case whose look or "
                "flow changes"
            )
            return


def lint_trunk_groups(groups: list[Group], trunk: TrunkMap, where: str, report: Report) -> None:
    """I17: a group whose Files: match a trunk entry says risk: high, so compile pauses for a
    human look at its diff."""
    for group in groups:
        if group.risk == "high":
            continue
        for path in group.files:
            if entry := trunk.entry_for(path):
                report.fail(
                    f"{where}: I17: G{group.number} lists {path}, which is trunk ({entry.why}); "
                    "mark it risk: high"
                )


def lint_validation(
    change: Change, text: str, scenarios: dict[str, Scenario], report: Report
) -> None:
    where = f"{change.path}/validation.md"
    section = ""
    rows = 0
    checks = 0
    table_rows = 0
    proof_table = 0
    found: set[str] = set()
    raw_lines = text.splitlines()
    change.proof_rows = []
    for number, line in prose_lines(text):
        stripped = line.strip()
        if stripped.startswith("## "):
            title = stripped[3:]
            section = next(
                (
                    s
                    for s in ("Review focus", "Run it", "Human checks", "Proof")
                    if title.startswith(s)
                ),
                "?",
            )
            found.add(section)
            if section == "?":
                report.warn(f"{where}:{number}: unexpected section '{stripped}'")
            continue
        if section == "Review focus" and stripped.startswith("- "):
            rows += 1
            match = REVIEW_ROW_RE.match(stripped)
            if not match:
                report.fail(
                    f"{where}:{number}: I13: a row is '- <input> -> <id>' or '-> none: <reason>'"
                )
                continue
            target = match.group(2)
            if target.startswith("none:"):
                if not target[len("none:") :].strip():
                    report.fail(f"{where}:{number}: I13: 'none:' needs a reason")
                continue
            written = shown_line(raw_lines, number)  # the input as written: `code` kept
            focus = written[2:].rsplit("->", 1)[0].strip() if "->" in written else match.group(1)
            for sid in (t for t in re.split(r"[,\s]+", target) if t):
                if sid not in scenarios:
                    report.fail(
                        f"{where}:{number}: I13: review focus '{focus}' names unknown id {sid}"
                    )
                else:
                    change.review_ids.append(sid)
        elif section == "Run it" and stripped.startswith("|"):
            table_rows += 1
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if table_rows <= 2 or set(stripped) <= set("|-: "):
                continue  # header and separator
            if len(cells) != 4 or not cells[0]:
                report.fail(
                    f"{where}:{number}: a Run it row is | command | exit | stdout | stderr |"
                )
            elif not re.fullmatch(r"-?\d+", cells[1]):
                report.fail(f"{where}:{number}: Run it exit code must be a number")
        elif section == "Human checks" and stripped.startswith("- "):
            checks += 1
            written = shown_line(raw_lines, number)  # as written: `code` shown, not blanked
            change.human_checks.append(written[2:] if written.startswith("- ") else stripped[2:])
        elif section == "Proof" and stripped.startswith("|"):
            proof_table += 1
            if proof_table > 2 and not set(stripped) <= set("|-: "):
                lint_proof_row(change, raw_lines, number, where, scenarios, report)
    for required in ("Review focus", "Human checks"):
        if required not in found:
            report.fail(f"{where}: missing section '## {required}'")
    if "Review focus" in found and rows == 0:
        report.fail(f"{where}: I13: Review focus is empty (each implied input -> an id, or none)")
    if rows > REVIEW_FOCUS_CAP:
        report.warn(f"{where}: {rows} Review focus rows (cap {REVIEW_FOCUS_CAP})")
    if checks > HUMAN_CHECKS_CAP:
        report.warn(f"{where}: {checks} Human checks (cap {HUMAN_CHECKS_CAP})")
    if len(change.proof_rows) > PROOF_ROWS_CAP:
        report.warn(f"{where}: {len(change.proof_rows)} Proof rows (cap {PROOF_ROWS_CAP})")


def lint_proof_row(
    change: Change,
    raw_lines: list[str],
    number: int,
    where: str,
    scenarios: dict[str, Scenario],
    report: Report,
) -> None:
    """One row of ## Proof (design C.3): | for | kind | shows |. `for` is a scenario ID of this
    change or a G<n> of its plan, the kind one a capture makes, and each case gets one row: the
    kind that shows it best, never every kind."""
    cells = re.split(r"(?<!\\)\|", raw_lines[number - 1].strip().strip("|"))
    values = [cell.strip().replace("\\|", "|") for cell in cells]
    at = f"{where}:{number}"
    if len(values) != 3 or not all(values):
        report.fail(f"{at}: a Proof row is | for | kind | shows |, each cell filled")
        return
    target, kind, shows = values[0].strip("`"), values[1].strip("`"), values[2]
    kinds = ", ".join(PROOF_ROW_KINDS[:-2]) + f", {PROOF_ROW_KINDS[-2]} or run --before"
    if kind in ("test", "confidence"):
        report.fail(
            f"{at}: test proof is automatic and confidence is validate's line; a Proof row's kind "
            f"is one of {kinds}"
        )
        return
    if kind not in PROOF_ROW_KINDS:
        report.fail(f"{at}: a Proof row's kind is one of {kinds}, not '{kind}'")
        return
    group = GROUP_ID_RE.match(target)
    ids = {sid for g in change.groups for sid in g.ids}
    if group and int(group.group(1)) not in {g.number for g in change.groups}:
        report.fail(f"{at}: {target} is not a group of {change.path}/plan.md")
        return
    if not group and target not in scenarios:
        report.fail(f"{at}: the Proof row names unknown id {target}")
        return
    if not group and target not in ids:
        report.fail(f"{at}: {target} is not an ID of this change (the groups of plan.md)")
        return
    if any(row.target == target for row in change.proof_rows):
        report.fail(
            f"{at}: a second Proof row for {target}: one proof per case, in the kind that fits "
            'it (specs/README.md, "Proof")'
        )
        return
    change.proof_rows.append(ProofRow(target, kind, shows))


# ---------------------------------------------------------------- test results


@dataclass
class Node:
    node: str
    ids: list[str]
    outcome: str
    xfail_strict: bool | None  # None: no xfail marker
    xfail_reason: str
    xfail_run: bool  # False: xfail(run=False), the body never runs
    xfail_raises: list[str]  # the exception types xfail(raises=...) names; [] when none
    skip: bool
    crash: str
    body: str | None  # what the test body raised: None = it never ran, "" = nothing
    raised_in: str = ""  # "test": the test's own code raised body (tests/conftest.py _raised_in)


@dataclass
class Results:
    complete: bool
    partial: list[str]
    finished: str
    nodes: dict[str, Node]
    by_id: dict[str, list[Node]]
    collect_errors: list[tuple[str, str]]
    bad_tags: list[tuple[str, str]]
    files: dict[str, str] | None  # the tree the tests ran on (tests/conftest.py tree_files)
    collect_exc: dict[str, str] = field(default_factory=dict)  # collector -> exception type


def raises_names(xfail: object) -> list[str]:
    """The exception type names an xfail marker's raises= accepts (conftest records them)."""
    raises = xfail.get("raises") if isinstance(xfail, dict) else None
    if not isinstance(raises, list):
        return []
    return [str(name) for name in raises if isinstance(name, str)]


def load_results(root: Path) -> Results | str:
    """The last pytest run's .cache/spec-results.json, or why it cannot be used."""
    path = root / RESULTS
    if not path.is_file():
        return f"no test results ({RESULTS}): run `mise run test`"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return f"{RESULTS} is unreadable ({exc}): run `mise run test`"
    if not isinstance(data, dict) or data.get("format") != RESULTS_FORMAT:
        return f"{RESULTS} has an unknown format: run `mise run test`"
    nodes: dict[str, Node] = {}
    raw_nodes = data.get("nodes")
    for name, info in raw_nodes.items() if isinstance(raw_nodes, dict) else []:
        if not isinstance(info, dict):
            continue
        xfail = info.get("xfail")
        body = info.get("body")
        ids = [str(i) for i in info.get("ids", []) if isinstance(i, str)]
        nodes[str(name)] = Node(
            node=str(name),
            ids=ids,
            outcome=str(info.get("outcome", "notrun")),
            xfail_strict=bool(xfail.get("strict")) if isinstance(xfail, dict) else None,
            xfail_reason=str(xfail.get("reason", "")) if isinstance(xfail, dict) else "",
            xfail_run=bool(xfail.get("run", True)) if isinstance(xfail, dict) else True,
            xfail_raises=raises_names(xfail),
            skip=bool(info.get("skip")),
            crash=str(info.get("crash", "")),
            body=body if isinstance(body, str) else None,
            raised_in=str(info.get("raised_in") or ""),
        )
    by_id: dict[str, list[Node]] = {}
    for node in nodes.values():
        for sid in node.ids:
            by_id.setdefault(sid, []).append(node)

    def pairs(key: str, second: str) -> list[tuple[str, str]]:
        raw = data.get(key)
        items = raw if isinstance(raw, list) else []
        return [
            (str(i.get("node", "")), str(i.get(second, ""))) for i in items if isinstance(i, dict)
        ]

    partial = data.get("partial")
    files = data.get("files")
    raw_errors = data.get("collect_errors")
    collect_exc = {
        str(i.get("node", "")): str(i.get("exc", ""))
        for i in (raw_errors if isinstance(raw_errors, list) else [])
        if isinstance(i, dict) and i.get("exc")
    }
    return Results(
        complete=bool(data.get("complete")),
        partial=[str(p) for p in partial] if isinstance(partial, list) else [],
        finished=str(data.get("finished", "")),
        nodes=nodes,
        by_id=by_id,
        collect_errors=pairs("collect_errors", "error"),
        bad_tags=pairs("bad_tags", "problem"),
        files={str(k): str(v) for k, v in files.items()} if isinstance(files, dict) else None,
        collect_exc=collect_exc,
    )


def tree_files(root: Path) -> dict[str, str] | None:
    """path -> blob id of each file git sees outside specs/, proof/ and .cache/, as it is on
    disk now: tracked files and untracked files that are not ignored. None when git cannot tell.
    A tracked file keeps its index blob id only when git compares it with the disk by its full
    stat data: one marked assume-unchanged or skip-worktree (git never looks at it) is hashed
    from the disk, and no fsmonitor, untracked cache or looser stat setting is trusted.
    tests/conftest.py holds the same function and stores its map in the results."""
    index = run_git(root, *FULL_STAT, "ls-files", "-s", "-v", "-z")
    changed = run_git(root, *FULL_STAT, "ls-files", "-z", "-m", "-d", "-o", "--exclude-standard")
    if index.returncode != 0 or changed.returncode != 0:
        return None
    files: dict[str, str] = {}
    unwatched: list[str] = []
    for entry in index.stdout.decode("utf-8", "surrogateescape").split("\0"):
        meta, _, path = entry.partition("\t")
        if not path:
            continue
        tag, _mode, blob = meta.split()[:3]
        files[path] = blob
        if tag != "H":  # h: assume-unchanged, S or s: skip-worktree, M: unmerged
            unwatched.append(path)
    regular: list[str] = []
    listed = changed.stdout.decode("utf-8", "surrogateescape").split("\0")
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
        out = run_git(root, "hash-object", "--stdin-paths", stdin=request)
        hashes = out.stdout.decode().split() if out.returncode == 0 else []
        if len(hashes) != len(regular):
            return None
        files.update(zip(regular, hashes, strict=True))
    return {p: h for p, h in sorted(files.items()) if not p.startswith(NOT_TEST_INPUTS)}


def stale_files(root: Path, results: Results) -> list[str] | None:
    """Files that changed since the test run (outside specs/), [] when none did, and None
    when the results carry no file map to compare."""
    if results.files is None:
        return None
    now = tree_files(root)
    if now is None:
        return None
    return sorted(p for p in set(now) | set(results.files) if now.get(p) != results.files.get(p))


def results_problem(root: Path, results: Results) -> str | None:
    """Why the last run cannot stand for the tree as it is now; None when it can."""
    if not results.complete:
        why = ", ".join(results.partial) or "partial run"
        return f"test results are partial ({why}): run `mise run test` without selection"
    stale = stale_files(root, results)
    if stale is None:
        return f"{RESULTS} names no file state to compare: run `mise run test` in the git repo"
    if stale:
        shown = ", ".join(stale[:3]) + (f" (+{len(stale) - 3} more)" if len(stale) > 3 else "")
        return f"test results are stale ({shown} changed since the run): run `mise run test`"
    return None


def names_id(text: str, sid: str) -> bool:
    """True when text names sid as a whole id: 'cli.help-page' or 'cli.helper' do not name cli.help
    (a trailing '.' is sentence punctuation, so 'fixed by cli.help.' does)."""
    pattern = rf"(?<![\w.-]){re.escape(sid)}(?![\w-]|\.\w)"
    return re.search(pattern, text) is not None


RED_BODIES = ("AssertionError", "DID NOT RAISE")  # an assertion, or pytest.raises that missed
BROAD_RAISES = ("Exception", "BaseException")  # xfail(raises=...) this wide names no crash


def gap_body_hits_gap(node: Node) -> bool:
    """True when an xfailed gap test failed the way a fix turns into an XPASS: on an assertion
    about the behaviour, or on the crash its xfail(raises=...) names (pytest already checked
    the type). Any other error (AttributeError from a typo, RuntimeError, pytest.fail()) keeps
    the test failing after the gap is fixed, so it would never go red."""
    if node.body in RED_BODIES:
        return True
    named = [name for name in node.xfail_raises if name not in BROAD_RAISES]
    return bool(named) and len(named) == len(node.xfail_raises)


def judge(
    scenario: Scenario, nodes: list[Node], roadmap: dict[str, bool]
) -> tuple[list[str], list[str]]:
    """Problems with one scenario's linked tests (I3): (hard, soft).

    Hard problems always fail. Soft ones mean "not proven yet": pending where the branch
    may have pending scenarios, a failure everywhere else.
    """
    hard: list[str] = []
    soft: list[str] = []
    if scenario.gap:
        if scenario.gap not in roadmap:
            hard.append(f"gap slug '{scenario.gap}' is not in {ROADMAP}")
        if not nodes:
            soft.append(
                f'no linked test (a gap needs xfail(strict=True, reason="{scenario.id}: ..."))'
            )
        for node in nodes:
            if not node.xfail_strict or not names_id(node.xfail_reason, scenario.id):
                hard.append(
                    f"{node.node}: a gap test needs "
                    f'@pytest.mark.xfail(strict=True, reason="{scenario.id}: ...")'
                )
            elif not node.xfail_run:
                hard.append(
                    f"{node.node}: xfail(run=False) never runs the test, so fixing the gap "
                    "never turns it red; drop run=False"
                )
            elif node.outcome == "xfailed" and node.body is None:
                hard.append(
                    f"{node.node}: xfailed before its body ran (a fixture or setup failed), so "
                    "fixing the gap never turns it red; the body must hit the gap itself"
                )
            elif node.outcome == "xfailed" and node.body in ("XFailed", "Failed"):
                call = "pytest.xfail()" if node.body == "XFailed" else "pytest.fail()"
                hard.append(
                    f"{node.node}: xfails by calling {call}, so fixing the gap never "
                    "turns it red; assert the behaviour the scenario names instead"
                )
            elif node.outcome == "xfailed" and not gap_body_hits_gap(node):
                hard.append(
                    f"{node.node}: its body raised {node.body or 'nothing'}, not an "
                    "AssertionError, so fixing the gap need not turn it red (a typo fails the "
                    "same way); assert the behaviour the scenario names, or name the crash the "
                    "gap is about with xfail(raises=<its type>)"
                )
            elif node.outcome == "xpassed":
                soft.append(
                    f"{node.node} passes now (strict XPASS): the gap is fixed, so rewrite "
                    f"{scenario.id} as an exact contract without the [gap] tag"
                )
            elif node.outcome != "xfailed":
                soft.append(f"linked gap test {node.outcome} ({node.node})")
        return hard, soft
    if not nodes:
        soft.append("no linked test")
    for node in nodes:
        if node.skip or node.outcome == "skipped":
            soft.append(f"skip on a linked test ({node.node})")
        elif node.xfail_strict is not None or node.outcome in ("xfailed", "xpassed"):
            soft.append(f"xfail on a linked test ({node.node}); only [gap] scenarios may xfail")
        elif node.outcome != "passed":
            detail = f": {node.crash}" if node.crash else ""
            soft.append(f"linked test {node.outcome} ({node.node}{detail})")
    return hard, soft


# ---------------------------------------------------------------- the spec state of a branch


@dataclass
class State:
    ctx: Context
    report: Report
    texts: dict[str, str]
    scenarios: dict[str, Scenario]
    base_scenarios: dict[str, Scenario] | None
    roadmap: dict[str, bool]
    changes: dict[str, Change]
    added: set[str] = field(default_factory=set)
    modified: set[str] = field(default_factory=set)
    removed: set[str] = field(default_factory=set)
    grammar: list[tuple[str, str]] = field(default_factory=list)  # capability file problems

    @property
    def open_change(self) -> Change | None:
        if self.ctx.lane != "feat" or not self.ctx.slug:
            return None
        return find_change(self.changes, self.ctx.slug)


def load_state(ctx: Context) -> State:
    report = Report()
    paths, strays = capability_files(ctx.root)
    for stray in strays:
        report.fail(f"{stray}: capabilities are {CAPS_DIR}/<cap>.md; this file is never read")
    texts = {path: read_text(ctx.root / path) or "" for path in paths}
    scenarios = load_scenarios(texts, report)
    base_scenarios = scenarios_at(ctx.root, ctx.base) if ctx.base else None
    roadmap = roadmap_items(read_text(ctx.root / ROADMAP) or "")
    state = State(ctx, report, texts, scenarios, base_scenarios, roadmap, load_changes(ctx.root))
    state.grammar = list(report.lines)
    if base_scenarios is not None:
        state.added = set(scenarios) - set(base_scenarios)
        state.removed = set(base_scenarios) - set(scenarios)
        state.modified = {
            sid
            for sid in set(scenarios) & set(base_scenarios)
            if scenarios[sid].block != base_scenarios[sid].block
        }
    return state


def may_pend(state: State, strict: bool) -> set[str]:
    """Scenarios allowed to lack a passing test: ADDED/MODIFIED on a spec lane branch (I3)."""
    if strict or state.ctx.on_default or state.ctx.lane not in SPEC_LANES:
        return set()
    return state.added | state.modified


# ---------------------------------------------------------------- check


def check_trace(state: State, results: Results, strict: bool) -> dict[str, str]:
    """I3 and orphan tags. Returns scenario id -> proven | gap | pending | failing."""
    report = state.report
    pendable = may_pend(state, strict)
    verdicts: dict[str, str] = {}
    for sid in sorted(set(results.by_id) - set(state.scenarios)):
        where = ", ".join(n.node for n in results.by_id[sid])
        report.fail(f"{sid}: unknown id, tagged on {where}")
    for sid, scenario in sorted(state.scenarios.items()):
        if scenario.gap and state.roadmap.get(scenario.gap):
            report.warn(f"{sid}: gap slug '{scenario.gap}' is ticked done in {ROADMAP}")
        hard, soft = judge(scenario, results.by_id.get(sid, []), state.roadmap)
        for problem in hard:
            report.fail(f"{sid}: {problem}")
        if soft and sid in pendable:
            kind = "added" if sid in state.added else "modified"
            for problem in soft:
                report.pend(f"{sid}: {problem} ({kind} on {state.ctx.branch})")
            verdicts[sid] = "pending"
        elif soft:
            for problem in soft:
                report.fail(f"{sid}: {problem}")
            verdicts[sid] = "failing"
        elif hard:
            verdicts[sid] = "failing"
        else:
            verdicts[sid] = "gap" if scenario.gap else "proven"
    return verdicts


def check_markers(state: State, strict: bool) -> None:
    """[NEEDS CLARIFICATION: refused on the default branch, in mission.md, in approved changes.

    Once the branch's own change is approved, the whole spec it approved counts: a marker in
    any specs/ file other than another change folder is refused too. Before the first merge
    (G1: the default branch holds no .project.toml yet), a branch's markers are the questions
    the constitution talk left open: each is listed as a warning, and G1's merge (strict)
    refuses while any remain.
    """
    root = state.ctx.root
    folder = root / SPECS
    if not folder.is_dir():
        return
    own = state.open_change
    own_approved = own is not None and own.status in ("approved", "done")
    talk = not strict and not state.ctx.on_default and not adopted(state.ctx)
    for path in sorted(folder.rglob("*.md")):
        rel = path.relative_to(root).as_posix()
        if rel == PROCESS:
            continue  # the process document describes the marker
        # A question parked in an HTML comment is still open: comments are searched too.
        text = read_text(path) or ""
        hits = [
            (n, line) for n, line in prose_lines(text, hide_comments=False) if NEEDS_RE.search(line)
        ]
        if not hits:
            continue
        if talk:
            for number, line in hits:
                question = MARKER_RE.search(line)
                shown = snippet(question.group(0) if question else line)
                state.report.warn(f"{rel}:{number}: open question {shown}; G1's merge refuses it")
            continue
        change = None
        if rel.startswith(CHANGES_DIR + "/"):
            change = state.changes.get(rel.split("/")[2])
        refused = (
            strict
            or state.ctx.on_default
            or rel == MISSION
            or (change is not None and change.status in ("approved", "done"))
            or (own_approved and (change is None or change is own))
        )
        where = f"{rel}:{hits[0][0]}" + (f" (+{len(hits) - 1} more)" if len(hits) > 1 else "")
        if refused:
            report_why = "open question [NEEDS CLARIFICATION ...] must be answered"
            state.report.fail(f"{where}: {report_why}")
        else:
            state.report.warn(
                f"{where}: open question [NEEDS CLARIFICATION ...]; approve refuses it"
            )


def adopted(ctx: Context) -> bool:
    """True once the default branch holds .project.toml: the first merge (G1) landed the
    adoption there. Before it, every branch is the adoption's own."""
    ref = ctx.default_ref
    return ref is not None and git(ctx.root, "cat-file", "-e", f"{ref}:.project.toml") is not None


def mise_tasks(root: Path) -> set[str] | str:
    """Task names (and aliases) in the committed mise config, or why they cannot be read."""
    tasks: set[str] = set()
    for name in MISE_CONFIGS:
        path = root / name
        if not path.is_file():
            continue
        try:
            data = parse_toml(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:  # ValueError: bad TOML, or bytes that are not UTF-8
            return f"{name}: {exc}"
        table = data.get("tasks")
        if not isinstance(table, dict):
            continue
        for task, spec in table.items():
            tasks.add(str(task))
            alias = spec.get("alias") if isinstance(spec, dict) else None
            if isinstance(alias, str):
                tasks.add(alias)
            elif isinstance(alias, list):
                tasks.update(str(a) for a in alias)
    for name in MISE_TASK_DIRS:
        folder = root / name
        if folder.is_dir():
            for path in folder.rglob("*"):
                if path.is_file():
                    rel = path.relative_to(folder).with_suffix("").as_posix()
                    tasks.add(rel.replace("/", ":"))
    return tasks


def check_doc_commands(state: State) -> None:
    """I15: every `mise run X` in AGENTS.md, README.md and specs/README.md is a real task."""
    root = state.ctx.root
    docs = [(name, read_text(root / name)) for name in DOCS_WITH_COMMANDS]
    docs = [(name, text) for name, text in docs if text is not None]
    if not docs:
        return
    tasks = mise_tasks(root)
    if isinstance(tasks, str):
        state.report.fail(f"I15: cannot read the mise tasks: {tasks}")
        return
    for name, text in docs:
        for number, line in enumerate(text.splitlines(), 1):
            for match in MISE_RUN_RE.finditer(line):
                if match.group(1) not in tasks:
                    state.report.fail(
                        f"I15: {name}:{number} names `mise run {match.group(1)}`, "
                        "which is not a mise task"
                    )


def branch_changes(ctx: Context) -> tuple[set[str], set[str]]:
    """Paths changed on this branch: (committed since the merge-base, uncommitted)."""
    committed: set[str] = set()
    if ctx.base and ctx.head:
        committed.update(
            git_lines(ctx.root, "diff", "--name-only", "--no-renames", ctx.base, ctx.head)
        )
    uncommitted: set[str] = set()
    if ctx.head:
        uncommitted.update(git_lines(ctx.root, "diff", "--name-only", "--no-renames", "HEAD"))
        uncommitted.update(
            git_lines(ctx.root, "diff", "--name-only", "--no-renames", "--cached", "HEAD")
        )
    uncommitted.update(git_lines(ctx.root, "ls-files", "--others", "--exclude-standard"))
    return committed, uncommitted


def roadmap_close_problem(before: str, after: str, slug: str) -> str | None:
    """What is wrong with a close commit's roadmap edit: merge only ticks the change's own item
    in place, or adds it as `- [x] <slug>: <title> (unplanned)`; every other line stays."""

    def own(line: str) -> bool:
        match = ROADMAP_ITEM_RE.match(line.strip())
        return match is not None and match.group(2) == slug

    old, new = before.splitlines(), after.splitlines()
    if any(own(line) for line in old):
        ticked = [line.replace("- [ ]", "- [x]", 1) if own(line) else line for line in old]
        if new == ticked and ticked != old:
            return None
        if [line for line in new if not own(line)] != [line for line in old if not own(line)]:
            return f"it changes {ROADMAP} beyond the item '{slug}'"
        return f"it may only tick the item '{slug}' in {ROADMAP}, where it stands"
    added = [line for line in new if own(line)]
    if [line for line in new if not own(line)] != old:
        return f"it changes {ROADMAP} beyond the item '{slug}'"
    if len(added) != 1 or not re.fullmatch(
        rf"- \[x\] {re.escape(slug)}: .+ \(unplanned\)", added[0].strip()
    ):
        return f"a new roadmap item is one line: '- [x] {slug}: <title> (unplanned)'"
    return None


def launch_target(slug: str | None) -> str | None:
    """The roadmap item a branch slug launches: <slug> for launch-<slug>, else None."""
    if not slug or not slug.startswith(LAUNCH_PREFIX):
        return None
    target = slug.removeprefix(LAUNCH_PREFIX)
    return target if re.fullmatch(SLUG, target) else None


def launch_item_problem(text: str, slug: str) -> tuple[int, str | None]:
    """(line number, problem) of the roadmap item slug as a launch finds it: it must be there,
    ticked, and not launched yet. The number is 0 when the item is missing."""
    own = [entry for entry in roadmap_entries(text) if entry[1] == slug]
    if not own:
        return 0, (
            f"{ROADMAP} has no item '{slug}' to mark launched (a slug that starts with "
            f"{LAUNCH_PREFIX} launches the item named by the rest)"
        )
    number, _, ticked, title, _ = own[0]
    if not ticked:
        return number, f"'{slug}' is not ticked yet: its change merges first, then its launch"
    if LAUNCHED_MARK in title:
        return number, f"'{slug}' is launched already"
    return number, None


def launch_close_problem(root: Path, sha: str, touched: set[str], slug: str) -> str | None:
    """What is wrong with the roadmap edit of the close commit sha on a launch-<slug> branch."""
    if ROADMAP not in touched:
        return f"it leaves {ROADMAP} alone; merge marks '{slug}' launched"
    before = read_blobs(root, f"{sha}^", [ROADMAP]).get(ROADMAP, "")
    after = read_blobs(root, sha, [ROADMAP]).get(ROADMAP, "")
    return roadmap_launch_problem(before, after, slug)


def roadmap_launch_problem(before: str, after: str, slug: str) -> str | None:
    """What is wrong with the roadmap edit of a launch-<slug> branch's close commit: merge
    appends ` (launched <date>)` to the ticked item slug where it stands; every other line
    stays (design D.2)."""
    number, problem = launch_item_problem(before, slug)
    if problem:
        return problem
    old, new = before.splitlines(), after.splitlines()
    rest = [line for index, line in enumerate(old) if index != number - 1]
    if len(new) != len(old) or [ln for i, ln in enumerate(new) if i != number - 1] != rest:
        return f"it changes {ROADMAP} beyond the item '{slug}'"
    line, marked = old[number - 1].rstrip(), new[number - 1]
    if marked == old[number - 1]:
        return f"it leaves the item '{slug}' as it was; merge marks the item '{slug}' launched"
    if not (marked.startswith(line) and LAUNCHED_RE.fullmatch(marked[len(line) :])):
        return f"it may only append ' (launched <date>)' to the item '{slug}' in {ROADMAP}"
    return None


def changelog_entry(title: str) -> tuple[str, str] | None:
    """(group, line) that git-cliff writes for a conventional title under the [tool.git-cliff]
    config project-init renders, or None when the title's type gets no line."""
    match = TITLE_PARTS_RE.match(title.strip())
    if not match:
        return None
    kind, scope, bang, text = match.groups()
    group = BREAKING_GROUP if bang else CLIFF_GROUPS.get(kind)
    if group is None:
        return None
    return group, f"- {text.strip()}" + (f" ({scope})" if scope else "")


def changelog_header(root: Path, ref: str) -> list[str]:
    """The [tool.git-cliff.changelog] header at ref: what merge writes above the entries when
    CHANGELOG.md does not exist yet."""
    text = read_blobs(root, ref, ["pyproject.toml"]).get("pyproject.toml", "")
    try:
        node: object = parse_toml(text)
    except ValueError:
        return []
    for key in ("tool", "git-cliff", "changelog", "header"):
        node = node.get(key) if isinstance(node, dict) else None
    return node.splitlines() if isinstance(node, str) else []


def inserted_lines(old: list[str], new: list[str]) -> list[int] | None:
    """Indexes of the lines new adds to old when new only adds lines; None when it drops or
    rewrites one (old is then not a subsequence of new)."""
    added: list[int] = []
    pos = 0
    for index, line in enumerate(new):
        if pos < len(old) and line == old[pos]:
            pos += 1
        else:
            added.append(index)
    return added if pos == len(old) else None


def changelog_close_problem(
    old: list[str], new: list[str], groups: tuple[str, ...], entry: str | None
) -> str | None:
    """What is wrong with a close commit's CHANGELOG.md edit. Merge regenerates the file with
    git-cliff, which keeps every line and adds one `- <entry>` under `## [Unreleased]` and a
    `### <group>` of the lane, plus those two headings and blank lines when they are new.
    entry is the exact line when the title is known (feat/), else None."""
    added = inserted_lines(old, new)
    if added is None:
        return f"it removes or rewrites lines of {CHANGELOG}; merge only adds its entry"
    entries = [index for index in added if new[index].startswith("- ")]
    if len(entries) != 1:
        return f"it adds {len(entries)} entries to {CHANGELOG}; merge adds exactly one"
    at = entries[0]
    group, section = None, None
    for line in reversed(new[:at]):
        if line.startswith("### ") and group is None:
            group = line[4:].strip()
        elif line.startswith("## "):
            section = line.strip()
            break
    if section != UNRELEASED:
        return f"its entry '{new[at]}' is not under '{UNRELEASED}'"
    if group not in groups:
        where = " or ".join(f"'### {name}'" for name in groups)
        return f"its entry '{new[at]}' is not under {where}"
    if entry is not None and new[at] != entry:
        return f"its entry is '{new[at]}', and merge writes '{entry}' for the change title"
    headings = [new[index] for index in added if index != at and new[index].strip()]
    allowed = (UNRELEASED, f"### {group}")
    extra = [line for line in headings if line not in allowed]
    extra += [line for line in allowed if headings.count(line) > 1]
    if extra:
        return f"it adds '{extra[0]}' to {CHANGELOG}; merge adds only its entry and its headings"
    return None


def launch_items_added(root: Path, sha: str, change: Change) -> list[str]:
    """The launch backlog item a flag: change's close commit adds, `<date>-launch-<slug>.md`
    (at most one), or none when the change's Rollback line at sha is not a flag."""
    rollback = change_rollback(root, change, sha)
    if rollback is None or rollback.kind != "flag":
        return []
    name = re.compile(
        rf"{BACKLOG_DIR}/\d{{4}}-\d{{2}}-\d{{2}}-launch-{re.escape(change.roadmap)}\.md"
    )
    added = ["diff", "--name-only", "--no-renames", "--diff-filter=A", f"{sha}^", sha]
    return [path for path in git_lines(root, *added, "--", BACKLOG_DIR) if name.fullmatch(path)][:1]


def close_commit_problem(state: State, sha: str, tip: str | None) -> str | None:
    """Why a commit carrying the Merged-By trailer is not merge's close commit (specs/README.md,
    "Definition of Done", step 7), or None when it is one. The close commit is the branch's
    last commit; it touches only CHANGELOG.md and, on feat/, the roadmap and the change's
    requirements.md; it moves the change from approved to done, ticks only its own roadmap
    item, and adds the one CHANGELOG line merge writes (changelog_close_problem). A flag:
    change's close commit also adds its launch backlog item, and no other new file. On feat/,
    chg/ and fix/ it may write the ## Tests section of the branch's proof README.md, and
    nothing else there. On a launch-<slug> branch, whatever its lane, it marks the roadmap item
    <slug> launched and ticks none. So a hand-written trailer can do nothing that merge would
    not do."""
    ctx = state.ctx
    if sha != tip:
        return "commits follow it, and merge's close commit is the last one on the branch"
    touched = set(git_lines(ctx.root, "diff", "--name-only", "--no-renames", f"{sha}^", sha))
    change = state.open_change
    target = launch_target(ctx.slug)
    allowed = {CHANGELOG, *([ROADMAP] if target else [])}
    if ctx.lane == "feat" and change is not None:
        allowed.update({ROADMAP, f"{change.path}/requirements.md"})
        allowed.update(launch_items_added(ctx.root, sha, change))
    name = proof_name(ctx, change) if ctx.lane in SPEC_LANES_NEED_SPEC else None
    proof_readme = f"{PROOF_DIR}/{name}/{PROOF_INDEX}" if name else ""
    if proof_readme:
        allowed.add(proof_readme)
    if extra := sorted(touched - allowed):
        return f"it also changes {', '.join(extra)}"
    why = proof_close_problem(ctx.root, sha, proof_readme, name) if name else None
    if why and proof_readme in touched:
        return why
    if target and (why := launch_close_problem(ctx.root, sha, touched, target)):
        return why
    groups = LANE_CHANGELOG_GROUPS.get(ctx.lane or "", ())
    title = ""
    entry: str | None = None
    if ctx.lane == "feat":
        if change is None:
            return f"{ctx.branch} has no change folder to close"
        req = f"{change.path}/requirements.md"
        before = read_blobs(ctx.root, f"{sha}^", [req, ROADMAP])
        after = read_blobs(ctx.root, sha, [req, ROADMAP])
        moves = (
            frontmatter(before.get(req, ""))[0].get("status"),
            frontmatter(after.get(req, ""))[0].get("status"),
        )
        if moves != ("approved", "done"):
            return f"it does not move {change.path} from approved to done"
        slug = change.roadmap
        if target is None and ROADMAP not in touched:
            return f"it leaves {ROADMAP} alone; merge ticks '{slug}' (or adds it, unplanned)"
        if target is None and (
            problem := roadmap_close_problem(before.get(ROADMAP, ""), after.get(ROADMAP, ""), slug)
        ):
            return problem
        title = frontmatter(after.get(req, ""))[0].get("title", "")
        line = changelog_entry(title)
        groups, entry = ((line[0],), line[1]) if line else ((), None)
        if line and CHANGELOG not in touched:
            return f"it adds no {CHANGELOG} line; merge adds '{line[1]}' under '### {line[0]}'"
    if CHANGELOG not in touched:
        return None
    if not groups:
        why = f"the title '{title}'" if ctx.lane == "feat" else f"the {ctx.lane}/ lane"
        return f"merge writes no {CHANGELOG} line for {why}"
    before = read_blobs(ctx.root, f"{sha}^", [CHANGELOG])
    old = before[CHANGELOG].splitlines() if CHANGELOG in before else changelog_header(ctx.root, sha)
    new = read_blobs(ctx.root, sha, [CHANGELOG]).get(CHANGELOG, "").splitlines()
    return changelog_close_problem(old, new, groups, entry)


def tool_file_commits(state: State, path: str) -> list[str]:
    """Why each commit on this branch that changes a file only merge writes (the roadmap
    outside plan/, CHANGELOG.md) is refused: no Merged-By trailer, or not the close commit."""
    ctx = state.ctx
    if not ctx.base or not ctx.head:
        return []
    span = f"{ctx.base}..{ctx.head}"
    shas = git_lines(ctx.root, "rev-list", "--no-merges", "--full-history", span, "--", path)
    tip = next(iter(git_lines(ctx.root, "rev-list", "--no-merges", "-n", "1", span)), None)
    problems = []
    for sha in shas:
        trailers = "\n".join(commit_trailers(ctx.root, "-1", sha))
        if TOOL_TRAILER[1] not in trailer_values(trailers, TOOL_TRAILER[0]):
            problems.append(
                f"commit {sha[:10]} changes {path} on {ctx.branch}; only merge writes it"
            )
        elif why := close_commit_problem(state, sha, tip):
            problems.append(
                f"commit {sha[:10]} changes {path} on {ctx.branch} and carries "
                f"'{': '.join(TOOL_TRAILER)}', but it is not merge's close commit: {why}"
            )
    return problems


@dataclass
class HarnessEdit:
    """A commit on the branch that changes a test file which existed at the merge-base."""

    sha: str
    reason: str  # its Test-Harness: reason; "" when it carries none
    files: list[str]


def base_test_files(ctx: Context) -> set[str]:
    """The test code at the merge-base (in_tests: a test_*.py beside the code too): the
    "existing test files" of I7."""
    if not ctx.base:
        return set()
    src, tests = project_paths(ctx.root)
    listed = git_lines(ctx.root, "ls-tree", "-r", "--name-only", ctx.base, "--", *tests, *src)
    return {path for path in listed if in_tests(path, src, tests)}


def edited_test_files(ctx: Context) -> list[HarnessEdit]:
    """I7: the branch's commits that change (edit, delete or rename) an existing test file,
    oldest first, each with its Test-Harness: reason. Adding a test file is not an edit. Merge
    commits are left out: they bring the default branch in, not this branch's work."""
    existing = base_test_files(ctx)
    if not existing or not ctx.base or not ctx.head:
        return []
    edits: list[HarnessEdit] = []
    span = f"{ctx.base}..{ctx.head}"
    for sha in reversed(git_lines(ctx.root, "rev-list", "--no-merges", span)):
        touched = git_lines(
            ctx.root, "diff-tree", "--no-commit-id", "--name-only", "-r", "--no-renames", sha
        )
        files = sorted(p for p in touched if p in existing)
        if files:
            trailers = "\n".join(commit_trailers(ctx.root, "-1", sha))
            reason = next((v for v in trailer_values(trailers, "Test-Harness") if v), "")
            edits.append(HarnessEdit(sha, reason, files))
    return edits


def check_test_harness(state: State, uncommitted: set[str]) -> None:
    """I7: on chore/ and refactor/, existing test files stay unedited, except in commits that
    carry `Test-Harness: <reason>`; those are noted for the human at merge."""
    ctx = state.ctx
    if ctx.lane not in ("chore", "refactor"):
        return
    for edit in edited_test_files(ctx):
        files = ", ".join(edit.files)
        if edit.reason:
            state.report.note(
                f"I7: {edit.sha[:10]} edits {files} (Test-Harness: {edit.reason}); "
                "merge shows this diff to a human"
            )
        else:
            state.report.fail(
                f"I7: commit {edit.sha[:10]} edits {files} on {ctx.branch}; {ctx.lane}/ leaves "
                "existing tests unedited. Add new tests freely; a harness-only edit (fixtures, "
                "imports, mocks) goes in a commit with a 'Test-Harness: <reason>' trailer"
            )
    for path in sorted(uncommitted & base_test_files(ctx)):
        state.report.warn(
            f"I7: {path} is edited and not committed; on {ctx.lane}/ its commit needs a "
            "'Test-Harness: <reason>' trailer"
        )


def requirement_name(requirement: str) -> str | None:
    """The normalized project name of a PEP 508 requirement ('Pydantic_Settings>=2' ->
    'pydantic-settings')."""
    match = REQ_NAME_RE.match(requirement)
    return re.sub(r"[-_.]+", "-", match.group(1)).lower() if match else None


def declared_stack(pyproject: str | None, mise_configs: dict[str, str]) -> dict[str, str] | str:
    """'<kind> <name>' -> the file declaring it, for every runtime dependency and tool, or why
    the files cannot be read. Kinds: runtime dependency ([project] dependencies and extras),
    dev tool ([dependency-groups], [tool.uv] dev-dependencies), mise tool ([tools]). Versions
    are left out: I11 is about adding, removing and swapping, not bumping."""
    found: dict[str, str] = {}

    def add(kind: str, requirements: object, where: str) -> None:
        for requirement in requirements if isinstance(requirements, list) else []:
            if isinstance(requirement, str) and (name := requirement_name(requirement)):
                found.setdefault(f"{kind} {name}", where)

    if pyproject is not None:
        try:
            data = parse_toml(pyproject)
        except ValueError as exc:
            return f"pyproject.toml: {exc}"
        project = data.get("project")
        project = project if isinstance(project, dict) else {}
        add("runtime dependency", project.get("dependencies"), "pyproject.toml")
        extras = project.get("optional-dependencies")
        for requirements in extras.values() if isinstance(extras, dict) else []:
            add("runtime dependency", requirements, "pyproject.toml")
        groups = data.get("dependency-groups")
        for requirements in groups.values() if isinstance(groups, dict) else []:
            add("dev tool", requirements, "pyproject.toml")
        tool = data.get("tool")
        uv = tool.get("uv") if isinstance(tool, dict) else None
        if isinstance(uv, dict):
            add("dev tool", uv.get("dev-dependencies"), "pyproject.toml")
    for name, text in mise_configs.items():
        try:
            tools = parse_toml(text).get("tools")
        except ValueError as exc:
            return f"{name}: {exc}"
        for key in tools if isinstance(tools, dict) else {}:
            found.setdefault(f"mise tool {key}", name)
    return found


def stack_at(root: Path, ref: str | None) -> dict[str, str] | str:
    """declared_stack() of the files at ref, or of the working tree when ref is None."""
    names = ["pyproject.toml", *MISE_CONFIGS]
    if ref is None:
        texts = {name: text for name in names if (text := read_text(root / name)) is not None}
    else:
        texts = read_blobs(root, ref, names)
    pyproject = texts.pop("pyproject.toml", None)
    return declared_stack(pyproject, texts)


def check_tech_stack(state: State, changed: set[str]) -> None:
    """I11: a runtime dependency or tool added, removed or swapped on this branch means
    specs/tech-stack.md changed on it too."""
    ctx = state.ctx
    if ctx.on_default or not ctx.base or TECH_STACK in changed:
        return
    before, now = stack_at(ctx.root, ctx.base), stack_at(ctx.root, None)
    if isinstance(before, str) or isinstance(now, str):
        problem = before if isinstance(before, str) else now
        state.report.warn(f"I11: cannot compare the declared dependencies: {problem}")
        return
    for key in sorted(set(now) - set(before)):
        state.report.fail(
            f"I11: {key} added ({now[key]}), but {TECH_STACK} is unchanged on {ctx.branch}; "
            "record it there"
        )
    for key in sorted(set(before) - set(now)):
        state.report.fail(
            f"I11: {key} removed ({before[key]}), but {TECH_STACK} is unchanged on "
            f"{ctx.branch}; record it there"
        )


def check_lane_rules(state: State) -> None:
    """I1, I2, I5 on the branch diff (pre-commit enforces them on each staged commit), I7 and
    I11, and the lane table (specs/README.md): chore/ and refactor/ never change capabilities,
    neither a scenario nor any other line (a requirement's SHALL sentence, a heading)."""
    ctx = state.ctx
    report = state.report
    if ctx.on_default or ctx.branch is None:
        committed, uncommitted = set(), branch_changes(ctx)[1]
    else:
        committed, uncommitted = branch_changes(ctx)
    changed = committed | uncommitted
    lane = ctx.lane
    if lane in LANES and lane not in SPEC_LANES:
        never = f"{lane}/ never changes capabilities (a behaviour change is chg/, fix/ or feat/)"
        named: set[str] = set()  # capability files a scenario line below already points at
        for kind, ids, where in (
            ("added", state.added, state.scenarios),
            ("modified", state.modified, state.scenarios),
            ("removed", state.removed, state.base_scenarios or {}),
        ):
            for sid in sorted(ids):
                report.fail(f"{sid}: scenario {kind} on {ctx.branch}; {never}")
                if sid in where:
                    named.add(where[sid].path)
        for path in sorted(changed - named):
            if path.startswith(CAPS_DIR + "/"):
                report.fail(f"{path}: changed on {ctx.branch}; {never}")
    if not ctx.on_default and ctx.branch is not None:
        if MISSION in changed and lane != "plan":
            report.fail(
                f"I1: {MISSION} changed on {ctx.branch}; the mission changes only on plan/ branches"
            )
        tool_merge = bool(os.environ.get("PROJECT_MERGE"))
        guarded = [(ROADMAP, "I1", lane == "plan")]
        guarded.append((CHANGELOG, "I2", lane == "release" or ctx.branch == INIT_BRANCH))
        for path, rule, allowed in guarded:
            if allowed or path not in changed:
                continue
            if path in uncommitted and not tool_merge:
                report.fail(
                    f"{rule}: {path} is edited on {ctx.branch}; "
                    "only `mise run merge` writes it here"
                )
            if path in committed:
                for problem in tool_file_commits(state, path):
                    report.fail(f"{rule}: {problem}")
        check_test_harness(state, uncommitted)
        check_tech_stack(state, changed)
    ref = ctx.base or ctx.head
    folders = sorted(
        {p.split("/")[2] for p in changed if p.startswith(CHANGES_DIR + "/") and p.count("/") >= 3}
    )
    if ref and folders:
        paths = [f"{CHANGES_DIR}/{name}/requirements.md" for name in folders]
        for path, text in read_blobs(ctx.root, ref, paths).items():
            if frontmatter(text)[0].get("status") == "done":
                report.fail(
                    f"I5: {PurePosixPath(path).parent} is done and frozen; it was edited here"
                )


def approve_lint(state: State, change: Change) -> Report:
    """What approve checks: the change folder, scenario grammar, and no open question anywhere
    in specs/ (other live change folders are left out)."""
    lint = Report(list(state.grammar))
    for problem in trunk_at(state.ctx.root).problems:
        lint.fail(problem)
    lint_change(state.ctx.root, change, state.scenarios, lint)
    markers = Report()
    for problem in encoding_problems(state.ctx.root):
        if problem.startswith(SPECS + "/"):
            markers.fail(problem)
    check_markers(replace(state, report=markers), strict=True)
    for level, text in markers.lines:
        if not text.startswith(CHANGES_DIR + "/") or text.startswith(change.path + "/"):
            lint.lines.append((level, text))
    return lint


def plural(count: int, word: str) -> str:
    return f"{count} {word}" + ("" if count == 1 else "s")


def check_caps(state: State) -> None:
    root = state.ctx.root
    for path, text in state.texts.items():
        if len(text.splitlines()) > CAPABILITY_CAP:
            state.report.warn(
                f"{path}: {len(text.splitlines())} lines (cap {CAPABILITY_CAP}); split it"
            )
    agents = read_text(root / "AGENTS.md")
    if agents is not None and len(agents.splitlines()) > AGENTS_CAP:
        state.report.warn(f"AGENTS.md: {len(agents.splitlines())} lines (cap {AGENTS_CAP})")
    memory = root / "project_memory" / "README.md"
    if memory.is_file() and memory.stat().st_size > MEMORY_README_CAP_BYTES:
        state.report.warn(f"project_memory/README.md: {memory.stat().st_size} bytes (cap 1 KB)")


def check_flag_tags(state: State) -> None:
    """I22: each [flag-off: <ENV>] tag names a row of kind flag in .env.example."""
    tagged = sorted(
        (s for s in state.scenarios.values() if s.flag_off), key=lambda s: (s.path, s.line)
    )
    if not tagged:
        return
    rows = env_contract(read_text(state.ctx.root / ".env.example") or "")[0]
    flags = {row.name for row in rows if row.kind == "flag"}
    for scenario in tagged:
        if scenario.flag_off not in flags:
            env = scenario.flag_off
            state.report.fail(
                f"{scenario.path}:{scenario.line}: I22: [flag-off: {env}] names no flag row in "
                f".env.example; add '# {env} | flag | bool | no | 0 | <what it turns on>'"
            )


def check_changes(state: State, strict: bool) -> None:
    """Lint every live change folder; the branch's own feat change must exist."""
    for change in state.changes.values():
        if change.status == "done":
            continue
        if state.ctx.on_default:
            state.report.warn(
                f"{change.path}: status {change.status or '?'} on {state.ctx.default}"
            )
        lint_change(state.ctx.root, change, state.scenarios, state.report)
    if state.ctx.lane == "feat" and state.open_change is None:
        state.report.fail(
            f"{state.ctx.branch}: the feat lane needs specs/changes/<date>-{state.ctx.slug}/"
        )
    change = state.open_change
    if change is not None and not strict:
        grouped = {sid for group in change.groups for sid in group.ids}
        for sid in sorted((state.added | state.modified) - grouped):
            state.report.warn(
                f"{sid}: changed on this branch but in no group of {change.path}/plan.md"
            )


def summarize(state: State, verdicts: dict[str, str] | None) -> str:
    report = state.report
    parts = [f"{len(state.scenarios)} scenarios"]
    if verdicts is not None:
        counts = {
            k: sum(1 for v in verdicts.values() if v == k) for k in ("proven", "gap", "pending")
        }
        parts.append(
            f"{counts['proven']} proven, {counts['gap']} gaps, {counts['pending']} pending"
        )
    if state.base_scenarios is not None and not state.ctx.on_default:
        parts.append(
            f"{len(state.added)} added, {len(state.modified)} modified, "
            f"{len(state.removed)} removed since {state.ctx.default}"
        )
    verdict = "FAIL" if report.errors else "ok"
    tally = f"{plural(report.errors, 'error')}, {plural(report.count('warn'), 'warning')}"
    return f"spec-check: {verdict} ({tally}); " + "; ".join(parts)


def cmd_check(ctx: Context, args: argparse.Namespace) -> int:
    if not (ctx.root / SPECS).is_dir():
        print(f"FAIL  no {SPECS}/ folder: this repo has no specs yet (run /project-init)")
        return 1
    strict = bool(args.strict)
    if args.change:
        state = load_state(ctx)
        change = find_change(state.changes, args.change)
        if change is None:
            print(f"FAIL  no change folder for '{args.change}' under {CHANGES_DIR}/")
            return 1
        lint = approve_lint(state, change)
        lint.print()
        errors = lint.errors
        print(f"change {change.name}: {'FAIL' if errors else 'ok'} ({plural(errors, 'error')})")
        return 1 if errors else 0
    state, verdicts = run_check(ctx, strict)
    state.report.print()
    print(summarize(state, verdicts))
    return 1 if state.report.errors else 0


# ---------------------------------------------------------------- status


def local_time(stamp: str) -> str:
    try:
        return datetime.fromisoformat(stamp).astimezone().strftime("%H:%M")
    except ValueError:
        return "?"


def next_group(change: Change, verdicts: dict[str, str]) -> Group | None:
    for group in change.groups:
        if any(verdicts.get(sid) not in ("proven",) for sid in group.ids):
            return group
    return None


def cmd_status(ctx: Context, args: argparse.Namespace) -> int:
    if args.merge:
        return cmd_status_merge(ctx)
    if args.audit:
        return cmd_status_audit(ctx)
    if not (ctx.root / SPECS).is_dir():
        print(f"[{ctx.name}] {ctx.branch or 'detached'} | no {SPECS}/ folder (run /project-init)")
        return 0
    state = load_state(ctx)
    if args.change:
        return print_change(state)
    change = state.open_change
    head = [f"[{ctx.name}] {ctx.branch or 'detached HEAD'}"]
    busy = open_changes(ctx) if ctx.on_default else []  # what `change` would refuse on (I8)
    if ctx.on_default:
        head.append(f"change open on {', '.join(busy)}" if busy else "no open change")
    elif ctx.lane:
        head.append(f"lane {ctx.lane}")
        head.append(f"change {change.name} ({change.status})" if change else "no change folder")
    else:
        head.append("not a lane branch (feat/ chg/ fix/ chore/ refactor/ plan/)")
    print(" | ".join(head))
    older = [  # the ones that would block `change` under the plain rule; merged ones never did
        branch
        for branch in (pre_adoption(ctx) if ctx.on_default else [])
        if not is_ancestor(ctx.root, f"refs/heads/{branch}", ctx.default_ref or "HEAD")
    ]
    if older:
        print(
            f"from before adoption: {', '.join(older)}: not changes, so I8 skips them. Delete "
            f"one, or `git merge {ctx.default}` into it to go on with it as a change"
        )

    results = load_results(ctx.root)
    verdicts: dict[str, str] = {}
    if isinstance(results, Results):
        verdicts = check_trace(state, results, strict=False)
        counts = {
            k: sum(1 for v in verdicts.values() if v == k)
            for k in ("proven", "gap", "pending", "failing")
        }
        when = local_time(results.finished)
        if not results.complete:
            when += ", partial"
        elif stale_files(ctx.root, results) != []:
            when += ", stale"
        line = f"scenarios: {len(state.scenarios)}"
        if not ctx.on_default and state.base_scenarios is not None:
            diff = (len(state.added), len(state.modified), len(state.removed))
            line += " ({} added, {} modified, {} removed)".format(*diff)
        line += (
            f" | proven {counts['proven']}, gaps {counts['gap']}, pending {counts['pending']}, "
            f"failing {counts['failing']} (results {when})"
        )
        print(line)
        if counts["failing"]:
            print("failing: details with `mise run spec-check`")
    else:
        print(f"scenarios: {len(state.scenarios)} | {results}")

    if ctx.lane and ctx.default_ref and ctx.head:
        behind = run_git(
            ctx.root, "merge-base", "--is-ancestor", ctx.default_ref, "HEAD"
        ).returncode
        if behind == 1:
            print(f"{ctx.default} moved: run git merge {ctx.default}")

    dirty = git_lines(ctx.root, "status", "--porcelain")
    if dirty:
        print(f"dirty: {len(dirty)} {'file' if len(dirty) == 1 else 'files'}")

    if change is not None:
        print_change_state(state, change, verdicts)
    elif busy:
        print(
            f"next: finish {busy[0]} (`git switch {busy[0]}`, or its worktree); one change at a "
            "time (I8)"
        )
    elif ctx.on_default:
        pending = [slug for slug, done in state.roadmap.items() if not done]
        if pending:
            print(f'next roadmap item: {pending[0]} (start it: /sdd "{pending[0]}")')
        for line in launch_lines(unlaunched_items(ctx.root, state.changes)):
            print(line)
        backlog = open_backlog(ctx.root)
        if len(backlog) >= 5:
            print(f"backlog: {len(backlog)} open items; time to replan (/sdd replan)")
        merged = features_since_replan(ctx.root, ctx.default_ref or "HEAD")
        if merged >= 3:
            print(f"replan: {merged} features merged since the last replan (/sdd replan)")
    return 0


LAUNCHES_SHOWN = 4  # status lists at most this many items not launched, below one line


def unlaunched_items(root: Path, changes: dict[str, Change]) -> list[tuple[str, list[str]]]:
    """(slug, live flags) of each ticked roadmap item without the launched mark, in roadmap
    order (design D.2). A flag row of .env.example is live for an item when a change of the item
    names it in its Rollback line, or when its notes name the item or one of its change folders
    (`(change <date>-<slug>)`)."""
    rows = env_contract(read_text(root / ".env.example") or "")[0]
    flags = [row for row in rows if row.kind == "flag"]
    items = []
    for _, slug, ticked, title, _ in roadmap_entries(read_text(root / ROADMAP) or ""):
        if not ticked or LAUNCHED_MARK in title:
            continue
        own = [change for change in changes.values() if change.roadmap == slug]
        rollbacks = [change_rollback(root, change) for change in own]
        rolled = {r.value for r in rollbacks if r is not None and r.kind == "flag"}
        names = {slug, *(change.name for change in own)}
        live = [row.name for row in flags if row.name in rolled or names_any(row.notes, names)]
        items.append((slug, live))
    return items


def names_any(notes: str, names: set[str]) -> bool:
    """Whether notes hold one of names as a whole word; `<date>-<slug>` also names <slug>."""
    words = re.findall(r"[a-z0-9][a-z0-9-]*[a-z0-9]|[a-z0-9]", notes.lower())
    return any(word in names or DATE_PREFIX_RE.sub("", word) in names for word in words)


def launch_lines(items: list[tuple[str, list[str]]]) -> list[str]:
    """status's launch block: one line with the count and the next `/sdd launch`, then the
    items with a live flag first, at most LAUNCHES_SHOWN. Nothing when every item is launched."""
    if not items:
        return []
    ordered = sorted(items, key=lambda item: not item[1])  # stable: roadmap order within each
    count = len(ordered)
    what = "item is" if count == 1 else "items are"
    shown = f", the first {LAUNCHES_SHOWN} below" if count > LAUNCHES_SHOWN else ""
    head = f"launch: {count} merged roadmap {what} not launched yet{shown}"
    lines = [f"{head} (next: /sdd launch {ordered[0][0]})"]
    for slug, live in ordered[:LAUNCHES_SHOWN]:
        flag = f" ({'flag' if len(live) == 1 else 'flags'} {', '.join(live)})" if live else ""
        lines.append(f"  {slug}{flag}")
    return lines


def open_backlog(root: Path) -> list[str]:
    folder = root / SPECS / "backlog"
    if not folder.is_dir():
        return []
    items = []
    for path in sorted(folder.glob("*.md")):
        if frontmatter(read_text(path) or "")[0].get("status", "open") == "open":
            items.append(path.name)
    return items


def print_change_state(state: State, change: Change, verdicts: dict[str, str]) -> None:
    if change.status == "draft":
        problems = [text for level, text in approve_lint(state, change).lines if level == "FAIL"]
        if problems:
            print(f"not ready for approve: {plural(len(problems), 'problem')}")
            for text in problems[:5]:
                print(f"  {text}")
            if len(problems) > 5:
                print(f"  ... run: mise run spec-check -- --change {change.slug}")
        else:
            print("ready for approve: a human runs `! mise run approve`")
        return
    if change.status == "approved":
        group = next_group(change, verdicts)
        if group is None:
            print("all groups green: /sdd validate, then `mise run status -- --merge`")
            return
        missing = [sid for sid in group.ids if verdicts.get(sid) != "proven"]
        risk = ", risk: high (compile pauses after it)" if group.risk == "high" else ""
        trunk = trunk_at(state.ctx.root)
        named = [path for path in group.files if trunk.entry_for(path)]
        if risk and named:
            risk += f"; trunk: {', '.join(named)}"
        print(
            f"next: G{group.number} {group.name}: {' '.join(missing)} (no passing tests yet{risk})"
        )
        return
    print(f"change {change.name} is {change.status or 'without a status'}")


def print_change(state: State) -> int:
    ctx = state.ctx
    change = state.open_change
    if change is not None:
        print(f"change {change.name} ({change.status}) on {ctx.branch}")
        for name in ("requirements.md", "plan.md", "validation.md"):
            text = read_text(ctx.root / change.path / name)
            print(f"\n== {change.path}/{name}")
            print((text or "(missing)").rstrip())
    elif ctx.lane:
        print(f"{ctx.branch}: lane {ctx.lane} has no change folder; the branch is the whole state")
    else:
        print(f"{ctx.branch or 'detached HEAD'}: no open change")
        return 0
    if not ctx.base:
        print(f"\n(no merge-base with {ctx.default}: capability diff unavailable)")
        return 0
    print(f"\n== capability changes since {ctx.default} (git diff {ctx.base[:10]})")
    diff = git(ctx.root, "diff", "--no-color", ctx.base, "--", CAPS_DIR) or ""
    print(diff.rstrip() or "(none committed or staged)")
    for path in git_lines(ctx.root, "ls-files", "--others", "--exclude-standard", "--", CAPS_DIR):
        print(f"\nnew file, untracked: {path}")
        print((read_text(ctx.root / path) or "").rstrip())
    return 0


# ---------------------------------------------------------------- running uv and pytest


def uv_binary(root: Path) -> str | None:
    """The real uv executable, resolved in this repo. A mise shim re-reads the mise config of
    the folder it runs in, and a prove-red worktree's copy of mise.toml is untrusted there (mise
    refuses a config with [env] or [hooks] it was not told to trust) and may pin a uv that is
    not installed. So a shim is resolved once, here, with `mise which uv`; a shim mise does not
    manage here falls through to the next uv on PATH, as the shim itself would."""
    for folder in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(folder or ".") / "uv"
        if not candidate.is_file() or not os.access(candidate, os.X_OK):
            continue
        if candidate.resolve().name != "mise":
            return str(candidate)
        try:
            proc = subprocess.run(
                ["mise", "which", "uv"],  # noqa: S607
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        found = proc.stdout.strip()
        if proc.returncode == 0 and found and Path(found).is_file():
            return found
    return None


def tool_env(*, trusted: Path | None = None) -> dict[str, str]:
    """The environment for child uv and pytest runs: SCRUB_ENV removed. trusted: a temp folder
    holding worktrees of this repo, whose mise configs mise may then read."""
    env = {k: v for k, v in os.environ.items() if k not in SCRUB_ENV}
    if trusted is not None:
        env["PYTHONDONTWRITEBYTECODE"] = "1"  # a swapped source file must never meet a stale .pyc
        prior = env.get("MISE_TRUSTED_CONFIG_PATHS", "")
        env["MISE_TRUSTED_CONFIG_PATHS"] = os.pathsep.join(p for p in (str(trusted), prior) if p)
    return env


def run_uv(
    tree: Path,
    uv: str,
    args: list[str],
    env: dict[str, str],
    groups: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """uv with a fixed argv in tree, in a process group of its own. When the run passes
    PYTEST_TIMEOUT (it comes back as exit 124), or this script is interrupted or terminated,
    the whole group is killed, so no test process outlives the worktree it runs in. groups: a
    file to append the group id to, for sweep_stale_worktrees after a SIGKILL."""
    argv = [uv, *args]
    try:  # (no held_signals here: a child inherits the blocked signal mask)
        proc = subprocess.Popen(  # noqa: S603
            argv,
            cwd=tree,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            start_new_session=True,
        )
    except OSError as exc:
        return subprocess.CompletedProcess(argv, 127, "", f"cannot run {uv}: {exc}")
    try:
        if groups is not None:
            with groups.open("a", encoding="utf-8") as record:
                record.write(f"{proc.pid}\n")
        out, err = proc.communicate(timeout=PYTEST_TIMEOUT)
    except subprocess.TimeoutExpired:
        kill_group(proc)
        out, err = proc.communicate()
        return subprocess.CompletedProcess(
            argv, 124, out, err + f"\ntimed out after {PYTEST_TIMEOUT} s"
        )
    except BaseException:
        kill_group(proc)
        raise
    return subprocess.CompletedProcess(argv, proc.returncode, out, err)


def kill_group(proc: subprocess.Popen[str]) -> None:
    """Kill a child started with start_new_session=True and everything it started."""
    try:
        if hasattr(os, "killpg"):
            os.killpg(proc.pid, signal.SIGKILL)
        else:
            proc.kill()
    except (ProcessLookupError, PermissionError):
        pass
    proc.wait()


EXIT_SIGNALS = ("SIGTERM", "SIGHUP")  # CI cancelling a job; a closed terminal or SSH session


def exit_on_signal(signum: int, _frame: object) -> None:
    """SIGTERM or SIGHUP as an exception, so run_uv kills its process group and prove-red's
    finally block still removes its worktrees. (SIGINT already arrives as KeyboardInterrupt.)"""
    raise SystemExit(128 + signum)


def catch_exit_signals() -> None:
    """Route EXIT_SIGNALS through exit_on_signal. Only the main thread may set handlers."""
    for name in EXIT_SIGNALS:
        number = getattr(signal, name, None)
        if number is None:  # no SIGHUP on Windows
            continue
        try:
            signal.signal(number, exit_on_signal)
        except ValueError:
            return


@contextmanager
def held_signals() -> Iterator[None]:
    """Hold SIGINT and EXIT_SIGNALS inside the with block (cleanup must not be cut short); they
    are delivered when it ends. Children started inside inherit the mask, so only short git
    commands may run here, never uv or the tests."""
    names = ("SIGINT", *EXIT_SIGNALS)
    held = {getattr(signal, name) for name in names if hasattr(signal, name)}
    if not hasattr(signal, "pthread_sigmask"):
        yield
        return
    signal.pthread_sigmask(signal.SIG_BLOCK, held)
    try:
        yield
    finally:
        signal.pthread_sigmask(signal.SIG_UNBLOCK, held)


def tail(proc: subprocess.CompletedProcess[str], lines: int = 6) -> str:
    """The last lines of a run's output, for an error message."""
    text = [line for line in (proc.stdout + proc.stderr).splitlines() if line.strip()]
    return " | ".join(text[-lines:]) or f"exit {proc.returncode}, no output"


def split_ids(values: list[str]) -> list[str]:
    """Scenario ids from arguments that may be comma or space separated, in order, once each."""
    ids = [part for value in values for part in re.split(r"[,\s]+", value) if part]
    return list(dict.fromkeys(ids))


def covers(collector: str, test_file: str) -> bool:
    """True when a collection error in collector hides the tests of test_file."""
    if collector in ("", "."):
        return True
    return test_file == collector or test_file.startswith(collector.rstrip("/") + "/")


# ---------------------------------------------------------------- new and changed tests


def test_key(node: str) -> tuple[str, str]:
    """(file, function) of a pytest node id: 'tests/t.py::TestA::test_b[x-y]' gives
    ('tests/t.py', 'TestA::test_b'). The parametrized cases of a function share one key."""
    path, _, rest = node.partition("::")
    return path, rest.split("[", 1)[0]


def is_spec_tag(decorator: ast.expr) -> bool:
    """@pytest.mark.spec(...): tagging a test with one more id does not change what it checks."""
    func = decorator.func if isinstance(decorator, ast.Call) else None
    return isinstance(func, ast.Attribute) and func.attr == "spec"


def test_functions(text: str) -> dict[str, str] | None:
    """test key ('test_x', 'TestA::test_b') -> a dump of its code (positions and spec tags left
    out) for each function, method and plain `name = ...` assignment (a test made by calling a
    decorator) in a Python file; None when it does not parse."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return None
    found: dict[str, str] = {}

    def walk(body: list[ast.stmt], prefix: str) -> None:
        for stmt in body:
            if isinstance(stmt, ast.FunctionDef | ast.AsyncFunctionDef):
                stmt.decorator_list = [d for d in stmt.decorator_list if not is_spec_tag(d)]
                found[prefix + stmt.name] = ast.dump(stmt)
            elif isinstance(stmt, ast.ClassDef):
                walk(stmt.body, f"{prefix}{stmt.name}::")
            elif isinstance(stmt, ast.Assign | ast.AnnAssign):
                targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
                for target in targets:
                    if isinstance(target, ast.Name):
                        found[prefix + target.id] = ast.dump(stmt)

    walk(tree.body, "")
    return found


@dataclass
class Fresh:
    """The test nodes a branch wrote. changed: the test is new or its code differs from the
    base. added: the test did not exist at the base at all, so every one of its cases is new.
    same: the test's code is the base's (the other nodes could not be compared). moved: node ->
    its node id at the base, for a test the branch moved to another file."""

    changed: set[str] = field(default_factory=set)
    added: set[str] = field(default_factory=set)
    same: set[str] = field(default_factory=set)
    moved: dict[str, str] = field(default_factory=dict)


def fresh_tests(
    nodes: list[str],
    old: dict[str, str],
    new: dict[str, str],
    sources: dict[str, str] | None = None,
) -> Fresh:
    """Which nodes are new or changed from old to new (file path -> text). Every node of a file
    missing from old is added. In a file both have, a node whose function (or assignment) is
    missing from old is added, and one whose code differs is changed. A node whose definition
    cannot be found in a file old also has (a test inherited from a base class, a generated
    test) is left out: nothing shows it changed.
    sources: the base's text of the Python files the branch deleted or edited (moved_sources).
    A test that is new to its file but whose function, by name, sits in one of them was moved
    there, not written: it is same when its code is unchanged, else changed, never added."""
    parsed: dict[tuple[str, str], dict[str, str] | None] = {}
    origins: dict[str, list[tuple[str, str]]] = {}  # test key -> (base path, code) of each
    for source, text in sorted((sources or {}).items()):
        for key, code in (test_functions(text) or {}).items():
            origins.setdefault(key, []).append((source, code))

    def functions(side: str, texts: dict[str, str], path: str) -> dict[str, str] | None:
        if (side, path) not in parsed:
            text = texts.get(path)
            parsed[side, path] = None if text is None else test_functions(text)
        return parsed[side, path]

    fresh = Fresh()
    for node in nodes:
        path, key = test_key(node)
        now = functions("new", new, path)
        if now is None:
            continue  # not readable here, or not Python: nothing to compare
        before = functions("old", old, path) if path in old else {}
        if path not in old or (before is not None and key in now and key not in before):
            found = [item for item in origins.get(key, []) if item[0] != path]
            if key in now and found:
                source, code = next((i for i in found if i[1] == now[key]), found[0])
                fresh.moved[node] = source + node[len(path) :]
                (fresh.same if code == now[key] else fresh.changed).add(node)
                continue
            fresh.changed.add(node)
            fresh.added.add(node)
        elif key in now and (before is None or before.get(key) != now[key]):
            fresh.changed.add(node)
        elif key in now:
            fresh.same.add(node)
    return fresh


def moved_sources(root: Path, base: str, head: str | None) -> dict[str, str]:
    """The base's text of each Python file that head (None: the working tree) deletes or edits:
    where a test the branch moved to another file came from (fresh_tests)."""
    args = ["diff", "--name-only", "--no-renames", "--diff-filter=DM", "-z", base]
    out = run_git(root, *args, *([head] if head else []), "--", "*.py").stdout
    return read_blobs(root, base, z_paths(out))


# ---------------------------------------------------------------- tdd red | green


@dataclass
class TddVerdict:
    sid: str
    ok: bool
    lines: list[str]  # what to print: the verdict, then details
    reason: str = ""  # red: the Red: trailer text
    tests: list[str] = field(default_factory=list)
    passes: bool = False  # red refused because every linked test passes on this branch's code


def red_kind(node: Node | None) -> str:
    """How a test body failed: "right" (RIGHT_REDS), "wrong" (WRONG_REDS, or an AttributeError
    for a name a module lacks: the code is absent), "test" (another exception the test's own
    code raised, such as an IndexError on output that is not there: it proves nothing about
    the code), "raised" (any other exception, which code that exists raised: red as well), or
    "" when the body did not fail."""
    if node is None or node.outcome != "failed" or not node.body:
        return ""
    if node.body in RIGHT_REDS:
        return "right"
    if node.body in WRONG_REDS or MISSING_ATTR_RE.match(node.crash):
        return "wrong"
    if node.raised_in == "test":
        return "test"
    return "raised"


def red_reason(node: Node) -> str:
    """The Red: trailer text for a test that failed for the right reason: the assertion line
    ('assert 1 == 2'), 'DID NOT RAISE <...>', 'NotImplementedError', or the exception code that
    exists raised ('ValueError: bill must be a number')."""
    crash = " ".join(node.crash.split())
    if node.body == "AssertionError":
        text = crash.removeprefix("AssertionError").removeprefix(":").strip()
        reason = text or "AssertionError"
    elif node.body == "DID NOT RAISE":
        reason = crash.removeprefix("Failed:").strip() or "DID NOT RAISE"
    elif node.body and node.body != "NotImplementedError":
        reason = crash if crash.startswith(node.body) else node.body
    else:
        reason = node.body or "failed"
    return reason[:REASON_CAP]


def hidden_by_errors(root: Path, results: Results, sid: str) -> list[tuple[str, str, str]]:
    """(collector, exception type, message) of each collection error that may hide a test of
    sid: a test file that names sid, or a folder (its files are unknown)."""
    hits: list[tuple[str, str, str]] = []
    for collector, message in results.collect_errors:
        path = root / collector
        text = read_text(path) if path.is_file() else None
        if text is None or names_id(text, sid):
            hits.append((collector, results.collect_exc.get(collector, ""), message))
    return hits


def judge_red(root: Path, results: Results, sid: str, fresh: Fresh) -> TddVerdict:
    """Red for the right reason: at least one linked test fails in its body on RIGHT_REDS or
    on another exception code that exists raised (red_kind), no linked test fails for a wrong
    reason, every test function that is new or changed on the branch fails, and so does every
    case of a test that is new on the branch (a parametrized case of a new function cannot ride
    on its neighbour). Only a test the branch did not touch may pass (an older test on the id,
    beside a fix/ regression test)."""
    wrong: list[str] = []
    right: list[Node] = []
    for collector, exc, message in hidden_by_errors(root, results, sid):
        what = exc or "a collection error"
        wrong.append(f"{sid}: {what} is the wrong red: {STUB_HINT}")
        wrong.append(f"      {collector}: {message}")
    nodes = results.by_id.get(sid, [])
    for node in nodes:
        detail = f"      {node.node}: {node.crash}" if node.crash else f"      {node.node}"
        kind = red_kind(node)
        if kind in ("right", "raised"):
            right.append(node)
        elif kind == "wrong":
            wrong += [f"{sid}: {node.body} is the wrong red: {STUB_HINT}", detail]
        elif kind == "test":
            wrong += [f"{sid}: {node.body} is the wrong red: {TEST_SIDE_HINT}", detail]
        elif node.outcome in ("failed", "error"):
            wrong += [f"{sid}: a fixture error is the wrong red: the test body must run", detail]
        elif node.outcome in ("xfailed", "xpassed", "skipped"):
            wrong += [
                f"{sid}: {node.node} is {node.outcome}; a red test has no skip or xfail marker",
                detail,
            ]
        elif node.outcome != "passed":
            wrong += [f"{sid}: {node.node} did not run ({node.outcome})"]
    if wrong:
        return TddVerdict(sid, False, wrong)
    if not right:
        if not nodes:
            return TddVerdict(
                sid, False, [f'{sid}: no test is tagged @pytest.mark.spec("{sid}") yet']
            )
        names = ", ".join(n.node for n in nodes)
        return TddVerdict(
            sid,
            False,
            [
                (
                    f"{sid}: passes already ({names}); a red test fails before the code exists, "
                    "so assert what the scenario's THEN says"
                )
            ],
            passes=True,
        )
    red_keys = {test_key(n.node) for n in right}
    red_nodes = {n.node for n in right}
    idle = [
        n.node
        for n in nodes
        if (n.node in fresh.changed and test_key(n.node) not in red_keys)
        or (n.node in fresh.added and n.node not in red_nodes)
    ]
    if idle:
        return TddVerdict(
            sid,
            False,
            [
                (
                    f"{sid}: {', '.join(idle)} passes already; every new or changed test must "
                    "fail before the code exists (only a test this branch did not touch may pass)"
                )
            ],
        )
    reason = red_reason(next((n for n in right if red_kind(n) == "right"), right[0]))
    tests = [n.node for n in right]
    return TddVerdict(sid, True, [f"{sid}: red, {len(tests)} failing ({reason})"], reason, tests)


def judge_green(root: Path, results: Results, sid: str) -> TddVerdict:
    """Green: every linked test passes and no collection error hides one."""
    problems: list[str] = []
    for collector, exc, message in hidden_by_errors(root, results, sid):
        problems.append(f"{sid}: {collector} does not collect ({exc or 'error'}: {message})")
    nodes = results.by_id.get(sid, [])
    if not nodes:
        problems.append(f'{sid}: no test is tagged @pytest.mark.spec("{sid}")')
    for node in nodes:
        if node.outcome != "passed":
            detail = f": {node.crash}" if node.crash else ""
            problems.append(f"{sid}: {node.node} {node.outcome}{detail}")
    if problems:
        return TddVerdict(sid, False, problems)
    tests = [n.node for n in nodes]
    return TddVerdict(sid, True, [f"{sid}: green, {len(tests)} passing"], tests=tests)


def working_tree_fresh(ctx: Context, nodes: list[str]) -> Fresh:
    """The nodes whose test, as it is on disk, is new or changed since the merge-base (on the
    default branch: since HEAD)."""
    files = sorted({test_key(node)[0] for node in nodes})
    ref = ctx.base or ctx.head
    old = read_blobs(ctx.root, ref, files) if ref else {}
    new = {path: text for path in files if (text := read_text(ctx.root / path)) is not None}
    return fresh_tests(nodes, old, new, moved_sources(ctx.root, ref, None) if ref else None)


def tdd_record_path(ctx: Context) -> Path:
    return ctx.root / TDD_DIR / f"{ctx.branch or 'detached'}.json"


def load_tdd_record(path: Path) -> dict[str, dict[str, object]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    ids = data.get("ids") if isinstance(data, dict) else None
    return (
        {str(k): v for k, v in ids.items() if isinstance(v, dict)} if isinstance(ids, dict) else {}
    )


def save_tdd_record(ctx: Context, path: Path, ids: dict[str, dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"branch": ctx.branch, "ids": dict(sorted(ids.items()))}
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    tmp.replace(path)


def branch_wrote_code(ctx: Context) -> bool:
    """Whether the branch changes a source root since its merge-base: then a test that passes
    here may still be red on the base (validate's in-scope finding on built behaviour)."""
    if ctx.on_default or not ctx.base or not ctx.head:
        return False
    roots = project_paths(ctx.root)[0]
    return bool(git_lines(ctx.root, "diff", "--name-only", ctx.base, ctx.head, "--", *roots))


def cmd_tdd(ctx: Context, args: argparse.Namespace) -> int:
    ids = split_ids(args.ids)
    bad = [sid for sid in ids if not ID_RE.match(sid)]
    if not ids or bad:
        raise UsageError(f"tdd {args.phase}: scenario ids look like cli.no-args (got {bad or ids})")
    state = load_state(ctx)
    unknown = [sid for sid in ids if sid not in state.scenarios]
    for sid in unknown:
        print(f"FAIL  {sid}: no such scenario in {CAPS_DIR}/ (write the scenario first)")
    if unknown:
        return 1
    path = tdd_record_path(ctx)
    record = load_tdd_record(path)
    rel = path.relative_to(ctx.root).as_posix()
    if args.phase == "green":
        missing = [sid for sid in ids if not isinstance(record.get(sid, {}).get("red"), dict)]
        for sid in missing:
            print(
                f"FAIL  {sid}: no red record in {rel}; run `mise run tdd -- red {sid}` "
                "before writing the code"
            )
        if missing:
            return 1
    uv = uv_binary(ctx.root)
    if uv is None:
        print("FAIL  uv is not on PATH: run mise install")
        return 1
    (ctx.root / RESULTS).unlink(missing_ok=True)  # the run below must write fresh results
    spec = ",".join(ids)
    proc = run_uv(
        ctx.root,
        uv,
        ["run", "--locked", "--quiet", "pytest", "--continue-on-collection-errors", "--spec", spec],
        tool_env(),
    )
    results = load_results(ctx.root)
    if isinstance(results, str):
        print(f"FAIL  pytest wrote no results ({conftest_problem(ctx.root, proc) or tail(proc)})")
        return 1
    if args.phase == "red":
        nodes = [node.node for sid in ids for node in results.by_id.get(sid, [])]
        fresh = working_tree_fresh(ctx, nodes)
        verdicts = [judge_red(ctx.root, results, sid, fresh) for sid in ids]
    else:
        verdicts = [judge_green(ctx.root, results, sid) for sid in ids]
    for verdict in verdicts:
        print(f"{'ok' if verdict.ok else 'FAIL':<5} {verdict.lines[0]}")
        for line in verdict.lines[1:]:
            print(line if line.startswith(" ") else f"FAIL  {line}")
    failed = [v.sid for v in verdicts if not v.ok]
    if failed:
        if args.phase == "red":
            print(
                f"tdd red: refused for {', '.join(failed)}; nothing recorded. A right red is an "
                "AssertionError, a NotImplementedError from a stub, a pytest.raises that saw "
                "no exception, or another exception that code which exists raised"
            )
            passing = [v.sid for v in verdicts if v.passes]
            if passing and branch_wrote_code(ctx):
                print(
                    f"or the code is here already: when an earlier commit on {ctx.branch} wrote "
                    f"the behaviour of {', '.join(passing)}, its red shows only on the base. "
                    "Commit the scenario and its test with `Spec:` and no `Red:` line, then run "
                    "`mise run prove-red`, which runs the test on the base's code "
                    "(.claude/skills/sdd/validate.md, outcome 1)"
                )
        else:
            print(f"tdd green: {', '.join(failed)} not green yet")
        return 1
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    for verdict in verdicts:
        entry = {"at": now, "head": ctx.head or "", "tests": verdict.tests}
        if args.phase == "red":
            record[verdict.sid] = {"red": {**entry, "reason": verdict.reason}, "green": None}
        else:
            record[verdict.sid]["green"] = entry
    save_tdd_record(ctx, path, record)
    if args.phase == "red":
        print(f"tdd red: recorded in {rel}. Trailers for the commit, once green:")
    else:
        print(f"tdd green: recorded in {rel}. Refactor (tests unedited), then `mise run verify`,")
        print("then commit on green with these trailers:")
        print(f"Spec: {', '.join(ids)}")
    for sid in ids:
        red = record[sid].get("red")
        reason = red.get("reason", "") if isinstance(red, dict) else ""
        print(f"Red: {sid}: {reason}")
    if args.phase == "red":
        print(f"next: minimal code, then `mise run tdd -- green {' '.join(ids)}`")
    return 0


# ---------------------------------------------------------------- prove-red

COLLECT_MODULE = "_project_py_collect"
COLLECT_OUT = "PROJECT_PY_COLLECT_OUT"
COLLECT_PLUGIN = f'''"""Written by scripts/project.py prove-red for one run: tests and their ids."""
import json
import os

_errors = []


def pytest_collectreport(report):
    if report.failed:
        _errors.append(report.nodeid or ".")


def pytest_collection_finish(session):
    items = []
    for item in session.items:
        ids = []
        for mark in item.iter_markers("spec"):
            for arg in mark.args:
                if isinstance(arg, str) and arg not in ids:
                    ids.append(arg)
        items.append({{"node": item.nodeid, "ids": ids}})
    with open(os.environ["{COLLECT_OUT}"], "w", encoding="utf-8") as out:
        json.dump({{"items": items, "errors": _errors}}, out)
'''

# A red on the old code that stopped before the test body reached an assertion (an import of a
# name the base lacks, most often) is run once more with this plugin. It stands in the stub
# `tdd red` asks for: a name this repo's own packages lack on the old code becomes a stub that
# raises NotImplementedError when called (or used in sums, loops, comparisons of order), a
# CapWords name a class whose instances cannot be made, a name ending in Error an Exception
# subclass, and a missing module an empty stub module. A test that passes like that never needed
# the new code, whatever trailer names it.
STUB_MODULE = "_project_py_stubs"
STUB_NAMES = "PROJECT_PY_STUB_NAMES"
STUB_PLUGIN = f'''"""Written by scripts/project.py prove-red for one run: stubs on the old code."""
import builtins
import importlib
import importlib.machinery
import importlib.util
import os
import sys

_OURS = frozenset(n for n in os.environ.get("{STUB_NAMES}", "").split(",") if n)
_patched = set()
_import = builtins.__import__
_active = [False]  # True while a test's own import statement runs


def _ours(name):
    return bool(name) and name.partition(".")[0] in _OURS


def _a_test(name):
    """A test module inside the package: pkg.tests.test_x (src/pkg/tests), pkg.test_x (a
    test_*.py beside the code) or a conftest. It is HEAD's test code, never the old code."""
    parts = name.split(".")
    last = parts[-1]
    return (
        "tests" in parts
        or "test" in parts
        or last.startswith("test_")
        or last.endswith("_test")
        or last == "conftest"
    )


def _for_a_test(depth):
    """True when the code that looked the name up is a test's, not the old code's own: the old
    code must go on seeing what it always saw (an optional import that fails, a getattr default)."""
    caller = sys._getframe(depth + 1).f_globals.get("__name__") or ""
    if _ours(caller) and not _a_test(caller):
        return False
    return _active[0] or not caller.startswith("importlib")


def _refuse(name):
    raise NotImplementedError(f"{{name}} is not on the old code (a prove-red stub)")


class _Stub:
    def __init__(self, name):
        self._stub_name = name

    def __getattr__(self, attr):
        if attr.startswith("_"):
            raise AttributeError(attr)
        return _Stub(f"{{self._stub_name}}.{{attr}}")

    def __bool__(self):
        return True

    def __repr__(self):
        return f"<stub {{self._stub_name}}>"


def _refusing(self, *args, **kwargs):
    _refuse(self._stub_name)


_OPS = ("call", "iter", "len", "getitem", "contains", "int", "float", "index", "fspath", "enter")
_OPS += ("lt", "le", "gt", "ge", "add", "radd", "sub", "rsub", "mul", "rmul", "truediv")
_OPS += ("rtruediv", "floordiv", "rfloordiv", "mod", "rmod", "pow", "rpow", "neg", "abs")
for _op in _OPS:
    setattr(_Stub, f"__{{_op}}__", _refusing)


class _StubType(type):
    def __call__(cls, *args, **kwargs):
        _refuse(f"{{cls.__module__}}.{{cls.__qualname__}}")

    def __getattr__(cls, attr):
        if attr.startswith("_"):
            raise AttributeError(attr)
        _refuse(f"{{cls.__module__}}.{{cls.__qualname__}}.{{attr}}")


def _stub(module, attr):
    if attr[:1].isupper() and not attr.isupper():
        if attr.endswith(("Error", "Exception", "Warning")):
            return type(attr, (Exception,), {{"__module__": module}})
        return _StubType(attr, (), {{"__module__": module}})
    return _Stub(f"{{module}}.{{attr}}")


def _submodule(module, attr):
    """The real submodule module.attr, imported, or None when the old code has none."""
    path = getattr(module, "__path__", None)
    full = f"{{module.__name__}}.{{attr}}"
    if path is not None and importlib.machinery.PathFinder.find_spec(full, path):
        return importlib.import_module(full)
    return None


# What pytest looks up on the package a test inside it belongs to (src/pkg/__init__.py, for a
# test in src/pkg/tests): these miss as they always did, as dunders such as __path__ do. The
# test modules themselves are never patched (_patch), so pytest's lookups there
# (pytest_generate_tests, setup_function, ...) miss too.
_PYTEST_PROBES = frozenset(
    ("pytest_plugins", "pytestmark", "setUpModule", "setup_module", "tearDownModule")
    + ("teardown_module", "setup_function", "teardown_function")
)


def _module_getattr(module_name):
    def __getattr__(attr):
        if attr.startswith("__") or attr in _PYTEST_PROBES or not _for_a_test(1):
            raise AttributeError(attr)
        module = sys.modules.get(module_name)
        found = None if module is None else _submodule(module, attr)
        if found is not None:
            return found
        value = _stub(module_name, attr)
        if module is not None:
            setattr(module, attr, value)
        return value

    return __getattr__


def _patch():
    for name, module in list(sys.modules.items()):
        if name in _patched or module is None or not _ours(name) or _a_test(name):
            continue  # a test module inside the package is HEAD's: nothing on it is stubbed
        _patched.add(name)
        if "__getattr__" not in getattr(module, "__dict__", {{}}):
            module.__getattr__ = _module_getattr(name)


def _absolute(name, globals, level):
    if not level:
        return name
    try:
        return importlib.util.resolve_name("." * level + name, (globals or {{}}).get("__package__"))
    except (ImportError, ValueError):
        return ""


def _stubbing_import(name, globals=None, locals=None, fromlist=(), level=0):
    full = _absolute(name, globals, level)
    caller = (globals or {{}}).get("__name__") or ""
    mine = _ours(caller) and not _a_test(caller)
    if mine or not _ours(full):  # the old code's own imports fail as they always did
        saved, _active[0] = _active[0], False
        try:
            return _import(name, globals, locals, fromlist, level)
        finally:
            _active[0] = saved
    saved, _active[0] = _active[0], True
    try:
        if fromlist:  # load and patch the module first: a missing name is a stub, not a module
            _import(name, globals, locals, (), level)
            _patch()
            target = sys.modules.get(full)
            for attr in fromlist if target is not None else ():
                if attr != "*" and attr not in vars(target) and _submodule(target, attr) is None:
                    setattr(target, attr, _stub(full, attr))  # (a dunder such as __version__ too)
        module = _import(name, globals, locals, fromlist, level)
    finally:
        _active[0] = saved
    _patch()
    return module


class _StubModules:
    """Last on sys.meta_path: a module of this repo that the old code does not have."""

    @staticmethod
    def find_spec(name, path=None, target=None):
        if not (_active[0] and _ours(name)):
            return None
        return importlib.machinery.ModuleSpec(name, _StubModules, is_package=True)

    @staticmethod
    def create_module(spec):
        return None

    @staticmethod
    def exec_module(module):
        _patched.add(module.__name__)
        module.__getattr__ = _module_getattr(module.__name__)


builtins.__import__ = _stubbing_import
sys.meta_path.append(_StubModules)
_patch()


def pytest_collectstart(collector):
    _patch()


def pytest_runtest_setup(item):
    _patch()
'''


class ProveRedError(Exception):
    """prove-red could not reach a verdict: a worktree, uv sync or pytest run failed."""


@dataclass
class Collected:
    items: dict[str, list[str]]  # test node -> the scenario ids it is tagged with
    errors: list[str]  # collectors that failed

    def by_id(self) -> dict[str, list[str]]:
        found: dict[str, list[str]] = {}
        for node, ids in self.items.items():
            for sid in ids:
                found.setdefault(sid, []).append(node)
        return found


@dataclass
class Proof:
    sid: str
    kind: str  # red | guard | gap
    level: str  # ok | FAIL | warn
    text: str
    how: str = ""  # red: assertion | collection | exception | error | xpass


@dataclass
class ProveRed:
    base: str
    head: str
    proofs: list[Proof] = field(default_factory=list)
    count: tuple[int, int, int] | None = None  # (base, removed-only at base, head)
    report: Report = field(default_factory=Report)
    seconds: float = 0.0

    @property
    def ok(self) -> bool:
        return self.report.errors == 0 and all(p.level != "FAIL" for p in self.proofs)

    def summary(self) -> str:
        parts: list[str] = []
        red = [p for p in self.proofs if p.kind == "red"]
        hows = [p.how for p in red if p.level == "ok"]
        kinds = ", ".join(f"{hows.count(h)} {h}" for h in RED_HOWS if h in hows)
        parts.append(f"{len(hows)}/{len(red)} red on base" + (f" ({kinds})" if kinds else ""))
        for kind, word in (("guard", "guards"), ("gap", "gaps")):
            group = [p for p in self.proofs if p.kind == kind]
            good = sum(1 for p in group if p.level == "ok")
            verb = "pass" if kind == "guard" else "xfail"
            parts.append(f"{word} {good}/{len(group)} {verb}")
        if self.count is not None:
            parts.append(f"tests {self.count[0]} -> {self.count[2]}")
        return ", ".join(parts)


WORKTREE_PREFIX = "prove-red-"
PLUGIN_DIR = "plugin"  # the one-run pytest plugins, next to the worktrees
OWNER_FILE = "owner"  # the pid of the prove-red run that made the folder
GROUPS_FILE = "groups"  # the process groups run_uv started there, one per line


class Worktrees:
    """Detached worktrees of the repo in one temp folder; close() removes every one of them.
    The folder records its owner's pid and the process groups run_uv starts in it, so a later
    run can clean up after one that was killed outright (sweep_stale_worktrees)."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.tmp = Path(tempfile.mkdtemp(prefix=WORKTREE_PREFIX))
        (self.tmp / OWNER_FILE).write_text(f"{os.getpid()}\n", encoding="utf-8")
        self.groups = self.tmp / GROUPS_FILE
        self.added: list[Path] = []

    def add(self, name: str, ref: str) -> Path:
        path = self.tmp / name
        proc = run_git(self.root, "worktree", "add", "--quiet", "--detach", str(path), ref)
        if proc.returncode != 0:
            raise ProveRedError(
                f"git worktree add {ref[:10]} failed: {proc.stderr.decode(errors='replace')}"
            )
        self.added.append(path)
        return path

    def close(self) -> None:
        """Remove the worktrees and the folder. A second Ctrl-C, SIGTERM or SIGHUP waits until
        this is done, then takes effect."""
        with held_signals():
            remove_worktree_folder(self.root, self.tmp, self.added)


def remove_worktree_folder(root: Path, folder: Path, trees: list[Path]) -> None:
    for path in trees:
        run_git(root, "worktree", "remove", "--force", str(path))
    shutil.rmtree(folder, ignore_errors=True)
    run_git(root, "worktree", "prune")


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except (PermissionError, OSError):
        return True  # it exists (another user's), or we cannot tell: leave it alone
    return True


def kill_leftover_groups(folder: Path) -> None:
    """SIGKILL the process groups a killed run recorded in folder, but only those that still
    have a process working inside folder (Linux /proc), so a reused group id is never hit.
    Elsewhere nothing is killed: those tests end on their own once their worktree is gone."""
    try:
        text = (folder / GROUPS_FILE).read_text(encoding="utf-8")
    except OSError:
        return
    recorded = {int(line) for line in text.split() if line.isdigit()}
    proc_root = Path("/proc")
    if not recorded or not proc_root.is_dir():
        return
    doomed: set[int] = set()
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            group = os.getpgid(int(entry.name))
            cwd = Path(os.readlink(entry / "cwd"))
        except OSError:
            continue
        if group in recorded and (cwd == folder or folder in cwd.parents):
            doomed.add(group)
    for group in doomed - {os.getpgrp()}:
        try:
            os.killpg(group, signal.SIGKILL)
        except OSError:
            pass


def sweep_stale_worktrees(root: Path) -> list[str]:
    """Remove the prove-red worktrees of this repo whose run is gone (SIGKILL, a crash, a power
    cut), after killing the tests still running in them. A folder whose owner still runs, or
    that has no owner file, is left alone. Returns the folders removed."""
    listing = git(root, "worktree", "list", "--porcelain") or ""
    by_folder: dict[Path, list[Path]] = {}
    for line in listing.splitlines():
        if line.startswith("worktree "):
            path = Path(line.removeprefix("worktree "))
            if path.parent.name.startswith(WORKTREE_PREFIX):
                by_folder.setdefault(path.parent, []).append(path)
    removed: list[str] = []
    for folder, trees in sorted(by_folder.items()):
        try:
            owner = int((folder / OWNER_FILE).read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            continue
        if owner == os.getpid() or pid_alive(owner):
            continue
        with held_signals():
            kill_leftover_groups(folder)
            remove_worktree_folder(root, folder, trees)
        removed.append(str(folder))
    return removed


def branch_trailers(root: Path, base: str, head: str) -> list[str]:
    """The trailer blocks of the branch's own commits, newest first (merges from the default
    branch left out)."""
    return commit_trailers(root, "--no-merges", f"{base}..{head}")


def trailer_ids(blocks: list[str], key: str) -> list[str]:
    return split_ids([value for block in blocks for value in trailer_values(block, key)])


def red_notes(blocks: list[str]) -> dict[str, str]:
    """scenario id -> reason, from the `Red: <id>: <reason>` trailers tdd red prints (the
    newest one per id)."""
    notes: dict[str, str] = {}
    for block in blocks:
        for value in trailer_values(block, "Red"):
            sid, sep, reason = value.partition(":")
            if sep and ID_RE.match(sid.strip()) and reason.strip():
                notes.setdefault(sid.strip(), reason.strip())
    return notes


CONFTEST_RE = re.compile(r"(\w+) while loading conftest '([^']+)'")


def conftest_problem(tree: Path, proc: subprocess.CompletedProcess[str]) -> str | None:
    """'tests/conftest.py does not load (ImportError: ...)' when pytest stopped before any test
    because a conftest.py failed to import; None otherwise."""
    text = f"{proc.stdout}\n{proc.stderr}"
    match = CONFTEST_RE.search(text)
    if match is None:
        return None
    path = match[2]
    for prefix in (str(tree), str(tree.resolve())):
        path = path.removeprefix(prefix + os.sep)
    error = next((line[1:].strip() for line in text.splitlines() if line.startswith("E ")), "")
    error = re.sub(r" \([^()]*[/\\][^()]*\)$", "", error)  # the module's file path
    error = " ".join((error or match[1]).split())[:REASON_CAP]
    return f"{path} does not load ({error})"


def sync_tree(tree: Path, uv: str, env: dict[str, str], groups: Path) -> None:
    proc = run_uv(tree, uv, ["sync", "--locked", "--quiet"], env, groups)
    if proc.returncode != 0:
        raise ProveRedError(f"uv sync --locked failed in the HEAD worktree: {tail(proc)}")


def with_plugins(tree: Path, env: dict[str, str]) -> dict[str, str]:
    """env with the folder of prove-red's one-run pytest plugins (next to tree) on PYTHONPATH."""
    plugin_dir = str(tree.parent / PLUGIN_DIR)
    return {
        **env,
        "PYTHONPATH": os.pathsep.join(p for p in (plugin_dir, env.get("PYTHONPATH")) if p),
    }


def collect(
    tree: Path,
    uv: str,
    env: dict[str, str],
    groups: Path,
    what: str,
    project: Path | None = None,
) -> Collected:
    """pytest --collect-only -q in tree, with a one-run plugin that lists each test's ids.
    what: 'HEAD' or 'base', for the output file and the error message. project: run in that
    worktree's (already synced) environment instead of tree's own."""
    out = tree.parent / f"collected-{what}.json"
    out.unlink(missing_ok=True)
    run_env = {**with_plugins(tree, env), COLLECT_OUT: str(out)}
    if project is None:
        argv = ["run", "--locked", "--quiet"]
    else:
        argv = ["run", "--no-sync", "--project", str(project), "--quiet"]
    # python -m: the environment's own pytest, never another one on PATH (uv run falls back to
    # PATH when the environment has none, as a brownfield base's may not)
    argv += ["python", "-m", "pytest", "--collect-only", "-q", "--continue-on-collection-errors"]
    proc = run_uv(tree, uv, [*argv, "-p", COLLECT_MODULE], run_env, groups)
    try:
        data = json.loads(out.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        where = "at HEAD" if what == "HEAD" else "on the base's tests and code"
        why = conftest_problem(tree, proc) or tail(proc)
        raise ProveRedError(f"pytest --collect-only failed {where}: {why}") from None
    raw = data.get("items") if isinstance(data, dict) else None
    items: dict[str, list[str]] = {}
    for entry in raw if isinstance(raw, list) else []:
        if isinstance(entry, dict) and isinstance(entry.get("node"), str):
            items[entry["node"]] = [str(i) for i in entry.get("ids", []) if isinstance(i, str)]
    errors = data.get("errors") if isinstance(data, dict) else None
    return Collected(items, [str(e) for e in errors] if isinstance(errors, list) else [])


def collect_base(
    trees: Worktrees, base: str, head: Path, uv: str, env: dict[str, str], report: Report
) -> Collected:
    """The count guard's collection, in a second worktree at the base: the base's own test
    files under the base's own pytest config, on the old code. It runs in the base's
    environment when the base's uv.lock syncs and pytest runs there. Otherwise (a brownfield
    base with no lockfile or no pytest yet, or a stale lock) it borrows HEAD's environment,
    whose editable install already points at the old code in the HEAD worktree, and notes it.
    When neither can collect the base (its pytest config is broken), the guard compares with 0
    and warns: the branch cannot fix the base, so failing here would leave no way to merge."""
    tree = trees.add("base", base)
    why = "the base has no uv.lock"
    found: Collected | None = None
    if (tree / "uv.lock").is_file():
        synced = run_uv(tree, uv, ["sync", "--locked", "--quiet"], env, trees.groups)
        if synced.returncode != 0:
            why = "uv sync --locked fails at the base"
        else:
            try:
                found = collect(tree, uv, env, trees.groups, "base")
            except ProveRedError:
                why = "pytest does not run in the base's environment"
    if found is None:
        try:
            found = collect(tree, uv, env, trees.groups, "base", project=head)
        except ProveRedError as exc:
            report.warn(
                f"the count guard compares with 0: the base's tests collect neither in its own "
                f"environment nor in HEAD's ({exc})"
            )
            return Collected({}, ["."])
        report.note(f"the base's tests were collected with HEAD's environment: {why}")
    if found.errors:
        report.warn(
            f"{', '.join(found.errors)} did not collect at the base, so its test count may be low"
        )
    return found


def stub_names(root: Path, ref: str, roots: list[str]) -> list[str]:
    """The top-level names this repo's code imports as at ref: each package folder and .py
    module directly in a source root, or the root itself when it is a package (a flat layout).
    The stub plugin stands in only for names under these."""
    names: set[str] = set()
    for folder in roots:
        if git_lines(root, "ls-tree", "--name-only", ref, "--", f"{folder}/__init__.py"):
            names.add(PurePosixPath(folder).name)
            continue
        for line in git_lines(root, "ls-tree", ref, "--", f"{folder}/"):
            meta, _, path = line.partition("\t")
            name = PurePosixPath(path).name
            if " tree " in f" {meta} " and name.isidentifier():
                names.add(name)
            elif name.endswith(".py") and name[:-3].isidentifier():
                names.add(name[:-3])
    return sorted(names)


def run_with_stubs(
    tree: Path, uv: str, env: dict[str, str], groups: Path, ids: list[str], names: list[str]
) -> Results | str:
    """The tests of ids on the old code once more, with STUB_PLUGIN standing in for the names
    the old code lacks; the results, or why there are none."""
    run_env = {**with_plugins(tree, env), STUB_NAMES: ",".join(names)}
    argv = ["run", "--locked", "--quiet", "pytest", "--continue-on-collection-errors"]
    argv += ["-p", STUB_MODULE, "--spec", ",".join(ids)]
    (tree / RESULTS).unlink(missing_ok=True)
    proc = run_uv(tree, uv, argv, run_env, groups)
    loaded = load_results(tree)
    if isinstance(loaded, str):
        return conftest_problem(tree, proc) or tail(proc)
    return loaded


def old_roots(root: Path, base: str, head: str, roots: list[str]) -> list[str]:
    """The roots that exist at base or at head: the pathspecs a --no-overlay checkout of the
    base takes (a root only at head is removed by it)."""
    return [
        r
        for r in roots
        if git_lines(root, "ls-tree", "--name-only", base, "--", r)
        or git_lines(root, "ls-tree", "--name-only", head, "--", r)
    ]


def tests_in_src(root: Path, base: str, head: str, src: list[str], tests: list[str]) -> list[str]:
    """The test code inside the source roots, as either commit holds it: each test root there
    (src/pkg/tests) and each test file outside those (a test_*.py or conftest.py beside the
    code). It is HEAD's test code, not the old code: prove-red puts it back after the swap."""
    nested = [t for t in tests if under(t, src)]
    listed = {
        path
        for ref in (base, head)
        for path in git_lines(root, "ls-tree", "-r", "--name-only", ref, "--", *src)
    }
    loose = sorted(p for p in listed if test_file(p) and not under(p, nested))
    return old_roots(root, base, head, nested) + loose


def test_file(path: str) -> bool:
    """A test file by pytest's default names (test_*.py, *_test.py), or a conftest.py."""
    name = PurePosixPath(path).name
    tested = name.startswith("test_") or name.endswith("_test.py")
    return name == "conftest.py" or (name.endswith(".py") and tested)


def in_tests(path: str, src_roots: list[str], test_roots: list[str]) -> bool:
    """A path of the test code: under a test root (src/pkg/tests too), or a test_file beside
    the code in a source root. commit-msg, pre-commit and prove-red read it as a test."""
    return under(path, test_roots) or (under(path, src_roots) and test_file(path))


def checkout_old(tree: Path, base: str, roots: list[str]) -> None:
    """Swap roots in tree for their state at base; files added since are removed [C]."""
    if not roots:
        return
    proc = run_git(tree, "checkout", "--no-overlay", base, "--", *roots)
    if proc.returncode != 0:
        raise ProveRedError(
            f"checkout of the old {', '.join(roots)} failed: "
            f"{proc.stderr.decode(errors='replace').strip()}"
        )


RED_OUTCOMES = ("failed", "error", "collection", "xpass-strict")
RED_HOWS = ("assertion", "exception", "error", "collection", "xpass")
SHOWN = {"xpass-strict": "passed (strict XPASS)", "collection": "does not collect"}


def shown(outcome: str) -> str:
    """An old_outcome() outcome as a message says it."""
    return SHOWN.get(outcome, outcome)


def old_outcome(results: Results, test: str) -> tuple[str, str]:
    """(outcome, detail) of one HEAD test on the old code. Outcomes: the conftest's (passed,
    failed, error, xfailed, xpassed, skipped), plus xpass-strict, collection and notrun."""
    node = results.nodes.get(test)
    if node is not None:
        if node.outcome == "xpassed" and node.xfail_strict:
            return "xpass-strict", "strict XPASS"
        return node.outcome, node.crash
    test_file = test.split("::", 1)[0]
    for collector, message in results.collect_errors:
        if covers(collector, test_file):
            return "collection", results.collect_exc.get(collector) or message
    return "notrun", ""


def shows_red(node: Node | None, outcome: str) -> bool:
    """A red on the old code that ran the test body to a right reason (RIGHT_REDS), or a strict
    XPASS. A collection error, a fixture error or another exception stops before the
    assertions: it shows that code is missing, not that the test pins anything."""
    if outcome == "xpass-strict":
        return True
    return outcome == "failed" and node is not None and node.body in RIGHT_REDS


Seen = tuple[str, str, str]  # (test node, old_outcome, detail)


def red_units(seen: list[Seen], fresh: Fresh) -> list[list[Seen]]:
    """What must be red, each unit on its own: every new or changed test function of the
    scenario (its parametrized cases together: one of them failing is enough, since an older
    case may be kept), and every case that is new on the branch (it cannot ride on another).
    With no new or changed test (a MODIFIED scenario whose tests stayed), all linked tests form
    one unit."""
    units: dict[tuple[str, ...], list[Seen]] = {}
    for item in seen:
        if item[0] in fresh.changed:
            units.setdefault(("function", *test_key(item[0])), []).append(item)
        if item[0] in fresh.added:
            units.setdefault(("case", item[0]), []).append(item)
    return list(units.values()) or [seen]


def prove_red_kind(
    sid: str,
    seen: list[Seen],
    results: Results,
    fresh: Fresh,
    note: str | None,
    stubbed: Results | str | None = None,
) -> Proof:
    """An ADDED, MODIFIED or `Spec:` id: some linked test is red on the old code, and so is each
    unit of red_units (a test the branch did not touch may pass, as an older test beside a fix/
    regression test does). A unit whose red never reached a right reason (a collection error, a
    fixture error, another exception) is judged by its run with stubs (stubbed): a right red
    there proves it, a pass there proves it pins nothing new. Only when neither shows (the stubs
    cannot reach the body either) does the id's `Red:` trailer from `tdd red` carry it."""
    reds = [s for s in seen if s[1] in RED_OUTCOMES]
    if not reds:
        outcomes = {outcome for _, outcome, _ in seen}
        verb = (
            "passes"
            if {"passed", "xpassed"} & outcomes
            else "xfails"
            if "xfailed" in outcomes
            else "is skipped"
            if "skipped" in outcomes
            else "does not run"
        )
        listed = ", ".join(f"{test} {shown(outcome)}" for test, outcome, _ in seen)
        return Proof(
            sid, "red", "FAIL", f"{sid} {verb} on the old code: it pins nothing new ({listed})"
        )
    units = red_units(seen, fresh)
    idle = [
        f"{test} {shown(outcome)}"
        for test, outcome, _ in dict.fromkeys(
            item
            for items in units
            if not any(outcome in RED_OUTCOMES for _, outcome, _ in items)
            for item in items
        )
    ]
    if idle:
        return Proof(
            sid,
            "red",
            "FAIL",
            f"{sid}: {', '.join(idle)} on the old code, so it pins nothing new; every new or "
            "changed test of the scenario must fail there",
        )

    def evidenced(items: list[Seen], where: Results, raised: bool = False) -> Node | None:
        """The first test of items that shows a right red in where; with raised, also one
        whose body met an exception that code which exists raised (red_kind)."""
        for test, _, _ in items:
            outcome, _ = old_outcome(where, test)
            node = where.nodes.get(test)
            if shows_red(node, outcome) or (raised and red_kind(node) == "raised"):
                return node
        return None

    def rank(item: Seen) -> int:
        node = results.nodes.get(item[0])
        return 0 if shows_red(node, item[1]) else 1 if red_kind(node) == "raised" else 2

    best = min(reds, key=rank)
    how, reason = red_how(results.nodes.get(best[0]), best[1], best[2])
    blind = [items for items in units if evidenced(items, results) is None]
    if not blind:
        return Proof(sid, "red", "ok", f"{sid} red ({reason})", how)
    open_units: list[list[Seen]] = []
    stub_reason = ""
    for items in blind:
        if not isinstance(stubbed, Results):
            open_units.append(items)
            continue
        node = evidenced(items, stubbed, raised=True)
        if node is not None:
            found = red_reason(node)
            stub_reason = stub_reason or ("" if found == reason else found)
            continue
        under = [(test, old_outcome(stubbed, test)[0]) for test, _, _ in items]
        if all(outcome in ("passed", "xpassed") for _, outcome in under):
            listed = ", ".join(f"{test} {outcome}" for test, outcome in under)
            return Proof(
                sid,
                "red",
                "FAIL",
                f"{sid}: {listed} on the old code with stubs for the names it lacks, so it pins "
                "nothing new: without the stubs it failed there only because the new code is "
                "missing",
            )
        open_units.append(items)
    if not open_units:
        stubs = f"; with stubs: {stub_reason}" if stub_reason else ""
        return Proof(sid, "red", "ok", f"{sid} red ({reason}{stubs})", how)
    if note is not None:
        return Proof(sid, "red", "ok", f"{sid} red ({reason}); Red: {note}", how)
    test, outcome, detail = next(s for s in open_units[0] if s[1] in RED_OUTCOMES)
    if red_kind(results.nodes.get(test)) == "test":
        return Proof(
            sid,
            "red",
            "FAIL",
            f"{sid}: {test} fails on the old code on an exception its own code raised "
            f"({detail or 'no detail'}), so that red proves nothing: {TEST_SIDE_HINT}",
        )
    return Proof(
        sid,
        "red",
        "FAIL",
        f"{sid}: {test} fails on the old code before its body reaches an assertion "
        f"({red_how(results.nodes.get(test), outcome, detail)[1]}), so that red proves "
        f"nothing; commit the 'Red: {sid}: <reason>' line that `mise run tdd -- red {sid}` "
        "prints once a stub lets the body run",
    )


def prove_one(
    sid: str,
    kind: str,
    tests: list[str],
    results: Results,
    fresh: Fresh | None = None,
    note: str | None = None,
    stubbed: Results | str | None = None,
) -> Proof:
    """One scenario's verdict on the old code (specs/README.md, the prove-red table). fresh:
    the tests new or changed on the branch; note: the id's Red: trailer reason; stubbed: the
    run with stubs of the ids whose red never reached a right reason (or why it has none)."""
    if not tests:
        return Proof(sid, kind, "FAIL", f"{sid} has no linked test at HEAD, so nothing proves it")
    seen = [(test, *old_outcome(results, test)) for test in tests]
    outcomes = [outcome for _, outcome, _ in seen]
    if kind == "red":
        return prove_red_kind(sid, seen, results, fresh or Fresh(), note, stubbed)
    if kind in ("guard", "flag-off"):
        name = "flag-off guard" if kind == "flag-off" else "guard"
        broke = f"{sid} {name} broke:"
        if kind == "flag-off":
            broke += " the old behaviour changed with the flag off:"
        for test, outcome, detail in seen:
            if outcome in ("failed", "error", "xpass-strict"):
                return Proof(
                    sid,
                    "guard",
                    "FAIL",
                    f"{broke} {test} {shown(outcome)} on the old code ({detail or 'no detail'})",
                )
        if all(outcome == "passed" for outcome in outcomes):
            return Proof(sid, "guard", "ok", f"{sid} {name}: passes on the old code")
        test, outcome, detail = next(s for s in seen if s[1] != "passed")
        what = shown(outcome)
        return Proof(
            sid,
            "guard",
            "warn",
            f"{sid} {name} inconclusive: {test} {what} on the old code"
            + (f" ({detail})" if detail else ""),
        )
    for test, outcome, _ in seen:
        if outcome in ("passed", "xpassed", "xpass-strict"):
            return Proof(
                sid,
                kind,
                "FAIL",
                f"{sid} gap test does not reproduce the gap: {test} {shown(outcome)} on the "
                "old code",
            )
    if all(outcome == "xfailed" for outcome in outcomes):
        return Proof(sid, kind, "ok", f"{sid} gap: xfails on the old code")
    test, outcome, detail = next(s for s in seen if s[1] != "xfailed")
    if outcome == "collection":
        return Proof(
            sid,
            kind,
            "warn",
            f"{sid} gap inconclusive: {test} does not collect on the old code ({detail})",
        )
    return Proof(
        sid,
        kind,
        "FAIL",
        f"{sid} gap test {shown(outcome)} on the old code; it must xfail there "
        f"({detail or 'no detail'})",
    )


def red_how(node: Node | None, outcome: str, detail: str) -> tuple[str, str]:
    """(kind of red, reason) for the summary and the per-id line."""
    if outcome == "collection":
        return "collection", "collection error"
    if outcome == "xpass-strict":
        return "xpass", "strict XPASS"
    if outcome == "error":
        return "error", f"error: {detail}" if detail else "error"
    if node is not None and node.body in ("AssertionError", "DID NOT RAISE"):
        return "assertion", red_reason(node)
    if node is not None and node.body:
        text = " ".join(detail.split())
        if not text or text.startswith(node.body):
            return "exception", text or node.body
        return "exception", f"{node.body}: {text}"
    return "exception", detail or "failed"


def kinds_to_prove(
    ctx: Context, head: dict[str, Scenario], base: dict[str, Scenario], blocks: list[str]
) -> tuple[dict[str, str], list[str]]:
    """scenario id -> red | guard | flag-off | gap, and warnings about trailers that do not apply.

    ids = ADDED + MODIFIED + ids in `Spec:` trailers on fix/ and chg/. Guards: on
    plan/project-init every ADDED scenario that is not a gap (a characterization guard); on
    fix/ the `Spec-Guard:` ids, the "SHALL CONTINUE TO" neighbours of a bug fix, as long as they
    are not MODIFIED or in `Spec:`. Everywhere else `Spec-Guard:` is ignored, so an added or
    changed scenario is always proven red (the human-only escape is merge --allow), except a
    [flag-off] one: on any lane it is a flag-off guard, the old behaviour with the flag off,
    which passes on the old code (I22). Every [gap] scenario at HEAD is proven as a gap,
    changed on the branch or not (design 5.5 runs `--spec <ids + guards + gaps>`), so a gap
    test edited on the branch must still xfail.
    """
    added = set(head) - set(base)
    modified = {sid for sid in set(head) & set(base) if head[sid].block != base[sid].block}
    spec = trailer_ids(blocks, "Spec") if ctx.lane in ("fix", "chg") else []
    named = trailer_ids(blocks, "Spec-Guard")
    warnings = [
        f"{sid}: named in a {key} trailer but not a scenario at HEAD; nothing to prove"
        for key, ids in (("Spec:", spec), ("Spec-Guard:", named))
        for sid in ids
        if sid not in head
    ]
    guards: set[str] = set()
    for sid in (sid for sid in named if sid in head):
        if ctx.lane != "fix":
            warnings.append(
                f"{sid}: Spec-Guard: ignored on {ctx.branch or 'a detached HEAD'}; only a fix/ "
                "branch declares guards, so the scenario is proven like any other"
            )
        elif sid in modified or sid in spec:
            what = "changed" if sid in modified else "named in Spec:"
            warnings.append(
                f"{sid}: Spec-Guard: ignored; the scenario is {what}, so it must be red on the "
                "old code (the human-only escape is merge --allow)"
            )
        else:
            guards.add(sid)
    if ctx.branch == INIT_BRANCH:
        guards |= {sid for sid in added if not head[sid].gap}
    gaps = {sid for sid, scenario in head.items() if scenario.gap}
    flagged = {sid for sid in (added | modified | set(spec)) & set(head) if head[sid].flag_off}
    kinds: dict[str, str] = {}
    for sid in sorted((added | modified | set(spec) | guards | gaps) & set(head)):
        kind = "flag-off" if sid in flagged else "guard" if sid in guards else "red"
        kinds[sid] = "gap" if head[sid].gap else kind
    return kinds, warnings


def run_prove_red(ctx: Context, base_ref: str | None) -> ProveRed:
    """The whole proof, in two worktrees. In one of HEAD, the source roots are swapped for the
    old code (as they were at the merge-base, checked out with --no-overlay so files added
    since are gone), all but the tests inside them (tests_in_src), which stay HEAD's. The
    tests of the scenarios to prove run there; a red that never reached a right reason runs
    once more with stubs for the names the old code lacks. The other, at the merge-base, is
    the count guard's: the base's own tests under the base's own pytest config, on the old
    code (see collect_base for the environment it runs in).
    """
    started = time.monotonic()
    if ctx.head is None:
        raise UsageError("prove-red: this repo has no commits")
    ref = base_ref or ctx.default_ref
    if ref is None:
        raise UsageError(f"prove-red: no {ctx.default} branch to compare with; pass --base <ref>")
    target = git(ctx.root, "rev-parse", "-q", "--verify", f"{ref}^{{commit}}")
    if not target:
        raise UsageError(f"prove-red: --base {ref} is not a commit")
    merge_base = (git(ctx.root, "merge-base", ctx.head, target.strip()) or "").strip()
    if not merge_base:
        raise UsageError(f"prove-red: HEAD and {ref} share no history")
    proof = ProveRed(merge_base, ctx.head)
    report = proof.report
    for folder in sweep_stale_worktrees(ctx.root):
        report.note(f"removed {folder}: a prove-red run that was killed left it behind")
    if merge_base == ctx.head:
        return proof
    if git_lines(ctx.root, "status", "--porcelain", "--untracked-files=no"):
        report.warn("prove-red judges the committed HEAD; uncommitted edits are left out")
    head_scen = scenarios_at(ctx.root, ctx.head)
    base_scen = scenarios_at(ctx.root, merge_base)
    blocks = branch_trailers(ctx.root, merge_base, ctx.head)
    kinds, warnings = kinds_to_prove(ctx, head_scen, base_scen, blocks)
    for text in warnings:
        report.warn(text)
    removed = set(base_scen) - set(head_scen)
    unmarked = sorted(removed - set(trailer_ids(blocks, "Spec-Removed")))
    if unmarked:
        report.warn(f"removed without a Spec-Removed: trailer: {', '.join(unmarked)}")
    src_roots, test_roots = committed_paths(ctx.root, (ctx.head, merge_base))
    uv = uv_binary(ctx.root)
    if uv is None:
        raise ProveRedError("uv is not on PATH: run mise install")
    trees = Worktrees(ctx.root)
    try:
        env = tool_env(trusted=trees.tmp)
        plugin = trees.tmp / PLUGIN_DIR
        plugin.mkdir()
        (plugin / f"{COLLECT_MODULE}.py").write_text(COLLECT_PLUGIN, encoding="utf-8")
        (plugin / f"{STUB_MODULE}.py").write_text(STUB_PLUGIN, encoding="utf-8")
        tree = trees.add("head", ctx.head)
        sync_tree(tree, uv, env, trees.groups)
        at_head = collect(tree, uv, env, trees.groups, "HEAD")
        for collector in at_head.errors:
            report.fail(f"{collector} does not collect at HEAD, so its tests prove nothing")
        tests_of = at_head.by_id()
        checkout_old(tree, merge_base, old_roots(ctx.root, merge_base, ctx.head, src_roots))
        own = tests_in_src(ctx.root, merge_base, ctx.head, src_roots, test_roots)
        checkout_old(tree, ctx.head, own)  # the tests inside src stay HEAD's
        at_base = collect_base(trees, merge_base, tree, uv, env, report)
        runnable = sorted(sid for sid in kinds if tests_of.get(sid))
        results = Results(True, [], "", {}, {}, [], [], None)
        if runnable:
            argv = ["run", "--locked", "--quiet", "pytest", "--continue-on-collection-errors"]
            proc = run_uv(tree, uv, [*argv, "--spec", ",".join(runnable)], env, trees.groups)
            loaded = load_results(tree)
            if isinstance(loaded, str):
                if problem := conftest_problem(tree, proc):
                    raise ProveRedError(
                        f"{problem} on the old code, so no test ran there and nothing is "
                        "proven. A conftest.py may import only what the base already has: "
                        "import new code inside the fixture that uses it"
                    )
                raise ProveRedError(f"the run on the old code wrote no results: {tail(proc)}")
            results = loaded
        red_ids = [sid for sid in runnable if kinds[sid] == "red"]
        blind = [sid for sid in red_ids if any(stops_short(results, t) for t in tests_of[sid])]
        stubbed: Results | str | None = None
        if blind:
            names = stub_names(ctx.root, ctx.head, src_roots)
            stubbed = run_with_stubs(tree, uv, env, trees.groups, blind, names)
            if isinstance(stubbed, str):
                report.warn(f"the run with stubs on the old code wrote no results: {stubbed}")
        nodes = [test for sid in red_ids for test in tests_of[sid]]
        files = sorted({test_key(test)[0] for test in nodes})
        fresh = fresh_tests(
            nodes,
            read_blobs(ctx.root, merge_base, files),
            read_blobs(ctx.root, ctx.head, files),
            moved_sources(ctx.root, merge_base, ctx.head),
        )
        fresh.added |= {  # a case the base did not collect is new, unless its code is the base's
            test
            for test in nodes
            if test not in fresh.same
            and (was := fresh.moved.get(test, test)) not in at_base.items
            and not any(covers(collector, test_key(was)[0]) for collector in at_base.errors)
        }
        notes = red_notes(blocks)
        order = {"red": 0, "guard": 1, "flag-off": 1, "gap": 2}
        for sid in sorted(kinds, key=lambda s: (order[kinds[s]], s)):
            tests = tests_of.get(sid, [])
            proof.proofs.append(
                prove_one(sid, kinds[sid], tests, results, fresh, notes.get(sid), stubbed)
            )
        base_count = len(at_base.items)
        removed_only = sum(1 for ids in at_base.items.values() if ids and set(ids) <= removed)
        head_count = len(at_head.items)
        proof.count = (base_count, removed_only, head_count)
        floor = base_count - removed_only
        note = f" ({removed_only} linked only to removed ids)" if removed_only else ""
        if head_count >= floor:
            report.ok(f"test count {base_count} -> {head_count}{note}")
        else:
            report.fail(
                f"tests disappeared: {head_count} collected at HEAD, {base_count} at the base"
                f"{note}; a test goes only with its scenario (Spec-Removed:)"
            )
    finally:
        trees.close()
        proof.seconds = time.monotonic() - started
    return proof


def stops_short(results: Results, test: str) -> bool:
    """True when test is red on the old code but never reached a right reason there."""
    outcome, _ = old_outcome(results, test)
    return outcome in RED_OUTCOMES and not shows_red(results.nodes.get(test), outcome)


def cmd_prove_red(ctx: Context, args: argparse.Namespace) -> int:
    try:
        proof = run_prove_red(ctx, args.base)
    except ProveRedError as exc:
        print(f"FAIL  prove-red: {exc}")
        return 1
    where = ctx.branch or "detached HEAD"
    if proof.base == proof.head:
        print(f"prove-red {where}: nothing to prove, HEAD is the base ({proof.base[:10]})")
        proof.report.print()
        return 0
    print(f"prove-red {where}: HEAD {proof.head[:10]} against the base {proof.base[:10]}")
    for item in proof.proofs:
        print(f"{item.level:<5} {item.text}")
    proof.report.print()
    verdict = "ok" if proof.ok else "FAIL"
    print(f"prove-red: {verdict}; {proof.summary()} ({proof.seconds:.1f} s)")
    return 0 if proof.ok else 1


# ---------------------------------------------------------------- git hooks

# The .githooks shims call `project.py hook <name>`. pre-commit is the staged subset of verify,
# commit-msg checks the subject and the trailers, pre-push keeps the default branch for merge.
# The fourth hook, reference-transaction, is plain sh: it guards every move of the default branch.
# `hook install` (mise's postinstall) points git at them, pins a second copy of that guard, and
# gives the guard its record of the default branch (record_main).
GATES = f"{PROCESS}#gates"
HOOKS = ("pre-commit", "commit-msg", "pre-push")
SCISSORS = "# ------------------------ >8 ------------------------"
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
ID_IN_TEXT_RE = re.compile(r"[a-z][a-z0-9-]*\.[a-z0-9][a-z0-9-]*")
SKIP_MARKS = ("skip", "skipif", "xfail")
# Calls that skip or xfail a test: (kind, position of a reason given without a keyword).
SKIP_CALLS = {
    "pytest.skip": ("skip()", 0),
    "pytest.skip.Exception": ("skip()", 0),
    "pytest.Skipped": ("skip()", 0),  # _pytest.outcomes.Skipped, what skip() raises
    "pytest.xfail": ("xfail()", 0),
    "pytest.xfail.Exception": ("xfail()", 0),
    "pytest.XFailed": ("xfail()", 0),  # _pytest.outcomes.XFailed, what xfail() raises
    "pytest.importorskip": ("importorskip()", None),
    "unittest.skip": ("skip", 0),
    "unittest.skipIf": ("skipif", 1),
    "unittest.skipUnless": ("skipif", 1),
    "unittest.SkipTest": ("skip()", 0),
}
SKIP_EXCEPTIONS = frozenset(  # raised as a class, without a call: a skip with no reason
    {"pytest.skip.Exception", "pytest.Skipped", "pytest.xfail.Exception", "pytest.XFailed"}
    | {"unittest.SkipTest"}
)
SKIP_DECORATORS = {"unittest.expectedFailure": "xfail"}  # used without a call: no reason, lax
QUALIFIED_ALIASES = (("_pytest.outcomes.", "pytest."), ("unittest.case.", "unittest."))
PY_SUFFIXES = (".py", ".pyi")
TY_EXPORT = ("pyproject.toml", "ty.toml", ".python-version")  # config ty reads beside the code
TOOL_TIMEOUT = 300  # seconds for one ruff, ty or gitleaks run inside a hook
SPEC_LANES_NEED_SPEC = ("feat", "chg", "fix")  # their commits that touch src name the scenarios
MISE_INSTALL = "run: mise install"
GIT_REVERT_RE = re.compile(r'^(?:Revert|Reapply) "(.+)"$')  # git revert, of a commit or a revert
GIT_FIXUP_RE = re.compile(r"^(?:fixup|squash|amend)! (.+)$")
HOOK_DEFAULT_RE = re.compile(r"^D=([^\s;]+);", re.MULTILINE)  # reference-transaction's D= line


GUARD_HOOK = ".githooks/reference-transaction"
GUARD_NAME = "project-main-guard"  # the config-defined hook that runs a pinned copy of it
PINNED_RE = re.compile(r"cat-file blob ([0-9a-f]{40,64})\)")  # the blob in guard_command()


def guard_command(blob: str) -> str:
    """The shell line git runs for hook.project-main-guard: the reference-transaction hook as
    the object store holds it (blob), so a command that rewrites the working tree before it
    moves a ref (reset --hard, merge, checkout -B) cannot drop or swap the guard it runs. It
    steps aside while the working tree's copy, which core.hooksPath runs, is that same blob
    and executable (git skips a hook file without the x bit)."""
    missing = "echo 'blocked: the main guard is not installed here: run mise install' >&2"
    return (
        f'[ "$(git config core.hooksPath)" = .githooks ] && [ -x {GUARD_HOOK} ] && '
        f'[ "$(git hash-object {GUARD_HOOK} 2>/dev/null)" = {blob} ] && exit 0; '
        f"s=$(git --no-replace-objects cat-file blob {blob}) || {{ {missing}; exit 1; }}; "
        f'sh -c "$s" {GUARD_NAME}'
    )


def guard_blob(root: Path, default: str) -> str | None:
    """The reference-transaction hook to pin: the default branch's committed copy, or, before
    the default branch has one (the bootstrap), the working tree's, written to the object store."""
    ref = f"refs/heads/{default}:{GUARD_HOOK}"
    out = git(root, "--no-replace-objects", "rev-parse", "-q", "--verify", ref)
    if out:
        return out.strip()
    if not (root / GUARD_HOOK).is_file():
        return None
    out = git(root, "hash-object", "-w", "--", GUARD_HOOK)
    return out.strip() if out else None


def gate_config(root: Path, default: str) -> list[tuple[str, str, str]]:
    """The local git config the gates need, as (key, value, value pattern for `git config
    --replace-all`); `hook install` sets it (mise's postinstall), doctor and merge check it.
    - core.hooksPath: the tracked hooks in .githooks/.
    - receive.hideRefs: a push into this repo itself runs receive-pack inside .git, where the
      relative hooks path finds no hook, so receive-pack refuses the default branch outright.
    - hook.project-main-guard: reference-transaction again, from a pinned blob (guard_command)."""
    blob = guard_blob(root, default)
    if blob is None:
        raise UsageError(f"{GUARD_HOOK} is missing: project-init writes it")
    ref = f"refs/heads/{default}"
    return [
        ("core.hooksPath", ".githooks", "."),
        ("receive.hideRefs", ref, f"^{re.escape(ref)}$"),
        (f"hook.{GUARD_NAME}.event", "reference-transaction", "."),
        (f"hook.{GUARD_NAME}.command", guard_command(blob), "."),
    ]


def install_gates(root: Path, default: str) -> list[str]:
    """Set gate_config() in this repo's local config, and give the guard its record of the
    default branch (record_main); the lines say what was set."""
    done = []
    for key, value, pattern in gate_config(root, default):
        proc = run_git(root, "config", "--replace-all", key, value, pattern)
        if proc.returncode != 0:
            raise UsageError(f"git config {key}: {plain(proc.stderr.decode('utf-8', 'replace'))}")
        done.append(f"{key} = {value if len(value) < 60 else value[:57] + '...'}")
    done.append(record_main(root, default))
    return done


# The guard's record of the default branch: where it was after the last ref update the guard
# saw. git branch -m/-c onto the default branch writes it without any hook, so the guard refuses
# every ref update while the branch is elsewhere, and doctor and merge report it.
MAIN_TIP = "project-main-tip"  # in the git common dir, next to the refs it describes


def main_tip_file(root: Path) -> Path | None:
    out = git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return Path(out.strip()) / MAIN_TIP if out else None


def recorded_main(root: Path) -> str | None:
    path = main_tip_file(root)
    text = read_text(path) if path else None
    return (text or "").strip() or None


def record_main(root: Path, default: str) -> str:
    """Write the guard's record when there is none (trust on first install: this is the moment
    a human sets the gates up). A record that disagrees with the branch is never overwritten
    here: that is the tripwire gate_setup_problems() reports."""
    path, tip = main_tip_file(root), rev(root, f"refs/heads/{default}")
    if path is None or tip is None:
        return f"{MAIN_TIP}: no {default} branch yet (its first update records it)"
    have = recorded_main(root)
    if have is None:
        path.write_text(tip + "\n", encoding="utf-8")
        return f"{MAIN_TIP} = {tip[:10]} ({default})"
    if have == tip:
        return f"{MAIN_TIP} = {tip[:10]} ({default}, as recorded)"
    return f"{MAIN_TIP}: kept {have[:10]}; {default} is at {tip[:10]} (see mise run doctor)"


def main_record_problem(root: Path, default: str) -> str | None:
    """The tripwire, as doctor and merge see it: the default branch is somewhere the guard never
    saw it move to (git branch -m/-c onto it, or a write into .git), or it has no record."""
    tip = rev(root, f"refs/heads/{default}")
    if tip is None:
        return None
    have = recorded_main(root)
    if have is None:
        return f"the main guard has no record of {default} ({tip[:10]}): run mise install"
    if have == tip:
        return None
    how = git(root, "reflog", "show", "-n", "1", "--format=%gs", f"refs/heads/{default}") or ""
    why = how.strip() or f"git branch -m/-c onto {default}, or a write into .git"
    return (
        f"{default} is at {tip[:10]}, but the main guard last saw it at {have[:10]} ({why}); "
        f"put it back: git update-ref refs/heads/{default} {have}"
    )


def z_paths(out: bytes) -> list[str]:
    """Paths from a `git ... -z` listing."""
    return [p for p in out.decode("utf-8", "surrogateescape").split("\0") if p]


def under(path: str, roots: list[str]) -> bool:
    return any(path == r or path.startswith(r.rstrip("/") + "/") for r in roots)


def plain(text: str) -> str:
    """Tool output without colour codes and blank lines."""
    lines = ANSI_RE.sub("", text).splitlines()
    return "\n".join(line.rstrip() for line in lines if line.strip())


def run_tool(
    argv: list[str], cwd: Path, env: dict[str, str], stdin: bytes | None = None
) -> subprocess.CompletedProcess[str]:
    """A tool run with a fixed argv (no shell) and a time limit; never raises."""
    try:
        proc = subprocess.run(  # noqa: S603
            argv,
            cwd=cwd,
            env=env,
            input=stdin,
            capture_output=True,
            check=False,
            timeout=TOOL_TIMEOUT,
        )
    except OSError as exc:
        return subprocess.CompletedProcess(argv, 127, "", f"cannot run {argv[0]}: {exc}")
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(argv, 124, "", f"{argv[0]} ran past {TOOL_TIMEOUT} s")
    out = proc.stdout.decode("utf-8", "replace")
    return subprocess.CompletedProcess(
        argv, proc.returncode, out, proc.stderr.decode("utf-8", "replace")
    )


@dataclass
class Staged:
    """The commit being made: the paths it changes and the scenarios before and after it.
    While a merge is being committed, a path whose staged content is what git's merge made of
    it, or MERGE_HEAD's copy, came from the merge, so the lane rules leave it alone. A path
    edited by hand during the merge (a conflict resolution included) is the commit's own."""

    paths: list[str]  # every path the commit changes: added, modified or deleted
    content: list[str]  # the ones it adds or modifies (--diff-filter=ACMR)
    merge_head: str | None
    from_merge: set[str]
    head: dict[str, Scenario]  # scenarios at HEAD (none before the first commit)
    index: dict[str, Scenario]  # scenarios as staged
    merged: dict[str, Scenario] | None  # scenarios at MERGE_HEAD
    merge_base: dict[str, Scenario] | None  # scenarios where HEAD and MERGE_HEAD forked

    def taken_from_merge(self, sid: str) -> bool:
        """True when the staged state of a scenario is what the merged branch did to it: its
        block as MERGE_HEAD has it, or removed there (present at the fork, gone at MERGE_HEAD)."""
        if self.merged is None or self.merge_base is None:
            return False
        if sid in self.index:
            return sid in self.merged and self.merged[sid].block == self.index[sid].block
        return sid not in self.merged and sid in self.merge_base

    @property
    def removed(self) -> list[str]:
        return sorted(sid for sid in self.head if sid not in self.index)


def load_staged(root: Path) -> Staged:
    """What `git commit` is about to record. Every read goes through the index git hands the
    hook (GIT_INDEX_FILE for `commit -a` and `commit <paths>`), so it is the commit's content."""

    def names(*extra: str) -> list[str]:
        out = run_git(root, "diff", "--cached", "--name-only", "--no-renames", "-z", *extra)
        return z_paths(out.stdout)

    paths = names()
    out = git(root, "rev-parse", "-q", "--verify", "MERGE_HEAD^{commit}")
    merge_head = out.strip() if out else None
    from_merge: set[str] = set()
    merged = merge_base = None
    if merge_head:
        from_merge = set(paths) - set(names(merge_head))
        # git's own merge result; with conflicts (exit 1) the tree holds the conflict markers
        out = run_git(root, "merge-tree", "--write-tree", "--no-messages", "HEAD", merge_head)
        tree = out.stdout.decode("utf-8", "replace").partition("\n")[0].strip()
        if out.returncode in (0, 1) and re.fullmatch(r"[0-9a-f]{40,64}", tree):
            from_merge |= set(paths) - set(names(tree))
        merged = scenarios_at(root, merge_head)
        fork = git(root, "merge-base", "HEAD", merge_head)
        merge_base = scenarios_at(root, fork.strip()) if fork else {}
    head = scenarios_at(root, "HEAD") if git(root, "rev-parse", "-q", "--verify", "HEAD") else {}
    return Staged(
        paths=paths,
        content=names("--diff-filter=ACMR"),
        merge_head=merge_head,
        from_merge=from_merge,
        head=head,
        index=scenarios_at(root, ""),
        merged=merged,
        merge_base=merge_base,
    )


@dataclass
class SkipMark:
    """A skip or xfail in a Python file: a marker (skip, skipif, xfail, or unittest's decorators),
    a call (skip(), xfail(), importorskip(), unittest's SkipTest and skipTest()), or one named by
    a string (named_skip)."""

    line: int
    kind: str
    reason: str
    strict: bool
    key: str  # the marker's code: a marker HEAD already had is not new


@dataclass
class TestMarks:
    tags: list[tuple[int, str]]  # (line, id) for each @pytest.mark.spec("<id>", ...) argument
    skips: list[SkipMark]


def qualified(node: ast.expr, names: dict[str, str]) -> str | None:
    """The dotted name an expression refers to, through the file's imports and plain aliases:
    `pt.skip` is pytest.skip after `import pytest as pt`, `skip` is pytest.skip after
    `from pytest import skip`. None for anything but a name or an attribute chain."""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    return public_name(".".join([names.get(node.id, node.id), *reversed(parts)]))


def bound_names(tree: ast.Module) -> dict[str, str]:
    """What each name in a file is bound to by its imports, and by `x = <name or attribute>`
    (two rounds, so an alias of an alias resolves too). Scopes are not told apart."""
    names: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update({a.asname: a.name for a in node.names if a.asname})
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names.update({a.asname or a.name: f"{node.module}.{a.name}" for a in node.names})
    assigns = [
        (node.targets[0].id, node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and isinstance(node.value, (ast.Name, ast.Attribute))
    ]
    for _ in range(2):
        for target, value in assigns:
            if (name := qualified(value, names)) is not None and name != target:
                names[target] = name
    return names


def mark_name(name: str | None) -> str | None:
    """'skip' for pytest.mark.skip (or mark.skip, however pytest or its mark was imported)."""
    if name is None or "." not in name:
        return None
    owner, _, attr = name.rpartition(".")
    return attr if mark_namespace(owner) else None


def mark_namespace(name: str) -> bool:
    """pytest.mark, however it was reached (_pytest.mark.MARK_GEN is the same object)."""
    return name == "mark" or name.endswith((".mark", "MARK_GEN"))


def folded(node: ast.expr, strings: dict[str, str]) -> str | None:
    """The value of a string built from literals: "skip", "sk" + "ip", an f-string without
    fields, or a name bound to one of those. None for anything else."""
    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, str) else None
    if isinstance(node, ast.Name):
        return strings.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = folded(node.left, strings), folded(node.right, strings)
        return None if left is None or right is None else left + right
    if isinstance(node, ast.JoinedStr):
        parts = [folded(value, strings) for value in node.values]
        return None if None in parts else "".join(p for p in parts if p is not None)
    return None


def bound_strings(tree: ast.Module) -> dict[str, str]:
    """Names bound to a string built from literals (`name = "sk" + "ip"`), in two rounds."""
    assigns = [
        (node.targets[0].id, node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
    ]
    assigns += [
        (node.target.id, node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value
    ]
    strings: dict[str, str] = {}
    for _ in range(2):
        for target, value in assigns:
            if (text := folded(value, strings)) is not None:
                strings[target] = text
    return strings


STRING_EXPRS = (ast.Constant, ast.BinOp, ast.JoinedStr)  # what a marker name in a string looks like
SKIP_OWNERS = ("pytest", "unittest")  # getattr() on these, or on pytest.mark, may reach a skip
NAMED_SKIP = "named"  # the kind of a skip or xfail reached through a string


def public_name(name: str) -> str:
    """pytest.skip for _pytest.outcomes.skip, unittest.skip for unittest.case.skip."""
    for internal, public in QUALIFIED_ALIASES:
        if name.startswith(internal):
            return public + name[len(internal) :]
        if name == internal.rstrip("."):
            return public.rstrip(".")
    return name


def named_skip(
    call: ast.Call, name: str | None, names: dict[str, str], strings: dict[str, str]
) -> bool:
    """True for a skip or xfail named by a string, which the reason rule cannot read:
    getattr(pytest.mark, "sk" + "ip"), pytest.mark.__getattr__("skip"), item.add_marker("skip"),
    request.applymarker("xfail"), pytest.Mark("skip", ...). getattr() on pytest's namespaces
    with a name that does not fold to a literal counts too: nothing can say what it reaches.
    A string computed some other way (a call, exec) is left to spec-check, which sees the run."""
    func, args = call.func, call.args
    if name == "getattr" and len(args) >= 2:
        owner, attr = qualified(args[0], names), args[1]
    elif (
        isinstance(func, ast.Attribute)
        and func.attr in ("__getattr__", "__getattribute__")
        and args
    ):
        owner, attr = qualified(func.value, names), args[0]
    elif (isinstance(func, ast.Attribute) and func.attr in ("add_marker", "applymarker")) or (
        name is not None and name.startswith(("pytest.", "_pytest.")) and name.endswith(".Mark")
    ):
        arg = args[0] if args else None
        if not isinstance(arg, (ast.Name, *STRING_EXPRS)):
            return False  # a marker object: its pytest.mark.<name> is read where it is made
        kind = folded(arg, strings)
        if kind is None:
            return not isinstance(arg, (ast.Name, ast.Constant))  # a string built at run time
        return kind in SKIP_MARKS
    else:
        return False
    text = folded(attr, strings)
    if text == "skipTest":
        return True  # getattr(self, "skipTest")
    if owner is None or not (owner in SKIP_OWNERS or mark_namespace(owner)):
        return False
    if text is None:
        return True
    full = f"{owner}.{text}"
    return mark_name(full) in SKIP_MARKS or full in SKIP_CALLS or full in SKIP_DECORATORS


def expr_text(node: ast.expr) -> str:
    """A string constant's value, or the code of any other expression (an f-string, a name)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return ast.unparse(node)


def skip_mark(call: ast.Call, kind: str, reason_at: int | None) -> SkipMark:
    """reason_at: the position of a reason passed without a keyword (skip("why")), if any."""
    reason = ""
    strict = False
    for keyword in call.keywords:
        if keyword.arg in ("reason", "msg"):
            reason = expr_text(keyword.value)
        elif keyword.arg == "strict":
            strict = isinstance(keyword.value, ast.Constant) and keyword.value.value is True
    if not reason and reason_at is not None and len(call.args) > reason_at:
        reason = expr_text(call.args[reason_at])
    return SkipMark(call.lineno, kind, reason, strict, f"{kind}|{ast.unparse(call)}")


def test_marks(text: str) -> TestMarks | None:
    """Spec tags and skip/xfail uses in a Python file; None when it does not parse (ruff says
    why). Names resolve through the file's imports, so `from pytest import skip` and `import
    pytest as pt` count the same as `pytest.skip`."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return None
    names = bound_names(tree)
    strings = bound_strings(tree)
    marks = TestMarks([], [])
    calls: set[int] = set()  # callee nodes already read as part of a call
    for node in ast.walk(tree):  # breadth first: a call comes before the name it calls
        if isinstance(node, ast.Call):
            calls.add(id(node.func))
            name = qualified(node.func, names)
            marker = mark_name(name)
            if marker == "spec":
                marks.tags += [
                    (node.lineno, arg.value)
                    for arg in node.args
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
                ]
            elif marker in SKIP_MARKS:
                marks.skips.append(skip_mark(node, marker, 0 if marker == "skip" else None))
            elif name in SKIP_CALLS:
                marks.skips.append(skip_mark(node, *SKIP_CALLS[name]))
            elif isinstance(node.func, ast.Attribute) and node.func.attr == "skipTest":
                marks.skips.append(skip_mark(node, "skip()", 0))  # unittest's self.skipTest()
            elif named_skip(node, name, names, strings):
                key = f"{NAMED_SKIP}|{ast.unparse(node)}"
                marks.skips.append(SkipMark(node.lineno, NAMED_SKIP, "", False, key))
        elif isinstance(node, ast.Raise) and isinstance(node.exc, (ast.Attribute, ast.Name)):
            name = qualified(node.exc, names)  # `raise Skipped`: the class itself, no reason
            if name in SKIP_EXCEPTIONS:
                kind = SKIP_CALLS[name][0]
                text = f"{kind}|{ast.unparse(node)}"
                marks.skips.append(SkipMark(node.lineno, kind, "", False, text))
        elif (
            isinstance(node, (ast.Attribute, ast.Name))
            and isinstance(node.ctx, ast.Load)
            and id(node) not in calls
        ):
            name = qualified(node, names)
            kind = mark_name(name) if isinstance(node, ast.Attribute) else None
            kind = kind if kind in SKIP_MARKS else SKIP_DECORATORS.get(name or "")
            if kind is not None:
                marks.skips.append(
                    SkipMark(node.lineno, kind, "", False, f"{kind}|{ast.unparse(node)}")
                )
    return marks


def unapproved_feat(ctx: Context) -> bool:
    """True on a feat/ branch with an open change that is not approved at HEAD yet: its folder
    is committed or staged, and HEAD's copy is not approved. Talk writes scenarios before their
    tests and approve commits them, so I4 starts once the change is approved. A feat/ branch
    with no change folder at all gets no such window."""
    if ctx.lane != "feat" or not ctx.slug:
        return False

    def ours(paths: list[str]) -> list[str]:
        """The change folders among paths (folders or files under them) that belong to slug."""
        found = []
        for path in paths:
            parts = PurePosixPath(path).parts
            name = parts[2] if len(parts) > 2 else ""
            match = CHANGE_DIR_RE.match(name)
            if match and match.group(1) == ctx.slug:
                found.append(f"{CHANGES_DIR}/{name}")
        return sorted(set(found))

    committed = ours(git_lines(ctx.root, "ls-tree", "--name-only", "HEAD", f"{CHANGES_DIR}/"))
    staged = ours(z_paths(run_git(ctx.root, "ls-files", "-z", "--", CHANGES_DIR).stdout))
    if not committed and not staged:
        return False
    texts = read_blobs(ctx.root, "HEAD", [f"{name}/requirements.md" for name in committed])
    statuses = [frontmatter(text)[0].get("status") for text in texts.values()]
    return "approved" not in statuses


def check_staged_lanes(ctx: Context, staged: Staged) -> list[str]:
    """I1, I2 and I5 on the files this commit changes."""
    paths = [p for p in staged.paths if p not in staged.from_merge]
    lane = ctx.lane
    tool = bool(os.environ.get("PROJECT_MERGE"))
    where = ctx.branch or "a detached HEAD"
    problems = []
    if MISSION in paths and lane != "plan":
        problems.append(
            f"I1: {MISSION} is staged on {where}; the mission changes only on plan/ branches"
        )
    if ROADMAP in paths and lane != "plan" and not tool:
        problems.append(
            f"I1: {ROADMAP} is staged on {where}; it changes on plan/ branches, and merge ticks it"
        )
    if CHANGELOG in paths and not tool and lane != "release" and ctx.branch != INIT_BRANCH:
        problems.append(f"I2: {CHANGELOG} is staged on {where}; only merge and release write it")
    folders = sorted(
        {p.split("/")[2] for p in paths if p.startswith(CHANGES_DIR + "/") and p.count("/") >= 3}
    )
    requirements = [f"{CHANGES_DIR}/{name}/requirements.md" for name in folders]
    for path, text in read_blobs(ctx.root, "HEAD", requirements).items():
        if frontmatter(text)[0].get("status") == "done":
            problems.append(
                f"I5: {PurePosixPath(path).parent} is done and frozen; this commit changes it"
            )
    return problems


def check_staged_scenarios(
    ctx: Context,
    staged: Staged,
    marks: dict[str, TestMarks],
    roots: tuple[list[str], list[str]],
) -> list[str]:
    """I4: a scenario added or modified in this commit comes with a staged test tagged with it;
    a scenario removed in it leaves no test tagged with it (commit-msg wants Spec-Removed:).
    roots: (source roots, test roots); the tests are the files in_tests() names."""
    problems = []
    head, index = staged.head, staged.index
    changed = {sid: "added" for sid in index if sid not in head}
    changed |= {
        sid: "modified" for sid in index if sid in head and index[sid].block != head[sid].block
    }
    if not unapproved_feat(ctx):
        tagged = {tag for m in marks.values() for _, tag in m.tags}
        for sid, kind in sorted(changed.items()):
            if sid in tagged or staged.taken_from_merge(sid):
                continue
            problems.append(
                f"I4: scenario {sid} is {kind} in this commit, but no staged test is tagged with "
                f'it; stage its test in the same commit (@pytest.mark.spec("{sid}"))'
            )
    removed = [sid for sid in staged.removed if not staged.taken_from_merge(sid)]
    if removed:
        listing = z_paths(run_git(ctx.root, "ls-files", "-z", "--", *roots[1], *roots[0]).stdout)
        tests = sorted({p for p in listing if p.endswith(".py") and in_tests(p, *roots)})
        for path, text in sorted(read_blobs(ctx.root, "", tests).items()):
            found = test_marks(text)
            for line, tag in found.tags if found else []:
                if tag in removed:
                    problems.append(
                        f"I4: scenario {tag} is removed in this commit, but {path}:{line} is "
                        "still tagged with it; delete its tests in the same commit"
                    )
    return problems


def check_staged_tests(
    staged: Staged, marks: dict[str, TestMarks], root: Path, roots: tuple[list[str], list[str]]
) -> list[str]:
    """Staged Python files: no tag in a test file (in_tests) names an unknown id; a new skip, in
    any file (a conftest.py or a plugin skips tests too), names a scenario in its reason; a new
    xfail is strict and names a [gap] scenario (specs/README.md, "Tests and commits")."""
    problems = []
    removed = set(staged.removed)
    gaps = {sid for sid, scenario in staged.index.items() if scenario.gap}
    before = read_blobs(root, "HEAD", list(marks))
    for path, found in sorted(marks.items()):
        for line, tag in found.tags if in_tests(path, *roots) else []:
            if tag not in staged.index and tag not in removed:
                problems.append(
                    f"{path}:{line}: unknown id '{tag}': no scenario in {CAPS_DIR}/ has it"
                )
        old = test_marks(before.get(path, ""))
        seen: dict[str, int] = {}
        for mark in old.skips if old else []:
            seen[mark.key] = seen.get(mark.key, 0) + 1
        for mark in found.skips:
            if seen.get(mark.key, 0) > 0:
                seen[mark.key] -= 1  # HEAD already had it
                continue
            named = [i for i in ID_IN_TEXT_RE.findall(mark.reason) if i in staged.index]
            where = f"{path}:{mark.line}"
            if mark.kind == NAMED_SKIP:
                problems.append(
                    f"{where}: a skip or xfail named by a string cannot be checked; write the "
                    'marker out, e.g. @pytest.mark.skip(reason="<cap>.<slug>: why")'
                )
            elif mark.kind == "xfail()":
                problems.append(
                    f"{where}: pytest.xfail() stops the test before it can turn red; a known gap "
                    'is @pytest.mark.xfail(strict=True, reason="<gap id>: ...")'
                )
            elif mark.kind == "xfail" and not (mark.strict and any(i in gaps for i in named)):
                problems.append(
                    f"{where}: a new xfail needs strict=True and a [gap] scenario id in its "
                    'reason: @pytest.mark.xfail(strict=True, reason="<gap id>: ...")'
                )
            elif mark.kind != "xfail" and not named:
                problems.append(
                    f"{where}: a new {mark.kind} needs a scenario id in its reason, "
                    'e.g. reason="<cap>.<slug>: why"'
                )
    return problems


def python_tools(root: Path) -> tuple[dict[str, str], str | None]:
    """The project's python, ruff and ty, found through one `uv run --locked` (which syncs the
    venv the way every mise task does), or why they cannot be found."""
    uv = uv_binary(root)
    if uv is None:
        return {}, f"uv is not installed on this machine: {MISE_INSTALL}"
    code = (
        "import shutil, sys; print(sys.executable); "
        "print(shutil.which('ruff') or ''); print(shutil.which('ty') or '')"
    )
    proc = run_uv(root, uv, ["run", "--locked", "--quiet", "python", "-c", code], tool_env())
    lines = proc.stdout.strip().splitlines()
    if proc.returncode != 0 or len(lines) != 3:
        return {}, f"cannot sync the project environment (uv run --locked):\n{plain(tail(proc))}"
    tools = dict(zip(("python", "ruff", "ty"), lines, strict=True))
    missing = [name for name in ("ruff", "ty") if not tools[name]]
    if missing:
        return (
            {},
            f"{' and '.join(missing)} missing from the dev dependencies: uv add --dev ruff ty",
        )
    return tools, None


def ruff_staged(root: Path, ruff: str, paths: list[str]) -> list[str]:
    """ruff check and ruff format --check on each staged copy, through stdin (H22): the working
    copy may be fixed while the commit still holds the broken one."""
    env = tool_env()
    problems = []
    for path in paths:
        blob = run_git(root, "show", f":{path}").stdout
        runs = (
            ("ruff check", ["check", "--no-fix", "--output-format", "concise"]),
            ("ruff format --check", ["format", "--check"]),
        )
        for label, args in runs:
            argv = [ruff, *args, "--force-exclude", "--stdin-filename", path, "-"]
            proc = run_tool(argv, root, env, stdin=blob)
            if proc.returncode != 0:
                said = plain(proc.stdout + proc.stderr) or "would reformat"
                if label == "ruff check" and " S101 " in said and a_test_path(path):
                    said += f"\n{UNSEEN_TESTS_HINT if test_file(path) else helper_hint(path)}"
                problems.append(f"{label} {path} (the staged copy):\n{said}")
    return problems


# render writes a per-file-ignores row (assert allowed) for each test folder it finds, and for
# the test_*.py beside the code in a folder; a test made after it may have none until the next
# render
UNSEEN_TESTS_HINT = (
    "hint: no per-file-ignores row of pyproject.toml covers this test yet: render writes the "
    "rows for the tests it finds (a test folder, or test_*.py beside the code), and this one "
    "came later. To add its row, re-render: init.py render (re-run /project-init)"
)


def helper_hint(path: str) -> str:
    """The hint for a helper or conftest.py in a test folder: a re-render writes rows for the
    test_*.py files only, so re-rendering would not cover this file."""
    folder = PurePosixPath(path).parent
    return (
        "hint: no per-file-ignores row of pyproject.toml covers this file, and a re-render "
        "adds rows for test_*.py files only. Add the folder's row by hand, above the "
        f'baseline mark in [tool.ruff.lint.per-file-ignores]: "{folder}/**" = ["S101"]'
    )


def a_test_path(path: str) -> bool:
    """A test by its name (test_file) or its folder (a tests/ or test/ folder on the way)."""
    return test_file(path) or bool({"tests", "test"} & set(PurePosixPath(path).parts[:-1]))


def ty_staged(root: Path, tools: dict[str, str], paths: list[str]) -> list[str]:
    """ty check on the staged files: in place when their working copies match the index, else
    on an export of the index (every tracked .py plus ty's config) into a temp dir."""
    argv = [tools["ty"], "check", "--python", tools["python"], "--output-format", "concise"]
    argv += ["--color", "never"]
    env = tool_env()
    if not git_lines(root, "diff", "--name-only", "--", *paths):
        proc = run_tool([*argv, *paths], root, env)
        where = "ty check"
    else:
        with tempfile.TemporaryDirectory(prefix="project-pre-commit-") as tmp:
            listing = z_paths(run_git(root, "ls-files", "-z").stdout)
            export = [
                p for p in listing if p.endswith(PY_SUFFIXES) or PurePosixPath(p).name in TY_EXPORT
            ]
            request = "\0".join(export).encode("utf-8", "surrogateescape")
            out = run_git(
                root, "checkout-index", "-z", "--stdin", f"--prefix={tmp}/", stdin=request
            )
            if out.returncode != 0:
                return [f"cannot export the index for ty: {plain(out.stderr.decode())}"]
            proc = run_tool([*argv, *paths], Path(tmp), env)
        where = "ty check (the staged copies; some files have unstaged edits)"
    if proc.returncode == 0:
        return []
    return [f"{where}:\n{plain(proc.stdout + proc.stderr)}"]


def gitleaks_staged(root: Path) -> list[str]:
    """The staged diff through gitleaks with this repo's .gitleaks.toml. There is no bypass: a
    machine without gitleaks cannot commit until `mise install` has run."""
    version = run_tool(["gitleaks", "version"], root, dict(os.environ))
    if version.returncode != 0:
        return [f"gitleaks is not installed on this machine: {MISE_INSTALL}"]
    argv = ["gitleaks", "git", "--pre-commit", "--staged", "--redact", "--no-banner", "--verbose"]
    proc = run_tool([*argv, "."], root, dict(os.environ))  # the env keeps git's GIT_INDEX_FILE
    if proc.returncode == 0:
        return []
    keep = ("Finding", "RuleID", "File", "Line", "Fingerprint", "leaks found", "ERR", "FTL")
    said = [
        line
        for line in plain(proc.stdout + proc.stderr).splitlines()
        if any(k in line for k in keep)
    ]
    return [
        "gitleaks found a secret, a personal path or a wiki-link in the staged changes "
        "(rules: .gitleaks.toml):\n" + "\n".join(said or [plain(tail(proc))])
    ]


def hook_pre_commit(ctx: Context) -> list[str]:
    """The staged subset of verify (specs/README.md#gates): lane rules I1, I2, I4, I5; proof
    files against their README entries (I24); tags in staged tests; skips and xfails in every
    staged .py; ruff and ty on the staged copies; gitleaks on the diff."""
    root = ctx.root
    staged = load_staged(root)
    if not staged.paths:
        return []
    roots = committed_paths(root)
    scanned = [p for p in staged.content if p.endswith(".py") and p not in staged.from_merge]
    texts = read_blobs(root, "", scanned)
    marks = {p: found for p in scanned if (found := test_marks(texts.get(p, ""))) is not None}
    tests = {p: found for p, found in marks.items() if in_tests(p, *roots)}
    problems: list[str] = []
    if git_lines(root, "for-each-ref", "--count=1", "refs/heads"):  # not the first commit
        problems += check_staged_lanes(ctx, staged)
        problems += check_staged_scenarios(ctx, staged, tests, roots)
    problems += check_staged_proof(ctx, staged)
    problems += check_staged_tests(staged, marks, root, roots)
    python = [p for p in staged.content if p.endswith(PY_SUFFIXES)]
    if python:
        tools, why = python_tools(root)
        if why:
            problems.append(why)
        else:
            problems += ruff_staged(root, tools["ruff"], python)
            problems += ty_staged(root, tools, python)
    problems += gitleaks_staged(root)
    return problems


def comment_string(root: Path) -> str:
    """What starts a comment line in a commit message: core.commentString or core.commentChar
    (git -c included, which the hook inherits), '#' by default. `auto` picks one of `#;@!$%^&|:`
    per message; no conventional subject starts with any of them, so '#' stands in for it."""
    for key in ("core.commentString", "core.commentChar"):
        value = (git(root, "config", key) or "").rstrip("\n")
        if value and value != "auto":
            return value
    return "#"


def message_text(raw: str, comment: str = "#") -> str:
    """A commit message as git stores it under the strip cleanup (an edited message, by
    default): comment lines and everything below the scissors line of `commit -v` left out."""
    lines = []
    for line in raw.splitlines():
        if line.startswith(f"{comment} {SCISSORS[2:]}"):
            break
        if not line.startswith(comment):
            lines.append(line)
    return "\n".join(lines).strip() + "\n"


def message_subjects(raw: str, comment: str = "#") -> list[str]:
    """The subject git stores, under each cleanup a commit may use (the hook cannot tell which
    one it gets): strip, the default for an edited message, drops comment lines; whitespace,
    the default for -m and -F, verbatim and scissors keep them, so a first line such as
    '# update stuff' is the subject there. Each one must be conventional."""
    stripped = next(
        (ln.strip() for ln in message_text(raw, comment).splitlines() if ln.strip()), ""
    )
    kept = next((ln.strip() for ln in message_text(raw, "\0").splitlines() if ln.strip()), "")
    return [stripped] if kept in ("", stripped) else [kept, stripped]


def conventional_subject(subject: str) -> bool:
    """A conventional subject, or one git writes around a conventional one: `Revert "<subject>"`
    and `Reapply "<subject>"` (git revert) or `fixup! `, `squash! ` and `amend! ` in front of it
    (commit --fixup). The subject inside is checked too, so a wrapper never lets any text in."""
    if TITLE_RE.match(subject):
        return True
    match = GIT_REVERT_RE.match(subject) or GIT_FIXUP_RE.match(subject)
    return bool(match) and conventional_subject(match.group(1))


def hook_commit_msg(ctx: Context, args: list[str]) -> list[str]:
    """Conventional subject; Spec:, Spec-Guard: and Spec-Removed: name real scenarios; a removed
    scenario is named in Spec-Removed: (I4); Test-Harness: has a reason; on feat/, chg/ and fix/
    a commit that touches src says which scenarios it serves."""
    if not args:
        raise UsageError("hook commit-msg needs the message file")
    root = ctx.root
    raw = read_text(Path(args[0])) or ""
    comment = comment_string(root)
    text = message_text(raw, comment)
    subjects = message_subjects(raw, comment)
    staged = load_staged(root)
    merging = staged.merge_head is not None
    problems = []
    for subject in subjects:
        if (merging and subject.startswith("Merge ")) or conventional_subject(subject):
            continue
        wrapped = GIT_REVERT_RE.match(subject) or GIT_FIXUP_RE.match(subject)
        kept = len(subjects) > 1 and subject == subjects[0]
        dropped = len(subjects) > 1 and subject == subjects[1]
        problems.append(
            f"'{subject}' is not a conventional subject: <type>(<scope>)!: <summary>, with a type "
            "from feat change fix perf refactor build ci docs test chore spec style revert"
            + (
                "\nthe subjects git revert and commit --fixup write need a conventional subject "
                "inside; to revert a commit whose subject is not one, write: revert: <summary>"
                if wrapped
                else ""
            )
            + (
                f"\nit starts with the comment string '{comment}': git keeps it as the subject "
                "under -m, -F and --cleanup=verbatim|whitespace|scissors; put the subject first"
                if kept
                else ""
            )
            + (
                f"\ngit drops the lines that start with '{comment}' (core.commentChar) under "
                "--cleanup=strip, so this line becomes the subject there"
                if dropped
                else ""
            )
        )
    trailers = run_git(root, "interpret-trailers", "--parse", stdin=text.encode()).stdout.decode()
    spec = split_ids(trailer_values(trailers, "Spec"))
    guard = split_ids(trailer_values(trailers, "Spec-Guard"))
    gone = split_ids(trailer_values(trailers, "Spec-Removed"))
    for key, ids in (("Spec", spec), ("Spec-Guard", guard)):
        for sid in ids:
            if sid not in staged.index:
                problems.append(f"{key}: {sid} is not a scenario in {CAPS_DIR}/ (as staged)")
    for sid in gone:
        if sid not in staged.head:
            problems.append(f"Spec-Removed: {sid} is not a scenario at HEAD")
        elif sid in staged.index:
            problems.append(f"Spec-Removed: {sid} is still in {CAPS_DIR}/ (as staged)")
    for sid in staged.removed:
        if sid not in gone and not staged.taken_from_merge(sid):
            problems.append(
                f"I4: scenario {sid} is removed in this commit; add the trailer "
                f"'Spec-Removed: {sid}'"
            )
    if any(not value for value in trailer_values(trailers, "Test-Harness")):
        problems.append("Test-Harness: needs a reason ('Test-Harness: <what the edit is for>')")
    src_roots, test_roots = committed_paths(root)
    touched = [  # a test inside a source root (src/pkg/tests, a test_*.py beside the code)
        p
        for p in staged.paths
        if under(p, src_roots)
        and not in_tests(p, src_roots, test_roots)
        and p not in staged.from_merge
    ]
    if ctx.lane in SPEC_LANES_NEED_SPEC and touched and not (spec or gone):
        problems.append(
            f"a {ctx.lane}/ commit that touches {', '.join(src_roots)} needs a 'Spec: <ids>' "
            f"trailer naming the scenarios it serves (or 'Spec-Removed: <ids>'); it touches "
            f"{touched[0]}" + (f" and {len(touched) - 1} more" if len(touched) > 1 else "")
        )
    return problems


def guarded_branches(ctx: Context) -> list[str]:
    """The branches pre-push keeps for merge: the default branch reference-transaction was
    rendered with (its D= line, in the working tree's copy and in the copy `hook install`
    pinned), and the one .project.toml names. The working tree can add a branch here, never
    take the rendered one away."""
    texts = []
    hook = git(ctx.root, "rev-parse", "--git-path", "hooks/reference-transaction")
    if hook:
        texts.append(read_text(ctx.root / hook.strip()) or "")
    pinned = PINNED_RE.search(git(ctx.root, "config", f"hook.{GUARD_NAME}.command") or "")
    if pinned:
        texts.append(git(ctx.root, "cat-file", "blob", pinned.group(1)) or "")
    names = [ctx.default]
    for text in texts:
        match = HOOK_DEFAULT_RE.search(text)
        if match and match.group(1) not in names:
            names.append(match.group(1))
    return names


def hook_pre_push(ctx: Context, args: list[str]) -> list[str]:
    """Pushes to the default branch belong to merge (PROJECT_MERGE). The one other push allowed
    is the bootstrap: the remote has no such branch yet and the local default branch goes up."""
    remote = args[0] if args else "the remote"
    updates = sys.stdin.read().splitlines()  # read it all, even when nothing is checked
    if os.environ.get("PROJECT_MERGE"):
        return []
    guarded = {f"refs/heads/{name}": name for name in guarded_branches(ctx)}
    problems = []
    for line in updates:
        parts = line.split()
        if len(parts) != 4 or parts[2] not in guarded:
            continue
        local_ref, local_sha, remote_ref, remote_sha = parts
        out = git(ctx.root, "rev-parse", "-q", "--verify", f"{remote_ref}^{{commit}}")
        if set(remote_sha) == {"0"} and out and local_sha == out.strip():
            continue  # bootstrap: the remote lacks the branch, and ours goes up as it is
        problems.append(
            f"blocked: {guarded[remote_ref]} on {remote} moves only via 'mise run merge' "
            f"(pushing {local_ref})"
        )
    return problems


def cmd_hook(ctx: Context, args: argparse.Namespace) -> int:
    rest = list(args.args)
    if args.name in CLAUDE_HOOKS:  # main() takes the plain call; this is `hook <name> <extra>`
        return claude_hook(args.name, read_stdin())
    if args.name == "install":
        for line in install_gates(ctx.root, ctx.default):
            print(f"hook install: {line}")
        return 0
    if args.name == "pre-commit":
        problems = hook_pre_commit(ctx)
    elif args.name == "commit-msg":
        problems = hook_commit_msg(ctx, rest)
    else:
        problems = hook_pre_push(ctx, rest)
    if not problems:
        return 0
    for problem in problems:
        first, *more = problem.splitlines()
        print(f"{args.name}: {first}", file=sys.stderr)
        for line in more:
            print(f"    {line}", file=sys.stderr)
    print(
        f"{args.name}: blocked ({plural(len(problems), 'problem')}); see {GATES}", file=sys.stderr
    )
    return 1


# ---------------------------------------------------------------- Claude Code hooks

# .claude/settings.json runs `project.py hook session-start` when a session starts and
# `project.py hook pre-bash` before each Bash tool call, each with Claude Code's hook JSON on
# stdin. $CLAUDE_PROJECT_DIR stays at the session's root, so this file is also the launcher:
# when the input's cwd sits in another worktree of this repo that has its own scripts/project.py,
# that copy runs instead, with the same stdin. pre-bash exits 2 to block a command, and Claude
# Code shows its one stderr line to the agent. Any other outcome lets the command run, so a
# malformed input or a broken hook fails open while the git gates still hold. session-start
# always exits 0: its stdout is the session's derived state, tail-capped at 3 KB.
CLAUDE_HOOKS = ("session-start", "pre-bash")
LAUNCHED = "PROJECT_PY_LAUNCHED"  # set on a re-exec: a launched copy never launches another
BLOCK = 2  # the exit code with which a PreToolUse hook blocks the tool call
SCRIPT_READ_CAP = 256 * 1024  # bytes of a script file pre-bash reads
SCRIPT_DEPTH = 3  # shell scripts that run shell scripts, followed this deep
SESSION_CAP = 3 * 1024  # bytes of the session-start block
SESSION_LINE_CAP = 300  # characters of one line in it
NEWEST_LESSONS = 5
NEWEST_DECISIONS = 3
LESSONS_FILE = "project_memory/lessons.md"
DECISIONS_DIR = "project_memory/decisions"
LESSON_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2}) \| (.+?)\s*$")
TITLE_H1_RE = re.compile(r"^# (.+?)\s*$")

HUMAN_GATE = "approve, merge, abandon and release are human gates: a person runs them in a terminal"
PRE_BASH_DENY: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"PROJECT_MERGE"), "PROJECT_MERGE is set only by merge, abandon and release"),
    (
        re.compile(
            r"\bmise\s+(?:(?:-C|--cd)\s+\S+\s+|-\S+\s+)*"
            r"(?:(?:run|r|watch|w)\s+(?:-\S+\s+)*|tasks\s+run\s+(?:-\S+\s+)*)?"
            r"(?:approve|merge|abandon|release)\b"
        ),
        HUMAN_GATE,
    ),
    (
        re.compile(r"project\.py['\"]?\s+(?:-\S+\s+)*(?:approve|merge|abandon|release)\b"),
        HUMAN_GATE,
    ),
    (re.compile(r"--no-veri"), "--no-verify skips the git gates"),  # git takes --no-veri too
    (
        re.compile(
            r"\bgit\s+(?:-\S+\s+(?:[^-\s]\S*\s+)?)*?commit\b[^\n;&|]*?\s-[aeiopqsvz]*n[A-Za-z]*\b"
        ),
        "git commit -n skips the git gates",
    ),
    (re.compile(r"(?i)core\.hookspath"), "core.hooksPath is what points git at the gates"),
    (
        re.compile(  # hook.<name>.<key>, or a whole hook.<name> section; never a file hook.py
            r"(?i)(?:(?<![^\s'\"=])hook\.[\w-]+\.[\w.-]*[\w-]|-section\s+['\"]?hook\.[\w.-]+)"
        ),
        "a hook.* config key runs, or switches off, the pinned main guard",
    ),
    (
        re.compile(r"GIT_CONFIG_(?:COUNT|KEY_|VALUE_|PARAMETERS|GLOBAL|SYSTEM)"),
        "GIT_CONFIG_* sets git config past the gates",
    ),
    # The git config the main guard trusts (insteadOf rules, HOME) is judged by command
    # structure in config_hit(), never by text: a commit message may name insteadOf.
    (re.compile(r"\bsend-pack\b"), "git send-pack pushes without the pre-push gate"),
    (re.compile(r"\.githooks\b"), ".githooks/ holds the git gates"),
    (re.compile(r"\.git/(?:hooks|config)\b"), ".git/hooks and .git/config hold the gate config"),
    (re.compile(r"\bgh\s+pr\s+merge\b"), "a pull request lands through `mise run merge`"),
    (
        re.compile(r"\bgh\s+repo\s+(?:edit|delete|rename|archive)\b"),
        "the repo's settings are a person's call",
    ),
    (re.compile(r"\bgh\s+ruleset\b"), "the branch rulesets are a person's call"),
)
GH_API_RE = re.compile(r"\bgh\s+api\b([^\n;&|]*)")
GH_API_FIELDS = ("-f", "-F", "--field", "--raw-field", "--input")
GH_API_FIELD_PREFIXES = ("-f", "-F", "--field=", "--raw-field=", "--input=")  # -fkey=v, --field=k=v

# The main guard follows the url.<base>.insteadOf rules and core.sshCommand of the user's and
# the system's git config (~/.gitconfig, found through HOME) when it confirms a sync from
# origin: a rule there can point origin at another repo, so that config is a person's.
# config_hit() reads each command's structure for what writes or picks it: a git config write
# in the user's or the system's scope, or of an insteadOf key; git -c with an insteadOf key;
# HOME or XDG_CONFIG_HOME set for git, a shell or the rest of the command line; a write to such
# a file by any other program. A read, echo or printf that names it writes nothing, as long as
# what it prints reaches only the terminal: printed into a $(...), a pipe to another program
# (xargs) or a file, the name can become a write's argument. Text inside a word never counts:
# a commit message may name it.
GUARD_HOME_VARS = frozenset({"HOME", "XDG_CONFIG_HOME"})
EXPORTS = frozenset({"export", "declare", "typeset", "readonly", "local"})
INSTEADOF_KEY_RE = re.compile(r"(?i)^url\..*\.(?:push)?insteadof(?:=|$)")
GIT_GLOBAL_VALUES = frozenset(
    {"-C", "--git-dir", "--work-tree", "--namespace", "--super-prefix", "--attr-source"}
)
GIT_CONFIG_VALUES = frozenset({"--blob", "--type", "--default", "--comment", "--value", "--url"})
GIT_CONFIG_VERBS = {  # git config <verb> (git 2.46 and later): True when the verb writes
    "get": False,
    "list": False,
    "set": True,
    "unset": True,
    "edit": True,
    "rename-section": True,
    "remove-section": True,
}
PERSON_CONFIG = "the user's and the system's git config are a person's (the main guard trusts them)"
INSTEADOF_WHY = "a url.<base>.insteadOf rule can point origin at another repo; a person writes it"
HOME_WHY = "HOME and XDG_CONFIG_HOME pick the git config the main guard trusts"
PRINTS = frozenset({"echo", "printf", "test", "["})  # their words are never files they write
SUBST = "$SUBST"  # the word a $(...) becomes while config_hit() reads the command around it

# The read-only exemption: a command whose every part is one of these reads runs even when its
# text names a pattern above (grep -n PROJECT_MERGE, git config --get core.hooksPath).
SHELL_PUNCT = ";&|()<>\n"
SUBSTITUTION_RE = re.compile(r"\$\(|`|<\(|>\(")
READS: dict[str, tuple[str, ...]] = {  # a read, and the option prefixes that make it more
    "cat": (),
    "head": (),
    "tail": (),
    "grep": (),
    "ls": (),
    "wc": (),
    "stat": (),
    "diff": (),
    "cd": (),
    "less": ("-o", "-O", "--log-file", "--LOG-FILE"),
    "file": ("-C", "--compile"),
    "rg": ("--pre",),
}
FIND_WRITES = frozenset(
    {"-exec", "-execdir", "-ok", "-okdir", "-delete", "-fprint", "-fprint0", "-fprintf", "-fls"}
)
SED_ADDRESS = r"(?:\d+|\$|/[^/]*/)"
SED_PRINT_RE = re.compile(
    rf"^{SED_ADDRESS}(?:,{SED_ADDRESS})?p(?:;{SED_ADDRESS}(?:,{SED_ADDRESS})?p)*;?$"
)
GIT_READS = ("log", "show", "diff", "status", "rev-parse", "ls-files")
GIT_CONFIG_READS = frozenset({"--get", "--get-all", "--get-regexp", "-l", "--list"})
GIT_CONFIG_WRITES = (
    "--add",
    "--unset",
    "--replace-all",
    "--rename-section",
    "--remove-section",
    "-e",
    "--edit",
)
GIT_BRANCH_WRITES = (
    "-d",
    "-D",
    "--delete",
    "-m",
    "-M",
    "--move",
    "-c",
    "-C",
    "--copy",
    "-f",
    "--force",
    "-u",
    "--set-upstream-to",
    "--unset-upstream",
    "--edit-description",
    "-t",
    "--track",
    "--no-track",
)

# Script indirection: a script file inside the repo or a temp dir, run by one of these, is read
# (up to 256 KB) and held to the same patterns.
SHELLS = frozenset({"sh", "bash", "zsh", "dash", "ksh"})
PYTHON_RE = re.compile(r"^python(?:\d+(?:\.\d+)*)?$")
SHELL_KEYWORDS = frozenset({"{", "}", "!", "if", "then", "else", "elif", "fi", "do", "done"})
SHELL_KEYWORDS_LOOP = frozenset({"while", "until"})
WRAPPERS = frozenset({"env", "command", "exec", "nohup", "time", "builtin", "nice", "timeout"})
WRAPPER_VALUE_RE = re.compile(r"^[\d.]+[smhd]?$")  # timeout 5, nice 10
ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
PYTHON_VALUES = frozenset({"-W", "-X", "-Q"})
NODE_VALUES = frozenset({"-r", "--require", "--import", "--loader", "--experimental-loader"})
NODE_CODE = frozenset({"-e", "--eval", "-p", "--print"})
UV_RUN_VALUES = frozenset(
    {
        "--with",
        "-w",
        "--with-editable",
        "--with-requirements",
        "--python",
        "-p",
        "--directory",
        "--project",
        "--package",
        "--extra",
        "--group",
        "--only-group",
        "--no-group",
        "--env-file",
        "--index",
        "--default-index",
        "--index-url",
        "--extra-index-url",
        "--find-links",
        "-f",
        "-i",
        "--config-file",
        "--cache-dir",
    }
)


def read_stdin() -> bytes:
    stream = sys.stdin
    if stream is None or stream.isatty():
        return b""
    try:
        return stream.buffer.read()
    except (OSError, ValueError):
        return b""


def claude_hook(name: str, raw: bytes) -> int:
    """A Claude Code hook. It never exits 2 by accident: an error lets the command run (pre-bash
    exits 1, which Claude Code shows the user) and session-start prints it into the block."""
    try:
        return run_claude_hook(name, raw)
    except Exception as exc:  # noqa: BLE001 - a broken hook must never block every Bash call
        why = f"{type(exc).__name__}: {exc}"
        if name == "session-start":
            print(f"[project.py] session-start failed ({why}); run: mise run status")
            return 0
        print(f"project.py hook {name}: {why}; the command was not checked", file=sys.stderr)
        return 1


def hook_payload(raw: bytes) -> dict[str, object] | None:
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def common_dir(root: Path) -> str | None:
    out = git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return os.path.realpath(out.strip()) if out else None


def serves_claude_hooks(script: Path) -> bool:
    """True when a project.py knows both Claude hooks: an older copy would read `hook pre-bash`
    as a usage error, and argparse's exit 2 would block every Bash call."""
    try:
        text = script.read_bytes()
    except OSError:
        return False
    return all(f'"{name}"'.encode() in text for name in CLAUDE_HOOKS)


def run_claude_hook(name: str, raw: bytes) -> int:
    payload = hook_payload(raw)
    if payload is None and name == "pre-bash":
        return 0  # malformed input fails open; the git gates still hold
    payload = payload or {}
    here = Path(__file__).resolve()
    given = payload.get("cwd")
    cwd = Path(given) if isinstance(given, str) and given and Path(given).is_dir() else Path.cwd()
    own = find_root(here.parent)
    at = find_root(cwd)
    same = at is not None and own is not None and same_path(at, own)
    worktree = at is not None and (own is None or same or common_dir(at) == common_dir(own))
    if at is not None and own is not None and worktree and not same:
        other = at / "scripts" / "project.py"
        if not os.environ.get(LAUNCHED) and other.is_file() and serves_claude_hooks(other):
            sys.stdout.flush()
            proc = subprocess.run(  # noqa: S603 - this repo's own gate script, fixed argv
                [sys.executable, str(other), "hook", name],
                input=raw,
                cwd=at,
                env={**os.environ, LAUNCHED: str(other)},
                check=False,
            )
            return proc.returncode
    if name == "pre-bash":
        roots = [r for r in (at, own) if r is not None]
        reason = pre_bash(payload, cwd, roots)
        if reason is None:
            return 0
        print(f"pre-bash: blocked {reason} (see {GATES})", file=sys.stderr)
        return BLOCK
    root = at if at is not None and worktree else own or at
    if root is None:
        print("[project.py] session-start: not inside a git repository")
        return 0
    print(session_block(load_context(root)), end="")
    return 0


# -- pre-bash


def pre_bash(payload: dict[str, object], cwd: Path, roots: list[Path]) -> str | None:
    """Why pre-bash blocks the Bash call in a PreToolUse payload; None lets it run. roots: the
    repos whose script files it reads (the temp dirs are added)."""
    if payload.get("tool_name", "Bash") != "Bash":
        return None
    tool_input = payload.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str) or not command.strip():
        return None
    return bash_verdict(command, cwd, roots)


def bash_verdict(command: str, cwd: Path, roots: list[Path]) -> str | None:
    commands = shell_commands(command)
    if commands is not None and read_only(command, commands):
        return None
    hit = denied_text(command) or config_hit(command)
    if hit:
        return f"`{hit[0]}`: {hit[1]}"
    parsed = commands if commands is not None else naive_commands(command)
    return script_reason(parsed, cwd, [*roots, *temp_dirs()], 0, set())


def snippet(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= 60 else text[:57] + "..."


def denied_text(text: str) -> tuple[str, str] | None:
    """(what matched, why) for the first deny pattern the text holds, or None."""
    for pattern, why in PRE_BASH_DENY:
        match = pattern.search(text)
        if match:
            return snippet(match.group(0)), why
    return gh_api_write(text)


def gh_api_write(text: str) -> tuple[str, str] | None:
    """A `gh api` call that writes: a method other than GET, or fields without -X GET (gh then
    sends a POST)."""
    for match in GH_API_RE.finditer(text):
        try:
            words = shlex.split(match.group(1))
        except ValueError:
            words = match.group(1).split()
        words = [w.strip("'\"") for w in words]
        method: str | None = None
        fields = False
        for index, word in enumerate(words):
            if word in ("-X", "--method"):
                method = words[index + 1] if index + 1 < len(words) else ""
            elif word.startswith("--method="):
                method = word.split("=", 1)[1]
            elif word.startswith("-X") and len(word) > 2:
                method = word[2:]
            elif word in GH_API_FIELDS or word.startswith(GH_API_FIELD_PREFIXES):
                fields = True
        verb = (method or ("POST" if fields else "GET")).upper()
        if verb != "GET":
            return snippet(match.group(0)), f"gh api {verb} writes to GitHub; a person does that"
    return None


def config_hit(text: str, depth: int = 0, terminal: bool = True) -> tuple[str, str] | None:
    """(what, why) when a command line writes or picks the git config the main guard trusts
    (see GUARD_HOME_VARS), judged by the structure of each command; the command texts that
    sh -c, eval and $(...) run are read the same way, SCRIPT_DEPTH deep. terminal: what the
    text prints reaches only the terminal, as far as the command around it goes."""
    outer, inner = fold_substitutions(text)
    tokens = shell_tokens(outer)
    commands = None if tokens is None else token_commands(tokens)
    parsed = commands if commands is not None else naive_commands(outer)
    terminal = terminal and tokens is not None and to_terminal(tokens, parsed)
    texts = [(part, False) for part in inner]  # a $(...) prints into the command around it
    for words in parsed:
        why = command_config_problem(words, terminal)
        if why:
            return snippet(" ".join(words).replace(SUBST, "$(...)")), why
        texts += [(part, terminal) for part in script_runs(argv_of(words)[0])[1]]
    for part, printed in texts if depth < SCRIPT_DEPTH else []:
        if hit := config_hit(part, depth + 1, printed):
            return hit
    return None


def to_terminal(tokens: list[str], commands: list[list[str]]) -> bool:
    """True when what a command line prints reaches only the terminal: no redirection into a
    file (/dev/null and 2>&1 aside), and a pipe only into reads and prints (grep, wc, head),
    which pass it on to the terminal. Then the words of a print or a read there are no write's
    arguments; printed into a pipe to xargs or into a file, they can be."""
    if any(argv_of(words)[1] for words in commands):
        return False
    piped = any(is_operator(token) and "|" in token.replace("||", "") for token in tokens)
    return not piped or all(prints_or_reads(words) for words in commands)


def prints_or_reads(words: list[str]) -> bool:
    """A simple command that only prints or reads (echo, cat, grep -n), or one with no program
    (an assignment, or the } that closes a group)."""
    program = prefix_assignments(argv_of(words)[0])[1]
    name = program[0].rsplit("/", 1)[-1] if program else ""
    if name == "printf" and any(word.startswith("-v") for word in program[1:]):
        return False  # printf -v stores into a variable a later command can write through
    return not program or name in PRINTS or is_read([name, *program[1:]])


def fold_substitutions(text: str) -> tuple[str, list[str]]:
    """text with each $(...), `...`, <(...) and >(...) outside single quotes turned into the
    one word SUBST, and the texts they held, each a command line of its own. So
    `HOME=$(mktemp -d) uv run pytest` stays one command that sets HOME for uv."""
    out: list[str] = []
    inner: list[str] = []
    single = double = False
    index, size = 0, len(text)
    while index < size:
        char = text[index]
        opens = text.startswith(("$(", "<(", ">("), index) and (char == "$" or not double)
        if single:
            single = char != "'"
        elif char == "\\":
            out.append(text[index : index + 2])
            index += 2
            continue
        elif char == "'" and not double:
            single = True
        elif char == '"':
            double = not double
        elif char == "`" or opens:
            start = index + (1 if char == "`" else 2)
            end = text.find("`", start) if char == "`" else closing_paren(text, start)
            end = size if end < 0 else end
            inner.append(text[start:end])
            out.append(SUBST)
            index = end + 1
            continue
        out.append(char)
        index += 1
    return "".join(out), inner


def closing_paren(text: str, start: int) -> int:
    """The index of the ) that closes the ( just before start, quoted text skipped; -1 when
    there is none."""
    depth = 0
    index = start
    while index < len(text):
        char = text[index]
        if char in "'\"":
            end = text.find(char, index + 1)
            if end < 0:
                return -1
            index = end + 1
            continue
        if char == "\\":
            index += 2
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            if depth == 0:
                return index
            depth -= 1
        index += 1
    return -1


def prefix_assignments(argv: list[str]) -> tuple[set[str], list[str]]:
    """(the variables a simple command sets for its program: VAR=value words before it, also
    past env and the other wrappers; the program's argv), as program_argv() walks it."""
    names: set[str] = set()
    index = 0
    while index < len(argv):
        word = argv[index]
        if ASSIGNMENT_RE.match(word):
            names.add(word.split("=", 1)[0])
            index += 1
        elif word in SHELL_KEYWORDS or word in SHELL_KEYWORDS_LOOP:
            index += 1
        elif word in WRAPPERS:
            index += 1
            while index < len(argv) and (
                argv[index].startswith("-")
                or ASSIGNMENT_RE.match(argv[index])
                or WRAPPER_VALUE_RE.match(argv[index])
            ):
                if ASSIGNMENT_RE.match(argv[index]):
                    names.add(argv[index].split("=", 1)[0])
                index += 1
        else:
            break
    return names, argv[index:]


def command_config_problem(words: list[str], terminal: bool = False) -> str | None:
    """Why one simple command (its words, redirections included) writes or picks the git
    config the main guard trusts; None when it does neither. terminal: what it prints reaches
    only the terminal (to_terminal), so a print's or a read's words name no file it writes."""
    argv, _ = argv_of(words)
    names, program = prefix_assignments(argv)
    name = program[0].rsplit("/", 1)[-1] if program else ""
    if name in EXPORTS:
        names |= {word.split("=", 1)[0] for word in program[1:] if ASSIGNMENT_RE.match(word)}
    # a standalone assignment or an export holds for the rest of the command line; a shell,
    # eval or source runs command texts that no longer show the assignment
    runs_more = not program or name in EXPORTS or name in SHELLS or name in ("eval", "source", ".")
    if names & GUARD_HOME_VARS and (name == "git" or runs_more):
        return HOME_WHY
    written = [nxt for op, nxt in pairwise(words) if ">" in op and is_operator(op)]
    given = [nxt for op, nxt in pairwise(words) if op == "<<<"]  # a here-string: xargs's input
    # a git word is a message or a ref, and the words of a read or a print whose output reaches
    # only the terminal are no write
    # a bare assignment prints nothing: its value can reach a later write (f=~/.gitconfig; cp x "$f")
    reads = name == "git" or (terminal and bool(program) and prints_or_reads(words))
    paths = written if reads else [*written, *given, *argv]
    if any(person_config_path(word) for word in paths):
        return PERSON_CONFIG
    return git_config_problem(program[1:]) if name == "git" else None


def person_config_path(word: str) -> bool:
    """A path of the user's or the system's git config: ~/.gitconfig (and a .gitconfig.<x>
    it includes), /etc/gitconfig, or <dir>/git/config such as ~/.config/git/config (never a
    repo's .git/config). A word with a space in it is prose, such as a message, not a path."""
    if not word or any(char.isspace() for char in word):
        return False
    parts = [part for part in word.split("/") if part]
    if not parts:
        return False
    return (
        parts[-1] == "gitconfig"
        or parts[-1].startswith(".gitconfig")
        or parts[-2:] == ["git", "config"]
    )


def git_config_problem(args: list[str]) -> str | None:
    """Why a git command (its arguments past `git`) writes or picks the git config the main
    guard trusts: -c or --config-env with an insteadOf key; git config writing in the user's or
    the system's scope (--global, --system, or a --file that is such a file), or writing an
    insteadOf key in any scope."""
    index = 0
    while index < len(args) and args[index].startswith("-"):
        arg = args[index]
        setting: str | None = None
        if arg in ("-c", "--config-env"):
            setting = args[index + 1] if index + 1 < len(args) else ""
            index += 1
        elif arg.startswith("--config-env="):
            setting = arg.split("=", 1)[1]
        elif arg.startswith("-c"):
            setting = arg[2:]
        elif arg in GIT_GLOBAL_VALUES:
            index += 1
        index += 1
        if setting is not None and INSTEADOF_KEY_RE.match(setting):
            return INSTEADOF_WHY
    if index >= len(args) or args[index] != "config":
        return None
    return config_write_problem(args[index + 1 :])


def config_write_problem(args: list[str]) -> str | None:
    """Why `git config <args>` writes the git config the main guard trusts (see
    git_config_problem); None for a read or a write elsewhere. Both forms count: the verbs
    (`git config set --global k v`) and the flags (`git config --global k v`, `--unset`)."""
    person = False
    verb: str | None = None
    action: bool | None = None  # True: a flag that writes; False: a flag that reads
    positionals: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        nxt = args[index + 1] if index + 1 < len(args) else ""
        if arg in ("--global", "--system"):
            person = True
        elif arg in ("-f", "--file"):
            person = person or person_config_path(nxt)
            index += 1
        elif arg.startswith("--file="):
            person = person or person_config_path(arg.split("=", 1)[1])
        elif arg in GIT_CONFIG_VALUES:
            index += 1
        elif arg in GIT_CONFIG_READS or arg.startswith("--get"):
            action = False if action is None else action
        elif arg.startswith(GIT_CONFIG_WRITES):
            action = True
        elif arg.startswith("-"):
            pass
        elif verb is None and not positionals and arg in GIT_CONFIG_VERBS:
            verb = arg
        else:
            positionals.append(arg)
        index += 1
    if verb is not None:
        writes = GIT_CONFIG_VERBS[verb]
    else:
        writes = action if action is not None else len(positionals) >= 2  # `k v` sets, `k` gets
    if not writes:
        return None
    if person:
        return PERSON_CONFIG
    if any(INSTEADOF_KEY_RE.match(word) for word in positionals):
        return INSTEADOF_WHY
    return None


def shell_commands(text: str) -> list[list[str]] | None:
    """The simple commands of a shell text as word lists, split at ; & | ( ) and newlines. A
    redirection stays in its command as operator words ('2', '>', '/dev/null'). None when the
    text does not tokenize (an open quote)."""
    tokens = shell_tokens(text)
    return None if tokens is None else token_commands(tokens)


def shell_tokens(text: str) -> list[str] | None:
    """A shell text's words and operator runs (';', '|', '2', '>'), or None when it does not
    tokenize (an open quote)."""
    lexer = shlex.shlex(text, posix=True, punctuation_chars=SHELL_PUNCT)
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        return list(lexer)
    except ValueError:
        return None


def token_commands(tokens: list[str]) -> list[list[str]]:
    """shell_commands() from shell_tokens()."""
    commands: list[list[str]] = [[]]
    for token in tokens:
        if token and not token.strip(SHELL_PUNCT) and not set(token) & {"<", ">"}:
            if commands[-1]:
                commands.append([])
            continue
        commands[-1].append(token)
    return [words for words in commands if words]


def naive_commands(text: str) -> list[list[str]]:
    """shell_commands() for a text shlex cannot read: split at the operators and spaces."""
    parts = re.split(r"[;&|()\n]+", text.replace('"', " ").replace("'", " "))
    return [part.split() for part in parts if part.split()]


def is_operator(word: str) -> bool:
    return bool(word) and not word.strip(SHELL_PUNCT)


def argv_of(words: list[str]) -> tuple[list[str], bool]:
    """(the words without their redirections, True when a redirection writes a file or opens a
    here-document). Writing to /dev/null or duplicating a descriptor (2>&1) writes nothing."""
    argv: list[str] = []
    writes = False
    index = 0
    while index < len(words):
        word = words[index]
        if not is_operator(word):
            argv.append(word)
            index += 1
            continue
        target = words[index + 1] if index + 1 < len(words) else ""
        if "<<" in word and "<<<" not in word:
            writes = True  # a here-document: its body lines read as commands here
        elif ">" in word and target != "/dev/null":
            duplicate = word.endswith("&") and (target.isdigit() or target == "-")
            writes = writes or not duplicate
        if argv and argv[-1].isdigit():
            argv.pop()  # the descriptor number of 2> or 1>&2
        index += 2
    return argv, writes


def read_only(text: str, commands: list[list[str]]) -> bool:
    """True when every part of the command is a known read with no redirection into a file."""
    if SUBSTITUTION_RE.search(text):
        return False
    for words in commands:
        argv, writes = argv_of(words)
        if writes or not is_read(argv):
            return False
    return True


def is_read(argv: list[str]) -> bool:
    if not argv:
        return True
    name, args = argv[0], argv[1:]
    if name in READS:
        banned = READS[name]
        return not any(arg.startswith(banned) for arg in args) if banned else True
    if name == "find":
        return not any(arg in FIND_WRITES for arg in args)
    if name == "sed":
        return sed_prints(args)
    if name == "git":
        return git_reads(args)
    return False


def sed_prints(args: list[str]) -> bool:
    """sed -n with only print scripts (10,20p or /re/p), and no -i: a sed that reads."""
    quiet = False
    scripts: list[str] = []
    files: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        nxt = args[index + 1] if index + 1 < len(args) else ""
        if arg in ("-n", "--quiet", "--silent"):
            quiet = True
        elif arg in ("-e", "--expression"):
            scripts.append(nxt)
            index += 1
        elif arg.startswith("--expression="):
            scripts.append(arg.split("=", 1)[1])
        elif arg in ("--regexp-extended", "--separate", "--null-data", "--unbuffered", "--posix"):
            pass
        elif arg.startswith("-") and not arg.startswith("--") and len(arg) > 1:
            letters = arg[1:]
            for at, letter in enumerate(letters):
                if letter == "n":
                    quiet = True
                elif letter == "e":
                    rest = letters[at + 1 :]
                    scripts.append(rest or nxt)
                    index += 0 if rest else 1
                    break
                elif letter not in "Ersuz":
                    return False
        elif arg.startswith("-") and arg != "-":
            return False
        else:
            files.append(arg)
        index += 1
    if not scripts and files:
        scripts.append(files.pop(0))
    return quiet and bool(scripts) and all(SED_PRINT_RE.match(s) for s in scripts)


def git_reads(args: list[str]) -> bool:
    """git log, show, diff, status, rev-parse, ls-files, ls-remote, config --get, branch
    --list: the read-only git commands, with no option that writes or runs something."""
    index = 0
    while index < len(args) and args[index].startswith("-"):
        if args[index] == "-C" and index + 1 < len(args):
            index += 2
        elif args[index] in ("--no-pager", "-P"):
            index += 1
        else:
            return False  # -c, --config-env, --git-dir and the rest
    if index >= len(args):
        return False
    sub, rest = args[index], args[index + 1 :]
    if sub in GIT_READS:
        return not any(arg.startswith("--output") for arg in rest)
    if sub == "ls-remote":
        return not any(arg.startswith(("--upload-pack", "-u")) for arg in rest)
    if sub == "config":
        return any(arg in GIT_CONFIG_READS for arg in rest) and not any(
            arg.startswith(GIT_CONFIG_WRITES) for arg in rest
        )
    if sub == "branch":
        return any(arg in ("--list", "-l") for arg in rest) and not any(
            arg in GIT_BRANCH_WRITES or arg.startswith(("--set-upstream-to=", "--track="))
            for arg in rest
        )
    return False


def temp_dirs() -> list[Path]:
    found: list[Path] = []
    for raw in (os.environ.get("TMPDIR"), tempfile.gettempdir(), "/tmp", "/var/tmp", "/dev/shm"):  # noqa: S108
        if raw and os.path.isdir(raw):
            path = Path(os.path.realpath(raw))
            if path not in found:
                found.append(path)
    return found


def program_argv(argv: list[str]) -> list[str]:
    """argv past shell keywords, VAR=value words and wrappers (env, command, exec, nohup, time,
    nice, timeout): the program that runs, and its arguments."""
    index = 0
    while index < len(argv):
        word = argv[index]
        if word in SHELL_KEYWORDS or word in SHELL_KEYWORDS_LOOP or ASSIGNMENT_RE.match(word):
            index += 1
        elif word in WRAPPERS:
            index += 1
            while index < len(argv) and (
                argv[index].startswith("-")
                or ASSIGNMENT_RE.match(argv[index])
                or WRAPPER_VALUE_RE.match(argv[index])
            ):
                index += 1
        else:
            break
    return argv[index:]


def script_runs(argv: list[str]) -> tuple[list[tuple[str, str]], list[str]]:
    """What a simple command runs besides its own program: ([(file, kind)], [command text]).
    kind is 'shell' for a file a shell reads, 'exec' for a file run directly (its #! line
    decides), 'code' for python and node files; command texts come from sh -c and eval."""
    argv = program_argv(argv)
    if not argv:
        return [], []
    name, args = argv[0].rsplit("/", 1)[-1], argv[1:]
    if name == "eval":
        return [], [" ".join(args)]
    if name in ("source", "."):
        return ([(args[0], "shell")] if args else []), []
    if name in SHELLS:
        return shell_script(args)
    if PYTHON_RE.match(name):
        return interpreter_file(args, ("-c", "-m"), PYTHON_VALUES), []
    if name == "node":
        return interpreter_file(args, NODE_CODE, NODE_VALUES), []
    if name == "uv" and args[:1] == ["run"]:
        rest = args[1:]
        script = "--script" in rest
        index = 0
        while index < len(rest) and rest[index].startswith("-"):
            index += 2 if rest[index] in UV_RUN_VALUES else 1
        rest = rest[index:]
        if rest and (script or rest[0].endswith(".py")):
            return [(rest[0], "code")], []
        return script_runs(rest) if rest else ([], [])
    if "/" in argv[0]:
        return [(argv[0], "exec")], []
    return [], []


def shell_script(args: list[str]) -> tuple[list[tuple[str, str]], list[str]]:
    files: list[tuple[str, str]] = []
    index = 0
    while index < len(args):
        arg = args[index]
        nxt = args[index + 1] if index + 1 < len(args) else None
        if arg.startswith("-") and not arg.startswith("--") and "c" in arg[1:]:
            return files, [nxt] if nxt is not None else []  # sh -c '<command>'
        if arg in ("--rcfile", "--init-file") and nxt is not None:
            files.append((nxt, "shell"))
            index += 2
        elif arg in ("-o", "+o", "-O", "+O"):
            index += 2
        elif arg == "--":
            return files + ([(nxt, "shell")] if nxt is not None else []), []
        elif arg.startswith(("-", "+")):
            index += 1
        else:
            return [*files, (arg, "shell")], []
    return files, []


def interpreter_file(
    args: list[str], code: frozenset[str] | tuple[str, ...], values: frozenset[str]
) -> list[tuple[str, str]]:
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in code or any(arg.startswith(c) and len(c) == 2 and len(arg) > 2 for c in code):
            return []  # python -c, python -m, node -e: code on the command line (read above)
        if arg in values:
            index += 2
        elif arg == "--":
            return [(args[index + 1], "code")] if index + 1 < len(args) else []
        elif arg.startswith("-"):
            index += 1
        else:
            return [(arg, "code")]
    return []


def script_path(word: str, cwd: Path, roots: list[Path]) -> Path | None:
    """The file a script word names, when it lies inside one of roots (by its own path or by
    where a symlink leads)."""
    raw = os.path.expanduser(os.path.expandvars(word))
    path = Path(os.path.normpath(raw if os.path.isabs(raw) else cwd / raw))
    try:
        real = path.resolve()
        if not real.is_file():
            return None
    except OSError:
        return None
    for candidate in (path, real):
        if any(candidate.is_relative_to(root) for root in roots):
            return real
    return None


def is_this_script(path: Path) -> bool:
    """The running project.py, or a byte-identical copy: the gate script itself, protected by
    the Edit deny rules and merge's gate-file check, reads its own patterns by design."""
    here = Path(__file__).resolve()
    if path == here:
        return True
    try:
        return path.stat().st_size == here.stat().st_size and path.read_bytes() == here.read_bytes()
    except OSError:
        return False


def moved(cwd: Path, args: list[str]) -> Path:
    """Where `cd <args>` leaves a command that runs after it."""
    target = args[-1] if args else "~"
    raw = os.path.expanduser(os.path.expandvars(target))
    path = Path(os.path.normpath(raw if os.path.isabs(raw) else cwd / raw))
    return path if path.is_dir() else cwd


def script_reason(
    commands: list[list[str]], cwd: Path, roots: list[Path], depth: int, seen: set[Path]
) -> str | None:
    """The deny reason for a script file these commands run (sh, bash, zsh, source, ., python,
    uv run, node, or the file itself), read up to 256 KB. Shell scripts are followed into the
    scripts they run, SCRIPT_DEPTH deep."""
    for words in commands:
        argv = program_argv(argv_of(words)[0])
        if argv[:1] == ["cd"]:
            cwd = moved(cwd, argv[1:])
            continue
        files, texts = script_runs(argv)
        for text in texts if depth < SCRIPT_DEPTH else []:
            inner = shell_commands(text)
            found = script_reason(
                inner if inner is not None else naive_commands(text), cwd, roots, depth + 1, seen
            )
            if found:
                return found
        for word, kind in files:
            path = script_path(word, cwd, roots)
            if path is None or path in seen or is_this_script(path):
                continue
            seen.add(path)
            try:
                with path.open("rb") as handle:
                    data = handle.read(SCRIPT_READ_CAP)
            except OSError:
                continue
            text = data.decode("utf-8", "replace")
            first = text.split("\n", 1)[0]
            shell = kind == "shell" or (kind == "exec" and first.startswith("#!") and "sh" in first)
            # what a script prints goes where its caller sends it, which is not seen here
            hit = denied_text(text) or (config_hit(text, terminal=False) if shell else None)
            if hit:
                inside = roots and path.is_relative_to(roots[0])
                shown = path.relative_to(roots[0]).as_posix() if inside else str(path)
                return f"`{hit[0]}` in {shown}: {hit[1]}"
            if shell and depth < SCRIPT_DEPTH:
                inner = shell_commands(text)
                found = script_reason(
                    inner if inner is not None else naive_commands(text),
                    cwd,
                    roots,
                    depth + 1,
                    seen,
                )
                if found:
                    return found
    return None


# -- session-start


def lesson_lines(root: Path, count: int) -> list[tuple[str, str]]:
    """(date, line) of the newest lessons in project_memory/lessons.md, oldest first. The file
    is append-only with a union merge, so the date orders them; file order breaks a tie."""
    entries: list[list[str]] = []  # [date, title, rule]
    for line in (read_text(root / LESSONS_FILE) or "").splitlines():
        match = LESSON_RE.match(line)
        if match:
            entries.append([match.group(1), match.group(2), ""])
        elif entries and line.startswith("Rule:") and not entries[-1][2]:
            entries[-1][2] = line[len("Rule:") :].strip()
    ordered = [e for _, e in sorted(enumerate(entries), key=lambda pair: (pair[1][0], pair[0]))]
    return [
        (date, f"- {date} {title}" + (f" | Rule: {rule}" if rule else ""))
        for date, title, rule in ordered[-count:]
    ]


def decision_lines(root: Path, count: int) -> list[tuple[str, str]]:
    """(date, line) of the newest active ADRs in project_memory/decisions/, oldest first."""
    folder = root / DECISIONS_DIR
    found: list[tuple[str, str]] = []
    for path in sorted(folder.glob("*.md")) if folder.is_dir() else []:
        text = read_text(path) or ""
        fields, _ = frontmatter(text)
        if fields.get("status", "").split()[:1] != ["active"]:
            continue
        lines = text.splitlines()
        if lines and lines[0].strip() == "---":
            closing = next((i for i, l in enumerate(lines[1:], 1) if l.strip() == "---"), 0)
            lines = lines[closing + 1 :]
        title = next((m.group(1) for l in lines if (m := TITLE_H1_RE.match(l))), path.stem)
        date = path.name[:10] if DATE_PREFIX_RE.match(path.name) else ""
        found.append((date, f"- {date} {title} ({path.name})".replace("-  ", "- ")))
    found.sort(key=lambda entry: entry[0])
    return found[-count:]


def clip(line: str) -> str:
    return line if len(line) <= SESSION_LINE_CAP else line[: SESSION_LINE_CAP - 3] + "..."


def render_session(
    head: list[str],
    lessons: list[tuple[str, str]],
    decisions: list[tuple[str, str]],
    cap: int = SESSION_CAP,
) -> str:
    """The block, tail-capped at cap bytes: while it is over, the oldest lesson or decision goes
    first, so the newest entries survive; a head still over keeps its last cap bytes."""
    lessons, decisions = list(lessons), list(decisions)

    def text() -> str:
        lines = [clip(line) for line in head]
        if lessons:
            lines += [f"lessons (newest {len(lessons)}):", *(clip(l) for _, l in lessons)]
        if decisions:
            lines += [
                f"decisions (active, newest {len(decisions)}):",
                *(clip(l) for _, l in decisions),
            ]
        return "\n".join(lines) + "\n"

    out = text()
    while len(out.encode()) > cap and (lessons or decisions):
        pool = [
            (entries[0][0], which) for which, entries in enumerate((lessons, decisions)) if entries
        ]
        (lessons, decisions)[min(pool)[1]].pop(0)
        out = text()
    data = out.encode()
    if len(data) > cap:
        out = data[-cap:].decode("utf-8", "ignore").split("\n", 1)[-1]
    return out


def mise_trusted(root: Path) -> bool | None:
    """False when mise reports a config here untrusted, None when mise does not run."""
    proc = run_cmd(["mise", "trust", "--show"], root, lifecycle_env(), timeout=30)
    if proc.returncode != 0:
        return None
    return not any(
        line.rstrip().endswith(": untrusted") for line in plain(proc.stdout).splitlines()
    )


def session_next(ctx: Context, state: State | None) -> str:
    """What comes next on this branch, from the change folder and the last test run."""
    if state is None:
        return f"no {SPECS}/ folder (run /project-init)"
    results = load_results(ctx.root)
    verdicts: dict[str, str] = {}
    if isinstance(results, Results):
        verdicts = check_trace(state, results, strict=False)
        seen = f"results {local_time(results.finished)}"
        if not results.complete:
            seen += ", partial"
        elif stale_files(ctx.root, results) != []:
            seen += ", stale"
    else:
        seen = results
    change = state.open_change
    if change is not None and change.status == "draft":
        fails = [text for level, text in approve_lint(state, change).lines if level == "FAIL"]
        if fails:
            return (
                f"draft spec, {plural(len(fails), 'problem')} before approve "
                f"(mise run spec-check -- --change {change.slug})"
            )
        return "the spec is ready for approve: a person runs `! mise run approve`"
    if change is not None and change.status == "approved":
        group = next_group(change, verdicts)
        if group is None:
            return f"every group has passing tests ({seen}): /sdd validate, then status --merge"
        missing = [sid for sid in group.ids if verdicts.get(sid) != "proven"]
        return f"G{group.number} {group.name}: {' '.join(missing)} (no passing tests; {seen})"
    if change is not None:
        return f"change {change.slug} is {change.status or 'without a status'}"
    if ctx.on_default:
        busy = open_changes(ctx)
        if busy:
            return f"finish {busy[0]} first (`git switch {busy[0]}`): one change at a time (I8)"
        pending = [slug for slug, done in state.roadmap.items() if not done]
        if pending:
            return f'roadmap item {pending[0]} (start it: /sdd "{pending[0]}")'
        return "the roadmap has no open item"
    return "`mise run status` has the details"


def session_head(ctx: Context) -> list[str]:
    """The fixed lines of the session block: where this branch stands, then a WARNING line for
    each thing that is off (git gates, mise trust, gitleaks, the default branch, the audit)."""
    warnings: list[str] = []
    state = load_state(ctx) if (ctx.root / SPECS).is_dir() else None
    change = state.open_change if state is not None else None
    parts = [f"[{ctx.name}] {ctx.branch or 'detached HEAD'}"]
    if ctx.on_default:
        busy = open_changes(ctx)  # what `change` would refuse on (I8)
        parts.append(f"change open on {', '.join(busy)}" if busy else "no open change")
    elif change is not None:
        parts.append(f"change {change.slug} ({change.status or 'no status'})")
    elif ctx.lane:
        parts.append(f"lane {ctx.lane}, no change folder")
    else:
        parts.append("not a lane branch")
    gates = gate_setup_problems(ctx)
    parts.append("hooks OFF" if gates else "hooks on")
    warnings += [f"WARNING: git gates off: {problem}" for problem in gates[:3]]
    trusted = mise_trusted(ctx.root)
    parts.append(
        {True: "mise trusted", False: "mise UNTRUSTED", None: "mise NOT RUNNABLE"}[trusted]
    )
    if trusted is False:
        warnings.append(
            "WARNING: mise does not trust this repo's config, so its shims (uv, gitleaks) fail "
            "here: run `mise trust`, then `mise install`"
        )
    elif trusted is None:
        warnings.append(
            "WARNING: mise does not run here: the git hooks fail closed and the Claude hooks are "
            "off; install mise, then run `mise install`"
        )
    if run_cmd(["gitleaks", "version"], ctx.root, lifecycle_env(), timeout=30).returncode != 0:
        warnings.append(
            "WARNING: gitleaks is not runnable here, so pre-commit refuses every commit: run "
            "`mise install`"
        )
    if ctx.head and rev(ctx.root, f"refs/heads/{ctx.default}") is None:
        warnings.append(
            f"WARNING: the default branch {ctx.default} is missing here; only a person "
            f"recreates it ({GATES})"
        )
    _, origin_problem = landing_mode(ctx)
    if origin_problem:
        warnings.append(f"WARNING: merge will refuse to land: {origin_problem}")
    flagged, summary = audit_lines(ctx)
    warnings += [f"WARNING: audit: {text}" for text in flagged[:3]]
    if len(flagged) > 3:
        warnings.append(f"WARNING: audit: {len(flagged) - 3} more (mise run status -- --audit)")
    dirty = len(git_lines(ctx.root, "status", "--porcelain"))
    return [
        " | ".join(parts),
        *warnings,
        f"next: {session_next(ctx, state)} | dirty: {dirty}",
        *(summary or [f"audit {ctx.default}: unavailable"]),
    ]


def session_block(ctx: Context) -> str:
    """The SessionStart block: derived from git, the specs and the last test run, never from a
    log. AGENTS.md is not repeated: Claude Code loads it natively."""
    return render_session(
        session_head(ctx),
        lesson_lines(ctx.root, NEWEST_LESSONS),
        decision_lines(ctx.root, NEWEST_DECISIONS),
    )


# ---------------------------------------------------------------- selftest

# `mise run selftest`: the gate matrix of specs/README.md#gates, run for real in a scratch clone
# of this repo (committed state plus the working tree's files) with a bare origin next to it.
# Every refusal case must be refused for its own reason, every allowed case must pass; a case
# that behaves otherwise fails the selftest. The fixture moves the default branch only under
# PROJECT_MERGE, the way merge does.
SELFTEST_USER = ("project selftest", "selftest@example.invalid")
FAKE_AWS_ID = "AKIA" + "QYLPMN5HHHFPZAM2"  # split, so this file never matches the rule itself
SELFTEST_NOTE = "SELFTEST.md"
FROZEN_CHANGE = f"{CHANGES_DIR}/2000-01-01-selftest-frozen"
SELFTEST_SCENARIOS = {
    "selftest.kept": ("the selftest runs", "this scenario stays"),
    "selftest.dropped": ("a case removes this scenario", "its tests go in the same commit"),
    "selftest.gap [gap: selftest-gap]": ("the selftest runs", "this known gap stays open"),
    "selftest.added": ("a case adds this scenario", "its test comes in the same commit"),
}
BLOCKED = "moves only via 'mise run merge'"
HINT = "check git status"  # every refusal of the main guard tells what git may have done already
GUARDED = (BLOCKED, HINT)
MISSING = ("is missing here", HINT)
TRIPPED = ("moved without an update the guard saw", HINT)  # the guard's record of main disagrees
WEAK_GUARD = "#!/bin/sh\n# selftest: a guard that lets every ref move through\nexit 0\n"
# pre-bash's cases (specs/README.md#gates): (command, True when pre-bash must block it). x.sh is
# written into the clone first, so `bash ./x.sh` runs a script that sets PROJECT_MERGE.
PRE_BASH_SCRIPT = ("x.sh", "#!/bin/sh\nPROJECT_MERGE=1 git merge x\n")
PRE_BASH_CASES = (
    ("mise run merge", True),
    ('sh -c "PROJECT_MERGE=1 git merge x"', True),
    (f"bash ./{PRE_BASH_SCRIPT[0]}", True),
    ("git -c core.hooksPath=/dev/null commit", True),
    ("git -c core.hookspath=/dev/null commit", True),
    ("git -c hook.project-main-guard.enabled=false branch -f main x", True),
    ("git send-pack origin feat/x:main", True),
    ("gh api -X PUT repos/o/r/pulls/1/merge", True),
    ("gh api -X DELETE repos/o/r/branches/main/protection", True),
    ("cp /tmp/h .githooks/pre-commit", True),
    ("grep -n PROJECT_MERGE scripts/project.py", False),
    ("git config --get core.hooksPath", False),
    ("grep -- --no-verify specs/README.md", False),
    ("mise run test -- -k merge", False),
)
LAUNCH_MARK = "selftest: the worktree's own project.py ran"


def selftest_capability(*headers: str) -> str:
    blocks = [
        f"### Scenario: {h}\n- WHEN {SELFTEST_SCENARIOS[h][0]}\n- THEN {SELFTEST_SCENARIOS[h][1]}\n"
        for h in headers
    ]
    return (
        "# Capability: selftest\n\n## Requirement: Gate probes\n"
        "The selftest SHALL keep scenarios to add, change and remove.\n\n" + "\n".join(blocks)
    )


def selftest_tests(*ids: str, head: str = "") -> str:
    """A ruff- and ty-clean test file with one test per id; head goes above the tests."""
    text = '"""Written by `project.py selftest`."""\n\nimport pytest\n' + head
    for sid in ids:
        name = sid.split(".", 1)[1].replace("-", "_")
        text += f'\n\n@pytest.mark.spec("{sid}")\ndef test_{name}() -> None:\n    """{sid}."""\n'
    return text


class SelftestError(Exception):
    """A fixture step failed, so the cases that need it cannot run."""


@dataclass
class CaseResult:
    name: str
    ok: bool
    detail: str
    seconds: float


class Selftest:
    def __init__(self, ctx: Context, tmp: Path) -> None:
        self.ctx = ctx
        self.tmp = tmp
        self.d = ctx.default
        self.main = f"refs/heads/{ctx.default}"
        self.origin = tmp / "origin.git"
        self.v = tmp / "v"
        src_roots, test_roots = project_paths(ctx.root)
        self.src = src_roots[0]
        self.tests = test_roots[0]
        self.results: list[CaseResult] = []
        self.timing = 0.0  # seconds of one src commit through pre-commit and commit-msg
        config = tmp / "gitconfig"  # the user's global git config stays out of the matrix
        config.write_text(
            "[commit]\n\tgpgsign = false\n[tag]\n\tgpgsign = false\n[gc]\n\tauto = 0\n"
            "[maintenance]\n\tauto = false\n[advice]\n\tdetachedHead = false\n",
            encoding="utf-8",
        )
        env = {
            k: v
            for k, v in os.environ.items()
            if not k.startswith("GIT_") and k not in ("PROJECT_MERGE", *SCRUB_ENV)
        }
        trusted = os.pathsep.join(p for p in (str(tmp), env.get("MISE_TRUSTED_CONFIG_PATHS")) if p)
        env.update(
            GIT_CONFIG_GLOBAL=str(config),
            GIT_CONFIG_NOSYSTEM="1",
            GIT_AUTHOR_NAME=SELFTEST_USER[0],
            GIT_AUTHOR_EMAIL=SELFTEST_USER[1],
            GIT_COMMITTER_NAME=SELFTEST_USER[0],
            GIT_COMMITTER_EMAIL=SELFTEST_USER[1],
            GIT_TERMINAL_PROMPT="0",
            MISE_TRUSTED_CONFIG_PATHS=trusted,
        )
        self.env = env

    # -- running things

    def run(
        self,
        *argv: str,
        cwd: Path | None = None,
        extra: dict[str, str] | None = None,
        stdin: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = {**self.env, **(extra or {})}
        try:
            return subprocess.run(  # noqa: S603
                list(argv),
                cwd=cwd or self.v,
                env=env,
                input=stdin,
                capture_output=True,
                text=True,
                check=False,
                timeout=600,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return subprocess.CompletedProcess(list(argv), 127, "", str(exc))

    def must(
        self,
        *argv: str,
        cwd: Path | None = None,
        extra: dict[str, str] | None = None,
        stdin: str | None = None,
    ) -> str:
        proc = self.run(*argv, cwd=cwd, extra=extra, stdin=stdin)
        if proc.returncode != 0:
            said = plain(proc.stdout + proc.stderr).splitlines()[-4:]
            raise SelftestError(f"`{' '.join(argv)}` failed: {' | '.join(said)}")
        return proc.stdout

    def rev(self, ref: str, where: Path | None = None) -> str | None:
        proc = self.run("git", "rev-parse", "-q", "--verify", f"{ref}^{{commit}}", cwd=where)
        return proc.stdout.strip() or None

    def case(
        self,
        name: str,
        allowed: bool,
        *argv: str,
        cwd: Path | None = None,
        extra: dict[str, str] | None = None,
        needle: str | tuple[str, ...] | None = None,
        guard: str | None = None,
        guard_in: Path | None = None,
    ) -> bool:
        """One matrix row. allowed: the command exits 0. Refused: it exits non-zero, its output
        holds needle, or each needle of a tuple (so the gate meant to refuse it did, and said
        all it should), and guard (a ref, read in guard_in) did not move."""
        where = guard_in or cwd or self.v
        before = self.rev(guard, where) if guard else None
        start = time.monotonic()
        proc = self.run(*argv, cwd=cwd, extra=extra)
        seconds = time.monotonic() - start
        said = plain(proc.stdout + proc.stderr)
        short = " | ".join(said.splitlines()[-4:]) or "no output"
        needles = (needle,) if isinstance(needle, str) else needle or ()
        unsaid = [n for n in needles if n not in said]
        problems = []
        if allowed and proc.returncode != 0:
            problems.append(f"expected exit 0, got {proc.returncode}: {short}")
        if not allowed and proc.returncode == 0:
            problems.append("expected a refusal, got exit 0")
        elif not allowed and unsaid:
            problems.append(f"refused, but its output lacks '{unsaid[0]}': {short}")
        if guard and not allowed and self.rev(guard, where) != before:
            problems.append(f"{guard} moved")
            tool = {"PROJECT_MERGE": "1"}  # put it back, so the next cases start where they expect
            if before:
                self.run("git", "update-ref", guard, before, cwd=where, extra=tool)
            else:
                self.run("git", "update-ref", "-d", guard, cwd=where, extra=tool)
        self.results.append(CaseResult(name, not problems, "; ".join(problems), seconds))
        return not problems

    def expect(self, name: str, ok: bool, detail: str) -> None:
        self.results.append(CaseResult(name, ok, "" if ok else detail, 0.0))

    def write(self, rel: str, text: str, cwd: Path | None = None) -> None:
        path = (cwd or self.v) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def append(self, rel: str, text: str, cwd: Path | None = None) -> None:
        path = (cwd or self.v) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(text)

    def branch(self, name: str) -> None:
        """A clean checkout of name, reset to the default branch (never the default itself)."""
        self.must("git", "reset", "-q", "--hard")
        self.must("git", "clean", "-fdq")
        self.must("git", "switch", "-q", "-C", name, self.d)

    def tidy(self) -> None:
        for argv in (("merge", "--abort"), ("reset", "-q", "--hard"), ("clean", "-fdq")):
            self.run("git", *argv)
        self.run("git", "switch", "-q", self.d)
        offline = self.tmp / "origin.off"
        if offline.exists() and not self.origin.exists():
            offline.rename(self.origin)
        self.run("git", "remote", "set-url", "origin", str(self.origin))

    def group(self, name: str, body: Callable[[], None]) -> None:
        try:
            body()
        except SelftestError as exc:
            self.results.append(CaseResult(f"{name} (fixture)", False, str(exc), 0.0))
        finally:
            self.tidy()

    # -- the fixture

    def setup(self) -> None:
        root = self.ctx.root
        self.must("git", "init", "-q", "--bare", "-b", self.d, str(self.origin), cwd=self.tmp)
        self.must("git", "clone", "-q", "--no-local", str(root), str(self.v), cwd=self.tmp)
        self.must("git", "checkout", "-q", "-B", self.d)
        self.overlay()
        for name in (
            *(f".githooks/{h}" for h in (*HOOKS, "reference-transaction")),
            ".project.toml",
        ):
            if not (self.v / name).is_file():
                raise SelftestError(f"{name} is missing: project-init writes it")
        toml = self.v / ".project.toml"
        line = f'origin_url = "{self.origin}"'
        text, count = re.subn(r"(?m)^origin_url = .*$", line, read_text(toml) or "")
        toml.write_text(text if count else f"{line}\n{text}", encoding="utf-8")
        self.write(
            f"{CAPS_DIR}/selftest.md",
            selftest_capability(
                "selftest.kept", "selftest.dropped", "selftest.gap [gap: selftest-gap]"
            ),
        )
        self.write(
            f"{self.tests}/test_selftest.py", selftest_tests("selftest.kept", "selftest.dropped")
        )
        self.write(
            f"{FROZEN_CHANGE}/requirements.md",
            "---\nchange: 2000-01-01-selftest-frozen\nlane: feat\nstatus: done\n"
            'roadmap: selftest-frozen\ntitle: "feat(selftest): a done change"\n---\n'
            "## Why\nThe frozen change folder of the I5 case.\n",
        )
        self.write(SELFTEST_NOTE, "# Selftest\n\nA note the selftest cases edit.\n")
        self.must("git", "add", "-A")
        self.must("git", "commit", "-q", "-m", "chore: selftest fixture")  # no hooks active yet
        self.must("git", "switch", "-q", "-c", "feat/x")
        self.append(SELFTEST_NOTE, "feat/x\n")
        self.must("git", "commit", "-q", "-am", "docs: selftest feat/x")
        self.must("git", "switch", "-q", self.d)
        self.must("git", "remote", "remove", "origin")
        self.must("git", "remote", "add", "origin", str(self.origin))
        self.install(self.v)
        if (self.v / "uv.lock").is_file():
            self.must("uv", "sync", "--locked", "--quiet")

    def install(self, where: Path) -> None:
        """What `mise install` does to a clone: `project.py hook install`, run in it."""
        script = where / "scripts" / "project.py"
        self.must("uv", "run", "--script", str(script), "hook", "install", cwd=where)

    def overlay(self) -> None:
        """Make the clone's tree the source's working tree (tracked and untracked, not ignored):
        at setup time the machinery may not be committed yet."""
        root = self.ctx.root
        listing = z_paths(run_git(root, "ls-files", "-z", "-co", "--exclude-standard").stdout)
        wanted = set(listing)
        for rel in z_paths(run_git(self.v, "ls-files", "-z").stdout):
            if rel not in wanted:
                (self.v / rel).unlink(missing_ok=True)
        for rel in listing:
            source, target = root / rel, self.v / rel
            if source.is_symlink() or source.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.is_symlink() or target.is_file():
                    target.unlink()
                if source.is_symlink():
                    target.symlink_to(os.readlink(source))
                else:
                    shutil.copy2(source, target)
            elif not source.exists():
                target.unlink(missing_ok=True)  # tracked, deleted in the working tree

    # -- the matrix

    def pushes(self) -> None:
        self.case("push main to an empty origin", True, "git", "push", "-q", "origin", self.d)
        self.must("git", "branch", "feat/main-menu", self.d)
        self.case(
            "push -u origin feat/main-menu",
            True,
            *("git", "push", "-q", "-u", "origin", "feat/main-menu"),
        )

    def main_guard(self) -> None:
        d, main = self.d, self.main
        self.must("git", "switch", "-q", d)
        self.append(SELFTEST_NOTE, "on main\n")
        commit = ("git", "commit", "-q", "-am", "docs: selftest on main")
        self.case("commit on main", False, *commit, needle=GUARDED, guard=main)
        self.case(
            "--no-verify commit on main",
            False,
            *commit[:3],
            "--no-verify",
            *commit[3:],
            needle=GUARDED,
            guard=main,
        )
        self.must("git", "reset", "-q", "--hard")
        reset = ("git", "reset", "-q", "--hard", "HEAD~1")
        self.case("reset --hard HEAD~1 on main", False, *reset, needle=GUARDED, guard=main)
        self.must("git", "reset", "-q", "--hard")
        merge = ("git", "merge", "-q", "--ff-only", "feat/x")
        self.case("fast-forward merge into main", False, *merge, needle=GUARDED, guard=main)
        self.must("git", "reset", "-q", "--hard")
        self.must("git", "switch", "-q", "feat/main-menu")
        force = ("git", "branch", "-f", d, "feat/x")
        self.case("branch -f main feat/x", False, *force, needle=GUARDED, guard=main)
        update = ("git", "update-ref", main, "feat/x")
        self.case("update-ref refs/heads/main feat/x", False, *update, needle=GUARDED, guard=main)
        self.renamed_onto()
        self.renamed_away("loose")
        tip = self.rev(main) or ""
        if self.case("delete main (branch -D)", True, "git", "branch", "-q", "-D", d):
            self.case(
                "recreate main at origin's tip after deleting it",
                False,
                *("git", "branch", d, f"origin/{d}"),
                needle=MISSING,
                guard=main,
            )
        if self.rev(main) != tip:  # a human puts it back, as specs/README.md#gates says
            self.must("git", "branch", "-f", d, tip, extra={"PROJECT_MERGE": "1"})
        # a forged remote-tracking ref: origin (reachable) holds another tip
        self.must("git", "update-ref", f"refs/remotes/origin/{d}", "feat/x")
        sync = ("git", "branch", "-f", d, f"origin/{d}")
        self.case(
            "forged origin/main, then branch -f main origin/main",
            False,
            *sync,
            needle=GUARDED,
            guard=main,
        )
        self.must("git", "fetch", "-q", "origin")
        # origin re-pointed at a fake repository whose main is feat/x
        fake = self.tmp / "fake.git"
        self.must("git", "init", "-q", "--bare", "-b", d, str(fake), cwd=self.tmp)
        self.must("git", "fetch", "-q", str(self.v), f"refs/heads/feat/x:{main}", cwd=fake)
        self.must("git", "remote", "set-url", "origin", str(fake))
        try:
            self.must("git", "fetch", "-q", "origin")
            self.case(
                "origin re-pointed at a fake repo, then synced",
                False,
                *sync,
                needle=GUARDED,
                guard=main,
            )
        finally:
            self.run("git", "remote", "set-url", "origin", str(self.origin))
            self.run("git", "fetch", "-q", "--prune", "origin")
        # the same, with main's committed origin_url forged through a replace object
        tip = self.rev(main) or ""
        self.must("git", "replace", "-f", tip, self.forged_commit(fake))
        self.must("git", "remote", "set-url", "origin", str(fake))
        try:
            self.must("git", "fetch", "-q", "origin")
            self.case(
                "origin_url forged by git replace, origin re-pointed, then synced",
                False,
                *sync,
                needle=GUARDED,
                guard=main,
            )
        finally:
            self.run("git", "replace", "-d", tip)
            self.run("git", "remote", "set-url", "origin", str(self.origin))
            self.run("git", "fetch", "-q", "--prune", "origin")
        self.upload_pack(fake)
        offline = self.tmp / "origin.off"
        self.origin.rename(offline)
        try:
            self.case(
                "origin unreachable, branch -f main feat/x",
                False,
                *force,
                needle=("cannot reach origin", "it ignores GIT_SSH_COMMAND", HINT),
                guard=main,
            )
        finally:
            offline.rename(self.origin)

    def hooks_rewritten(self) -> None:
        """git rewrites the working tree before it moves the ref (reset --hard, merge), so the
        .githooks/ copy it then runs may be gone or weakened: the pinned guard still runs."""
        d, main = self.d, self.main
        weak = WEAK_GUARD
        self.branch("chore/unhooked")
        self.must("git", "rm", "-r", "-q", "--", ".githooks")
        self.must("git", "commit", "-q", "-m", "chore: drop the hooks")
        self.branch("chore/weak")
        self.write(GUARD_HOOK, weak)
        self.must("git", "commit", "-q", "-am", "chore: weaken the main guard")
        self.must("git", "switch", "-q", d)
        for name, argv in (
            ("reset --hard main to a commit without .githooks", ("reset", "-q", "--hard")),
            ("fast-forward main to a commit that weakens the guard", ("merge", "-q", "--ff-only")),
        ):
            target = "chore/unhooked" if "without" in name else "chore/weak"
            self.case(name, False, "git", *argv, target, needle=GUARDED, guard=main)
            self.must("git", "reset", "-q", "--hard")
        self.write(GUARD_HOOK, weak)  # an edit in the working tree, not committed
        self.append(SELFTEST_NOTE, "guard emptied\n")
        try:
            self.case(
                "commit on main with the guard emptied in the working tree",
                False,
                *("git", "commit", "-q", "-m", "docs: guard emptied", "--", SELFTEST_NOTE),
                needle=GUARDED,
                guard=main,
            )
        finally:
            self.must("git", "reset", "-q", "--hard")
        hook = self.v / GUARD_HOOK
        mode = hook.stat().st_mode
        hook.chmod(mode & 0o666)  # git skips a hook file without the x bit
        try:
            self.must("git", "switch", "-q", "feat/main-menu")
            self.case(
                "branch -f main with the guard's x bit cleared",
                False,
                *("git", "branch", "-f", d, "feat/x"),
                needle=GUARDED,
                guard=main,
            )
        finally:
            hook.chmod(mode)
        self.renamed_onto(pinned=True)

    def renamed_onto(self, *, pinned: bool = False) -> None:
        """git branch -m/-c onto main writes main without asking reference-transaction. The
        files backend clears main out of the way first, and the guard refuses that and puts
        the renamed branch back; a copy asks nothing, so the guard's record of main trips at the
        next ref update, until main is back where the guard saw it. pinned: the working tree's
        guard lets everything through, so the pinned copy is the one that holds."""
        d, main, name = self.d, self.main, "feat/renamed"
        how = " (guard emptied in the working tree)" if pinned else ""
        self.branch(name)
        self.append(SELFTEST_NOTE, "renamed\n")
        self.must("git", "commit", "-q", "-am", "docs: selftest renamed")
        tip, mine = self.rev(main) or "", self.rev(name) or ""
        if pinned:
            self.write(GUARD_HOOK, WEAK_GUARD)
        try:
            self.case(
                f"branch -M main on a lane branch{how}",
                False,
                *("git", "branch", "-M", d),
                needle=(*GUARDED, "-m/-M onto it"),
                guard=main,
            )
            head = self.run("git", "symbolic-ref", "-q", "HEAD").stdout.strip()
            self.expect(
                f"the refused rename put {name} back, still checked out{how}",
                self.rev(name) == mine and head == f"refs/heads/{name}",
                f"{name} is {self.rev(name)}, HEAD is {head or 'detached'}",
            )
            if self.rev(name) is None:  # the rename went through: the next cases need the branch
                self.run("git", "branch", name, mine)
                self.run("git", "switch", "-q", name)
            self.must("git", "branch", "-C", name, d)  # git runs no hook for a copy
            self.case(
                f"a ref update after branch -C onto main{how}",
                False,
                *("git", "branch", "selftest-probe"),
                needle=TRIPPED,
                guard=main,
            )
            self.case(
                f"put main back where the guard saw it{how}",
                True,
                *("git", "update-ref", main, tip),
            )
            if pinned:
                return
            self.must("git", "update-ref", "-d", main, tip)  # a delete is recoverable
            self.case(
                "branch -m onto a deleted main",
                False,
                *("git", "branch", "-m", name, d),
                needle=MISSING,
                guard=main,
            )
            self.expect(
                f"{name} is still there after the refused rename",
                self.rev(name) == mine,
                f"{name} is {self.rev(name)}",
            )
        finally:
            if self.rev(main) != tip:
                self.must("git", "update-ref", main, tip, extra={"PROJECT_MERGE": "1"})
            if pinned:
                self.must("git", "checkout", "-q", "--", GUARD_HOOK)
            self.run("git", "branch", "-D", "selftest-probe")

    def upload_pack(self, fake: Path) -> None:
        """git -c (or the repo's own config) cannot point the guard's ls-remote at another repo
        whose main holds a commit with a forged Merged-By trailer."""
        d, main = self.d, self.main
        tip = self.rev(main) or ""
        tree = self.must("git", "rev-parse", f"{main}^{{tree}}").strip()
        message = f"docs: forged\n\n{MERGED_BY}"
        forged = self.must("git", "commit-tree", tree, "-p", tip, "-m", message).strip()
        self.must("git", "update-ref", "refs/selftest/forged", forged)
        self.must("git", "fetch", "-q", str(self.v), f"+refs/selftest/forged:{main}", cwd=fake)
        self.must("git", "update-ref", "-d", "refs/selftest/forged")
        pack = f"git-upload-pack '{fake}'; exit; "  # the shell line git runs for a local origin
        self.must("git", "switch", "-q", "feat/main-menu")
        move = ("branch", "-f", d, forged)
        self.case(
            "git -c remote.origin.uploadpack=<fake repo> branch -f main <forged Merged-By>",
            False,
            *("git", "-c", f"remote.origin.uploadpack={pack}", *move),
            needle=GUARDED,
            guard=main,
        )
        self.must("git", "config", "remote.origin.uploadpack", pack)
        try:
            self.case(
                "remote.origin.uploadpack=<fake repo> in .git/config, branch -f main <forged>",
                False,
                *("git", *move),
                needle=GUARDED,
                guard=main,
            )
        finally:
            self.run("git", "config", "--unset", "remote.origin.uploadpack")
        # the same fake through a url.<base>.insteadOf in the repo's own config: origin_url and
        # origin's URL both rewrite to it, so only the rule's scope gives it away
        rule = f"url.{fake}.insteadOf"
        self.must("git", "config", rule, str(self.origin))
        try:
            self.must("git", "fetch", "-q", "origin")
            self.case(
                "url.<fake repo>.insteadOf <origin> in .git/config, then synced",
                False,
                *("git", "branch", "-f", d, f"origin/{d}"),
                needle=(BLOCKED, "insteadOf", HINT),
                guard=main,
            )
        finally:
            self.run("git", "config", "--unset", rule)
            self.run("git", "fetch", "-q", "--prune", "origin")
        # the same rule in a git config file that GIT_CONFIG_GLOBAL names: git fetches from the
        # fake, but the guard reads the user's own ~/.gitconfig and asks the real origin
        named = self.tmp / "named-gitconfig"
        named.write_text(f'[url "{fake}"]\n\tinsteadOf = {self.origin}\n', encoding="utf-8")
        try:
            self.case(
                "GIT_CONFIG_GLOBAL names url.<fake repo>.insteadOf <origin>, then fetch main:main",
                False,
                *("git", "fetch", "-q", "origin", f"{d}:{d}"),
                extra={"GIT_CONFIG_GLOBAL": str(named)},
                needle=GUARDED,
                guard=main,
            )
        finally:
            self.run("git", "fetch", "-q", "--prune", "origin")

    def renamed_away(self, how: str) -> None:
        """Renaming main away passes (a delete is recoverable), recreating it does not."""
        d, main = self.d, self.main
        tip = self.rev(main) or ""
        rename = ("git", "branch", "-m", d, "selftest-old")
        if self.case(f"branch -m main away while main is {how}", True, *rename):
            self.case(
                "recreate main at another commit" + ("" if how == "packed" else f" ({how})"),
                False,
                *("git", "branch", d, "feat/x"),
                needle=MISSING,
                guard=main,
            )
        if self.rev("refs/heads/selftest-old"):
            self.must("git", "branch", "-D", "selftest-old")
        if self.rev(main) != tip:
            self.must("git", "branch", "-f", d, tip, extra={"PROJECT_MERGE": "1"})

    def forged_commit(self, url: Path) -> str:
        """A commit with main's tree, except that .project.toml names url as origin_url."""
        text = self.must("git", "--no-replace-objects", "show", f"{self.main}:.project.toml")
        text = re.sub(r"(?m)^origin_url = .*$", f'origin_url = "{url}"', text)
        blob = self.must("git", "hash-object", "-w", "--stdin", stdin=text).strip()
        index = {"GIT_INDEX_FILE": str(self.tmp / "forged.index")}
        self.must("git", "read-tree", self.main, extra=index)
        self.must("git", "update-index", "--cacheinfo", f"100644,{blob},.project.toml", extra=index)
        tree = self.must("git", "write-tree", extra=index).strip()
        return self.must("git", "commit-tree", tree, "-m", "forged").strip()

    def packed(self) -> None:
        main = self.main
        tip = self.rev(main)
        self.case("pack-refs --all", True, "git", "pack-refs", "--all")
        self.case("gc", True, "git", "gc", "-q")
        self.expect(
            "pack-refs and gc leave main where it was", self.rev(main) == tip, f"{main} moved"
        )
        self.must("git", "switch", "-q", "feat/main-menu")
        self.renamed_away("packed")

    def origin_sync(self) -> None:
        d, main = self.d, self.main
        other = self.tmp / "other"
        self.must("git", "clone", "-q", str(self.origin), str(other), cwd=self.tmp)  # no hooks
        landed = "\n\n" + ": ".join(TOOL_TRAILER)  # what merge writes into each commit
        for step in ("pull", "reset"):
            self.append(SELFTEST_NOTE, f"origin moved ({step})\n", cwd=other)
            message = f"docs: origin moved ({step}){landed}"
            self.must("git", "commit", "-q", "-am", message, cwd=other)
            self.must("git", "push", "-q", "origin", d, cwd=other)
            tip = self.rev(main, other)
            self.must("git", "switch", "-q", d)
            if step == "pull":
                self.case(
                    "pull --ff-only to what origin holds",
                    True,
                    "git",
                    "pull",
                    "-q",
                    "--ff-only",
                    "origin",
                    d,
                )
            else:
                self.must("git", "fetch", "-q", "origin")
                self.case(
                    "reset --hard origin/main to what origin holds",
                    True,
                    "git",
                    "reset",
                    "-q",
                    "--hard",
                    f"origin/{d}",
                )
            self.expect(
                f"main is origin's tip after the {step}",
                self.rev(main) == tip,
                f"{main} is not {tip}",
            )
        # a url.<base>.insteadOf in the user's git config (https to ssh, say) rewrites origin's
        # URL and the origin_url main records alike: the guard compares them after the rewrite.
        # The guard reads ~/.gitconfig whatever GIT_CONFIG_GLOBAL says, so the rule goes there
        # (HOME is a scratch folder) and GIT_CONFIG_GLOBAL names the same file for this git
        home = self.tmp / "home"
        home.mkdir(exist_ok=True)
        user = home / ".gitconfig"
        rule = f'[url "file://{self.origin}"]\n\tinsteadOf = {self.origin}\n'
        user.write_text(Path(self.env["GIT_CONFIG_GLOBAL"]).read_text("utf-8") + rule, "utf-8")
        mine = {"HOME": str(home), "GIT_CONFIG_GLOBAL": str(user)}
        try:
            self.append(SELFTEST_NOTE, "origin moved (rewritten)\n", cwd=other)
            message = f"docs: origin moved (rewritten){landed}"
            self.must("git", "commit", "-q", "-am", message, cwd=other)
            self.must("git", "push", "-q", "origin", d, cwd=other)
            tip = self.rev(main, other)
            self.case(
                "pull --ff-only through a url.<base>.insteadOf in the user's git config",
                True,
                *("git", "pull", "-q", "--ff-only", "origin", d),
                extra=mine,
            )
            self.expect(
                "main is origin's tip after the rewritten pull",
                self.rev(main) == tip,
                f"{main} is not {tip}",
            )
        finally:
            user.unlink(missing_ok=True)
        # origin's main moved outside merge: send-pack is plumbing, so no pre-push ran (only a
        # server ruleset stops that); the sync must not carry the unmerged commit into main
        self.branch("feat/sent")
        self.append(SELFTEST_NOTE, "sent past merge\n")
        self.must("git", "commit", "-q", "-am", "docs: sent past merge")
        self.must("git", "switch", "-q", d)
        before = self.rev(main, self.origin) or ""
        self.must("git", "send-pack", str(self.origin), f"refs/heads/feat/sent:{main}")
        try:
            self.must("git", "fetch", "-q", "origin")
            for label, argv in (
                ("pull --ff-only", ("git", "pull", "-q", "--ff-only", "origin", d)),
                ("reset --hard origin/main", ("git", "reset", "-q", "--hard", f"origin/{d}")),
            ):
                self.case(
                    f"origin's main moved outside merge (send-pack), then {label}",
                    False,
                    *argv,
                    needle=("Merged-By", HINT),
                    guard=main,
                )
                self.must("git", "reset", "-q", "--hard")
            self.case(
                "the same pull --ff-only with grep missing from PATH",
                False,
                *("git", "pull", "-q", "--ff-only", "origin", d),
                extra={"PATH": str(self.path_without("grep"))},
                needle=("needs grep", HINT),
                guard=main,
            )
            self.must("git", "reset", "-q", "--hard")
        finally:
            self.run("git", "update-ref", main, before, cwd=self.origin)
            self.run("git", "fetch", "-q", "origin")

    def path_without(self, tool: str) -> Path:
        """A PATH folder with what the hooks and git run, except tool."""
        folder = self.tmp / f"path-without-{tool}"
        folder.mkdir(exist_ok=True)
        path = self.env.get("PATH", "")
        for name in ("git", "sh", "sed", "grep", "cut", "head", "tr", "timeout", "mkdir", "mv"):
            found = shutil.which(name, path=path)
            link = folder / name
            if name != tool and found and not link.exists():
                link.symlink_to(found)
        return folder

    def merges_and_pushes(self) -> None:
        d, main = self.d, self.main
        self.branch("feat/ff")
        self.append(SELFTEST_NOTE, "feat/ff\n")
        self.must("git", "commit", "-q", "-am", "docs: selftest feat/ff")
        self.must("git", "switch", "-q", d)
        merge = ("git", "merge", "-q", "--ff-only", "feat/ff")
        self.case(
            "ff merge into main with PROJECT_MERGE=1", True, *merge, extra={"PROJECT_MERGE": "1"}
        )
        push = ("git", "push", "-q", "origin", d)
        self.case(
            "push main once origin has it",
            False,
            *push,
            needle="pre-push",
            guard=main,
            guard_in=self.origin,
        )
        self.branch("feat/push")
        self.append(SELFTEST_NOTE, "feat/push\n")
        self.must("git", "commit", "-q", "-am", "docs: selftest feat/push")
        self.case(
            "push feat/x:main",
            False,
            *("git", "push", "-q", "origin", f"feat/push:{d}"),
            needle="pre-push",
            guard=main,
            guard_in=self.origin,
        )
        empty = self.tmp / "empty.git"
        self.must("git", "init", "-q", "--bare", "-b", d, str(empty), cwd=self.tmp)
        self.case(
            "push feat/x:main to a remote that has no main",
            False,
            *("git", "push", "-q", str(empty), f"feat/push:{d}"),
            needle="pre-push",
        )
        self.expect(
            "that remote still has no main", self.rev(main, empty) is None, f"{main} was created"
        )
        self.case(
            "push . feat/x:main into this repo",
            False,
            *("git", "push", "-q", ".", f"feat/push:{d}"),
            needle="pre-push",
            guard=main,
        )
        # no client hook runs for these: receive-pack refuses, through receive.hideRefs
        self.case(
            "push --no-verify . feat/x:main into this repo",
            False,
            *("git", "push", "-q", "--no-verify", ".", f"feat/push:{d}"),
            needle="hidden ref",
            guard=main,
        )
        self.case(
            "send-pack . feat/x:main into this repo",
            False,
            *("git", "send-pack", ".", f"refs/heads/feat/push:{main}"),
            needle="hidden ref",
            guard=main,
        )
        # pre-push keeps the rendered default, whatever the working tree's .project.toml says
        toml = self.v / ".project.toml"
        text = read_text(toml) or ""
        edited, count = re.subn(r'(?m)^default_branch = ".*"$', 'default_branch = "trunk"', text)
        toml.write_text(edited if count else f'default_branch = "trunk"\n{text}', encoding="utf-8")
        try:
            self.case(
                "push feat/x:main with default_branch edited in .project.toml",
                False,
                *("git", "push", "-q", "origin", f"feat/push:{d}"),
                needle="pre-push",
                guard=main,
                guard_in=self.origin,
            )
        finally:
            toml.write_text(text, encoding="utf-8")
        self.must("git", "switch", "-q", d)
        self.case("push main with PROJECT_MERGE=1", True, *push, extra={"PROJECT_MERGE": "1"})
        self.expect(
            "origin's main is main after that push",
            self.rev(main, self.origin) == self.rev(main),
            "origin's main differs",
        )

    def staged_content(self) -> None:
        commit = ("git", "commit", "-q", "-m")
        head = "HEAD"

        def attempt(
            name: str,
            allowed: bool,
            files: dict[str, str],
            message: str,
            needle: str | None = None,
        ) -> None:
            self.branch("feat/gates")
            for rel, text in files.items():
                self.write(rel, text)
            self.must("git", "add", "--", *files)
            self.case(name, allowed, *commit, message, guard=head, needle=needle)

        note = {"selftest-notes.md": "# Notes\n\nplain text\n"}
        attempt(
            "staged fake AWS key",
            False,
            {"selftest.env": f"aws_access_key_id = {FAKE_AWS_ID}\n"},
            "chore: key",
            needle="gitleaks",
        )
        attempt(
            "staged .md with a vault path",
            False,
            {"selftest-notes.md": "see ~/helm/05-projects/x\n"},
            "docs: path",
            needle="gitleaks",
        )
        for label, text in (
            ("staged .md with a home path", "see /home/someone/notes\n"),
            ("staged .md with a macOS home folder", "made in /Users/someone\n"),
            ("staged .md with $HOME/helm", "see $HOME/helm/05-projects/x\n"),
        ):
            attempt(label, False, {"selftest-notes.md": text}, "docs: path", needle="gitleaks")
        attempt(
            "staged .md naming k8s/helm/01-base",
            True,
            {"selftest-notes.md": "deploy k8s/helm/01-base\n"},
            "docs: k8s path",
        )
        self.branch("feat/gates")
        self.write("selftest-notes.md", note["selftest-notes.md"])
        self.must("git", "add", "--", "selftest-notes.md")
        path = os.pathsep.join(
            p
            for p in self.env.get("PATH", "").split(os.pathsep)
            if not (Path(p) / "gitleaks").exists()
        )
        self.case(
            "gitleaks missing",
            False,
            *commit,
            "docs: notes",
            extra={"PATH": path, "MISE_DISABLE_TOOLS": "gitleaks"},
            needle=MISE_INSTALL,
            guard=head,
        )
        probe = f"{self.src}/selftest_probe.py"
        clean = '"""Selftest probe."""\n\nX: int = 1\n'
        for label, broken, needle in (
            ("ruff", '"""Selftest probe."""\n\nimport os\n', "ruff check"),
            ("ty", '"""Selftest probe."""\n\nX: int = "one"\n', "ty check"),
        ):
            self.branch("feat/gates")
            self.write(probe, broken)
            self.must("git", "add", "--", probe)
            self.write(probe, clean)  # the working copy is clean, the staged copy is not
            self.case(
                f"partially staged .py, {label} error in the staged copy",
                False,
                *commit,
                "chore: probe",
                needle=needle,
                guard=head,
            )
        attempt(
            "specs/mission.md staged on feat/",
            False,
            {MISSION: "# Mission\n\nchanged\n"},
            "docs: mission",
            needle="I1",
        )
        attempt(
            "CHANGELOG.md staged on feat/",
            False,
            {CHANGELOG: "# Changelog\n"},
            "docs: changelog",
            needle="I2",
        )
        skip_head = '\n\n@pytest.mark.skip\ndef test_skipped() -> None:\n    """Skipped."""\n'
        attempt(
            "new bare @pytest.mark.skip",
            False,
            {f"{self.tests}/test_selftest_skip.py": selftest_tests(head=skip_head)},
            "test: skip",
            needle="new skip",
        )
        doc = '"""Written by `project.py selftest`."""\n\n'
        body = '\n\n\ndef test_later() -> None:\n    """Later."""\n    '
        for label, code, needle in (
            ("skip() imported from pytest", 'from pytest import skip{}skip("later")\n', "skip()"),
            (
                "pt.skip() with pytest imported as pt",
                'import pytest as pt{}pt.skip("later")\n',
                "skip()",
            ),
            (
                "pytest.importorskip()",
                'import pytest{}pytest.importorskip("selftest_missing")\n',
                "importorskip()",
            ),
        ):
            attempt(
                f"new {label} without an id",
                False,
                {f"{self.tests}/test_selftest_skip.py": doc + code.format(body)},
                "test: skip",
                needle=f"new {needle}",
            )
        # a skip outside the test folders skips tests too, and so does one named by a string
        conftest = (
            doc + "import pytest\n\n\n"
            "def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:\n"
            '    """Skip every test."""\n'
            "    for item in items:\n"
            "        item.add_marker(pytest.mark.skip)\n"
        )
        attempt(
            "new skip in a conftest.py at the repo root",
            False,
            {"conftest.py": conftest},
            "test: skip all",
            needle="new skip",
        )
        hidden = (
            '\n\n@getattr(pytest.mark, "sk" + "ip")\ndef test_hidden() -> None:\n    """H."""\n'
        )
        attempt(
            "new skip named by a string (getattr on pytest.mark)",
            False,
            {f"{self.tests}/test_selftest_skip.py": selftest_tests(head=hidden)},
            "test: skip",
            needle="named by a string",
        )
        xfail_head = (
            '\n\n@pytest.mark.spec("selftest.gap")\n'
            '@pytest.mark.xfail(strict=True, reason="selftest.gap: known gap")\n'
            'def test_gap() -> None:\n    """selftest.gap."""\n'
        )
        attempt(
            "new strict xfail naming a gap id",
            True,
            {f"{self.tests}/test_selftest_gap.py": selftest_tests(head=xfail_head)},
            "test: gap",
        )
        attempt("message 'update stuff'", False, note, "update stuff", needle="conventional")
        # the subject git stores depends on the cleanup, which the hook cannot see: -m and -F
        # keep a first line that starts with '#', and core.commentChar decides what strip drops
        for label, argv in (
            (
                "message '# update stuff' then 'docs: x' (-m keeps the comment line)",
                ("commit", "-q", "-m", "# update stuff", "-m", "docs: x"),
            ),
            (
                "--cleanup=verbatim with the first line '# update stuff'",
                ("commit", "-q", "--cleanup=verbatim", "-m", "# update stuff\n\ndocs: x"),
            ),
            (
                "core.commentChar=f and --cleanup=strip drop the subject 'feat: x'",
                ("-c", "core.commentChar=f", "commit", "-q", "--cleanup=strip", "-m", "feat: x")
                + ("-m", "update stuff"),
            ),
        ):
            self.branch("feat/gates")
            self.write("selftest-notes.md", note["selftest-notes.md"])
            self.must("git", "add", "--", "selftest-notes.md")
            self.case(label, False, "git", *argv, needle="conventional", guard=head)
        attempt("message 'docs: notes' then a comment line", True, note, "docs: notes\n\n# later")
        for subject in ('Revert "docs: notes"', 'Reapply "docs: notes"', "fixup! docs: notes"):
            attempt(f"git's own subject '{subject}'", True, note, subject)
        attempt(
            "message 'Revert \"update stuff\"'",
            False,
            note,
            'Revert "update stuff"',
            needle="conventional",
        )
        attempt(
            "feat(cli): x touching src without Spec:",
            False,
            {probe: clean},
            "feat(cli): x",
            needle="Spec:",
        )
        attempt(
            "feat(cli): x touching src with Spec: selftest.kept",
            True,
            {probe: clean},
            "feat(cli): x\n\nSpec: selftest.kept",
        )
        self.timing = self.results[-1].seconds
        # commit-msg reads [paths] from HEAD and the index, never the working tree
        toml = self.v / ".project.toml"
        self.branch("feat/gates")
        self.write(probe, clean)
        self.must("git", "add", "--", probe)
        text = read_text(toml) or ""
        edited, count = re.subn(r"(?m)^src = .*$", 'src = ["nowhere"]', text)
        toml.write_text(edited if count else f'{text}\n[paths]\nsrc = ["nowhere"]\n', "utf-8")
        try:
            self.case(
                "feat(cli): x touching src, [paths] src edited in the working tree",
                False,
                *commit,
                "feat(cli): x",
                needle="Spec:",
                guard=head,
            )
        finally:
            toml.write_text(text, encoding="utf-8")
        attempt(
            "test tagged nope.nope",
            False,
            {f"{self.tests}/test_selftest_nope.py": selftest_tests("nope.nope")},
            "test: nope",
            needle="nope.nope",
        )
        frozen = f"{FROZEN_CHANGE}/requirements.md"
        self.branch("feat/gates")
        self.append(frozen, "edited\n")
        self.must("git", "add", "--", frozen)
        self.case(
            "edit a done change folder", False, *commit, "docs: frozen", needle="I5", guard=head
        )
        self.proof_files(attempt)

    def proof_files(self, attempt: Callable[..., None]) -> None:
        """I24 in pre-commit: a proof file goes in with the sha256 its README.md entry records;
        one edited by hand is refused (feat/gates has no change folder: today's folder)."""
        name = f"{today()}-gates"
        file = "selftest.kept-run-echo-kept.txt"
        capture = "$ echo kept\nexit 0 in 0.0 s\n--- stdout\nkept\n--- stderr (empty)\n"
        entry = ProofEntry("selftest.kept", "run", "echo kept", "0" * 10, [])
        entry.files = [(file, sha256_hex(capture.encode()))]

        def files(text: str) -> dict[str, str]:
            readme = render_index(ProofIndex(name, entries=[entry]), lambda _: text.encode())
            return {f"{PROOF_DIR}/{name}/{PROOF_INDEX}": readme, f"{PROOF_DIR}/{name}/{file}": text}

        message = "docs(proof): selftest.kept run"
        attempt("a proof capture with its README.md entry", True, files(capture), message)
        edited = files(capture + "edited by hand\n")
        attempt("a proof file edited by hand", False, edited, message, needle="I24")

    def scenarios(self) -> None:
        cap = f"{CAPS_DIR}/selftest.md"
        tests = f"{self.tests}/test_selftest.py"
        gap = "selftest.gap [gap: selftest-gap]"
        commit = ("git", "commit", "-q", "-m")

        def attempt(
            name: str,
            allowed: bool,
            files: dict[str, str],
            message: str,
            needle: str | None = None,
        ) -> None:
            self.branch("chg/selftest")
            for rel, text in files.items():
                self.write(rel, text)
            self.must("git", "add", "-A", "--", *files)
            self.case(name, allowed, *commit, message, guard="HEAD", needle=needle)

        added = selftest_capability("selftest.kept", "selftest.dropped", gap, "selftest.added")
        attempt(
            "scenario added without a test",
            False,
            {cap: added},
            "change(selftest): add",
            needle="I4",
        )
        new_test = {f"{self.tests}/test_selftest_added.py": selftest_tests("selftest.added")}
        attempt(
            "scenario added with its test", True, {cap: added, **new_test}, "change(selftest): add"
        )
        dropped = selftest_capability("selftest.kept", gap)
        trailer = "change(selftest)!: drop\n\nSpec-Removed: selftest.dropped"
        attempt("scenario removed, its test kept", False, {cap: dropped}, trailer, needle="I4")
        both = {cap: dropped, tests: selftest_tests("selftest.kept")}
        attempt(
            "scenario and test removed, no Spec-Removed:",
            False,
            both,
            "change(selftest)!: drop",
            needle="Spec-Removed",
        )
        attempt("scenario and test removed with Spec-Removed:", True, both, trailer)
        # a feat/ branch waits for approve only while its change folder is open
        self.branch("feat/no-folder")
        self.write(cap, added)
        self.must("git", "add", "--", cap)
        self.case(
            "scenario added without a test on feat/ with no change folder",
            False,
            *commit,
            "spec(selftest): add",
            needle="I4",
            guard="HEAD",
        )

    def merge_main(self) -> None:
        """`git merge main` into a lane branch, as status asks once main moved: files that come
        from main (CHANGELOG.md, the roadmap) pass the lane rules, the branch's own edits do not."""
        d = self.d
        tool = {"PROJECT_MERGE": "1"}
        self.branch("feat/merge")
        self.append(SELFTEST_NOTE, "feat/merge\n")
        self.must("git", "commit", "-q", "-am", "docs: selftest feat/merge")
        self.must("git", "switch", "-q", d)
        self.write(CHANGELOG, "# Changelog\n\nmain moved\n")
        self.append(ROADMAP, "- [ ] selftest-main: from main\n")
        self.write("selftest-main.md", "# From main\n")
        self.must("git", "add", "--", CHANGELOG, ROADMAP, "selftest-main.md")
        self.must("git", "commit", "-q", "-m", "chore: main moved", extra=tool)
        self.must("git", "switch", "-q", "feat/merge")
        merge = ("git", "merge", "-q", "--no-edit", d)
        self.case("git merge main into a lane branch", True, *merge)
        self.must("git", "switch", "-q", d)
        self.append(SELFTEST_NOTE, "main side\n")
        self.write(CHANGELOG, "# Changelog\n\nmain moved twice\n")
        self.append(ROADMAP, "- [ ] selftest-main-two: from main\n")
        self.must("git", "commit", "-q", "-am", "chore: main moved again", extra=tool)
        self.must("git", "switch", "-q", "feat/merge")
        self.append(SELFTEST_NOTE, "branch side\n")
        self.must("git", "commit", "-q", "-am", "docs: branch side")
        conflicted = self.run(*merge)
        if conflicted.returncode == 0:
            raise SelftestError("the conflicting merge of main did not stop for a resolution")
        self.write(SELFTEST_NOTE, "# Selftest\n\nresolved\n")
        self.must("git", "add", "--", SELFTEST_NOTE)
        self.append(MISSION, "edited while resolving\n")
        self.must("git", "add", "--", MISSION)
        resolve = ("git", "commit", "-q", "--no-edit")
        self.case(
            "a conflicted merge that also edits specs/mission.md",
            False,
            *resolve,
            needle="I1",
            guard="HEAD",
        )
        self.must("git", "reset", "-q", "--", MISSION)  # unstaged: the merge commits HEAD's
        self.case("a conflicted merge of main, resolved", True, *resolve)

    def merge_side(self) -> None:
        """A merge that is not `git merge main`: src content that comes from the merged branch
        (whose own commits named their scenarios) passes; src edited during the merge is the
        merge commit's own and needs Spec:."""
        probe = f"{self.src}/selftest_merge.py"
        first = '"""Selftest probe."""\n\n\ndef one() -> int:\n    """One."""\n    return 1\n'
        last = '\n\ndef two() -> int:\n    """Two."""\n    return 2\n'
        spec = "\n\nSpec: selftest.kept"
        self.branch("fix/merge")
        self.write(probe, first + last)
        self.must("git", "add", "--", probe)
        self.must("git", "commit", "-q", "-m", f"fix(cli): probe{spec}")
        self.must("git", "switch", "-q", "-c", "fix/merge--g1")
        self.write(probe, first + last.replace("return 2", "return 2 + 0"))
        self.must("git", "commit", "-q", "-am", f"fix(cli): two{spec}")
        self.must("git", "switch", "-q", "fix/merge")
        self.write(probe, first.replace("return 1", "return 1 + 0") + last)
        self.must("git", "commit", "-q", "-am", f"fix(cli): one{spec}")
        merge = ("git", "merge", "-q", "--no-ff", "--no-edit", "fix/merge--g1")
        self.case("a clean merge of two edits to one src file", True, *merge)
        self.must("git", "switch", "-q", "fix/merge--g1")
        self.append(SELFTEST_NOTE, "side\n")
        self.must("git", "commit", "-q", "-am", "docs: side")
        self.must("git", "switch", "-q", "fix/merge")
        self.must("git", "merge", "-q", "--no-commit", "--no-ff", "fix/merge--g1")
        self.append(probe, '\n\ndef three() -> int:\n    """Three."""\n    return 3\n')
        self.must("git", "add", "--", probe)
        self.case(
            "src edited by hand during a merge, no Spec:",
            False,
            *("git", "commit", "-q", "-m", "Merge branch 'fix/merge--g1' into fix/merge"),
            needle="Spec:",
            guard="HEAD",
        )

    def worktree(self) -> None:
        wt = self.tmp / "wt"
        self.must("git", "worktree", "add", "-q", "-b", "feat/wt", str(wt), self.d)
        self.append(SELFTEST_NOTE, "from a worktree\n", cwd=wt)
        self.case(
            "a commit from a worktree",
            True,
            "git",
            "commit",
            "-q",
            "-am",
            "docs: from a worktree",
            cwd=wt,
        )

    def first_commit(self) -> None:
        fresh = self.tmp / "fresh"
        self.must("git", "init", "-q", "-b", self.d, str(fresh), cwd=self.tmp)
        machinery = [".githooks", "scripts/project.py", ".project.toml", ".gitleaks.toml"]
        machinery += [n for n in (*MISE_CONFIGS, "mise.lock") if (self.v / n).is_file()]
        for rel in machinery:
            source, target = self.v / rel, fresh / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.is_dir():
                shutil.copytree(source, target)
            elif source.is_file():
                shutil.copy2(source, target)
        exclude = fresh / ".git" / "info" / "exclude"
        exclude.parent.mkdir(parents=True, exist_ok=True)
        exclude.write_text("\n".join(f"/{rel}" for rel in machinery) + "\n", encoding="utf-8")
        self.install(fresh)
        self.write("README.md", "# fresh\n", cwd=fresh)
        self.must("git", "add", "README.md", cwd=fresh)
        self.case(
            "first commit in a fresh repo",
            True,
            "git",
            "commit",
            "-q",
            "-m",
            "chore: scaffold fresh",
            cwd=fresh,
        )
        self.expect(
            "the first commit made main", self.rev(self.main, fresh) is not None, f"no {self.main}"
        )
        # main is the only branch: deleting it must not reopen the first-commit door
        first = self.rev(self.main, fresh) or ""
        self.must("git", "switch", "-q", "--detach", cwd=fresh)
        self.case(
            "delete main while it is the only branch",
            True,
            *("git", "branch", "-q", "-D", self.d),
            cwd=fresh,
        )
        self.write("README.md", "# fresh, moved\n", cwd=fresh)
        self.must("git", "commit", "-q", "-am", "docs: detached", cwd=fresh)
        self.case(
            "then create main at another commit",
            False,
            *("git", "branch", self.d, "HEAD"),
            cwd=fresh,
            needle=MISSING,
            guard=self.main,
        )
        # nor does wiping every ref and reflog: the object store still holds other commits
        self.must("git", "checkout", "-q", "--orphan", "selftest-orphan", cwd=fresh)
        self.must("git", "reflog", "expire", "--expire=now", "--all", cwd=fresh)
        self.case(
            "recreate main after every ref and reflog is gone",
            False,
            *("git", "update-ref", self.main, first),
            cwd=fresh,
            needle=MISSING,
            guard=self.main,
        )

    # -- the Claude Code hooks

    def hook(
        self, name: str, cwd: Path, payload: dict[str, object], script: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        """`project.py hook <name>` of the clone, as Claude Code runs it: hook JSON on stdin."""
        data = json.dumps({"session_id": "selftest", "cwd": str(cwd), **payload})
        script = script or self.v / "scripts" / "project.py"
        return self.run(sys.executable, str(script), "hook", name, stdin=data)

    def claude_hooks(self) -> None:
        """pre-bash's cases, fed as hook JSON in this process, so the session's own permission
        rules never mask a result; then session-start's cap and the launcher, as subprocesses."""
        self.write(*PRE_BASH_SCRIPT)
        for command, deny in PRE_BASH_CASES:
            raw = json.dumps(
                {
                    "hook_event_name": "PreToolUse",
                    "tool_name": "Bash",
                    "tool_input": {"command": command},
                    "cwd": str(self.v),
                }
            ).encode()
            reason = pre_bash(hook_payload(raw) or {}, self.v, [self.v])
            label = command
            if command.endswith(PRE_BASH_SCRIPT[0]):
                label += f" ({PRE_BASH_SCRIPT[0]} sets PROJECT_MERGE=1)"
            if deny:
                self.expect(f"pre-bash denies {label}", reason is not None, "allowed")
            else:
                self.expect(f"pre-bash allows {label}", reason is None, f"blocked {reason}")
        self.session_start()
        self.launcher()

    def session_start(self) -> None:
        lessons = "".join(
            f"\n## 2026-01-{day:02d} | selftest lesson {day:02d} {'long title ' * 20}\n"
            f"Trigger: the selftest wrote twelve lessons\nRule: {'keep the newest ' * 20}\n"
            for day in range(1, 13)
        )
        self.write(LESSONS_FILE, "# Lessons\n" + lessons)
        proc = self.hook("session-start", self.v, {"hook_event_name": "SessionStart"})
        size = len(proc.stdout.encode())
        shown = [day for day in range(1, 13) if f"selftest lesson {day:02d}" in proc.stdout]
        ok = proc.returncode == 0 and size <= SESSION_CAP and shown == list(range(8, 13))
        self.expect(
            "session-start with 12 lessons: 3 KB at most, the newest 5 in it",
            ok,
            f"exit {proc.returncode}, {size} bytes, lessons shown {shown}: {said(proc, 3)}",
        )

    def launcher(self) -> None:
        wt = self.tmp / "wt-hooks"
        self.must("git", "worktree", "add", "-q", "-b", "feat/hooks", str(wt), self.d)
        script = wt / "scripts" / "project.py"
        text = read_text(script) or ""
        marked = text.replace("\ndef main(", f"\nprint({LAUNCH_MARK!r})\n\n\ndef main(", 1)
        if marked == text:
            raise SelftestError("the worktree's scripts/project.py has no main() to mark")
        script.write_text(marked, encoding="utf-8")
        bash: dict[str, object] = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
        }
        there = self.hook("pre-bash", wt, bash)
        self.expect(
            "pre-bash from a worktree runs that worktree's project.py",
            there.returncode == 0 and LAUNCH_MARK in there.stdout,
            said(there),
        )
        here = self.hook("pre-bash", self.v, bash)
        self.expect(
            "pre-bash in the main checkout runs its own project.py",
            here.returncode == 0 and LAUNCH_MARK not in here.stdout,
            said(here),
        )
        start = self.hook("session-start", wt, {"hook_event_name": "SessionStart"})
        self.expect(
            "session-start from a worktree runs that worktree's copy, on its branch",
            LAUNCH_MARK in start.stdout and "feat/hooks" in start.stdout,
            said(start),
        )
        merge = self.hook("pre-bash", wt, {**bash, "tool_input": {"command": "mise run merge"}})
        self.expect(
            "pre-bash from a worktree still blocks mise run merge",
            merge.returncode == BLOCK and GATES in merge.stderr,
            said(merge),
        )


def cmd_selftest(ctx: Context, args: argparse.Namespace) -> int:
    tmp = Path(tempfile.mkdtemp(prefix="project-selftest-"))
    test = Selftest(ctx, tmp)
    start = time.monotonic()
    print(f"selftest: a clone of {ctx.root.name} with a bare origin in {tmp}")
    try:
        try:
            test.setup()
        except SelftestError as exc:
            print(f"FAIL  fixture: {exc}")
            return 1
        for name, body in (
            ("pushes", test.pushes),
            ("the main guard", test.main_guard),
            ("hooks rewritten by git", test.hooks_rewritten),
            ("pack-refs and gc", test.packed),
            ("origin sync", test.origin_sync),
            ("merge and push", test.merges_and_pushes),
            ("staged content", test.staged_content),
            ("scenarios and tests", test.scenarios),
            ("merging main into a branch", test.merge_main),
            ("merging another branch", test.merge_side),
            ("worktree", test.worktree),
            ("first commit", test.first_commit),
            ("claude hooks", test.claude_hooks),
        ):
            test.group(name, body)
    finally:
        if not args.keep:
            shutil.rmtree(tmp, ignore_errors=True)
    for result in test.results:
        level = "ok" if result.ok else "FAIL"
        timing = f" ({result.seconds:.1f} s)" if result.seconds >= 0.05 else ""
        print(f"{level:<5} {result.name}{timing}" + (f": {result.detail}" if result.detail else ""))
    failed = sum(1 for r in test.results if not r.ok)
    total = time.monotonic() - start
    print(f"      a src commit through pre-commit and commit-msg: {test.timing:.1f} s (target 5 s)")
    verdict = "FAIL" if failed else "ok"
    print(f"selftest: {verdict} ({len(test.results)} cases, {failed} failed, {total:.0f} s)")
    return 1 if failed else 0


# ---------------------------------------------------------------- lifecycle: shared

# change, backlog, approve, merge, abandon, release and doctor (specs/README.md, Lifecycle and
# Definition of Done). approve, merge, abandon and release are human gates that a person types.
# The default branch moves here only under PROJECT_MERGE, and every commit these commands put on
# it carries the Merged-By trailer, which `status --audit`, doctor and CI look for.

BACKLOG_DIR = "specs/backlog"
SPEC_APPROVED = "Spec-Approved"
MERGED_BY = f"{TOOL_TRAILER[0]}: {TOOL_TRAILER[1]}"
LANE_WEIGHT = {"chore": 0, "refactor": 0, "fix": 1, "chg": 1, "feat": 2}  # a lane only gets heavier
WORKER_RE = re.compile(r"--g(\d+)$")  # feat/<slug>--g<n>: a parallel worker branch
DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-")
CHANGE_SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"  # what `change` accepts: no leading, trailing or double -
RATCHET_SUBJECT_RE = re.compile(r"^spec\([^)]*\): ratchet [a-z]+ to feat$")  # change_ratchet's
CLOSE_COMMIT = "<close-commit>"  # merge --dry-run: the sha of the close commit merge will write
# Gate files (Definition of Done, step 6): a branch that changes one needs merge --gate-change.
GATE_FILES = (
    ".githooks/",
    "scripts/project.py",
    ".gitleaks.toml",
    ".github/workflows/ci.yml",
    ".github/workflows/sdd.yml",
    ".claude/settings.json",
)
GATE_MISE_TABLES = ("tasks", "hooks")  # of mise.toml
RUN_IT_TIMEOUT = 60  # seconds for one Run it row of validation.md
CHECKS_TIMEOUT = 3600  # seconds merge waits for the pull request's checks to finish
CHECKS_REGISTER = 300  # seconds the checks merge waits on get to show up on the pull request
CHECKS_POLL = 10  # seconds between two looks at the pull request's checks
CHECKS_ERRORS = 3  # `gh pr checks` failures in a row before merge gives up waiting
CHECK_FIELDS = "name,bucket,workflow,link"  # gh pr checks --json; bucket: pass fail pending ...
CHECK_DONE = ("pass", "skipping")  # a bucket that lets the merge go on
CHECK_FAILED = ("fail", "cancel")
PR_FIELDS = "number,state,headRefOid,mergeCommit"  # gh pr view --json: the pull request's record
SYNC_TRIES = 6  # looks at origin's default branch, 2 s apart, for the merge commit to show up
CI_WORKFLOWS = (".github/workflows/ci.yml", ".github/workflows/sdd.yml")  # what render writes
TRUSTED_SCOPES = ("global", "system")  # the git config whose url.<base>.insteadOf the guard follows
# The subject types a fast lane lands under. Merge takes the branch's first commit of one of these
# types as the squash subject, which the CHANGELOG line comes from, unless --title names one.
LANE_TITLE_TYPES = {
    "fix": ("fix",),
    "chg": ("change",),
    "refactor": ("perf", "refactor"),
    "chore": ("chore", "build", "ci", "docs", "style", "test"),
    "plan": ("spec", "docs", "chore"),
}
DISTRIBUTIONS = ("pypi", "git", "service", "none")
BUMPS = ("patch", "minor", "major")
BOOL_WORDS = ("1", "0", "true", "false", "yes", "no", "on", "off", "t", "f", "y", "n")
STATUS_LINE_RE = re.compile(r"^(status:[ \t]*)(['\"]?)([A-Za-z]+)\2")
ENV_ROW_RE = re.compile(r"^#\s*([A-Za-z_][A-Za-z0-9_]*)\s*\|(.*)$")
RANGE_RE = re.compile(r"^(-?\d+(?:\.\d+)?)\.\.(-?\d+(?:\.\d+)?)$")
BASELINE_MARK = "project-init baseline: shrink only"
PLACEHOLDER_DESCRIPTION = "Add your description here"


def text_lines(*lines: str) -> str:
    return "\n".join(lines) + "\n"


# A change folder and a backlog item start from these templates: the same text as project-init's
# product templates (its tests keep the copies identical), so `change` and `backlog` need nothing
# from outside this repo.
CHANGE_TEMPLATES = {
    "requirements.md": text_lines(
        "---",
        'change: "{DATE}-{SLUG}"',
        "lane: feat",
        "status: draft                                   # draft | approved | done",
        'roadmap: "{ROADMAP_SLUG}"',
        'title: "{CONVENTIONAL_TITLE}"   # becomes the squash commit + CHANGELOG line',
        "---",
        "<!-- requirements.md: why this change exists and what it decided. status moves only via "
        "approve and merge; frozen at done. title is a YAML double-quoted string, so escape any "
        '" or \\ in it. Rollback is one line: revert: <why a revert of the squash is enough>, '
        "flag: <ENV_NAME> (its flag row in .env.example, off by default), or one-way: <what "
        "cannot be undone>. Cap 120 lines. -->",
        "## Why",
        "{WHY}",
        "## Scope",
        "In: {SCOPE_IN}. Out: {SCOPE_OUT}.",
        "## Decisions",
        "- {DECISION}. Rejected: {REJECTED_OPTION}, {REASON}.",
        "## Context",
        "- {CONTEXT}",
        "## Rollback",
        "{ROLLBACK_KIND}: {ROLLBACK_DETAIL}",
    ),
    "plan.md": text_lines(
        "<!-- plan.md: task groups for this change, numbered G1, G2 and on. A group is done when "
        "every ID in it has a passing test, so no checkboxes; risk: high pauses compile after the "
        "group. Cap 100 lines. -->",
        "## G{N} {GROUP_NAME} | {SCENARIO_IDS} | risk: {LOW_OR_HIGH} | parallel: {YES_OR_NO}",
        "Files: {FILES}",
    ),
    "validation.md": text_lines(
        "<!-- validation.md: what gets checked beyond the tests. Review focus at most 5 rows, "
        "Proof at most 6, Human checks at most 3. Cap 60 lines. Proof: one row per case (a "
        "scenario ID or G<n>), in the one kind that shows it best: run (--before when the old "
        "output matters), log, http, screenshot, video, terminal or attach. A case whose tests "
        "show enough gets no row. -->",
        "## Review focus   (implied inputs the spec never named; each -> a scenario, or "
        '"none: <reason>")',
        "- {IMPLIED_INPUT} -> {SCENARIO_ID}",
        "## Run it   (optional, feat only: what tests cannot reach, e.g. a real server; merge "
        "executes each row)",
        "| command | exit | stdout contains | stderr contains |",
        "|---|---|---|---|",
        "## Proof   (what a human looks at instead of reading leaf code; test proof is "
        "automatic; mise run proof captures each row, merge checks it)",
        "| for | kind | shows |",
        "|---|---|---|",
        "## Human checks   (<=3; merge asks with a TTY, or records your --attest)",
        "- {HUMAN_CHECK}",
    ),
}
BACKLOG_TEMPLATE = text_lines(
    "---",
    "status: open                                    # open | scheduled",
    "roadmap:                                        # the roadmap slug, once scheduled",
    "---",
    "<!-- backlog item: an idea, spike finding or abandoned change that is not being built now. "
    "Deleted when its work starts or a replan drops it. No line cap. -->",
    "# {TITLE}",
    "",
    "## What",
    "{WHAT}",
    "",
    "## Why",
    "{WHY}",
    "",
    "## Notes",
    "{NOTES}",
)


def today() -> str:
    return datetime.now().astimezone().date().isoformat()


def fill(template: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        template = template.replace("{" + key + "}", value)
    return template


def user_name(root: Path) -> str:
    """Who is at the keyboard, for an attestation: git's user.name."""
    name = (git(root, "config", "user.name") or "").strip()
    return name or os.environ.get("GIT_AUTHOR_NAME", "").strip() or "unknown"


def lifecycle_env(*, merge: bool = False) -> dict[str, str]:
    """The environment of the git, mise, uv and gh runs below: SCRUB_ENV removed, and
    PROJECT_MERGE set only when merge is True, the one way the default branch moves (the
    reference-transaction guard and pre-push let it through)."""
    env = {k: v for k, v in os.environ.items() if k not in SCRUB_ENV and k != "PROJECT_MERGE"}
    if merge:
        env["PROJECT_MERGE"] = "1"
    return env


def run_cmd(
    argv: list[str],
    cwd: Path,
    env: dict[str, str],
    *,
    stdin: str | None = None,
    timeout: int = TOOL_TIMEOUT,
) -> subprocess.CompletedProcess[str]:
    """A command with a fixed argv (no shell) in a process group of its own, with a time limit.
    On a timeout (exit 124) or an interrupt the whole group is killed. Never raises OSError."""
    try:
        proc = subprocess.Popen(  # noqa: S603
            argv,
            cwd=cwd,
            env=env,
            stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
    except OSError as exc:
        return subprocess.CompletedProcess(argv, 127, "", f"cannot run {argv[0]}: {exc}")
    try:
        out, err = proc.communicate(stdin, timeout=timeout)
    except subprocess.TimeoutExpired:
        kill_group(proc)
        out, err = proc.communicate()
        return subprocess.CompletedProcess(argv, 124, out, f"{err}\ntimed out after {timeout} s")
    except BaseException:
        kill_group(proc)
        raise
    return subprocess.CompletedProcess(argv, proc.returncode, out, err)


def git_run(
    root: Path, env: dict[str, str], *args: str, stdin: str | None = None
) -> subprocess.CompletedProcess[str]:
    return run_cmd(["git", *args], root, env, stdin=stdin)


def said(proc: subprocess.CompletedProcess[str], lines: int = 8) -> str:
    """The last lines a run printed, colour codes and blank lines left out."""
    text = plain(f"{proc.stdout}\n{proc.stderr}").splitlines()
    return "\n".join(text[-lines:]) or f"exit {proc.returncode}, no output"


def rev(root: Path, ref: str) -> str | None:
    out = git(root, "rev-parse", "-q", "--verify", f"{ref}^{{commit}}")
    return out.strip() if out else None


def is_ancestor(root: Path, older: str, newer: str) -> bool:
    return run_git(root, "merge-base", "--is-ancestor", older, newer).returncode == 0


def dirty_paths(root: Path, *, backlog_ok: bool = False) -> list[str]:
    """What `git status` shows as changed or untracked (ignored files never count). backlog_ok:
    untracked files under specs/backlog/ do not count either (an idea parked on the default
    branch waits there, untracked, for the next change)."""
    out = run_git(root, "status", "--porcelain", "-z", "--untracked-files=all").stdout
    found: list[str] = []
    skip = False
    for entry in out.decode("utf-8", "surrogateescape").split("\0"):
        if skip:
            skip = False
            continue
        if len(entry) < 4:
            continue
        code, path = entry[:2], entry[3:]
        skip = code[0] in "RC"  # the next entry is the source of the rename or copy
        if backlog_ok and code == "??" and path.startswith(BACKLOG_DIR + "/"):
            continue
        found.append(path)
    return found


def print_dirty(paths: list[str], what: str) -> None:
    print(f"FAIL  the tree is dirty ({plural(len(paths), 'file')}); {what}:")
    for path in paths[:20]:
        print(f"  {path}")
    if len(paths) > 20:
        print(f"  ... and {len(paths) - 20} more (git status)")


@dataclass
class Worktree:
    path: Path
    branch: str | None  # the branch checked out there; None when detached


def list_worktrees(root: Path) -> list[Worktree]:
    trees: list[Worktree] = []
    for block in (git(root, "worktree", "list", "--porcelain") or "").split("\n\n"):
        fields = {}
        for line in block.splitlines():
            key, _, value = line.partition(" ")
            fields[key] = value
        path = Path(fields.get("worktree", ""))
        if fields.get("worktree") and path.is_dir():
            branch = fields.get("branch", "").removeprefix("refs/heads/")
            trees.append(Worktree(path, branch or None))
    return trees


def worktree_of(root: Path, branch: str) -> Path | None:
    """The worktree that has branch checked out, if one does."""
    return next((tree.path for tree in list_worktrees(root) if tree.branch == branch), None)


def same_path(one: Path, other: Path) -> bool:
    return one.resolve() == other.resolve()


def lane_branches(root: Path) -> list[str]:
    """The local lane branches, parallel workers (feat/<slug>--g<n>) left out."""
    refs = git_lines(
        root,
        "for-each-ref",
        "--format=%(refname:short)",
        *(f"refs/heads/{lane}/" for lane in LANES),
    )
    return [ref for ref in refs if not WORKER_RE.search(ref)]


def open_changes(ctx: Context) -> list[str]:
    """I8: the lane branches that hold an open change: every one with commits the default
    branch lacks, and every one checked out here or in another worktree (a change just started
    has no commit yet). Merge and abandon delete a branch once it is done, so a branch that is
    neither never started. A branch from before the adoption is no change (pre_adoption)."""
    held = {tree.branch for tree in list_worktrees(ctx.root) if tree.branch}
    older = set(pre_adoption(ctx))
    found = []
    for branch in lane_branches(ctx.root):
        if branch in older:
            continue
        merged = ctx.default_ref is not None and is_ancestor(
            ctx.root, f"refs/heads/{branch}", ctx.default_ref
        )
        if branch == ctx.branch or branch in held or not merged:
            found.append(branch)
    return found


def pre_adoption(ctx: Context) -> list[str]:
    """The lane-named branches that fork before the adoption: their merge-base with the default
    branch has no .project.toml (the default branch has one, so project-init landed). Such a
    branch was never opened by `change` (an old feat/ branch, a v2 chore/project-init), so I8
    does not count it: `status` lists it instead. A `git merge <default>` into one moves its
    fork point past the adoption, and from then on it is an open change like any other."""
    default = ctx.default_ref
    if default is None or not has_manifest(ctx.root, default):
        return []  # no adoption on the default branch yet: nothing is from before it
    found = []
    for branch in lane_branches(ctx.root):
        fork = (git(ctx.root, "merge-base", f"refs/heads/{branch}", default) or "").strip()
        if not fork or not has_manifest(ctx.root, fork):
            found.append(branch)
    return found


def has_manifest(root: Path, commit: str) -> bool:
    """Whether commit's tree holds .project.toml: project-init had landed by then."""
    return run_git(root, "cat-file", "-e", f"{commit}:.project.toml").returncode == 0


def branch_commits(ctx: Context) -> list[tuple[str, str, str]]:
    """(sha, subject, trailer block) of the branch's own commits since the merge-base, oldest
    first; merges (the default branch coming in) left out."""
    if not ctx.base or not ctx.head:
        return []
    out = git(
        ctx.root,
        "log",
        "--no-merges",
        "--reverse",
        "--format=%H%x1f%s%x1f%(trailers:only,unfold)%x1e",
        f"{ctx.base}..{ctx.head}",
    )
    commits = []
    for record in (out or "").split("\x1e"):
        parts = record.strip("\n").split("\x1f")
        if len(parts) == 3 and parts[0]:
            commits.append((parts[0], parts[1], parts[2]))
    return commits


DISMISSED_RE = re.compile(r"^Dismissed:\s*\S")


def dismissed_lines(ctx: Context) -> list[str]:
    """The `Dismissed: <finding>: <reason>` lines in the bodies of the branch's own commits,
    oldest first: validate's outcome 3. The squash deletes the branch, so merge copies them
    into the squash body, the record that stays on the default branch."""
    if not ctx.base or not ctx.head:
        return []
    out = git(
        ctx.root, "log", "--no-merges", "--reverse", "--format=%B%x1e", f"{ctx.base}..{ctx.head}"
    )
    found: list[str] = []
    for body in (out or "").split("\x1e"):
        for line in body.splitlines():
            text = line.strip()
            if DISMISSED_RE.match(text) and text not in found:
                found.append(text)
    return found


TRAILER_LINE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*:\s")


def title_commit_notes(ctx: Context, title: str) -> list[str]:
    """The prose body of the branch commit the squash subject comes from (a fast lane or
    plan/ branch: fast_lane_title picks it), without its trailer block and its `Dismissed:`
    lines, which have their own place in the squash body. The squash deletes the branch, so
    the record that commit carries (the ship commit's P5 results and render notes, N21) must
    move into the squash body to stay on the default branch. None for a --title no commit has."""
    if not ctx.base or not ctx.head or not title:
        return []
    out = git(
        ctx.root,
        "log",
        "--no-merges",
        "--reverse",
        "--format=%s%x1f%b%x1e",
        f"{ctx.base}..{ctx.head}",
    )
    for record in (out or "").split("\x1e"):
        subject, sep, body = record.strip("\n").partition("\x1f")
        if not sep or subject != title:
            continue
        paragraphs = body.strip().split("\n\n")
        last = [line for line in paragraphs[-1].splitlines() if line.strip()]
        if last and all(TRAILER_LINE_RE.match(line) or line[:1].isspace() for line in last):
            paragraphs.pop()  # the trailer block (Spec:, Red:, Co-Authored-By: ...)
        lines = [
            line.rstrip()
            for line in "\n\n".join(paragraphs).splitlines()
            if not DISMISSED_RE.match(line.strip())
        ]
        while lines and not lines[-1]:
            lines.pop()
        while lines and not lines[0]:
            lines.pop(0)
        return lines
    return []


def merged_by(trailers: str) -> bool:
    return TOOL_TRAILER[1] in trailer_values(trailers, TOOL_TRAILER[0])


def slugify(text: str) -> str:
    """'Percent flag!' -> 'percent-flag'."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60].strip("-")


def with_status(text: str, old: str, new: str) -> str | None:
    """requirements.md with its frontmatter `status: old` set to new, or None when the
    frontmatter holds no such line."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return None
        match = STATUS_LINE_RE.match(lines[index])
        if match:
            if match.group(3) != old:
                return None
            quote = match.group(2)
            rest = lines[index][match.end() :]
            lines[index] = f"{match.group(1)}{quote}{new}{quote}{rest}"
            return "\n".join(lines)
    return None


def spec_paths(root: Path, ref: str, change_path: str) -> list[str]:
    """What approve approves: every file in the change folder (its three files at least, and
    any note or diagram beside them) and every capability file, at ref ("" reads the index).
    Every capability, not only the ones the change names: an edit to any of them after approve
    is listed by merge."""
    if ref:
        listing = git_lines(root, "ls-tree", "-r", "--name-only", ref, "--", CAPS_DIR, change_path)
    else:
        listing = git_lines(root, "ls-files", "--", CAPS_DIR, change_path)
    caps = [p for p in listing if PurePosixPath(p).parent.as_posix() == CAPS_DIR]
    caps = [p for p in caps if p.endswith(".md")]
    folder = {f"{change_path}/{name}" for name in ("requirements.md", "plan.md", "validation.md")}
    folder |= {p for p in listing if under(p, [change_path])}
    return sorted(set(caps) | folder)


def spec_hash(root: Path, ref: str, change_path: str) -> str:
    """The Spec-Approved: value: sha256 over the paths and contents spec_paths names at ref."""
    paths = spec_paths(root, ref, change_path)
    blobs = read_blobs(root, ref, paths)
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.encode() + b"\0")
        digest.update(blobs.get(path, "").encode("utf-8", "surrogateescape") + b"\0")
    return f"sha256:{digest.hexdigest()}"


def recorded_origin(ctx: Context) -> str:
    """origin_url as .project.toml on the default branch records it (on the branch that adopts
    the repo, before the default branch has one: that branch's copy; before that branch has a
    commit, as render left it in the working tree, which merge never lands: its tree is dirty)."""
    for ref in (ctx.default_ref, "HEAD", None):
        if ref is None:
            text = read_text(ctx.root / ".project.toml")
        elif ref:
            text = read_blobs(ctx.root, ref, [".project.toml"]).get(".project.toml")
        else:
            continue
        if text is None:
            continue
        try:
            value = parse_toml(text).get("origin_url")
        except ValueError:
            return ""
        return value if isinstance(value, str) else ""
    return ""


# What the main guard (.githooks/reference-transaction) unsets before its own git runs, and merge
# before it confirms and fetches origin's default branch: git -c, the GIT_CONFIG_* files, the
# XDG_CONFIG_HOME that picks the user's config, and the GIT_SSH* commands. Both then read only
# the repo's config, ~/.gitconfig and the system's (with the files they include), and take
# core.sshCommand from the last two.
GUARD_UNSET = (
    "GIT_CONFIG_PARAMETERS",
    "GIT_CONFIG_COUNT",
    "GIT_CONFIG_GLOBAL",
    "GIT_CONFIG_SYSTEM",
    "GIT_CONFIG_NOSYSTEM",
    "XDG_CONFIG_HOME",
    "GIT_SSH_COMMAND",
    "GIT_SSH",
    "GIT_SSH_VARIANT",
)


def guard_env(root: Path, env: dict[str, str]) -> dict[str, str]:
    """env for the git that asks origin what its default branch holds, the way the main guard
    asks: GUARD_UNSET removed, and GIT_SSH_COMMAND set to the core.sshCommand of the user's or
    the system's git config, the files they include too (plain ssh when neither sets one), so
    neither the environment nor the repo's own .git/config can send the question to another
    repo."""
    clean = {key: value for key, value in env.items() if key not in GUARD_UNSET}
    command = ""
    for scope in TRUSTED_SCOPES:
        argv = ["git", "config", f"--{scope}", "--includes", "--get", "core.sshCommand"]
        proc = run_cmd(argv, root, clean)
        command = proc.stdout.strip() if proc.returncode == 0 else ""
        if command:
            break
    return {**clean, "GIT_SSH_COMMAND": command or "ssh"}


def own_rewrite(root: Path, url: str) -> str | None:
    """The url.<base>.insteadOf value git rewrites url by (the longest match), when this repo's
    own git config sets it (.git/config, a worktree's config, `git -c`); None when the rule git
    applies comes from the user's or the system's config, or no rule applies. The main guard
    follows only those two: a rule in .git/config could send its `ls-remote origin` elsewhere.
    A tie in length counts as the repo's own, as the guard counts it."""
    out = git(root, "config", "--show-scope", "--get-regexp", r"^url\..*\.insteadof$") or ""
    best: str | None = None
    length = -1
    for line in out.splitlines():
        scope, _, rest = line.partition("\t")
        value = rest.partition(" ")[2]
        if not line or not url.startswith(value):
            continue
        if len(value) > length:
            length, best = len(value), None
        if len(value) == length and scope not in TRUSTED_SCOPES:
            best = value
    return best


def origin_problem(root: Path, url: str, recorded: str) -> str | None:
    """None when origin (url, as `git remote get-url` prints it: after any url.<base>.insteadOf)
    is the repo .project.toml records. Both sides are compared after the rewrite, the way the
    main guard (.githooks/reference-transaction) compares them, so origin_url may be recorded
    either way, and a rule in ~/.gitconfig (https to ssh) is fine; a rule in this repo's own
    config is not, since the guard would not follow it."""
    rewritten = ""
    if recorded and not recorded.startswith("-"):
        rewritten = (git(root, "ls-remote", "--get-url", "--", recorded) or "").strip()
        if rewritten == url:
            local = own_rewrite(root, recorded)
            if local is None:
                return None
            return (
                f"this repo's own git config rewrites origin_url '{recorded}' (url.<base>."
                f"insteadOf '{local}'): main's guard follows only the rewrites in your user or "
                "system git config, so move the rule to ~/.gitconfig"
            )
    after = (
        f" ('{rewritten}' after url.<base>.insteadOf)" if rewritten not in ("", recorded) else ""
    )
    return (
        f"origin is {url}, but .project.toml records origin_url = '{recorded}'{after}: re-run "
        "/project-init to take the remote on (EXTEND), or remove origin"
    )


def project_setting(root: Path, key: str) -> str:
    config = load_toml(root / ".project.toml") if (root / ".project.toml").is_file() else {}
    value = config.get(key)
    return value if isinstance(value, str) else ""


def git_cliff_argv() -> list[str] | None:
    """git-cliff as mise installed it (on PATH inside `mise run`, else through `mise x`), told
    to read [tool.git-cliff] from pyproject.toml. Left to itself it prefers any cliff.toml it
    finds, in a parent folder or the user's config folder, over the project's own config."""
    found = shutil.which("git-cliff")
    mise = shutil.which("mise")
    if found:
        argv = [found]
    elif mise:
        argv = [mise, "x", "--", "git-cliff"]
    else:
        return None
    return [*argv, "--config", "pyproject.toml"]


# ---------------------------------------------------------------- lifecycle: change, backlog


def cmd_change(ctx: Context, args: argparse.Namespace) -> int:
    if not (ctx.root / SPECS).is_dir():
        print(f"FAIL  no {SPECS}/ folder: this repo has no specs yet (run /project-init)")
        return 1
    lane = str(args.lane)
    slug = str(args.slug).strip()
    if args.hotfix and lane != "fix":
        raise UsageError("--hotfix is for the fix lane: change -- <slug> --lane fix --hotfix")
    if args.parallel:
        if lane != "feat":
            raise UsageError("--parallel makes a worker branch of a feat change")
        return change_parallel(ctx, slug)
    if lane == "plan" and not DATE_PREFIX_RE.match(slug):
        slug = f"{today()}-{slug}"
    elif lane != "plan" and DATE_PREFIX_RE.match(slug):
        raise UsageError(
            f"change: '{args.slug}' starts with a date; drop it: only plan/ slugs carry one "
            "(a change folder gets today's date on its own)"
        )
    if not re.fullmatch(CHANGE_SLUG, slug):
        raise UsageError(
            f"change: '{args.slug}' is not a slug (lowercase letters and digits, words joined "
            "by single dashes)"
        )
    if args.hotfix:
        return change_hotfix(ctx, slug)
    if ctx.lane in LANES and not ctx.on_default and ctx.slug == slug:
        return change_ratchet(ctx, lane, slug)
    branch = f"{lane}/{slug}"
    if rev(ctx.root, f"refs/heads/{branch}"):
        print(f"FAIL  {branch} exists already")
        return 1
    dirty = dirty_paths(ctx.root, backlog_ok=True)
    if ctx.on_default:  # nothing commits here: an edited backlog file rides into the branch too
        dirty = [path for path in dirty if not path.startswith(BACKLOG_DIR + "/")]
    if dirty:
        print_dirty(dirty, "commit or stash them first")
        return 1
    busy = open_changes(ctx)
    if busy:
        print(
            f"FAIL  I8: a change is open ({', '.join(busy)}); one change at a time. Finish it "
            f'(`! mise run merge`), drop it (`! mise run abandon -- "<why>"`), or park this one '
            f"(`mise run backlog -- {slug}`). Only an urgent fix starts alongside: "
            f"`mise run change -- {slug} --lane fix --hotfix`"
        )
        return 1
    if ctx.default_ref is None:
        print(f"FAIL  no {ctx.default} branch to start from")
        return 1
    env = lifecycle_env()
    proc = git_run(ctx.root, env, "switch", "-q", "--no-track", "-c", branch, ctx.default_ref)
    if proc.returncode != 0:
        print(f"FAIL  git switch -c {branch}: {said(proc)}")
        return 1
    start = (rev(ctx.root, "HEAD") or "")[:10]
    print(f"change: {branch} off {ctx.default} ({start})")
    if lane == "feat":
        return start_change_folder(ctx.root, slug, "start")
    if lane == "plan":
        print("next: /sdd replan (.claude/skills/sdd/replan.md)")
    else:
        print(
            "next: the fast-lane recipe in .claude/skills/sdd/SKILL.md: red first where behaviour "
            "moves, commit on green, then `mise run status -- --merge`; a human merges"
        )
    return 0


def start_change_folder(root: Path, slug: str, verb: str, proof: str | None = None) -> int:
    """Write specs/changes/<date>-<slug>/ from the templates (status: draft) and commit it as
    `spec(<slug>): <verb>`. A feat branch then starts with its change folder, so I12 (spec
    before code) has a fixed start, and the tree stays clean for the next command. proof: the
    proof folder of the fast lane that ratchets to feat, moved (git mv) in the same commit to
    the change folder's name, so its captures carry over."""
    name = f"{today()}-{slug}"
    folder = root / CHANGES_DIR / name
    if folder.exists():
        print(f"FAIL  {CHANGES_DIR}/{name} exists already")
        return 1
    folder.mkdir(parents=True)
    values = {"DATE": today(), "SLUG": slug, "ROADMAP_SLUG": slug}
    for file, template in CHANGE_TEMPLATES.items():
        (folder / file).write_text(fill(template, values), encoding="utf-8")
    rel = f"{CHANGES_DIR}/{name}"
    env = lifecycle_env()
    paths = [rel, *carry_proof(root, proof, name)]
    proc = git_run(root, env, "add", "--", rel)
    if proc.returncode == 0:
        proc = git_run(root, env, "commit", "-q", "-m", f"spec({slug}): {verb}", "--", *paths)
    for file in CHANGE_TEMPLATES:
        extra = "  (status: draft)" if file == "requirements.md" else ""
        print(f"  {rel}/{file}{extra}")
    if proc.returncode != 0:
        print(f"FAIL  the change folder is written but not committed: {said(proc)}")
        return 1
    for item in scheduled_backlog(root, slug):
        print(f"  {item}: this item's backlog entry; talk moves its content into requirements.md")
    print(
        "next: talk (.claude/skills/sdd/talk.md) fills the three files and the scenarios in "
        "specs/capabilities/, until `mise run status` says ready for approve; then a human runs "
        "`! mise run approve`"
    )
    return 0


def carry_proof(root: Path, old: str | None, new: str) -> list[str]:
    """git mv proof/<old>/ to proof/<new>/, its README.md titled for the new name: the paths
    the ratchet's commit takes along, [] when there is no tracked folder to move."""
    source, target = f"{PROOF_DIR}/{old}", f"{PROOF_DIR}/{new}"
    if not old or old == new or not git_lines(root, "ls-files", "--", source):
        return []
    if (root / target).exists():
        print(f"warn  {source}/ stays: {target}/ exists already")
        return []
    proc = git_run(root, lifecycle_env(), "mv", "--", source, target)
    if proc.returncode != 0:
        print(f"warn  {source}/ stays where it is: git mv failed ({said(proc)})")
        return []
    readme = root / target / PROOF_INDEX
    text = read_text(readme)
    if text is not None and text.startswith(f"# Proof: {old}\n"):
        readme.write_text(f"# Proof: {new}\n" + text.split("\n", 1)[1], encoding="utf-8")
        git_run(root, lifecycle_env(), "add", "--", f"{target}/{PROOF_INDEX}")
    print(f"  {source}/ moves to {target}/ (its captures carry over)")
    return [source, target]


def scheduled_backlog(root: Path, slug: str) -> list[str]:
    folder = root / BACKLOG_DIR
    if not folder.is_dir():
        return []
    return [
        f"{BACKLOG_DIR}/{path.name}"
        for path in sorted(folder.glob("*.md"))
        if frontmatter(read_text(path) or "")[0].get("roadmap") == slug
    ]


def change_ratchet(ctx: Context, lane: str, slug: str) -> int:
    """`change <slug> --lane <heavier>` on <lane>/<slug>: rename the branch in place (feat adds
    its change folder). A lane only gets heavier; plan/ neither ratchets nor is reached so."""
    current = ctx.lane or ""
    branch = ctx.branch or ""
    if lane == current:
        print(f"change: already on {branch}")
        return 0
    if "plan" in (lane, current) or LANE_WEIGHT[lane] <= LANE_WEIGHT[current]:
        print(
            f"FAIL  a lane only gets heavier: {current}/ to {lane}/ is refused "
            f'(specs/README.md#lanes). To start over: `! mise run abandon -- "<why>"`'
        )
        return 1
    new = f"{lane}/{slug}"
    if rev(ctx.root, f"refs/heads/{new}"):
        print(f"FAIL  {new} exists already")
        return 1
    proof = proof_name(ctx, None)  # the fast lane's folder; feat names it after the change
    proc = git_run(ctx.root, lifecycle_env(), "branch", "-m", branch, new)
    if proc.returncode != 0:
        print(f"FAIL  git branch -m {branch} {new}: {said(proc)}")
        return 1
    record = tdd_record_path(ctx)
    if record.is_file():
        moved = ctx.root / TDD_DIR / f"{new}.json"
        moved.parent.mkdir(parents=True, exist_ok=True)
        record.replace(moved)
    print(f"change: {branch} is now {new}")
    if lane == "feat":
        return start_change_folder(ctx.root, slug, f"ratchet {current} to feat", proof)
    return 0


def change_hotfix(ctx: Context, slug: str) -> int:
    """A fix/ branch in a worktree of its own, next to this checkout, off the default branch.
    The open change's tree is untouched; a human lands it with merge --branch."""
    branch = f"fix/{slug}"
    path = ctx.root.parent / f"{ctx.root.name}-fix-{slug}"
    if rev(ctx.root, f"refs/heads/{branch}"):
        print(f"FAIL  {branch} exists already")
        return 1
    if path.exists():
        print(f"FAIL  {path} exists already")
        return 1
    if ctx.default_ref is None:
        print(f"FAIL  no {ctx.default} branch to start from")
        return 1
    env = lifecycle_env()
    proc = git_run(
        ctx.root,
        env,
        "worktree",
        "add",
        "-q",
        "--no-track",
        "-b",
        branch,
        str(path),
        ctx.default_ref,
    )
    if proc.returncode != 0:
        print(f"FAIL  git worktree add {path}: {said(proc)}")
        return 1
    print(f"change: {branch} in the worktree {path}, off {ctx.default}")
    here = (
        f"the change open here ({ctx.branch}) is untouched"
        if ctx.lane in LANES and not ctx.on_default
        else "this checkout is untouched"
    )
    print(
        f"next: work there (cd {path}); {here}. A human lands it with "
        f"`! mise run merge -- --branch {branch}`"
    )
    return 0


def change_parallel(ctx: Context, slug: str) -> int:
    """`change <slug>--g<n> --parallel`: the worker branch feat/<slug>--g<n> off feat/<slug>,
    for group G<n> of its approved plan, which must say `parallel: yes`. Workers merge into
    feat/<slug> with git merge, never into the default branch."""
    match = WORKER_RE.search(slug)
    base = slug[: match.start()] if match else ""
    if match is None or not re.fullmatch(CHANGE_SLUG, base):
        raise UsageError("--parallel takes a worker slug: change -- <slug>--g<n> --parallel")
    number = int(match.group(1))
    parent = f"feat/{base}"
    tip = rev(ctx.root, f"refs/heads/{parent}")
    if tip is None:
        print(f"FAIL  no {parent}: a worker branches off an open feat change")
        return 1
    listing = git_lines(ctx.root, "ls-tree", "--name-only", tip, f"{CHANGES_DIR}/")
    names = [PurePosixPath(p).name for p in listing]
    folders = [n for n in names if (m := CHANGE_DIR_RE.match(n)) and m.group(1) == base]
    texts = read_blobs(ctx.root, tip, [f"{CHANGES_DIR}/{n}/requirements.md" for n in folders])
    live = [
        name
        for name in folders
        if frontmatter(texts.get(f"{CHANGES_DIR}/{name}/requirements.md", ""))[0].get("status")
        == "approved"
    ]
    if not live:
        print(f"FAIL  {parent} has no approved change folder: parallel groups start after approve")
        return 1
    plan_path = f"{CHANGES_DIR}/{live[-1]}/plan.md"
    plan = read_blobs(ctx.root, tip, [plan_path]).get(plan_path, "")
    group = next((g for g in parse_groups(plan, None, "") if g.number == number), None)
    if group is None or group.parallel != "yes":
        print(f"FAIL  G{number} of {plan_path} is not a `parallel: yes` group")
        return 1
    worker = f"feat/{slug}"
    if rev(ctx.root, f"refs/heads/{worker}"):
        print(f"FAIL  {worker} exists already")
        return 1
    proc = git_run(ctx.root, lifecycle_env(), "branch", "--no-track", worker, tip)
    if proc.returncode != 0:
        print(f"FAIL  git branch {worker}: {said(proc)}")
        return 1
    print(f"change: {worker} off {parent} ({tip[:10]}) for G{number} {group.name}")
    print(
        f"next: check it out in the worker's own worktree (git worktree add <dir> {worker}); it "
        f"merges into {parent} with git merge, never into {ctx.default}"
    )
    return 0


def cmd_backlog(ctx: Context, args: argparse.Namespace) -> int:
    """Park an idea: specs/backlog/<date>-<slug>.md from the template, status open. It is not
    committed: on a lane branch it goes in with the branch; on the default branch it waits,
    untracked, for the next change. --spike adds a scratch worktree, detached at the default
    branch, to answer the question in; only the findings (this file) ever land."""
    topic = " ".join(args.topic).strip()
    slug = slugify(topic)
    if not slug:
        raise UsageError("backlog needs a topic: backlog -- <topic> [--spike]")
    if not (ctx.root / SPECS).is_dir():
        print(f"FAIL  no {SPECS}/ folder: this repo has no specs yet (run /project-init)")
        return 1
    rel = f"{BACKLOG_DIR}/{today()}-{slug}.md"
    path = ctx.root / rel
    if path.exists():
        print(f"FAIL  {rel} exists already: edit it, or name another topic")
        return 1
    notes = "{NOTES}"
    title = topic
    if args.spike:
        spike = ctx.root.parent / f"{ctx.root.name}-spike-{slug}"
        if spike.exists():
            print(f"FAIL  {spike} exists already")
            return 1
        if ctx.default_ref is None:
            print(f"FAIL  no {ctx.default} branch to start the spike from")
            return 1
        proc = git_run(
            ctx.root,
            lifecycle_env(),
            "worktree",
            "add",
            "-q",
            "--detach",
            str(spike),
            ctx.default_ref,
        )
        if proc.returncode != 0:
            print(f"FAIL  git worktree add {spike}: {said(proc)}")
            return 1
        title = f"Spike: {topic}"
        notes = (
            f"Spike worktree: {spike} (detached at {ctx.default}). Answer the question there and "
            f"write the findings here. Then remove it: `git worktree remove --force {spike}`. "
            "Its code is never merged."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(fill(BACKLOG_TEMPLATE, {"TITLE": title, "NOTES": notes}), encoding="utf-8")
    print(f"backlog: {rel} (status: open)")
    if args.spike:
        print(f"spike: scratch worktree {ctx.root.parent / f'{ctx.root.name}-spike-{slug}'}")
    where = "commit it with this branch" if ctx.lane else "it waits, untracked, for the next change"
    print(f"next: fill What, Why and Notes; {where}")
    return 0


# ---------------------------------------------------------------- lifecycle: approve


def cmd_approve(ctx: Context, args: argparse.Namespace) -> int:
    """G2: lint the open feat change (approve_lint), set `status: approved`, and commit the
    change folder, the capabilities and the backlog as `spec(<slug>): approve` with the
    `Spec-Approved: sha256:<hash>` trailer merge checks (I6)."""
    del args
    state = load_state(ctx)
    change = state.open_change
    if ctx.lane != "feat" or change is None:
        where = ctx.branch or "detached HEAD"
        print(f"FAIL  approve works on a feat/ branch with its change folder; {where} has none")
        return 1
    if change.status != "draft":
        print(f"FAIL  {change.path} is {change.status or 'without a status'}, not draft")
        return 1
    lint = approve_lint(state, change)
    if lint.errors:
        lint.print()
        print(f"approve: refused ({plural(lint.errors, 'problem')}); fix them, then approve again")
        return 1
    root = ctx.root
    paths = [change.path, CAPS_DIR, BACKLOG_DIR]
    paths = [p for p in paths if (root / p).exists() or git_lines(root, "ls-files", "--", p)]
    staged = git_lines(root, "diff", "--cached", "--name-only", "--no-renames")
    stray = [p for p in staged if not under(p, paths)]
    if stray:
        print(
            f"FAIL  staged outside the spec, and approve commits only the spec: {', '.join(stray)}"
        )
        print("      unstage them (git restore --staged <path>), then approve again")
        return 1
    req = root / change.path / "requirements.md"
    before = req.read_text(encoding="utf-8")
    approved = with_status(before, "draft", "approved")
    if approved is None:
        print(f"FAIL  {change.path}/requirements.md has no `status: draft` line to move")
        return 1
    req.write_text(approved, encoding="utf-8")
    env = lifecycle_env()
    proc = git_run(root, env, "add", "-A", "--", *paths)
    digest = spec_hash(root, "", change.path)
    if proc.returncode == 0:
        message = f"spec({change.slug}): approve"
        proc = git_run(
            root, env, "commit", "-q", "-m", message, "--trailer", f"{SPEC_APPROVED}: {digest}"
        )
    if proc.returncode != 0:
        req.write_text(before, encoding="utf-8")
        git_run(root, env, "add", "--", str(req.relative_to(root)))
        print(f"FAIL  the approve commit was refused:\n{said(proc, 20)}")
        return 1
    sha = rev(root, "HEAD") or ""
    print(
        f"approved: {change.path} ({sha[:10]} spec({change.slug}): approve, "
        f"{SPEC_APPROVED}: {digest})"
    )
    code_before_approve(ctx, change, sha)
    print("next: a fresh context (/clear), then /sdd compile")
    return 0


def code_before_approve(ctx: Context, change: Change, sha: str) -> None:
    """Tell the human who just approved about code already on the branch: a fast lane's work
    from before its ratchet to feat (merge asks about it at G3), or code committed after the
    change folder but before this approve (merge refuses it: I12)."""
    if not ctx.base or not sha:
        return
    src_roots = project_paths(ctx.root)[0]
    roots = ", ".join(src_roots)
    start, ratchet = folder_start(ctx, change)
    early = code_before_folder(ctx, start) if ratchet else []
    if early:
        listed = "; ".join(f"{commit[:10]} {subject}" for commit, subject in early)
        print(
            f"note: {plural(len(early), 'commit')} touched {roots} before the ratchet to feat, "
            f"so this approval came after that code ({listed}); merge asks a human about it"
        )
    seen = {commit for commit, _ in early}
    span = f"{ctx.base}..{sha}"
    touching = git_lines(ctx.root, "rev-list", "--no-merges", "--reverse", span, "--", *src_roots)
    late = [commit for commit in touching if commit not in seen]
    if late:
        print(
            f"warn: {late[0][:10]} touched {roots} before this approve; merge refuses it "
            "(I12, spec before code)"
        )


# ---------------------------------------------------------------- lifecycle: the Definition of Done

# `merge` checks the Definition of Done (specs/README.md#definition-of-done) in two passes: the
# cheap checks first (tree, lane, hooks, the lane rules, what changed since approve, human checks,
# gate files, what the close commit would write, how the branch lands), then verify, prove-red
# and the Run it rows. Only when every step passes does it write: the close commit on the
# branch, then the landing.
# `status --merge` and `merge --dry-run` run both passes and write nothing.


@dataclass
class Step:
    order: int  # the step of the Definition of Done it belongs to
    name: str
    level: str  # ok | FAIL | warn | human (a person decides: merge asks, or needs a flag)
    summary: str = ""
    details: list[str] = field(default_factory=list)
    sub: int = 0  # its place among the steps of the same order: proof comes after Run it


@dataclass
class MergeFlags:
    attest: bool = False
    read_trunk: bool = False  # the human read the trunk diff (I19), for a merge with no terminal
    gate_change: bool = False
    reapprove: bool = False  # the approved Human checks and Run it rows changed, on purpose
    allow: list[str] = field(default_factory=list)
    reason: str = ""
    title: str | None = None
    without_ci: str = ""  # why a pull request whose CI never reported may land anyway
    tty: bool = False
    preview: bool = False  # status --merge: report what a human decides instead of failing on it


@dataclass
class HumanCheck:
    text: str
    diff: str = ""  # a Test-Harness: commit's diff, shown before the question


@dataclass
class Dod:
    ctx: Context
    state: State
    change: Change | None
    flags: MergeFlags
    title: str = ""
    steps: list[Step] = field(default_factory=list)
    stop: bool = False  # not a lane branch: nothing else can be judged
    closing: bool = False  # HEAD is already merge's close commit (a merge run again)
    checks: list[HumanCheck] = field(default_factory=list)
    writes: dict[str, str] = field(default_factory=dict)  # what the close commit writes
    roadmap_note: str = ""
    changelog_note: str = ""
    landing: str = "local"  # local | remote
    proof: ProveRed | None = None
    approved_at: str | None = None  # the approve commit of a feat change
    early_code: list[tuple[str, str]] = field(default_factory=list)  # src before a ratchet
    amended: list[str] = field(default_factory=list)  # scenario ids changed since approve
    amended_files: list[str] = field(default_factory=list)  # spec files changed since approve
    dropped: list[str] = field(default_factory=list)  # approved checks gone from validation.md
    gate_paths: list[str] = field(default_factory=list)  # gate files the branch changes
    depth: ReviewDepth = field(default_factory=lambda: ReviewDepth())  # trunk READ, leaf SKIM
    trunk_read: str = ""  # the squash body's record of who read the trunk diff (I19)
    bundle: ProofBundle | None = None  # the branch's proof folder (design C)

    @property
    def problems(self) -> int:
        return sum(1 for step in self.steps if step.level == "FAIL")

    @property
    def ok(self) -> bool:
        return self.problems == 0


def label(name: str) -> str:
    """'  name ........ ': the left column of merge's report."""
    return f"  {name} {'.' * max(2, 18 - len(name))} "


def print_steps(steps: list[Step]) -> None:
    shown = {"ok": "ok", "FAIL": "FAIL", "warn": "warn", "human": "for a human"}
    for step in sorted(steps, key=lambda s: (s.order, s.sub)):
        text = label(step.name) + shown[step.level]
        print(text + (f" {step.summary}" if step.summary else ""))
        for line in step.details:
            print(f"      {line}")


def dod_prepare(ctx: Context, flags: MergeFlags) -> Dod:
    """The cheap pass: steps 1, 3 (hooks, the lane rules, trunk files in the plan, what changed
    since approve), 4 (the proof bundle; Run it runs in the slow pass), 5 (human checks, the
    trunk diff), 6, 7 (what the close commit writes) and 8 (how)."""
    state = load_state(ctx)
    dod = Dod(ctx, state, state.open_change, flags)
    dod.steps.append(step_tree(ctx))
    dod.steps.append(step_lane(dod))
    if dod.stop:
        return dod
    dod.depth = review_depth(ctx)
    dod.bundle = load_bundle(ctx, dod.change)
    dod.steps.append(step_hooks(ctx))
    dod.steps.append(step_lane_rules(dod))
    if ctx.lane == "feat" and dod.change is not None:
        dod.steps.append(step_trunk_plan(dod))
    if dod.approved_at is not None:
        dod.steps.append(step_amended(dod))
    dod.steps.append(step_proof(dod))
    dod.steps.append(step_human_checks(dod))
    dod.steps.append(step_trunk(dod))
    dod.steps.append(step_gate_files(dod))
    dod.steps.append(step_close(dod))
    dod.steps.append(step_landing(dod))
    return dod


def dod_prove(dod: Dod) -> None:
    """The slow pass: steps 2, 3 (prove-red) and 4, then step 7 again (reclose)."""
    dod.steps.append(step_verify(dod))
    dod.steps.append(step_prove_red(dod))
    dod.steps.append(step_run_it(dod))
    reclose(dod)


def reclose(dod: Dod) -> None:
    """Step 7 worked out again once prove-red ran: the ## Tests section the close commit writes
    carries prove-red's verdicts and the last test run, which the cheap pass does not know yet.
    So the preview names the proof README write whenever merge's close commit makes it."""
    if dod.bundle is not None:
        dod.writes.pop(f"{dod.bundle.folder}/{PROOF_INDEX}", None)
    dod.steps = [step for step in dod.steps if step.order != 7]
    dod.steps.append(step_close(dod))


def step_tree(ctx: Context) -> Step:
    dirty = dirty_paths(ctx.root)
    if not dirty:
        return Step(1, "tree clean", "ok")
    shown = dirty[:10] + ([f"... and {len(dirty) - 10} more"] if len(dirty) > 10 else [])
    return Step(1, "tree clean", "FAIL", f"{plural(len(dirty), 'file')} not committed", shown)


def step_lane(dod: Dod) -> Step:
    ctx = dod.ctx
    stop = None
    if ctx.branch is None:
        stop = "a detached HEAD: merge lands a lane branch"
    elif ctx.on_default:
        stop = f"on {ctx.default}: merge lands a lane branch; switch to it, or pass --branch <b>"
    elif ctx.lane is None:
        stop = f"{ctx.branch} is not a lane branch (feat/ chg/ fix/ chore/ refactor/ plan/)"
    elif ctx.lane == "release":
        stop = "a release branch lands through `! mise run release`"
    elif WORKER_RE.search(ctx.branch):
        stop = (
            f"{ctx.branch} is a parallel worker: it merges into feat/{ctx.slug} with git merge, "
            f"never into {ctx.default}"
        )
    elif ctx.default_ref is None or ctx.head is None:
        stop = f"no {ctx.default} branch, or no commit on {ctx.branch}"
    if stop is not None:
        dod.stop = True
        return Step(1, "lane", "FAIL", details=[stop])
    root, lane = ctx.root, ctx.lane or ""
    problems: list[str] = []
    if not is_ancestor(root, ctx.default_ref or "", "HEAD"):
        problems.append(
            f"{ctx.default} moved: run git merge {ctx.default}, then merge again (merge lands "
            "only what it verified)"
        )
    head_trailers = "\n".join(commit_trailers(root, "-1", "HEAD"))
    change = dod.change
    summary = lane
    if lane == "feat":
        if change is None:
            problems.append(f"no change folder for {ctx.branch} under {CHANGES_DIR}/")
        else:
            dod.closing = change.status == "done" and is_close_commit(dod, head_trailers)
            summary += f", change {change.name} ({change.status or 'no status'})"
            if change.status == "draft":
                problems.append(
                    f"{change.path} is a draft: a human runs `! mise run approve` first"
                )
            elif change.status not in ("approved", "done") or (
                change.status == "done" and not dod.closing
            ):
                problems.append(f"{change.path} is {change.status or 'without a status'}")
            dod.title = change.fields.get("title", "")
            slug = change.roadmap
            if not dod.closing and dod.state.roadmap.get(slug):
                problems.append(
                    f"roadmap item '{slug}' is ticked already; name a new slug in "
                    f"{change.path}/requirements.md (roadmap:)"
                )
        if dod.flags.title:
            problems.append(
                "--title is for the fast lanes: a feat title is requirements.md's title"
            )
    else:
        dod.closing = is_close_commit(dod, head_trailers)
        dod.title, problem = fast_lane_title(ctx, dod.flags.title)
        if problem:
            problems.append(problem)
    if dod.title and not TITLE_RE.match(dod.title):
        problems.append(f"the title '{dod.title}' is not a conventional commit subject")
    if dod.title:
        summary += f"; lands as '{dod.title}'"
    return Step(1, "lane", "FAIL" if problems else "ok", summary, problems)


def is_close_commit(dod: Dod, head_trailers: str) -> bool:
    """True when HEAD is merge's own close commit, left by a merge that stopped after it (a
    landing that failed): the trailer, and nothing close_commit_problem objects to."""
    head = dod.ctx.head
    if not head or not merged_by(head_trailers):
        return False
    return close_commit_problem(dod.state, head, head) is None


def fast_lane_title(ctx: Context, given: str | None) -> tuple[str, str | None]:
    """The squash subject of a fast-lane or plan/ branch: --title, else its first commit of a
    type the lane lands under, else its first commit. The type decides the CHANGELOG line, so a
    type the lane never writes one for (a feat: subject on fix/) is refused."""
    lane = ctx.lane or ""
    types = LANE_TITLE_TYPES.get(lane, ())
    if given:
        title = given.strip()
    else:
        subjects = [  # a proof capture is never the work a branch lands
            subject
            for _, subject, trailers in branch_commits(ctx)
            if not merged_by(trailers) and not subject.startswith("docs(proof): ")
        ]
        typed = [
            s
            for s in subjects
            if (m := TITLE_PARTS_RE.match(s)) is not None and m.group(1) in types
        ]
        title = (typed or subjects or [""])[0]
    if not title:
        return "", f"{ctx.branch} has no commit of its own to land"
    entry = changelog_entry(title)
    if entry and ctx.branch != INIT_BRANCH and entry[0] not in LANE_CHANGELOG_GROUPS.get(lane, ()):
        return title, (
            f"the squash subject '{title}' puts a CHANGELOG line under '### {entry[0]}', which a "
            f"{lane}/ branch never writes; pass --title with a type from: {', '.join(types)}"
        )
    return title, None


def rendered_hashes(root: Path) -> dict[str, str]:
    """.project.toml [generated]: the sha256 of every file project-init rendered, as it wrote it."""
    path = root / ".project.toml"
    try:
        table = load_toml(path).get("generated") if path.is_file() else None
    except UsageError:
        return {}
    return {k: v for k, v in table.items() if isinstance(v, str)} if isinstance(table, dict) else {}


def file_sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def fresh_render_problem(root: Path, path: str, rendered: dict[str, str]) -> str | None:
    """A hook file with no committed blob yet: project-init just rendered it (the adoption
    branch before its ship commit). It passes while the working copy, and the staged one if it
    is staged, are the bytes .project.toml [generated] records for it."""
    record = rendered.get(path)
    try:
        data = (root / path).read_bytes()
    except OSError:
        return f"{path} is not committed"
    if record is None:
        return f"{path} is not committed, and .project.toml [generated] does not record it"
    if file_sha256(data) != record:
        return f"{path} differs from what project-init rendered (.project.toml [generated])"
    staged = run_git(root, "cat-file", "blob", f":{path}")
    if staged.returncode == 0 and file_sha256(staged.stdout) != record:
        return f"{path} as staged differs from what project-init rendered"
    return None


def gate_setup_problems(ctx: Context) -> list[str]:
    """The git config `hook install` sets, the guard's record of the default branch, and the
    hook files as HEAD has them (step 3). Before the ship commit of the adoption, a hook HEAD
    lacks passes while it is the file project-init rendered (fresh_render_problem)."""
    try:
        wanted = gate_config(ctx.root, ctx.default)
    except UsageError as exc:
        return [str(exc)]
    problems = []
    for key, value, _ in wanted:
        have = (git(ctx.root, "config", "--get-all", key) or "").splitlines()
        if have != [value]:
            state = "unset" if not have else "not what `hook install` sets"
            problems.append(f"git config {key} is {state}: run mise install")
    if tripped := main_record_problem(ctx.root, ctx.default):
        problems.append(tripped)
    tracked = git_lines(ctx.root, "ls-tree", "-r", "--name-only", "HEAD", "--", ".githooks")
    rendered = rendered_hashes(ctx.root)
    present = list(tracked)
    hooks = [f".githooks/{name}" for name in (*HOOKS, "reference-transaction")]
    for path in hooks:
        if path in tracked:
            continue
        problem = fresh_render_problem(ctx.root, path, rendered)
        if problem:
            problems.append(problem)
        else:
            present.append(path)
    for path in git_lines(ctx.root, "diff", "--name-only", "HEAD", "--", ".githooks"):
        if path in tracked or path not in hooks:  # a fresh render was judged just above
            problems.append(f"{path} differs from HEAD's copy")
    for path in present:
        if not os.access(ctx.root / path, os.X_OK):
            problems.append(f"{path} is not executable, so git skips it")
    return problems


def step_hooks(ctx: Context) -> Step:
    problems = gate_setup_problems(ctx)
    if problems:
        return Step(3, "hooks", "FAIL", details=problems)
    count = len(git_lines(ctx.root, "ls-tree", "-r", "--name-only", "HEAD", "--", ".githooks"))
    matched = f"{count} files match HEAD" if count else "the hooks are project-init's render"
    return Step(3, "hooks", "ok", f"core.hooksPath=.githooks, {matched}")


def human_checks_of(change: Change, text: str, scenarios: dict[str, Scenario]) -> list[str]:
    """The Human checks of a validation.md text, read the way approve lints it."""
    copy = replace(change, review_ids=[], human_checks=[], proof_rows=[])
    lint_validation(copy, text, scenarios, Report())
    return copy.human_checks


def step_human_checks(dod: Dod) -> Step:
    """Step 5: the change's Human checks, its own one-way check (a `one-way:` Rollback line;
    it is not one of validation.md's 3), the code a fast lane wrote before its ratchet to feat
    (so before approve), and the Test-Harness: diffs of chore/ and refactor/."""
    ctx, flags = dod.ctx, dod.flags
    checks: list[HumanCheck] = []
    if dod.change is not None:
        text = read_text(ctx.root / dod.change.path / "validation.md") or ""
        for check in human_checks_of(dod.change, text, dod.state.scenarios):
            checks.append(HumanCheck(check))
        rollback = change_rollback(ctx.root, dod.change)
        if rollback is not None and rollback.kind == "one-way":
            checks.append(HumanCheck(f"I read the one-way part: {rollback.value}"))
    if dod.early_code:
        roots = ", ".join(project_paths(ctx.root)[0])
        listed = "; ".join(f"{sha[:10]} {subject}" for sha, subject in dod.early_code)
        shas = [sha for sha, _ in dod.early_code]
        stat = git(ctx.root, "show", "--no-color", "--stat", "--format=%h %s", *shas) or ""
        text = (
            f"Code before approve: {plural(len(shas), 'commit')} touched {roots} before the "
            f"ratchet to feat, so G2 approved a spec written after this code ({listed})"
        )
        checks.append(HumanCheck(text, stat.rstrip()))
    if ctx.lane in ("chore", "refactor"):
        for edit in edited_test_files(ctx):
            if edit.reason:
                diff = git(ctx.root, "show", "--no-color", "--format=", edit.sha, "--", *edit.files)
                text = f"Test-Harness {edit.sha[:10]} ({', '.join(edit.files)}): {edit.reason}"
                checks.append(HumanCheck(text, (diff or "").rstrip()))
    dod.checks = checks
    if not checks:
        return Step(5, "human checks", "ok", "none")
    lines = [f"- {check.text}" for check in checks]
    for check in checks:
        if check.diff:
            lines += ["", *check.diff.splitlines()[:60], ""]
    count = plural(len(checks), "check")
    if flags.attest:
        return Step(5, "human checks", "ok", f"{count}, attested by {user_name(ctx.root)}", lines)
    if flags.preview:
        return Step(
            5,
            "human checks",
            "human",
            f"{count}: merge asks for each in a terminal, or `! mise run merge -- --attest`",
            lines,
        )
    if flags.tty:
        return Step(5, "human checks", "ok", f"{count}, asked below", lines)
    return Step(
        5,
        "human checks",
        "FAIL",
        f"{count} and no terminal to ask in: read them, then `! mise run merge -- --attest`",
        lines,
    )


def gate_changes(ctx: Context) -> tuple[list[str], list[str]]:
    """(what changed, paths to diff) among the gate files since the merge-base, and a Trunk entry
    of specs/tech-stack.md removed or changed (I20: shrinking the trunk dodges review). The
    branch that adopts the repo brings every gate in for the first time; that is G1's review,
    not a change."""
    if not ctx.base or not ctx.head:
        return [], []
    if ".project.toml" not in git_lines(ctx.root, "ls-tree", "--name-only", ctx.base):
        return [], []
    changed = git_lines(ctx.root, "diff", "--name-only", "--no-renames", ctx.base, ctx.head)
    paths = [
        p
        for p in changed
        if p in GATE_FILES or under(p, [g for g in GATE_FILES if g.endswith("/")])
    ]
    what = list(paths)
    if TECH_STACK in changed and (gone := trunk_narrowed(ctx.root, ctx.base, ctx.head)):
        what.append(f"{TECH_STACK} ## Trunk (removed or changed: {', '.join(gone)})")
        paths.append(TECH_STACK)
    for name in MISE_CONFIGS:
        if name not in changed:
            continue
        before = read_blobs(ctx.root, ctx.base, [name]).get(name, "")
        after = read_blobs(ctx.root, ctx.head, [name]).get(name, "")
        try:
            old, new = parse_toml(before or ""), parse_toml(after or "")
            tables = [t for t in GATE_MISE_TABLES if old.get(t) != new.get(t)]
        except ValueError:
            tables = list(GATE_MISE_TABLES)  # unreadable on one side: treat both as changed
        if tables:
            what += [f"{name} [{table}]" for table in tables]
            paths.append(name)
    return what, paths


def trunk_narrowed(root: Path, base: str, head: str) -> list[str]:
    """I20: the globs of the Trunk entries at base that head no longer holds word for word
    (removed, or changed: another glob or another why). Adding an entry is free."""
    kept = {(entry.glob, entry.why) for entry in trunk_at(root, head).entries}
    return [e.glob for e in trunk_at(root, base).entries if (e.glob, e.why) not in kept]


@dataclass
class ReviewDepth:
    """How much of the branch diff a human reads (specs/README.md, "Definition of Done"): each
    trunk file in full (READ), every other path, tests included, skimmed (SKIM)."""

    trunk: list[tuple[str, TrunkEntry]] = field(default_factory=list)
    leaf: list[str] = field(default_factory=list)
    lines: dict[str, tuple[int, int]] = field(default_factory=dict)  # path -> (added, removed)

    def counts(self, paths: list[str]) -> str:
        added = sum(self.lines.get(path, (0, 0))[0] for path in paths)
        removed = sum(self.lines.get(path, (0, 0))[1] for path in paths)
        return f"+{added} -{removed}"


def branch_trunk(ctx: Context) -> TrunkMap:
    """The trunk a merge reads by: HEAD's entries, plus those of the merge-base that HEAD
    dropped or changed. Until a human lands that edit (I20), the old entry still counts."""
    trunk = trunk_at(ctx.root, ctx.head) if ctx.head else TrunkMap()
    if ctx.base:
        globs = {entry.glob for entry in trunk.entries}
        older = trunk_at(ctx.root, ctx.base).entries
        trunk.entries += [entry for entry in older if entry.glob not in globs]
    return trunk


def review_depth(ctx: Context) -> ReviewDepth:
    """The branch diff (merge-base..HEAD) split into trunk and leaf files, with +/- lines. The
    proof folder is neither: it is what the leaf is skimmed against."""
    depth = ReviewDepth()
    if not ctx.base or not ctx.head:
        return depth
    trunk = branch_trunk(ctx)
    stat = run_git(ctx.root, "diff", "--numstat", "-z", "--no-renames", ctx.base, ctx.head)
    for record in z_paths(stat.stdout):
        added, removed, path = (record.split("\t", 2) + ["", ""])[:3]
        if not path or under(path, [PROOF_DIR]):
            continue
        depth.lines[path] = (
            int(added) if added.isdigit() else 0,
            int(removed) if removed.isdigit() else 0,
        )
        if entry := trunk.entry_for(path):
            depth.trunk.append((path, entry))
        else:
            depth.leaf.append(path)
    return depth


def leaf_evidence(dod: Dod) -> str:
    """What the leaf diff is skimmed against, for the review depth block: "" until the proof
    bundle (design part C) records captures, then e.g. "proof: 9 entries, confidence G1 high,
    G2 medium". The one place part C hooks into this block."""
    return bundle_evidence(dod.bundle)


def review_lines(dod: Dod) -> list[str]:
    """The review depth block: trunk READ (files, +/- lines, each file's why), leaf SKIM."""
    return depth_lines(dod.depth, leaf_evidence(dod))


def depth_lines(depth: ReviewDepth, evidence: str) -> list[str]:
    """review_lines() of a ReviewDepth, the leaf line ending 'against <evidence>' when given."""
    paths = [path for path, _ in depth.trunk]
    trunk = f"trunk: READ  {plural(len(paths), 'file')}"
    if paths:
        whys = ", ".join(f"{path} ({entry.why})" for path, entry in depth.trunk)
        trunk += f"  {depth.counts(paths)}  {whys}"
    leaf = f"leaf:  SKIM  {plural(len(depth.leaf), 'file')}"
    if depth.leaf:
        leaf += f"  {depth.counts(depth.leaf)}"
    if evidence:
        leaf += f"  against {evidence}"
    return [trunk, leaf]


def print_review(dod: Dod) -> None:
    if dod.stop:
        return
    trunk, leaf = review_lines(dod)
    print(f"review depth  {trunk}")
    print(f"              {leaf}")


def step_trunk_plan(dod: Dod) -> Step:
    """Step 3, I18 (feat): each trunk file the branch diff touches is in the Files: of a
    risk: high group, so compile paused on it. The fix for a trunk file the plan called leaf is
    a plan.md edit, which merge then lists as amended after approval."""
    change, touched = dod.change, dod.depth.trunk
    name = "trunk in plan"
    if change is None or not touched:
        return Step(3, name, "ok", "no trunk file touched")
    listed = [glob_regex(path) for g in change.groups if g.risk == "high" for path in g.files]
    plan = f"{change.path}/plan.md"
    problems = [
        f"{path}: the plan said leaf, the diff touched trunk ({entry.why}): add it to a "
        f"risk: high group's Files: in {plan}"
        for path, entry in touched
        if not any(pattern.fullmatch(path) for pattern in listed)
    ]
    if problems:
        summary = f"{plural(len(problems), 'trunk file')} outside a risk: high group"
        return Step(3, name, "FAIL", summary, problems)
    return Step(3, name, "ok", f"{plural(len(touched), 'trunk file')}, each in a risk: high group")


def step_trunk(dod: Dod) -> Step:
    """Step 5, I19: the branch diff limited to trunk files, shown in full. A human confirms
    reading it: y at merge's prompt in a terminal, or --read-trunk without one; the squash body
    records who. A branch that touches no trunk file asks nothing."""
    ctx, flags = dod.ctx, dod.flags
    touched = dod.depth.trunk
    if not touched:
        return Step(5, "trunk", "ok", "none")
    paths = [path for path, _ in touched]
    diff = git(
        ctx.root, "diff", "--no-color", "--no-renames", ctx.base or "", ctx.head or "", "--", *paths
    )
    lines = [f"- {path} ({entry.why})" for path, entry in touched]
    lines += ["", *(diff or "").splitlines()]
    count = plural(len(paths), "trunk file")
    if flags.read_trunk:
        return Step(
            5, "trunk", "ok", f"{count}, read by {user_name(ctx.root)} (--read-trunk)", lines
        )
    if flags.preview:
        summary = f"{count}: merge asks in a terminal, or `! mise run merge -- --read-trunk`"
        return Step(5, "trunk", "human", summary, lines)
    if flags.tty:
        return Step(5, "trunk", "ok", f"{count}, asked below", lines)
    summary = (
        f"{count} and no terminal to ask in: read the diff, then `! mise run merge -- --read-trunk`"
    )
    return Step(5, "trunk", "FAIL", summary, lines)


def step_gate_files(dod: Dod) -> Step:
    ctx = dod.ctx
    what, paths = gate_changes(ctx)
    dod.gate_paths = paths
    if not what and ctx.base and not read_blobs(ctx.root, ctx.base, [".project.toml"]):
        return Step(6, "gate files", "ok", "new with the adoption: this merge (G1) reviews them")
    if not what:
        return Step(6, "gate files", "ok", "unchanged")
    diff = git(ctx.root, "diff", "--no-color", ctx.base or "", ctx.head or "", "--", *paths) or ""
    lines = [f"changed: {', '.join(what)}", *diff.splitlines()[:200]]
    if len(diff.splitlines()) > 200:
        lines.append(
            f"... the whole diff: git diff {(ctx.base or '')[:10]} HEAD -- {' '.join(paths)}"
        )
    if dod.flags.gate_change:
        return Step(6, "gate files", "ok", "changed; --gate-change given", lines)
    if dod.flags.preview:
        return Step(6, "gate files", "human", "changed: merge needs --gate-change", lines)
    return Step(
        6, "gate files", "FAIL", "changed: read the diff, then merge -- --gate-change", lines
    )


def roadmap_entries(text: str) -> list[tuple[int, str, bool, str, str]]:
    """(line number, slug, ticked, title, section heading) of each roadmap item."""
    entries = []
    section = ""
    raw_lines = text.splitlines()
    for number, line in prose_lines(text):
        stripped = line.strip()
        if stripped.startswith("## "):
            section = stripped[3:].strip()
            continue
        if match := ROADMAP_ITEM_RE.match(stripped):
            written = shown_line(raw_lines, number)  # the title as written: `code` kept
            again = ROADMAP_ITEM_RE.match(written)
            title = (written[again.end() :] if again else stripped[match.end() :]).strip()
            entries.append((number, match.group(2), match.group(1) != " ", title, section))
    return entries


def roadmap_close(text: str, slug: str, title: str) -> tuple[str, str]:
    """The roadmap as merge writes it: slug's item ticked where it stands, or, when the roadmap
    lacks it, `- [x] <slug>: <title> (unplanned)` added after the last item of the last phase."""
    lines = text.splitlines()
    entries = roadmap_entries(text)
    own = [entry for entry in entries if entry[1] == slug]
    if own:
        number, _, _, _, section = own[0]
        lines[number - 1] = lines[number - 1].replace("- [ ]", "- [x]", 1)
        note = f"ticked {slug}"
        rest = [e for e in entries if e[4] == section and e[1] != slug]
        if section and all(e[2] for e in rest):
            note += f" ({section}: done)"
    else:
        match = TITLE_PARTS_RE.match(title)
        what = match.group(4) if match else title
        phases = [e for e in entries if e[4].startswith("Phase")]
        after = (phases or entries)[-1][0] if (phases or entries) else len(lines)
        lines.insert(after, f"- [x] {slug}: {what} (unplanned)")
        note = f"added {slug} as unplanned, ticked"
    return "\n".join(lines) + ("\n" if text.endswith("\n") or not text else ""), note


def roadmap_launch(text: str, slug: str, date: str) -> tuple[str, str | None]:
    """The roadmap as the close commit of a launch-<slug> branch writes it: the ticked item slug
    with ` (launched <date>)` appended where it stands (design D.2). Or the text unchanged, and
    why the item cannot be marked."""
    number, problem = launch_item_problem(text, slug)
    if problem:
        return text, problem
    lines = text.splitlines()
    lines[number - 1] = lines[number - 1].rstrip() + f" (launched {date})"
    return "\n".join(lines) + ("\n" if text.endswith("\n") else ""), None


def changelog_target(dod: Dod) -> tuple[str | None, str, str | None]:
    """(CHANGELOG.md as merge writes it, or None to leave it; what it adds; a problem). The
    file is git-cliff's output for the history of the default branch plus the squash subject
    (`git cliff <default tip> --with-commit "<title>"`), so the branch's own commits never add
    lines of their own. That output must be the old file plus the one line (close_commit_problem
    accepts nothing else), except on the adoption branch, which writes the file whole."""
    ctx, lane, title = dod.ctx, dod.ctx.lane or "", dod.title
    init = ctx.branch == INIT_BRANCH
    entry = changelog_entry(title) if title else None
    if lane in ("chore", "plan") and not init:
        return None, f"no line on {lane}/", None
    if entry is None and not init:
        return None, f"no line for a '{title.split(':')[0]}' subject", None
    argv = git_cliff_argv()
    if argv is None:
        return None, "", "git-cliff is not installed here: run mise install"
    tip = rev(ctx.root, ctx.default_ref or "")
    if tip is None:
        return None, "", f"no {ctx.default} tip to read the history from"
    extra = ["--with-commit", title] if entry else []
    proc = run_cmd([*argv, tip, *extra], ctx.root, lifecycle_env())
    if proc.returncode != 0:
        return None, "", f"git cliff failed: {said(proc)}"
    new = proc.stdout
    current = read_text(ctx.root / CHANGELOG)
    if init:
        if current == new:
            return None, "unchanged", None
        return new, f"written from the history of {ctx.default}", None
    old = current.splitlines() if current is not None else changelog_header(ctx.root, "HEAD")
    groups = (entry[0],) if lane == "feat" and entry else LANE_CHANGELOG_GROUPS.get(lane, ())
    problem = changelog_close_problem(old, new.splitlines(), groups, entry[1] if entry else None)
    if problem:
        return (
            None,
            "",
            (
                f"{CHANGELOG} is not what git-cliff makes of the history of {ctx.default} "
                f"({problem}); re-run /project-init, whose merge rewrites it from the history"
            ),
        )
    group = entry[0] if entry else "?"
    return new, f"1 line under {group}: {entry[1] if entry else ''}", None


def step_close(dod: Dod) -> Step:
    """Step 7 as a preview: what the close commit will write, each part checked the way
    spec-check checks a close commit."""
    ctx, change = dod.ctx, dod.change
    if dod.closing:
        return Step(
            7, "close", "ok", f"merge's close commit is already HEAD ({(ctx.head or '')[:10]})"
        )
    problems: list[str] = []
    parts: list[str] = []
    if ctx.lane == "feat" and change is not None:
        req = f"{change.path}/requirements.md"
        text = read_text(ctx.root / req) or ""
        done = with_status(text, "approved", "done")
        if done is None:
            problems.append(f"{req}: no `status: approved` line to move to done")
        else:
            dod.writes[req] = done
            parts.append("status approved -> done")
        slug = change.roadmap
        if launch_target(ctx.slug) is None:  # a launch marks its item below, and ticks none
            before = read_text(ctx.root / ROADMAP) or ""
            after, dod.roadmap_note = roadmap_close(before, slug, dod.title)
            if problem := roadmap_close_problem(before, after, slug):
                problems.append(f"{ROADMAP}: {problem}")
            else:
                dod.writes[ROADMAP] = after
                parts.append(f"roadmap {dod.roadmap_note}")
        rollback = change_rollback(ctx.root, change)
        if rollback is not None and rollback.kind == "flag":
            launch = f"{BACKLOG_DIR}/{today()}-launch-{slug}.md"
            dod.writes[launch] = launch_item(change, rollback.value)
            parts.append(f"{launch} (launch: flip {rollback.value} on, then remove the flag)")
    if target := launch_target(ctx.slug):
        after, problem = roadmap_launch(read_text(ctx.root / ROADMAP) or "", target, today())
        if problem:
            problems.append(f"{ROADMAP}: {problem}")
        else:
            dod.writes[ROADMAP] = after
            dod.roadmap_note = f"marked {target} launched"
            parts.append(f"roadmap {dod.roadmap_note}")
    text, dod.changelog_note, problem = changelog_target(dod)
    if problem:
        problems.append(problem)
    elif text is not None:
        dod.writes[CHANGELOG] = text
    parts.append(f"{CHANGELOG}: {dod.changelog_note}")
    if written := proof_close(dod):
        dod.writes[written[0]] = written[1]
        parts.append(f"{written[0]}: ## Tests")
    return Step(7, "close", "FAIL" if problems else "ok", "; ".join(parts), problems)


def launch_item(change: Change, env: str) -> str:
    """The backlog item a flag: change's close commit adds (design B.2), named after its roadmap
    item: the launch (`/sdd launch <item>`), which flips the flag on, then removes it with its
    off path and its [flag-off] scenarios on the branch launch-<item>."""
    title = change.fields.get("title", "")
    roadmap = change.roadmap
    values = {
        "TITLE": f"Launch: {roadmap}",
        "WHAT": (
            f"`/sdd launch {roadmap}`. Flip {env} on, then remove the flag, its off path and its "
            f"[flag-off: {env}] scenarios (their tests go with them, under Spec-Removed:), on "
            f"chg/launch-{roadmap}."
        ),
        "WHY": (
            f"{change.slug} merged on {today()} behind {env}, off by default. Until the flag comes "
            f"off, both paths stay in the code; doctor calls it flag debt after {FLAG_DEBT_DAYS} "
            "days."
        ),
        "NOTES": (
            f"- Change: {change.path} ({title}), roadmap item `{roadmap}`.\n"
            f"- The flag is the `{env}` row of .env.example."
        ),
    }
    return fill(BACKLOG_TEMPLATE, values)


def landing_mode(ctx: Context) -> tuple[str, str | None]:
    """('local' or 'remote', a problem). No origin: a local squash. An origin that is the one
    .project.toml records: a pull request (D1 option 1). Any other origin: refused."""
    url = (git(ctx.root, "remote", "get-url", "origin") or "").strip()
    if not url:
        return "local", None
    return "remote", origin_problem(ctx.root, url, recorded_origin(ctx))


def step_landing(dod: Dod) -> Step:
    dod.landing, problem = landing_mode(dod.ctx)
    if problem:
        return Step(8, "land", "FAIL", details=[problem])
    if dod.landing == "remote":
        return Step(8, "land", "ok", "a pull request on origin, squash-merged once its checks pass")
    if dod.flags.without_ci:
        return Step(
            8,
            "land",
            "FAIL",
            details=["--without-ci is for a merge through a pull request; this one lands locally"],
        )
    return Step(8, "land", "ok", f"a local squash onto {dod.ctx.default}")


def run_check(ctx: Context, strict: bool) -> tuple[State, dict[str, str] | None]:
    """spec-check without printing: the state with its report, and the verdict per scenario."""
    state = load_state(ctx)
    for problem in encoding_problems(ctx.root):
        state.report.fail(problem)
    verdicts = None
    results = load_results(ctx.root)
    if isinstance(results, str):
        if state.scenarios:
            state.report.fail(results)
    else:
        for node, error in results.collect_errors:
            state.report.fail(f"collection error in {node}: {error}")
        for node, problem in results.bad_tags:
            state.report.fail(f"{node}: {problem}")
        if problem := results_problem(ctx.root, results):
            state.report.fail(problem)
        else:
            verdicts = check_trace(state, results, strict)
    check_markers(state, strict)
    for problem in trunk_at(ctx.root).problems:
        state.report.fail(problem)
    check_flag_tags(state)
    check_changes(state, strict)
    check_lane_rules(state)
    check_doc_commands(state)
    check_caps(state)
    return state, verdicts


def step_verify(dod: Dod) -> Step:
    """Step 2: `mise run verify`, then spec-check strict on the results it just wrote."""
    ctx = dod.ctx
    mise = shutil.which("mise")
    if mise is None:
        return Step(2, "verify", "FAIL", "mise is not on PATH: run it as `! mise run merge`")
    proc = run_cmd([mise, "run", "verify"], ctx.root, lifecycle_env(), timeout=PYTEST_TIMEOUT)
    state, verdicts = run_check(ctx, strict=True)
    details: list[str] = []
    if proc.returncode != 0:
        details += ["mise run verify failed:", *said(proc, 12).splitlines()]
    fails = [text for level, text in state.report.lines if level == "FAIL"]
    if fails:
        details += ["spec-check --strict:", *fails[:20]]
    unproven = sorted(
        sid
        for sid, verdict in (verdicts or {}).items()
        if verdict == "failing" and sid in state.added | state.modified
    )
    if details:
        summary = f"not proven yet: {', '.join(unproven)}" if unproven else ""
        return Step(2, "verify", "FAIL", summary, details)
    return Step(2, "verify", "ok", "lint types secrets test spec-check (strict)")


def step_prove_red(dod: Dod) -> Step:
    """Step 3: prove-red and the count guard; merge --allow <id> --reason turns that id's FAIL
    into an allowance printed in the squash body."""
    flags = dod.flags
    try:
        proof = run_prove_red(dod.ctx, None)
    except (ProveRedError, UsageError) as exc:
        return Step(3, "prove-red", "FAIL", details=[str(exc)])
    dod.proof = proof
    if proof.base == proof.head:
        return Step(3, "prove-red", "ok", "nothing to prove: HEAD is the base")
    for item in proof.proofs:
        if item.level == "FAIL" and item.sid in flags.allow:
            item.level = "allowed"
            item.text += f" (allowed by {user_name(dod.ctx.root)}: {flags.reason})"
    details = [f"{p.level:<7} {p.text}" for p in proof.proofs if p.level != "ok"]
    details += [f"{level:<7} {text}" for level, text in proof.report.lines if level != "ok"]
    for sid in flags.allow:
        if not any(p.sid == sid and p.level == "allowed" for p in proof.proofs):
            details.append(f"warn    --allow {sid}: its proof did not fail, so nothing is allowed")
    return Step(3, "prove-red", "ok" if proof.ok else "FAIL", proof.summary(), details)


def approve_commit(ctx: Context) -> tuple[str, str] | None:
    """(sha, trailer block) of the branch's first commit with a Spec-Approved: trailer."""
    commits = branch_commits(ctx)
    return next(((sha, t) for sha, _, t in commits if trailer_values(t, SPEC_APPROVED)), None)


def folder_start(ctx: Context, change: Change) -> tuple[str | None, bool]:
    """(the commit that added the change folder on this branch, whether it is the ratchet of a
    fast-lane branch to feat: `spec(<slug>): ratchet <lane> to feat`)."""
    req = f"{change.path}/requirements.md"
    log = ["log", "--no-merges", "--reverse", "--diff-filter=A", "--format=%H%x1f%s"]
    added = git_lines(ctx.root, *log, f"{ctx.base}..{ctx.head}", "--", req)
    if not added:
        return None, False
    sha, _, subject = added[0].partition("\x1f")
    return sha, RATCHET_SUBJECT_RE.match(subject) is not None


def code_before_folder(ctx: Context, start: str | None) -> list[tuple[str, str]]:
    """(sha, subject) of the branch's commits that touch the source roots but do not descend
    from start, the commit that added the change folder: code written before there was a spec
    to approve."""
    if start is None or not ctx.base or not ctx.head:
        return []
    src_roots = project_paths(ctx.root)[0]
    span = f"{ctx.base}..{ctx.head}"
    every = git_lines(
        ctx.root, "log", "--no-merges", "--reverse", "--format=%H%x1f%s", span, "--", *src_roots
    )
    descendants = ["rev-list", "--no-merges", "--ancestry-path", f"{start}^..{ctx.head}"]
    later = set(git_lines(ctx.root, *descendants, "--", *src_roots))
    found = []
    for line in every:
        sha, _, subject = line.partition("\x1f")
        if sha not in later:
            found.append((sha, subject))
    return found


def approval(ctx: Context, change: Change) -> tuple[list[str], str | None, list[tuple[str, str]]]:
    """I6 and I12 for a feat change: (problems, the approve commit, the code a fast lane wrote
    before its ratchet to feat). The approve commit is the branch's first commit with a
    Spec-Approved: trailer, whose hash must be the hash of the spec it commits. Every commit
    that touches the source roots after the change folder arrived comes after that approve.
    Code from before the folder is an I12 failure on a branch that started as feat; on one that
    ratcheted to feat it is the fast lane's own work, which merge puts to a human (step 5)."""
    found = approve_commit(ctx)
    if found is None:
        problem = (
            f"I6: {change.path} says approved, but no commit on {ctx.branch} carries "
            f"'{SPEC_APPROVED}:'; only `! mise run approve` writes it"
        )
        return [problem], None, []
    sha, trailers = found
    problems = []
    claimed = trailer_values(trailers, SPEC_APPROVED)[0]
    if claimed != spec_hash(ctx.root, sha, change.path):
        problems.append(
            f"I6: the {SPEC_APPROVED}: hash of {sha[:10]} is not the hash of the spec it "
            "commits; only `! mise run approve` writes it"
        )
    req = f"{change.path}/requirements.md"
    then = frontmatter(read_blobs(ctx.root, sha, [req]).get(req, ""))[0].get("status")
    if then != "approved":
        problems.append(f"I6: {sha[:10]} carries {SPEC_APPROVED}: but leaves {req} {then}")
    src_roots = project_paths(ctx.root)[0]
    start, ratchet = folder_start(ctx, change)
    early = code_before_folder(ctx, start)
    if early and not ratchet:
        problems.append(
            f"I12: {early[0][0][:10]} touches {', '.join(src_roots)} before the change folder "
            f"arrived ({(start or '')[:10]}); spec before code"
        )
        early = []
    listing = ["rev-list", "--no-merges", "--reverse"]
    if start:
        listing += ["--ancestry-path", f"{start}^..{ctx.head}"]
    else:
        listing.append(f"{ctx.base}..{ctx.head}")
    touching = git_lines(ctx.root, *listing, "--", *src_roots)
    if touching:
        first = touching[0]
        if first == sha or not is_ancestor(ctx.root, sha, first):
            problems.append(
                f"I12: {first[:10]} touches {', '.join(src_roots)} before the approve commit "
                f"{sha[:10]}; spec before code"
            )
    return problems, sha, early


def step_lane_rules(dod: Dod) -> Step:
    """Step 3: I6 and I12 (feat); I7 and I11 ran with spec-check in verify."""
    ctx, change = dod.ctx, dod.change
    if ctx.lane != "feat" or change is None:
        return Step(3, "lane rules", "ok", "I7 I11 (spec-check)")
    if change.status in ("", "draft"):
        return Step(3, "lane rules", "ok", "I7 I11 (spec-check); I6 and I12 once approved")
    problems, dod.approved_at, dod.early_code = approval(ctx, change)
    if not dod.early_code:
        summary = "I6 approve hash, I12 spec before code, I7 I11 (spec-check)"
        return Step(3, "lane rules", "FAIL" if problems else "ok", summary, problems)
    summary = (
        f"I6 approve hash, I7 I11 (spec-check); I12: {plural(len(dod.early_code), 'commit')} "
        "touched the source before approve (before the ratchet to feat): a human check"
    )
    early = [f"code before approve: {sha[:10]} {subject}" for sha, subject in dod.early_code]
    return Step(3, "lane rules", "FAIL" if problems else "ok", summary, [*problems, *early])


def run_it_label(row: tuple[str, str, str, str]) -> str:
    """A Run it row as a line of text: `command` exit N, stdout 'x', stderr 'y'."""
    command, code, out, err = row
    text = f"`{command}` exit {code}"
    if out:
        text += f", stdout '{out}'"
    if err:
        text += f", stderr '{err}'"
    return text


def step_amended(dod: Dod) -> Step:
    """Step 3, the drift rule: what changed in the approved spec since the approve commit.
    Every file approve hashed that differs at HEAD (the status line aside) is listed, with the
    scenarios changed, added or removed, and the change folder's diff; none of that is refused.
    An approved Human check, Run it row or Proof row that validation.md no longer holds word for
    word (gone, reworded, a looser exit or output, a weaker kind) is: G2 approved that list, so
    the diff is shown and --reapprove is required."""
    ctx, change, sha, flags = dod.ctx, dod.change, dod.approved_at, dod.flags
    name = "amended after approval"
    if change is None or sha is None:
        return Step(3, name, "ok", "none")
    root = ctx.root
    then, now = scenarios_at(root, sha), scenarios_at(root, "HEAD")
    dod.amended = sorted(sid for sid in now if sid not in then or now[sid].block != then[sid].block)
    dod.amended += sorted(f"{sid} (removed)" for sid in then if sid not in now)
    paths = sorted(
        set(spec_paths(root, sha, change.path)) | set(spec_paths(root, "HEAD", change.path))
    )
    old, new = read_blobs(root, sha, paths), read_blobs(root, "HEAD", paths)
    req = f"{change.path}/requirements.md"
    if req in new:
        new[req] = with_status(new[req], "done", "approved") or new[req]
    dod.amended_files = [path for path in paths if old.get(path) != new.get(path)]
    val = f"{change.path}/validation.md"
    before, after = old.get(val, ""), new.get(val, "")
    kept = human_checks_of(change, after, now)
    rows = {row[1:] for row in run_it_rows(after)}
    dod.dropped = [
        f'human check "{text}"'
        for text in human_checks_of(change, before, then)
        if text not in kept
    ]
    dod.dropped += [
        f"Run it row {run_it_label(row[1:])}" for row in run_it_rows(before) if row[1:] not in rows
    ]
    proofs = proof_rows_of(change, after, now)
    dod.dropped += [
        f"Proof row {row}" for row in proof_rows_of(change, before, then) if row not in proofs
    ]
    folder = [path for path in dod.amended_files if under(path, [change.path])]
    parts = []
    if dod.amended:
        parts.append(f"{plural(len(dod.amended), 'scenario')} ({', '.join(dod.amended)})")
    if folder:
        parts.append(", ".join(PurePosixPath(path).name for path in folder) + " changed")
    summary = "; ".join(parts) or "none"
    details = []
    if dod.amended_files:
        details.append(f"changed since approve ({sha[:10]}): {', '.join(dod.amended_files)}")
    details += [f"dropped: {item}" for item in dod.dropped]
    if folder:
        diff = (git(root, "diff", "--no-color", sha, "HEAD", "--", *folder) or "").splitlines()
        details += diff[:80]
        if len(diff) > 80:
            details.append(f"... the whole diff: git diff {sha[:10]} HEAD -- {change.path}")
    if not dod.dropped:
        return Step(3, name, "ok", summary, details)
    count = plural(len(dod.dropped), "approved check")
    if flags.reapprove:
        return Step(3, name, "ok", f"{summary}; {count} dropped, --reapprove given", details)
    if flags.preview:
        return Step(
            3, name, "human", f"{summary}; {count} dropped: merge needs --reapprove", details
        )
    return Step(
        3,
        name,
        "FAIL",
        f"{summary}; {count} dropped since G2 approved them: read the diff, then merge -- "
        "--reapprove",
        details,
    )


def run_it_rows(text: str) -> list[tuple[int, str, str, str, str]]:
    """(line, command, exit, stdout contains, stderr contains) of validation.md's Run it table,
    read from the raw lines (code spans in the cells are the commands themselves)."""
    raw = text.splitlines()
    rows = []
    section = ""
    seen = 0
    for number, line in prose_lines(text):
        stripped = line.strip()
        if stripped.startswith("## "):
            section = "run" if stripped[3:].startswith("Run it") else ""
            seen = 0
            continue
        if section != "run" or not stripped.startswith("|"):
            continue
        seen += 1
        if seen <= 2 or set(stripped) <= set("|-: "):
            continue
        cells = re.split(r"(?<!\\)\|", raw[number - 1].strip().strip("|"))
        values = []
        for cell in cells:
            value = cell.strip().replace("\\|", "|")
            if len(value) >= 2 and value[0] == value[-1] == "`":
                value = value[1:-1]
            values.append(value)
        if len(values) == 4 and values[0]:
            rows.append((number, values[0], values[1], values[2], values[3]))
    return rows


def step_run_it(dod: Dod) -> Step:
    """Step 4: each Run it row of a feat change, `sh -c` in the repo, 60 s each."""
    ctx, change = dod.ctx, dod.change
    if ctx.lane != "feat" or change is None:
        return Step(4, "run it", "ok", "none (feat only)")
    rows = run_it_rows(read_text(ctx.root / change.path / "validation.md") or "")
    if not rows:
        return Step(4, "run it", "ok", "no rows")
    problems: list[str] = []
    matched = 0
    for number, command, code, out, err in rows:
        proc = run_cmd(["sh", "-c", command], ctx.root, lifecycle_env(), timeout=RUN_IT_TIMEOUT)
        where = f"validation.md:{number} `{command}`"
        found: list[str] = []
        if proc.returncode == 124 and "timed out" in proc.stderr:
            found.append(f"{where}: ran past {RUN_IT_TIMEOUT} s")
        else:
            if not re.fullmatch(r"-?\d+", code) or proc.returncode != int(code):
                found.append(f"{where}: exit {proc.returncode}, the row wants {code}")
            if out and out not in proc.stdout:
                found.append(f"{where}: stdout lacks '{out}' ({said(proc, 3)})")
            if err and err not in proc.stderr:
                found.append(f"{where}: stderr lacks '{err}'")
        matched += not found
        problems += found
    summary = f"{matched}/{len(rows)} rows match"
    return Step(4, "run it", "FAIL" if problems else "ok", summary, problems)


# ---------------------------------------------------------------- lifecycle: merge


def merge_flags(args: argparse.Namespace, *, preview: bool = False) -> MergeFlags:
    allow = split_ids(list(getattr(args, "allow", None) or []))
    reason = str(getattr(args, "reason", None) or "").strip()
    if allow and not reason:
        raise UsageError('--allow needs --reason "<why>": the squash body records both')
    if reason and not allow:
        raise UsageError("--reason goes with --allow <id>: it says why that id's proof may fail")
    without_ci = getattr(args, "without_ci", None)
    if without_ci is not None and not str(without_ci).strip():
        raise UsageError('--without-ci needs a reason ("<why>"): the squash body records it')
    return MergeFlags(
        attest=bool(getattr(args, "attest", False)),
        read_trunk=bool(getattr(args, "read_trunk", False)),
        gate_change=bool(getattr(args, "gate_change", False)),
        reapprove=bool(getattr(args, "reapprove", False)),
        allow=allow,
        reason=reason,
        title=getattr(args, "title", None),
        without_ci=str(without_ci or "").strip(),
        tty=sys.stdin.isatty() and sys.stdout.isatty(),
        preview=preview,
    )


def cmd_merge(ctx: Context, args: argparse.Namespace) -> int:
    """G1 and G3: check the Definition of Done, then close the branch and land it."""
    target = ctx
    if args.branch and args.branch != ctx.branch:
        where = worktree_of(ctx.root, args.branch)
        if where is None:
            print(
                f"FAIL  {args.branch} is not checked out in any worktree; check it out in one "
                f"(git worktree add ../{ctx.root.name}-<name> {args.branch}), then merge again"
            )
            return 1
        target = load_context(where)
    flags = merge_flags(args, preview=bool(args.dry_run))
    if not (target.root / SPECS).is_dir():
        print(f"FAIL  no {SPECS}/ folder: this repo has no specs yet (run /project-init)")
        return 1
    header = f"merge {target.branch or 'detached HEAD'}"
    if not same_path(target.root, ctx.root):
        header += f" (worktree {target.root})"
    print(header + (" --dry-run: nothing is written" if args.dry_run else ""))
    dod = dod_prepare(target, flags)
    if not dod.ok and not args.dry_run:
        print_steps(dod.steps)
        print_review(dod)
        print(
            f"merge: refused ({plural(dod.problems, 'problem')}); nothing changed. verify, "
            "prove-red and the Run it rows run once these pass (all of it: mise run status -- "
            "--merge)"
        )
        return 1
    if not dod.stop:
        dod_prove(dod)
    if args.dry_run:
        print_steps(dod.steps)
        print_review(dod)
        print_land_plan(dod)
        verdict = "ok" if dod.ok else f"FAIL ({plural(dod.problems, 'problem')})"
        print(f"merge --dry-run: {verdict}; nothing written")
        return 0 if dod.ok else 1
    print_steps(dod.steps)
    print_review(dod)
    if not dod.ok:
        print(f"merge: refused ({plural(dod.problems, 'problem')}); nothing changed")
        return 1
    confirmed = confirm_checks(dod)
    if confirmed is None:
        print("merge: refused: a human check was not confirmed; nothing changed")
        return 1
    trunk_read = confirm_trunk(dod)
    if trunk_read is None:
        print("merge: refused: the trunk diff was not confirmed as read; nothing changed")
        return 1
    dod.trunk_read = trunk_read
    problem = close_branch(dod)
    if problem:
        print(f"FAIL  close: {problem}")
        return 1
    dod.bundle = load_bundle(dod.ctx, dod.change)  # the close commit wrote its ## Tests
    message = squash_message(dod, confirmed)
    if dod.landing == "remote":
        notes, problem = land_remote(ctx, dod, message)
    else:
        notes, problem = land_local(ctx, dod, message)
    if problem:
        print(f"FAIL  land: {problem}")
        for note in notes:
            print(f"      {note}")
        if dod.writes and not dod.closing:
            print("      the close commit stays on the branch; merge again once this is fixed")
        return 1
    if GUARD_HOOK in dod.gate_paths:
        try:
            install_gates(ctx.root, ctx.default)
            notes.append(f"the main guard is pinned to the new {GUARD_HOOK} (hook install)")
        except UsageError as exc:
            notes.append(f"pin the new main guard: run mise install ({exc})")
    print_landed(ctx, dod, notes)
    return 0


def confirm_checks(dod: Dod) -> list[str] | None:
    """The squash body's record of the human checks: attested (--attest) or answered y at the
    prompt. None when one is answered no."""
    if not dod.checks:
        return []
    who = user_name(dod.ctx.root)
    if dod.flags.attest:
        return [f"- {check.text} (attested by {who}, --attest)" for check in dod.checks]
    lines = []
    for check in dod.checks:
        if check.diff:
            print(check.diff)
        try:
            answer = input(f"human check: {check.text} [y/N] ")
        except EOFError:
            answer = ""
        if answer.strip().lower() not in ("y", "yes"):
            print(f"not confirmed: {check.text}")
            return None
        lines.append(f"- {check.text} (confirmed at the prompt by {who})")
    return lines


def confirm_trunk(dod: Dod) -> str | None:
    """The squash body's record of the trunk read (I19): --read-trunk, or y at the prompt.
    "" when the branch touches no trunk file; None when the answer is no."""
    touched = ", ".join(path for path, _ in dod.depth.trunk)
    if not touched:
        return ""
    who = user_name(dod.ctx.root)
    if dod.flags.read_trunk:
        return f"Trunk read by {who} (--read-trunk): {touched}"
    try:
        answer = input("read the trunk diff? [y/N] ")
    except EOFError:
        answer = ""
    if answer.strip().lower() not in ("y", "yes"):
        print(f"not confirmed: the trunk diff of {touched}")
        return None
    return f"Trunk read by {who} (confirmed at the prompt): {touched}"


def close_branch(dod: Dod) -> str | None:
    """Step 7: the close commit on the branch, under PROJECT_MERGE, with the Merged-By trailer:
    the roadmap tick, `status: done`, CHANGELOG.md and the proof README's ## Tests section (now
    with prove-red's verdicts), as step_close worked them out. A branch with nothing to write
    gets none; one that has it already (a merge run again) keeps it."""
    ctx = dod.ctx
    if dod.closing or not dod.writes:
        return None
    if written := proof_close(dod):
        dod.writes[written[0]] = written[1]
    before = {path: read_text(ctx.root / path) for path in dod.writes}
    for path, text in dod.writes.items():
        (ctx.root / path).parent.mkdir(parents=True, exist_ok=True)
        (ctx.root / path).write_text(text, encoding="utf-8")
    env = lifecycle_env(merge=True)
    message = f"chore({ctx.slug}): close for merge\n\n{MERGED_BY}\n"
    proc = git_run(ctx.root, env, "add", "--", *dod.writes)
    if proc.returncode == 0:
        proc = git_run(ctx.root, env, "commit", "-q", "-m", message)
    if proc.returncode == 0:
        return None
    git_run(ctx.root, env, "reset", "-q", "--", *dod.writes)
    for path, text in before.items():
        if text is None:
            (ctx.root / path).unlink(missing_ok=True)
        else:
            (ctx.root / path).write_text(text, encoding="utf-8")
    return f"the close commit was refused, nothing changed:\n{said(proc, 20)}"


def squash_message(dod: Dod, confirmed: list[str]) -> str:
    """The commit that lands on the default branch: the title, then the durable record (the
    scenario ids, the dismissed findings, the prove-red table, the checks, the attestation),
    then the trailer."""
    ctx, state = dod.ctx, dod.state
    notes = title_commit_notes(ctx, dod.title) if dod.change is None else []
    lines = [dod.title, "", *notes, *([""] if notes else []), f"Branch: {ctx.branch}"]
    if dod.change is not None:
        lines.append(f"Change: {dod.change.path}")
        if rollback := change_rollback(ctx.root, dod.change):
            lines.append(f"Rollback: {rollback}")
    for kind, ids in (
        ("added", state.added),
        ("modified", state.modified),
        ("removed", state.removed),
    ):
        if ids:
            lines.append(f"Scenarios {kind}: {', '.join(sorted(ids))}")
    spec = trailer_ids([t for _, _, t in branch_commits(ctx)], "Spec")
    if spec and ctx.lane in ("fix", "chg"):
        lines.append(f"Scenarios in Spec: trailers: {', '.join(spec)}")
    if dod.amended:
        lines.append(f"Amended after approval: {', '.join(dod.amended)}")
    if dod.amended_files:
        lines.append(f"Spec files changed after approval: {', '.join(dod.amended_files)}")
    if dod.dropped:
        who = user_name(ctx.root)
        lines.append(f"Dropped after approval (--reapprove by {who}): {'; '.join(dod.dropped)}")
    if dod.early_code:
        listed = ", ".join(f"{sha[:10]} {subject}" for sha, subject in dod.early_code)
        lines.append(f"Code before approve (before the ratchet to feat): {listed}")
    lines += ["", "Review depth:", *(f"  {line}" for line in review_lines(dod))]
    if dod.trunk_read:
        lines.append(dod.trunk_read)
    lines += proof_record(dod.bundle)
    dismissed = dismissed_lines(ctx)
    if dismissed:
        lines += ["", "Findings dismissed at validate:", *(f"  {text}" for text in dismissed)]
    proof = dod.proof
    if proof is not None and proof.base != proof.head:
        lines += ["", f"prove-red against {proof.base[:10]}: {proof.summary()}"]
        lines += [f"  {item.level:<7} {item.text}" for item in proof.proofs]
    lines += ["", "Definition of Done:"]
    for step in sorted(dod.steps, key=lambda s: (s.order, s.sub)):
        lines.append(
            f"  {step.name}: {step.level}" + (f" ({step.summary})" if step.summary else "")
        )
    if confirmed:
        lines += ["", "Human checks:", *confirmed]
    lines += ["", MERGED_BY]
    return "\n".join(lines) + "\n"


def land_on_default(root: Path, default: str, old: str, new: str) -> str | None:
    """Move the default branch from old to new under PROJECT_MERGE: a fast-forward in the
    worktree that has it checked out (its files follow), else update-ref."""
    env = lifecycle_env(merge=True)
    holder = worktree_of(root, default)
    if holder is not None:
        proc = git_run(holder, env, "merge", "--ff-only", "-q", new)
        if proc.returncode != 0:
            return (
                f"{default} is checked out in {holder}, and its fast-forward failed: "
                f"{said(proc)}; commit or stash the changes there, then run this again"
            )
        return None
    proc = git_run(
        root, env, "update-ref", "-m", "mise run merge", f"refs/heads/{default}", new, old
    )
    if proc.returncode != 0:
        return f"git update-ref refs/heads/{default}: {said(proc)}"
    return None


def drop_branch(invoker: Path, root: Path, branch: str, default: str, tip: str) -> list[str]:
    """Delete branch once its work landed or was abandoned. The worktree running this switches
    to the default branch (or detaches at tip when another worktree holds it); another worktree
    that has the branch (a hotfix) is removed. Returns what it did."""
    env = lifecycle_env()
    if rev(root, f"refs/heads/{branch}") is None:
        return [f"branch {branch} deleted"]
    where = worktree_of(root, branch)
    notes = []
    if where is not None and same_path(where, invoker):
        holder = worktree_of(root, default)
        if holder is None:
            proc = git_run(where, env, "switch", "-q", default)
        else:
            proc = git_run(where, env, "switch", "-q", "--detach", tip)
            notes.append(f"this worktree is detached at {tip[:10]}: {default} is out in {holder}")
        if proc.returncode != 0:
            return [f"kept {branch}: cannot switch away from it ({said(proc)})"]
    elif where is not None:
        proc = git_run(invoker, env, "worktree", "remove", str(where))
        if proc.returncode != 0:
            return [f"kept {branch} and its worktree {where}: {said(proc)}"]
        notes.append(f"worktree {where} removed")
    proc = git_run(invoker, env, "branch", "-D", branch)
    if proc.returncode != 0:
        return [*notes, f"kept {branch}: {said(proc)}"]
    return [*notes, f"branch {branch} deleted"]


def drop_workers(invoker: Path, root: Path, branch: str, default: str, tip: str) -> list[str]:
    """The parallel workers of a feat branch that landed (feat/<slug>--g<n>, `change --parallel`)
    go with it when their work reached it: tip, the branch as it landed, holds their commits. A
    worker with commits the branch never merged stays, named in the report."""
    if not branch.startswith("feat/"):
        return []
    refs = git_lines(root, "for-each-ref", "--format=%(refname:short)", f"refs/heads/{branch}--g*")
    notes = []
    for worker in (ref for ref in refs if WORKER_RE.search(ref)):
        if is_ancestor(root, f"refs/heads/{worker}", tip):
            notes += drop_branch(invoker, root, worker, default, tip)
        else:
            notes.append(f"kept {worker}: it holds commits {branch} never merged")
    return notes


def land_local(invoker: Context, dod: Dod, message: str) -> tuple[list[str], str | None]:
    """Step 8 without a remote: `git merge-tree --write-tree` + `git commit-tree` of the squash,
    moved onto the default branch under PROJECT_MERGE; then the branch goes."""
    ctx = dod.ctx
    root, default, branch = ctx.root, ctx.default, ctx.branch or ""
    old = rev(root, f"refs/heads/{default}")
    tip = rev(root, "HEAD")
    if old is None or tip is None:
        return [], f"no local {default} branch to land on"
    if not is_ancestor(root, old, tip):
        return [], f"{default} moved during the merge: run git merge {default}, then merge again"
    proc = git_run(root, lifecycle_env(), "merge-tree", "--write-tree", old, tip)
    tree = proc.stdout.partition("\n")[0].strip()
    want = (git(root, "rev-parse", f"{tip}^{{tree}}") or "").strip()
    if proc.returncode != 0 or tree != want:
        return (
            [],
            f"git merge-tree of {default} and {branch} is not the branch's tree: {said(proc)}",
        )
    proc = git_run(root, lifecycle_env(), "commit-tree", tree, "-p", old, "-F", "-", stdin=message)
    squash = proc.stdout.strip()
    if proc.returncode != 0 or not squash:
        return [], f"git commit-tree: {said(proc)}"
    if problem := land_on_default(root, default, old, squash):
        return [], problem
    notes = [f"{default} ({squash[:10]}, a local squash with the Merged-By trailer)"]
    notes += drop_branch(invoker.root, root, branch, default, squash)
    notes += drop_workers(invoker.root, root, branch, default, tip)
    return notes, None


def remote_plan(branch: str, default: str, title: str, tip: str, team: bool) -> list[list[str]]:
    """The commands of step 8 with a remote (D1 option 1), in order; land_remote runs them. The
    PR body and the squash body are the squash message, read from stdin. gh merges on the
    server only: with --delete-branch it would also switch to the default branch and pull it
    outside PROJECT_MERGE, which the main guard refuses while the default branch records no
    origin_url (the first merge, G1). merge syncs the default branch itself, once origin's tip
    is the pull request's merge commit or a later tip that holds it (another merge landed in
    between), then deletes the branch."""
    create = ["gh", "pr", "create", "--base", default, "--head", branch, "--title", title]
    plan = [
        ["git", "push", "-u", "origin", branch],
        [*create, "--body-file", "-"],
        ["gh", "pr", "checks", branch, "--json", CHECK_FIELDS],
    ]
    if team:
        plan.append(
            ["gh", "pr", "view", branch, "--json", "reviewDecision", "-q", ".reviewDecision"]
        )
    squash = ["gh", "pr", "merge", branch, "--squash", "--match-head-commit", tip]
    plan += [
        [*squash, "--subject", title, "--body-file", "-"],
        ["gh", "pr", "view", branch, "--json", PR_FIELDS],
        ["git", "ls-remote", "origin", f"refs/heads/{default}"],
        ["git", "fetch", "-q", "origin", f"refs/heads/{default}"],
        ["git", "push", "-q", "origin", "--delete", branch],
    ]
    return plan


def remote_step_note(argv: list[str], default: str, gate: str) -> str:
    """What print_land_plan says under one command of remote_plan."""
    kind = " ".join(argv[:3])
    if kind == "gh pr create":
        return "unless the branch has an open pull request"
    if kind == "gh pr checks":
        return f"and --required, every {CHECKS_POLL} s: waits on {gate}; other checks only warn"
    if kind == "gh pr view":
        if "reviewDecision" in argv:
            return "the team tier: waits for APPROVED"
        return "the pull request's merge commit"
    if kind == "git ls-remote origin":
        return f"origin's {default} must be that merge commit, or a tip that holds it"
    if kind == "git fetch -q":
        return (
            f"then {default} fast-forwards to it under PROJECT_MERGE, files and all, when each "
            "first-parent commit it brings carries Merged-By"
        )
    if kind == "git push -q":
        return "when origin still has the branch; then the branch goes here too"
    return ""


@dataclass
class PullRequest:
    number: str
    state: str  # OPEN, MERGED or CLOSED
    head: str  # headRefOid: the commit the pull request holds
    merge: str  # mergeCommit.oid once merged: the squash on the default branch


def pull_request(root: Path, env: dict[str, str], branch: str) -> PullRequest | None:
    """`gh pr view <branch>`: the branch's open pull request, else its latest one; None when
    it has none, or gh cannot say."""
    proc = run_cmd(["gh", "pr", "view", branch, "--json", PR_FIELDS], root, env, timeout=120)
    try:
        data = json.loads(proc.stdout) if proc.returncode == 0 else None
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    merge = data.get("mergeCommit")
    oid = merge.get("oid") if isinstance(merge, dict) else None
    return PullRequest(
        str(data.get("number") or ""),
        str(data.get("state") or ""),
        str(data.get("headRefOid") or ""),
        oid if isinstance(oid, str) else "",
    )


@dataclass
class Check:
    name: str
    bucket: str  # pass fail pending skipping cancel
    workflow: str
    link: str

    def shown(self) -> str:
        return f"{self.name} ({self.workflow})" if self.workflow else self.name


@dataclass
class Workflow:
    path: str
    name: str
    jobs: list[str]  # the check name of each job: its `name:`, else its id


JOB_ID_RE = re.compile(r"""^("[^"]*"|'[^']*'|[^\s:#"']+)\s*:(?:\s|$)""")


def workflow_jobs(text: str) -> tuple[str, list[str]]:
    """A GitHub Actions workflow's `name:` and the check name of each job, read line by line:
    enough for the workflow render writes (templates/ci.yml), not YAML at large."""
    name = ""
    jobs: list[str] = []
    in_jobs = False
    job_indent = key_indent = -1
    for raw in text.splitlines():
        body = raw.strip()
        if not body or body.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent == 0:
            in_jobs = body.startswith("jobs:")
            if body.startswith("name:"):
                name = yaml_scalar(body[5:])
            continue
        if not in_jobs:
            continue
        match = JOB_ID_RE.match(body)
        if job_indent < 0 or indent <= job_indent:
            if match is None:
                continue
            job_indent, key_indent = indent, -1
            jobs.append(yaml_scalar(match.group(1)))
            continue
        if key_indent < 0:
            key_indent = indent
        if indent == key_indent and body.startswith("name:") and jobs:
            jobs[-1] = yaml_scalar(body[5:]) or jobs[-1]
    return name, jobs


def generated_ci(root: Path) -> Workflow | None:
    """The CI workflow project-init rendered (.project.toml [generated] lists it): the one whose
    jobs are the CI rung of the gate ladder. A repo's own CI (helios's ci.yml) is not it."""
    rendered = rendered_hashes(root)
    for path in CI_WORKFLOWS:
        text = read_text(root / path) if path in rendered else None
        if text is not None:
            name, jobs = workflow_jobs(text)
            return Workflow(path, name, jobs)
    return None


def gate_description(ci: Workflow | None) -> str:
    if ci is None:
        return "the required checks (no generated CI workflow)"
    return f"the required checks and the jobs of {ci.path} ({', '.join(ci.jobs) or 'none'})"


def pr_checks(root: Path, env: dict[str, str], branch: str, *, required: bool) -> list[Check] | str:
    """The pull request's checks as `gh pr checks --json` reports them (required: only those a
    branch protection or ruleset requires); [] while none has reported; the error when gh
    fails."""
    argv = ["gh", "pr", "checks", branch, "--json", CHECK_FIELDS]
    proc = run_cmd([*argv, "--required"] if required else argv, root, env, timeout=120)
    try:
        data = json.loads(proc.stdout) if proc.stdout.strip() else None
    except ValueError:
        data = None
    if isinstance(data, list):
        return [
            Check(*(str(item.get(key) or "") for key in ("name", "bucket", "workflow", "link")))
            for item in data
            if isinstance(item, dict)
        ]
    said_text = f"{proc.stdout}\n{proc.stderr}"
    if "no checks reported" in said_text or "no required checks reported" in said_text:
        return []
    return said(proc, 3)


@dataclass
class ChecksVerdict:
    done: bool
    problem: str | None = None
    unreported: list[str] = field(default_factory=list)  # generated jobs that never reported
    notes: list[str] = field(default_factory=list)
    waiting: str = ""


def judge_checks(
    every: list[Check], required: list[Check], ci: Workflow | None, waited: float, without_ci: str
) -> ChecksVerdict:
    """One look at the pull request's checks. The ones that gate the merge: the required ones,
    and the jobs of the generated workflow (the gate ladder's CI rung); any other check only
    warns (a legacy job that is red on main already must not hold the merge forever). The
    generated jobs must report within CHECKS_REGISTER seconds: a pull request that shows none
    of them (Actions off, a workflow GitHub rejected) lands only with --without-ci."""
    wanted = {(c.name, c.workflow) for c in required}

    def generated(check: Check) -> bool:
        if ci is None or (ci.name and check.workflow not in ("", ci.name)):
            return False
        return check.name in ci.jobs if ci.jobs else bool(check.workflow)  # jobs not read: any

    def gates(check: Check) -> bool:
        return (check.name, check.workflow) in wanted or generated(check)

    gate = [c for c in every if gates(c)]
    warn = [
        f"warning: {c.shown()} {c.bucket}, a check this merge does not wait on (neither "
        f"required nor a job of the generated workflow){': ' + c.link if c.link else ''}"
        for c in every
        if not gates(c) and c.bucket in CHECK_FAILED
    ]
    failed = [c for c in gate if c.bucket in CHECK_FAILED]
    if failed:
        listed = "; ".join(
            f"{c.shown()} {c.bucket}" + (f" ({c.link})" if c.link else "") for c in failed
        )
        return ChecksVerdict(True, problem=f"checks failed: {listed}", notes=warn)
    reported = {c.name for c in gate if generated(c)}
    if ci is None:
        missing = []
    elif ci.jobs:
        missing = [job for job in ci.jobs if job not in reported]
    else:  # the workflow's jobs could not be read: a check of any job of it will do
        missing = [] if reported else ["any job"]
    pending = [c.shown() for c in gate if c.bucket not in CHECK_DONE]
    early = waited < CHECKS_REGISTER
    if pending or (early and (missing or not gate)):
        shown = pending + [f"{job} (not reported yet)" for job in missing]
        return ChecksVerdict(False, waiting=", ".join(shown) or "the checks to report")
    if missing and ci is not None:
        if not without_ci:
            problem = (
                f"the pull request shows no check from {ci.path} ({', '.join(missing)}) after "
                f"{CHECKS_REGISTER // 60} min: GitHub Actions may be off for this repo, or GitHub "
                "rejected the workflow (the repo's Actions tab says which). Fix that, then merge "
                "again. To land without that CI, a human runs `! mise run merge -- --without-ci "
                '"<why>"`, and the squash body records it'
            )
            return ChecksVerdict(True, problem=problem, notes=warn)
        note = f"--without-ci: {', '.join(missing)} never reported; the squash body says why"
        return ChecksVerdict(True, unreported=missing, notes=[note, *warn])
    if not gate:
        return ChecksVerdict(
            True, notes=["no check gates this pull request: no generated CI, none required", *warn]
        )
    unused = ["--without-ci was not needed: the checks reported"] if without_ci else []
    passed = ", ".join(c.shown() for c in gate)
    return ChecksVerdict(True, notes=[f"checks passed: {passed}", *unused, *warn])


def wait_for_checks(
    root: Path, env: dict[str, str], branch: str, without_ci: str, notes: list[str]
) -> tuple[str | None, list[str]]:
    """Poll the pull request's checks every CHECKS_POLL seconds until judge_checks decides, for
    CHECKS_TIMEOUT seconds at most. Returns (the problem, the generated jobs that never
    reported and that --without-ci lets the merge land without)."""
    ci = generated_ci(root)
    start = time.monotonic()
    errors = 0
    shown = ""
    while True:
        waited = time.monotonic() - start
        every = pr_checks(root, env, branch, required=False)
        listed = isinstance(every, list) and bool(every)
        required = pr_checks(root, env, branch, required=True) if listed else []
        if isinstance(every, list) and isinstance(required, list):
            errors = 0
            verdict = judge_checks(every, required, ci, waited, without_ci)
            if verdict.done:
                notes += verdict.notes
                return verdict.problem, verdict.unreported
            if verdict.waiting != shown:
                shown = verdict.waiting
                print(label("checks") + f"waiting on {shown}", flush=True)
        else:
            errors += 1
            if errors >= CHECKS_ERRORS:
                failure = every if isinstance(every, str) else str(required)
                return f"gh pr checks failed {errors} times in a row: {failure}", []
        if waited >= CHECKS_TIMEOUT:
            left = shown or "the checks to report"
            late = (
                f"the pull request's checks did not finish in {CHECKS_TIMEOUT // 60} min (waiting "
                f"on {left}); merge again to wait longer"
            )
            return late, []
        time.sleep(CHECKS_POLL)


def with_record(body: str, line: str) -> str:
    """body with line as a paragraph of its own before the closing trailer paragraph."""
    head, sep, trailers = body.rstrip("\n").rpartition("\n\n")
    return f"{head}\n\n{line}\n\n{trailers}\n" if sep else f"{line}\n\n{body}"


def merge_commit(root: Path, env: dict[str, str], branch: str, tip: str) -> str:
    """The merge commit of the branch's pull request once gh reports it merged with head tip;
    asked SYNC_TRIES times, 2 s apart. "" when it never does."""
    for attempt in range(SYNC_TRIES):
        pr = pull_request(root, env, branch)
        if pr is not None and pr.state == "MERGED" and pr.head == tip and pr.merge:
            return pr.merge
        if attempt + 1 < SYNC_TRIES:
            time.sleep(2)
    return ""


def skipped_merge(root: Path, old: str, new: str) -> list[str]:
    """The first-parent commits from old to new that lack the Merged-By trailer, newest first,
    by the main guard's rule for a sync from origin (.githooks/reference-transaction): read past
    replace refs, and 'mise run merge' is the trailer's one value. ["?"] when git cannot say."""
    out = git(
        root,
        "--no-replace-objects",
        "log",
        "--first-parent",
        "--format=%H%x1f%(trailers:key=Merged-By,valueonly,separator=%x2C,unfold)%x1e",
        new,
        "--not",
        old,
        "--",
    )
    if out is None:
        return ["?"]
    skipped = []
    for record in out.split("\x1e"):
        sha, _, value = record.strip("\n").partition("\x1f")
        if sha and value.strip() != TOOL_TRAILER[1]:
            skipped.append(sha)
    return skipped


def merge_again(branch: str, default: str) -> str:
    """How a human finishes a merge whose pull request merged on origin but whose sync failed
    here: merge run again finds the merge and only syncs. That holds while the default branch
    here has not moved, since merge refuses a branch the default branch moved past."""
    return (
        f"the pull request merged on origin; once that is fixed, a human runs `! mise run merge` "
        f"again on {branch}: it finds the merge and syncs {default}"
    )


def sync_by_hand(default: str) -> str:
    """The manual sync of the default branch for commits that skipped merge. The main guard's
    refusal of such a pull (.githooks/reference-transaction) names the same step."""
    return (
        f"a human who checked those commits syncs {default} by hand (on {default}: "
        f"PROJECT_MERGE=1 git pull --ff-only origin {default}; status --audit keeps naming them)"
    )


def drop_by_hand(branch: str) -> str:
    """How a human deletes a branch whose pull request merged: origin has usually deleted it
    already (publish turns delete-branch-on-merge on)."""
    return (
        f"deletes {branch} (git branch -D {branch}, and git push origin --delete {branch} if "
        "origin still has it)"
    )


def origin_tip(
    root: Path, env: dict[str, str], plan: tuple[list[str], list[str]], oid: str
) -> tuple[str, bool, str]:
    """(origin's default branch as `git ls-remote origin` names it, True once it is fetched
    and holds oid, what the last failed fetch of a tip past oid said: "" when none failed). A
    tip past oid is a merge that landed on origin after this one. Asked SYNC_TRIES times, 2 s
    apart: origin may show the merge commit late."""
    confirm, fetch = plan
    remote = ""
    failed = ""
    for attempt in range(SYNC_TRIES):
        proc = run_cmd(confirm, root, env, timeout=60)
        remote = proc.stdout.partition("\t")[0].strip() if proc.returncode == 0 else ""
        if remote == oid:
            return remote, False, ""
        if remote and remote != rev(root, "FETCH_HEAD"):
            fetched = run_cmd(fetch, root, env, timeout=600)
            failed = said(fetched, 3) if fetched.returncode != 0 else ""
        if remote and rev(root, "FETCH_HEAD") == remote and is_ancestor(root, oid, remote):
            return remote, True, ""
        if attempt + 1 < SYNC_TRIES:
            time.sleep(2)
    return remote, False, failed


def sync_merged(
    root: Path,
    branch: str,
    default: str,
    env: dict[str, str],
    plan: tuple[list[str], list[str]],
    oid: str,
) -> tuple[str | None, list[str]]:
    """Bring the default branch here to origin's tip once that holds the pull request's merge
    commit oid. `git ls-remote origin` names the tip, `git fetch` brings it (plan: those two
    commands, run with guard_env as the main guard runs its own git), and the default branch
    fast-forwards to it under PROJECT_MERGE (land_on_default). The tip is oid itself, or a
    commit past it when another merge landed on origin in between. Each first-parent commit
    the sync brings must carry the Merged-By trailer (skipped_merge): a commit that reached
    origin's default branch around merge (a merge in GitHub's UI, a push past pre-push) never
    rides along. The main guard would confirm the same sync only once the default branch
    records origin_url, which the first merge (G1) is the one to land. A problem says how a
    human recovers."""
    env = guard_env(root, env)
    fetch = plan[1]
    again = merge_again(branch, default)
    tip, past, fetch_failed = origin_tip(root, env, plan, oid)
    if not tip:
        return f"origin's {default} cannot be read; {again}", []
    if tip != oid and not past and fetch_failed:
        failed = (
            f"git fetch origin {default} did not bring its tip {tip[:10]}, so whether that holds "
            f"the pull request's merge commit {oid[:10]} is unknown: {fetch_failed}; {again}"
        )
        return failed, []
    if tip != oid and not past:
        lost = (
            f"origin's {default} is {tip[:10]}, which does not hold the pull request's merge "
            f"commit {oid[:10]}. If origin is only slow to show the merge, a human runs "
            f"`! mise run merge` again on {branch} later: it finds the merge and syncs {default}. "
            f"If origin's {default} was rewritten, to recover: a human who checked origin's "
            f"{default} syncs {default} by hand (on {default}: PROJECT_MERGE=1 git pull "
            f"--ff-only origin {default}), then {drop_by_hand(branch)}"
        )
        return lost, []
    if tip == oid:
        proc = run_cmd(fetch, root, env, timeout=600)
        if proc.returncode != 0 or rev(root, "FETCH_HEAD") != oid:
            return (
                f"git fetch origin {default} did not bring {oid[:10]}: {said(proc, 3)}; {again}",
                [],
            )
    old = rev(root, f"refs/heads/{default}")
    if old is None:
        return f"there is no local {default} to move to {tip[:10]}; {again}", []
    if old != tip and not is_ancestor(root, old, tip):
        ahead = (
            f"{default} here ({old[:10]}) holds commits origin's {default} lacks, so it cannot "
            f"fast-forward to origin's {tip[:10]}; {again}"
        )
        return ahead, []
    if old != tip and (skipped := skipped_merge(root, old, tip)):
        shown = ", ".join(sha[:10] for sha in skipped[:5]) + (", ..." if len(skipped) > 5 else "")
        refused = (
            f"origin's {default} holds {plural(len(skipped), 'commit')} that did not land through "
            f"'mise run merge' (no '{MERGED_BY}' trailer): {shown}, so {default} here stays at "
            f"{old[:10]}. The pull request merged on origin. To recover: "
            f"{sync_by_hand(default)}, then {drop_by_hand(branch)}"
        )
        return refused, []
    if old != tip and (problem := land_on_default(root, default, old, tip)):
        return f"{problem}; {again}", []
    notes = []
    if tip != oid:
        count = len(git_lines(root, "rev-list", "--first-parent", tip, "--not", oid, "--"))
        notes.append(
            f"origin's {default} had moved on to {tip[:10]} ({plural(count, 'more commit')}, "
            f"each with the Merged-By trailer): {default} here is there too"
        )
    if not merged_by("\n".join(commit_trailers(root, oid))):
        notes.append(f"warning: the merge commit {oid[:10]} lacks the '{MERGED_BY}' trailer")
    return None, notes


def land_remote(invoker: Context, dod: Dod, message: str) -> tuple[list[str], str | None]:
    """Step 8 with a remote: push, open (or reuse) the pull request with the body pr_body()
    writes (design E, the proof shown inline), wait for the checks that gate it (judge_checks;
    the team tier also for an approving review), squash-merge it on the server with the squash
    message, whose last line is the Merged-By trailer, then sync the default branch to the
    merge commit (sync_merged) and delete the branch. A pull request that merged on an earlier
    run whose sync failed goes straight to the sync."""
    ctx = dod.ctx
    root, default, branch = ctx.root, ctx.default, ctx.branch or ""
    if shutil.which("gh") is None:
        return [], "gh is not installed: the remote path opens a pull request with it"
    tip = rev(root, "HEAD") or ""
    team = project_setting(root, "tier") == "team"
    env = lifecycle_env()
    plan = remote_plan(branch, default, dod.title, tip, team)
    push, create, _checks, *rest = plan
    review = rest.pop(0) if team else None
    squash, _view, confirm, fetch, delete = rest
    body = message.split("\n\n", 1)[1] if "\n\n" in message else message  # gh adds the title
    notes: list[str] = []
    pr = pull_request(root, env, branch)
    merged = pr is not None and pr.state == "MERGED" and pr.head == tip
    number = pr.number if pr is not None and (merged or pr.state == "OPEN") else ""
    again = merge_again(branch, default)
    oid = ""
    if pr is not None and merged:
        notes.append(f"pull request #{number} had merged on origin already")
        oid = pr.merge or merge_commit(root, env, branch, tip)
        if not oid:
            return notes, f"gh names no merge commit for {branch} yet; {again}"
    else:
        proc = run_cmd(push, root, env)
        if proc.returncode != 0:
            return notes, f"git push -u origin {branch}: {said(proc)}"
        if pr is None or pr.state != "OPEN":
            proc = run_cmd(create, root, env, stdin=pr_body(dod, body, tip))
            if proc.returncode != 0:
                return notes, f"gh pr create: {said(proc)}"
            found = re.search(r"/pull/(\d+)", proc.stdout)
            number = found.group(1) if found else number
        problem, unreported = wait_for_checks(root, env, branch, dod.flags.without_ci, notes)
        if problem:
            return notes, problem
        if unreported:
            who = user_name(root)
            body = with_record(
                body,
                f"Landed without CI (--without-ci, by {who}): {dod.flags.without_ci}. "
                f"{', '.join(unreported)} never reported on the pull request.",
            )
        if review is not None:
            proc = run_cmd(review, root, env)
            if proc.stdout.strip() != "APPROVED":
                return (
                    notes,
                    "the team tier waits for an approving review; merge again once it is in",
                )
        proc = run_cmd(squash, root, env, stdin=body)
        if proc.returncode != 0:
            return notes, f"gh pr merge: {said(proc)}"
        oid = merge_commit(root, env, branch, tip)
        if not oid:
            return notes, f"gh names no merge commit for {branch} yet; {again}"
    problem, synced = sync_merged(root, branch, default, env, (confirm, fetch), oid)
    if problem:
        return notes, problem
    shown = f"pull request #{number}" if number else "the pull request"
    notes = [f"{default} ({oid[:10]}): {shown} squash-merged on origin, synced here", *notes]
    notes += synced
    gone = run_cmd(["git", "ls-remote", "origin", f"refs/heads/{branch}"], root, env, timeout=60)
    if gone.returncode == 0 and gone.stdout.strip():
        proc = run_cmd(delete, root, env)
        notes.append(
            f"deleted {branch} on origin"
            if proc.returncode == 0
            else f"kept {branch} on origin: {said(proc, 2)}"
        )
    notes += drop_branch(invoker.root, root, branch, default, oid)
    notes += drop_workers(invoker.root, root, branch, default, tip)
    return notes, None


def print_land_plan(dod: Dod) -> None:
    """merge --dry-run and status --merge: steps 7 and 8 as merge would run them."""
    if dod.stop:
        return
    ctx = dod.ctx
    if dod.writes and not dod.closing:
        print(label("would close") + f"one commit on {ctx.branch}: {', '.join(dod.writes)}")
    if any(step.name == "land" and step.level == "FAIL" for step in dod.steps):
        return
    if dod.landing == "remote":
        # the pull request's head is the close commit, which merge writes before it pushes
        tip = CLOSE_COMMIT if dod.writes and not dod.closing else ctx.head or ""
        team = project_setting(ctx.root, "tier") == "team"
        gate = gate_description(generated_ci(ctx.root))
        for argv in remote_plan(ctx.branch or "", ctx.default, dod.title, tip, team):
            print(label("would run") + shlex.join(argv))
            if note := remote_step_note(argv, ctx.default, gate):
                print(" " * 22 + f"({note})")
    else:
        what = f"a squash commit on {ctx.default} (Merged-By), then {ctx.branch} is deleted"
        print(label("would land") + what)


def print_landed(invoker: Context, dod: Dod, notes: list[str]) -> None:
    """The end of a merge: what it wrote, where it landed, and what comes next."""
    if dod.roadmap_note:
        print(label("roadmap") + dod.roadmap_note)
    print(label("CHANGELOG") + dod.changelog_note)
    for number, note in enumerate(notes):
        print((label("merged") if number == 0 else " " * 22) + note)
    ref = f"refs/heads/{invoker.default}"
    text = read_blobs(invoker.root, ref, [ROADMAP]).get(ROADMAP, "")
    pending = [(slug, title) for _, slug, done, title, _ in roadmap_entries(text) if not done]
    if pending:
        slug, title = pending[0]
        upcoming = f'{slug} "{title}"' if title else slug
    else:
        upcoming = "the roadmap has no open item"
    print(label("next") + f"{upcoming}. Still right? If not: /sdd replan")
    count = features_since_replan(invoker.root, ref)
    if count >= 3:
        print(label("replan") + f"{count} features merged since the last replan: /sdd replan")
    print(label("now") + "/clear")


def features_since_replan(root: Path, ref: str) -> int:
    """feat/ merges on the default branch since the last plan/ merge, from the squash bodies."""
    out = git(root, "log", "--first-parent", "-n", "200", "--format=%B%x1e", ref) or ""
    count = 0
    for body in out.split("\x1e"):
        match = re.search(r"(?m)^Branch: (\S+)$", body)
        if match is None:
            continue
        if match.group(1).startswith("plan/"):
            break
        count += match.group(1).startswith("feat/")
    return count


# ---------------------------------------------------------------- lifecycle: status flags


def cmd_status_merge(ctx: Context) -> int:
    """The Definition of Done, read-only: every check merge runs, and what it would write."""
    if not (ctx.root / SPECS).is_dir():
        print(f"FAIL  no {SPECS}/ folder: this repo has no specs yet (run /project-init)")
        return 1
    print(f"status --merge {ctx.branch or 'detached HEAD'}: the Definition of Done, read-only")
    dod = dod_prepare(ctx, MergeFlags(preview=True))
    if not dod.stop:
        dod_prove(dod)
    print_steps(dod.steps)
    print_review(dod)
    print_land_plan(dod)
    humans = [step.name for step in dod.steps if step.level == "human"]
    if not dod.ok:
        print(f"merge would refuse ({plural(dod.problems, 'problem')})")
        return 1
    if humans:
        flags = ["--attest"] if "human checks" in humans else []
        flags += ["--read-trunk"] if "trunk" in humans else []
        flags += ["--gate-change"] if "gate files" in humans else []
        flags += ["--reapprove"] if "amended after approval" in humans else []
        read = [{"trunk": "trunk diff"}.get(name, name) for name in humans]
        print(
            f"ready for a human: `! mise run merge -- {' '.join(flags)}` after reading the "
            + " and ".join(read)
        )
    else:
        print("ready: a human runs `! mise run merge`")
    return 0


@dataclass
class Audit:
    ref: str | None
    commits: int  # first-parent commits since adoption
    anchor: str | None  # the oldest of them
    unmerged: list[tuple[str, str]]  # (sha, subject) without the Merged-By trailer
    note: str = ""


def audit_default(ctx: Context) -> Audit:
    """The trailer audit (specs/README.md#gates): each first-parent commit on the default branch
    since adoption carries `Merged-By: mise run merge`. Adoption is the oldest first-parent
    commit that carries it (the G1 merge), or, when none does, the one that added .project.toml.
    A commit's date is never used: it is easy to fake."""
    ref = ctx.default_ref
    if ref is None:
        return Audit(None, 0, None, [], f"no {ctx.default} branch")
    out = git(
        ctx.root,
        "log",
        "--first-parent",
        "--format=%H%x1f%s%x1f%(trailers:key=Merged-By,valueonly,separator=%x2C,unfold)%x1e",
        ref,
    )
    entries = []
    for record in (out or "").split("\x1e"):
        parts = record.strip("\n").split("\x1f")
        if len(parts) == 3 and parts[0]:
            values = [v.strip() for v in parts[2].split(",")]
            entries.append((parts[0], parts[1], TOOL_TRAILER[1] in values))
    merged = [index for index, entry in enumerate(entries) if entry[2]]
    note = ""
    if merged:
        anchor = merged[-1]
    else:
        added = git_lines(
            ctx.root,
            "log",
            "--first-parent",
            "--diff-filter=A",
            "--format=%H",
            ref,
            "--",
            ".project.toml",
        )
        index = next((i for i, e in enumerate(entries) if added and e[0] == added[-1]), None)
        if index is None:
            return Audit(ref, 0, None, [], f"not adopted yet: no .project.toml on {ctx.default}")
        anchor = index
        note = f"no commit on {ctx.default} carries the Merged-By trailer"
    audited = entries[: anchor + 1]
    unmerged = [(sha, subject) for sha, subject, ok in audited if not ok]
    return Audit(ref, len(audited), audited[-1][0], unmerged, note)


def audit_lines(ctx: Context) -> tuple[list[str], list[str]]:
    """(warnings, summary) of the trailer audit, for status --audit and doctor."""
    audit = audit_default(ctx)
    if audit.anchor is None:
        return [], [f"audit {ctx.default}: {audit.note}"]
    warnings = [
        f"{sha[:10]} \"{subject}\" on {ctx.default} has no '{MERGED_BY}' trailer: it did not "
        "land through merge"
        for sha, subject in audit.unmerged
    ]
    if audit.note:
        warnings.insert(0, audit.note)
    since = f"since adoption ({audit.anchor[:10]})"
    if audit.unmerged:
        counted = plural(audit.commits, "commit")
        summary = f"audit {ctx.default}: {len(audit.unmerged)} of {counted} {since} skipped merge"
    else:
        summary = (
            f"audit {ctx.default}: ok ({plural(audit.commits, 'commit')} {since}, all via merge)"
        )
    return warnings, [summary]


def cmd_status_audit(ctx: Context) -> int:
    """WARN for each commit that reached the default branch around merge. A warning, never a
    failure: history cannot be fixed by the next person who runs a check (CI annotates it)."""
    warnings, summary = audit_lines(ctx)
    for text in warnings:
        print(f"WARN  {text}")
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"::warning title=main audit::{text}")
    for text in summary:
        print(text)
    return 0


# ---------------------------------------------------------------- lifecycle: abandon


def cmd_abandon(ctx: Context, args: argparse.Namespace) -> int:
    """Drop the change checked out here: tag its tip abandoned/<slug>, commit a backlog report
    (the why, and how to get the work back) onto the default branch with the Merged-By trailer,
    then delete the branch (its change folder goes with it)."""
    why = " ".join(args.why).strip()
    if not why:
        raise UsageError('abandon needs the reason: abandon -- "<why>"')
    branch = ctx.branch
    if branch is None or ctx.on_default or ctx.lane is None or ctx.lane == "release":
        print(
            "FAIL  abandon drops the lane branch checked out here; "
            f"{branch or 'detached HEAD'} is not one"
        )
        return 1
    if WORKER_RE.search(branch):
        print(f"FAIL  {branch} is a parallel worker: remove its worktree, then git branch -D it")
        return 1
    dirty = dirty_paths(ctx.root, backlog_ok=True)
    if dirty:
        print_dirty(dirty, "commit what should survive under the tag, or discard it")
        return 1
    root, head = ctx.root, ctx.head
    main = rev(root, f"refs/heads/{ctx.default}")
    if head is None or main is None:
        print(f"FAIL  no commit on {branch}, or no local {ctx.default} branch")
        return 1
    slug = ctx.slug or slugify(branch)
    existing_tags = set(git_lines(root, "tag", "--list", f"abandoned/{slug}*"))
    tag = next(
        t
        for n in range(1, 1000)
        if (t := f"abandoned/{slug}" + (f"-{n}" if n > 1 else "")) not in existing_tags
    )
    listed = set(git_lines(root, "ls-tree", "--name-only", main, f"{BACKLOG_DIR}/"))
    rel = next(
        p
        for n in range(1, 1000)
        if (p := f"{BACKLOG_DIR}/{today()}-{slug}" + (f"-{n}" if n > 1 else "") + ".md")
        not in listed
        and not (root / p).exists()
    )
    report = abandon_report(ctx, why, tag)
    env = lifecycle_env()
    proc = git_run(root, env, "tag", "-a", tag, head, "-m", f"abandoned: {why}")
    if proc.returncode != 0:
        print(f"FAIL  git tag {tag}: {said(proc)}")
        return 1
    message = (
        f"docs(backlog): abandon {slug}\n\n{why}\n\n"
        f"Branch: {branch} at {head[:10]}, tagged {tag}\n\n{MERGED_BY}\n"
    )
    commit, problem = commit_file_onto(root, main, rel, report, message)
    if problem is None and commit is not None:
        problem = land_on_default(root, ctx.default, main, commit)
    if problem or commit is None:
        print(f"FAIL  the backlog report did not land on {ctx.default}: {problem}")
        print(f"      {branch} is kept; its tip is tagged {tag}")
        return 1
    notes = [f"{rel} on {ctx.default} ({commit[:10]}, Merged-By trailer)"]
    mode, why_not = landing_mode(ctx)
    if mode == "remote" and why_not is None:
        push = git_run(root, lifecycle_env(merge=True), "push", "origin", ctx.default)
        notes.append(
            f"pushed {ctx.default}"
            if push.returncode == 0
            else f"push {ctx.default} by hand: {said(push)}"
        )
    notes += drop_branch(root, root, branch, ctx.default, commit)
    print(f"abandon {branch}: {why}")
    print(label("tag") + f"{tag} ({head[:10]}); get it back: git switch -c {branch} {tag}")
    for note in notes:
        print(label("done") + note)
    print(label("next") + "the next replan decides whether it comes back")
    return 0


def commit_file_onto(
    root: Path, parent: str, rel: str, text: str, message: str
) -> tuple[str | None, str | None]:
    """A commit on top of parent that adds one file, built in a scratch index (no checkout, no
    hooks: the file is the tool's own). Returns (sha, problem)."""
    env = lifecycle_env()
    blob = git_run(root, env, "hash-object", "-w", "--stdin", stdin=text)
    if blob.returncode != 0:
        return None, f"git hash-object: {said(blob)}"
    with tempfile.TemporaryDirectory(prefix="project-abandon-") as tmp:
        scratch = {**env, "GIT_INDEX_FILE": str(Path(tmp) / "index")}
        steps = (
            ["read-tree", parent],
            ["update-index", "--add", "--cacheinfo", f"100644,{blob.stdout.strip()},{rel}"],
            ["write-tree"],
        )
        proc = blob
        for args in steps:
            proc = git_run(root, scratch, *args)
            if proc.returncode != 0:
                return None, f"git {args[0]}: {said(proc)}"
        tree = proc.stdout.strip()
    proc = git_run(root, env, "commit-tree", tree, "-p", parent, "-F", "-", stdin=message)
    if proc.returncode != 0:
        return None, f"git commit-tree: {said(proc)}"
    return proc.stdout.strip(), None


def section_text(text: str, heading: str) -> str:
    """The body of one `## <heading>` section of a markdown file."""
    out: list[str] = []
    inside = False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line[3:].strip() == heading
            continue
        if inside:
            out.append(line)
    return "\n".join(out).strip()


def abandon_report(ctx: Context, why: str, tag: str) -> str:
    state = load_state(ctx)
    change = state.open_change
    title = ctx.branch or ""
    if change is not None:
        req = read_text(ctx.root / change.path / "requirements.md") or ""
        named = change.fields.get("title", "")
        if named and not PLACEHOLDER_RE.search(named):
            match = TITLE_PARTS_RE.match(named)
            title = match.group(4) if match else named
        what = "\n\n".join(
            s for s in (section_text(req, "Why"), section_text(req, "Scope")) if s and "{" not in s
        )
    else:
        what = ""
    subjects = [subject for _, subject, _ in branch_commits(ctx)]
    if not what:
        what = f"The work on {ctx.branch}."
    notes = [
        (
            f"- {ctx.branch} ended at {(ctx.head or '')[:10]}; the tip is tagged `{tag}`. Get it "
            f"back: `git switch -c {ctx.branch} {tag}`."
        ),
        f"- Its commits: {'; '.join(subjects[:10]) or 'none'}.",
        "- The next replan decides whether it comes back.",
    ]
    values = {
        "TITLE": f"Abandoned: {title}",
        "WHAT": what,
        "WHY": f"Abandoned on {today()}: {why}",
        "NOTES": "\n".join(notes),
    }
    return fill(BACKLOG_TEMPLATE, values)


# ---------------------------------------------------------------- lifecycle: doctor


@dataclass
class EnvRow:
    """One row of the typed env contract in .env.example."""

    name: str
    kind: str  # knob | secret | flag (a bool, off by default, that turns new behaviour on)
    type: str  # int | float | bool | str, optionally with a range: float 0..100
    required: bool
    default: str | None  # None: no default ("-")
    line: int
    notes: str = ""


READ_IN_RE = re.compile(r"\bread in ([^;|]+)")


ENV_PREFIX_RE = re.compile(r"""\benv_prefix\s*=\s*['"]([A-Za-z0-9_]*)['"]""")
# a class whose base ends in Settings: pydantic's BaseSettings, or the project's own subclass
SETTINGS_CLASS_RE = re.compile(r"(?m)^[ \t]*class[ \t]+\w+[ \t]*\([^)]*Settings\b")


def names_variable(text: str, name: str) -> bool:
    """Whether a file's text still names the environment variable, as a whole word: the name
    itself (PORT, never the port inside `import`), or, in a file with a pydantic-settings class
    (BaseSettings, or a class of the project's own that ends in Settings, such as AppSettings),
    its field, in any case (case_sensitive=False): the name in lower case, or the name past
    the model's env_prefix (ORCA_DEBUG is the field `debug` under env_prefix="ORCA_"). Outside
    such a file a lower-case word is code (`import sys`, `def main`), not the variable."""

    def names(word: str, where: str, flags: re.RegexFlag = re.NOFLAG) -> bool:
        pattern = rf"(?<![A-Za-z0-9_]){re.escape(word)}(?![A-Za-z0-9_])"
        return bool(word) and re.search(pattern, where, flags) is not None

    if names(name, text):
        return True
    if "BaseSettings" not in text and not SETTINGS_CLASS_RE.search(text):
        return False
    fields = [name] + [
        name[len(prefix) :]
        for prefix in ENV_PREFIX_RE.findall(text)
        if prefix and name.lower().startswith(prefix.lower())
    ]
    return any(names(field_name, text, re.IGNORECASE) for field_name in fields)


def stale_read_notes(root: Path, row: EnvRow) -> list[str]:
    """The files a row's `read in <files>` note names that no longer name the variable
    (names_variable): the read moved (to a config.py, say), and the note went stale with it."""
    match = READ_IN_RE.search(row.notes)
    stale: list[str] = []
    for part in match.group(1).split(",") if match else []:
        rel = re.sub(r":\d+$", "", part.strip())  # an older render wrote file:line
        path = PurePosixPath(rel)
        if not rel or path.is_absolute() or ".." in path.parts:
            continue
        text = read_text(root / rel)
        if text is None or not names_variable(text, row.name):
            stale.append(rel)
    return stale


def env_contract(text: str) -> tuple[list[EnvRow], list[str]]:
    """The rows of `# NAME | kind | type | required | default | notes`, and grammar problems.
    The header row and the commented example lines (`#NAME=value`) are not rows."""
    rows: list[EnvRow] = []
    problems: list[str] = []
    for number, line in enumerate(text.splitlines(), 1):
        match = ENV_ROW_RE.match(line)
        if match is None or match.group(1) == "NAME":
            continue
        cells = [cell.strip() for cell in match.group(2).split("|")]
        where = f".env.example:{number}"
        if len(cells) < 4:
            problems.append(
                f"{where}: a row is '# NAME | kind | type | required | default | notes'"
            )
            continue
        kind, kind_of, required, default = cells[0], cells[1], cells[2], cells[3]
        if kind not in ("knob", "secret", "flag"):
            problems.append(f"{where}: kind is knob, secret or flag, not '{kind}'")
            continue
        if required not in ("yes", "no"):
            problems.append(f"{where}: required is yes or no, not '{required}'")
            continue
        value = None if default in ("", "-") else default
        notes = "|".join(cells[4:]).strip()
        rows.append(
            EnvRow(match.group(1), kind, kind_of or "str", required == "yes", value, number, notes)
        )
    return rows, problems


def dotenv(text: str) -> dict[str, str]:
    """KEY=value lines of a .env file; quotes and `export ` stripped, comments left out."""
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.removeprefix("export ").partition("=")
        if not sep:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] in "'\"" and value[-1] == value[0]:
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        values[key.strip()] = value
    return values


def type_problem(kind_of: str, value: str) -> str | None:
    """Why value does not fit the contract's type, or None when it does (or the type is one
    doctor cannot check). The value itself is never quoted: a secret pasted into a knob's slot
    must not reach the terminal."""
    words = kind_of.split()
    kind = words[0].lower() if words else "str"
    bounds = RANGE_RE.match(words[1]) if len(words) > 1 else None
    number: float | None = None
    if kind == "int":
        if not re.fullmatch(r"\s*[+-]?\d+\s*", value):
            return "the value is not an int"
        number = int(value)
    elif kind == "float":
        try:
            number = float(value)
        except ValueError:
            return "the value is not a float"
        if not math.isfinite(number):
            return "the value is not a finite float"
    elif kind == "bool":
        if value.strip().lower() not in BOOL_WORDS:
            return "the value is not a bool (true or false, yes or no, on or off, 1 or 0)"
    if bounds is not None and number is not None:
        low, high = float(bounds.group(1)), float(bounds.group(2))
        if not low <= number <= high:
            return f"the value is outside {bounds.group(1)}..{bounds.group(2)}"
    return None


OP_PART_RE = re.compile(r"[A-Za-z0-9._-](?:[A-Za-z0-9._ -]*[A-Za-z0-9._-])?")
OP_QUERY_RE = re.compile(r"\?[a-z-]+=[A-Za-z0-9_-]+")  # ?attribute=otp, ?ssh-format=openssh


def op_pointer(value: str) -> bool:
    """A 1Password secret reference: op://<vault>/<item>/[<section>/]<field>, each part in
    1Password's own characters (letters, digits, - _ . and inner spaces; a name with other
    characters is referenced by its ID). So `op://a/b/c <note>` or a value pasted after the
    pointer is refused. A space inside a name is 1Password's, not a reason to refuse one."""
    if not value.startswith("op://"):
        return False
    rest = value.removeprefix("op://")
    head, mark, query = rest.partition("?")
    if mark and not OP_QUERY_RE.fullmatch(mark + query):
        return False
    parts = head.split("/")
    return len(parts) in (3, 4) and all(OP_PART_RE.fullmatch(part) for part in parts)


def judge_env(row: EnvRow, value: str | None) -> tuple[str, str]:
    """(level, text) for one contract row. Empty means unset, so the default applies; only a
    non-empty knob of the wrong type, a required secret that is unset, or a secret that is not
    an op:// pointer FAILs (an optional secret, unset, is ok).
    Empty is exactly "", as pydantic-settings' env_ignore_empty reads it (H17): a value of
    spaces reaches the app, so it is judged against the type like any other. A secret's value
    is never printed."""
    unset = "unset" if value is None else "empty" if value == "" else ""
    if row.kind == "secret":
        if unset and not row.required:
            return (
                "ok",
                f"secret, {unset}: optional (required no); its op:// pointer in .env turns it on",
            )
        if unset:
            return (
                "FAIL",
                f"secret, {unset}: put its op:// pointer in .env (op://<vault>/<item>/<field>)",
            )
        if not op_pointer((value or "").strip()):
            why = "secret, not an op:// pointer (op://<vault>/<item>/<field>): .env holds op://"
            return "FAIL", f"{why} pointers only, never the value"
        return "ok", "secret, an op:// pointer"
    if unset:
        if row.default is not None:
            return "ok", f"{unset}: default {row.default} applies"
        if row.required:
            return "warn", f"{unset}, required and without a default: set it in .env"
        return "ok", unset
    problem = type_problem(row.type, value or "")
    if problem:
        return "FAIL", problem
    kind = (row.type.split() or ["str"])[0].lower()
    if kind in ("int", "float", "bool"):
        return "ok", f"{(value or '').strip()} ({row.type})"
    return "ok", f"set ({row.type})"  # free text is not echoed: it could be anything


def gaps_naming(root: Path, name: str) -> list[Scenario]:
    """The [gap] scenarios whose text names the variable: behaviour the spec says the app
    lacks today. H17's "empty means unset" is the contract; an open gap on the variable says
    the app does not honour it yet (a migrated repo before its entrypoint fix)."""
    paths, _ = capability_files(root)
    texts = {path: read_text(root / path) or "" for path in paths}
    named = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])")
    return [s for s in load_scenarios(texts, None).values() if s.gap and named.search(s.block)]


FLAG_OFF_WORDS = ("0", "false", "no", "off")
FLAG_DEBT_DAYS = 30  # a flag row older than this on the default branch is debt: launch it


def flag_row_problems(row: EnvRow) -> list[str]:
    """A flag row's type is bool and its default is off (design B.2): the new behaviour runs
    only once someone turns it on."""
    problems = []
    if row.type.strip().lower() != "bool":
        problems.append(f"a flag's type is bool, not '{row.type}'")
    if (row.default or "").strip().lower() not in FLAG_OFF_WORDS:
        shown = row.default or "-"
        problems.append(f"a flag's default is off (0, false, no or off), not '{shown}'")
    return problems


def doctor_flag_debt(ctx: Context, report: Report) -> None:
    """Flag debt: a flag row whose line reached the default branch more than FLAG_DEBT_DAYS ago
    (the date of the commit there that added it). Its launch is due: flip it on, then remove the
    flag, its off path and its [flag-off] scenarios."""
    ref = ctx.default_ref
    rows = env_contract(read_text(ctx.root / ".env.example") or "")[0]
    if ref is None:
        return
    now = time.time()
    for row in (row for row in rows if row.kind == "flag"):
        added = f"-G^#[[:space:]]*{row.name}[[:space:]]*[|]"  # the row's own line
        log = ["log", "--reverse", "--format=%ct", added, ref, "--", ".env.example"]
        stamp = next(iter(git_lines(ctx.root, *log)), "")
        if not stamp.isdigit():
            continue
        days = int((now - int(stamp)) // 86400)
        if days > FLAG_DEBT_DAYS:
            since = datetime.fromtimestamp(int(stamp)).astimezone().date().isoformat()
            report.warn(
                f"env {row.name}: flag debt: on {ctx.default} since {since} ({days} days); "
                "launch it: flip it on, then remove the flag, its off path and its [flag-off] "
                "scenarios"
            )


def doctor_env(root: Path, report: Report) -> None:
    text = read_text(root / ".env.example")
    if text is None:
        report.warn(".env.example is missing: the typed env contract (specs/tech-stack.md)")
        return
    rows, problems = env_contract(text)
    for problem in problems:
        report.fail(problem)
    values = dotenv(read_text(root / ".env") or "")
    for row in rows:
        value = values.get(row.name, os.environ.get(row.name))
        level, text = judge_env(row, value)
        getattr(report, {"ok": "ok", "warn": "warn", "FAIL": "fail"}[level])(
            f"env {row.name}: {text}"
        )
        for problem in flag_row_problems(row) if row.kind == "flag" else []:
            report.fail(f"env {row.name}: {problem}")
        gaps = gaps_naming(root, row.name) if value == "" and row.kind != "secret" else []
        if gaps:
            ids = ", ".join(f"{s.id} [gap: {s.gap}]" for s in gaps)
            report.warn(
                f"env {row.name}: empty, which the contract reads as unset, but the app may not "
                f"yet: open gap scenarios name it ({ids}). Unset it (`env -u {row.name}`) until "
                "that gap is closed"
            )
        for rel in stale_read_notes(root, row):
            report.warn(
                f"env {row.name}: .env.example says it is read in {rel}, which no longer names "
                "it; point the row's notes at the file that reads it now"
            )
    declared = {row.name for row in rows}
    for name in sorted(set(values) - declared):
        report.warn(
            f"env {name}: in .env but not in the .env.example contract; declare it there (a "
            "secret as an op:// pointer) or drop it from .env"
        )
    if not rows and not problems:
        report.ok("env: the contract names no variable")


def doctor_tools(root: Path, report: Report) -> None:
    """Every tool the gates need, checked by running it (a shim that exists but fails is no
    tool)."""
    uv = uv_binary(root)
    cliff = git_cliff_argv()
    tools: list[tuple[str, list[str] | None]] = [
        ("git", ["git", "--version"]),
        ("mise", ["mise", "--version"]),
        ("uv", [uv, "--version"] if uv else None),
        ("gitleaks", ["gitleaks", "version"]),
        ("git-cliff", [*cliff, "--version"] if cliff else None),
    ]
    env = lifecycle_env()
    for name, argv in tools:
        proc = run_cmd(argv, root, env, timeout=120) if argv else None
        if proc is None or proc.returncode != 0:
            why = said(proc, 1) if proc is not None else "not found"
            report.fail(f"{name}: not runnable here ({why}): run mise install")
            continue
        first = next((line for line in plain(proc.stdout).splitlines() if line.strip()), "")
        report.ok(f"{name}: {first.strip()}")


def baseline_rows(text: str | None) -> dict[str, set[str]] | None:
    """The ruff baseline block of a pyproject.toml text, file -> codes: the per-file-ignores
    rows render wrote under the `# project-init baseline: shrink only` comment, up to the next
    table. The project's own rows above the comment are not the baseline. None: no block. A
    root file's row is keyed `./setup.py` (an older render wrote `setup.py`): both are one file."""
    lines = (text or "").splitlines()
    start = next(
        (
            i
            for i, line in enumerate(lines)
            if line.lstrip().startswith("#") and BASELINE_MARK in line
        ),
        None,
    )
    if start is None:
        return None
    body: list[str] = []
    for line in lines[start + 1 :]:
        if line.lstrip().startswith("["):
            break
        body.append(line)
    try:
        data = parse_toml("\n".join(body))
    except ValueError:
        return {}
    return {
        str(path).removeprefix("./"): {str(code) for code in codes}
        for path, codes in data.items()
        if isinstance(codes, list)
    }


def baseline_reference(ctx: Context) -> tuple[dict[str, set[str]] | None, str]:
    """(the baseline rows the working tree's block may only shrink from, where they come from).
    Once project-init landed on the default branch (it holds .project.toml): that branch's
    block, empty when it has none. Before that, on the branch that adopts the repo: the first
    commit there whose pyproject.toml holds the block, which is the block as render wrote it.
    (None, "") before any such commit: the block is render's own output, not committed yet."""
    root = ctx.root
    if ctx.default_ref and has_manifest(root, ctx.default_ref):
        text = read_blobs(root, ctx.default_ref, ["pyproject.toml"]).get("pyproject.toml")
        return baseline_rows(text) or {}, ctx.default
    if ctx.head is None:
        return None, ""
    since = f"{ctx.base}..HEAD" if ctx.base else "HEAD"
    for sha in git_lines(root, "log", "--reverse", "--format=%H", since, "--", "pyproject.toml"):
        rows = baseline_rows(read_blobs(root, sha, ["pyproject.toml"]).get("pyproject.toml"))
        if rows is not None:
            return rows, sha[:10]
    return None, ""


def doctor_baseline(ctx: Context, pyproject: str, report: Report) -> None:
    """N3: the ruff baseline only shrinks. Growth is counted per file against baseline_reference:
    a file the block did not have, or a code its row did not have."""
    rows = baseline_rows(pyproject)
    if rows is None:
        return
    reference, where = baseline_reference(ctx)
    if reference is None:
        report.ok("N3: the ruff baseline is render's, not committed yet: nothing to compare with")
        return
    grown = {path: sorted(codes - reference.get(path, set())) for path, codes in rows.items()}
    grown = {path: codes for path, codes in sorted(grown.items()) if codes}
    for path, codes in grown.items():
        report.fail(
            f"N3: the ruff baseline grew: {path} gains {', '.join(codes)} (against {where}); it "
            "only shrinks, so fix the findings instead"
        )
    if not grown:
        report.ok(
            f"N3: the ruff baseline did not grow ({plural(len(rows), 'file')}, against {where})"
        )


def doctor_repo(ctx: Context, report: Report) -> None:
    """The repo side: python owned by uv (H16), the pyproject description (H6), the ruff
    baseline that only shrinks (N3), and the mise tasks the docs name (I15)."""
    root = ctx.root
    for name in MISE_CONFIGS:
        path = root / name
        if not path.is_file():
            continue
        try:
            tools = parse_toml(path.read_text(encoding="utf-8")).get("tools")
        except (OSError, ValueError) as exc:
            report.fail(f"{name}: {exc}")
            continue
        pinned = [
            k for k in (tools if isinstance(tools, dict) else {}) if k.split(":")[-1] == "python"
        ]
        if pinned:
            report.fail(
                f"H16: {name} pins python in [tools]; uv owns the interpreter (.python-version)"
            )
    pyproject = read_text(root / "pyproject.toml")
    if pyproject is not None:
        try:
            project = parse_toml(pyproject).get("project")
        except ValueError as exc:
            report.fail(f"pyproject.toml: {exc}")
            project = None
        described = project.get("description") if isinstance(project, dict) else None
        if isinstance(described, str) and PLACEHOLDER_DESCRIPTION in described:
            report.fail(
                "H6: pyproject.toml description is uv's placeholder; it is the mission one-liner"
            )
        doctor_baseline(ctx, pyproject, report)
    state = load_state(ctx)
    check_doc_commands(state)
    fails = [
        text for level, text in state.report.lines if level == "FAIL" and text.startswith("I15")
    ]
    for text in fails:
        report.fail(text)
    if not fails:
        report.ok("I15: every `mise run` the docs name is a task")


def doctor_trunk(root: Path, report: Report) -> None:
    """The trunk map of specs/tech-stack.md: without one every path is leaf, so merge asks no
    one to read a diff (a warning); a malformed line FAILs as in check."""
    trunk = trunk_at(root)
    if not trunk.found:
        report.warn(
            f"{TECH_STACK} has no ## Trunk section: every path counts as leaf, so merge asks no "
            f"one to read a diff; add one ({PROCESS}#formats)"
        )
        return
    for problem in trunk.problems:
        report.fail(problem)
    count = len(trunk.entries)
    report.ok(f"trunk: {count} {'entry' if count == 1 else 'entries'} in {TECH_STACK}")


def cmd_doctor(ctx: Context, args: argparse.Namespace) -> int:
    del args
    report = Report()
    if not (ctx.root / ".project.toml").is_file():
        print("FAIL  no .project.toml: this repo is not set up yet (run /project-init)")
        return 1
    doctor_tools(ctx.root, report)
    problems = gate_setup_problems(ctx)
    for problem in problems:
        report.fail(problem)
    if not problems:
        where = "matches it" if ctx.default_ref else "waits for its first update"
        report.ok(
            "git gates: core.hooksPath, receive.hideRefs and the pinned main guard are set; "
            f"the guard's record of {ctx.default} {where}"
        )
    landing, origin_problem = landing_mode(ctx)  # what merge's land step refuses, up front
    if origin_problem:
        report.fail(origin_problem)
    elif landing == "local":
        report.ok(f"origin: none, so merge squashes onto {ctx.default} locally")
    else:
        report.ok("origin: the origin_url .project.toml records, so merge opens a pull request")
    doctor_env(ctx.root, report)
    doctor_flag_debt(ctx, report)
    doctor_repo(ctx, report)
    doctor_trunk(ctx.root, report)
    warnings, summary = audit_lines(ctx)
    for text in warnings:
        report.warn(text)
    for text in summary:
        if warnings:
            report.warn(text)
        else:
            report.ok(text)
    report.print()
    verdict = "FAIL" if report.errors else "ok"
    print(
        f"doctor: {verdict} ({plural(report.errors, 'problem')}, "
        f"{plural(report.count('warn'), 'warning')})"
    )
    return 1 if report.errors else 0


# ---------------------------------------------------------------- lifecycle: release


def distribution(root: Path) -> str | None:
    """The first word under `## Distribution` in specs/tech-stack.md, when it is a known one."""
    text = read_text(root / TECH_STACK) or ""
    body = section_text(text, "Distribution")
    for line in body.splitlines():
        word = line.strip().strip("`*-").strip().split(" ")[0].lower() if line.strip() else ""
        if word and not word.startswith("<!--"):
            return word if word in DISTRIBUTIONS else None
    return None


def cmd_release(ctx: Context, args: argparse.Namespace) -> int:
    """`release <bump> [--dry-run]` by the Distribution line (design, release shapes): pypi and
    git bump the version, write the CHANGELOG version section, land and tag; pypi publishes
    through `op run -- uv publish`, git with a remote makes a GitHub release; service tags. none
    has no release."""
    dist = distribution(ctx.root)
    if dist is None:
        print(
            f"release: {TECH_STACK} names no distribution under '## Distribution' "
            f"({', '.join(DISTRIBUTIONS)})"
        )
        return 1
    if dist == "none":
        print("no release for distribution: none")
        return 1
    uv = uv_binary(ctx.root)
    if uv is None:
        print("FAIL  uv is not on PATH: run mise install")
        return 1
    env = lifecycle_env()
    proc = run_cmd([uv, "version", "--bump", args.bump, "--dry-run", "--short"], ctx.root, env)
    current = run_cmd([uv, "version", "--short"], ctx.root, env)
    version = proc.stdout.strip()
    if proc.returncode != 0 or current.returncode != 0 or not version:
        print(f"FAIL  uv version --bump {args.bump} --dry-run: {said(proc)}")
        return 1
    if args.dry_run:
        return release_preview(ctx, dist, args.bump, current.stdout.strip(), version)
    return release_cut(ctx, dist, args.bump, version)


def release_preview(ctx: Context, dist: str, bump: str, current: str, version: str) -> int:
    """The P5 dry-runs: `uv version --bump <b> --dry-run`, `git cliff --bumped-version`, and
    `uv build -o <temp dir>` for pypi and git."""
    root, env = ctx.root, lifecycle_env()
    print(f"release {bump} --dry-run: {ctx.name}, distribution {dist}; nothing is written")
    print(label("version") + f"{current} -> {version} (uv version --bump {bump} --dry-run)")
    ok = True
    cliff = git_cliff_argv()
    if cliff is None:
        print(label("git-cliff") + "FAIL not installed here: run mise install")
        ok = False
    elif not git_lines(root, "tag", "--list", "v[0-9]*"):
        print(
            label("git-cliff")
            + f"no release tag yet, so nothing to bump from; this first release is v{version}"
        )
    else:
        proc = run_cmd([*cliff, "--bumped-version"], root, env)
        suggested = proc.stdout.strip().removeprefix("v")
        shown = suggested if proc.returncode == 0 else f"FAIL {said(proc, 2)}"
        ok = ok and proc.returncode == 0
        note = ""
        if proc.returncode == 0 and suggested != version:
            note = f"; --bump {bump} gives {version}: pick the bump the commits call for"
        print(
            label("git-cliff")
            + f"the commits since the last tag suggest {shown} (git cliff --bumped-version){note}"
        )
    if dist in ("pypi", "git"):
        uv = uv_binary(root) or "uv"
        with tempfile.TemporaryDirectory(prefix="project-release-") as tmp:
            proc = run_cmd([uv, "build", "-q", "-o", tmp], root, env, timeout=600)
            names = [p.name for p in Path(tmp).iterdir()] if proc.returncode == 0 else []
            built = sorted(n for n in names if n.endswith((".whl", ".tar.gz")))
        shown = ", ".join(built) if proc.returncode == 0 else f"FAIL {said(proc, 3)}"
        ok = ok and proc.returncode == 0
        print(label("build") + f"{shown} (uv build -o <temp dir>)")
    steps = [
        f"release/v{version} off {ctx.default}",
        f"uv version --bump {bump}",
        f"git cliff --tag v{version} -o {CHANGELOG}",
        f"land on {ctx.default} (Merged-By)",
        f"tag v{version}",
    ]
    if dist == "pypi":
        steps.append("uv build, then op run -- uv publish")
    elif dist == "git":
        steps.append("gh release create (with a remote)")
    else:
        steps.append("the deploy skill deploys the tag")
    print(label("would") + "; ".join(steps))
    print(f"release --dry-run: {'ok' if ok else 'FAIL'}")
    return 0 if ok else 1


def release_cut(ctx: Context, dist: str, bump: str, version: str) -> int:
    """The release itself, from a clean default branch: verify, then on release/v<version> the
    version bump and the CHANGELOG version section in one commit; that lands on the default
    branch like a merge (Merged-By), and the landed commit is tagged v<version>."""
    root, default = ctx.root, ctx.default
    tag, branch = f"v{version}", f"release/v{version}"
    if not ctx.on_default:
        print(f"FAIL  release runs on {default}; switch to it first")
        return 1
    dirty = dirty_paths(root, backlog_ok=True)
    if dirty:
        print_dirty(dirty, "a release starts from a clean tree")
        return 1
    if rev(root, f"refs/tags/{tag}") or rev(root, f"refs/heads/{branch}"):
        print(f"FAIL  {tag} or {branch} exists already")
        return 1
    mode, problem = landing_mode(ctx)
    if problem or mode == "remote":
        why = f": {problem}" if problem else ""
        print(f"FAIL  release with a remote is not built yet (it would land by pull request){why}")
        return 1
    mise = shutil.which("mise")
    uv = uv_binary(root) or "uv"
    cliff = git_cliff_argv()
    if mise is None or cliff is None:
        print("FAIL  mise and git-cliff are needed: run it as `! mise run release -- <bump>`")
        return 1
    env = lifecycle_env()
    proc = run_cmd([mise, "run", "verify"], root, env, timeout=PYTEST_TIMEOUT)
    if proc.returncode != 0:
        print(f"FAIL  mise run verify on {default}:\n{said(proc, 12)}")
        return 1
    main = rev(root, f"refs/heads/{default}") or ""
    steps = [
        ["git", "switch", "-q", "--no-track", "-c", branch, main],
        [uv, "version", "--bump", bump, "-q"],
        [*cliff, main, "--tag", tag, "-o", CHANGELOG],
        ["git", "add", "--", "pyproject.toml", "uv.lock", CHANGELOG],
        ["git", "commit", "-q", "-m", f"chore(release): {tag}\n\n{MERGED_BY}\n"],
    ]
    for argv in steps:
        proc = run_cmd(argv, root, env)
        if proc.returncode != 0:
            print(f"FAIL  {' '.join(argv[:4])}: {said(proc)}")
            print(
                f"      you are on {branch}: fix it, or `git switch {default}` and delete {branch}"
            )
            return 1
    release_ctx = load_context(root)
    state = load_state(release_ctx)
    dod = Dod(release_ctx, state, None, MergeFlags(), title=f"chore(release): {tag}")
    message = f"chore(release): {tag}\n\nBranch: {branch}\nVersion: {version}\n\n{MERGED_BY}\n"
    notes, problem = land_local(ctx, dod, message)
    if problem:
        print(f"FAIL  land: {problem}")
        return 1
    landed = rev(root, f"refs/heads/{default}") or ""
    proc = run_cmd(["git", "tag", "-a", tag, landed, "-m", f"release {tag}"], root, env)
    if proc.returncode != 0:
        print(f"FAIL  git tag {tag}: {said(proc)}")
        return 1
    print(f"release {tag}: {', '.join(notes)}; tagged {tag}")
    if dist == "pypi":
        print(
            "next: uv build, then `op run -- uv publish` (a human, with the PyPI token in "
            "1Password)"
        )
    return 0


# ---------------------------------------------------------------- proof (design C)

# `mise run proof`: the proof bundle of a change (specs/README.md, "Proof"). A human reads the
# trunk diff line by line and skims the leaf against proof: the tests (automatic), a command's
# output before and after, a log excerpt, an HTTP exchange, a screenshot, a video, a terminal
# recording, an attachment. Every capture is one commit on the lane branch under
# proof/<date>-<slug>/, indexed by that folder's README.md, which GitHub renders with its media
# inline. Merge holds the index to validation.md's ## Proof rows (I23), and every file to the
# sha256 its entry records and to the caps (I24); pre-commit holds each commit to the second
# part. Captures run headless: nothing opens a window.
PROOF_DIR = "proof"
PROOF_INDEX = "README.md"
PROOF_KINDS = ("run", "log", "http", "screenshot", "video", "terminal", "attach")
PROOF_ROW_KINDS = (*PROOF_KINDS, "run --before")
PROOF_VISIBLE = ("screenshot", "video", "terminal")  # what a UI change shows best (design C.3)
PROOF_VERB_KIND = {  # the verb names the file, the kind names the case's proof
    "run": "run",
    "log": "log",
    "http": "http",
    "shot": "screenshot",
    "video": "video",
    "tape": "terminal",
    "attach": "attach",
}
PROOF_KIND_VERB = {kind: verb for verb, kind in PROOF_VERB_KIND.items()}
PROOF_KIND_FILES: dict[str, tuple[str, ...] | None] = {  # the types of an entry's files
    "run": ("txt",),
    "run --before": ("txt", "txt"),
    "log": ("txt",),
    "http": ("txt",),
    "screenshot": ("png",),
    "video": ("webm", "gif"),
    "terminal": ("gif", "tape"),
    "attach": None,  # one file of an ATTACH_TYPES type
}
PROOF_SHRINK = {  # what makes a capture smaller, named when one passes a cap
    "screenshot": "--viewport (a smaller page) or --selector (one element)",
    "video": "--seconds (a shorter recording) or --width (a smaller GIF)",
    "terminal": "a smaller Set Width and Set Height, or a shorter tape",
    "attach": "a smaller file",
}
CONFIDENCE_LEVELS = ("high", "medium", "low")
PROOF_ROWS_CAP = 6
PROOF_FILE_CAP = 5 * 1024 * 1024
PROOF_FOLDER_CAP = 15 * 1024 * 1024
PROOF_STREAM_CAP = 4096  # bytes of stdout, stderr, a body or a log excerpt a capture keeps
PROOF_FOLD_LINES = 40  # a longer text capture folds into <details> in README.md
PROOF_PR_TEXT = 3000  # characters of one text capture the pull request body shows
PROOF_TIMEOUT = 120  # seconds for a capture's command, page or tape
PROOF_FRESH = ("specs", "proof", "project_memory")  # edits here leave a capture current
PLAYWRIGHT = "playwright==1.63.0"
SYSTEM_CHROMIUM = "/usr/bin/chromium"
CHROMIUM_ENV = "PROJECT_PROOF_CHROMIUM"  # a Chromium to drive instead of the system's
TERMINAL_TOOLS = ("aqua:charmbracelet/vhs@0.12.1", "aqua:tsl0922/ttyd@1.7.7")
SETUP_WEB = "mise run proof -- setup web"
SETUP_TERMINAL = "mise run proof -- setup terminal"
ATTACH_TYPES = ("png", "jpg", "jpeg", "gif", "svg", "webm", "mp4", "cast", "pdf", "txt", "json")
ATTACH_TYPES += ("csv",)
TEXT_TYPES = ("txt", "json", "csv", "cast", "svg", "tape")
IMAGE_TYPES = ("png", "jpg", "jpeg", "gif", "svg")
MEDIA_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "svg": "image/svg+xml",
    "webm": "video/webm",
    "mp4": "video/mp4",
    "pdf": "application/pdf",
}
MAGIC = {
    "png": (b"\x89PNG\r\n\x1a\n",),
    "gif": (b"GIF87a", b"GIF89a"),
    "webm": (b"\x1a\x45\xdf\xa3",),
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "pdf": (b"%PDF-",),
}
# A repo has a UI when a runtime dependency is a known web or TUI framework (design C.3). An
# HTTP API framework (FastAPI, Starlette) is left out: its proof is http. project-init's probe
# reads the two lists from this file, to name the proof setup (web or terminal) a repo needs.
WEB_UI_FRAMEWORKS = (
    *("django", "flask", "streamlit", "gradio", "dash", "nicegui", "reflex", "panel"),
    *("python-fasthtml", "flet"),
)
TUI_FRAMEWORKS = ("textual", "urwid", "prompt-toolkit", "npyscreen", "asciimatics", "pytermgui")
UI_FRAMEWORKS = (*WEB_UI_FRAMEWORKS, *TUI_FRAMEWORKS)
LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")
PROOF_NOTE = (
    '<!-- The proof of this change (specs/README.md, "Proof"): `mise run proof` writes every '
    "entry and commits it; merge checks each file against the sha256 its entry records. Never "
    "edit it by hand: capture again. -->"
)
TESTS_NOTE = (
    "<!-- `mise run proof -- tests` and merge write this section: each scenario ID of the "
    "branch, its tests, how they failed first (tdd red, or the Red: trailer), the last run, and "
    "prove-red on the old code at merge. -->"
)
PROOF_HEADING_RE = re.compile(r"^### (\S+) · (run --before|[a-z]+) · (.+)$")
PROOF_META_RE = re.compile(
    r"^captured at `([0-9a-f]{7,40})`((?: · `[^`]+` sha256 `[0-9a-f]{64}`)+)$"
)
PROOF_FILE_RE = re.compile(r" · `([^`]+)` sha256 `([0-9a-f]{64})`")
CONFIDENCE_RE = re.compile(r"^- (G\d+) (high|medium|low): (.+)$")
GROUP_ID_RE = re.compile(r"^G(\d+)$")
TAPE_OUTPUT_RE = re.compile(r"^\s*Output\s")
PR_CHECKLIST = (  # templates/pull_request_template.md holds the same items
    "- [ ] `mise run verify` is green.",
    (
        "- [ ] Each behaviour change edits its scenario in `specs/capabilities/`, in the same "
        "commit as its test and code."
    ),
    (
        "- [ ] The `## Trunk` section of `specs/tech-stack.md` is current, and a `flag:` change "
        "has its `[flag-off]` guard."
    ),
    (
        "- [ ] The `## Proof` rows are captured and current (`mise run proof -- show`), and each "
        "group has its confidence line."
    ),
    (
        "- [ ] A surprise is in `project_memory/lessons.md`. A choice later changes must respect "
        "has its file in `project_memory/decisions/`."
    ),
    "- [ ] No secret values: `op://` pointers only.",
)


class ProofError(Exception):
    """A capture that cannot be made as asked; nothing was written."""


@dataclass(frozen=True)
class ProofRow:
    """One row of validation.md's ## Proof table (design C.3)."""

    target: str  # a scenario ID of the change, or G<n> of its plan
    kind: str  # one of PROOF_ROW_KINDS
    shows: str  # what the reviewer sees in it

    def __str__(self) -> str:
        return f"{self.target} | {self.kind} | {self.shows}"


@dataclass
class ProofEntry:
    """One capture in a proof folder's README.md."""

    sid: str  # a scenario ID, or G<n>
    kind: str  # one of PROOF_ROW_KINDS
    caption: str
    at: str  # the commit the capture shows: HEAD when it was made
    files: list[tuple[str, str]]  # (file name in the folder, sha256 hex), in capture order
    line: int = 0  # its heading's line in README.md


@dataclass
class ProofIndex:
    """A proof folder's README.md, read back."""

    name: str  # <date>-<slug>
    tests: list[str] = field(default_factory=list)  # the ## Tests section's lines, as written
    confidence: dict[str, tuple[str, str]] = field(default_factory=dict)  # G<n> -> (level, why)
    entries: list[ProofEntry] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


@dataclass
class ProofBundle:
    """This branch's proof folder: its name, and its index once README.md exists."""

    name: str
    index: ProofIndex | None

    @property
    def folder(self) -> str:
        return f"{PROOF_DIR}/{self.name}"


@dataclass
class ProofTarget:
    """What a capture works on: the branch, its spec state and change, and its proof folder."""

    ctx: Context
    state: State
    change: Change | None
    bundle: ProofBundle


# -- the index: README.md


def file_type(name: str) -> str:
    """A file's type by its last extension: 'txt' for x.before.txt."""
    return PurePosixPath(name).suffix.lstrip(".").lower()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def home_free(text: str) -> str:
    """text with the home folder written as ~: a repo is shared, a home folder is not."""
    homes = {str(Path.home()), os.path.realpath(Path.home())}
    for home in sorted((h for h in homes if h not in ("", "/")), key=len, reverse=True):
        text = text.replace(home, "~")
    return text


def proof_caption(text: str, cap: int = 100) -> str:
    """A caption on one line: home as ~, no backticks, no ' · ' (the heading's separator) and
    no comment opener, cap characters at most."""
    line = " ".join(home_free(text).split()).replace("`", "'").replace(" · ", " - ")
    line = line.replace("<!--", "<!- -")
    return line if len(line) <= cap else line[: cap - 3] + "..."


def fenced(text: str) -> list[str]:
    """text in a fenced block whose fence is longer than any backtick run inside it."""
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    fence = "`" * max(3, longest + 1)
    return [f"{fence}text", *text.splitlines(), fence]


def text_markdown(name: str, read: Callable[[str], bytes | None]) -> list[str]:
    """A text capture as README.md shows it: fenced, folded into <details> when long."""
    text = (read(name) or b"").decode("utf-8", "replace").rstrip("\n")
    count = len(text.splitlines())
    if count > PROOF_FOLD_LINES:
        summary = f"<details><summary>{name} ({count} lines)</summary>"
        return [summary, "", *fenced(text), "", "</details>"]
    return fenced(text)


def media_rank(name: str) -> int:
    """Images first, then links, then text: the order an entry shows its files in."""
    kind = file_type(name)
    return 0 if kind in IMAGE_TYPES else 2 if kind in TEXT_TYPES else 1


def media_markdown(entry: ProofEntry, name: str, read: Callable[[str], bytes | None]) -> list[str]:
    kind = file_type(name)
    alt = entry.caption.replace("[", "(").replace("]", ")")
    if kind in IMAGE_TYPES:
        return [f"![{alt}]({name})"]
    if kind in ("webm", "mp4"):
        preview = entry.kind == "video"
        return [f"[{name}]({name})" + (": the full recording; the GIF is its preview" * preview)]
    if kind == "tape":
        return [f"[{name}]({name}): the tape; `vhs {name}` in this folder renders the GIF again"]
    if kind in TEXT_TYPES:
        return text_markdown(name, read)
    return [f"[{name}]({name})"]


def entry_markdown(entry: ProofEntry, read: Callable[[str], bytes | None]) -> list[str]:
    """One entry of README.md: its heading, the meta line, then its media."""
    meta = f"captured at `{entry.at}`" + "".join(f" · `{n}` sha256 `{h}`" for n, h in entry.files)
    lines = [f"### {entry.sid} · {entry.kind} · {entry.caption}", "", meta, ""]
    names = [name for name, _ in entry.files]
    if entry.kind == "run --before" and len(names) == 2:
        for label, name in (("before, on the merge-base code:", names[0]), ("after:", names[1])):
            lines += [label, "", *text_markdown(name, read), ""]
        return lines
    for name in sorted(names, key=media_rank):
        lines += [*media_markdown(entry, name, read), ""]
    return lines


def by_group(confidence: dict[str, tuple[str, str]]) -> list[tuple[str, str, str]]:
    """(group, level, why) in group order: G1, G2, ... G10."""
    return sorted(((g, *pair) for g, pair in confidence.items()), key=lambda c: int(c[0][1:]))


def confidence_lines(index: ProofIndex) -> list[str]:
    """The confidence lines as merge and the preview print them: low first, marked with !."""
    ordered = by_group(index.confidence)
    ordered.sort(key=lambda c: c[1] != "low")
    return [
        ("! " if level == "low" else "") + f"confidence {group} {level}: {why}"
        for group, level, why in ordered
    ]


def render_index(index: ProofIndex, read: Callable[[str], bytes | None]) -> str:
    """README.md from the index. read gives a file's bytes by name (a text capture shows its
    text), or None."""
    lines = [f"# Proof: {index.name}", "", PROOF_NOTE, ""]
    if index.tests:
        lines += ["## Tests", "", *index.tests, ""]
    if index.confidence:
        lines += ["## Confidence", ""]
        lines += [f"- {group} {level}: {why}" for group, level, why in by_group(index.confidence)]
        lines.append("")
    lines += ["## Entries", ""]
    for entry in index.entries:
        lines += entry_markdown(entry, read)
    return "\n".join(lines).rstrip("\n") + "\n"


def trimmed(lines: list[str]) -> list[str]:
    """lines without the blank lines at either end."""
    start = next((i for i, line in enumerate(lines) if line.strip()), len(lines))
    end = len(lines)
    while end > start and not lines[end - 1].strip():
        end -= 1
    return lines[start:end]


def index_sections(text: str) -> list[tuple[int, int, str]]:
    """(heading line, the line after the section, heading) of each ## section, as markdown
    sees them: a heading inside a fenced capture does not count."""
    heads = [(n, line.strip()) for n, line in prose_lines(text) if line.startswith("## ")]
    end = len(text.splitlines()) + 1
    return [
        (n, heads[i + 1][0] if i + 1 < len(heads) else end, h) for i, (n, h) in enumerate(heads)
    ]


def parse_entries(index: ProofIndex, text: str, start: int, stop: int) -> None:
    raw = text.splitlines()
    entry: ProofEntry | None = None
    for number, line in prose_lines(text):
        if not start < number < stop:
            continue
        written = shown_line(raw, number)
        if line.startswith("### "):
            match = PROOF_HEADING_RE.match(written)
            if match is None or match.group(2) not in PROOF_ROW_KINDS:
                index.problems.append(
                    f"line {number}: an entry heading is '### <id> · <kind> · <caption>'"
                )
                entry = None
                continue
            entry = ProofEntry(match.group(1), match.group(2), match.group(3), "", [], number)
            index.entries.append(entry)
        elif line.startswith("captured at") and entry is not None and not entry.at:
            match = PROOF_META_RE.match(written)
            if match is None:
                index.problems.append(f"line {number}: a meta line is 'captured at `<sha>` · ...'")
                continue
            entry.at = match.group(1)
            entry.files = PROOF_FILE_RE.findall(match.group(2))


def parse_index(text: str, name: str) -> ProofIndex:
    """A proof folder's README.md read back into its index; what does not parse is a problem."""
    index = ProofIndex(name)
    raw = text.splitlines()
    for number, stop, heading in index_sections(text):
        if heading == "## Tests":
            index.tests = trimmed(raw[number : stop - 1])
        elif heading == "## Confidence":
            for line_number, line in prose_lines(text):
                if not number < line_number < stop or not line.strip():
                    continue
                match = CONFIDENCE_RE.match(shown_line(raw, line_number))
                if match and match.group(1) in index.confidence:
                    index.problems.append(
                        f"line {line_number}: a second confidence line for {match.group(1)}: one "
                        "per group; `mise run proof -- confidence` replaces it"
                    )
                elif match:
                    index.confidence[match.group(1)] = (match.group(2), match.group(3))
                else:
                    index.problems.append(
                        f"line {line_number}: a confidence line is '- G<n> high|medium|low: <why>'"
                    )
        elif heading == "## Entries":
            parse_entries(index, text, number, stop)
        else:
            index.problems.append(f"line {number}: unexpected section '{heading}'")
    seen: set[str] = set()
    for entry in index.entries:
        if not entry.at:
            index.problems.append(
                f"line {entry.line}: {entry.sid} {entry.kind} has no 'captured at' line"
            )
        if entry.sid in seen:
            index.problems.append(
                f"line {entry.line}: a second entry for {entry.sid}: one capture per case, in "
                "the kind that fits it; capturing it again replaces them"
            )
        seen.add(entry.sid)
    return index


def with_tests(text: str, tests: list[str]) -> str:
    """README.md with its ## Tests section replaced by tests (or cut, when tests is empty); a new
    section goes above the others. Every other line stays as it is."""
    raw = text.splitlines()
    sections = index_sections(text)
    block = ["## Tests", "", *tests, ""] if tests else []
    own = [s for s in sections if s[2] == "## Tests"]
    if own:
        start, stop = own[0][0] - 1, own[0][1] - 1
    else:
        start = stop = sections[0][0] - 1 if sections else len(raw)
    return "\n".join([*raw[:start], *block, *raw[stop:]]).rstrip("\n") + "\n"


def disk_reader(
    folder: Path, extra: dict[str, bytes] | None = None
) -> Callable[[str], bytes | None]:
    """read() for render_index: extra's bytes first, then the file in folder."""

    def read(name: str) -> bytes | None:
        if extra and name in extra:
            return extra[name]
        try:
            return (folder / name).read_bytes()
        except OSError:
            return None

    return read


# -- files: types, caps, the leak scan


def media_problem(name: str, data: bytes) -> str | None:
    """Why data is not a file of its type (by name), or None when it is one."""
    kind = file_type(name)
    if not data:
        return "is empty"
    if kind in MAGIC:
        return None if data.startswith(MAGIC[kind]) else f"is not a {kind} file (by its bytes)"
    if kind == "mp4":
        return None if data[4:8] == b"ftyp" else "is not an mp4 file (by its bytes)"
    if kind in TEXT_TYPES:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return "is not UTF-8 text"
        return "is not an svg file" if kind == "svg" and "<svg" not in text else None
    return f"has an extension proof does not know (.{kind})"


def megabytes(size: int) -> str:
    return f"{size / (1024 * 1024):.1f} MB"


def cap_problems(kind: str, sizes: dict[str, int], kept: int) -> list[str]:
    """I24 at capture: each new file within PROOF_FILE_CAP, and the folder (kept bytes plus the
    new ones) within PROOF_FOLDER_CAP; each refusal names what shrinks it."""
    shrink = PROOF_SHRINK.get(kind, "a shorter output (--grep, --since)")
    problems = [
        f"{name} is {megabytes(size)}, over the 5 MB cap per file: shrink it with {shrink}"
        for name, size in sizes.items()
        if size > PROOF_FILE_CAP
    ]
    total = kept + sum(sizes.values())
    if total > PROOF_FOLDER_CAP:
        problems.append(
            f"the folder would hold {megabytes(total)}, over the 15 MB cap per change: shrink "
            f"this capture with {shrink}, or keep fewer captures"
        )
    return problems


def leak_scan(root: Path, files: dict[str, bytes]) -> list[str]:
    """gitleaks, with this repo's .gitleaks.toml, over the text files a capture is about to
    write (repo paths -> bytes), in a scratch copy with the same paths: [] when clean, else
    what it found. There is no bypass: without gitleaks a capture is refused, as pre-commit
    would refuse its commit."""
    if not files:
        return []
    env = dict(os.environ)
    if run_tool(["gitleaks", "version"], root, env).returncode != 0:
        return [f"gitleaks is not installed on this machine: {MISE_INSTALL}"]
    with tempfile.TemporaryDirectory(prefix="project-proof-") as tmp:
        for rel, data in files.items():
            path = Path(tmp) / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        argv = ["gitleaks", "dir", tmp, "--no-banner", "--redact", "--verbose"]
        argv += ["--log-level", "error"]
        if (root / ".gitleaks.toml").is_file():
            argv += ["-c", str(root / ".gitleaks.toml")]
        proc = run_tool(argv, root, env)
    if proc.returncode == 0:
        return []
    keep = ("Finding", "RuleID", "File", "Line", "ERR", "FTL")
    said = [
        line.replace(tmp + os.sep, "")
        for line in plain(proc.stdout + proc.stderr).splitlines()
        if any(k in line for k in keep)
    ]
    return [
        "gitleaks found a secret, a personal path or a wiki-link in the capture (rules: "
        ".gitleaks.toml); nothing was written:\n" + "\n".join(said or [plain(tail(proc))])
    ]


def clip_text(text: str, cap: int = PROOF_STREAM_CAP) -> str:
    """text within cap bytes: its head and its tail, and how much was cut between them."""
    data = text.encode("utf-8")
    if len(data) <= cap:
        return text
    half = cap // 2
    head = data[:half].decode("utf-8", "ignore")
    tail_text = data[-half:].decode("utf-8", "ignore")
    return f"{head}\n[... {len(data) - 2 * half} bytes cut ...]\n{tail_text}"


# -- the branch's folder and its state


def proof_name(ctx: Context, change: Change | None) -> str | None:
    """This branch's proof folder, <date>-<slug>: the change folder's name on feat; on the
    other lanes the author date of the branch's first commit (today while it has none) and the
    slug, which a plan/ slug already starts with. None off a lane branch."""
    if ctx.on_default or ctx.lane is None or ctx.lane == "release" or not ctx.slug:
        return None
    if change is not None:
        return change.name
    if DATE_PREFIX_RE.match(ctx.slug):
        return ctx.slug
    dates: list[str] = []
    if ctx.base and ctx.head:
        span = f"{ctx.base}..{ctx.head}"
        dates = git_lines(ctx.root, "log", "--reverse", "--no-merges", "--format=%as", span)
    return f"{dates[0] if dates else today()}-{ctx.slug}"


def load_bundle(ctx: Context, change: Change | None) -> ProofBundle | None:
    name = proof_name(ctx, change)
    if name is None:
        return None
    text = read_text(ctx.root / PROOF_DIR / name / PROOF_INDEX)
    return ProofBundle(name, parse_index(text, name) if text is not None else None)


def stale_since(root: Path, at: str, head: str) -> list[str] | None:
    """The files outside specs/, proof/, project_memory/ and CHANGELOG.md that changed between
    the commit a capture shows and head (design C.4): [] while it is current, None when that
    commit is not in head's history (the branch was rebased, or it is another branch's)."""
    full = rev(root, at)
    if full is None or not is_ancestor(root, full, head):
        return None
    changed = git_lines(root, "diff", "--name-only", "--no-renames", full, head)
    return [p for p in changed if not under(p, list(PROOF_FRESH)) and p != CHANGELOG]


def bundle_evidence(bundle: ProofBundle | None) -> str:
    """The review depth's leaf line ends 'against <this>': the entries, the confidence."""
    index = bundle.index if bundle is not None else None
    if index is None or not (index.entries or index.confidence):
        return ""
    count = len(index.entries)
    text = f"proof: {count} {'entry' if count == 1 else 'entries'}"
    if index.confidence:
        text += ", confidence " + ", ".join(
            f"{g} {lvl}" for g, lvl, _ in by_group(index.confidence)
        )
    return text


def change_ids(state: State, change: Change) -> set[str]:
    """The scenario IDs of a feat change: its groups', and those the branch adds or changes."""
    return {sid for group in change.groups for sid in group.ids} | state.added | state.modified


def branch_ids(state: State, change: Change | None) -> list[str]:
    """The scenario IDs a branch's test proof covers: the change's, and on fix/ and chg/ the
    ones its Spec: trailers name."""
    ctx = state.ctx
    ids = change_ids(state, change) if change is not None else state.added | state.modified
    if ctx.lane in ("fix", "chg") and ctx.base and ctx.head:
        ids |= set(trailer_ids(branch_trailers(ctx.root, ctx.base, ctx.head), "Spec"))
    return sorted(sid for sid in ids if sid in state.scenarios)


def table_cell(text: str) -> str:
    return home_free(" ".join(text.split())).replace("|", "\\|")


def results_line(root: Path, results: Results | str) -> str:
    if isinstance(results, str):
        return "Last run: none (`mise run test` writes one)."
    state = "complete" if results.complete else "partial"
    if results.complete and results_problem(root, results):
        state = "stale"
    try:
        when = datetime.fromisoformat(results.finished).astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        when = "?"
    return f"Last run: {when}, {state}."


def tests_section(state: State, change: Change | None, proof: ProveRed | None) -> list[str]:
    """The ## Tests section: per scenario ID of the branch, its tests, how they failed first
    (the tdd red record, else the Red: trailer), the last run, and prove-red at merge."""
    ctx = state.ctx
    ids = branch_ids(state, change)
    if not ids:
        return []
    results = load_results(ctx.root)
    record = load_tdd_record(tdd_record_path(ctx))
    blocks = branch_trailers(ctx.root, ctx.base, ctx.head) if ctx.base and ctx.head else []
    notes = red_notes(blocks)
    verdicts = {item.sid: item for item in proof.proofs} if proof is not None else {}
    lines = [TESTS_NOTE, "", "| scenario | tests | red first | green | prove-red |"]
    lines.append("|---|---|---|---|---|")
    for sid in ids:
        nodes = results.by_id.get(sid, []) if isinstance(results, Results) else []
        red = record.get(sid, {}).get("red")
        red = red if isinstance(red, dict) else {}
        tests = [node.node for node in nodes] or [str(t) for t in red.get("tests", [])]
        shown = "<br>".join(f"`{table_cell(test)}`" for test in tests) or "none linked"
        reason = str(red.get("reason") or "") or notes.get(sid, "") or "not recorded"
        green = ", ".join(sorted({node.outcome for node in nodes})) or "no result"
        item = verdicts.get(sid)
        verdict = "at merge"
        if item is not None:
            verdict = f"{item.level} {item.kind}" + (f" ({item.how})" if item.how else "")
        cells = [f"`{sid}`", shown, table_cell(reason), green, table_cell(verdict)]
        lines.append("| " + " | ".join(cells) + " |")
    return [*lines, "", results_line(ctx.root, results)]


# -- merge: the proof step, the close commit, the squash body and the pull request


def proof_rows_of(change: Change, text: str, scenarios: dict[str, Scenario]) -> list[ProofRow]:
    """The ## Proof rows of a validation.md text, read the way approve lints them."""
    copy = replace(change, review_ids=[], human_checks=[], proof_rows=[])
    lint_validation(copy, text, scenarios, Report())
    return copy.proof_rows


def fills(entry: ProofEntry, row: ProofRow) -> bool:
    """An entry fills a row of its case and kind; a run --before capture fills a run row."""
    return entry.sid == row.target and (
        entry.kind == row.kind or (row.kind == "run" and entry.kind == "run --before")
    )


def entry_files_problem(root: Path, folder: str, entry: ProofEntry) -> str | None:
    """Why an entry's files are not the kind's files (types, bytes, not empty), or None."""
    names = [name for name, _ in entry.files]
    kinds = tuple(file_type(name) for name in names)
    wanted = PROOF_KIND_FILES.get(entry.kind)
    if wanted is not None and kinds != wanted:
        return f"its files are {', '.join(names) or 'none'}; a {entry.kind} entry holds {wanted}"
    if wanted is None and (len(names) != 1 or kinds[0] not in ATTACH_TYPES):
        return f"its files are {', '.join(names) or 'none'}; an attach entry holds one file"
    for name in names:
        try:
            data = (root / folder / name).read_bytes()
        except OSError:
            return f"{name} is missing"
        if problem := media_problem(name, data):
            return f"{name} {problem}"
    return None


def row_problem(dod: Dod, bundle: ProofBundle, row: ProofRow) -> str | None:
    """I23 for one ## Proof row: its newest capture was made on this branch after approve, is
    current, and holds non-empty files of its kind's type."""
    ctx = dod.ctx
    index = bundle.index or ProofIndex(bundle.name)
    found = [entry for entry in index.entries if fills(entry, row)]
    where = f"{row.target} | {row.kind}"
    if not found:
        verb = PROOF_KIND_VERB.get(row.kind.split()[0], "run")
        before = " --before" if row.kind == "run --before" else ""
        return f"{where}: no capture: mise run proof -- {verb}{before} {row.target} ..."
    entry = found[-1]
    stale = stale_since(ctx.root, entry.at, ctx.head or "HEAD")
    if stale is None:
        return (
            f"{where}: its capture shows {entry.at}, which is not on this branch: capture it again"
        )
    at = rev(ctx.root, entry.at) or entry.at
    if dod.approved_at and not is_ancestor(ctx.root, dod.approved_at, at):
        return f"{where}: its capture was made before approve ({entry.at}): capture it again"
    if stale:
        shown = ", ".join(stale[:3]) + (f" (+{len(stale) - 3} more)" if len(stale) > 3 else "")
        return f"{where}: its capture is stale ({shown} changed since {entry.at}): capture it again"
    if problem := entry_files_problem(ctx.root, bundle.folder, entry):
        return f"{where}: {problem}"
    return None


def folder_problems(root: Path, bundle: ProofBundle) -> list[str]:
    """I24 on the folder: every file is named by an entry and matches the sha256 it records,
    within the 5 MB cap per file and the 15 MB cap per change."""
    index = bundle.index or ProofIndex(bundle.name)
    recorded = {name: digest for entry in index.entries for name, digest in entry.files}
    folder = root / bundle.folder
    problems: list[str] = []
    total = 0
    for path in sorted(folder.iterdir()) if folder.is_dir() else []:
        rel = f"{bundle.folder}/{path.name}"
        if path.is_dir():
            problems.append(f"{rel}/: a proof folder holds files only")
            continue
        if path.name == PROOF_INDEX:
            continue
        data = path.read_bytes()
        total += len(data)
        if path.name not in recorded:
            problems.append(
                f"{rel} is in no entry of README.md: proof files come from `mise run proof`"
            )
        elif sha256_hex(data) != recorded[path.name]:
            problems.append(
                f"I24: {rel} does not match the sha256 its entry records (edited by hand?): "
                "capture it again"
            )
        if len(data) > PROOF_FILE_CAP:
            problems.append(f"I24: {rel} is {megabytes(len(data))}, over the 5 MB cap per file")
    for name in recorded:
        if not (folder / name).is_file():
            problems.append(f"{bundle.folder}/{name}: its entry names it, and it is missing")
    if total > PROOF_FOLDER_CAP:
        problems.append(f"I24: {bundle.folder}/ holds {megabytes(total)}, over the 15 MB cap")
    return problems


def stale_notes(dod: Dod, bundle: ProofBundle, rows: list[ProofRow]) -> list[str]:
    """The preview's marks on the entries no row needs that a later commit made stale: a human
    decides whether they still show the truth (design C.4)."""
    index = bundle.index or ProofIndex(bundle.name)
    newest = {
        id(entry) for row in rows for entry in [e for e in index.entries if fills(e, row)][-1:]
    }
    notes = []
    for entry in index.entries:
        if id(entry) in newest:
            continue
        stale = stale_since(dod.ctx.root, entry.at, dod.ctx.head or "HEAD")
        if stale:
            notes.append(f"stale: {entry.sid} {entry.kind} ({entry.at}; {stale[0]} changed since)")
    return notes


def step_proof(dod: Dod) -> Step:
    """Step 4, after Run it (design C.5): I23, each ## Proof row of validation.md has its
    capture, made on this branch after approve and current since, and each feat group has a
    confidence line (low listed first, marked); I24, every file matches the sha256 its entry
    records, within the caps. It names the folder and the command that renders proof.html."""
    ctx, change, bundle = dod.ctx, dod.change, dod.bundle
    name = "proof"
    if bundle is None:
        return Step(4, name, "ok", "none", sub=1)
    rows: list[ProofRow] = []
    groups: list[Group] = []
    if ctx.lane == "feat" and change is not None:
        text = read_text(ctx.root / change.path / "validation.md") or ""
        rows = proof_rows_of(change, text, dod.state.scenarios)
        groups = change.groups
    index = bundle.index
    if index is None and not rows and not groups:
        return Step(4, name, "ok", "none", sub=1)
    index = index or ProofIndex(bundle.name)
    problems = [f"{bundle.folder}/README.md: {p}" for p in index.problems]
    problems += folder_problems(ctx.root, bundle)
    problems += [p for row in rows if (p := row_problem(dod, bundle, row))]
    problems += [
        f"G{g.number} has no confidence line: mise run proof -- confidence G{g.number} "
        'high|medium|low -- "<why>"'
        for g in groups
        if f"G{g.number}" not in index.confidence
    ]
    details = [*problems, *confidence_lines(index), *stale_notes(dod, bundle, rows)]
    details.append(
        f"folder: {bundle.folder}/ (mise run proof -- show renders .agent/proof/{bundle.name}.html)"
    )
    if problems:
        return Step(4, name, "FAIL", f"{plural(len(problems), 'problem')}", details, sub=1)
    parts = [f"{plural(len(rows), 'row')} captured, current"] if rows else []
    parts.append(f"{plural(len(index.entries), 'capture')}, every file matches its sha256")
    return Step(4, name, "ok", "; ".join(parts), details, sub=1)


def proof_close(dod: Dod) -> tuple[str, str] | None:
    """(path, text) of the proof README.md merge's close commit writes on feat/, chg/ and fix/:
    its ## Tests section as it stands now, the rest as the branch has it. None when the branch
    has no scenario ID, or nothing changes."""
    ctx, bundle = dod.ctx, dod.bundle
    if bundle is None or ctx.lane not in SPEC_LANES_NEED_SPEC:
        return None
    tests = tests_section(dod.state, dod.change, dod.proof)
    if not tests:
        return None
    path = f"{bundle.folder}/{PROOF_INDEX}"
    current = read_text(ctx.root / path)
    base = current if current is not None else render_index(ProofIndex(bundle.name), lambda _: None)
    text = with_tests(base, tests)
    return None if text == current else (path, text)


def proof_close_problem(root: Path, sha: str, path: str, name: str) -> str | None:
    """What is wrong with a close commit's edit of the proof README.md: merge writes its
    ## Tests section and nothing else."""
    before = read_blobs(root, f"{sha}^", [path]).get(path)
    after = read_blobs(root, sha, [path]).get(path, "")
    old = before if before is not None else render_index(ProofIndex(name), lambda _: None)
    if with_tests(old, []) != with_tests(after, []):
        return f"it changes {path} beyond its ## Tests section"
    return None


def proof_record(bundle: ProofBundle | None) -> list[str]:
    """The squash body's Proof block (design C.6): the folder, the captures per kind, the test
    proof, and each confidence line, low first."""
    index = bundle.index if bundle is not None else None
    if bundle is None or index is None:
        return []
    kinds: dict[str, int] = {}
    for entry in index.entries:
        kinds[entry.kind] = kinds.get(entry.kind, 0) + 1
    parts = [", ".join(f"{count} {kind}" for kind, count in sorted(kinds.items()))] if kinds else []
    tested = sum(1 for line in index.tests if line.startswith("| `"))
    if tested:
        parts.append(f"tests for {plural(tested, 'scenario')}")
    head = f"Proof: {bundle.folder}/" + (f" ({'; '.join(parts)})" if parts else "")
    return ["", head, *(f"  {line}" for line in confidence_lines(index))]


def blob_base(url: str) -> str | None:
    """https://<host>/<owner>/<repo> for a remote URL in any of git's network forms (https,
    ssh, git@host:owner/repo); None for a local path or a file:// URL."""
    url = url.strip()
    match = re.match(r"^(?:https?|ssh|git)://(?:[^@/]+@)?([^/:]+)(?::\d+)?/(.+?)(?:\.git)?/?$", url)
    match = match or re.match(r"^(?:[^@/]+@)?([^/:]+):(?!/)(.+?)(?:\.git)?/?$", url)
    if match is None or "/" not in match.group(2):
        return None
    return f"https://{match.group(1)}/{match.group(2)}"


def pr_text(label: str, data: bytes) -> list[str]:
    """A text capture in the pull request body: its label, then a fence, cut to PROOF_PR_TEXT."""
    text = data.decode("utf-8", "replace").rstrip("\n")
    if len(text) > PROOF_PR_TEXT:
        text = text[:PROOF_PR_TEXT] + "\n[... cut here: the full text is in the proof folder]"
    return [label, "", *fenced(text), ""]


def pr_entry_lines(
    entry: ProofEntry, url: Callable[[str], str], read: Callable[[str], bytes | None]
) -> list[str]:
    """One capture as the pull request body shows it: an image or GIF inline (a WebM as a
    link beside its GIF), text in a <details> block."""
    names = [name for name, _ in entry.files]
    title = f"{entry.sid} · {entry.kind} · {entry.caption}"
    if entry.kind == "run --before" and len(names) == 2:
        lines = [f"<details><summary>before and after: {title}</summary>", ""]
        lines += pr_text("before, on the merge-base code:", read(names[0]) or b"")
        lines += pr_text("after:", read(names[1]) or b"")
        return [*lines, "</details>", ""]
    texts = [n for n in names if file_type(n) in TEXT_TYPES and file_type(n) not in IMAGE_TYPES]
    shown = [n for n in names if n not in texts]
    lines = [f"**{title}**", ""] if shown else []
    for name in sorted(shown, key=media_rank):
        alt = entry.caption.replace("[", "(").replace("]", ")")
        if file_type(name) in IMAGE_TYPES:
            lines += [f"![{alt}]({url(name)})", ""]
        else:
            lines += [f"[{name}]({url(name)})", ""]
    for name in texts:
        if file_type(name) == "tape":
            lines += [f"[{name}]({url(name)}): the tape", ""]
            continue
        lines += [f"<details><summary>{title}</summary>", ""]
        lines += [*pr_text(name, read(name) or b""), "</details>", ""]
    return lines


def pr_proof_lines(bundle: ProofBundle | None, root: Path, base: str | None, tip: str) -> list[str]:
    """The ## Proof section of the pull request body (design C.6): the confidence lines, low
    first, then the capture of each case, each image and GIF through its blob
    URL at the pushed tip (a relative path without a known host), then the full index."""
    index = bundle.index if bundle is not None else None
    if bundle is None or index is None:
        return ["Test proof only: no capture on this branch."]

    def url(name: str) -> str:
        path = f"{bundle.folder}/{name}"
        return f"{base}/blob/{tip}/{path}?raw=true" if base else path

    lines = [
        f"- {line.removeprefix('! ')}" + (" (read first)" if line.startswith("!") else "")
        for line in confidence_lines(index)
    ]
    newest: dict[str, ProofEntry] = {}
    for entry in index.entries:  # one per case; after a hand edit, the newest
        newest[entry.sid] = entry
    read = disk_reader(root / bundle.folder)
    for entry in newest.values():
        lines += ["", *pr_entry_lines(entry, url, read)]
    readme = f"{bundle.folder}/{PROOF_INDEX}"
    target = f"{base}/blob/{tip}/{readme}" if base else readme
    return [*lines, "", f"full index: [{readme}]({target})"]


def what_lines(dod: Dod) -> list[str]:
    """The pull request's What: the title, then up to two lines of the change's Why (feat), or
    of the commit notes its subject came from (the fast lanes)."""
    ctx, change = dod.ctx, dod.change
    more: list[str] = []
    if change is not None:
        text = read_text(ctx.root / change.path / "requirements.md") or ""
        more = [line for line in section_text(text, "Why").splitlines() if line.strip()]
    else:
        more = [line for line in title_commit_notes(ctx, dod.title) if line.strip()]
    return [dod.title, *more[:2]]


def scenario_lines(dod: Dod) -> list[str]:
    state = dod.state
    lines = [
        f"- {kind}: {', '.join(f'`{sid}`' for sid in sorted(ids))}"
        for kind, ids in (
            ("added", state.added),
            ("modified", state.modified),
            ("removed", state.removed),
        )
        if ids
    ]
    spec = trailer_ids([t for _, _, t in branch_commits(dod.ctx)], "Spec")
    if spec and dod.ctx.lane in ("fix", "chg"):
        lines.append(f"- in Spec: trailers: {', '.join(f'`{sid}`' for sid in spec)}")
    return lines or ["none: no scenario changed on this branch"]


def pr_body(dod: Dod, record: str, tip: str) -> str:
    """The pull request's body in the shape of design E (templates/pull_request_template.md):
    What, Review depth, Rollback, Proof with each capture shown, Scenarios, Checklist; then the
    squash body, the durable record, folded."""
    ctx = dod.ctx
    base = blob_base((git(ctx.root, "remote", "get-url", "origin") or "").strip())
    rollback = change_rollback(ctx.root, dod.change) if dod.change is not None else None
    lines = ["## What", "", *what_lines(dod), "", "## Review depth", "", "```"]
    lines += [*review_lines(dod), "```", "", "## Rollback", ""]
    lines.append(
        f"`{rollback}`" if rollback else "No change folder: a revert of the squash undoes it."
    )
    lines += ["", "## Proof", "", *pr_proof_lines(dod.bundle, ctx.root, base, tip), ""]
    lines += ["## Scenarios", "", *scenario_lines(dod), "", "## Checklist", "", *PR_CHECKLIST, ""]
    lines += ["<details><summary>The merge record (the squash body)</summary>", ""]
    lines += [*fenced(record.rstrip("\n")), "", "</details>"]
    return "\n".join(lines) + "\n"


# -- pre-commit: I24 and the frozen folders


def staged_proof_name(ctx: Context) -> str | None:
    """proof_name() as the commit sees it: on feat the change folder in the index whose slug is
    the branch's (the newest one not done), never the working tree's copy."""
    change = None
    if ctx.lane == "feat" and ctx.slug:
        listed = z_paths(run_git(ctx.root, "ls-files", "-z", "--", CHANGES_DIR).stdout)
        names = sorted(
            {
                parts[2]
                for parts in (PurePosixPath(p).parts for p in listed)
                if len(parts) > 3
                and (m := CHANGE_DIR_RE.match(parts[2]))
                and m.group(1) == ctx.slug
            }
        )
        texts = read_blobs(ctx.root, "", [f"{CHANGES_DIR}/{n}/requirements.md" for n in names])
        live = [
            n
            for n in names
            if frontmatter(texts.get(f"{CHANGES_DIR}/{n}/requirements.md", ""))[0].get("status")
            != "done"
        ]
        if live or names:
            change = Change((live or names)[-1], f"{CHANGES_DIR}/{(live or names)[-1]}", {})
    return proof_name(ctx, change)


def check_staged_proof(ctx: Context, staged: Staged) -> list[str]:
    """I24 on the proof files this commit adds or changes: each one is named by its folder's
    staged README.md with the sha256 of its staged bytes, within the caps. I5: a branch writes
    only its own proof folder, so one that landed with its change stays frozen."""
    touched = [p for p in staged.paths if under(p, [PROOF_DIR]) and p not in staged.from_merge]
    if not touched:
        return []
    root = ctx.root
    own = staged_proof_name(ctx)
    before = proof_name(ctx, None)  # its folder before a ratchet to feat, which moves it
    problems: list[str] = []
    folders = sorted({"/".join(PurePosixPath(p).parts[:2]) for p in touched})
    for folder in folders:
        name = PurePosixPath(folder).name
        listed = z_paths(run_git(root, "ls-files", "-z", "--", folder).stdout)
        if name == before and name != own and not listed:
            continue  # moved away whole, to the change folder's name
        if own is not None and name != own:
            problems.append(
                f"I5: {folder}/ is not this branch's proof folder ({PROOF_DIR}/{own}/); a proof "
                "folder is written by its own branch only, and frozen once it lands"
            )
            continue
        text = read_blobs(root, "", [f"{folder}/{PROOF_INDEX}"]).get(f"{folder}/{PROOF_INDEX}")
        recorded = {
            n: digest for e in parse_index(text or "", name).entries for n, digest in e.files
        }
        total = 0
        for path in listed:
            data = run_git(root, "cat-file", "blob", f":{path}").stdout
            total += len(data) if PurePosixPath(path).name != PROOF_INDEX else 0
            if path not in staged.content or PurePosixPath(path).name == PROOF_INDEX:
                continue
            file = PurePosixPath(path).name
            if recorded.get(file) != sha256_hex(data):
                problems.append(
                    f"I24: {path} does not match the sha256 its README.md entry records: proof "
                    "files come from `mise run proof`; capture it again instead of editing it"
                )
            if len(data) > PROOF_FILE_CAP:
                problems.append(
                    f"I24: {path} is {megabytes(len(data))}, over the 5 MB cap per file"
                )
        if total > PROOF_FOLDER_CAP:
            problems.append(f"I24: {folder}/ would hold {megabytes(total)}, over the 15 MB cap")
    return problems


# -- the proof command


def proof_target(ctx: Context) -> ProofTarget:
    if not (ctx.root / SPECS).is_dir():
        raise ProofError(f"no {SPECS}/ folder: this repo has no specs yet (run /project-init)")
    state = load_state(ctx)
    change = state.open_change
    bundle = load_bundle(ctx, change)
    if bundle is None:
        where = ctx.branch or "a detached HEAD"
        raise ProofError(
            "proof lives on a lane branch (feat/ chg/ fix/ chore/ refactor/ plan/); "
            f"{where} is none"
        )
    return ProofTarget(ctx, state, change, bundle)


def check_case(target: ProofTarget, sid: str) -> None:
    """The case a capture proves: a scenario ID of the change or a G<n> of its plan (feat); any
    scenario ID on the other lanes."""
    change, ctx = target.change, target.ctx
    if match := GROUP_ID_RE.match(sid):
        if change is None:
            raise ProofError(
                f"{sid}: a group is a feat change's; on {ctx.lane}/ name a scenario ID"
            )
        if int(match.group(1)) not in {group.number for group in change.groups}:
            raise ProofError(f"{sid} is not a group of {change.path}/plan.md")
        return
    if sid not in target.state.scenarios:
        raise ProofError(f"{sid}: no such scenario in {CAPS_DIR}/")
    if change is not None and sid not in change_ids(target.state, change):
        raise ProofError(
            f"{sid} is not an ID of this change ({change.path}/plan.md): name one of its "
            "groups' IDs, or G<n>"
        )


def require_clean(target: ProofTarget, *, code: bool) -> None:
    """A capture records the commit it shows, so the tree matches HEAD (specs/ and
    project_memory/ aside); code=False: only the proof folder must be untouched."""
    dirty = dirty_paths(target.ctx.root)
    if code:
        dirty = [p for p in dirty if not under(p, ["specs", "project_memory"])]
    else:
        dirty = [p for p in dirty if under(p, [target.bundle.folder])]
    if dirty:
        shown = ", ".join(dirty[:5]) + (f" (+{len(dirty) - 5} more)" if len(dirty) > 5 else "")
        raise ProofError(
            f"commit first: a capture records the commit it shows (HEAD), and these files "
            f"differ from it: {shown}"
        )


def proof_stem(target: ProofTarget, sid: str, verb: str, caption: str) -> str:
    """<id>-<verb>-<slug>, with -2, -3 ... when another case's file has that name already (the
    case's own files are replaced, so their names are free)."""
    slug = slugify(caption)[:48].strip("-") or verb
    stem = f"{sid}-{verb}-{slug}"
    folder = target.ctx.root / target.bundle.folder
    index = target.bundle.index or ProofIndex(target.bundle.name)
    own = {name for entry in index.entries if entry.sid == sid for name, _ in entry.files}
    names = (
        [p.name.removesuffix(".before.txt") for p in folder.iterdir() if p.name not in own]
        if folder.is_dir()
        else []
    )
    taken = {name.rsplit(".", 1)[0] if "." in name else name for name in names}
    count = 1
    found = stem
    while found in taken:
        count += 1
        found = f"{stem}-{count}"
    return found


def folder_size(target: ProofTarget) -> int:
    folder = target.ctx.root / target.bundle.folder
    if not folder.is_dir():
        return 0
    return sum(p.stat().st_size for p in folder.iterdir() if p.is_file() and p.name != PROOF_INDEX)


def commit_proof(
    target: ProofTarget, message: str, writes: dict[str, bytes], removes: tuple[str, ...] = ()
) -> None:
    """Write the capture's files and README.md, remove the files of the entry it replaces, and
    commit only the proof folder, through the normal hooks. A refused commit undoes it all."""
    ctx, bundle = target.ctx, target.bundle
    folder = ctx.root / bundle.folder
    before = {
        name: (folder / name).read_bytes() if (folder / name).is_file() else None
        for name in [*writes, *removes]
    }
    folder.mkdir(parents=True, exist_ok=True)
    for name, data in writes.items():
        (folder / name).write_bytes(data)
    for name in removes:
        (folder / name).unlink(missing_ok=True)
    env = lifecycle_env()
    proc = git_run(ctx.root, env, "add", "--", bundle.folder)
    if proc.returncode == 0:
        proc = git_run(ctx.root, env, "commit", "-q", "-m", message, "--", bundle.folder)
    if proc.returncode == 0:
        return
    git_run(ctx.root, env, "reset", "-q", "--", bundle.folder)
    for name, data in before.items():
        if data is None:
            (folder / name).unlink(missing_ok=True)
        else:
            (folder / name).write_bytes(data)
    if folder.is_dir() and not any(folder.iterdir()):
        folder.rmdir()
    raise ProofError(f"the proof commit was refused, and nothing is kept:\n{said(proc, 20)}")


def save_index(
    target: ProofTarget,
    index: ProofIndex,
    files: dict[str, bytes],
    message: str,
    removes: tuple[str, ...] = (),
) -> str:
    """Leak-scan and commit README.md written from index, with the new files and without the
    removed ones: the sha of the commit."""
    folder = target.ctx.root / target.bundle.folder
    readme = render_index(index, disk_reader(folder, files)).encode("utf-8")
    texts = {name: data for name, data in files.items() if file_type(name) in TEXT_TYPES}
    rel = target.bundle.folder
    scanned = {f"{rel}/{name}": data for name, data in {**texts, PROOF_INDEX: readme}.items()}
    if problems := leak_scan(target.ctx.root, scanned):
        raise ProofError(problems[0])
    commit_proof(target, message, {**files, PROOF_INDEX: readme}, removes)
    return rev(target.ctx.root, "HEAD") or ""


def save_capture(
    target: ProofTarget, sid: str, kind: str, caption: str, files: dict[str, bytes]
) -> int:
    """One capture: its files (name -> bytes; text written with ~ for home), its entry in
    README.md, the caps and the leak scan, then the commit `docs(proof): <id> <kind>`. A case
    holds one entry (design C.3): one it had already is replaced, its files removed in the same
    commit."""
    ctx, bundle = target.ctx, target.bundle
    kept = {
        name: home_free(data.decode("utf-8", "replace")).encode("utf-8")
        if file_type(name) in TEXT_TYPES
        else data
        for name, data in files.items()
    }
    index = bundle.index or ProofIndex(bundle.name)
    old = [entry for entry in index.entries if entry.sid == sid]
    removes = tuple(name for entry in old for name, _ in entry.files if name not in kept)
    folder = ctx.root / bundle.folder
    freed = sum((folder / name).stat().st_size for name in removes if (folder / name).is_file())
    if problems := cap_problems(
        kind, {name: len(data) for name, data in kept.items()}, folder_size(target) - freed
    ):
        raise ProofError("; ".join(problems))
    head = (ctx.head or "")[:10]
    entry = ProofEntry(
        sid, kind, proof_caption(caption), head, [(n, sha256_hex(d)) for n, d in kept.items()]
    )
    entries = [*(e for e in index.entries if e.sid != sid), entry]
    index = replace(index, entries=entries, problems=[])
    sha = save_index(target, index, kept, f"docs(proof): {sid} {kind}", removes)
    for gone in old:
        print(f"proof: replaced {gone.kind} captured at {gone.at}")
    for name, data in kept.items():
        size = megabytes(len(data)) if len(data) >= 1024 * 1024 else f"{len(data) / 1024:.1f} KB"
        print(f"proof: {bundle.folder}/{name} ({size})")
    print(f"proof: {sid} {kind} captured at {head}; committed {sha[:10]} docs(proof): {sid} {kind}")
    return 0


def run_text(argv: list[str], cwd: Path, env: dict[str, str], timeout: int) -> str:
    """A command's run as a text capture: the command, its exit code and time, then stdout and
    stderr, each cut to PROOF_STREAM_CAP (head and tail)."""
    started = time.monotonic()
    proc = run_cmd(argv, cwd, env, timeout=timeout)
    seconds = time.monotonic() - started
    if proc.returncode == 127 and proc.stderr.startswith("cannot run"):
        raise ProofError(proc.stderr.strip())
    if proc.returncode == 124 and "timed out" in proc.stderr:
        raise ProofError(f"`{shlex.join(argv)}` ran past {timeout} s: pass --timeout <seconds>")
    lines = [f"$ {shlex.join(argv)}", f"exit {proc.returncode} in {seconds:.1f} s"]
    for stream, text in (("stdout", proc.stdout), ("stderr", proc.stderr)):
        lines.append(f"--- {stream}" + ("" if text else " (empty)"))
        if text:
            lines.append(clip_text(text).rstrip("\n"))
    return "\n".join(lines) + "\n"


def synced(tree: Path, uv: str | None, env: dict[str, str]) -> None:
    """The tree's environment synced quietly, so a `uv run` in the command prints no install."""
    if uv is not None and (tree / "uv.lock").is_file():
        run_cmd([uv, "sync", "--locked", "--quiet"], tree, env, timeout=PYTEST_TIMEOUT)


def run_before(ctx: Context, argv: list[str], timeout: int) -> str:
    """argv on the merge-base's code: a throwaway worktree of HEAD whose source roots are
    swapped for their state at the merge-base (the tests inside them stay HEAD's), as prove-red
    builds it, synced, then removed. Its path reads as the repo's in the text."""
    if not ctx.base or not ctx.head or ctx.base == ctx.head:
        raise ProofError("--before needs commits past the merge-base: there is no old code to run")
    src, tests = committed_paths(ctx.root, (ctx.head, ctx.base))
    uv = uv_binary(ctx.root)
    trees = Worktrees(ctx.root)
    try:
        env = tool_env(trusted=trees.tmp)
        tree = trees.add("before", ctx.head)
        checkout_old(tree, ctx.base, old_roots(ctx.root, ctx.base, ctx.head, src))
        checkout_old(tree, ctx.head, tests_in_src(ctx.root, ctx.base, ctx.head, src, tests))
        if uv is not None and (tree / "uv.lock").is_file():
            sync_tree(tree, uv, env, trees.groups)
        text = run_text(argv, tree, env, timeout)
    except ProveRedError as exc:
        raise ProofError(f"--before: {exc}") from exc
    finally:
        trees.close()
    for path in {str(tree.resolve()), str(tree)}:
        text = text.replace(path, str(ctx.root))
    return text


def proof_run(target: ProofTarget, args: argparse.Namespace) -> int:
    argv = list(args.command)
    if argv and argv[0] == "--":  # argparse keeps it on some Python versions
        argv = argv[1:]
    if not argv:
        raise UsageError("proof run needs the command after --: proof run <id> -- <cmd...>")
    ctx = target.ctx
    caption = args.caption or shlex.join(argv)
    stem = proof_stem(target, args.id, "run", caption)
    files: dict[str, bytes] = {}
    if args.before:
        files[f"{stem}.before.txt"] = run_before(ctx, argv, args.timeout).encode("utf-8")
    env = tool_env()
    synced(ctx.root, uv_binary(ctx.root), env)
    files[f"{stem}.txt"] = run_text(argv, ctx.root, env, args.timeout).encode("utf-8")
    kind = "run --before" if args.before else "run"
    return save_capture(target, args.id, kind, caption, files)


def log_text(path: Path, shown: str, grep: str | None, since: str | None) -> str:
    """An excerpt of a log: the lines from the last one holding since, those matching grep,
    cut to PROOF_STREAM_CAP."""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        raise ProofError(f"{shown}: cannot read it ({exc.strerror or exc})") from exc
    if since is not None:
        marks = [number for number, line in enumerate(lines) if since in line]
        if not marks:
            raise ProofError(f"{shown}: no line holds '{since}'")
        lines = lines[marks[-1] :]
    if grep is not None:
        try:
            pattern = re.compile(grep)
        except re.error as exc:
            raise UsageError(f"--grep: {exc}") from exc
        lines = [line for line in lines if pattern.search(line)]
    if not lines:
        raise ProofError(f"{shown}: nothing matched, so the excerpt would be empty")
    head = f"$ log {shown}"
    head += f" --since {shlex.quote(since)}" if since is not None else ""
    head += f" --grep {shlex.quote(grep)}" if grep is not None else ""
    body = clip_text("\n".join(lines) + "\n").rstrip("\n")
    return f"{head}\n{plural(len(lines), 'line')}\n{body}\n"


def proof_log(target: ProofTarget, args: argparse.Namespace) -> int:
    path = Path(args.file)
    full = path if path.is_absolute() else target.ctx.root / path
    text = log_text(full, args.file, args.grep, args.since)
    caption = args.caption or " ".join([args.file, *(["--grep", args.grep] if args.grep else [])])
    stem = proof_stem(target, args.id, "log", caption)
    return save_capture(target, args.id, "log", caption, {f"{stem}.txt": text.encode("utf-8")})


def http_text(method: str, url: str, data: str | None, headers: list[str]) -> str:
    """One request to a local server and its answer: the request, the status, the headers and
    the body's head. Anything but localhost, 127.0.0.1 or ::1 is refused."""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https") or parts.hostname not in LOCAL_HOSTS:
        raise ProofError(
            "http captures a local server only (localhost, 127.0.0.1, ::1), not "
            f"{parts.hostname or url}"
        )
    sent: dict[str, str] = {}
    body = None
    if data is not None:
        try:
            json.loads(data)
        except ValueError as exc:
            raise UsageError(f"--data is not JSON: {exc}") from exc
        body = data.encode("utf-8")
        sent["Content-Type"] = "application/json"
    for header in headers:
        key, sep, value = header.partition(":")
        if not sep or not key.strip():
            raise UsageError(f"--header is 'Name: value', not '{header}'")
        sent[key.strip()] = value.strip()
    method = method.upper()
    request = urllib.request.Request(url, data=body, method=method, headers=sent)  # noqa: S310
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=30) as response:
            status, reason = response.status, response.reason
            got, content = list(response.headers.items()), response.read(PROOF_STREAM_CAP * 4)
    except urllib.error.HTTPError as exc:
        status, reason, got, content = exc.code, exc.reason, list(exc.headers.items()), exc.read()
    except (urllib.error.URLError, OSError) as exc:
        why = getattr(exc, "reason", exc)
        raise ProofError(f"cannot reach {url} ({why}): start the server first") from exc
    lines = [f"> {method.upper()} {url}", *(f"> {k}: {v}" for k, v in sent.items())]
    if data is not None:
        lines += [">", *data.splitlines()]
    lines += ["", f"< {status} {reason}", *(f"< {k}: {v}" for k, v in got), ""]
    lines.append(clip_text(content.decode("utf-8", "replace")).rstrip("\n"))
    return "\n".join(lines) + "\n"


def proof_http(target: ProofTarget, args: argparse.Namespace) -> int:
    text = http_text(args.method, args.url, args.data, args.header or [])
    caption = args.caption or f"{args.method.upper()} {args.url}"
    stem = proof_stem(target, args.id, "http", caption)
    return save_capture(target, args.id, "http", caption, {f"{stem}.txt": text.encode("utf-8")})


# The headless browser behind shot and video: Chromium driven by Playwright, run through
# `uv run --with playwright`, so the repo's own environment never needs it. It never opens a
# window. Exit 3 says a browser part is missing, which `mise run proof -- setup web` installs.
BROWSER_SCRIPT = '''"""Written by scripts/project.py proof for one capture: headless Chromium."""
import importlib.util
import json
import sys
import time

from playwright.sync_api import Error, sync_playwright

job = json.loads(sys.argv[1])
MISSING = 3


def steps_of(path):
    spec = importlib.util.spec_from_file_location("proof_steps", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.steps


def missing(exc):
    print("missing: " + str(exc).splitlines()[0], file=sys.stderr)
    sys.exit(MISSING)


with sync_playwright() as p:
    try:
        browser = p.chromium.launch(headless=True, executable_path=job["executable"] or None)
    except Error as exc:
        missing(exc)
    width, height = job["viewport"]
    options = {
        "viewport": {"width": width, "height": height},
        "color_scheme": "dark" if job["dark"] else "light",
    }
    if job["mode"] == "video":
        options["record_video_dir"] = job["dir"]
        options["record_video_size"] = {"width": width, "height": height}
    context = browser.new_context(**options)
    try:
        page = context.new_page()
    except Error as exc:
        missing(exc)
    page.set_default_timeout(job["timeout_ms"])
    started = time.monotonic()
    page.goto(job["url"], wait_until="load")
    result = {}
    if job["mode"] == "shot":
        if job["selector"]:
            page.locator(job["selector"]).screenshot(path=job["out"])
        else:
            page.screenshot(path=job["out"], full_page=True)
    else:
        steps_of(job["steps"])(page)
        page.wait_for_timeout(500)
        video = page.video
    context.close()
    if job["mode"] == "video":
        result["out"] = video.path()
        result["seconds"] = time.monotonic() - started
    browser.close()
print(json.dumps(result))
'''


def chromium() -> str:
    """The Chromium to drive: PROJECT_PROOF_CHROMIUM, else the system's, else "" (Playwright's
    own, which `setup web` installs)."""
    chosen = os.environ.get(CHROMIUM_ENV, "")
    if chosen:
        if not Path(chosen).is_file():
            raise ProofError(f"{CHROMIUM_ENV}={chosen} is no file: run `{SETUP_WEB}`, or fix it")
        return chosen
    return SYSTEM_CHROMIUM if Path(SYSTEM_CHROMIUM).is_file() else ""


def run_browser(root: Path, job: dict[str, object], timeout: int) -> dict[str, object]:
    """BROWSER_SCRIPT for one job; what it printed last, as JSON."""
    uv = uv_binary(root)
    if uv is None:
        raise ProofError(f"uv is not on PATH: run mise install, then `{SETUP_WEB}`")
    job = {**job, "executable": chromium()}
    argv = [uv, "run", "--no-project", "--quiet", "--with", PLAYWRIGHT, "python", "-c"]
    proc = run_cmd([*argv, BROWSER_SCRIPT, json.dumps(job)], root, tool_env(), timeout=timeout)
    if proc.returncode == 3:
        raise ProofError(f"the headless browser lacks a part ({said(proc, 2)}): run `{SETUP_WEB}`")
    if proc.returncode != 0:
        raise ProofError(
            f"the headless browser failed ({said(proc, 4)}); if Playwright or Chromium is "
            f"missing: `{SETUP_WEB}`"
        )
    try:
        found = json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        found = None
    if not isinstance(found, dict):
        raise ProofError(f"the headless browser said nothing to read: {said(proc, 4)}")
    return found


def viewport(text: str) -> list[int]:
    match = re.fullmatch(r"(\d{2,5})x(\d{2,5})", text)
    if match is None:
        raise UsageError(f"--viewport is <width>x<height>, e.g. 1280x800, not '{text}'")
    return [int(match.group(1)), int(match.group(2))]


def proof_shot(target: ProofTarget, args: argparse.Namespace) -> int:
    size = viewport(args.viewport)
    with tempfile.TemporaryDirectory(prefix="project-proof-") as tmp:
        out = Path(tmp) / "shot.png"
        job = {"mode": "shot", "url": args.url, "out": str(out), "viewport": size}
        job |= {"dark": args.dark, "selector": args.selector, "timeout_ms": PROOF_TIMEOUT * 1000}
        run_browser(target.ctx.root, job, PROOF_TIMEOUT + 60)
        data = out.read_bytes() if out.is_file() else b""
    if problem := media_problem("shot.png", data):
        raise ProofError(f"the screenshot {problem}")
    caption = args.caption or args.url
    stem = proof_stem(target, args.id, "shot", caption)
    return save_capture(target, args.id, "screenshot", caption, {f"{stem}.png": data})


def gif_preview(video: Path, gif: Path, seconds: int, width: int) -> None:
    """ffmpeg: the first seconds of a recording as a GIF width pixels wide, for inline view."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise ProofError(
            f"ffmpeg makes the GIF preview and is not on PATH: install it, then `{SETUP_WEB}`"
        )
    scale = (
        f"fps=10,scale={width}:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"
    )
    argv = [ffmpeg, "-loglevel", "error", "-y", "-i", str(video), "-t", str(seconds)]
    proc = run_cmd([*argv, "-vf", scale, str(gif)], video.parent, tool_env(), timeout=PROOF_TIMEOUT)
    if proc.returncode != 0 or not gif.is_file():
        raise ProofError(f"ffmpeg could not make the GIF preview: {said(proc, 4)}")


def proof_video(target: ProofTarget, args: argparse.Namespace) -> int:
    steps = Path(args.steps).resolve()
    if not steps.is_file():
        raise ProofError(f"--steps {args.steps}: no such file (a .py file with steps(page))")
    if shutil.which("ffmpeg") is None:
        raise ProofError(
            f"ffmpeg makes the GIF preview and is not on PATH: install it, then `{SETUP_WEB}`"
        )
    size = viewport(args.viewport)
    with tempfile.TemporaryDirectory(prefix="project-proof-") as tmp:
        job = {"mode": "video", "url": args.url, "dir": tmp, "viewport": size, "dark": args.dark}
        job |= {"steps": str(steps), "timeout_ms": args.seconds * 1000}
        found = run_browser(target.ctx.root, job, PROOF_TIMEOUT + args.seconds + 60)
        video = Path(str(found.get("out", "")))
        if float(str(found.get("seconds", 0))) > args.seconds:
            raise ProofError(f"the steps ran past --seconds {args.seconds}: pass a larger one")
        if not video.is_file():
            raise ProofError("the headless browser wrote no recording")
        gif = Path(tmp) / "preview.gif"
        gif_preview(video, gif, args.seconds, args.width)
        caption = args.caption or args.url
        stem = proof_stem(target, args.id, "video", caption)
        files = {f"{stem}.webm": video.read_bytes(), f"{stem}.gif": gif.read_bytes()}
    return save_capture(target, args.id, "video", caption, files)


def terminal_tools(root: Path) -> tuple[str, str]:
    """The vhs and ttyd a tape renders with. One missing from PATH, or one that does not run,
    refuses with the setup command: a mise shim outside a repo that pins the tool is on PATH,
    and it only prints mise's own advice (`mise use -g ...`)."""
    found: list[str] = []
    for tool in ("vhs", "ttyd"):
        path = shutil.which(tool)
        if path is None:
            raise ProofError(f"vhs and ttyd render terminal recordings: run `{SETUP_TERMINAL}`")
        proc = run_cmd([path, "--version"], root, tool_env(), timeout=60)
        if proc.returncode != 0:
            raise ProofError(f"{tool} does not run here ({said(proc, 1)}): run `{SETUP_TERMINAL}`")
        found.append(path)
    return found[0], found[1]


def proof_tape(target: ProofTarget, args: argparse.Namespace) -> int:
    tape = Path(args.file)
    try:
        text = tape.read_text(encoding="utf-8")
    except OSError as exc:
        raise ProofError(f"{args.file}: cannot read it ({exc.strerror or exc})") from exc
    vhs, _ = terminal_tools(target.ctx.root)
    body = [line for line in text.splitlines() if not TAPE_OUTPUT_RE.match(line)]
    caption = args.caption or tape.name
    stem = proof_stem(target, args.id, "tape", caption)
    with tempfile.TemporaryDirectory(prefix="project-proof-") as tmp:
        gif = Path(tmp) / "tape.gif"
        script = Path(tmp) / "capture.tape"
        script.write_text("\n".join([f'Output "{gif}"', *body]) + "\n", encoding="utf-8")
        proc = run_cmd([vhs, str(script)], target.ctx.root, tool_env(), timeout=PROOF_TIMEOUT * 2)
        if proc.returncode != 0 or not gif.is_file():
            raise ProofError(f"vhs could not render {args.file}: {said(proc, 4)}")
        data = gif.read_bytes()
    kept = "\n".join([f"Output {stem}.gif", *body]) + "\n"
    files = {f"{stem}.gif": data, f"{stem}.tape": kept.encode("utf-8")}
    return save_capture(target, args.id, "terminal", caption, files)


def proof_attach(target: ProofTarget, args: argparse.Namespace) -> int:
    path = Path(args.file)
    kind = file_type(path.name)
    if kind not in ATTACH_TYPES:
        raise ProofError(f"attach takes {', '.join(ATTACH_TYPES)} files, not .{kind or '?'}")
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ProofError(f"{args.file}: cannot read it ({exc.strerror or exc})") from exc
    if problem := media_problem(path.name, data):
        raise ProofError(f"{args.file} {problem}")
    stem = proof_stem(target, args.id, "attach", args.caption)
    return save_capture(target, args.id, "attach", args.caption, {f"{stem}.{kind}": data})


def proof_confidence(target: ProofTarget, args: argparse.Namespace) -> int:
    """One line per group, `- G<n> <level>: <why>`, replaced when given again; validate writes
    it with a one-line reason."""
    change = target.change
    group, level = args.group, args.level
    why = proof_caption(" ".join(args.why), cap=300)
    if change is None:
        raise ProofError("confidence is per group of a feat change's plan; this branch has none")
    if not GROUP_ID_RE.match(group) or int(group[1:]) not in {g.number for g in change.groups}:
        raise ProofError(f"{group} is not a group of {change.path}/plan.md")
    if level not in CONFIDENCE_LEVELS:
        raise ProofError(f"a confidence level is high, medium or low, not '{level}'")
    if not why:
        raise UsageError('proof confidence needs the why: confidence G1 high -- "<why>"')
    require_clean(target, code=False)
    index = target.bundle.index or ProofIndex(target.bundle.name)
    index = replace(index, confidence={**index.confidence, group: (level, why)}, problems=[])
    sha = save_index(target, index, {}, f"docs(proof): {group} confidence")
    print(f"proof: {group} {level}: {why}; committed {sha[:10]} docs(proof): {group} confidence")
    return 0


def proof_tests(target: ProofTarget) -> int:
    """The ## Tests section, regenerated now; merge writes it once more in its close commit."""
    ctx, bundle = target.ctx, target.bundle
    tests = tests_section(target.state, target.change, None)
    if not tests:
        print("proof tests: this branch has no scenario ID yet; nothing to write")
        return 0
    require_clean(target, code=False)
    path = ctx.root / bundle.folder / PROOF_INDEX
    current = read_text(path)
    base = current if current is not None else render_index(ProofIndex(bundle.name), lambda _: None)
    text = with_tests(base, tests)
    if text == current:
        print(f"proof tests: {bundle.folder}/README.md is unchanged")
        return 0
    scanned = {f"{bundle.folder}/{PROOF_INDEX}": text.encode("utf-8")}
    if problems := leak_scan(ctx.root, scanned):
        raise ProofError(problems[0])
    commit_proof(target, "docs(proof): tests", {PROOF_INDEX: text.encode("utf-8")})
    count = sum(1 for line in tests if line.startswith("| `"))
    print(f"proof tests: {plural(count, 'scenario')} in {bundle.folder}/README.md; committed")
    return 0


def html_pre(data: bytes) -> str:
    return f"<pre>{html.escape(data.decode('utf-8', 'replace'))}</pre>"


def html_media(entry: ProofEntry, name: str, read: Callable[[str], bytes | None]) -> str:
    data = read(name) or b""
    kind = file_type(name)
    alt = html.escape(entry.caption, quote=True)
    if kind in MEDIA_TYPES and kind not in ("pdf",):
        src = f"data:{MEDIA_TYPES[kind]};base64,{base64.b64encode(data).decode()}"
        if kind in IMAGE_TYPES:
            return f'<img alt="{alt}" src="{src}">'
        return f'<video controls src="{src}"></video>'
    if kind in TEXT_TYPES:
        return html_pre(data)
    return f"<p>{html.escape(name)} ({megabytes(len(data))}): open it from the proof folder</p>"


PROOF_CSS = """
:root { --bg: #f7f5f0; --fg: #26231f; --muted: #6b645a; --line: #d9d3c7; --low: #b3261e; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #1f1d1a; --fg: #e8e2d6; --muted: #a39b8c; --line: #3a3630; --low: #f2b8b5; }
}
body { background: var(--bg); color: var(--fg); font: 15px/1.5 system-ui, sans-serif;
  margin: 0 auto; max-width: 1100px; padding: 16px; }
pre { background: rgba(127,127,127,.12); padding: 8px; overflow-x: auto; white-space: pre-wrap; }
img, video { max-width: 100%; border: 1px solid var(--line); }
.meta { color: var(--muted); font-size: 13px; }
.low { color: var(--low); font-weight: 600; }
.pair { display: grid; gap: 8px; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }
table { border-collapse: collapse; } td, th { border: 1px solid var(--line); padding: 4px 8px; }
article { border-top: 1px solid var(--line); padding: 8px 0; }
"""


def html_cell(text: str) -> str:
    """A markdown table cell as HTML: `code` spans and <br> kept, the rest escaped."""
    shown = html.escape(text).replace("&lt;br&gt;", "<br>")
    return re.sub(r"`([^`]*)`", r"<code>\1</code>", shown)


def html_table(lines: list[str]) -> str:
    """The ## Tests section's markdown table (and its last line) as HTML."""
    rows = [line for line in lines if line.startswith("|") and not set(line) <= set("|-: ")]
    cells = [
        [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", row.strip().strip("|"))]
        for row in rows
    ]
    out = ["<table>"]
    for number, row in enumerate(cells):
        tag = "th" if number == 0 else "td"
        items = "".join(f"<{tag}>{html_cell(c)}</{tag}>" for c in row)
        out.append(f"<tr>{items}</tr>")
    out.append("</table>")
    rest = [line for line in lines if line.strip() and not line.startswith(("|", "<!--"))]
    return "\n".join([*out, *(f"<p>{html.escape(line)}</p>" for line in rest)])


def proof_html(target: ProofTarget, depth: list[str]) -> str:
    """proof.html (design C.7): the review depth, the confidence lines (low first), the test
    proof, then every entry grouped by its case: images inline, videos in <video controls>,
    text in panes, before and after side by side. Everything is inline, so it opens offline
    and asks nothing from the network."""
    ctx, bundle = target.ctx, target.bundle
    index = bundle.index or ProofIndex(bundle.name)
    read = disk_reader(ctx.root / bundle.folder)
    title = html.escape(f"Proof: {bundle.name}")
    parts = [f"<h1>{title}</h1>", f"<pre>{html.escape(chr(10).join(depth))}</pre>"]
    if index.confidence:
        items = "".join(
            f'<li class="{"low" if line.startswith("!") else ""}">{html.escape(line)}</li>'
            for line in confidence_lines(index)
        )
        parts.append(f"<h2>Confidence</h2><ul>{items}</ul>")
    if index.tests:
        parts.append(f"<h2>Tests</h2>{html_table(index.tests)}")
    cases: dict[str, list[ProofEntry]] = {}
    for entry in index.entries:
        cases.setdefault(entry.sid, []).append(entry)
    for sid, entries in cases.items():
        parts.append(f"<h2>{html.escape(sid)}</h2>")
        for entry in entries:
            stale = stale_since(ctx.root, entry.at, ctx.head or "HEAD")
            mark = " · stale" if stale else " · not on this branch" if stale is None else ""
            meta = f"captured at {entry.at}{mark}"
            head = f"<h3>{html.escape(entry.kind)} · {html.escape(entry.caption)}</h3>"
            names = [name for name, _ in entry.files]
            if entry.kind == "run --before" and len(names) == 2:
                panes = "".join(
                    f"<div><p class='meta'>{label}</p>{html_pre(read(n) or b'')}</div>"
                    for label, n in (
                        ("before, on the merge-base code", names[0]),
                        ("after", names[1]),
                    )
                )
                body = f'<div class="pair">{panes}</div>'
            else:
                body = "".join(html_media(entry, n, read) for n in sorted(names, key=media_rank))
            parts.append(f'<article>{head}<p class="meta">{html.escape(meta)}</p>{body}</article>')
    return (
        f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><title>{title}</title>'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<style>{PROOF_CSS}</style></head><body>\n" + "\n".join(parts) + "\n</body></html>\n"
    )


def proof_show(target: ProofTarget) -> int:
    """.agent/proof/<name>.html from the folder's README.md; the path, and no browser."""
    ctx, bundle = target.ctx, target.bundle
    if bundle.index is None:
        raise ProofError(f"{bundle.folder}/README.md does not exist yet: capture something first")
    depth = depth_lines(review_depth(ctx), bundle_evidence(bundle))
    out = ctx.root / ".agent" / "proof" / f"{bundle.name}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        proof_html(target, [f"review depth  {depth[0]}", f"              {depth[1]}"]),
        encoding="utf-8",
    )
    print(
        f"proof show: {out.relative_to(ctx.root).as_posix()} (open it yourself; nothing was opened)"
    )
    return 0


def proof_setup(ctx: Context, what: str) -> int:
    """setup web: what Playwright needs for a headless Chromium (its ffmpeg, and its own
    Chromium when the system has none). setup terminal: vhs and ttyd, pinned in mise.toml."""
    if what == "web":
        uv = uv_binary(ctx.root)
        if uv is None:
            print("FAIL  proof setup web: uv is not on PATH: run mise install")
            return 1
        parts = ["ffmpeg"] if chromium() else ["chromium", "ffmpeg"]
        argv = [uv, "run", "--no-project", "--quiet", "--with", PLAYWRIGHT, "playwright", "install"]
        proc = run_cmd([*argv, *parts], ctx.root, tool_env(), timeout=1800)
        if proc.returncode != 0:
            print(f"FAIL  proof setup web: playwright install {' '.join(parts)}:\n{said(proc, 8)}")
            return 1
        where = chromium() or "Playwright's own Chromium"
        print(
            f"ok    proof setup web: headless Chromium ({where}) for shot and video; no window "
            "opens"
        )
        if shutil.which("ffmpeg") is None:
            print("warn  ffmpeg is not on PATH: video needs it for the GIF preview; install it")
        return 0
    mise = shutil.which("mise")
    if mise is None:
        print("FAIL  proof setup terminal: mise is not on PATH")
        return 1
    proc = run_cmd([mise, "use", *TERMINAL_TOOLS], ctx.root, lifecycle_env(), timeout=1800)
    if proc.returncode != 0:
        print(f"FAIL  proof setup terminal: mise use {' '.join(TERMINAL_TOOLS)}:\n{said(proc, 8)}")
        return 1
    print(f"ok    proof setup terminal: {', '.join(TERMINAL_TOOLS)} pinned in mise.toml")
    print(
        f"next: {TECH_STACK} names vhs and ttyd under its tooling on this branch (I11: a tool "
        "added to mise.toml changes tech-stack.md too)"
    )
    return 0


PROOF_VERBS = {
    "run": proof_run,
    "log": proof_log,
    "http": proof_http,
    "shot": proof_shot,
    "video": proof_video,
    "tape": proof_tape,
    "attach": proof_attach,
    "confidence": proof_confidence,
}


def cmd_proof(ctx: Context, args: argparse.Namespace) -> int:
    """`mise run proof -- <verb>`: a capture, a confidence line, the test proof, the page, or
    the setup of the capture tools (design C.2)."""
    try:
        if args.verb == "setup":
            return proof_setup(ctx, args.what)
        target = proof_target(ctx)
        if args.verb == "show":
            return proof_show(target)
        if args.verb == "tests":
            return proof_tests(target)
        if args.verb != "confidence":
            check_case(target, args.id)
            require_clean(target, code=True)
        return PROOF_VERBS[args.verb](target, args)
    except ProofError as exc:
        print(f"FAIL  proof {args.verb}: {exc}")
        return 1


# ---------------------------------------------------------------- cli


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="project.py",
        description="Spec checks and status for this repo. The process: specs/README.md.",
    )
    parser.add_argument("--version", action="version", version=f"project.py {VERSION}")
    sub = parser.add_subparsers(dest="command", required=True, metavar="<command>")

    check = sub.add_parser(
        "check",
        help="scenario grammar, scenario <-> test trace, lane rules (run after the tests)",
        description="Exit 1 on any FAIL line. Reads .cache/spec-results.json from the last "
        "full test run; `mise run spec-check` runs the tests first.",
    )
    check.add_argument("--change", metavar="SLUG", help="lint one change folder, as approve does")
    check.add_argument(
        "--strict",
        action="store_true",
        help="nothing may be pending and no open question may remain (merge uses this)",
    )
    check.set_defaults(func=cmd_check)

    status = sub.add_parser("status", help="where this branch stands and what comes next")
    status.add_argument(
        "--change", action="store_true", help="print the change and its capability diff"
    )
    status.add_argument(
        "--merge",
        action="store_true",
        help="the Definition of Done, read-only: every check merge runs, and what it would write",
    )
    status.add_argument(
        "--audit",
        action="store_true",
        help="WARN for each commit on the default branch without the Merged-By trailer",
    )
    status.set_defaults(func=cmd_status)

    change = sub.add_parser(
        "change",
        help="start a change: its lane branch (feat: plus the change folder)",
        description="Refuses on a dirty tree (untracked backlog files aside) and while another "
        "change is open (I8). --lane feat commits specs/changes/<date>-<slug>/ from the templates "
        "(status: draft); plan/ slugs get today's date. On <lane>/<slug>, a heavier --lane "
        "upgrades the branch in place; a lighter one is refused.",
    )
    change.add_argument("slug", help="the change's slug, e.g. split-bill")
    change.add_argument("--lane", choices=LANES, default="feat", help="default: feat")
    change.add_argument(
        "--hotfix",
        action="store_true",
        help="fix lane only: a worktree ../<repo>-fix-<slug> off the default branch, allowed "
        "while a change is open; a human lands it with merge --branch fix/<slug>",
    )
    change.add_argument(
        "--parallel",
        action="store_true",
        help="multi-agent runs: slug <feat-slug>--g<n> makes the worker branch of group G<n> "
        "(parallel: yes) off feat/<feat-slug>",
    )
    change.set_defaults(func=cmd_change)

    backlog = sub.add_parser(
        "backlog",
        help="park an idea: specs/backlog/<date>-<slug>.md (never the roadmap)",
        description="Writes the backlog item from the template, uncommitted. --spike also makes "
        "a scratch worktree ../<repo>-spike-<slug>, detached at the default branch; only the "
        "findings, written into the item, ever land.",
    )
    backlog.add_argument("topic", nargs="+", help="a few words; the slug comes from them")
    backlog.add_argument("--spike", action="store_true", help="you want an answer, not code")
    backlog.set_defaults(func=cmd_backlog)

    approve = sub.add_parser(
        "approve",
        help="HUMAN (G2): approve the open feat change's spec",
        description="Lints the change folder and the scenarios (as spec-check --change does), "
        "sets status: approved and commits the spec as spec(<slug>): approve with the "
        "Spec-Approved: sha256 trailer merge checks (I6).",
    )
    approve.set_defaults(func=cmd_approve)

    merge = sub.add_parser(
        "merge",
        help="HUMAN (G1, G3): check the Definition of Done, then close and land the branch",
        description="specs/README.md#definition-of-done, in order. Nothing is written until "
        "every check passes; then a close commit on the branch (roadmap tick, status: done, "
        "CHANGELOG.md) and a squash onto the default branch with the Merged-By trailer (a pull "
        "request when origin is the recorded remote).",
    )
    merge.add_argument(
        "--branch", metavar="BRANCH", help="land the branch another worktree has checked out"
    )
    merge.add_argument(
        "--attest",
        action="store_true",
        help="no terminal to ask in: you read the human checks and confirm them all",
    )
    merge.add_argument(
        "--read-trunk",
        action="store_true",
        help="no terminal to ask in: you read the trunk diff merge prints (I19); the squash body "
        "records it",
    )
    merge.add_argument(
        "--gate-change",
        action="store_true",
        help="the branch changes gate files, or removes or changes a Trunk entry, on purpose",
    )
    merge.add_argument(
        "--reapprove",
        action="store_true",
        help="validation.md lost or reworded a Human check or Run it row since approve: you read "
        "the diff and approve the new list",
    )
    merge.add_argument(
        "--allow",
        action="append",
        metavar="ID",
        help="human-only escape: a prove-red FAIL for this id is allowed (needs --reason)",
    )
    merge.add_argument("--reason", help="why --allow; printed into the squash body")
    merge.add_argument(
        "--without-ci",
        metavar="WHY",
        help="human-only escape: the pull request may land although the generated workflow's "
        "checks never reported (Actions off, a rejected workflow); the squash body records WHY",
    )
    merge.add_argument(
        "--title", help="fast lanes: the squash subject (default: the branch's first commit)"
    )
    merge.add_argument(
        "--dry-run", action="store_true", help="every check, and what it would write; no writes"
    )
    merge.set_defaults(func=cmd_merge)

    abandon = sub.add_parser(
        "abandon",
        help="HUMAN: drop the open change: tag it, report it in the backlog, delete the branch",
    )
    abandon.add_argument("why", nargs="+", help="why it is dropped; it goes into the report")
    abandon.set_defaults(func=cmd_abandon)

    doctor = sub.add_parser(
        "doctor",
        help="this machine and repo: tools, git gates, the env contract, the audit",
        description="FAIL on a tool that does not run, gate config that is off, a non-empty env "
        "knob of the wrong type, a required secret that is unset, a secret that is not an op:// "
        "pointer, a flag that is not a bool off by default, a python pin in mise, uv's "
        "placeholder description, a malformed Trunk line, or a grown ruff baseline. The trailer "
        "audit, flag debt (a flag row older than 30 days) and a missing Trunk section warn.",
    )
    doctor.set_defaults(func=cmd_doctor)

    release = sub.add_parser(
        "release",
        help="HUMAN: cut a release by the Distribution in specs/tech-stack.md",
    )
    release.add_argument("bump", choices=BUMPS)
    release.add_argument(
        "--dry-run",
        action="store_true",
        help="the version, git-cliff's view and a build to a temp dir; no writes",
    )
    release.set_defaults(func=cmd_release)

    tdd = sub.add_parser(
        "tdd",
        help="compile loop: see tests fail for the right reason (red), then pass (green)",
        description="red: runs the tests tagged with the ids; each id needs a test that fails "
        "on an AssertionError, a NotImplementedError or a pytest.raises that saw nothing, every "
        "test new or changed on the branch must fail, and none may fail another way. Records "
        ".agent/tdd/<branch>.json and prints the Red: trailers. green: needs a red record per "
        "id; every linked test must pass.",
    )
    tdd.add_argument("phase", choices=("red", "green"))
    tdd.add_argument("ids", nargs="+", metavar="ID", help="scenario ids (space or comma separated)")
    tdd.set_defaults(func=cmd_tdd)

    prove = sub.add_parser(
        "prove-red",
        help="run the tests of new and changed scenarios on the old code (merge, CI)",
        description="Checks the scenarios this branch adds or changes, its Spec: (fix/, chg/) "
        "and Spec-Guard: (fix/) trailers, and every gap scenario against the source roots as "
        "they were at the merge-base, and that no test disappeared since the base. Exit 1 on "
        "any FAIL line.",
    )
    prove.add_argument(
        "--base",
        metavar="REF",
        help="compare with merge-base(HEAD, REF); default: the default branch",
    )
    prove.set_defaults(func=cmd_prove_red)

    hook = sub.add_parser(
        "hook",
        help="git hook entry points; the .githooks shims call these",
        description="pre-commit: the staged subset of verify (lane rules I1 I2 I4 I5, proof files "
        "against their README entries (I24), test tags, skips and xfails, ruff and ty on the "
        "staged copies, gitleaks). commit-msg: conventional "
        "subject and the Spec:, Spec-Guard:, Spec-Removed:, Test-Harness: trailers. pre-push: the "
        "default branch is pushed only by merge (PROJECT_MERGE) or at bootstrap. Exit 1 blocks. "
        "session-start and pre-bash are Claude Code's hooks (.claude/settings.json), fed the "
        "hook JSON on stdin: the derived session block, and the Bash guard (exit 2 blocks).",
    )
    hook.add_argument("name", choices=(*HOOKS, "install", *CLAUDE_HOOKS))
    hook.add_argument("args", nargs=argparse.REMAINDER, help="what git passes the hook")
    hook.set_defaults(func=cmd_hook)

    selftest = sub.add_parser(
        "selftest",
        help="the gate matrix: every bypass refused, every sanctioned move allowed",
        description="Runs the gate cases of specs/README.md#gates for real, in a scratch clone of "
        "this repo (its working tree included) with a bare origin, then pre-bash's cases, "
        "session-start's 3 KB cap and the hook launcher. Exit 1 when any case behaves otherwise "
        "than specified.",
    )
    selftest.add_argument("--keep", action="store_true", help="keep the scratch clone")
    selftest.set_defaults(func=cmd_selftest)
    add_proof_parser(sub)
    return parser


def add_proof_parser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    proof = sub.add_parser(
        "proof",
        help="the proof bundle: captures a reviewer looks at instead of reading leaf code",
        description="Each capture is one commit, docs(proof): <id> <kind>, under "
        'proof/<date>-<slug>/, indexed by its README.md (specs/README.md, "Proof"). Text '
        "passes gitleaks first, with the home folder written as ~; 5 MB per file, 15 MB per "
        "change. <id> is a scenario ID of the change or G<n> of its plan (any scenario ID on the "
        "fast lanes). Headless only: nothing opens a window.",
    )
    verbs = proof.add_subparsers(dest="verb", required=True, metavar="<verb>")
    case = "a scenario ID of the change, or G<n> of its plan"
    caption = "the entry's caption (default: the command, the file or the URL)"
    run = verbs.add_parser("run", help="a command's exit code, stdout and stderr")
    run.add_argument(
        "--before",
        action="store_true",
        help="also run it on the merge-base's code in a throwaway worktree: before and after",
    )
    run.add_argument("--timeout", type=int, default=PROOF_TIMEOUT, help="seconds per run")
    run.add_argument("--caption", help=caption)
    run.add_argument("id", help=case)
    run.add_argument("command", nargs=argparse.REMAINDER, help="-- <cmd...>")
    log = verbs.add_parser("log", help="an excerpt of a log the run wrote")
    log.add_argument("id", help=case)
    log.add_argument("file", help="the log file")
    log.add_argument("--grep", metavar="RE", help="keep the lines that match")
    log.add_argument("--since", metavar="MARKER", help="start at the last line holding it")
    log.add_argument("--caption", help=caption)
    http = verbs.add_parser("http", help="one request to a local server, and its answer")
    http.add_argument("id", help=case)
    http.add_argument("method", help="GET, POST, ...")
    http.add_argument("url", help="on localhost, 127.0.0.1 or ::1")
    http.add_argument("--data", metavar="JSON", help="the request body")
    http.add_argument("--header", action="append", metavar="'NAME: VALUE'")
    http.add_argument("--caption", help=caption)
    shot = verbs.add_parser("shot", help="a screenshot of a page, headless Chromium")
    shot.add_argument("id", help=case)
    shot.add_argument("url")
    shot.add_argument("--selector", metavar="CSS", help="one element instead of the whole page")
    shot.add_argument("--viewport", default="1280x800", metavar="WxH")
    shot.add_argument("--dark", action="store_true", help="prefers-color-scheme: dark")
    shot.add_argument("--caption", help=caption)
    video = verbs.add_parser("video", help="a recording of a flow, and its GIF preview")
    video.add_argument("id", help=case)
    video.add_argument("url")
    video.add_argument("--steps", required=True, metavar="FILE.py", help="defines steps(page)")
    video.add_argument("--seconds", type=int, default=15, help="the longest it may run")
    video.add_argument("--viewport", default="1280x800", metavar="WxH")
    video.add_argument("--width", type=int, default=800, help="the GIF preview's width")
    video.add_argument("--dark", action="store_true", help="prefers-color-scheme: dark")
    video.add_argument("--caption", help=caption)
    tape = verbs.add_parser("tape", help="a terminal recording that vhs renders from a .tape")
    tape.add_argument("id", help=case)
    tape.add_argument("file", help="the .tape script; it is kept beside the GIF")
    tape.add_argument("--caption", help=caption)
    attach = verbs.add_parser("attach", help="a file captured another way")
    attach.add_argument("id", help=case)
    attach.add_argument("file", help=", ".join(ATTACH_TYPES))
    attach.add_argument("--caption", required=True)
    confidence = verbs.add_parser("confidence", help="a group's confidence line, from validate")
    confidence.add_argument("group", help="G<n>")
    confidence.add_argument("level", help="high, medium or low")
    confidence.add_argument("why", nargs="*", help='-- "<one line: why>"')
    verbs.add_parser("tests", help="the automatic test proof: README.md's ## Tests section")
    verbs.add_parser("show", help="render .agent/proof/<date>-<slug>.html; opens nothing")
    setup = verbs.add_parser("setup", help="install the capture tools")
    setup.add_argument("what", choices=("web", "terminal"))
    proof.set_defaults(func=cmd_proof)


def main(argv: list[str] | None = None) -> int:
    words = sys.argv[1:] if argv is None else argv
    if len(words) == 2 and words[0] == "hook" and words[1] in CLAUDE_HOOKS:
        return claude_hook(words[1], read_stdin())  # before argparse: never exit 2 by accident
    args = build_parser().parse_args(argv)
    root = find_root(Path.cwd())
    if root is None:
        print("project.py: not inside a git repository", file=sys.stderr)
        return 2
    catch_exit_signals()
    try:
        return int(args.func(load_context(root), args))
    except UsageError as exc:
        print(f"project.py: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("project.py: interrupted", file=sys.stderr)
        return 128 + signal.SIGINT


if __name__ == "__main__":
    sys.exit(main())
