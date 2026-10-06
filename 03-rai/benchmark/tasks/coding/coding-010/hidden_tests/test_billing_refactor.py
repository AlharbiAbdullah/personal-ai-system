import importlib
import random
from pathlib import Path

import legacy_reference
import pytest

ROOT = Path(__file__).resolve().parent.parent


def outcome(fn, *args):
    try:
        return ("ok", fn(*args))
    except Exception as exc:  # noqa: BLE001 - behaviour includes the errors raised
        return ("error", type(exc).__name__, str(exc))


def random_case(rng):
    plan = rng.choice(
        ["free", "free", "starter", "starter", "pro", "pro", "pro", "gold", "Pro", ""]
    )
    customer = {"id": f"c-{rng.randrange(1000)}", "plan": plan}
    if rng.random() < 0.9:
        customer["country"] = rng.choice(
            ["DE", "de", " fr ", "GB", "NL", "nl", "SA", "US", "", "BR"]
        )
    if rng.random() < 0.7:
        customer["discount_code"] = rng.choice(
            [
                None,
                "",
                "WELCOME10",
                " welcome10 ",
                "PRO20",
                "pro20",
                "FLAT5",
                "flat100",
                "FLAT0",
                "FLAT",
                "FLATX",
                "SPRING",
                "FLAT99999",
            ]
        )
    usage = []
    for _ in range(rng.randrange(0, 5)):
        metric = rng.choice(
            ["api_calls", "api_calls", "storage_gb", "storage_gb", "bandwidth"]
            if rng.random() < 0.1
            else ["api_calls", "storage_gb"]
        )
        if metric == "api_calls":
            quantity = rng.choice(
                [
                    rng.randrange(0, 1500),
                    rng.randrange(0, 30000),
                    rng.randrange(90000, 700000),
                    rng.randrange(0, 1_600_000),
                ]
            )
        else:
            quantity = rng.randrange(0, 900)
        usage.append({"metric": metric, "quantity": quantity})
    return customer, usage, f"2026-{rng.randrange(1, 13):02d}"


def test_billing_is_a_package():
    billing = importlib.import_module("billing")
    assert hasattr(billing, "__path__"), (
        "billing must be a package (billing/__init__.py)"
    )
    for name in ("plans", "discounts", "tax", "invoice"):
        importlib.import_module(f"billing.{name}")


def test_public_entry_points_agree():
    from billing import compute_invoice
    from billing.invoice import compute_invoice as from_module

    customer = {"id": "c", "plan": "pro", "country": "NL", "discount_code": "PRO20"}
    usage = [
        {"metric": "api_calls", "quantity": 123456},
        {"metric": "storage_gb", "quantity": 150},
    ]
    assert compute_invoice(customer, usage, "2026-01") == from_module(
        customer, usage, "2026-01"
    )


@pytest.mark.parametrize("seed", range(6))
def test_behaviour_is_unchanged_for_existing_inputs(seed):
    from billing import compute_invoice

    rng = random.Random(seed)
    for _ in range(250):
        customer, usage, period = random_case(rng)
        expected = outcome(
            legacy_reference.compute_invoice,
            dict(customer),
            [dict(u) for u in usage],
            period,
        )
        got = outcome(compute_invoice, dict(customer), [dict(u) for u in usage], period)
        assert got == expected, (customer, usage)


@pytest.mark.parametrize(
    "subtotal_usage",
    [
        [{"metric": "api_calls", "quantity": 10500}],  # starter: 900 + 40 = 940
        [{"metric": "storage_gb", "quantity": 15}],  # starter: 900 + 100 = 1000
        [
            {"metric": "api_calls", "quantity": 25000},
            {"metric": "storage_gb", "quantity": 11},
        ],
    ],
)
@pytest.mark.parametrize("code", ["WELCOME10", "FLAT3", None])
@pytest.mark.parametrize("country", ["DE", "FR", "NL", "SA", "US"])
def test_rounding_quirks_are_preserved(subtotal_usage, code, country):
    from billing import compute_invoice

    customer = {"id": "q", "plan": "starter", "country": country, "discount_code": code}
    assert compute_invoice(
        customer, subtotal_usage, "2026-02"
    ) == legacy_reference.compute_invoice(customer, subtotal_usage, "2026-02")


