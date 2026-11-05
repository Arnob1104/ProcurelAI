"""The fixed pipeline. Eight steps, always in this order. No step chooses what runs next;
the only branches are two plain if-checks written below: stop early if the PDF cannot be read,
and ask a person if the answer is not a clear Approve or Reject."""
from __future__ import annotations

import asyncio
import operator
import time
from typing import Annotated, Any, Awaitable, Callable, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from .extract.ai_reader import Completer, ai_model, extract_with_ai
from .extract.reconcile import reconcile
from .extract.rules_reader import extract_with_rules
from .models import (
    AnalysisResult, ComparisonRow, HumanQuestion, Mode, PurchaseRequestItem, QuoteFields,
    RuleResult, TraceStep, Uncertainty,
)
from .pdf import pdf_to_text
from .rules.compare import compare_with_request
from .rules.contract import check_contract
from .rules.decide import decide

STEPS = [
    ("ingest", "Read the PDF"),
    ("read_rules", "Read the layout with fixed patterns"),
    ("read_ai", "Read the quotation with the AI"),
    ("verify", "Check every quote against the document"),
    ("compare", "Compare with the purchase request"),
    ("contract", "Check the contract rules"),
    ("decide", "Give the final answer"),
    ("ask_person", "Ask a person"),
]
LABELS = dict(STEPS)


class State(TypedDict, total=False):
    filename: str
    pdf: Optional[bytes]
    raw_text: str
    request: list[PurchaseRequestItem]
    fatal: Optional[str]
    rules_fields: Optional[QuoteFields]
    ai_fields: Optional[QuoteFields]
    fields: Optional[QuoteFields]
    comparison: list[ComparisonRow]
    rule_results: Annotated[list[RuleResult], operator.add]
    uncertainties: Annotated[list[Uncertainty], operator.add]
    decision: Optional[str]
    reasons: list[str]
    questions: list[HumanQuestion]
    trace: Annotated[list[TraceStep], operator.add]


# A step returns (state update, one-line summary, status).
StepResult = tuple[dict[str, Any], str, str]


def step(step_id: str):
    """Wrap a step so it is timed and leaves a line in the trace."""

    def deco(fn: Callable[..., Awaitable[StepResult]]):
        async def node(state: State, config) -> dict[str, Any]:
            t0 = time.perf_counter()
            update, summary, status = await fn(state, config)
            ms = int((time.perf_counter() - t0) * 1000)
            update["trace"] = [TraceStep(step=step_id, label=LABELS[step_id], status=status, summary=summary, ms=ms)]
            return update

        node.__name__ = step_id
        return node

    return deco


@step("ingest")
async def ingest(state: State, config) -> StepResult:
    text = state.get("raw_text") or ""
    if not text and state.get("pdf"):
        try:
            text = await asyncio.to_thread(pdf_to_text, state["pdf"])
        except Exception:  # noqa: BLE001 - any parse error means a person must look at the file
            why = "The file could not be opened as a PDF."
            return {"raw_text": "", "fatal": why}, why, "stopped"
    if len(text.replace(" ", "").replace("\n", "").replace("\t", "")) < 40:
        why = "This PDF has no readable text. It may be a scan, so a person needs to read it."
        return {"raw_text": text, "fatal": why}, why, "stopped"
    return {"raw_text": text}, f"Read {len(text.splitlines())} lines of text.", "done"


@step("read_rules")
async def read_rules(state: State, config) -> StepResult:
    f = extract_with_rules(state["raw_text"])
    n = sum(1 for k in type(f).model_fields if (len(getattr(f, k)) if k == "items" else getattr(f, k)))
    return {"rules_fields": f}, f"Found {len(f.items)} item row(s) and {n} fields.", "done"


@step("read_ai")
async def read_ai(state: State, config) -> StepResult:
    complete: Optional[Completer] = (config.get("configurable") or {}).get("complete")
    if complete is None:
        return {"ai_fields": None}, "AI is off (no GROQ_API_KEY). Only the fixed reader was used.", "skipped"
    fields, error = await extract_with_ai(state["raw_text"], complete)
    if error:
        return {"ai_fields": None}, f"The AI call failed ({error}). Only the fixed reader was used.", "skipped"
    return {"ai_fields": fields}, f"The AI returned {len(fields.items)} item row(s).", "done"


