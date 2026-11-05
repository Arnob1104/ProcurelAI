"""Step: check the contract terms against the company rules.
A rule that cannot be tested is marked "unknown" and sent to a person. It is never passed by default."""
from __future__ import annotations

import re
from typing import Optional

from ..extract.rules_reader import mentions_penalty, split_clauses
from ..models import Evidence, Finding, QuoteFields, RuleResult, Uncertainty
from ..money import D, fmt, num_str, parse_number, same_money
from .catalog import new_result


def check_contract(fields: QuoteFields, raw_text: str, earlier: list[Uncertainty]):
    """Returns (rule results, new uncertainties)."""
    rules = {i: new_result(i) for i in ["R2", "R3", "R4", "R5", "C3", "C4", "C5", "C6", "C7", "N1"]}
    unc: list[Uncertainty] = []

    def unknown(rid: str, why: str) -> None:
        r = rules[rid]
        if r.status == "pass":
            r.status = "unknown"
        r.unknown_reason = f"{r.unknown_reason} {why}" if r.unknown_reason else why

    def fail(rid: str, title: str, detail: str, evidence: list[Evidence]) -> None:
        r = rules[rid]
        r.status = "fail"
        r.findings.append(Finding(rule_id=rid, severity=r.severity, title=title, detail=detail, evidence=evidence))

    def was_uncertain(word: str) -> bool:
        return any(word in u.field.lower() for u in earlier)

    # R2: advance payment
    adv = fields.advance_percent
    if not adv:
        unknown("R2", "The advance payment could not be confirmed (see the flagged reading)." if was_uncertain("advance")
                else "The quotation does not state the advance payment.")
    else:
        pct = parse_number(adv.value)
        if pct is None:
            unknown("R2", "The advance payment is not a number.")
        elif pct > 20:
            fail("R2", f"Advance payment is {num_str(pct)}%",
                 f"The supplier asks for {num_str(pct)}% with the purchase order. The limit is 20%.",
                 [Evidence(quote=adv.quote)])

    # R3 and N1: late-delivery penalty
    clause = fields.penalty_clause
    if not clause:
        if was_uncertain("penalty") or was_uncertain("late-delivery"):
            unknown("R3", "A late-delivery clause may exist but could not be confirmed (see the flagged reading).")
            unknown("N1", "The penalty could not be read.")
        elif mentions_penalty(raw_text):
            unknown("R3", "The text mentions delay or penalty, but no clause could be read from it.")
            unknown("N1", "The penalty could not be read.")
        else:
            heads = [c.title for c in split_clauses(raw_text)]
            has_heading = re.search(r"TERMS AND CONDITIONS", raw_text, re.I) is not None
            fail("R3", "No late-delivery penalty clause",
                 "Nothing in the document mentions a penalty for late delivery.",
                 [Evidence(
                     quote="TERMS AND CONDITIONS" if has_heading else None,
                     note=f"No clause about late delivery follows this heading. Clauses present: {', '.join(heads) if heads else 'none'}.",
                 )])
    else:
        pct = parse_number(fields.penalty_percent.value if fields.penalty_percent else None)
        period = fields.penalty_period.value if fields.penalty_period else ""
        basis = fields.penalty_basis.value if fields.penalty_basis else ""
        ev = [Evidence(quote=clause.quote)]
        if pct is None:
            unknown("N1", "The penalty percent could not be read.")
        elif not re.search(r"week", period, re.I):
            fail("N1", "Penalty is not stated per week",
                 "The clause does not say the penalty applies per week of delay, so it cannot be compared with 0.5% per week.", ev)
        elif not re.search(r"order value", basis, re.I):
            fail("N1", "Penalty does not say what the percent applies to",
                 f"The clause gives {num_str(pct)}% per week but does not say it is a percent of order value.", ev)
        elif pct < D("0.5"):
            fail("N1", f"Penalty is only {num_str(pct)}% per week",
                 "The company minimum is 0.5% of order value per week of delay.", ev)

    # R4: TIN and BIN
    missing: list[str] = []
    for name, f, pat in (("TIN", fields.tin, r"\bTIN\W{0,3}\d"), ("BIN", fields.bin, r"\bBIN\W{0,3}\d")):
        if f:
            continue
        if was_uncertain(name.lower()):
            unknown("R4", f"The {name} could not be confirmed (see the flagged reading).")
        elif re.search(pat, raw_text, re.I):
            unknown("R4", f"A {name} seems to be printed but could not be read.")
        else:
            missing.append(name)
    if missing:
        reg: Optional[str] = next(
            (l.strip() for l in raw_text.splitlines() if re.search(r"registration|TIN|BIN", l, re.I)), None
        )
        joined_and, joined_or = " and ".join(missing), " or ".join(missing)
        fail("R4", f"{joined_and} missing", f"The quotation gives no {joined_or}.",
             [Evidence(quote=reg, note=None if reg else f"No {joined_or} appears anywhere in the document.")])

    # R5 and C4: delivery time
    amt = parse_number(fields.delivery_amount.value if fields.delivery_amount else None)
    unit = fields.delivery_unit.value if fields.delivery_unit else None
    if amt is None or not unit or not fields.delivery_amount:
        why = ("The delivery time could not be confirmed (see the flagged reading)." if was_uncertain("delivery")
               else "The quotation does not state a delivery time.")
        unknown("R5", why)
        unknown("C4", why)
    else:
        days = amt * 7 if unit == "weeks" else amt
        note = f"{num_str(amt)} weeks = {num_str(days)} days" if unit == "weeks" else None
        ev = [Evidence(quote=fields.delivery_amount.quote, note=note)]
        if days > 45:
            fail("R5", f"Delivery in {num_str(days)} days",
                 f"Promised {num_str(days)} days after the purchase order. The limit is 45 days.", ev)
        elif days > 30:
            fail("C4", f"Delivery in {num_str(days)} days",
                 f"Promised {num_str(days)} days after the purchase order. 31 to 45 days needs a person to check.", ev)

    # C3: payment terms (one finding per clause, even if it is both open and out of range)
    p_min = parse_number(fields.payment_min_days.value if fields.payment_min_days else None)
    p_max = parse_number(fields.payment_max_days.value if fields.payment_max_days else None)
    days_known = p_min is not None and p_max is not None and fields.payment_min_days is not None
    out_of_range = days_known and (p_min < 30 or p_max > 60)
    span = ""
    if days_known:
        span = f"{num_str(p_min)} days" if p_min == p_max else f"{num_str(p_min)} to {num_str(p_max)} days"
    if fields.payment_unclear:
        fail("C3",
             f"Payment terms are open ({span})" if out_of_range else "Payment terms are open",
             (f"The wording leaves the payment period to be agreed later, and the stated range of {span} is outside 30 to 60 days after delivery."
              if out_of_range else "The wording leaves the payment period to be agreed later."),
             [Evidence(quote=fields.payment_unclear.quote)])
    elif not days_known:
        if was_uncertain("payment"):
            unknown("C3", "The payment period could not be confirmed (see the flagged reading).")
        else:
            fail("C3", "No payment period stated",
                 "The quotation does not say how many days after delivery payment is due.",
                 [Evidence(quote=None, note="No 'within N days' payment period appears in the payment clause.")])
    elif out_of_range:
        fail("C3", f"Payment due in {span}", "Payment must fall within 30 to 60 days after delivery.",
             [Evidence(quote=fields.payment_min_days.quote)])

    # C5: VAT shown separately at 15%
    if fields.vat_included:
        fail("C5", "VAT is included in the price", "VAT is not shown as a separate 15% line.",
             [Evidence(quote=fields.vat_included.quote)])
    elif not fields.vat_rate or not fields.vat_amount:
        if was_uncertain("vat"):
            unknown("C5", "The VAT line could not be confirmed (see the flagged reading).")
        else:
            fail("C5", "VAT is not shown", "No separate VAT line was found.",
                 [Evidence(quote=None, note="No line starting with VAT appears in the document.")])
    elif parse_number(fields.vat_rate.value) != 15:
        fail("C5", f"VAT is {fields.vat_rate.value}%, not 15%", "VAT must be shown separately at 15%.",
             [Evidence(quote=fields.vat_rate.quote)])

    # C6: do the numbers add up?
    sum_lines = D(0)
    lines_ok = len(fields.items) > 0
    for it in fields.items:
        q, p, a = parse_number(it.value.quantity), parse_number(it.value.unit_price), parse_number(it.value.line_amount)
        if q is None or p is None or a is None:
            lines_ok = False
            unknown("C6", "A line amount could not be read as a number.")
            continue
        sum_lines += a
        expect = q * p
        if not same_money(expect, a):
            fail("C6", "Line total is wrong", f"{fmt(q, 0)} x {fmt(p)} = {fmt(expect)}, but the quotation shows {fmt(a)}.",
                 [Evidence(quote=it.quote, note=f"Calculated: {fmt(q, 0)} x {fmt(p)} = {fmt(expect)}")])
    total = parse_number(fields.total.value if fields.total else None)
    if not lines_ok or total is None or not fields.total:
        if rules["C6"].status == "pass":
            unknown("C6", "The line items or the total could not be read, so the sums cannot be checked.")
    elif fields.vat_included:
        if not same_money(sum_lines, total):
            fail("C6", "Total does not match the lines", f"Lines add up to {fmt(sum_lines)} but the total shows {fmt(total)}.",
                 [Evidence(quote=fields.total.quote, note=f"Sum of lines: {fmt(sum_lines)}")])
    else:
        sub = parse_number(fields.subtotal.value if fields.subtotal else None)
        vat = parse_number(fields.vat_amount.value if fields.vat_amount else None)
        rate = parse_number(fields.vat_rate.value if fields.vat_rate else None)
        if sub is None or vat is None or rate is None:
            if rules["C6"].status == "pass":
                unknown("C6", "The subtotal or VAT line could not be read, so the sums cannot be checked.")
        else:
            if not same_money(sum_lines, sub):
                fail("C6", "Subtotal does not match the lines", f"Lines add up to {fmt(sum_lines)} but the subtotal shows {fmt(sub)}.",
                     [Evidence(quote=fields.subtotal.quote, note=f"Sum of lines: {fmt(sum_lines)}")])
            exp_vat = sub * rate / 100
            if not same_money(exp_vat, vat):
                fail("C6", "VAT amount is wrong", f"{num_str(rate)}% of {fmt(sub)} is {fmt(exp_vat)}, but the quotation shows {fmt(vat)}.",
                     [Evidence(quote=fields.vat_amount.quote, note=f"Calculated: {fmt(sub)} x {num_str(rate)}% = {fmt(exp_vat)}")])
            exp_total = sub + vat
            if not same_money(exp_total, total):
                fail("C6", "Total is wrong", f"{fmt(sub)} + {fmt(vat)} = {fmt(exp_total)}, but the quotation shows {fmt(total)}.",
                     [Evidence(quote=fields.total.quote, note=f"Calculated: {fmt(sub)} + {fmt(vat)} = {fmt(exp_total)}")])

    # C7: validity
    val = parse_number(fields.validity_days.value if fields.validity_days else None)
    if val is None or not fields.validity_days:
        unknown("C7", "The validity period could not be confirmed (see the flagged reading)." if was_uncertain("validity")
                else "The quotation does not state how long it is valid.")
    elif val < 30:
        fail("C7", f"Valid for only {num_str(val)} days", "The quotation must be valid for at least 30 days.",
             [Evidence(quote=fields.validity_days.quote)])

    for r in rules.values():
        if r.status == "unknown" and r.unknown_reason:
            unc.append(Uncertainty(field=f"rule {r.rule_id}", reason=r.unknown_reason))

    return list(rules.values()), unc
