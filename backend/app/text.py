from __future__ import annotations

import re
from typing import Optional


def squash(s: str) -> str:
    """Collapse every run of whitespace to one space. Used for quote checking only."""
    return re.sub(r"\s+", " ", s).strip()


def is_exact_quote(text: str, quote: Optional[str]) -> bool:
    """True when `quote` appears word for word in `text` (ignoring line breaks and spacing)."""
    if not quote:
        return False
    q = squash(quote)
    return bool(q) and q in squash(text)


def number_in_quote(quote: str, printed: str) -> bool:
    """Does this number, as printed ('12,000', '0.5'), appear as a whole number in the quote?"""
    pattern = r"(^|[^\d.,])" + re.escape(printed) + r"(?!\d|[.,]\d)"
    return re.search(pattern, quote) is not None
