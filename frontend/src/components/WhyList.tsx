import { EvidenceQuote } from "./EvidenceQuote";
import type { StoredAnalysis } from "@/lib/types";

/** The reasons behind the system's own answer, each with the exact quote that supports it. */
export function WhyList({ row }: { row: StoredAnalysis }) {
  const r = row.result;
  if (row.decision === "Approve") return null;
  const wanted = row.decision === "Reject" ? "reject" : "check";
  const findings = r.rules.flatMap((rule) => rule.findings).filter((f) => f.severity === wanted);
  const unsure = row.decision === "Reject" ? [] : r.uncertainties;
  if (findings.length === 0 && unsure.length === 0) return null;

  return (
    <ul className="space-y-3">
      {findings.map((f, i) => (
        <li key={`${f.ruleId}-${i}`}>
          <p className="text-sm font-semibold">
            <span className={f.severity === "reject" ? "text-reject" : "text-check"}>{f.ruleId}</span> {f.title}
          </p>
          <p className="text-xs text-ink-soft">{f.detail}</p>
          <div className="mt-1.5 space-y-1.5">
            {f.evidence.map((e, k) => (
              <EvidenceQuote key={k} evidence={e} tone={f.severity} />
            ))}
          </div>
        </li>
      ))}
      {unsure.map((u, i) => (
        <li key={`u-${i}`}>
          <p className="text-sm font-semibold text-check">Not sure: {u.field}</p>
          <p className="text-xs text-ink-soft">{u.reason}</p>
          {u.quote && (
            <div className="mt-1.5">
              <EvidenceQuote evidence={{ quote: u.quote }} tone="check" />
            </div>
          )}
        </li>
      ))}
    </ul>
  );
}
