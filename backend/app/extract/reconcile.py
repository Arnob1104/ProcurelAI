"""Step: verify. Every value must have a quote that appears word for word in the document.
When the AI and the fixed reader disagree, the field is left empty and a person is asked."""
from __future__ import annotations

import re
from typing import Any, Callable, Optional

from ..models import QuoteFields, Sourced, Uncertainty
from ..money import parse_number
from ..text import is_exact_quote, number_in_quote, squash

STR_KEYS = [
    "supplier_name", "quotation_no", "quote_date", "pr_reference", "tin", "bin",
    "subtotal", "vat_rate", "vat_amount", "total", "advance_percent",
    "payment_min_days", "payment_max_days", "delivery_amount", "delivery_unit",
    "penalty_percent", "penalty_period", "penalty_basis", "penalty_clause", "validity_days",
]
BOOL_KEYS = ["vat_included", "payment_unclear"]
NUMERIC = {
    "subtotal", "vat_rate", "vat_amount", "total", "advance_percent",
    "payment_min_days", "payment_max_days", "delivery_amount", "penalty_percent", "validity_days",
}
LABEL = {
    "supplier_name": "supplier name", "quotation_no": "quotation number", "quote_date": "quotation date",
    "pr_reference": "purchase request reference", "tin": "TIN", "bin": "BIN", "subtotal": "subtotal",
    "vat_rate": "VAT rate", "vat_amount": "VAT amount", "total": "total", "advance_percent": "advance payment",
    "payment_min_days": "payment days (shortest)", "payment_max_days": "payment days (longest)",
    "delivery_amount": "delivery time", "delivery_unit": "delivery time unit", "penalty_percent": "penalty percent",
    "penalty_period": "penalty period", "penalty_basis": "penalty basis", "penalty_clause": "late-delivery clause",
    "validity_days": "validity", "vat_included": "VAT included flag", "payment_unclear": "payment wording",
}


def _value_supported_by_quote(key: str, value: str, quote: str) -> bool:
    """Does the claimed value really appear in the quote it points to?"""
    if key == "advance_percent" and value == "0":
        return re.search(r"no advance|nil advance|without advance", quote, re.I) is not None
    if key == "delivery_unit":
        return re.search(re.sub(r"s$", "", value), quote, re.I) is not None
    if key == "penalty_clause":
        return squash(quote) == squash(value)
    if key in NUMERIC:
        return number_in_quote(quote, value)
    return squash(value).lower() in squash(quote).lower()


def _same_value(key: str, a: str, b: str) -> bool:
    if key in NUMERIC:
        x, y = parse_number(a), parse_number(b)
        return x is not None and y is not None and x == y
    return squash(a).lower() == squash(b).lower()


def reconcile(text: str, rules: QuoteFields, ai: Optional[QuoteFields]) -> tuple[QuoteFields, list[Uncertainty]]:
    out = QuoteFields()
    unc: list[Uncertainty] = []

    def check(key: str, c: Optional[Sourced], who: str, value_ok: Callable[[Sourced], bool]) -> Optional[Sourced]:
        if c is None:
            return None
        if not is_exact_quote(text, c.quote):
            unc.append(Uncertainty(
                field=LABEL.get(key, key),
                reason=f"The {who} gave a quote that is not in the document, so it was ignored.",
                quote=c.quote,
            ))
            return None
        if not value_ok(c):
            unc.append(Uncertainty(
                field=LABEL.get(key, key),
                reason=f"The {who} gave a value that is not in its own quote, so it was ignored.",
                quote=c.quote,
            ))
            return None
        return c

    for key in STR_KEYS:
        r = check(key, getattr(rules, key), "fixed reader", lambda c, k=key: _value_supported_by_quote(k, c.value, c.quote))
        a = check(key, getattr(ai, key) if ai else None, "AI", lambda c, k=key: _value_supported_by_quote(k, c.value, c.quote))
        if r and a:
            if _same_value(key, r.value, a.value):
                setattr(out, key, r.model_copy(update={"source": "both"}))
            else:
                unc.append(Uncertainty(
                    field=LABEL[key],
                    reason=f'The AI read "{a.value}" but the fixed reader read "{r.value}". They disagree, so a person should confirm.',
                    quote=r.quote,
                ))
        else:
            setattr(out, key, r or a)

    for key in BOOL_KEYS:
        r = check(key, getattr(rules, key), "fixed reader", lambda c: True)
        a = check(key, getattr(ai, key) if ai else None, "AI", lambda c: True)
        if r and a:
            if r.value == a.value:
                setattr(out, key, r.model_copy(update={"source": "both"}))
            else:
                unc.append(Uncertainty(field=LABEL[key], reason="The AI and the fixed reader disagree.", quote=r.quote))
        else:
            setattr(out, key, r or a)

    # Line items: match rows by their exact quote.
    def row_ok(c: Sourced, who: str) -> Optional[Sourced]:
        row = c.value
        if not is_exact_quote(text, c.quote):
            unc.append(Uncertainty(field="line item", reason=f"The {who} gave a table row that is not in the document, so it was ignored.", quote=c.quote))
            return None
        for name, v in (("quantity", row.quantity), ("unit price", row.unit_price), ("line amount", row.line_amount)):
            if not number_in_quote(c.quote, v):
                unc.append(Uncertainty(field=f"line item {name}", reason=f'The {who} gave {name} "{v}" which is not in the row it quoted.', quote=c.quote))
                return None
        return c

    r_items = [x for x in (row_ok(i, "fixed reader") for i in rules.items) if x]
    a_items = [x for x in (row_ok(i, "AI") for i in (ai.items if ai else [])) if x]
    used: set[int] = set()
    for r in r_items:
        j = next((idx for idx, a in enumerate(a_items) if idx not in used and squash(a.quote) == squash(r.quote)), -1)
        if j < 0:
            out.items.append(r)
            continue
        used.add(j)
        a = a_items[j].value
        pairs = [(r.value.quantity, a.quantity), (r.value.unit_price, a.unit_price), (r.value.line_amount, a.line_amount)]
        if all(parse_number(x) is not None and parse_number(x) == parse_number(y) for x, y in pairs):
            out.items.append(r.model_copy(update={"source": "both"}))
        else:
            unc.append(Uncertainty(field="line item", reason="The AI and the fixed reader read different numbers from this row.", quote=r.quote))
    for idx, a in enumerate(a_items):
        if idx not in used:
            out.items.append(a)

    return out, unc
