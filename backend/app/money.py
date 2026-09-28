"""Money handling for quotations.

All monetary arithmetic uses ``decimal.Decimal``. Binary floating point is
never used for a value that is persisted, because 0.1 + 0.2 is
0.30000000000000004 in IEEE-754 and that error would be baked permanently into
the stored subtotal, the stored discount and the stored total.

Amounts are persisted as ``NUMERIC(12, 2)`` — exact decimal in PostgreSQL, and
exact in the SQLite test database too. Rounding is half-up, which is what a
quotation is expected to do, rather than the banker's rounding that
``Decimal.quantize`` applies by default.
"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

#: The canonical scale for money. GBP, USD and NGN all use two decimal places.
MONEY_SCALE = Decimal("0.01")

#: Guards against absurd values reaching the database. NUMERIC(12, 2) allows
#: ten integer digits, so this sits comfortably inside the column.
MAX_MONEY = Decimal("9999999999.99")
MAX_QUANTITY = Decimal("99999999.99")


class MoneyError(ValueError):
    """A monetary value or a derived total is not acceptable."""


def to_decimal(value: object, *, field: str) -> Decimal:
    """Coerces to Decimal and rejects NaN/Infinity.

    ``float('nan')`` would otherwise sail through numeric comparisons and
    poison every total it touched.
    """
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise MoneyError(f"{field} is not a valid number") from exc

    if not result.is_finite():
        raise MoneyError(f"{field} is not a valid number")
    return result


def quantize(value: Decimal) -> Decimal:
    """Rounds to the money scale, half-up."""
    return value.quantize(MONEY_SCALE, rounding=ROUND_HALF_UP)


def parse_money(value: object, *, field: str, allow_zero: bool = True) -> Decimal:
    """Validates and normalises a single monetary amount."""
    amount = to_decimal(value, field=field)

    if amount < 0:
        raise MoneyError(f"{field} cannot be negative")
    if not allow_zero and amount == 0:
        raise MoneyError(f"{field} must be greater than zero")
    if amount > MAX_MONEY:
        raise MoneyError(f"{field} is too large")

    return quantize(amount)


def parse_quantity(value: object, *, field: str = "quantity") -> Decimal:
    """Validates a line-item quantity. Must be strictly positive.

    Quantities are decimal rather than integer so a quote can bill fractional
    hours or a part-clean.
    """
    amount = to_decimal(value, field=field)

    if amount <= 0:
        raise MoneyError(f"{field} must be greater than zero")
    if amount > MAX_QUANTITY:
        raise MoneyError(f"{field} is too large")

    return quantize(amount)


def line_total(quantity: Decimal, unit_price: Decimal) -> Decimal:
    """Authoritative line total, rounded to the money scale exactly once."""
    return quantize(quantity * unit_price)


def sum_money(amounts: list[Decimal]) -> Decimal:
    total = sum(amounts, Decimal("0"))
    return quantize(total)
