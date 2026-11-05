from __future__ import annotations

import os
from typing import Optional

from .base import Store

_store: Optional[Store] = None


def get_store() -> Store:
    """Supabase when both keys are set, otherwise temporary in-memory storage."""
    global _store
    if _store is None:
        if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
            from .supabase_store import SupabaseStore
            _store = SupabaseStore()
        else:
            from .memory import MemoryStore
            _store = MemoryStore()
    return _store


def reset_store() -> None:
    """Used by tests."""
    global _store
    _store = None
