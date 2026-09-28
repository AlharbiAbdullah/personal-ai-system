"""
Fixtures for the sanity harness tests.

Every test gets `w`, a throwaway home tree, and the whole harness (core.P) points at it for the
test's duration. A test builds only what its check reads, then asserts the verdict through the
runner's own path (`st()`), so a check that raises reports FAIL exactly as it would live.

Naming (META-3 reads it): every check has at least one `test_<id>_fault*` function, e.g.
`test_data_1_fault_no_remote` for DATA-1, proving the check fires on the fault it exists for.

Run: uv run --offline --python 3.12 --with chromadb --with pytest \
       python3 -m pytest 03-rai/skills/rai/scripts/tests -q -p no:cacheprovider
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import sanity  # noqa: E402  (registers every check)
from sanity_checks import core  # noqa: E402

GIT = ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
       "-c", "user.name=t", "-c", "user.email=t@t", "-c", "init.defaultBranch=main"]


class World:
    """A fixture home: `~/helm`, `~/.claude`, `~/.local/state` and friends under one tmp dir."""

    def __init__(self, root: Path):
        self.home = root
        self.helm = root / "helm"
        self.rai = self.helm / "03-rai"
        self.sm = self.rai / "semantic-memory"
        self.helm.mkdir(parents=True)

    def path(self, rel: str) -> Path:
        return self.home / rel

    def write(self, rel: str, text: str = "", age_h: float | None = None, mode: int | None = None) -> Path:
        p = self.path(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        if mode is not None:
            p.chmod(mode)
        if age_h is not None:
            self.age(rel, age_h)
        return p

    def json(self, rel: str, obj, age_h: float | None = None) -> Path:
        return self.write(rel, json.dumps(obj), age_h=age_h)

    def jsonl(self, rel: str, rows: list, age_h: float | None = None) -> Path:
        return self.write(rel, "".join(json.dumps(r) + "\n" for r in rows), age_h=age_h)

    def age(self, rel: str, hours: float):
        t = time.time() - hours * 3600
        os.utime(self.path(rel), (t, t))

    def link(self, rel: str, target: Path | str):
        p = self.path(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.is_symlink() or p.exists():
            p.unlink()
        p.symlink_to(target)
        return p

    def mkdir(self, rel: str) -> Path:
        p = self.path(rel)
        p.mkdir(parents=True, exist_ok=True)
        return p

    # ── git ──────────────────────────────────────────────────────────────────────
    def git(self, *args, env: dict | None = None, cwd: Path | None = None) -> str:
        e = {**os.environ, **(env or {})}
        r = subprocess.run([*GIT, *args], cwd=cwd or self.helm, capture_output=True, text=True, env=e)
        assert r.returncode == 0, r.stderr
        return r.stdout.strip()

    def commit(self, msg: str = "c", age_h: float = 0.0, rel: str | None = None):
        rel = rel or f"f{time.time_ns()}.txt"
        (self.helm / rel).parent.mkdir(parents=True, exist_ok=True)
        (self.helm / rel).write_text(msg)
        self.git("add", "-A")
        when = f"@{int(time.time() - age_h * 3600)} +0000"
        self.git("commit", "-q", "-m", msg, env={"GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when})

    def git_repo(self, age_h: float = 0.0, origin: bool = True):
        """helm as a git repo with one commit; `origin` is a local bare repo tracking main."""
        self.git("init", "-q")
        self.commit("init", age_h=age_h)
        if origin:
            bare = self.home / "origin.git"
            self.git("init", "-q", "--bare", str(bare), cwd=self.home)
            self.git("remote", "add", "origin", str(bare))
            self.git("push", "-q", "-u", "origin", "main")

    # ── chromadb ─────────────────────────────────────────────────────────────────
    def chroma(self, collections: dict):
        """{name: [metadata, ...]} -> real collections under the fixture's chromadb dir.
        Rows carry explicit embeddings, so no embedding model is loaded."""
        client = core._client()
        for name, rows in collections.items():
            col = client.get_or_create_collection(name)
            if rows:
                col.add(ids=[f"{name}-{i}" for i in range(len(rows))],
                        embeddings=[[0.1, 0.2, 0.3] for _ in rows],
                        documents=[f"doc {i}" for i in range(len(rows))],
                        metadatas=[m or {"k": "v"} for m in rows])
        return client

    # ── the Claude Code edge ─────────────────────────────────────────────────────
    def settings(self, hooks: dict | None = None, extra: dict | None = None):
        """03-rai/config/settings.json with `hooks` as {event: [command, ...]}, linked from
        ~/.claude/settings.json the way claude-config.sh links it."""
        cfg = {"hooks": {ev: [{"hooks": [{"type": "command", "command": c} for c in cmds]}]
                         for ev, cmds in (hooks or {}).items()}}
        cfg.update(extra or {})
        self.json("helm/03-rai/config/settings.json", cfg)
        self.link(".claude/settings.json", self.rai / "config/settings.json")


@pytest.fixture
def w(tmp_path, monkeypatch):
    world = World(tmp_path / "home")
    core.set_home(world.home)
    monkeypatch.setenv("RAI_ROLE", "producer")
    yield world
    core.set_home(Path.home())


def entry(cid: str):
    for e in core.CHECKS:
        if e[0] == cid:
            return e
    raise KeyError(cid)


def st(cid: str, role: str = "producer", quick: bool = False):
    """Run one check exactly as the runner does; returns the R row."""
    return sanity.run_one(entry(cid), quick, role)


def hook_cmd(w: World, name: str) -> str:
    return f"python3 $HOME/helm/03-rai/hooks/{name}.py"
