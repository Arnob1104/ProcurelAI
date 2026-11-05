import pytest

pytest.importorskip("supabase")

from app.models import dump
from app.store.supabase_store import SupabaseStore
from app.models import AnalysisResult, Mode


def _row(human_reviews):
    result = AnalysisResult(filename="x.pdf", mode=Mode(ai="off"), decision="Needs a person to check")
    return {
        "id": "1", "created_at": "2026-11-05T00:00:00+00:00", "status": "resolved",
        "decision": "Needs a person to check", "final_decision": "Approve",
        "result": dump(result), "human_reviews": human_reviews,
    }


REVIEW = {"decision": "Approve", "note": "ok then", "reviewer": None, "created_at": "2026-11-05T00:00:00+00:00"}


@pytest.mark.parametrize("shape", [REVIEW, [REVIEW]])
def test_review_as_object_or_list(shape):
    assert SupabaseStore._to_stored(_row(shape)).review.decision == "Approve"


@pytest.mark.parametrize("shape", [None, []])
def test_no_review(shape):
    assert SupabaseStore._to_stored(_row(shape)).review is None
