"""The runner: a check can never crash, hang or silently pass the whole run."""

import json
import time

import pytest

import sanity
from sanity_checks import core
from sanity_checks.core import FAIL, PASS, R, SKIP, WARN


def _entry(fn, role="shared", slow=False, sub="Vault"):
    return ("T-1", sub, role, slow, fn)


def test_raising_check_reports_fail():
    def boom():
        raise RuntimeError("kaput")
    r = sanity.run_one(_entry(boom), False, "producer")
    assert r.status == FAIL and "RuntimeError" in r.evidence and "kaput" in r.evidence


def test_hung_check_times_out_as_fail():
    def hang():
        time.sleep(5)
        return PASS, "late", ""
    t0 = time.time()
    r = sanity.run_one(_entry(hang), False, "producer", timeout=0.2)
    assert r.status == FAIL and "timed out" in r.evidence
    assert time.time() - t0 < 2


def test_malformed_result_reports_fail():
    r = sanity.run_one(_entry(lambda: ("MAYBE", "x")), False, "producer")
    assert r.status == FAIL and "malformed" in r.evidence


def test_role_and_quick_skips():
    ok = lambda: (PASS, "fine", "")  # noqa: E731
    assert sanity.run_one(_entry(ok, role="consumer"), False, "producer").status == SKIP
    assert sanity.run_one(_entry(ok, slow=True), True, "producer").status == SKIP
    assert sanity.run_one(_entry(ok, slow=True), False, "producer").status == PASS


def test_report_groups_each_subsystem_once(monkeypatch):
    fake = [("A-1", "Identity", "shared", False, lambda: (PASS, "", "")),
            ("B-1", "Stores", "shared", False, lambda: (PASS, "", "")),
            ("A-2", "Identity", "shared", False, lambda: (PASS, "", "")),
            ("B-2", "Stores", "shared", False, lambda: (PASS, "", ""))]
    monkeypatch.setattr(sanity, "CHECKS", fake)
    order = [r.id for r in sanity.run(False, "producer")]
    assert order == ["B-1", "B-2", "A-1", "A-2"]  # Stores precedes Identity, registration order kept


@pytest.mark.parametrize("rows,want", [
    ([R("X", "Vault", "shared", PASS)], "HEALTHY"),
    ([R("X", "Vault", "shared", WARN)] * 2, "HEALTHY"),
    ([R("X", "Vault", "shared", WARN)] * 3, "DEGRADED"),
    ([R("X", "Vault", "shared", FAIL)], "DEGRADED"),
    ([R("X", "Pipeline", "shared", FAIL)], "BROKEN"),
])
def test_verdict_tiers(rows, want):
    assert sanity.verdict(rows)[0] == want


def test_every_check_id_is_unique():
    ids = [e[0] for e in core.CHECKS]
    assert len(ids) == len(set(ids))


def test_every_subsystem_is_ordered():
    assert {e[1] for e in core.CHECKS} <= set(core.SUBSYSTEM_ORDER)


def test_write_status_names_fails_and_warns(w):
    rows = [R("A-1", "Pipeline", "shared", FAIL, "dead"), R("B-1", "Vault", "shared", WARN, "meh"),
            R("C-1", "Vault", "shared", PASS, "ok")]
    sanity.write_status("BROKEN", rows, "producer")
    s = json.loads(core.P.STATUS_FILE.read_text())
    assert s["verdict"] == "BROKEN" and s["role"] == "producer" and s["ts"]
    assert s["counts"] == {"PASS": 1, "WARN": 1, "FAIL": 1, "SKIP": 0}
    assert [f["id"] for f in s["fails"]] == ["A-1"] and [x["id"] for x in s["warns"]] == ["B-1"]


def test_list_prints_every_check(capsys):
    sanity.print_catalog()
    out = capsys.readouterr().out
    for cid, *_ in core.CHECKS:
        assert cid in out


# the weekly baseline refresh behind --write-status ────────────────────────────
def _baseline(w, days_old):
    from datetime import datetime, timedelta
    w.json("helm/03-rai/.sanity-baseline.json",
           {"md_count": 1, "written": (datetime.now() - timedelta(days=days_old)).isoformat(timespec="seconds")})


def _rows(data3=PASS, pipe3=PASS):
    return [R("DATA-3", "Data safety", "shared", data3), R("PIPE-3", "Pipeline", "producer", pipe3)]


def _written(w):
    return json.loads(w.path("helm/03-rai/.sanity-baseline.json").read_text())["written"][:10]


def test_baseline_refreshed_when_stale_and_clean(w):
    from datetime import date
    w.chroma({"rai-semantic": [{"a": 1}]})
    _baseline(w, 10)
    assert sanity.refresh_baseline(_rows()) is True
    assert _written(w) == date.today().isoformat()


def test_baseline_kept_while_a_drop_is_warning(w):
    w.chroma({"rai-semantic": [{"a": 1}]})
    _baseline(w, 10)
    assert sanity.refresh_baseline(_rows(data3=WARN)) is False
    assert sanity.refresh_baseline(_rows(pipe3=WARN)) is False


def test_baseline_kept_when_recent(w):
    w.chroma({"rai-semantic": [{"a": 1}]})
    _baseline(w, 2)
    assert sanity.refresh_baseline(_rows()) is False


def test_baseline_written_when_missing(w):
    w.chroma({"rai-semantic": [{"a": 1}]})
    assert sanity.refresh_baseline(_rows(data3=WARN)) is True
    assert w.path("helm/03-rai/.sanity-baseline.json").exists()


def test_every_check_says_what_it_asserts():
    """--list is the catalog the docs point at, so every check carries a docstring."""
    assert [cid for cid, *_, fn in core.CHECKS if not (fn.__doc__ or "").strip()] == []
