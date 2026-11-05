"""The company rules, word for word where possible. One place so the API and the UI agree."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuleDef:
    id: str
    severity: str  # "reject" | "check"
    label: str
    assumed: bool = False  # True for rules added from the "Other notes" section


RULES: list[RuleDef] = [
    RuleDef("R1", "reject", "Unit price is more than 3% above the maximum in the purchase request"),
    RuleDef("R2", "reject", "Advance payment is more than 20%"),
    RuleDef("R3", "reject", "The contract has no late-delivery penalty clause"),
    RuleDef("R4", "reject", "The supplier's TIN or BIN is missing"),
    RuleDef("R5", "reject", "Delivery is promised later than 45 days after the purchase order"),
    RuleDef("C1", "check", "Unit price is above the maximum, but by no more than 3%"),
    RuleDef("C2", "check", "Quantity differs from the quantity requested by more than 5%"),
    RuleDef("C3", "check", "Payment terms are unclear, or outside 30 to 60 days after delivery"),
    RuleDef("C4", "check", "Delivery is promised in 31 to 45 days"),
    RuleDef("C5", "check", "VAT is not shown separately at 15%"),
    RuleDef("C6", "check", "The numbers do not add up"),
    RuleDef("C7", "check", "The quotation is valid for less than 30 days"),
    RuleDef("N1", "check", "Late-delivery penalty is at least 0.5% of order value per week of delay", assumed=True),
]


def rule_def(rule_id: str) -> RuleDef:
    for r in RULES:
        if r.id == rule_id:
            return r
    raise KeyError(f"Unknown rule {rule_id}")


def new_result(rule_id: str):
    from ..models import RuleResult

    d = rule_def(rule_id)
    return RuleResult(rule_id=d.id, severity=d.severity, label=d.label, status="pass", findings=[])
