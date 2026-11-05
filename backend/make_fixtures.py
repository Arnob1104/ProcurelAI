"""Writes the small text fixtures used by the 'never guess' tests."""
from pathlib import Path
from app.pdf import pdf_to_text

d = Path("data/samples")
fx = Path("tests/fixtures")
fx.mkdir(exist_ok=True, parents=True)
t5 = pdf_to_text((d / "supplier-pack-05.pdf").read_bytes())
t1 = pdf_to_text((d / "supplier-pack-01.pdf").read_bytes())
(fx / "pack-05.txt").write_text(t5)
# TIN printed with a letter inside the number: present but not readable.
assert "TIN: 101458013391" in t1
(fx / "odd-tin.txt").write_text(t1.replace("TIN: 101458013391", "TIN: 1014-58O13391"))
# An item that is not in the purchase request.
assert "A Cotton twill fabric, 280 gsm 12,000 metre" in t1
(fx / "unknown-item.txt").write_text(t1.replace("A Cotton twill fabric, 280 gsm 12,000 metre", "A Denim fabric, 340 gsm 12,000 metre"))
print("fixtures written")
