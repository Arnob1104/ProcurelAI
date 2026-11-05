"""Step: final answer. Any reject finding means Reject. Otherwise anything doubtful means a person checks.
Approve only when every rule was tested and none applies. Uncertainty never causes a Reject on its own."""
from __future__ import annotations

from typing import Optional

from ..models import Evidence, HumanQuestion, RuleResult, Uncertainty


def decide(rules: list[RuleResult], uncertainties: list[Uncertainty], fatal: Optional[str]):
    """Returns (decision, reasons, questions)."""
    if fatal:
        return "Needs a person to check", [fatal], [HumanQuestion(question=fatal, rule_id="-", evidence=[])]

    findings = [f for r in rules for f in r.findings]
    rejects = [f for f in findings if f.severity == "reject"]
    checks = [f for f in findings if f.severity == "check"]
    unknown_rules = [r for r in rules if r.status == "unknown"]

    if rejects:
        return "Reject", [f"{f.rule_id}: {f.title}. {f.detail}" for f in rejects], []

    if checks or uncertainties or unknown_rules:
        reasons = [f"{f.rule_id}: {f.title}. {f.detail}" for f in checks] + [
            f"Not sure about {u.field}: {u.reason}" for u in uncertainties
        ]
        questions = [
            HumanQuestion(question=f"{f.title}. Is this acceptable for this purchase?", rule_id=f.rule_id, evidence=f.evidence)
            for f in checks
        ] + [
            HumanQuestion(question=f"Please confirm {u.field}. {u.reason}", rule_id="-", evidence=[Evidence(quote=u.quote)])
            for u in uncertainties
        ]
        return "Needs a person to check", reasons, questions

    return "Approve", [f"All {len(rules)} rule checks were run on text found in the document and none applies."], []
