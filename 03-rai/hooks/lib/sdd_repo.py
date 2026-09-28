"""
sdd_repo.py — is this session inside a project-init v3 (SDD) repo? (H27 routing, M10)

Repo truth lives in the repo. A repo with `.project.toml` keeps its requirements,
decisions, commands and lessons in `specs/` + `project_memory/`, so Rai memory keeps
only John-level preferences he states himself (never inferred), cross-project lessons
with a repo pointer, and exactly one `worked in <repo>: <what>` pointer line. Both Rai-memory
writers ask this module: turn-capture.py (live daily bullets) and distill_session.py
(batch distill). Everything else (helm, plain repos, chat sessions) keeps today's
behaviour because `sdd_repo()` returns ''.

Detection walks from the cwd up to the git toplevel (the nearest dir holding `.git`,
a dir or a worktree file), inclusive; outside git only the cwd itself counts. A session
JSON whose `cwd` is empty (an archived capture from the retired SessionEnd hook, which read
only line 1 of the transcript) resolves it from the native transcript: `session_cwd()`.
`leak_check()` is the code-side backstop behind the prompt rule: it flags a memory line
that names one of the repo's declared scenario IDs or one of its files by path.
Pure python, no subprocess, never raises.
"""

import json
import re
from pathlib import Path

MARKER = ".project.toml"
MAX_WHAT_CHARS = 200

# A pointer line, bulleted or not: "- worked in tipcalc: ..." / "worked in tipcalc: ...".
POINTER_RE = re.compile(r"^\s*(?:-\s+)?worked in\b", re.IGNORECASE)
_POINTER_PREFIX_RE = re.compile(
    r"^\s*(?:-\s+)?worked in\s+\S+?(?:[:,]\s*|\s+[—–-]\s*|\s+|$)", re.IGNORECASE)
_ORIGIN_RE = re.compile(r'^\s*origin_url\s*=\s*"([^"]*)"', re.MULTILINE)
# "### Scenario: cli.no-args [gap: ...]" -> cli.no-args (design 5.1: `<cap>.<slug>`)
_SCENARIO_RE = re.compile(r"^#{2,6}\s+Scenario:\s*`?([\w-]+\.[\w.-]*[\w-])", re.MULTILINE)
_PATHISH_RE = re.compile(r"[\w.~@+-]*/[\w.@+/-]*[\w@+-]")  # a token holding a slash
MAX_SPEC_FILES = 500


def sdd_root(cwd) -> Path | None:
    """Dir holding `.project.toml` for `cwd` (itself, or an ancestor up to the git
    toplevel), else None. A removed cwd (a deleted worktree) still resolves when an
    ancestor up to its toplevel survives."""
    if not cwd:
        return None
    try:
        start = Path(cwd).expanduser().resolve()
        chain = [start, *start.parents]
        top = next((i for i, d in enumerate(chain) if (d / ".git").exists()), None)
        for d in chain[: 1 if top is None else top + 1]:
            if (d / MARKER).is_file():
                return d
    except (OSError, RuntimeError, ValueError):
        pass
    return None


def repo_name(root: Path) -> str:
    """Stable name for the pointer: the origin_url basename recorded in `.project.toml`,
    else the main checkout's folder for a linked worktree, else the folder name."""
    try:
        m = _ORIGIN_RE.search((root / MARKER).read_text(errors="replace"))
        url = m.group(1).strip().rstrip("/") if m else ""
        name = re.sub(r"\.git$", "", url.rsplit("/", 1)[-1].rsplit(":", 1)[-1])
        if name:
            return name
        git = root / ".git"
        if git.is_file():  # linked worktree: "gitdir: <main>/.git/worktrees/<name>"
            gitdir = git.read_text(errors="replace").partition("gitdir:")[2].strip()
            p = (root / gitdir).resolve()
            if p.parent.name == "worktrees" and p.parents[1].name == ".git":
                return p.parents[2].name
    except (OSError, RuntimeError, ValueError, IndexError):
        pass
    return root.name


def sdd_repo(cwd) -> str:
    """Repo name when `cwd` sits inside a project-init v3 repo, else '' (today's behaviour)."""
    root = sdd_root(cwd)
    return repo_name(root) if root else ""


def transcript_cwd(path) -> str:
    """First `cwd` recorded in a native Claude Code transcript, '' when none or unreadable."""
    if not path or not isinstance(path, (str, Path)):
        return ""
    try:
        with open(path, errors="replace") as fh:
            for line in fh:
                if '"cwd"' not in line:
                    continue
                try:
                    cwd = json.loads(line).get("cwd")
                except (ValueError, AttributeError):
                    continue
                if isinstance(cwd, str) and cwd:
                    return cwd
    except OSError:
        pass
    return ""


