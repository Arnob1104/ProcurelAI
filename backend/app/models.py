"""Shared data shapes. JSON uses camelCase so the Next.js frontend reads it directly."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

Decision = Literal["Approve", "Reject", "Needs a person to check"]


class Model(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Evidence(Model):
    """One piece of proof. `quote` is always exact document text (or None when something is missing)."""

    quote: Optional[str] = None
    note: Optional[str] = None


class Finding(Model):
    rule_id: str
    severity: Literal["reject", "check"]
    title: str
    detail: str
    evidence: list[Evidence] = []


class LineItem(Model):
    code: Optional[str] = None
    description: str
    unit: str
    quantity: str  # as printed, e.g. "12,000"
    unit_price: str
    line_amount: str
    quote: str  # the table row, exact text


class Sourced(Model):
    """A value read from the document, with the exact text that supports it."""

    value: Any
    quote: str
    source: Literal["regex", "llm", "both"]


class QuoteFields(Model):
    """Everything read from one quotation. None means 'not found', never 'guessed'."""

    supplier_name: Optional[Sourced] = None
    quotation_no: Optional[Sourced] = None
    quote_date: Optional[Sourced] = None
    pr_reference: Optional[Sourced] = None
    tin: Optional[Sourced] = None
    bin: Optional[Sourced] = None
    items: list[Sourced] = []  # each .value is a LineItem
    subtotal: Optional[Sourced] = None
    vat_rate: Optional[Sourced] = None
    vat_amount: Optional[Sourced] = None
    total: Optional[Sourced] = None
    vat_included: Optional[Sourced] = None
    advance_percent: Optional[Sourced] = None
    payment_min_days: Optional[Sourced] = None
    payment_max_days: Optional[Sourced] = None
    payment_unclear: Optional[Sourced] = None
    delivery_amount: Optional[Sourced] = None
    delivery_unit: Optional[Sourced] = None
    penalty_percent: Optional[Sourced] = None
    penalty_period: Optional[Sourced] = None
    penalty_basis: Optional[Sourced] = None
    penalty_clause: Optional[Sourced] = None
    validity_days: Optional[Sourced] = None


class PurchaseRequestItem(Model):
    pr_number: str
    item: str
    description: str
    unit: str
    quantity_requested: int
    max_unit_price: str  # decimal string, e.g. "6.50"


class Uncertainty(Model):
    field: str
    reason: str
    quote: Optional[str] = None


class RuleResult(Model):
    rule_id: str
    severity: Literal["reject", "check"]
    label: str
    status: Literal["pass", "fail", "unknown"] = "pass"
    findings: list[Finding] = []
    unknown_reason: Optional[str] = None


class ComparisonRow(Model):
    code: Optional[str] = None
    description: str
    requested_qty: Optional[int] = None
    quoted_qty: str
    qty_diff_percent: Optional[str] = None
    max_unit_price: Optional[str] = None
    quoted_unit_price: str
    price_over_percent: Optional[str] = None
    quote: str


class TraceStep(Model):
    step: str
    label: str
    status: Literal["done", "stopped", "skipped"]
    summary: str
    ms: int


class HumanQuestion(Model):
    question: str
    rule_id: str
    evidence: list[Evidence] = []


class Mode(Model):
    ai: Literal["groq", "off"]
    model: Optional[str] = None


class AnalysisResult(Model):
    filename: str
    mode: Mode
    fields: Optional[QuoteFields] = None
    comparison: list[ComparisonRow] = []
    rules: list[RuleResult] = []
    findings: list[Finding] = []
    uncertainties: list[Uncertainty] = []
    decision: Decision
    reasons: list[str] = []
    questions: list[HumanQuestion] = []
    trace: list[TraceStep] = []
    raw_text: str = ""


class HumanReview(Model):
    decision: Literal["Approve", "Reject"]
    note: str
    reviewer: Optional[str] = None
    created_at: str


class StoredAnalysis(Model):
    id: str
    created_at: str
    status: Literal["complete", "awaiting_person", "resolved"]
    decision: Decision  # the system's own answer
    final_decision: Decision  # the answer that counts (the person's, once resolved)
    result: AnalysisResult
    review: Optional[HumanReview] = None


def dump(model: BaseModel) -> dict[str, Any]:
    """Model to a JSON-ready dict in camelCase."""
    return model.model_dump(by_alias=True, mode="json")
