from __future__ import annotations

import csv
import io
import re

from .models import PurchaseRequestItem


def parse_purchase_request_csv(text: str) -> list[PurchaseRequestItem]:
    """Read purchase-request.csv. Raises ValueError with a plain message if a column or number is wrong."""
    rows = list(csv.reader(io.StringIO(text.lstrip("\ufeff"))))
    rows = [r for r in rows if any(c.strip() for c in r)]
    if len(rows) < 2:
        raise ValueError("The purchase request file has no rows.")
    head = [h.strip().lower() for h in rows[0]]

    def col(name: str) -> int:
        for i, h in enumerate(head):
            if h.startswith(name):
                return i
        raise ValueError(f'The purchase request file is missing the "{name}" column.')

    i_pr, i_item, i_desc, i_unit = col("pr number"), col("item"), col("description"), col("unit")
    i_qty, i_max = col("quantity"), col("maximum unit price")

    out: list[PurchaseRequestItem] = []
    for n, r in enumerate(rows[1:], start=2):
        qty_s, max_s = r[i_qty].strip(), r[i_max].strip()
        if not re.fullmatch(r"\d+", qty_s) or int(qty_s) <= 0:
            raise ValueError(f'Row {n}: quantity "{qty_s}" is not a whole number.')
        if not re.fullmatch(r"\d+(\.\d+)?", max_s):
            raise ValueError(f'Row {n}: maximum unit price "{max_s}" is not a number.')
        out.append(
            PurchaseRequestItem(
                pr_number=r[i_pr].strip(), item=r[i_item].strip(), description=r[i_desc].strip(),
                unit=r[i_unit].strip(), quantity_requested=int(qty_s), max_unit_price=max_s,
            )
        )
    return out
