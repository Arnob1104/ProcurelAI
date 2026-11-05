import { apiGet, type Health } from "@/lib/api";
import { UploadPanel } from "@/components/UploadPanel";
import { RequestActions } from "@/components/RequestActions";
import { ResultsTable } from "@/components/ResultsTable";
import type { PurchaseRequestItem } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function Home() {
  let health: Health | null = null;
  let request: PurchaseRequestItem[] = [];
  let error: string | null = null;
  try {
    [health, request] = await Promise.all([
      apiGet<Health>("/api/health"),
      apiGet<PurchaseRequestItem[]>("/api/purchase-request"),
    ]);
  } catch (e) {
    error = e instanceof Error ? e.message : "Could not reach the API.";
  }
  if (health?.error) error = health.error;

  const samples = health?.samples ?? [];
  const prNumbers = [...new Set(request.map((r) => r.prNumber))];

  return (
    <div className="mx-auto max-w-6xl px-4 pb-20 pt-8 sm:px-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm text-ink-soft">ProcurelAI</p>
          <h1 className="mt-1 text-4xl font-bold sm:text-5xl">AI Powered Supplier quote review</h1>
          <p className="mt-3 max-w-xl text-ink-soft">
            Every quotation is read, compared with the purchase request and checked against the company rules in the same eight steps. When the system is not sure, it stops and asks a person.
          </p>
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

      <ResultsTable />
    </div>
  );
}
