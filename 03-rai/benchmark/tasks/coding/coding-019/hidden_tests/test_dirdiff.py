import hashlib
import os
import random
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "dirdiff.sh"


def run(*args):
    return subprocess.run(
        ["bash", str(SCRIPT), *map(str, args)],
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )


def tree(base, files):
    base.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        path = base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes) else content.encode())
    return base


def expected_lines(old, new, excluded=lambda rel: False):
    def scan(base):
        out = {}
        for dirpath, _dirs, files in os.walk(base):
            for name in files:
                full = Path(dirpath) / name
                if full.is_symlink():
                    continue
                rel = full.relative_to(base).as_posix()
                if not excluded(rel):
                    out[rel] = hashlib.sha256(full.read_bytes()).hexdigest()
        return out

    a, b = scan(old), scan(new)
    lines = []
    for rel in sorted(set(a) | set(b)):
        if rel not in b:
            lines.append(f"D {rel}")
        elif rel not in a:
            lines.append(f"A {rel}")
        elif a[rel] != b[rel]:
            lines.append(f"M {rel}")
    return lines


def test_identical_trees(tmp_path):
    files = {"a.txt": "1", "sub/b.txt": "2", ".hidden": "3"}
    old, new = tree(tmp_path / "old", files), tree(tmp_path / "new", files)
    proc = run(old, new)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == ""


def test_added_deleted_modified_sorted(tmp_path):
    old = tree(
        tmp_path / "old",
        {
            "keep.txt": "same",
            "gone.txt": "x",
            "conf/app.toml": "port=1",
            "B.txt": "b",
            "z/deep/er.txt": "1",
        },
    )
    new = tree(
        tmp_path / "new",
        {
            "keep.txt": "same",
            "conf/app.toml": "port=2",
            "new.txt": "n",
            "B.txt": "b",
            "z/deep/er.txt": "2",
            "a.txt": "a",
        },
    )
    proc = run(old, new)
    assert proc.returncode == 1
    assert proc.stdout.splitlines() == [
        "A a.txt",
        "M conf/app.toml",
        "D gone.txt",
        "A new.txt",
        "M z/deep/er.txt",
    ]


def test_byte_order_with_spaces_dots_and_slashes(tmp_path):
    old = tree(tmp_path / "old", {})
    new = tree(
        tmp_path / "new",
        {"a/x.txt": "1", "a.txt": "2", "a b.txt": "3", "Z.txt": "4", "_u.txt": "5"},
    )
    assert run(old, new).stdout.splitlines() == [
        "A Z.txt",
        "A _u.txt",
        "A a b.txt",
        "A a.txt",
        "A a/x.txt",
    ]


def test_awkward_names(tmp_path):
    names = [
        "my file.txt",
        "w[1]*.txt",
        "-rf.txt",
        "dir with space/inner file",
        ".env",
        "back\\slash.txt",
        "quote's.txt",
    ]
    old = tree(tmp_path / "old", {n: "old" for n in names})
    new = tree(tmp_path / "new", {n: "new" for n in names})
    proc = run(old, new)
    assert proc.returncode == 1, proc.stderr
    assert proc.stdout.splitlines() == [f"M {n}" for n in sorted(names)]


def test_same_content_moved_is_add_and_delete(tmp_path):
    old = tree(tmp_path / "old", {"one/f.txt": "data"})
    new = tree(tmp_path / "new", {"two/f.txt": "data"})
    assert run(old, new).stdout.splitlines() == ["D one/f.txt", "A two/f.txt"]


def test_empty_file_counts(tmp_path):
    old = tree(tmp_path / "old", {"e.txt": ""})
    new = tree(tmp_path / "new", {"e.txt": "", "f.txt": ""})
    assert run(old, new).stdout.splitlines() == ["A f.txt"]


def test_symlinks_and_empty_dirs_are_ignored(tmp_path):
    old = tree(tmp_path / "old", {"real.txt": "r"})
    new = tree(tmp_path / "new", {"real.txt": "r"})
    (new / "link.txt").symlink_to(new / "real.txt")
    (new / "empty").mkdir()
    (old / "also-empty" / "nested").mkdir(parents=True)
    proc = run(old, new)
    assert proc.returncode == 0
    assert proc.stdout == ""


def test_excludes(tmp_path):
    old = tree(
        tmp_path / "old",
        {
            "a.tmp": "1",
            "x/b.tmp": "1",
            "build/out.bin": "1",
            "build.txt": "1",
            "notes.txt": "1",
            "src/main.py": "1",
        },
    )
    new = tree(
        tmp_path / "new",
        {
            "a.tmp": "2",
            "x/b.tmp": "2",
            "build/deep/out.bin": "2",
            "build.txt": "2",
            "notes.txt": "2",
            "src/main.py": "2",
        },
    )
    proc = run("-x", "*.tmp", "-x", "build/*", "-x", "notes.txt", old, new)
    assert proc.returncode == 1
    assert proc.stdout.splitlines() == ["M build.txt", "M src/main.py"]
    proc = run("-x", "*", old, new)
    assert proc.returncode == 0
    assert proc.stdout == ""


def test_quiet(tmp_path):
    old = tree(tmp_path / "old", {"a": "1"})
    new = tree(tmp_path / "new", {"a": "2"})
    proc = run("-q", old, new)
    assert (proc.returncode, proc.stdout) == (1, "")
    proc = run("-q", old, old)
    assert (proc.returncode, proc.stdout) == (0, "")


@pytest.mark.parametrize("seed", [2, 31, 777])
def test_generated_trees(tmp_path, seed):
    rng = random.Random(seed)
    names = [
        "a.txt",
        "b c.txt",
        "d/e.txt",
        "d/f g/h.txt",
        ".cfg",
        "x/y/z.bin",
        "Q.md",
        "q.md",
        "d-1.txt",
        "d.txt",
    ]
    old_files = {
        n: bytes(rng.randrange(256) for _ in range(rng.randrange(0, 50)))
        for n in names
        if rng.random() < 0.8
    }
    new_files = {}
    for n in names:
        r = rng.random()
        if n in old_files and r < 0.5:
            new_files[n] = old_files[n]
        elif r < 0.85:
            new_files[n] = bytes(
                rng.randrange(256) for _ in range(rng.randrange(0, 50))
            )
    old, new = tree(tmp_path / "old", old_files), tree(tmp_path / "new", new_files)
    want = expected_lines(old, new)
    proc = run(old, new)
    assert proc.stdout.splitlines() == want
    assert proc.returncode == (1 if want else 0)
    excluded = lambda rel: rel.startswith("d/")
    proc = run("-x", "d/*", old, new)
    assert proc.stdout.splitlines() == expected_lines(old, new, excluded)


@pytest.mark.parametrize(
    "case",
    [
        "none",
        "one",
        "three",
        "old-missing",
        "new-is-file",
        "bad-option",
        "x-without-value",
    ],
)
def test_usage_errors(tmp_path, case):
    old = tree(tmp_path / "old", {"a": "1"})
    new = tree(tmp_path / "new", {"a": "2"})
    plain = tmp_path / "plain.txt"
    plain.write_text("x")
    args = {
        "none": [],
        "one": [old],
        "three": [old, new, new],
        "old-missing": [tmp_path / "nope", new],
        "new-is-file": [old, plain],
        "bad-option": ["-z", old, new],
        "x-without-value": [old, new, "-x"],
    }[case]
    proc = run(*args)
    assert proc.returncode == 2
    assert proc.stderr.strip()
    assert proc.stdout == ""
