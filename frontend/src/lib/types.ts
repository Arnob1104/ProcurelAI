// Shared types for the fixed-step pipeline.

export type Decision = "Approve" | "Reject" | "Needs a person to check";

/** One piece of proof taken from the document. `quote` is always exact document text. */
export interface Evidence {
  quote: string | null;
  /** Used when the proof is something missing from the document. */
  note?: string | null;
}

export interface Finding {
  /** Rule id from the company rules, e.g. R1 (reject) or C3 (check). */
  ruleId: string;
  severity: "reject" | "check";
  title: string;
  detail: string;
  evidence: Evidence[];
}

/** A value read from the document, with the exact text that supports it. */
export interface Sourced<T> {
  value: T;
  quote: string;
  /** Which reader found it. "both" means the AI and the fixed parser agreed. */
  source: "regex" | "llm" | "both";
}

export interface LineItem {
  code: string | null;
  description: string;
  unit: string;
  quantity: string; // as printed, e.g. "12,000"
  unitPrice: string; // as printed, e.g. "472.00"
  lineAmount: string; // as printed
  quote: string; // the table row, exact text
}

/** Everything read from one quotation. Missing means "not found", never "guessed". */
export interface QuoteFields {
  supplierName: Sourced<string> | null;
  quotationNo: Sourced<string> | null;
  quoteDate: Sourced<string> | null;
  prReference: Sourced<string> | null;
  tin: Sourced<string> | null;
  bin: Sourced<string> | null;
  items: Sourced<LineItem>[];
  subtotal: Sourced<string> | null;
  vatRate: Sourced<string> | null; // "15"
  vatAmount: Sourced<string> | null;
  total: Sourced<string> | null;
  vatIncluded: Sourced<boolean> | null; // price stated as VAT included
  advancePercent: Sourced<string> | null; // "10", "0"
  paymentMinDays: Sourced<string> | null;
  paymentMaxDays: Sourced<string> | null;
  paymentUnclear: Sourced<boolean> | null;
  deliveryAmount: Sourced<string> | null;
  deliveryUnit: Sourced<string> | null; // "days" | "weeks"
  penaltyPercent: Sourced<string> | null;
  penaltyPeriod: Sourced<string> | null; // verbatim, e.g. "per week"
  penaltyBasis: Sourced<string> | null; // verbatim, e.g. "of order value"
  penaltyClause: Sourced<string> | null; // the whole clause, exact text
  validityDays: Sourced<string> | null;
}

export interface PurchaseRequestItem {
  prNumber: string;
  item: string;
  description: string;
  unit: string;
  quantityRequested: number;
  maxUnitPrice: string; // decimal string
}

export type RuleStatus = "pass" | "fail" | "unknown";

export interface RuleResult {
  ruleId: string;
  severity: "reject" | "check";
  /** The company rule in plain words. */
  label: string;
  status: RuleStatus;
  findings: Finding[];
  /** Why the rule could not be tested (status "unknown"). */
  unknownReason?: string;
}

export interface ComparisonRow {
  code: string | null;
  description: string;
  requestedQty: number | null;
  quotedQty: string;
  qtyDiffPercent: string | null; // signed, e.g. "-17.5"
  maxUnitPrice: string | null;
  quotedUnitPrice: string;
  priceOverPercent: string | null; // signed, e.g. "2.31"
  quote: string;
}

export interface Uncertainty {
  field: string;
  reason: string;
  quote?: string | null;
}

export interface TraceStep {
  step: string;
  label: string;
  status: "done" | "stopped" | "skipped";
  summary: string;
  ms: number;
}

export interface HumanQuestion {
  question: string;
  ruleId: string;
  evidence: Evidence[];
}

export interface AnalysisResult {
  filename: string;
  mode: { ai: "groq" | "off"; model: string | null };
  fields: QuoteFields | null;
  comparison: ComparisonRow[];
  rules: RuleResult[];
  findings: Finding[];
  uncertainties: Uncertainty[];
  decision: Decision;
  reasons: string[];
  questions: HumanQuestion[];
  trace: TraceStep[];
  rawText: string;
}

export interface HumanReview {
  decision: "Approve" | "Reject";
  note: string;
  reviewer: string | null;
  createdAt: string;
}

export interface StoredAnalysis {
  id: string;
  createdAt: string;
  status: "complete" | "awaiting_person" | "resolved";
  /** The system's own answer. */
  decision: Decision;
  /** The answer that counts: the person's if resolved, otherwise the system's. */
  finalDecision: Decision;
  result: AnalysisResult;
  review: HumanReview | null;
}
