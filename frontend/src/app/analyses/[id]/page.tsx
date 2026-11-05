import Link from "next/link";
import { notFound } from "next/navigation";
import { ApiError, apiGet } from "@/lib/api";
import { DecisionPatch } from "@/components/DecisionPatch";
import { EvidenceQuote } from "@/components/EvidenceQuote";
import { Seam } from "@/components/Seam";
import { RulesList } from "@/components/RulesList";
import { ComparisonTable } from "@/components/ComparisonTable";
import { FieldsTable } from "@/components/FieldsTable";
import { ReviewForm } from "@/components/ReviewForm";
import { DECISION, when } from "@/lib/format";
import type { StoredAnalysis } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function Detail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let row: StoredAnalysis;
  try {
    row = await apiGet<StoredAnalysis>(`/api/analyses/${encodeURIComponent(id)}`);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    throw e;
  }
  const r = row.result;
  const f = r.fields;
  const failed = r.rules.filter((x) => x.status === "fail");

  return (
    <div className="mx-auto max-w-6xl px-4 pb-24 pt-8 sm:px-6">
      <Link href="/" className="text-sm text-indigo underline underline-offset-4">
        Back to all results
      </Link>

      <header className="mt-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold sm:text-4xl">{f?.supplierName?.value ?? r.filename}</h1>
          <p className="mt-1 text-ink-soft">
            {f?.quotationNo?.value ?? "No quotation number"}, {r.filename}, checked {when(row.createdAt)}
            {r.mode.ai === "groq" ? `, AI: ${r.mode.model}` : ", AI off"}
          </p>
        </div>
        <DecisionPatch decision={row.finalDecision} large />
      </header>

      {row.review && (
        <section className={`mt-6 rounded-xl border-l-4 p-4 ${DECISION[row.finalDecision].edge} ${DECISION[row.finalDecision].wash}`}>
          <p className="font-semibold">
            A person decided: {row.review.decision}
            {row.review.reviewer ? `, ${row.review.reviewer}` : ""}
          </p>
          <p className="mt-1 text-sm">{row.review.note}</p>
          <p className="mt-1 text-xs text-ink-soft">The system had stopped with: {row.decision}.</p>
        </section>
      )}

      <div className="mt-8 grid gap-10 lg:grid-cols-[1fr_20rem]">
        <div className="min-w-0 space-y-10">
          <section aria-labelledby="why-h">
            <h2 id="why-h" className="text-2xl font-semibold">
              {row.decision === "Approve" ? "Why this passes" : row.decision === "Reject" ? "Why this is rejected" : "Why a person needs to check"}
            </h2>
            {failed.length === 0 && r.uncertainties.length === 0 && (
              <p className="mt-3 text-ink-soft">{r.reasons.join(" ")}</p>
            )}
            <div className="mt-4 space-y-4">
              {failed.flatMap((rule) =>
                rule.findings.map((fi, i) => (
                  <article key={`${rule.ruleId}-${i}`} className="rounded-xl border border-chalk bg-sheet p-4">
                    <h3 className="text-lg font-semibold">
                      <span className={fi.severity === "reject" ? "text-reject" : "text-check"}>{fi.ruleId}</span> {fi.title}
                    </h3>
                    <p className="mt-1 text-sm text-ink-soft">
                      {rule.label}. {fi.detail}
                    </p>
                    <div className="mt-3 space-y-2">
                      {fi.evidence.map((e, k) => (
                        <EvidenceQuote key={k} evidence={e} tone={fi.severity === "reject" ? "reject" : "check"} />
                      ))}
                    </div>
                  </article>
                )),
              )}
              {r.uncertainties.map((u, i) => (
                <article key={i} className="rounded-xl border border-check/40 bg-check-wash/60 p-4">
                  <h3 className="text-lg font-semibold text-check">Not sure: {u.field}</h3>
                  <p className="mt-1 text-sm">{u.reason}</p>
                  {u.quote && (
                    <div className="mt-3">
                      <EvidenceQuote evidence={{ quote: u.quote }} tone="check" />
                    </div>
                  )}
                </article>
              ))}
            </div>
          </section>

          {row.status === "awaiting_person" && (
            <section aria-labelledby="ask-h" className="rounded-xl border-2 border-dashed border-check bg-sheet p-5">
              <h2 id="ask-h" className="text-2xl font-semibold">
                The system stopped here and is asking you
              </h2>
              <ul className="mt-3 list-disc space-y-1 pl-5 text-sm">
                {r.questions.map((q, i) => (
                  <li key={i}>{q.question}</li>
                ))}
              </ul>
              <div className="mt-5">
                <ReviewForm id={row.id} />
              </div>
            </section>
          )}

          <section aria-labelledby="cmp-h">
            <h2 id="cmp-h" className="mb-3 text-2xl font-semibold">
              Compared with the purchase request
            </h2>
            <ComparisonTable rows={r.comparison} />
          </section>

          <section aria-labelledby="rules-h">
            <h2 id="rules-h" className="mb-3 text-2xl font-semibold">
              Company rules
            </h2>
            <RulesList rules={r.rules} />
          </section>

          {f && (
            <section aria-labelledby="fields-h">
              <h2 id="fields-h" className="mb-1 text-2xl font-semibold">
                What was read from the quotation
              </h2>
              <p className="mb-3 text-sm text-ink-soft">Every value comes with the exact text it was taken from. Values without a matching quote are never used.</p>
              <FieldsTable fields={f} />
            </section>
          )}
        </div>

        <aside className="lg:sticky lg:top-6 lg:self-start">
          <div className="rounded-xl border border-chalk bg-sheet p-5">
            <h2 className="mb-4 text-lg font-semibold">The eight steps</h2>
            <Seam trace={r.trace} />
          </div>
        </aside>
      </div>
    </div>
  );
}
