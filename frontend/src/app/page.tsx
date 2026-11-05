import Link from "next/link";
import { apiGet, type Health } from "@/lib/api";
import { DecisionPatch } from "@/components/DecisionPatch";
import { UploadPanel } from "@/components/UploadPanel";
import { RequestActions } from "@/components/RequestActions";
import { DECISION, when } from "@/lib/format";
import type { Decision, PurchaseRequestItem, StoredAnalysis } from "@/lib/types";

export const dynamic = "force-dynamic";

function Chip({ ok, children }: { ok: boolean; children: React.ReactNode }) {
  return (
    <span className={`rounded-full border px-3 py-1 text-xs font-medium ${ok ? "border-approve/40 bg-approve-wash text-approve" : "border-check/40 bg-check-wash text-check"}`}>
      {children}
    </span>
  );
}

export default async function Home() {
  let health: Health | null = null;
  let request: PurchaseRequestItem[] = [];
  let rows: StoredAnalysis[] = [];
  let error: string | null = null;
  try {
    [health, request, rows] = await Promise.all([
      apiGet<Health>("/api/health"),
      apiGet<PurchaseRequestItem[]>("/api/purchase-request"),
      apiGet<StoredAnalysis[]>("/api/analyses"),
    ]);
  } catch (e) {
    error = e instanceof Error ? e.message : "Could not reach the API.";
  }
  if (health?.error) error = health.error;

  const samples = health?.samples ?? [];
  const count = (d: Decision) => rows.filter((r) => r.finalDecision === d).length;
  const waiting = rows.filter((r) => r.status === "awaiting_person").length;
  const prNumbers = [...new Set(request.map((r) => r.prNumber))];

  return (
    <div className="mx-auto max-w-6xl px-4 pb-20 pt-8 sm:px-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm text-ink-soft">Aamar Garments Ltd (fictional)</p>
          <h1 className="mt-1 text-4xl font-bold sm:text-5xl">Supplier quote review</h1>
          <p className="mt-3 max-w-xl text-ink-soft">
            Every quotation is read, compared with the purchase request and checked against the company rules in the same eight steps. When the system is not sure, it stops and asks a person.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {health && (
            <>
              <Chip ok={health.storage === "supabase"}>{health.storage === "supabase" ? "Storage: Supabase" : "Storage: temporary, lost on restart"}</Chip>
              <Chip ok={health.ai.enabled}>{health.ai.enabled ? `AI: Groq ${health.ai.model}` : "AI: off, fixed reader only"}</Chip>
            </>
          )}
        </div>
      </header>

      {error && (
        <p className="mt-6 rounded-lg border border-reject/40 bg-reject-wash p-4 text-sm text-reject" role="alert">
          {error}
        </p>
      )}

      <div className="mt-8 grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <section aria-labelledby="pr-h" className="rounded-xl border border-chalk bg-sheet p-5">
          <h2 id="pr-h" className="text-xl font-semibold">
            Purchase request {prNumbers.join(", ")}
          </h2>
          {request.length ? (
            <div className="mt-3 overflow-x-auto">
              <table className="w-full min-w-[28rem] text-left text-sm">
                <thead className="border-b border-chalk text-ink-soft">
                  <tr>
                    <th className="py-2 pr-3 font-medium">Item</th>
                    <th className="py-2 pr-3 font-medium">Quantity</th>
                    <th className="py-2 text-right font-medium">Maximum unit price (BDT)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-chalk">
                  {request.map((r) => (
                    <tr key={`${r.prNumber}-${r.item}`}>
                      <td className="py-2 pr-3">
                        <span className="font-semibold">{r.item}</span> {r.description}
                      </td>
                      <td className="py-2 pr-3 tabular-nums">
                        {r.quantityRequested.toLocaleString("en-US")} {r.unit}
                      </td>
                      <td className="py-2 text-right tabular-nums">{r.maxUnitPrice}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="mt-2 text-sm text-ink-soft">No purchase request is loaded yet. Quotes are compared against it, so load it first.</p>
          )}
          <RequestActions hasSample={health?.hasSampleRequest ?? false} hasRequest={request.length > 0} />
        </section>

        <UploadPanel ready={request.length > 0} samples={samples} />
      </div>

      <section aria-labelledby="res-h" className="mt-10">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2 id="res-h" className="text-2xl font-semibold">
            Results
          </h2>
          {rows.length > 0 && (
            <p className="text-sm text-ink-soft">
              {rows.length} documents: {count("Approve")} approved, {count("Reject")} rejected, {waiting} waiting for a person
            </p>
          )}
        </div>

        {rows.length === 0 ? (
          <p className="mt-4 rounded-xl border border-dashed border-chalk-deep bg-sheet/70 p-8 text-center text-ink-soft">
            Nothing checked yet. Add supplier PDFs above to see an answer and the exact text behind it.
          </p>
        ) : (
          <div className="mt-4 overflow-x-auto rounded-xl border border-chalk bg-sheet">
            <table className="w-full min-w-[44rem] text-left text-sm">
              <thead className="border-b border-chalk bg-paper/60 text-ink-soft">
                <tr>
                  <th className="px-4 py-3 font-medium">Supplier</th>
                  <th className="px-4 py-3 font-medium">Item</th>
                  <th className="px-4 py-3 text-right font-medium">Price vs maximum</th>
                  <th className="px-4 py-3 text-right font-medium">Quantity</th>
                  <th className="px-4 py-3 font-medium">Answer</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-chalk">
                {rows.map((r) => {
                  const c = r.result.comparison[0];
                  return (
                    <tr key={r.id} className="align-top hover:bg-paper/50">
                      <td className="px-4 py-3">
                        <Link href={`/analyses/${r.id}`} className="font-semibold text-indigo underline decoration-chalk-deep underline-offset-4 hover:decoration-indigo">
                          {r.result.fields?.supplierName?.value ?? r.result.filename}
                        </Link>
                        <span className="block text-xs text-ink-soft">
                          {r.result.fields?.quotationNo?.value ?? "No quotation number"}, {r.result.filename}, {when(r.createdAt)}
                        </span>
                      </td>
                      <td className="px-4 py-3">{c ? `${c.code ?? ""} ${c.description}` : "-"}</td>
                      <td className="px-4 py-3 text-right tabular-nums">
                        {c ? (
                          <>
                            {c.quotedUnitPrice}
                            <span className="block text-xs text-ink-soft">max {c.maxUnitPrice ?? "-"}</span>
                          </>
                        ) : (
                          "-"
                        )}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">
                        {c ? (
                          <>
                            {c.quotedQty}
                            <span className="block text-xs text-ink-soft">asked {c.requestedQty?.toLocaleString("en-US") ?? "-"}</span>
                          </>
                        ) : (
                          "-"
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <DecisionPatch decision={r.finalDecision} />
                        {r.status === "awaiting_person" && <span className="mt-1 block text-xs text-check">Waiting for a person</span>}
                        {r.status === "resolved" && <span className={`mt-1 block text-xs ${DECISION[r.finalDecision].text}`}>Decided by a person</span>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
