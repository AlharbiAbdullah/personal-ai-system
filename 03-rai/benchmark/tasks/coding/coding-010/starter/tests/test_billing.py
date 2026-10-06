import pytest

from billing import compute_invoice


def test_starter_plan_with_overage_and_tax():
    invoice = compute_invoice(
        {"id": "c-1", "plan": "starter", "country": "DE"},
        [{"metric": "api_calls", "quantity": 12500}, {"metric": "storage_gb", "quantity": 12}],
        "2026-09",
    )
    assert invoice == {
        "customer": "c-1",
        "period": "2026-09",
        "lines": [
            {"item": "base", "cents": 900},
            {"item": "api_calls", "cents": 120},
            {"item": "storage", "cents": 40},
        ],
        "subtotal": 1060,
        "discount": 0,
        "tax": 201,
        "total": 1261,
    }


def test_pro_plan_second_tier_and_flat_discount():
    invoice = compute_invoice(
        {"id": "c-2", "plan": "pro", "country": "us", "discount_code": "flat5"},
        [{"metric": "api_calls", "quantity": 600000}],
        "2026-09",
    )
    assert invoice["lines"] == [{"item": "base", "cents": 4900}, {"item": "api_calls", "cents": 14000}]
    assert invoice["discount"] == 500
    assert invoice["total"] == 18400


def test_free_plan_limit():
    with pytest.raises(ValueError, match="free plan limit exceeded"):
        compute_invoice({"id": "c-3", "plan": "free"}, [{"metric": "api_calls", "quantity": 1001}], "2026-09")
