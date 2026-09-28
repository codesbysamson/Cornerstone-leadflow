"""The Decimal money layer in isolation.

The floating-point trap these guards exist to prevent: 0.1 + 0.2 is
0.30000000000000004 in IEEE-754, so a single float rounding error becomes a
permanent, wrong figure in a customer-facing quotation.
"""

from decimal import Decimal

import pytest

from app.money import (
    MAX_MONEY,
    MoneyError,
    line_total,
    parse_money,
    parse_quantity,
    quantize,
    sum_money,
    to_decimal,
)


def test_decimal_sum_is_exact_where_float_is_not() -> None:
    assert sum_money([Decimal("0.10"), Decimal("0.20")]) == Decimal("0.30")
    assert 0.1 + 0.2 != 0.3  # the reason Decimal is used at all


def test_ten_tenths_sum_exactly_to_one() -> None:
    assert sum_money([Decimal("0.10")] * 10) == Decimal("1.00")


@pytest.mark.parametrize(
    ("value", "expected"),
    [("0.125", "0.13"), ("0.135", "0.14"), ("0.025", "0.03"), ("1.005", "1.01")],
)
def test_quantize_rounds_half_up(value: str, expected: str) -> None:
    """Half-up, not the banker's rounding Decimal applies by default.

    Banker's rounding would turn 0.125 into 0.12, which is not what a
    quotation is expected to do.
    """
    assert quantize(Decimal(value)) == Decimal(expected)


def test_line_total_rounds_half_up() -> None:
    assert line_total(Decimal("0.10"), Decimal("0.25")) == Decimal("0.03")


def test_line_total_is_exact_for_ordinary_values() -> None:
    assert line_total(Decimal("3"), Decimal("19.99")) == Decimal("59.97")
    assert line_total(Decimal("2.5"), Decimal("40")) == Decimal("100.00")


def test_negative_money_is_rejected() -> None:
    with pytest.raises(MoneyError, match="cannot be negative"):
        parse_money(Decimal("-0.01"), field="unit price")


def test_zero_money_is_allowed_by_default() -> None:
    assert parse_money(Decimal("0"), field="unit price") == Decimal("0.00")


def test_zero_money_can_be_disallowed() -> None:
    with pytest.raises(MoneyError, match="greater than zero"):
        parse_money(Decimal("0"), field="discount", allow_zero=False)


def test_zero_and_negative_quantity_is_rejected() -> None:
    with pytest.raises(MoneyError, match="greater than zero"):
        parse_quantity(Decimal("0"))
    with pytest.raises(MoneyError, match="greater than zero"):
        parse_quantity(Decimal("-2"))


def test_oversized_money_is_rejected() -> None:
    with pytest.raises(MoneyError, match="too large"):
        parse_money(MAX_MONEY + Decimal("1"), field="unit price")


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_values_are_rejected(value: str) -> None:
    with pytest.raises(MoneyError, match="not a valid number"):
        to_decimal(value, field="unit price")


def test_non_numeric_value_is_rejected() -> None:
    with pytest.raises(MoneyError, match="not a valid number"):
        to_decimal("not a number", field="unit price")


def test_float_input_is_converted_without_binary_error() -> None:
    """A float that reached us as JSON is read via its shortest repr."""
    assert to_decimal(0.1, field="unit price") == Decimal("0.1")


def test_results_are_decimal_instances() -> None:
    assert isinstance(parse_money("19.99", field="unit price"), Decimal)
    assert isinstance(parse_quantity("2.5"), Decimal)
    assert isinstance(quantize(Decimal("1.005")), Decimal)
