"""project-init v3.1, milestone M15: the proof bundle (design C of
03-rai/skills/project-init/project-init-v3.1-review-depth.md).

`mise run proof` captures what a reviewer looks at instead of reading leaf code: a command's
output before and after, a log excerpt, an HTTP exchange, a screenshot, a video, a terminal
recording, an attachment, and a confidence line per group. Each capture is one commit under
proof/<date>-<slug>/, indexed by that folder's README.md; merge holds the index to the ## Proof
rows of validation.md (I23) and every file to its recorded sha256 and the caps (I24).

The ## Proof lint runs on the M2 fixture (test_check.py). Captures, merge and the pull request
body run on the adopted M5 fixture (test_lifecycle.py). Screenshots and videos drive a headless
Chromium through Playwright against a page served on localhost inside the test, and the terminal
recording runs vhs; each skips with its setup command in the reason when its tool is missing.
"""

from __future__ import annotations

import http.server
import json
import os
import re
import shutil
import subprocess
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest
import test_check as m2
import test_lifecycle as m5

Repo = m5.Repo
output = m5.output
CHANGE = m5.CHANGE
FOLDER = f"proof/{m5.TODAY}-split-bill"
HOME = str(Path.home())
FAKE_AWS_ID = "AKIA" + "QYLPMN5HHHFPZAM2"  # split, so this file never matches the rule itself
REVIEW = (
    '## Review focus   (implied inputs the spec never named; each -> a scenario, or "none: '
    '<reason>")\n- zero people -> none: out of scope, the backlog holds it\n'
)
PROOF_HEAD = (
    "## Proof   (what a human looks at instead of reading leaf code; test proof is automatic)\n"
    "| for | kind | shows |\n|---|---|---|\n"
)
SPLIT = ("uv", "run", "--locked", "tipcalc", "100", "--split", "4")
PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f"
    b"\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0\xf0\x1f\x00\x05\x00\x01\xff\x89\x99=\x1d"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)
PAGE = """<!doctype html>
<html><head><title>cards</title></head>
<body style="background:#223;color:#eee;font:20px sans-serif">
<h1>Saved cards</h1>
<button id="save" onclick="document.body.insertAdjacentHTML('beforeend','<p>saved</p>')">Save</button>
</body></html>
"""
STEPS = """\
def steps(page):
    page.click("#save")
    page.wait_for_selector("text=saved")
"""


def validation(*rows: str) -> str:
    """validation.md with Review focus, the ## Proof rows given, and no Human checks."""
    proof = PROOF_HEAD + "".join(f"| {row} |\n" for row in rows) if rows else ""
    return REVIEW + proof + m5.NO_CHECKS


def talked(repo: Repo, *rows: str) -> None:
    """feat/split-bill with talk's files written (uncommitted) and the ## Proof rows given."""
    started = repo.project("change", "split-bill")
    assert started.returncode == 0, output(started)
    m5.talk(repo)
    repo.write(f"{CHANGE}/validation.md", validation(*rows))


def approved(repo: Repo, *rows: str) -> None:
    """talked(), approved, and G1 compiled: the split-bill code committed on green."""
    talked(repo, *rows)
    result = repo.project("approve")
    assert result.returncode == 0, output(result)
    m5.compile_group(repo)


def proof(repo: Repo, *args: str, env: dict[str, str] | None = None) -> str:
    """`project.py proof <args>` that must pass; its output."""
    result = repo.project("proof", *args, env=env)
    assert result.returncode == 0, output(result)
    return output(result)


def refused(repo: Repo, *args: str, env: dict[str, str] | None = None) -> str:
    """`project.py proof <args>` that must be refused, leaving HEAD and the tree as they were."""
    head = repo.head()
    result = repo.project("proof", *args, env=env)
    assert result.returncode != 0, output(result)
    assert repo.head() == head
    assert repo.git("status", "--porcelain", "--", "proof").strip() == ""
    return output(result)


def readme(repo: Repo) -> str:
    return (repo.path / FOLDER / "README.md").read_text(encoding="utf-8")


def last_commit(repo: Repo) -> tuple[str, list[str]]:
    """(subject, paths) of HEAD."""
    subject = repo.git("log", "-1", "--format=%s").strip()
    return subject, repo.git("show", "--name-only", "--format=", "HEAD").split()


@pytest.fixture(scope="session")
def adopted(tmp_path_factory: pytest.TempPathFactory) -> m5.Adopted:
    return m5.adopt(tmp_path_factory)


@pytest.fixture
def repo(adopted: m5.Adopted, tmp_path: Path) -> Repo:
    """A copy of the adopted repo on main, as test_lifecycle.py's fixture makes it."""
    dest = tmp_path / "tipcalc"
    shutil.copytree(
        adopted.path, dest, symlinks=True, ignore=shutil.ignore_patterns(".venv", ".cache")
    )
    return Repo(dest, tmp_path)


