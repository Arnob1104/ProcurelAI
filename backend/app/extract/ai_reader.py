"""The AI reader (Groq). It only copies facts and quotes out of the document. It decides nothing."""
from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any, Awaitable, Callable, Optional

from ..models import LineItem, QuoteFields, Sourced

# Anything that sends (system, user) and returns the reply text. Easy to fake in tests.
Completer = Callable[[str, str], Awaitable[str]]

DEFAULT_MODEL = "llama-3.3-70b-versatile"


def ai_enabled() -> bool:
    return bool(os.environ.get("GROQ_API_KEY"))


def ai_model() -> str:
    return os.environ.get("GROQ_MODEL") or DEFAULT_MODEL


SYSTEM = """You read one supplier quotation and copy facts out of it. You do not decide anything.

Rules:
- Return one JSON object and nothing else.
- Every fact needs a "quote": text copied EXACTLY, character for character, from the document. Never fix spelling, never join lines, never summarise.
- A number in "value" must appear in its "quote".
- If a fact is not in the document, use null for the value and the quote. Never guess. Never calculate.
- Copy numbers as printed (keep commas and decimals).

JSON shape:
{
 "supplier_name": {"value": str|null, "quote": str|null},
 "quotation_no": {"value": str|null, "quote": str|null},
 "quote_date": {"value": str|null, "quote": str|null},
 "pr_reference": {"value": str|null, "quote": str|null},
 "tin": {"value": str|null, "quote": str|null},
 "bin": {"value": str|null, "quote": str|null},
 "items": [{"code": str|null, "description": str, "quantity": str, "unit": str, "unit_price": str, "line_amount": str, "quote": "the whole table row"}],
 "subtotal": {"value": str|null, "quote": str|null},
 "vat": {"rate": str|null, "amount": str|null, "quote": str|null},
 "total": {"value": str|null, "quote": str|null},
 "vat_included": {"value": true|false|null, "quote": str|null},
 "advance": {"percent": str|null, "quote": str|null},
 "payment": {"min_days": str|null, "max_days": str|null, "unclear": true|false|null, "quote": str|null},
 "delivery": {"amount": str|null, "unit": "days"|"weeks"|null, "quote": str|null},
 "penalty": {"percent": str|null, "period": str|null, "basis": str|null, "quote": str|null},
 "validity": {"days": str|null, "quote": str|null}
}

Notes:
- "advance.percent": the percent paid with the purchase order. Use "0" only if the document says no advance.
- "payment.min_days"/"max_days": days after delivery. "30 to 90 days" gives min "30", max "90". Set "unclear" true if the wording leaves terms open (for example "as agreed").
- "delivery": the promised time after the purchase order, as printed ("4" and "weeks").
- "penalty.period" and "penalty.basis" are short phrases copied from the clause, for example "per week" and "of order value". Use null for basis if the clause does not say what the percent applies to.
- "penalty" is null if the document has no late-delivery penalty clause.
- "vat_included": true only if the document says the prices already include VAT."""


def _str(v: Any) -> Optional[str]:
    if v is None:
        return None
    t = str(v).strip()
    return None if t == "" or t.lower() == "null" else t


def _obj(v: Any) -> dict:
    return v if isinstance(v, dict) else {}


def _sourced(value: Any, quote: Optional[str]) -> Optional[Sourced]:
    if value is None or quote is None:
        return None
    return Sourced(value=value, quote=quote, source="llm")


