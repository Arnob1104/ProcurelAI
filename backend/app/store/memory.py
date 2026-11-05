"""Temporary storage for trying the app. Everything is lost when the server stops."""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Optional

from ..models import AnalysisResult, HumanReview, PurchaseRequestItem, StoredAnalysis
from .base import status_for


class MemoryStore:
    kind = "memory"

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._request: list[PurchaseRequestItem] = []
        self._rows: list[StoredAnalysis] = []

    def get_request(self) -> list[PurchaseRequestItem]:
        return list(self._request)

    def replace_request(self, items: list[PurchaseRequestItem]) -> None:
        self._request = list(items)

    def save_analysis(self, result: AnalysisResult) -> StoredAnalysis:
        row = StoredAnalysis(
            id=str(uuid.uuid4()), created_at=datetime.now(timezone.utc).isoformat(),
            status=status_for(result), decision=result.decision, final_decision=result.decision, result=result,
        )
        with self._lock:
            self._rows.insert(0, row)
        return row

    def list_analyses(self) -> list[StoredAnalysis]:
        return list(self._rows)

    def get_analysis(self, analysis_id: str) -> Optional[StoredAnalysis]:
        return next((r for r in self._rows if r.id == analysis_id), None)

    def add_review(self, analysis_id: str, decision: str, note: str, reviewer: Optional[str]) -> StoredAnalysis:
        with self._lock:
            row = self.get_analysis(analysis_id)
            if row is None:
                raise KeyError("Analysis not found.")
            row.review = HumanReview(decision=decision, note=note, reviewer=reviewer,
                                     created_at=datetime.now(timezone.utc).isoformat())
            row.status = "resolved"
            row.final_decision = decision
            return row

    def clear_review(self, analysis_id: str) -> StoredAnalysis:
        """Take a person's answer back: the document waits for a person again."""
        with self._lock:
            row = self.get_analysis(analysis_id)
            if row is None:
                raise KeyError("Analysis not found.")
            row.review = None
            row.status = "awaiting_person"
            row.final_decision = row.decision
            return row

    def delete_analysis(self, analysis_id: str) -> bool:
        """Remove the result and its review."""
        with self._lock:
            before = len(self._rows)
            self._rows = [r for r in self._rows if r.id != analysis_id]
            return len(self._rows) < before