def session_cwd(session: dict) -> str:
    """Where a queued session ran: its `cwd`, else the first `cwd` of its native transcript,
    as the scanner's normalize_transcript records it. An archived capture from the retired
    SessionEnd hook carries cwd '' (the hook read only line 1, a `last-prompt` entry)."""
    cwd = session.get("cwd")
    if isinstance(cwd, str) and cwd:
        return cwd
    return transcript_cwd(session.get("transcript_path") or "")


def scenario_ids(root: Path) -> set[str]:
    """Scenario IDs the repo declares under specs/ (`### Scenario: <cap>.<slug>`)."""
    ids: set[str] = set()
    try:
        for i, f in enumerate(sorted((root / "specs").rglob("*.md"))):
            if i >= MAX_SPEC_FILES:
                break
            ids.update(_SCENARIO_RE.findall(f.read_text(errors="replace")))
    except (OSError, RuntimeError, ValueError):
        pass
    return ids


def leak_check(root):
    """Predicate over one memory line: True when it names a scenario ID declared in the
    repo's specs/ or one of the repo's files by path (repo-relative or absolute). A
    backstop behind the prompt rule; requirements and decisions in plain words are the
    prompt's job. `root` None (not a project-init repo) flags nothing."""
    if root is None:
        return lambda text: False
    try:
        root = Path(root).resolve()
    except (OSError, RuntimeError, ValueError):
        return lambda text: False
    ids = sorted(scenario_ids(root), key=len, reverse=True)
    id_re = re.compile(r"(?<![\w.-])(?:" + "|".join(map(re.escape, ids)) + r")(?![\w-])"
                       ) if ids else None

    def repo_file(token: str) -> bool:
        try:
            p = Path(token).expanduser()
            p = (p if p.is_absolute() else root / p).resolve()
            return p.is_relative_to(root) and p.is_file()
        except (OSError, RuntimeError, ValueError):
            return False

    def leaks(text) -> bool:
        text = str(text or "")
        return bool(id_re and id_re.search(text)) or any(
            repo_file(t) for t in _PATHISH_RE.findall(text))

    return leaks


def pointer_line(repo: str, what: str = "", leaks=None) -> str:
    """The one pointer Rai memory keeps: `worked in <repo>: <what>`, one sentence, one line.
    A `what` that `leaks` flags (a scenario ID or repo path) falls back to the generic text."""
    what = next((ln for ln in (what or "").splitlines() if ln.strip()), "")
    what = _POINTER_PREFIX_RE.sub("", what).strip()
    what = re.split(r"(?<=[.!?])\s", what, maxsplit=1)[0].strip()
    if leaks and leaks(what):
        what = ""
    if len(what) > MAX_WHAT_CHARS:
        what = what[: MAX_WHAT_CHARS - 1].rstrip() + "…"
    return f"worked in {repo}: {what or 'details live in the repo'}"


def has_pointer(text: str, repo: str) -> bool:
    """True when `text` already holds the `worked in <repo>:` pointer line."""
    return bool(re.search(rf"^\s*(?:-\s+)?worked in {re.escape(repo)}:", text or "",
                          re.IGNORECASE | re.MULTILINE))


def routing_rule(repo: str) -> str:
    """The H27 rule both writers add to their model prompt for a session in `repo`."""
    return (
        f'REPO RULE: this ran inside "{repo}", a project-init repo. That repo is the source of '
        "truth for its own work (specs/, project_memory/, git), so Rai memory must NOT hold its "
        "requirements, commands, decisions, scenario IDs, file paths, process steps or other "
        "facts about it. A choice made in or for this repo (a value, name, library, design or "
        "workflow step) stays in the repo, whether Rai made it, John left it to Rai "
        '("you pick") or John ordered it ("use 2"): leave it out, and never turn it into '
        '"John prefers / picks / defaults to ...". A request for what this repo\'s program '
        "should do is a requirement, not a preference. Keep ONLY: (1) John's own "
        "preferences and standing rules: a sentence in which John himself says what he "
        'prefers, likes, dislikes, always or never does ("I prefer ...", "I like ...", '
        '"always ...", "never ...", "from now on ..."). Keep it even though he said it while '
        "working here: restate it as his preference, close to his words, adding nothing from "
        "this repo. It must be something he wrote: never infer a pattern, habit or expectation "
        "from what Rai did or from John approving, delegating or reacting; (2) cross-project "
        "lessons that would change what Rai does in a different repo, stated generically with "
        f'no code, values or paths from this repo, each ending "(seen in {repo})"; (3) exactly '
        "one pointer line "
        f'"worked in {repo}: <under 20 words on what was done, no repo specifics>". Anything '
        "else is left out, and an empty result besides the pointer is normal."
    )
