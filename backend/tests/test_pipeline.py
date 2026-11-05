import json
from pathlib import Path

import pytest

from app.graph import run_pipeline
from app.pr import parse_purchase_request_csv

ROOT = Path(__file__).resolve().parents[1]
REQUEST = parse_purchase_request_csv((ROOT / "data/purchase-request.csv").read_text(encoding="utf-8"))
EXPECTED = json.loads((ROOT / "tests/expected.json").read_text())
FIX = ROOT / "tests/fixtures"


def pdf(name: str) -> bytes:
    return (ROOT / "data/samples" / name).read_bytes()


async def run(name: str, **kw):
    return await run_pipeline(name, REQUEST, pdf=pdf(name), **kw)


# ---- the 10 sample PDFs, fixed reader only -------------------------------------------------

@pytest.mark.parametrize("file,exp", list(EXPECTED.items()))
async def test_sample_pack(file, exp):
    r = await run(file)
    assert r.fields.supplier_name.value == exp["supplier"]
    assert r.decision == exp["decision"]
    assert sorted({f.rule_id for f in r.findings}) == sorted(exp["rules"])


async def test_every_quote_is_exact_document_text():
    for file in EXPECTED:
        r = await run(file)
        flat = " ".join(r.raw_text.split())
        for f in r.findings:
            for e in f.evidence:
                if e.quote:
                    assert " ".join(e.quote.split()) in flat, (file, e.quote)


async def test_steps_run_in_fixed_order():
    r = await run("supplier-pack-01.pdf")
    assert [t.step for t in r.trace] == ["ingest", "read_rules", "read_ai", "verify", "compare", "contract", "decide", "ask_person"]
    assert next(t for t in r.trace if t.step == "ask_person").status == "skipped"


async def test_person_is_asked_when_answer_needs_a_check():
    r = await run("supplier-pack-09.pdf")
    assert r.questions
    assert next(t for t in r.trace if t.step == "ask_person").status == "stopped"


# ---- never guess ---------------------------------------------------------------------------

async def test_stops_when_pdf_has_no_text():
    r = await run_pipeline("scan.pdf", REQUEST, text="   ")
    assert r.decision == "Needs a person to check"
    assert next(t for t in r.trace if t.step == "compare").status == "skipped"
    assert next(t for t in r.trace if t.step == "ask_person").status == "stopped"


async def test_stops_when_file_is_not_a_pdf():
    r = await run_pipeline("bad.pdf", REQUEST, pdf=b"hello, not a pdf at all")
    assert r.decision == "Needs a person to check"


async def test_no_reject_for_missing_tin_when_one_is_printed_but_unreadable():
    r = await run_pipeline("odd.pdf", REQUEST, text=(FIX / "odd-tin.txt").read_text())
    assert not any(f.rule_id == "R4" for f in r.findings)
    assert r.decision == "Needs a person to check"


async def test_unknown_item_is_flagged_not_assumed():
    r = await run_pipeline("x.pdf", REQUEST, text=(FIX / "unknown-item.txt").read_text())
    assert r.decision == "Needs a person to check"
    assert any(u.field == "line item match" for u in r.uncertainties)


async def test_missing_purchase_request_is_flagged():
    r = await run_pipeline("a.pdf", [], pdf=pdf("supplier-pack-01.pdf"))
    assert r.decision == "Needs a person to check"


# ---- AI cross-check (the AI is faked) --------------------------------------------------------

PACK5 = (FIX / "pack-05.txt").read_text()
FULL_CLAUSE = "1. Payment. 40% advance payable with the purchase order. 40% advance with the purchase order, balance 60% within 30 days of delivery."


def ai_json(**over):
    base = {
        "supplier_name": {"value": "Meghna Carton Works", "quote": "Meghna Carton Works"},
        "advance": {"percent": "40", "quote": FULL_CLAUSE},
    }
    base.update(over)
    return json.dumps(base)


def fake(reply: str):
    async def complete(system: str, user: str) -> str:
        return reply
    return complete


async def test_fields_confirmed_when_ai_and_fixed_reader_agree():
    r = await run_pipeline("a.pdf", REQUEST, text=PACK5, complete=fake(ai_json()))
    assert r.fields.advance_percent.source == "both"
    assert r.decision == "Reject"
    assert r.mode.ai == "groq"


async def test_ai_quote_not_in_document_is_ignored():
    reply = ai_json(advance={"percent": "5", "quote": "Only 5% advance is needed."})
    r = await run_pipeline("a.pdf", REQUEST, text=PACK5, complete=fake(reply))
    assert r.fields.advance_percent.value == "40"  # the fixed reader's verified value stays
    assert any("not in the document" in u.reason for u in r.uncertainties)
    assert r.decision == "Reject"


async def test_ai_contradiction_with_real_quote_goes_to_a_person():
    reply = ai_json(advance={"percent": "60", "quote": "40% advance with the purchase order, balance 60% within 30 days of delivery."})
    r = await run_pipeline("a.pdf", REQUEST, text=PACK5, complete=fake(reply))
    assert r.fields.advance_percent is None
    assert any(u.field == "advance payment" and "disagree" in u.reason for u in r.uncertainties)
    assert r.decision == "Needs a person to check"  # never rejects on a disputed reading


async def test_broken_ai_reply_falls_back_to_fixed_reader_and_says_so():
    r = await run_pipeline("a.pdf", REQUEST, text=PACK5, complete=fake("not json at all"))
    assert r.decision == "Reject"
    assert next(t for t in r.trace if t.step == "read_ai").status == "skipped"


async def test_ai_call_that_raises_falls_back():
    async def boom(system: str, user: str) -> str:
        raise RuntimeError("429 rate limit")
    r = await run_pipeline("a.pdf", REQUEST, text=PACK5, complete=boom)
    assert r.decision == "Reject"
    assert "429" in next(t for t in r.trace if t.step == "read_ai").summary


# ---- small unit checks -----------------------------------------------------------------------

def test_csv_errors_are_plain():
    with pytest.raises(ValueError, match="quantity"):
        parse_purchase_request_csv("PR number,Item,Description,Unit,Quantity requested,Maximum unit price (BDT)\nPR-1,A,x,m,abc,5\n")
    with pytest.raises(ValueError, match="no rows"):
        parse_purchase_request_csv("PR number,Item\n")
