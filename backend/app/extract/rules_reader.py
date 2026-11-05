"""The fixed reader. It never calls an AI. It reads the quotation layout with patterns
and returns only what it can point to in the text."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

from ..models import LineItem, QuoteFields, Sourced
from ..text import squash


def S(value: Any, quote: str) -> Sourced:
    return Sourced(value=value, quote=quote, source="regex")


@dataclass
class Clause:
    title: str
    text: str  # exact clause text with line breaks squashed to spaces


def split_clauses(text: str) -> list[Clause]:
    """Split the terms into numbered clauses, joining lines that wrap."""
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if re.match(r"^terms and conditions", l.strip(), re.I)), -1)
    if start < 0:
        return []
    clauses: list[Clause] = []
    cur: Optional[tuple[str, list[str]]] = None
    for raw in lines[start + 1:]:
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^\d+\.\s+([A-Za-z][A-Za-z ]*?)\.\s", line)
        if m:
            if cur:
                clauses.append(Clause(cur[0], squash(" ".join(cur[1]))))
            cur = (m.group(1), [line])
        elif re.match(r"^(For\s|Authorised)", line):
            break
        elif cur:
            cur[1].append(line)
    if cur:
        clauses.append(Clause(cur[0], squash(" ".join(cur[1]))))
    return clauses


def _line_with(text: str, pattern: str, flags: int = 0) -> Optional[str]:
    for l in text.splitlines():
        if re.search(pattern, l, flags):
            return l.strip()
    return None


def mentions_penalty(text: str) -> bool:
    return re.search(r"penalt|late delivery|delay", text, re.I) is not None


def extract_with_rules(text: str) -> QuoteFields:
    f = QuoteFields()
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    if lines:
        f.supplier_name = S(lines[0], lines[0])

    q_line = _line_with(text, r"Quotation no\.?", re.I)
    if q_line:
        m = re.search(r"Quotation no\.?\s+(\S+)(?:\s+Date\s+(\d{4}-\d{2}-\d{2}))?", q_line, re.I)
        if m:
            f.quotation_no = S(m.group(1), q_line)
            if m.group(2):
                f.quote_date = S(m.group(2), q_line)
    ref_line = _line_with(text, r"\bReference\b")
    if ref_line:
        m = re.search(r"Reference\s+(\S+)", ref_line)
        if m:
            f.pr_reference = S(m.group(1), ref_line)

    # Take the whole token after the label. If it has stray letters it is not accepted,
    # so a half-read number can never pass as a real TIN or BIN.
    tin = re.search(r"TIN:\s*(\S+)", text)
    if tin and re.fullmatch(r"\d+", tin.group(1)):
        f.tin = S(tin.group(1), tin.group(0))
    bin_ = re.search(r"BIN:\s*(\S+)", text)
    if bin_ and re.fullmatch(r"\d[\d-]*\d", bin_.group(1)):
        f.bin = S(bin_.group(1), bin_.group(0))

    row_re = re.compile(r"^([A-Z])\s+(.+?)\s+([\d,]+)\s+([A-Za-z]+)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})$")
    for l in lines:
        m = row_re.match(l)
        if m:
            item = LineItem(
                code=m.group(1), description=m.group(2), quantity=m.group(3), unit=m.group(4),
                unit_price=m.group(5), line_amount=m.group(6), quote=l,
            )
            f.items.append(S(item, l))

    for l in lines:
        m = re.match(r"^Subtotal\s+([\d,]+\.\d{2})$", l, re.I)
        if m:
            f.subtotal = S(m.group(1), l)
        m = re.match(r"^VAT\s+(\d+(?:\.\d+)?)\s*%\s+([\d,]+\.\d{2})$", l, re.I)
        if m:
            f.vat_rate = S(m.group(1), l)
            f.vat_amount = S(m.group(2), l)
        m = re.match(r"^Total\b.*?([\d,]+\.\d{2})$", l, re.I)
        if m:
            f.total = S(m.group(1), l)

    incl = _line_with(text, r"VAT included|all taxes included|inclusive of (VAT|all taxes)", re.I)
    if incl:
        f.vat_included = S(True, incl)

    clauses = split_clauses(text)

    def by_title(pattern: str) -> Optional[Clause]:
        return next((c for c in clauses if re.search(pattern, c.title, re.I)), None)

    pay = by_title(r"^payment$")
    if pay:
        if re.search(r"no advance", pay.text, re.I):
            f.advance_percent = S("0", pay.text)
        else:
            a = re.search(r"(\d+(?:\.\d+)?)\s*%\s*advance", pay.text, re.I)
            if a:
                f.advance_percent = S(a.group(1), pay.text)
        d = re.search(r"within\s+(\d+)(?:\s*(?:to|-)\s*(\d+))?\s+days", pay.text, re.I)
        if d:
            f.payment_min_days = S(d.group(1), pay.text)
            f.payment_max_days = S(d.group(2) or d.group(1), pay.text)
        if re.search(r"as agreed|to be agreed|negotiable|mutually agreed", pay.text, re.I):
            f.payment_unclear = S(True, pay.text)

    dlv = by_title(r"^delivery$")
    if dlv:
        d = re.search(r"within\s+(\d+)\s+(days?|weeks?)", dlv.text, re.I)
        if d:
            f.delivery_amount = S(d.group(1), dlv.text)
            f.delivery_unit = S("weeks" if d.group(2).lower().startswith("week") else "days", dlv.text)

    pen = by_title(r"^delay$") or next(
        (c for c in clauses if re.search(r"penalt", c.text, re.I) and not re.match(r"^delivery$", c.title, re.I)), None
    )
    if pen:
        f.penalty_clause = S(pen.text, pen.text)
        p = re.search(r"(\d+(?:\.\d+)?)\s*%", pen.text)
        if p:
            f.penalty_percent = S(p.group(1), pen.text)
        per = re.search(
            r"(per\s+(?:full\s+)?(?:week|day|month)|for\s+each\s+(?:full\s+)?(?:week|day|month)|each\s+(?:full\s+)?(?:week|day|month))",
            pen.text, re.I,
        )
        if per:
            f.penalty_period = S(per.group(1), pen.text)
        b = re.search(r"of\s+(?:the\s+)?(?:total\s+)?order\s+value", pen.text, re.I)
        if b:
            f.penalty_basis = S(b.group(0), pen.text)

    val = by_title(r"^validity$")
    if val:
        v = re.search(r"valid\s+for\s+(\d+)\s+days", val.text, re.I)
        if v:
            f.validity_days = S(v.group(1), val.text)

    return f