@pytest.fixture(scope="session")
def feat_tree(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """test_check.py's M2 fixture on feat/entrypoint-hardening, its change folder a draft."""
    built = m2.build(tmp_path_factory.mktemp("proof-feat") / "tipcalc")
    built.git("switch", "-q", "-c", m2.FEAT)
    shutil.copytree(m2.FIXTURES / "feat1", built.path, dirs_exist_ok=True)
    built.commit("spec(entrypoint-hardening): draft")
    return built.path


@pytest.fixture
def feat(feat_tree: Path, tmp_path: Path) -> m2.Repo:
    shutil.copytree(feat_tree, tmp_path / "tipcalc", symlinks=True)
    return m2.Repo(tmp_path / "tipcalc")


@pytest.fixture
def served(tmp_path: Path) -> Iterator[str]:
    """http://127.0.0.1:<port>: PAGE at /cards and a JSON answer at /api/cards, from a thread."""

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path.startswith("/api/"):
                body, kind = b'{"cards": ["visa 4242"]}', "application/json"
            else:
                body, kind = PAGE.encode(), "text/html; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: object) -> None:
            del args

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


# ---------------------------------------------------------------- the index, as a module


def test_the_index_is_markdown_that_reads_back() -> None:
    """README.md is written from the index and read back to the same index: one heading per
    entry (`### <id> · <kind> · <caption>`), a meta line with the commit and each file's
    sha256, then the media: an image inline, a text capture in a fence longer than any it
    holds, before and after as two blocks, a long one folded into <details>."""
    project = m5.load_project_module()
    name = "2026-09-26-split-bill"
    run = project.ProofEntry(
        "cli.split-bill",
        "run --before",
        "tipcalc 100 --split 4",
        "0123456789",
        [("r.before.txt", "0" * 64), ("r.txt", "f" * 64)],
    )
    shot = project.ProofEntry(
        "G1", "screenshot", "http://127.0.0.1:8000/cards", "0123456789", [("s.png", "a" * 64)]
    )
    log = project.ProofEntry("G2", "log", "app.log", "abcdef0123", [("l.txt", "b" * 64)])
    tests = ["| scenario | tests |", "|---|---|", "| `cli.split-bill` | `t.py::test` |"]
    confidence = {"G1": ("high", "every path has a test"), "G2": ("low", "dark mode unseen")}
    index = project.ProofIndex(name, tests, confidence, [run, shot, log])
    files = {
        "r.before.txt": b"$ tipcalc\n```\nold\n",
        "r.txt": b"new\n",
        "s.png": PNG,
        "l.txt": "".join(f"line {n}\n" for n in range(50)).encode(),
    }
    text = project.render_index(index, files.get)
    assert text.startswith(f"# Proof: {name}\n")
    assert "### cli.split-bill · run --before · tipcalc 100 --split 4\n" in text
    meta = f"captured at `0123456789` · `r.before.txt` sha256 `{'0' * 64}` · `r.txt` sha256 `"
    assert meta in text
    assert "before, on the merge-base code:\n\n````text\n$ tipcalc\n```\nold\n````\n" in text
    assert "after:\n\n```text\nnew\n```\n" in text
    assert "![http://127.0.0.1:8000/cards](s.png)" in text
    assert "<details><summary>l.txt (50 lines)</summary>" in text
    assert text.index("## Tests") < text.index("## Confidence") < text.index("## Entries")
    back = project.parse_index(text, name)
    assert not back.problems, back.problems
    assert back.tests == tests
    assert back.confidence == confidence
    got = [(e.sid, e.kind, e.caption, e.at, e.files) for e in back.entries]
    assert got == [(e.sid, e.kind, e.caption, e.at, e.files) for e in (run, shot, log)]
    broken = text.replace("captured at `abcdef0123`", "captured on a Tuesday")
    assert "has no 'captured at' line" in " ".join(project.parse_index(broken, name).problems)


def test_a_long_output_keeps_its_head_and_tail() -> None:
    project = m5.load_project_module()
    assert project.clip_text("short\n") == "short\n"
    text = "".join(f"{n:05d}\n" for n in range(4000))  # 24 000 bytes
    clipped = project.clip_text(text)
    assert clipped.startswith("00000\n")
    assert clipped.rstrip().endswith("03999")
    assert "bytes cut ...]" in clipped
    assert len(clipped.encode()) < project.PROOF_STREAM_CAP + 100


def test_proof_files_are_checked_by_their_bytes() -> None:
    project = m5.load_project_module()
    check = project.media_problem
    assert check("a.png", PNG) is None
    assert check("a.gif", b"GIF89a....") is None
    assert check("a.webm", b"\x1a\x45\xdf\xa3....") is None
    assert check("a.mp4", b"\x00\x00\x00\x18ftypmp42") is None
    assert check("a.pdf", b"%PDF-1.7\n") is None
    assert check("a.txt", "héllo\n".encode()) is None
    assert check("a.svg", b'<svg xmlns="http://www.w3.org/2000/svg"/>') is None
    assert "empty" in (check("a.txt", b"") or "")
    assert "not a png file" in (check("a.png", b"GIF89a") or "")
    assert "not UTF-8" in (check("a.txt", b"\xff\xfe\x00") or "")
    assert "extension" in (check("a.exe", b"MZ") or "")


def test_home_is_written_as_a_tilde_and_captions_stay_on_one_line() -> None:
    project = m5.load_project_module()
    assert project.home_free(f"{HOME}/notes and {HOME}") == "~/notes and ~"
    caption = project.proof_caption(f"sh -c 'cat {HOME}/x`y` · z'\nnext")
    assert caption == "sh -c 'cat ~/x'y' - z' next"
    assert len(project.proof_caption("x" * 300)) <= 100


def test_blob_urls_come_from_the_remote() -> None:
    project = m5.load_project_module()
    base = project.blob_base
    assert base("https://github.com/o/r.git") == "https://github.com/o/r"
    assert base("https://github.com/o/r") == "https://github.com/o/r"
    assert base("git@github.com:o/r.git") == "https://github.com/o/r"
    assert base("ssh://git@github.com:22/o/r.git") == "https://github.com/o/r"
    assert base("/srv/git/origin.git") is None
    assert base("file:///srv/git/origin.git") is None
    assert base("") is None


def test_the_pull_request_shows_each_capture_inline(tmp_path: Path) -> None:
    """Design C.6 and E: images and GIFs through their blob URL at the pushed tip, a WebM as a
    link beside its GIF, text in <details>, low confidence first, and the full index."""
    project = m5.load_project_module()
    name = "2026-09-26-split-bill"
    folder = tmp_path / "proof" / name
    folder.mkdir(parents=True)
    files = {
        "G1-shot-cards.png": PNG,
        "G2-video-save.webm": b"\x1a\x45\xdf\xa3 webm",
        "G2-video-save.gif": b"GIF89a gif",
        "cli.x-run-y.before.txt": b"$ tipcalc\nexit 2\n",
        "cli.x-run-y.txt": b"$ tipcalc\nexit 0\n",
    }
    for file, data in files.items():
        (folder / file).write_bytes(data)
    entries = [
        project.ProofEntry("G1", "screenshot", "the cards", "a" * 10, [("G1-shot-cards.png", "")]),
        project.ProofEntry(
            "G2",
            "video",
            "save a card",
            "a" * 10,
            [("G2-video-save.webm", ""), ("G2-video-save.gif", "")],
        ),
        project.ProofEntry(
            "cli.x",
            "run --before",
            "tipcalc",
            "a" * 10,
            [("cli.x-run-y.before.txt", ""), ("cli.x-run-y.txt", "")],
        ),
    ]
    confidence = {"G1": ("high", "tested"), "G2": ("low", "flaky page")}
    bundle = project.ProofBundle(name, project.ProofIndex(name, [], confidence, entries))
    tip = "c0ffee" * 6 + "c0ff"
    blob = f"https://github.com/o/r/blob/{tip}/proof/{name}"
    text = "\n".join(project.pr_proof_lines(bundle, tmp_path, "https://github.com/o/r", tip))
    assert text.index("G2 low") < text.index("G1 high")
    assert f"![the cards]({blob}/G1-shot-cards.png?raw=true)" in text
    assert f"![save a card]({blob}/G2-video-save.gif?raw=true)" in text
    assert f"({blob}/G2-video-save.webm?raw=true)" in text
    assert "<details><summary>before and after" in text
    assert "exit 2" in text and "exit 0" in text
    assert f"full index: [proof/{name}/README.md]({blob}/README.md)" in text
    local = "\n".join(project.pr_proof_lines(bundle, tmp_path, None, tip))
    assert f"![the cards](proof/{name}/G1-shot-cards.png)" in local


def test_the_pull_request_template_has_section_e_and_the_checklist_merge_writes() -> None:
    project = m5.load_project_module()
    text = (m5.SKILL / "templates" / "pull_request_template.md").read_text(encoding="utf-8")
    heads = [line for line in text.splitlines() if line.startswith("## ")]
    wanted = ["What", "Review depth", "Rollback", "Proof", "Scenarios", "Checklist"]
    assert heads == [f"## {name}" for name in wanted]
    checklist = [line for line in text.splitlines() if line.startswith("- [ ]")]
    assert checklist == list(project.PR_CHECKLIST)


# ---------------------------------------------------------------- ## Proof in validation.md


def test_proof_rows_are_one_per_case_in_a_kind_that_exists(feat: m2.Repo) -> None:
    """Design C.3: | for | kind | shows |, `for` an ID of this change or a G<n> of its plan,
    one row per case (a second row for the same case FAILs), at most 6 rows (a warning)."""
    rel = f"{m2.CHANGE}/validation.md"
    text = feat.read(rel)

    def lint(*rows: str) -> subprocess.CompletedProcess[str]:
        table = PROOF_HEAD + "".join(f"| {row} |\n" for row in rows)
        feat.write(rel, text.replace("## Human checks", table + "## Human checks"))
        return feat.check("--change", "entrypoint-hardening")

    result = lint("cli.no-args | run --before | `tipcalc` exits 2", "G2 | log | the knob")
    assert result.returncode == 0, output(result)
    assert "unexpected section" not in result.stdout
    result = lint("cli.no-args | run | exits 2", "cli.no-args | screenshot | the error")
    assert result.returncode == 1
    assert "a second Proof row for cli.no-args: one proof per case" in result.stdout, output(result)
    result = lint("cli.help | recording | the help")
    assert "a Proof row's kind is one of run, log, http, screenshot, video, terminal" in (
        result.stdout
    ), output(result)
    result = lint("cli.help | test | the test")
    assert "test proof is automatic" in result.stdout, output(result)
    result = lint("cli.tip-default | run | the tip")
    assert "cli.tip-default is not an ID of this change" in result.stdout, output(result)
    result = lint("G3 | run | a third group")
    assert "G3 is not a group of" in result.stdout, output(result)
    result = lint("cli.help | run |")
    assert "a Proof row is | for | kind | shows |" in result.stdout, output(result)
    many = [f"{sid} | run | out" for sid in ("cli.no-args", "cli.help", "cli.bad-amount")]
    many += ["cli.negative-amount | run | out", "config.percent-empty | log | x"]
    many += ["config.percent-invalid | log | x", "G1 | attach | chart"]
    result = lint(*many)
    assert result.returncode == 0, output(result)
    assert "7 Proof rows (cap 6)" in result.stdout


def test_a_repo_with_a_ui_warns_without_a_visual_row(feat: m2.Repo) -> None:
    """Design C.3, last bullet: a known web or TUI framework among the runtime dependencies and
    no screenshot, video or terminal row: spec-check and approve warn."""
    feat.edit("pyproject.toml", "dependencies = []", 'dependencies = ["textual>=1"]')
    result = feat.check("--change", "entrypoint-hardening")
    assert result.returncode == 0, output(result)
    assert "the repo has a UI (textual in pyproject.toml)" in result.stdout, output(result)
    rel = f"{m2.CHANGE}/validation.md"
    row = PROOF_HEAD + "| cli.help | terminal | the help screen |\n"
    feat.edit(rel, "## Human checks", row + "## Human checks")
    result = feat.check("--change", "entrypoint-hardening")
    assert "the repo has a UI" not in result.stdout, output(result)


# ---------------------------------------------------------------- captures


def test_run_before_commits_the_old_and_the_new_output(repo: Repo) -> None:
    """`run --before`: the command on the merge-base's code in a throwaway worktree, then on
    HEAD; both outputs in one entry and one commit, `docs(proof): <id> <kind>`, that touches
    only this change's folder."""
    approved(repo, "cli.split-bill | run --before | `tipcalc 100 --split 4` prints each share")
    said = proof(repo, "run", "--before", "cli.split-bill", "--", *SPLIT)
    assert f"{FOLDER}/" in said
    subject, paths = last_commit(repo)
    assert subject == "docs(proof): cli.split-bill run --before"
    stem = f"{FOLDER}/cli.split-bill-run-uv-run-locked-tipcalc-100-split-4"
    assert paths == [f"{FOLDER}/README.md", f"{stem}.before.txt", f"{stem}.txt"]
    before = (repo.path / f"{stem}.before.txt").read_text(encoding="utf-8")
    after = (repo.path / f"{stem}.txt").read_text(encoding="utf-8")
    assert before.startswith("$ uv run --locked tipcalc 100 --split 4\nexit 0 in ")
    assert "tip: 15.0" in before and "each:" not in before
    assert "each: 28.75" in after
    text = readme(repo)
    assert "### cli.split-bill · run --before · uv run --locked tipcalc 100 --split 4" in text
    head = repo.head("HEAD~1")[:10]
    assert re.search(rf"(?m)^captured at `{head}` · `cli\.split-bill-run-[^`]+\.before\.txt`", text)
    assert repo.git("status", "--porcelain").strip() == ""
    assert not list(Path(repo.path).glob("../prove-red-*"))


def test_a_capture_refuses_what_it_cannot_prove(repo: Repo) -> None:
    """Captures run on a lane branch, name a case of the change, record a committed HEAD, and
    reach only a local server; a refusal writes nothing."""
    said = refused(repo, "run", "cli.tip-default", "--", "true")
    assert "proof lives on a lane branch" in said
    approved(repo)
    said = refused(repo, "run", "cli.tip-default", "--", "true")
    assert "cli.tip-default is not an ID of this change" in said
    said = refused(repo, "run", "G2", "--", "true")
    assert "G2 is not a group of" in said
    said = refused(repo, "run", "nope.nope", "--", "true")
    assert "nope.nope: no such scenario" in said
    said = refused(repo, "http", "G1", "GET", "https://example.com/")
    assert "a local server only" in said
    said = refused(repo, "run", "G1", "--", "no-such-command-here")
    assert "cannot run" in said
    repo.append("README.md", "\nwork in progress\n")
    said = refused(repo, "run", "G1", "--", "true")
    assert "commit first" in said and "README.md" in said
    repo.git("checkout", "--", "README.md")
    shutil.copy(repo.path / "README.md", repo.path.parent / "notes.exe")
    said = refused(repo, "attach", "G1", str(repo.path.parent / "notes.exe"), "--caption", "x")
    assert "attach takes" in said
    said = refused(repo, "confidence", "G1", "sure", "--", "why")
    assert "high, medium or low" in said
    repo.git("switch", "-q", "-c", "chg/other", "main")
    said = refused(repo, "run", "G1", "--", "true")
    assert "a group is a feat change's" in said


def test_the_leak_scan_refuses_a_secret_and_writes_home_as_a_tilde(repo: Repo) -> None:
    """I24: a text capture passes gitleaks with the repo's rules before anything is written;
    the home folder is written as ~ first, so a path alone never trips it."""
    approved(repo)
    said = refused(repo, "run", "G1", "--", "sh", "-c", f"echo key={FAKE_AWS_ID}")
    assert "gitleaks found" in said and "nothing was written" in said
    assert FAKE_AWS_ID not in said
    proof(repo, "run", "G1", "--", "sh", "-c", 'echo "$HOME/notes"')
    capture = next((repo.path / FOLDER).glob("G1-run-*.txt")).read_text(encoding="utf-8")
    assert "~/notes" in capture
    assert HOME not in capture
    assert HOME not in readme(repo)


def test_log_http_and_attach_capture_text_and_files(repo: Repo, served: str) -> None:
    approved(repo)
    log = repo.path / ".cache" / "app.log"  # ignored: a runtime log is never tracked
    log.parent.mkdir(exist_ok=True)
    log.write_text("boot\nrequest a\nrun 2\nrequest b\nerror c\nrequest d\n", encoding="utf-8")
    proof(repo, "log", "G1", ".cache/app.log", "--since", "run 2", "--grep", "request")
    capture = next((repo.path / FOLDER).glob("G1-log-*.txt")).read_text(encoding="utf-8")
    assert "request b\nrequest d\n" in capture
    assert "request a" not in capture and "error c" not in capture
    assert last_commit(repo)[0] == "docs(proof): G1 log"

    proof(repo, "http", "cli.split-bill", "GET", f"{served}/api/cards")
    capture = next((repo.path / FOLDER).glob("cli.split-bill-http-*.txt")).read_text("utf-8")
    assert f"> GET {served}/api/cards" in capture
    assert "< 200 OK" in capture
    assert '{"cards": ["visa 4242"]}' in capture


def test_a_new_capture_for_a_case_replaces_its_entry(repo: Repo, served: str) -> None:
    """One entry per case (design C.3): a capture for a scenario or group that has one replaces
    it in the same commit, `docs(proof): <id> <kind>`: of the same kind, its file is written
    again; of another kind, the old files go (git rm) and the new ones come."""
    approved(repo)
    proof(repo, "http", "cli.split-bill", "GET", f"{served}/api/cards")
    first = repo.head("HEAD~1")[:10]
    said = proof(repo, "http", "cli.split-bill", "GET", f"{served}/api/cards")
    assert f"replaced http captured at {first}" in said
    names = [p.name for p in (repo.path / FOLDER).glob("cli.split-bill-http-*.txt")]
    assert len(names) == 1, names
    assert readme(repo).count("### cli.split-bill · ") == 1
    assert last_commit(repo) == (
        "docs(proof): cli.split-bill http",
        [f"{FOLDER}/README.md", f"{FOLDER}/{names[0]}"],
    )
    second = repo.head("HEAD~1")[:10]
    image = repo.path.parent / "chart.png"
    image.write_bytes(PNG)
    said = proof(repo, "attach", "cli.split-bill", str(image), "--caption", "the split chart")
    assert f"replaced http captured at {second}" in said
    changed = repo.git("show", "--name-status", "--format=", "HEAD").splitlines()
    assert f"D\t{FOLDER}/{names[0]}" in changed, changed
    assert f"A\t{FOLDER}/cli.split-bill-attach-the-split-chart.png" in changed
    assert last_commit(repo)[0] == "docs(proof): cli.split-bill attach"
    text = readme(repo)
    assert text.count("### cli.split-bill · ") == 1
    assert "### cli.split-bill · attach · the split chart" in text
    assert "![the split chart](cli.split-bill-attach-the-split-chart.png)" in text
    assert not list((repo.path / FOLDER).glob("cli.split-bill-http-*"))
    assert repo.git("status", "--porcelain").strip() == ""


def test_two_entries_for_one_case_fail_at_merge(repo: Repo) -> None:
    """A README.md edited by hand to hold two entries for one case fails merge's proof step
    (and its preview): one capture per case, and capturing again replaces them."""
    approved(repo)
    proof(repo, "run", "G1", "--", "echo", "one")
    proof(repo, "confidence", "G1", "high", "--", "tested")
    text = readme(repo)
    start = text.index("### G1 · run")
    repo.write(f"{FOLDER}/README.md", text + "\n" + text[start:])
    repo.commit("docs: the entry twice")
    result = repo.project("merge")
    assert result.returncode == 1
    assert "a second entry for G1: one capture per case" in result.stdout, output(result)


def test_a_capture_over_the_cap_names_the_flag_that_shrinks_it(repo: Repo) -> None:
    approved(repo)
    big = repo.path.parent / "big.png"
    big.write_bytes(PNG + b"\x00" * (5 * 1024 * 1024))
    said = refused(repo, "attach", "G1", str(big), "--caption", "too big")
    assert "over the 5 MB cap per file" in said
    project = m5.load_project_module()
    problems = project.cap_problems("screenshot", {"a.png": 6 << 20}, 0)
    assert any("--viewport" in problem for problem in problems)
    problems = project.cap_problems("video", {"a.webm": 1 << 20}, 15 << 20)
    assert any("15 MB cap per change" in problem and "--seconds" in problem for problem in problems)


def test_confidence_the_test_section_and_the_offline_page(repo: Repo) -> None:
    """confidence: one line per group, replaced when given again. tests: the ## Tests section
    from the results, the tdd red record or the Red: trailer. show: .agent/proof/<name>.html,
    self-contained, with no request to anywhere."""
    approved(repo)
    repo.commit("test(cli): keep the red reason", "--allow-empty", "--trailer", "Red: cli.split-bill: assert 'tip: 15.0\\n' == 'tip: 15.0\\neach: 28.75\\n'")  # fmt: skip
    proof(repo, "confidence", "G1", "medium", "--", "the split is tested; rounding is not")
    proof(repo, "confidence", "G1", "high", "--", "every path has a test")
    assert last_commit(repo)[0] == "docs(proof): G1 confidence"
    text = readme(repo)
    assert "- G1 high: every path has a test" in text
    assert "medium" not in text
    assert repo.run("uv", "run", "--locked", "pytest").returncode == 0
    proof(repo, "tests")
    subject, paths = last_commit(repo)
    assert (subject, paths) == ("docs(proof): tests", [f"{FOLDER}/README.md"])
    text = readme(repo)
    row = next(line for line in text.splitlines() if line.startswith("| `cli.split-bill`"))
    assert "`tests/test_split.py::test_split_bill`" in row
    assert "assert 'tip: 15.0\\n' == 'tip: 15.0\\neach: 28.75\\n'" in row
    assert "passed" in row and "at merge" in row
    said = proof(repo, "tests")
    assert "unchanged" in said

    image = repo.path.parent / "chart.png"
    image.write_bytes(PNG)
    proof(repo, "attach", "cli.split-bill", str(image), "--caption", "the chart")
    proof(repo, "run", "G1", "--", *SPLIT)
    said = proof(repo, "show")
    page = repo.path / ".agent" / "proof" / f"{m5.TODAY}-split-bill.html"
    assert f".agent/proof/{m5.TODAY}-split-bill.html" in said
    html = page.read_text(encoding="utf-8")
    assert html.startswith("<!doctype html>")
    assert '<img alt="the chart" src="data:image/png;base64,' in html
    assert "each: 28.75" in html
    assert "G1 high: every path has a test" in html
    assert "review depth" in html and "<td><code>cli.split-bill</code></td>" in html
    assert not re.search(r"""(src|href)=["']?(https?:)?//""", html)
    assert repo.git("status", "--porcelain").strip() == ""  # .agent/ is ignored


def test_merge_holds_the_proof_rows_to_their_captures(repo: Repo) -> None:
    """I23 and I24 at merge (a DoD step after Run it; status --merge runs it read-only): a
    row's capture is made on this branch after approve and current since, every feat group has
    a confidence line (low first, marked), every file matches its sha256 within the caps.
    Then the proof lands: its Tests section from the close commit, a Proof block in the squash
    body, and the review depth's leaf line skims against it."""
    talked(repo, "G1 | run | `tipcalc 100 --split 4` prints each share")
    early = repo.head()[:10]
    proof(repo, "run", "G1", "--", *SPLIT)  # the old output, captured while talking
    assert last_commit(repo)[0] == "docs(proof): G1 run"
    assert repo.project("approve").returncode == 0
    m5.compile_group(repo)
    result = repo.project("merge")
    assert result.returncode == 1
    text = result.stdout
    assert "proof ............. FAIL" in text, output(result)
    assert "G1 | run: its capture was made before approve" in text
    assert "G1 has no confidence line: mise run proof -- confidence G1" in text

    said = proof(repo, "run", "G1", "--", *SPLIT)
    assert f"replaced run captured at {early}" in said
    proof(repo, "confidence", "G1", "low", "--", "the split of odd cents is untested")
    repo.write("src/tipcalc/__init__.py", '"""Tip calculator."""\n\n' + m5.SPLIT_CODE)
    repo.commit("feat(cli): a docstring", "--trailer", "Spec: cli.split-bill")
    result = repo.project("merge")
    assert result.returncode == 1
    assert "G1 | run: its capture is stale (src/tipcalc/__init__.py changed since" in result.stdout

    stale = repo.head("HEAD~1")[:10]
    said = proof(repo, "run", "G1", "--", *SPLIT)  # the stale capture goes
    assert "replaced run captured at" in said
    assert readme(repo).count("### G1 · ") == 1
    assert f"captured at `{stale}`" not in readme(repo)
    captures = list((repo.path / FOLDER).glob("G1-run-*.txt"))
    assert len(captures) == 1, captures
    capture = captures[0]
    capture.write_text(capture.read_text(encoding="utf-8") + "edited\n", encoding="utf-8")
    repo.git("add", "-A")
    repo.git("-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "docs: a hand edit")
    big = repo.path / FOLDER / "big.png"
    big.write_bytes(PNG + b"\x00" * (5 * 1024 * 1024))
    repo.git("add", "-A")
    repo.git("-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "docs: a big file")
    result = repo.project("merge")
    assert result.returncode == 1
    text = result.stdout
    assert f"I24: {FOLDER}/{capture.name} does not match the sha256 its entry records" in text
    assert f"I24: {FOLDER}/big.png is 5.0 MB, over the 5 MB cap per file" in text
    assert f"{FOLDER}/big.png is in no entry of README.md" in text
    repo.git("reset", "-q", "--hard", "HEAD~2")

    status = repo.project("status", "--merge")
    assert status.returncode == 0, output(status)
    text = status.stdout
    assert "proof ............. ok 1 row captured" in text, output(status)
    assert "! confidence G1 low: the split of odd cents is untested" in text
    assert f"folder: {FOLDER}/ (mise run proof -- show renders .agent/proof/" in text
    assert text.index("run it ..") < text.index("proof .....")
    assert "against proof: 1 entry, confidence G1 low" in text

    result = repo.project("merge")
    assert result.returncode == 0, output(result)
    body = repo.git("log", "-1", "--format=%B", "main")
    assert f"Proof: {FOLDER}/ (1 run; tests for 1 scenario)" in body, body
    assert "  ! confidence G1 low: the split of odd cents is untested" in body
    assert "against proof: 1 entry, confidence G1 low" in body
    landed = repo.show("main", f"{FOLDER}/README.md")
    row = next(line for line in landed.splitlines() if line.startswith("| `cli.split-bill`"))
    assert "ok red (assertion)" in row, landed


def test_a_fast_lane_lands_its_test_proof(repo: Repo, tmp_path: Path) -> None:
    """On chg/ and fix/ the close commit writes the ## Tests section too, into proof/<date of
    the branch's first commit>-<slug>/README.md, and spec-check accepts that close commit: here
    it stays on the branch, since the pull request's checks fail."""
    origin = tmp_path / "origin.git"
    m5.record_origin(repo, origin)
    assert repo.project("change", "split-bill", "--lane", "chg").returncode == 0
    repo.append("specs/capabilities/cli.md", m5.SCENARIO)
    repo.write("tests/test_split.py", m5.TEST_SPLIT)
    repo.write("src/tipcalc/__init__.py", m5.SPLIT_CODE)
    repo.commit("change(cli): split the bill", "--trailer", "Spec: cli.split-bill")
    proof(repo, "run", "--before", "cli.split-bill", "--", *SPLIT)  # hooks pass it on chg/ too
    assert last_commit(repo)[0] == "docs(proof): cli.split-bill run --before"
    result = repo.project("merge", "--dry-run")
    assert result.returncode == 0, output(result)
    assert f"{FOLDER}/README.md: ## Tests" in result.stdout
    assert "lands as 'change(cli): split the bill'" in result.stdout  # never the proof commit
    failing = '[{"name": "verify", "bucket": "fail", "workflow": "ci", "link": ""}]'
    env = m5.gh_env(tmp_path, origin, GH_CHECKS=failing, GH_REQUIRED=failing)
    result = repo.project("merge", env=env)
    assert result.returncode == 1
    assert "the close commit stays on the branch" in result.stdout, output(result)
    subject, paths = last_commit(repo)
    assert subject == "chore(split-bill): close for merge"
    assert paths == ["CHANGELOG.md", f"{FOLDER}/README.md"]
    text = readme(repo)
    assert "| `cli.split-bill` | `tests/test_split.py::test_split_bill` |" in text
    assert "ok red (assertion)" in text
    assert "### cli.split-bill · run --before · uv run --locked tipcalc 100 --split 4" in text
    verify = repo.run("mise", "run", "verify")
    assert verify.returncode == 0, output(verify)


def test_the_preview_names_the_tests_section_merge_writes(repo: Repo) -> None:
    """`proof tests` leaves prove-red's column `at merge`, so merge's close commit writes the
    ## Tests section again with the verdicts. The preview's close line named that write only
    when the section differed before prove-red ran, so in the M18 run the preview and merge
    disagreed. Both now name it after the slow pass, and the lines match."""
    assert repo.project("change", "split-bill", "--lane", "chg").returncode == 0
    repo.append("specs/capabilities/cli.md", m5.SCENARIO)
    repo.write("tests/test_split.py", m5.TEST_SPLIT)
    repo.write("src/tipcalc/__init__.py", m5.SPLIT_CODE)
    repo.commit("change(cli): split the bill", "--trailer", "Spec: cli.split-bill")
    tested = repo.run("mise", "run", "test")
    assert tested.returncode == 0, output(tested)
    proof(repo, "tests")
    assert "| at merge |" in readme(repo)
    preview = repo.project("status", "--merge")
    assert preview.returncode == 0, output(preview)
    close = next(line for line in preview.stdout.splitlines() if line.startswith("  close "))
    assert f"{FOLDER}/README.md: ## Tests" in close, close
    result = repo.project("merge", "--read-trunk")
    assert result.returncode == 0, output(result)
    assert close in result.stdout.splitlines(), output(result)
    landed = repo.git("show", f"main:{FOLDER}/README.md")
    assert "ok red (assertion)" in landed and "| at merge |" not in landed


def test_a_ratchet_to_feat_carries_the_proof_folder_over(repo: Repo) -> None:
    """chg/ (or fix/) ratcheting to feat: the proof folder takes the change folder's name, by
    git mv in the ratchet's own commit, so the captures made on the fast lane carry over."""
    assert repo.project("change", "split-bill", "--lane", "chg").returncode == 0
    repo.append("specs/capabilities/cli.md", m5.SCENARIO)
    repo.write("tests/test_split.py", m5.TEST_SPLIT)
    repo.write("src/tipcalc/__init__.py", m5.SPLIT_CODE)
    dated = ("--date", "2026-01-02T10:00:00")  # the fast lane's folder is dated by it
    repo.commit("change(cli): split the bill", "--trailer", "Spec: cli.split-bill", *dated)
    proof(repo, "run", "cli.split-bill", "--", "echo", "split")
    old = "proof/2026-01-02-split-bill"
    capture = next((repo.path / old).glob("cli.split-bill-run-*.txt")).name
    result = repo.project("change", "split-bill", "--lane", "feat")
    assert result.returncode == 0, output(result)
    assert f"{old}/ moves to {FOLDER}/" in result.stdout
    assert last_commit(repo)[0] == "spec(split-bill): ratchet chg to feat"
    moved = repo.git("show", "-M", "--name-status", "--format=", "HEAD").splitlines()
    assert f"R100\t{old}/{capture}\t{FOLDER}/{capture}" in moved, moved
    assert not (repo.path / old).exists()
    text = readme(repo)
    assert text.startswith(f"# Proof: {m5.TODAY}-split-bill\n")
    assert "### cli.split-bill · run · echo split" in text
    assert repo.git("status", "--porcelain").strip() == ""
    said = proof(repo, "run", "cli.split-bill", "--", "echo", "again")  # I5: its own folder now
    assert "replaced run captured at" in said


def test_a_dropped_proof_row_needs_reapprove(repo: Repo) -> None:
    """A dropped or loosened ## Proof row after approve needs --reapprove, as a Human check."""
    approved(repo, "G1 | run --before | the old code has no --split")
    proof(repo, "confidence", "G1", "high", "--", "tested")
    rel = f"{CHANGE}/validation.md"
    repo.write(rel, validation("G1 | run | the split"))
    repo.commit("spec(split-bill): a looser proof row")
    result = repo.project("merge")
    assert result.returncode == 1
    text = result.stdout
    assert "dropped: Proof row G1 | run --before | the old code has no --split" in text, text
    assert "merge -- --reapprove" in text
    assert "G1 | run: no capture: mise run proof -- run G1 ..." in text


def test_pre_commit_holds_proof_files_to_their_entries(repo: Repo) -> None:
    """I24 in pre-commit: a proof file is committed only with its README entry's sha256; I5: a
    branch writes only its own proof folder, so a landed one stays frozen."""
    approved(repo)
    proof(repo, "run", "G1", "--", "echo", "one")
    capture = next((repo.path / FOLDER).glob("G1-run-*.txt"))
    capture.write_text("edited by hand\n", encoding="utf-8")
    repo.git("add", "-A")
    result = repo.run("git", "commit", "-q", "-m", "docs: tweak the proof")
    assert result.returncode == 1
    assert f"I24: {FOLDER}/{capture.name} does not match the sha256" in output(result)
    repo.git("checkout", "HEAD", "--", FOLDER)
    other = "proof/2000-01-01-old/README.md"
    repo.write(other, "# Proof: 2000-01-01-old\n")
    repo.git("add", "-A")
    result = repo.run("git", "commit", "-q", "-m", "docs: touch another proof folder")
    assert result.returncode == 1
    assert f"I5: proof/2000-01-01-old/ is not this branch's proof folder ({FOLDER}/)" in output(
        result
    )


def test_the_pull_request_body_embeds_the_proof(repo: Repo, tmp_path: Path) -> None:
    """Design C.6 and E, on the remote path: `gh pr create` gets the body in section E's shape
    (What, Review depth, Rollback, Proof, Scenarios, Checklist) with the proof shown, and the
    squash body stays the plain record."""
    origin = tmp_path / "origin.git"
    m5.record_origin(repo, origin)
    approved(repo, "G1 | run | the split")
    proof(repo, "run", "G1", "--", *SPLIT)
    proof(repo, "confidence", "G1", "high", "--", "every path has a test")
    env = m5.gh_env(tmp_path, origin, GH_CHECKS=m5.VERIFY, GH_REQUIRED=m5.VERIFY)
    result = repo.project("merge", env=env)
    assert result.returncode == 0, output(result)
    state = json.loads((tmp_path / "gh.json").read_text(encoding="utf-8"))
    body = state["pr"]["body"]
    heads = [line for line in body.splitlines() if line.startswith("## ")]
    assert heads == [
        "## What",
        "## Review depth",
        "## Rollback",
        "## Proof",
        "## Scenarios",
        "## Checklist",
    ], body
    assert "Groups want each person's share of the bill and the tip." in body
    assert "leaf:  SKIM  6 files  +" in body  # the proof folder is what the leaf is read against
    assert "revert: a new CLI option and nothing stored" in body
    assert "confidence G1 high: every path has a test" in body
    assert "<details><summary>G1 · run · uv run --locked tipcalc 100 --split 4" in body
    assert "each: 28.75" in body
    assert f"full index: [{FOLDER}/README.md]({FOLDER}/README.md)" in body
    assert "cli.split-bill" in body.split("## Scenarios")[1]
    assert "- [ ] The `## Proof` rows are captured" in body
    squash = repo.git("log", "-1", "--format=%B", "main")
    assert "## What" not in squash
    assert f"Proof: {FOLDER}/" in squash


# ---------------------------------------------------------------- tools


def fake_tool(tmp_path: Path, name: str) -> dict[str, str]:
    """PATH with a stand-in for name first, which logs its argv to <name>.log and exits 0."""
    bin_dir = tmp_path / "fake-bin"
    bin_dir.mkdir(exist_ok=True)
    tool = bin_dir / name
    tool.write_text(f'#!/bin/sh\necho "$@" >>"{tmp_path}/{name}.log"\n', encoding="utf-8")
    tool.chmod(0o755)
    return {"PATH": f"{bin_dir}{os.pathsep}{m5.clean_env(tmp_path)['PATH']}"}


def test_setup_pins_the_capture_tools(repo: Repo, tmp_path: Path) -> None:
    """setup terminal pins vhs and ttyd with mise and reminds that tech-stack.md lists new
    tools (I11); setup web installs what Playwright needs for a headless Chromium."""
    assert repo.project("change", "demo", "--lane", "chore").returncode == 0
    said = proof(repo, "setup", "terminal", env=fake_tool(tmp_path, "mise"))
    logged = (tmp_path / "mise.log").read_text(encoding="utf-8")
    assert "use aqua:charmbracelet/vhs@" in logged and "aqua:tsl0922/ttyd@" in logged
    assert "specs/tech-stack.md" in said and "I11" in said
    said = proof(repo, "setup", "web", env=fake_tool(tmp_path, "uv"))
    logged = (tmp_path / "uv.log").read_text(encoding="utf-8")
    assert "--with playwright==" in logged and "playwright install" in logged
    assert "ffmpeg" in logged
    assert "headless" in said


def test_a_missing_capture_tool_refuses_with_its_setup_command(repo: Repo, tmp_path: Path) -> None:
    approved(repo)
    tape = repo.path.parent / "demo.tape"
    tape.write_text('Type "tipcalc 100"\nEnter\nSleep 1s\n', encoding="utf-8")
    path = os.pathsep.join(
        p
        for p in m5.clean_env(tmp_path)["PATH"].split(os.pathsep)
        if not (Path(p) / "vhs").exists()
    )
    said = refused(repo, "tape", "G1", str(tape), env={"PATH": path})
    assert "mise run proof -- setup terminal" in said
    # mise's shims outside a repo that pins the tools: on PATH, but each run only errors. The
    # M18 acceptance run met mise's own advice (`mise use -g ...`) instead of the setup command
    shims = tmp_path / "shims"
    shims.mkdir()
    for tool in ("vhs", "ttyd"):
        (shims / tool).write_text(
            f"#!/bin/sh\necho 'mise ERROR No version is set for shim: {tool}' >&2\nexit 1\n",
            encoding="utf-8",
        )
        (shims / tool).chmod(0o755)
    said = refused(repo, "tape", "G1", str(tape), env={"PATH": f"{shims}{os.pathsep}{path}"})
    assert "mise run proof -- setup terminal" in said, said
    assert "mise use -g" not in said, said
    missing = {"PROJECT_PROOF_CHROMIUM": str(tmp_path / "no-chromium")}
    said = refused(repo, "shot", "G1", "http://127.0.0.1:9/cards", env=missing)
    assert "mise run proof -- setup web" in said


def playwright_ready(repo: Repo) -> str | None:
    """Why a headless capture cannot run here, or None when it can."""
    if not Path("/usr/bin/chromium").is_file() and not os.environ.get("PROJECT_PROOF_CHROMIUM"):
        return "no Chromium here: mise run proof -- setup web"
    probe = repo.run(
        "uv", "run", "--no-project", "--quiet", "--with", "playwright==1.63.0", "python", "-c",
        "import playwright",
    )  # fmt: skip
    if probe.returncode != 0:
        return "Playwright does not install here: mise run proof -- setup web"
    return None


def test_shot_and_video_capture_a_local_page_headless(repo: Repo, served: str) -> None:
    approved(repo)
    if why := playwright_ready(repo):
        pytest.skip(why)
    proof(repo, "shot", "G1", f"{served}/cards", "--viewport", "640x400", "--dark")
    shot = next((repo.path / FOLDER).glob("G1-shot-*.png"))
    assert shot.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert last_commit(repo)[0] == "docs(proof): G1 screenshot"
    steps = repo.path.parent / "save.py"
    steps.write_text(STEPS, encoding="utf-8")
    if not shutil.which("ffmpeg"):
        pytest.skip("no ffmpeg here for the GIF preview: mise run proof -- setup web")
    video = ("proof", "video", "cli.split-bill", f"{served}/cards", "--steps", str(steps))
    result = repo.project(*video)
    if "setup web" in output(result):
        pytest.skip(f"Playwright's video recorder is missing: {output(result)[-200:]}")
    assert result.returncode == 0, output(result)
    assert "replaced" not in output(result)  # another case: the screenshot stays
    assert shot.is_file()
    webm = next((repo.path / FOLDER).glob("cli.split-bill-video-*.webm"))
    gif = webm.with_suffix(".gif")
    assert webm.read_bytes().startswith(b"\x1a\x45\xdf\xa3")
    assert gif.read_bytes().startswith(b"GIF8")
    text = readme(repo)
    assert f"![{served}/cards]({gif.name})" in text
    assert f"[{webm.name}]({webm.name})" in text


def vhs_path(repo: Repo) -> str | None:
    """PATH with the vhs and ttyd of mise's aqua backend first, or None when mise cannot get
    them (a bare shim on PATH does not count: outside a repo that pins it, it only errors)."""
    tools = ("aqua:charmbracelet/vhs@0.12.1", "aqua:tsl0922/ttyd@1.7.7")
    where = repo.run("mise", "x", *tools, "--", "sh", "-c", 'dirname "$(command -v vhs)"; dirname "$(command -v ttyd)"')  # fmt: skip
    folders = where.stdout.split()
    if where.returncode != 0 or len(folders) != 2:
        return None
    return os.pathsep.join([*folders, m5.clean_env(repo.trusted)["PATH"]])


def test_tape_renders_a_terminal_recording(repo: Repo) -> None:
    approved(repo)
    path = vhs_path(repo)
    if path is None:
        pytest.skip("vhs and ttyd are not installed here: mise run proof -- setup terminal")
    tape = repo.path.parent / "split.tape"
    tape.write_text(
        'Output ignored.gif\nSet Width 800\nSet Height 300\nType "echo split"\nEnter\nSleep 1s\n',
        encoding="utf-8",
    )
    proof(repo, "tape", "G1", str(tape), env={"PATH": path})
    gif = next((repo.path / FOLDER).glob("G1-tape-*.gif"))
    kept = gif.with_suffix(".tape").read_text(encoding="utf-8")
    assert gif.read_bytes().startswith(b"GIF8")
    assert kept.startswith(f"Output {gif.name}\n")
    assert "ignored.gif" not in kept
    assert last_commit(repo)[0] == "docs(proof): G1 terminal"
    assert f"![split.tape]({gif.name})" in readme(repo)
