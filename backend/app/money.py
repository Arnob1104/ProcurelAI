"""Exact decimal maths. Floats are never used for money or percentages."""
from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal, getcontext
from typing import Optional

getcontext().prec = 40
getcontext().rounding = ROUND_HALF_UP

_NUM = re.compile(r"^-?\d+(\.\d+)?$")


def D(v) -> Decimal:
    return Decimal(str(v))


def parse_number(text) -> Optional[Decimal]:
    """Parse '5,664,000.00', '12,000' or '0.5'. None if it is not a plain number."""
    if text is None:
        return None
    cleaned = str(text).strip().replace(",", "")
    return Decimal(cleaned) if _NUM.match(cleaned) else None


def _quant(d: Decimal, dp: int) -> Decimal:
    return d.quantize(Decimal(1).scaleb(-dp), rounding=ROUND_HALF_UP)


def fmt(d: Decimal, dp: int = 2) -> str:
    """12345.6 -> '12,345.60'."""
    return f"{_quant(d, dp):,.{dp}f}"


def dp2(d: Decimal) -> str:
    """Two decimal places with trailing zeros trimmed: 2.3100 -> '2.31', -17.50 -> '-17.5'."""
    s = f"{_quant(d, 2):f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def num_str(d: Decimal) -> str:
    """Plain string without exponent or trailing zeros: Decimal('28') -> '28', Decimal('0.50') -> '0.5'."""
    s = f"{d.normalize():f}"
    return s


def same_money(a: Decimal, b: Decimal) -> bool:
    """Equal within one paisa (rounding on printed documents)."""
    return abs(a - b) <= Decimal("0.01")
