"""Step: compare the quotation with the purchase request. Price and quantity, line by line, exact decimals."""
from __future__ import annotations

from ..models import ComparisonRow, Evidence, Finding, PurchaseRequestItem, QuoteFields, RuleResult, Uncertainty
from ..money import D, dp2, fmt, num_str, parse_number
from ..text import squash
from .catalog import new_result

THREE, FIVE = D(3), D(5)


def _norm(s: str) -> str:
    return squash(s).lower()


def _unknown(r: RuleResult, why: str) -> None:
    if r.status == "pass":
        r.status = "unknown"
    r.unknown_reason = f"{r.unknown_reason} {why}" if r.unknown_reason else why


def compare_with_request(fields: QuoteFields, request: list[PurchaseRequestItem]):
    """Returns (rules [R1, C1, C2], comparison rows, uncertainties)."""
    r1, c1, c2 = new_result("R1"), new_result("C1"), new_result("C2")
    unc: list[Uncertainty] = []
    rows: list[ComparisonRow] = []

    ref = fields.pr_reference.value if fields.pr_reference else None
    pool = [i for i in request if i.pr_number == ref] if ref else []
    if not ref:
        unc.append(Uncertainty(field="purchase request reference", reason="The quotation does not show which purchase request it answers."))
    elif not pool:
        unc.append(Uncertainty(
            field="purchase request reference",
            reason=f'No purchase request "{ref}" has been loaded, so price and quantity cannot be compared.',
            quote=fields.pr_reference.quote,
        ))
    if not fields.items:
        unc.append(Uncertainty(field="line items", reason="No item rows could be read from the quotation."))

    for it in fields.items:
        row = it.value
        match = next(
            (p for p in pool if (p.item == row.code if row.code else True) and _norm(p.description) == _norm(row.description)),
            None,
        )
        qty, price = parse_number(row.quantity), parse_number(row.unit_price)

        if match is None:
            why = (
                f'Item "{row.description}" does not match any line in {ref} (matched on item letter and description).'
                if pool else "No purchase request lines to compare with."
            )
            unc.append(Uncertainty(field="line item match", reason=why, quote=row.quote))
            for r in (r1, c1, c2):
                _unknown(r, why)
            rows.append(ComparisonRow(
                code=row.code, description=row.description, requested_qty=None, quoted_qty=row.quantity,
                quoted_unit_price=row.unit_price, quote=row.quote,
            ))
            continue

        if _norm(match.unit) != _norm(row.unit):
            why = f'Unit "{row.unit}" in the quotation differs from "{match.unit}" in the purchase request.'
            unc.append(Uncertainty(field="unit", reason=why, quote=row.quote))
            for r in (r1, c1, c2):
                _unknown(r, why)
            continue

        mx = parse_number(match.max_unit_price)
        requested = D(match.quantity_requested)
        over = (price - mx) / mx * 100 if price is not None else None
        qty_pct = (qty - requested) / requested * 100 if qty is not None else None

        rows.append(ComparisonRow(
            code=row.code, description=row.description, requested_qty=match.quantity_requested,
            quoted_qty=row.quantity, qty_diff_percent=dp2(qty_pct) if qty_pct is not None else None,
            max_unit_price=match.max_unit_price, quoted_unit_price=row.unit_price,
            price_over_percent=dp2(over) if over is not None else None, quote=row.quote,
        ))

        note = f"Purchase request {match.pr_number} item {match.item}: maximum unit price {fmt(mx)} BDT."
        label = f"Item {row.code or ''} {row.description}"
        if price is None or over is None:
            _unknown(r1, "Unit price could not be read as a number.")
            _unknown(c1, "Unit price could not be read as a number.")
        elif over > THREE:
            r1.status = "fail"
            r1.findings.append(Finding(
                rule_id="R1", severity="reject", title=f"Price is {fmt(over)}% above the maximum",
                detail=f"{label}: quoted {fmt(price)} BDT, maximum in {match.pr_number} is {fmt(mx)} BDT. More than 3% over.",
                evidence=[Evidence(quote=row.quote, note=note)],
            ))
        elif over > 0:
            c1.status = "fail"
            c1.findings.append(Finding(
                rule_id="C1", severity="check", title=f"Price is {fmt(over)}% above the maximum",
                detail=f"{label}: quoted {fmt(price)} BDT, maximum in {match.pr_number} is {fmt(mx)} BDT. Over, but by no more than 3%.",
                evidence=[Evidence(quote=row.quote, note=note)],
            ))

        if qty is None or qty_pct is None:
            _unknown(c2, "Quantity could not be read as a number.")
        elif abs(qty_pct) > FIVE:
            direction = "below" if qty_pct < 0 else "above"
            c2.status = "fail"
            c2.findings.append(Finding(
                rule_id="C2", severity="check", title=f"Quantity is {fmt(abs(qty_pct), 1)}% {direction} the request",
                detail=f"{label}: quoted {fmt(qty, 0)}, requested {fmt(requested, 0)}. More than 5% different.",
                evidence=[Evidence(
                    quote=row.quote,
                    note=f"Purchase request {match.pr_number} item {match.item}: quantity requested {fmt(requested, 0)}.",
                )],
            ))

    if not fields.items:
        for r in (r1, c1, c2):
            _unknown(r, "No item rows could be read.")

    return [r1, c1, c2], rows, unc
