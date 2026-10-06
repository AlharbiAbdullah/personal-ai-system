import random
import re
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "colstats.sh"
NUM = re.compile(r"[+-]?[0-9]+(\.[0-9]+)?")
TWO_DECIMALS = re.compile(r"-?[0-9]+\.[0-9]{2}")


def run(*args):
    return subprocess.run(
        ["bash", str(SCRIPT), *map(str, args)],
        capture_output=True,
        check=False,
        text=True,
        timeout=20,
    )


def reference(text, column, delim=","):
    lines = [line.removesuffix("\r") for line in text.split("\n")]
    header = [cell.strip(" ") for cell in lines[0].split(delim)]
    idx = header.index(column)
    values, skipped = [], 0
    for line in lines[1:]:
        if line == "":
            continue
        cells = line.split(delim)
        cell = cells[idx].strip(" ") if idx < len(cells) else ""
        if NUM.fullmatch(cell):
            values.append(float(cell))
        else:
            skipped += 1
    return values, skipped


def parse(stdout):
    pairs = [line.split("=", 1) for line in stdout.splitlines()]
    return [k for k, _ in pairs], dict(pairs)


def assert_stats(proc, values, skipped):
    assert proc.returncode == 0, proc.stderr
    keys, got = parse(proc.stdout)
    assert got["count"] == str(len(values))
    assert got["skipped"] == str(skipped)
    if not values:
        assert keys == ["count", "skipped"]
        return
    assert keys == ["count", "sum", "min", "max", "mean", "skipped"]
    total = 0.0
    for v in values:
        total += v
    expected = {
        "sum": total,
        "min": min(values),
        "max": max(values),
        "mean": total / len(values),
    }
    for key, value in expected.items():
        assert TWO_DECIMALS.fullmatch(got[key]), (key, got[key])
        assert abs(float(got[key]) - value) <= 0.0051, (key, got[key], value)


def test_sample_style_file(tmp_path):
    text = "station, temp ,humidity\nn1,21.5,40\nn2, 19.25 ,n/a\ns1,,38\ns2,-3.5,41\ne1,22\n"
    f = tmp_path / "r.csv"
    f.write_text(text)
    proc = run(f, "temp")
    assert (
        proc.stdout
        == "count=4\nsum=59.25\nmin=-3.50\nmax=22.00\nmean=14.81\nskipped=1\n"
    )
    proc = run(f, "humidity")
    assert (
        proc.stdout
        == "count=3\nsum=119.00\nmin=38.00\nmax=41.00\nmean=39.67\nskipped=2\n"
    )


def test_numbers_compare_numerically_not_as_text(tmp_path):
    f = tmp_path / "n.csv"
    f.write_text("v\n9\n10\n100\n-20\n-3\n")
    assert (
        run(f, "v").stdout
        == "count=5\nsum=96.00\nmin=-20.00\nmax=100.00\nmean=19.20\nskipped=0\n"
    )


@pytest.mark.parametrize(
    "cell",
    ["1e3", ".5", "5.", "1,5", "abc", "--1", "+-2", "0x10", "inf", "nan", "1.2.3"],
)
def test_non_numeric_cells_are_skipped(tmp_path, cell):
    f = tmp_path / "x.csv"
    f.write_text(f"a;b\n1;{cell}\n2;4\n".replace(";", "\t"))
    proc = run("-d", "\t", f, "b")
    assert (
        proc.stdout == "count=1\nsum=4.00\nmin=4.00\nmax=4.00\nmean=4.00\nskipped=1\n"
    )


def test_signed_and_padded_numbers_count(tmp_path):
    f = tmp_path / "x.csv"
    f.write_text("a\n +3 \n-0.25\n007\n")
    assert (
        run(f, "a").stdout
        == "count=3\nsum=9.75\nmin=-0.25\nmax=7.00\nmean=3.25\nskipped=0\n"
    )


@pytest.mark.parametrize("seed", [5, 11, 99])
@pytest.mark.parametrize("delim", [",", ";", "|", "\t"])
def test_generated_files(tmp_path, seed, delim):
    rng = random.Random(seed)
    columns = ["id", "load", "temp", "load"]
    lines = [delim.join(f" {c} " if rng.random() < 0.3 else c for c in columns)]
    for i in range(300):
        cells = [str(i)]
        for _ in range(3):
            r = rng.random()
            if r < 0.1:
                cells.append("")
            elif r < 0.18:
                cells.append(rng.choice(["n/a", "1e2", "x", ".5", "-"]))
            else:
                cells.append(f"{rng.uniform(-500, 500):.{rng.choice([0, 1, 2, 3])}f}")
        if rng.random() < 0.05:
            cells = cells[:2]
        lines.append(delim.join(cells))
        if rng.random() < 0.03:
            lines.append("")
    text = "\n".join(lines) + "\n"
    f = tmp_path / "gen.txt"
    f.write_text(text)
    args = [f] if delim == "," else ["-d", delim, f]
    for column in ["load", "temp"]:
        values, skipped = reference(text, column, delim)
        assert_stats(run(*args, column), values, skipped)


def test_crlf_line_endings(tmp_path):
    f = tmp_path / "w.csv"
    f.write_bytes(b"name,score\r\nann,10\r\nbob,\r\n\r\ncy,2.5\r\n")
    assert (
        run(f, "score").stdout
        == "count=2\nsum=12.50\nmin=2.50\nmax=10.00\nmean=6.25\nskipped=1\n"
    )


def test_first_of_duplicate_headers_wins(tmp_path):
    f = tmp_path / "d.csv"
    f.write_text("x,x\n1,100\n2,200\n")
    assert run(f, "x").stdout.splitlines()[1] == "sum=3.00"


def test_no_numeric_values(tmp_path):
    f = tmp_path / "e.csv"
    f.write_text("a,b\n1,\n2,n/a\n")
    proc = run(f, "b")
    assert proc.returncode == 0
    assert proc.stdout == "count=0\nskipped=2\n"
    f.write_text("a,b\n")
    assert run(f, "b").stdout == "count=0\nskipped=0\n"


def test_column_not_found(tmp_path):
    f = tmp_path / "c.csv"
    f.write_text("a,b\n1,2\n")
    proc = run(f, "zzz")
    assert proc.returncode == 3
    assert "column not found: zzz" in proc.stderr
    assert proc.stdout == ""


@pytest.mark.parametrize(
    "case",
    [
        "no-args",
        "one-arg",
        "three-args",
        "missing-file",
        "empty-file",
        "long-delim",
        "bad-option",
    ],
)
def test_usage_errors(tmp_path, case):
    f = tmp_path / "ok.csv"
    f.write_text("a\n1\n")
    empty = tmp_path / "empty.csv"
    empty.write_text("")
    args = {
        "no-args": [],
        "one-arg": [f],
        "three-args": [f, "a", "b"],
        "missing-file": [tmp_path / "nope.csv", "a"],
        "empty-file": [empty, "a"],
        "long-delim": ["-d", ";;", f, "a"],
        "bad-option": ["-z", f, "a"],
    }[case]
    proc = run(*args)
    assert proc.returncode == 2
    assert proc.stderr.strip()