def test_error_order_is_preserved():
    from billing import compute_invoice

    cases = [
        (
            {"id": "e", "plan": "gold", "discount_code": "NOPE"},
            [{"metric": "bandwidth", "quantity": 1}],
        ),
        ({"id": "e", "plan": "gold", "discount_code": "NOPE"}, []),
        (
            {"id": "e", "plan": "free", "discount_code": "NOPE"},
            [{"metric": "api_calls", "quantity": 5000}],
        ),
        ({"id": "e", "plan": "free", "discount_code": "nope"}, []),
    ]
    messages = [
        "unknown metric: bandwidth",
        "unknown plan: gold",
        "free plan limit exceeded",
        "unknown discount code: NOPE",
    ]
    for (customer, usage), message in zip(cases, messages):
        with pytest.raises(ValueError) as err:
            compute_invoice(customer, usage, "2026-03")
        assert str(err.value) == message


def test_plan_registry():
    from billing.plans import get_plan

    assert get_plan("starter").base_cents == 900
    assert get_plan("pro").base_cents == 4900
    assert get_plan("free").base_cents == 0
    assert get_plan("enterprise").base_cents == 25000
    assert get_plan("pro").charges(600000, 101) == (14000, 15)
    assert get_plan("starter").charges(10001, 10) == (40, 0)
    assert get_plan("free").charges(1000, 3) == (0, 50)
    with pytest.raises(ValueError, match="free plan limit exceeded"):
        get_plan("free").charges(1001, 0)
    with pytest.raises(ValueError) as err:
        get_plan("platinum")
    assert str(err.value) == "unknown plan: platinum"


def test_discount_and_tax_helpers():
    from billing.discounts import discount_cents
    from billing.tax import tax_rate

    assert discount_cents(None, "pro", 1000) == 0
    assert discount_cents("", "pro", 1000) == 0
    assert discount_cents(" welcome10 ", "starter", 1005) == round(1005 * 0.10)
    assert discount_cents("PRO20", "starter", 1000) == 0
    assert discount_cents("PRO20", "pro", 1000) == 200
    assert discount_cents("PRO20", "enterprise", 1000) == 200
    assert discount_cents("FLAT12", "free", 500) == 500
    with pytest.raises(ValueError) as err:
        discount_cents("summer", "pro", 1000)
    assert str(err.value) == "unknown discount code: SUMMER"
    assert tax_rate("de") == 0.19
    assert tax_rate(" gb ") == 0.20
    assert tax_rate("SA") == 0.15
    assert tax_rate("JP") == 0.0


@pytest.mark.parametrize(
    "usage,code,country,expected",
    [
        (
            [
                {"metric": "api_calls", "quantity": 1_000_000},
                {"metric": "storage_gb", "quantity": 500},
            ],
            None,
            "US",
            {
                "lines": [{"item": "base", "cents": 25000}],
                "subtotal": 25000,
                "discount": 0,
                "tax": 0,
                "total": 25000,
            },
        ),
        (
            [
                {"metric": "api_calls", "quantity": 1_000_001},
                {"metric": "storage_gb", "quantity": 501},
            ],
            None,
            "US",
            {
                "lines": [
                    {"item": "base", "cents": 25000},
                    {"item": "api_calls", "cents": 10},
                    {"item": "storage", "cents": 10},
                ],
                "subtotal": 25020,
                "discount": 0,
                "tax": 0,
                "total": 25020,
            },
        ),
        (
            [
                {"metric": "api_calls", "quantity": 2_000_000},
                {"metric": "api_calls", "quantity": 500_000},
                {"metric": "storage_gb", "quantity": 800},
            ],
            "pro20",
            "DE",
            {
                "lines": [
                    {"item": "base", "cents": 25000},
                    {"item": "api_calls", "cents": 15000},
                    {"item": "storage", "cents": 3000},
                ],
                "subtotal": 43000,
                "discount": 8600,
                "tax": 6536,
                "total": 40936,
            },
        ),
        (
            [{"metric": "api_calls", "quantity": 1_234_567}],
            "WELCOME10",
            "SA",
            {
                "lines": [
                    {"item": "base", "cents": 25000},
                    {"item": "api_calls", "cents": 2350},
                ],
                "subtotal": 27350,
                "discount": 2735,
                "tax": 3692,
                "total": 28307,
            },
        ),
    ],
)
def test_enterprise_plan(usage, code, country, expected):
    from billing import compute_invoice

    customer = {"id": "big", "plan": "enterprise", "country": country}
    if code is not None:
        customer["discount_code"] = code
    assert compute_invoice(customer, usage, "2026-10") == {
        "customer": "big",
        "period": "2026-10",
        **expected,
    }
