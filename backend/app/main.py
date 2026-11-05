"""FastAPI service. Routes live under /api so the Next.js app can proxy them."""
from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()  # reads backend/.env if present

from fastapi import FastAPI, HTTPException, Request  # noqa: E402
from fastapi.concurrency import run_in_threadpool  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from pydantic import BaseModel, Field, ValidationError  # noqa: E402

from .extract.ai_reader import ai_enabled, ai_model, groq_completer  # noqa: E402
from .graph import run_pipeline  # noqa: E402
from .models import dump  # noqa: E402
from .pr import parse_purchase_request_csv  # noqa: E402
from .samples import list_samples, read_sample, read_sample_request_csv  # noqa: E402
from .store import get_store  # noqa: E402

MAX_BYTES = 10 * 1024 * 1024

app = FastAPI(title="Quote desk API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


def bad(message: str, status: int = 400) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception):
    return bad(str(exc) or "Something went wrong.", 500)


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException):
    return bad(str(exc.detail), exc.status_code)


@app.get("/api/health")
async def health():
    store = get_store()
    error: Optional[str] = None
    count = 0
    try:
        count = len(await run_in_threadpool(store.get_request))
    except Exception as e:  # noqa: BLE001
        error = str(e)
    return {
        "storage": store.kind,
        "ai": {"enabled": ai_enabled(), "model": ai_model() if ai_enabled() else None},
        "requestItems": count,
        "samples": list_samples(),
        "hasSampleRequest": read_sample_request_csv() is not None,
        "error": error,
    }


@app.get("/api/purchase-request")
async def get_purchase_request():
    items = await run_in_threadpool(get_store().get_request)
    return [dump(i) for i in items]


@app.post("/api/purchase-request")
async def set_purchase_request(request: Request):
    """Replace the purchase request. Send a CSV as form field "file", or JSON {"sample": true}."""
    try:
        if "application/json" in request.headers.get("content-type", ""):
            body = await request.json()
            csv_text = read_sample_request_csv() if body.get("sample") else None
            if not csv_text:
                return bad("No sample purchase request is bundled with this app.")
        else:
            form = await request.form()
            file = form.get("file")
            if file is None or not hasattr(file, "read"):
                return bad("Choose a CSV file.")
            raw = await file.read()
            if len(raw) > 1_000_000:
                return bad("The file is larger than 1 MB.")
            csv_text = raw.decode("utf-8-sig")
        items = parse_purchase_request_csv(csv_text)
    except (ValueError, UnicodeDecodeError) as e:
        return bad(str(e))
    await run_in_threadpool(get_store().replace_request, items)
    return {"items": len(items)}


@app.post("/api/analyze")
async def analyze(request: Request):
    """Check one quotation. One file per request, so the page can show progress file by file."""
    store = get_store()
    items = await run_in_threadpool(store.get_request)
    if not items:
        return bad("Load the purchase request first. Price and quantity cannot be compared without it.")

    if "application/json" in request.headers.get("content-type", ""):
        body = await request.json()
        filename = str(body.get("sample", ""))
        data = read_sample(filename)
        if data is None:
            return bad("That sample file does not exist.")
    else:
        form = await request.form()
        file = form.get("file")
        if file is None or not hasattr(file, "read"):
            return bad("Choose a PDF file.")
        data = await file.read()
        filename = getattr(file, "filename", None) or "upload.pdf"
        if len(data) > MAX_BYTES:
            return bad(f"{filename} is larger than 10 MB.")
        if data[:4] != b"%PDF":
            return bad(f"{filename} is not a PDF file.")

    result = await run_pipeline(
        filename, items, pdf=data, complete=groq_completer() if ai_enabled() else None
    )
    saved = await run_in_threadpool(store.save_analysis, result)
    return {"id": saved.id, "decision": saved.decision, "filename": filename}


@app.get("/api/analyses")
async def list_analyses():
    rows = await run_in_threadpool(get_store().list_analyses)
    return [dump(r) for r in rows]


@app.get("/api/analyses/{analysis_id}")
async def get_analysis(analysis_id: str):
    row = await run_in_threadpool(get_store().get_analysis, analysis_id)
    if row is None:
        return bad("Document not found.", 404)
    return dump(row)


class ReviewBody(BaseModel):
    decision: str = Field(pattern="^(Approve|Reject)$")
    note: str
    reviewer: Optional[str] = Field(default=None, max_length=80)


@app.post("/api/analyses/{analysis_id}/review")
async def review(analysis_id: str, request: Request):
    """A person answers a document the system stopped on."""
    try:
        body = ReviewBody.model_validate(await request.json())
    except (ValidationError, ValueError):
        return bad("Choose Approve or Reject and write a short reason.")
    note = body.note.strip()
    if len(note) < 5:
        return bad("Write a short reason (at least 5 characters).")
    store = get_store()
    row = await run_in_threadpool(store.get_analysis, analysis_id)
    if row is None:
        return bad("Document not found.", 404)
    if row.status != "awaiting_person":
        return bad("This document is not waiting for a person.", 409)
    saved = await run_in_threadpool(store.add_review, analysis_id, body.decision, note, (body.reviewer or "").strip() or None)
    return {"id": saved.id, "finalDecision": saved.final_decision}
