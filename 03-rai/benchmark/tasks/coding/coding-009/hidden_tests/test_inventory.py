from datetime import date
from decimal import Decimal

import pytest
from inventory import InsufficientStock, Item, Ledger, Movement
from inventory.report import low_stock, movement_summary
from inventory.valuation import average_cost, stock_value

D1, D2, D3, D4 = date(2026, 3, 1), date(2026, 3, 2), date(2026, 3, 3), date(2026, 3, 4)


def m_in(sku, qty, on, cost):
    return Movement(sku, qty, "in", on, Decimal(cost))


def m_out(sku, qty, on):
    return Movement(sku, qty, "out", on)


def test_two_ledgers_never_share_movements():
    first = Ledger()
    first.record(m_in("A", 5, D1, "1.00"))
    second = Ledger()
    assert second.movements == []
    assert second.stock_on_hand("A", D4) == 0
    third = Ledger()
    third.record(m_in("B", 1, D1, "1.00"))
    assert [m.sku for m in first.movements] == ["A"]


def test_initial_movements_are_copied():
    initial = [m_in("A", 5, D1, "1.00")]
    ledger = Ledger(initial)
    ledger.record(m_in("A", 2, D2, "1.00"))
    assert len(initial) == 1
    assert ledger.stock_on_hand("A", D2) == 7


def test_movements_on_the_query_date_count():
    ledger = Ledger()
    ledger.record(m_in("A", 10, D2, "1.00"))
    assert ledger.stock_on_hand("A", D1) == 0
    assert ledger.stock_on_hand("A", D2) == 10
    ledger.record(m_out("A", 4, D2))
    assert ledger.stock_on_hand("A", D2) == 6
    assert ledger.stock_on_hand("A", D3) == 6


def test_same_day_delivery_allows_same_day_shipment():
    ledger = Ledger()
    ledger.record(m_in("A", 3, D3, "2.00"))
    ledger.record(m_out("A", 3, D3))
    assert ledger.stock_on_hand("A", D3) == 0


def test_insufficient_stock():
    ledger = Ledger()
    ledger.record(m_in("A", 3, D2, "2.00"))
    with pytest.raises(InsufficientStock):
        ledger.record(m_out("A", 4, D2))
    with pytest.raises(InsufficientStock):
        ledger.record(m_out("A", 1, D1))
    assert len(ledger.movements) == 1


@pytest.mark.parametrize(
    "movement",
    [
        Movement("A", 0, "in", D1, Decimal(1)),
        Movement("A", -2, "out", D1),
        Movement("A", 1, "lost", D1),
        Movement("A", 1, "in", D1),
    ],
)
def test_record_validation(movement):
    with pytest.raises(ValueError):
        Ledger().record(movement)


def test_average_cost_is_weighted_by_quantity():
    ledger = Ledger()
    ledger.record(m_in("A", 10, D1, "2.00"))
    ledger.record(m_in("A", 30, D2, "3.00"))
    ledger.record(m_in("A", 60, D4, "9.00"))
    assert average_cost(ledger, "A", D3) == Decimal("2.75")
    assert str(average_cost(ledger, "A", D1)) == "2.00"
    assert average_cost(ledger, "A", D4) == Decimal("6.50")


def test_average_cost_rounds_half_up_exactly():
    ledger = Ledger()
    ledger.record(m_in("A", 1, D1, "2.675"))
    assert str(average_cost(ledger, "A", D1)) == "2.68"
    ledger.record(m_in("B", 1, D1, "1.00"))
    ledger.record(m_in("B", 1, D1, "1.01"))
    assert str(average_cost(ledger, "B", D1)) == "1.01"
    ledger.record(m_in("C", 2, D1, "0.10"))
    ledger.record(m_in("C", 1, D1, "0.20"))
    assert str(average_cost(ledger, "C", D1)) == "0.13"


def test_average_cost_without_deliveries():
    ledger = Ledger()
    ledger.record(m_in("A", 1, D2, "1.00"))
    with pytest.raises(KeyError):
        average_cost(ledger, "A", D1)
    with pytest.raises(KeyError):
        average_cost(ledger, "Z", D4)


def test_stock_value():
    ledger = Ledger()
    ledger.record(m_in("A", 3, D1, "0.10"))
    assert str(stock_value(ledger, "A", D1)) == "0.30"
    ledger.record(m_in("A", 1, D2, "0.20"))
    ledger.record(m_out("A", 2, D2))
    # average (0.30 + 0.20) / 4 = 0.125 -> 0.13; 2 on hand -> 0.26
    assert str(stock_value(ledger, "A", D2)) == "0.26"
    ledger.record(m_out("A", 2, D3))
    assert stock_value(ledger, "A", D3) == Decimal("0.00")
    assert stock_value(ledger, "Z", D3) == Decimal("0.00")


def test_low_stock_includes_threshold_and_sorts_by_stock():
    ledger = Ledger()
    for sku, qty in [("D", 5), ("C", 2), ("B", 7), ("A", 2), ("E", 9)]:
        ledger.record(m_in(sku, qty, D1, "1.00"))
    ledger.record(m_out("E", 4, D2))
    items = [Item(sku, sku.lower()) for sku in "ABCDEF"]
    assert low_stock(ledger, items, 5, D2) == [
        ("F", 0),
        ("A", 2),
        ("C", 2),
        ("D", 5),
        ("E", 5),
    ]
    assert low_stock(ledger, items, 5, D1) == [("F", 0), ("A", 2), ("C", 2), ("D", 5)]
    assert low_stock(ledger, items, 0, D2) == [("F", 0)]


def test_movement_summary_window_is_inclusive():
    ledger = Ledger()
    ledger.record(m_in("A", 5, D1, "1.00"))
    ledger.record(m_in("A", 5, D2, "1.00"))
    ledger.record(m_out("A", 3, D3))
    ledger.record(m_in("B", 1, D4, "1.00"))
    assert movement_summary(ledger, D2, D3) == {"A": (5, 3)}
    assert movement_summary(ledger, D1, D4) == {"A": (10, 3), "B": (1, 0)}
    assert movement_summary(ledger, D4, D4) == {"B": (1, 0)}
    assert len(ledger.movements_between(D1, D2)) == 2
