"""The bundled sample quotations and purchase request (backend/data)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

DATA = Path(os.environ.get("DATA_DIR") or Path(__file__).resolve().parents[1] / "data")


def list_samples() -> list[str]:
    d = DATA / "samples"
    return sorted(p.name for p in d.glob("*.pdf")) if d.is_dir() else []


def read_sample(name: str) -> Optional[bytes]:
    if name not in list_samples():  # only names that really exist in the folder
        return None
    return (DATA / "samples" / name).read_bytes()


def read_sample_request_csv() -> Optional[str]:
    p = DATA / "purchase-request.csv"
    return p.read_text(encoding="utf-8") if p.is_file() else None
