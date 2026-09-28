from __future__ import annotations

import pytest
from helpers import tipcalc


@pytest.mark.spec("config.percent-empty")
@pytest.mark.xfail(
    strict=True, reason="config.percent-empty: traceback today (gap entrypoint-hardening)"
)
def test_percent_empty() -> None:
    r = tipcalc("100", env={"TIPCALC_DEFAULT_PERCENT": ""})
    assert "Traceback" not in r.stderr


@pytest.mark.spec("config.percent-invalid")
@pytest.mark.xfail(
    strict=True, reason="config.percent-invalid: traceback today (gap entrypoint-hardening)"
)
def test_percent_invalid() -> None:
    r = tipcalc("100", env={"TIPCALC_DEFAULT_PERCENT": "abc"})
    assert "Traceback" not in r.stderr
    assert r.returncode != 0