@step("verify")
async def verify(state: State, config) -> StepResult:
    fields, unc = reconcile(state["raw_text"], state["rules_fields"], state.get("ai_fields"))
    if not fields.items and not unc:
        why = "No item rows could be read from this quotation, so a person needs to read it."
        return {"fields": fields, "fatal": why}, why, "stopped"
    both = sum(1 for k in type(fields).model_fields if k != "items" and getattr(fields, k) is not None and getattr(fields, k).source == "both")
    if unc:
        summary = f"{len(unc)} reading(s) could not be confirmed."
    else:
        summary = "Every value has an exact quote." + (f" {both} fields agreed between the AI and the fixed reader." if state.get("ai_fields") else "")
    return {"fields": fields, "uncertainties": unc}, summary, "done"


@step("compare")
async def compare(state: State, config) -> StepResult:
    rules, rows, unc = compare_with_request(state["fields"], state["request"])
    failed = [r.rule_id for r in rules if r.status == "fail"]
    summary = f"Rules triggered: {', '.join(failed)}." if failed else "Price and quantity match the request."
    return {"comparison": rows, "rule_results": rules, "uncertainties": unc}, summary, "done"


@step("contract")
async def contract(state: State, config) -> StepResult:
    rules, unc = check_contract(state["fields"], state["raw_text"], state.get("uncertainties", []))
    failed = [r.rule_id for r in rules if r.status == "fail"]
    summary = f"Rules triggered: {', '.join(failed)}." if failed else "No contract rule is triggered."
    return {"rule_results": rules, "uncertainties": unc}, summary, "done"


@step("decide")
async def decide_step(state: State, config) -> StepResult:
    decision, reasons, questions = decide(state.get("rule_results", []), state.get("uncertainties", []), state.get("fatal"))
    return {"decision": decision, "reasons": reasons, "questions": questions}, decision, "done"


@step("ask_person")
async def ask_person(state: State, config) -> StepResult:
    return {}, f"Stopped. {len(state['questions'])} question(s) are waiting for a person.", "stopped"


def _build():
    g = StateGraph(State)
    g.add_node("ingest", ingest)
    g.add_node("read_rules", read_rules)
    g.add_node("read_ai", read_ai)
    g.add_node("verify", verify)
    g.add_node("compare", compare)
    g.add_node("contract", contract)
    g.add_node("decide", decide_step)
    g.add_node("ask_person", ask_person)

    g.add_edge(START, "ingest")
    g.add_conditional_edges("ingest", lambda s: "decide" if s.get("fatal") else "read_rules",
                            {"decide": "decide", "read_rules": "read_rules"})
    g.add_edge("read_rules", "read_ai")
    g.add_edge("read_ai", "verify")
    g.add_conditional_edges("verify", lambda s: "decide" if s.get("fatal") else "compare",
                            {"decide": "decide", "compare": "compare"})
    g.add_edge("compare", "contract")
    g.add_edge("contract", "decide")
    g.add_conditional_edges("decide", lambda s: "ask_person" if s.get("decision") == "Needs a person to check" else "end",
                            {"ask_person": "ask_person", "end": END})
    g.add_edge("ask_person", END)
    return g.compile()


graph = _build()


async def run_pipeline(
    filename: str,
    request: list[PurchaseRequestItem],
    pdf: Optional[bytes] = None,
    text: Optional[str] = None,
    complete: Optional[Completer] = None,
) -> AnalysisResult:
    """Run the eight steps on one quotation. Pass `pdf` bytes, or `text` (used by tests)."""
    out = await graph.ainvoke(
        {
            "filename": filename, "pdf": pdf, "raw_text": text or "", "request": request, "fatal": None,
            "rule_results": [], "uncertainties": [], "trace": [], "comparison": [], "reasons": [], "questions": [],
        },
        config={"configurable": {"complete": complete}},
    )

    # Steps that never ran (because the PDF could not be read) are shown as skipped.
    trace: list[TraceStep] = list(out["trace"])
    ran = {t.step for t in trace}
    for sid, label in STEPS:
        if sid not in ran:
            trace.append(TraceStep(step=sid, label=label, status="skipped", summary="Not run.", ms=0))
    order = [sid for sid, _ in STEPS]
    trace.sort(key=lambda t: order.index(t.step))

    rules = out.get("rule_results", [])
    return AnalysisResult(
        filename=filename,
        mode=Mode(ai="groq", model=ai_model()) if complete else Mode(ai="off", model=None),
        fields=out.get("fields"),
        comparison=out.get("comparison", []),
        rules=rules,
        findings=[f for r in rules for f in r.findings],
        uncertainties=out.get("uncertainties", []),
        decision=out["decision"],
        reasons=out.get("reasons", []),
        questions=out.get("questions", []),
        trace=trace,
        raw_text=out.get("raw_text", ""),
    )