def llm_json_to_fields(raw: Any) -> QuoteFields:
    """Turn the AI's JSON into QuoteFields. No checking here; the verify step does that."""
    j = _obj(raw)
    f = QuoteFields()

    def simple(k: str) -> Optional[Sourced]:
        o = _obj(j.get(k))
        return _sourced(_str(o.get("value")), _str(o.get("quote")))

    f.supplier_name = simple("supplier_name")
    f.quotation_no = simple("quotation_no")
    f.quote_date = simple("quote_date")
    f.pr_reference = simple("pr_reference")
    f.tin = simple("tin")
    f.bin = simple("bin")
    f.subtotal = simple("subtotal")
    f.total = simple("total")

    vat = _obj(j.get("vat"))
    f.vat_rate = _sourced(_str(vat.get("rate")), _str(vat.get("quote")))
    f.vat_amount = _sourced(_str(vat.get("amount")), _str(vat.get("quote")))

    vi = _obj(j.get("vat_included"))
    f.vat_included = _sourced(True if vi.get("value") is True else None, _str(vi.get("quote")))

    adv = _obj(j.get("advance"))
    f.advance_percent = _sourced(_str(adv.get("percent")), _str(adv.get("quote")))

    pay = _obj(j.get("payment"))
    pq, pmin = _str(pay.get("quote")), _str(pay.get("min_days"))
    pmax = _str(pay.get("max_days")) or pmin
    f.payment_min_days = _sourced(pmin, pq)
    f.payment_max_days = _sourced(pmax, pq)
    f.payment_unclear = _sourced(True if pay.get("unclear") is True else None, pq)

    dl = _obj(j.get("delivery"))
    unit = (_str(dl.get("unit")) or "").lower()
    f.delivery_amount = _sourced(_str(dl.get("amount")), _str(dl.get("quote")))
    f.delivery_unit = _sourced(("weeks" if unit.startswith("week") else "days") if unit else None, _str(dl.get("quote")))

    pen = _obj(j.get("penalty"))
    pen_q = _str(pen.get("quote"))
    f.penalty_percent = _sourced(_str(pen.get("percent")), pen_q)
    f.penalty_period = _sourced(_str(pen.get("period")), pen_q)
    f.penalty_basis = _sourced(_str(pen.get("basis")), pen_q)
    f.penalty_clause = _sourced(pen_q, pen_q)

    val = _obj(j.get("validity"))
    f.validity_days = _sourced(_str(val.get("days")), _str(val.get("quote")))

    for it in j.get("items") if isinstance(j.get("items"), list) else []:
        o = _obj(it)
        quote, desc = _str(o.get("quote")), _str(o.get("description"))
        qty, price, amount = _str(o.get("quantity")), _str(o.get("unit_price")), _str(o.get("line_amount"))
        if not (quote and desc and qty and price and amount):
            continue
        item = LineItem(
            code=_str(o.get("code")), description=desc, unit=_str(o.get("unit")) or "",
            quantity=qty, unit_price=price, line_amount=amount, quote=quote,
        )
        f.items.append(Sourced(value=item, quote=quote, source="llm"))
    return f


def groq_completer() -> Completer:
    """Groq call with a short wait-and-retry on rate limits (the free tier allows few tokens per minute)."""
    import groq

    client = groq.AsyncGroq(api_key=os.environ["GROQ_API_KEY"])
    model = ai_model()

    async def complete(system: str, user: str) -> str:
        last: Exception | None = None
        for attempt in range(4):
            try:
                res = await client.chat.completions.create(
                    model=model,
                    temperature=0,
                    max_tokens=1800,
                    response_format={"type": "json_object"},
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                )
                return res.choices[0].message.content or ""
            except groq.APIConnectionError as e:
                last = e
            except groq.APIStatusError as e:
                if e.status_code == 429 or e.status_code >= 500:
                    last = e
                else:
                    raise
            await asyncio.sleep(2.5 * (attempt + 1))
        raise last or RuntimeError("The AI call failed.")

    return complete


async def extract_with_ai(text: str, complete: Completer) -> tuple[Optional[QuoteFields], Optional[str]]:
    """Step: read the quotation with the AI. A failure is reported, never hidden."""
    try:
        reply = await complete(SYSTEM, f'Document:\n"""\n{text}\n"""')
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", reply).strip()
        return llm_json_to_fields(json.loads(cleaned)), None
    except Exception as e:  # noqa: BLE001 - any failure falls back to the fixed reader, and is shown in the trace
        return None, str(e) or "The AI call failed."
