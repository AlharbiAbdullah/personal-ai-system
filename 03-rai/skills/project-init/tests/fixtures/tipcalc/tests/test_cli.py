from __future__ import annotations

import pytest
from helpers import tipcalc


@pytest.mark.spec("cli.tip-default")
def test_tip_default() -> None:
    r = tipcalc("100")
    assert r.returncode == 0
    assert r.stdout == "tip: 15.0\n"


@pytest.mark.spec("cli.no-args")
@pytest.mark.xfail(strict=True, reason="cli.no-args: traceback today (gap entrypoint-hardening)")
def test_no_args() -> None:
    r = tipcalc()
    assert "Traceback" not in r.stderr
    assert r.returncode != 0


@pytest.mark.spec("cli.help")
@pytest.mark.xfail(strict=True, reason="cli.help: traceback today (gap entrypoint-hardening)")
def test_help() -> None:
    r = tipcalc("--help")
    assert "Traceback" not in r.stderr
    assert r.returncode == 0


@pytest.mark.spec("cli.bad-amount")
@pytest.mark.xfail(strict=True, reason="cli.bad-amount: traceback today (gap entrypoint-hardening)")
def test_bad_amount() -> None:
    r = tipcalc("abc")
    assert "Traceback" not in r.stderr
    assert r.returncode != 0
