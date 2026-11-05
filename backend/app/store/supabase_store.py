"""Supabase (Postgres) storage. Uses the service role key, which stays on the server."""
from __future__ import annotations

import os
from decimal import Decimal
from typing import Any, Optional

from supabase import create_client

from ..models import AnalysisResult, HumanReview, PurchaseRequestItem, StoredAnalysis, dump
from .base import status_for

SELECT = "id, created_at, status, decision, final_decision, result, human_reviews(decision, note, reviewer, created_at)"


def _check(res: Any, where: str) -> Any:
    # supabase-py raises on HTTP errors; this adds a friendlier hint.
    return res


class SupabaseStore:
    kind = "supabase"

    def __init__(self) -> None:
        self.db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

    def _wrap(self, where: str, fn):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(
                f"Supabase {where} failed: {e}. Check that supabase/schema.sql was run and the keys in backend/.env are right."
            ) from e

    @staticmethod
    def _to_stored(r: dict) -> StoredAnalysis:
        # human_reviews is one-to-one with analyses (unique analysis_id), so PostgREST returns
        # a single object, not a list. Accept both shapes.
        h = r.get("human_reviews")
        if isinstance(h, list):
            h = h[0] if h else None
        review = HumanReview(decision=h["decision"], note=h["note"], reviewer=h.get("reviewer"), created_at=h["created_at"]) if h else None
        return StoredAnalysis(
            id=r["id"], created_at=r["created_at"], status=r["status"], decision=r["decision"],
            final_decision=r["final_decision"], result=AnalysisResult.model_validate(r["result"]), review=review,
        )

    def get_request(self) -> list[PurchaseRequestItem]:
        res = self._wrap("reading the purchase request",
                         lambda: self.db.table("purchase_request_items").select("*").order("pr_number").order("item").execute())
        return [
            PurchaseRequestItem(
                pr_number=r["pr_number"], item=r["item"], description=r["description"], unit=r["unit"],
                quantity_requested=int(Decimal(str(r["quantity_requested"]))),
                max_unit_price=f"{Decimal(str(r['max_unit_price'])):.2f}",
            )
            for r in res.data
        ]

    def replace_request(self, items: list[PurchaseRequestItem]) -> None:
        self._wrap("clearing the purchase request", lambda: self.db.table("purchase_request_items").delete().gte("id", 0).execute())
        rows = [
            {"pr_number": i.pr_number, "item": i.item, "description": i.description, "unit": i.unit,
             "quantity_requested": i.quantity_requested, "max_unit_price": i.max_unit_price}
            for i in items
        ]
        self._wrap("saving the purchase request", lambda: self.db.table("purchase_request_items").insert(rows).execute())

    def save_analysis(self, result: AnalysisResult) -> StoredAnalysis:
        f = result.fields
        row = {
            "filename": result.filename,
            "supplier_name": f.supplier_name.value if f and f.supplier_name else None,
            "quotation_no": f.quotation_no.value if f and f.quotation_no else None,
            "pr_number": f.pr_reference.value if f and f.pr_reference else None,
            "decision": result.decision,
            "status": status_for(result),
            "final_decision": result.decision,
            "result": dump(result),
        }
        res = self._wrap("saving the analysis", lambda: self.db.table("analyses").insert(row).execute())
        saved = self.get_analysis(res.data[0]["id"])
        assert saved is not None
        return saved

    def list_analyses(self) -> list[StoredAnalysis]:
        res = self._wrap("listing analyses",
                         lambda: self.db.table("analyses").select(SELECT).order("created_at", desc=True).execute())
        return [self._to_stored(r) for r in res.data]

    def get_analysis(self, analysis_id: str) -> Optional[StoredAnalysis]:
        res = self._wrap("reading the analysis",
                         lambda: self.db.table("analyses").select(SELECT).eq("id", analysis_id).limit(1).execute())
        return self._to_stored(res.data[0]) if res.data else None

    def add_review(self, analysis_id: str, decision: str, note: str, reviewer: Optional[str]) -> StoredAnalysis:
        self._wrap("saving the review", lambda: self.db.table("human_reviews").upsert(
            {"analysis_id": analysis_id, "decision": decision, "note": note, "reviewer": reviewer},
            on_conflict="analysis_id").execute())
        self._wrap("closing the analysis", lambda: self.db.table("analyses").update(
            {"status": "resolved", "final_decision": decision}).eq("id", analysis_id).execute())
        row = self.get_analysis(analysis_id)
        if row is None:
            raise KeyError("Analysis not found.")
        return row

    def clear_review(self, analysis_id: str) -> StoredAnalysis:
        self._wrap("removing the review", lambda: self.db.table("human_reviews").delete().eq("analysis_id", analysis_id).execute())
        row = self.get_analysis(analysis_id)
        if row is None:
            raise KeyError("Analysis not found.")
        self._wrap("reopening the analysis", lambda: self.db.table("analyses").update(
            {"status": "awaiting_person", "final_decision": row.decision}).eq("id", analysis_id).execute())
        row = self.get_analysis(analysis_id)
        assert row is not None
        return row

    def delete_analysis(self, analysis_id: str) -> bool:
        # human_reviews rows go too (on delete cascade in schema.sql).
        res = self._wrap("deleting the analysis", lambda: self.db.table("analyses").delete().eq("id", analysis_id).execute())
        return bool(res.data)
