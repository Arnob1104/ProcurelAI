from __future__ import annotations

from typing import Optional, Protocol

from ..models import AnalysisResult, PurchaseRequestItem, StoredAnalysis


class Store(Protocol):
    kind: str  # "supabase" | "memory"

    def get_request(self) -> list[PurchaseRequestItem]: ...
    def replace_request(self, items: list[PurchaseRequestItem]) -> None: ...
    def save_analysis(self, result: AnalysisResult) -> StoredAnalysis: ...
    def list_analyses(self) -> list[StoredAnalysis]: ...
    def get_analysis(self, analysis_id: str) -> Optional[StoredAnalysis]: ...
    def add_review(self, analysis_id: str, decision: str, note: str, reviewer: Optional[str]) -> StoredAnalysis: ...


def status_for(result: AnalysisResult) -> str:
    return "awaiting_person" if result.decision == "Needs a person to check" else "complete"
