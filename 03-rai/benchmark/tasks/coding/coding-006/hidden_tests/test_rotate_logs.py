import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "rotate_logs.sh"


def run(*args):
    return subprocess.run(
        ["bash", str(SCRIPT), *map(str, args)],
        capture_output=True,
        check=False,
        text=True,
        timeout=20,
    )


def write(d, name, text):
    (d / name).write_text(text)


def snapshot(d):
    return {
        str(p.relative_to(d)): (p.read_bytes() if p.is_file() else None)
        for p in sorted(d.rglob("*"))
    }


def test_basic_rotation(tmp_path):
    write(tmp_path, "app.log", "new\n")
    write(tmp_path, "app.log.1", "g1\n")
    write(tmp_path, "app.log.2", "g2\n")
    write(tmp_path, "app.log.3", "g3\n")
    proc = run(tmp_path, 3)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "rotated app.log\n"
    assert (tmp_path / "app.log").read_text() == ""
    assert (tmp_path / "app.log.1").read_text() == "new\n"
    assert (tmp_path / "app.log.2").read_text() == "g1\n"
    assert (tmp_path / "app.log.3").read_text() == "g2\n"
    assert not (tmp_path / "app.log.4").exists()


def test_output_is_byte_sorted_and_each_file_rotates(tmp_path):
    for name in ["b.log", "a.log", "Z.log", "a b.log"]:
        write(tmp_path, name, f"data of {name}")
    proc = run(tmp_path, 2)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines() == [
        "rotated Z.log",
        "rotated a b.log",
        "rotated a.log",
        "rotated b.log",
    ]
    for name in ["b.log", "a.log", "Z.log", "a b.log"]:
        assert (tmp_path / f"{name}.1").read_text() == f"data of {name}"
        assert (tmp_path / name).read_bytes() == b""


def test_empty_log_is_skipped(tmp_path):
    write(tmp_path, "idle.log", "")
    write(tmp_path, "idle.log.1", "old")
    write(tmp_path, "busy.log", "x")
    proc = run(tmp_path, 3)
    assert proc.returncode == 0
    assert proc.stdout == "rotated busy.log\n"
    assert (tmp_path / "idle.log.1").read_text() == "old"
    assert not (tmp_path / "idle.log.2").exists()


def test_lowered_keep_deletes_old_generations(tmp_path):
    write(tmp_path, "app.log", "now")
    write(tmp_path, "app.log.1", "g1")
    write(tmp_path, "app.log.2", "g2")
    write(tmp_path, "app.log.5", "g5")
    write(tmp_path, "app.log.10", "g10")
    assert run(tmp_path, 2).returncode == 0
    names = sorted(p.name for p in tmp_path.iterdir())
    assert names == ["app.log", "app.log.1", "app.log.2"]
    assert (tmp_path / "app.log.1").read_text() == "now"
    assert (tmp_path / "app.log.2").read_text() == "g1"


def test_gaps_shift_without_filling(tmp_path):
    write(tmp_path, "app.log", "now")
    write(tmp_path, "app.log.1", "g1")
    write(tmp_path, "app.log.3", "g3")
    assert run(tmp_path, 5).returncode == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "app.log",
        "app.log.1",
        "app.log.2",
        "app.log.4",
    ]
    assert (tmp_path / "app.log.2").read_text() == "g1"
    assert (tmp_path / "app.log.4").read_text() == "g3"


def test_keep_one(tmp_path):
    write(tmp_path, "app.log", "now")
    write(tmp_path, "app.log.1", "old")
    assert run(tmp_path, 1).returncode == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == ["app.log", "app.log.1"]
    assert (tmp_path / "app.log.1").read_text() == "now"


def test_other_files_untouched(tmp_path):
    write(tmp_path, "app.log", "now")
    write(tmp_path, "app.log.2.gz", "zipped")
    write(tmp_path, "app.logs", "not a log")
    write(tmp_path, "notes.txt", "notes")
    (tmp_path / "sub").mkdir()
    write(tmp_path / "sub", "deep.log", "deep")
    (tmp_path / "dir.log").mkdir()
    proc = run(tmp_path, 1)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "rotated app.log\n"
    assert (tmp_path / "app.log.2.gz").read_text() == "zipped"
    assert (tmp_path / "app.logs").read_text() == "not a log"
    assert (tmp_path / "sub" / "deep.log").read_text() == "deep"
    assert not (tmp_path / "sub" / "deep.log.1").exists()
    assert (tmp_path / "dir.log").is_dir()


def test_names_with_spaces_and_glob_characters(tmp_path):
    write(tmp_path, "my app.log", "now")
    write(tmp_path, "my app.log.1", "g1")
    write(tmp_path, "w[1]*.log", "star")
    proc = run(tmp_path, 4)
    assert proc.returncode == 0, proc.stderr
    assert (tmp_path / "my app.log.1").read_text() == "now"
    assert (tmp_path / "my app.log.2").read_text() == "g1"
    assert (tmp_path / "w[1]*.log.1").read_text() == "star"
    assert sorted(proc.stdout.splitlines()) == [
        "rotated my app.log",
        "rotated w[1]*.log",
    ]


def test_content_is_preserved_exactly(tmp_path):
    payload = bytes(range(256)) * 3
    (tmp_path / "bin.log").write_bytes(payload)
    assert run(tmp_path, 2).returncode == 0
    assert (tmp_path / "bin.log.1").read_bytes() == payload


def test_running_twice_rotates_again(tmp_path):
    write(tmp_path, "app.log", "first")
    run(tmp_path, 3)
    write(tmp_path, "app.log", "second")
    run(tmp_path, 3)
    assert (tmp_path / "app.log.1").read_text() == "second"
    assert (tmp_path / "app.log.2").read_text() == "first"
    proc = run(tmp_path, 3)
    assert proc.stdout == ""
    assert proc.returncode == 0


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["DIR"],
        ["DIR", "3", "extra"],
        ["DIR", "0"],
        ["DIR", "-1"],
        ["DIR", "abc"],
        ["DIR", "1.5"],
        ["DIR", ""],
        ["MISSING", "3"],
        ["FILE", "3"],
    ],
)
def test_usage_errors(tmp_path, args):
    write(tmp_path, "app.log", "now")
    write(tmp_path, "plain.txt", "x")
    mapping = {
        "DIR": str(tmp_path),
        "MISSING": str(tmp_path / "nope"),
        "FILE": str(tmp_path / "plain.txt"),
    }
    before = snapshot(tmp_path)
    proc = run(*[mapping.get(a, a) for a in args])
    assert proc.returncode == 2
    assert proc.stderr.strip()
    assert proc.stdout == ""
    assert snapshot(tmp_path) == before
