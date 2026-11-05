from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.store import reset_store

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
async def client(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    reset_store()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        yield c
    reset_store()


async def test_health_reports_modes(client):
    r = (await client.get("/api/health")).json()
    assert r["storage"] == "memory" and r["ai"]["enabled"] is False
    assert len(r["samples"]) == 10 and r["hasSampleRequest"] is True


async def test_refuses_to_check_before_purchase_request_is_loaded(client):
    r = await client.post("/api/analyze", json={"sample": "supplier-pack-01.pdf"})
    assert r.status_code == 400 and "purchase request" in r.json()["error"]


async def test_full_flow_with_person_review(client):
    assert (await client.post("/api/purchase-request", json={"sample": True})).json() == {"items": 5}
    for n in range(1, 11):
        r = await client.post("/api/analyze", json={"sample": f"supplier-pack-{n:02d}.pdf"})
        assert r.status_code == 200, r.text

    rows = (await client.get("/api/analyses")).json()
    by_file = {r["result"]["filename"]: r for r in rows}
    assert by_file["supplier-pack-01.pdf"]["decision"] == "Approve"
    assert by_file["supplier-pack-03.pdf"]["decision"] == "Reject"
    waiting = by_file["supplier-pack-07.pdf"]
    assert waiting["status"] == "awaiting_person"

    # camelCase shape the frontend relies on
    assert "finalDecision" in waiting and "rawText" in waiting["result"] and "findings" in waiting["result"]
    assert waiting["result"]["comparison"][0]["qtyDiffPercent"] == "-17.5"

    url = f"/api/analyses/{waiting['id']}/review"
    assert (await client.post(url, json={"decision": "Approve", "note": "ok"})).status_code == 400
    assert (await client.post(url, json={"decision": "Maybe", "note": "long enough"})).status_code == 400
    ok = await client.post(f"/api/analyses/{by_file['supplier-pack-01.pdf']['id']}/review",
                           json={"decision": "Reject", "note": "trying to override"})
    assert ok.status_code == 409  # not waiting for a person

    done = await client.post(url, json={"decision": "Approve", "note": "Supplier confirmed by phone.", "reviewer": "Nasrin"})
    assert done.status_code == 200 and done.json()["finalDecision"] == "Approve"
    again = await client.post(url, json={"decision": "Reject", "note": "changing my mind"})
    assert again.status_code == 409

    got = (await client.get(f"/api/analyses/{waiting['id']}")).json()
    assert got["status"] == "resolved" and got["decision"] == "Needs a person to check"
    assert got["finalDecision"] == "Approve" and got["review"]["reviewer"] == "Nasrin"


async def test_upload_validation(client):
    await client.post("/api/purchase-request", json={"sample": True})
    r = await client.post("/api/analyze", files={"file": ("x.pdf", b"hello", "application/pdf")})
    assert r.status_code == 400 and "not a PDF" in r.json()["error"]
    pdf = (ROOT / "data/samples/supplier-pack-04.pdf").read_bytes()
    r = await client.post("/api/analyze", files={"file": ("mine.pdf", pdf, "application/pdf")})
    assert r.status_code == 200 and r.json()["decision"] == "Needs a person to check"


async def test_csv_upload_and_errors(client):
    csv = (ROOT / "data/purchase-request.csv").read_bytes()
    assert (await client.post("/api/purchase-request", files={"file": ("pr.csv", csv, "text/csv")})).json() == {"items": 5}
    bad = await client.post("/api/purchase-request", files={"file": ("pr.csv", b"a,b\n1,2\n", "text/csv")})
    assert bad.status_code == 400 and "missing" in bad.json()["error"]


async def test_unknown_analysis_is_404(client):
    assert (await client.get("/api/analyses/does-not-exist")).status_code == 404
