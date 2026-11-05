"use client";

import Link from "next/link";
import { DecisionPatch } from "./DecisionPatch";
import { DeleteButton } from "./DeleteButton";
import { PersonDecision } from "./PersonDecision";
import { WhyList } from "./WhyList";
import { DECISION, when } from "@/lib/format";
import { useSession } from "@/lib/session";
import type { Decision } from "@/lib/types";

export function ResultsTable() {
  const { rows } = useSession();
  const count = (d: Decision) => rows.filter((r) => r.finalDecision === d).length;
  const waiting = rows.filter((r) => r.decision === "Needs a person to check" && !r.review).length;

  return (
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
      {rows.length > 0 && <p className="mt-1 text-xs text-ink-soft">Results are kept only while this page stays open. Reloading the window clears them.</p>}

      {rows.length === 0 ? (
        <p className="mt-4 rounded-xl border border-dashed border-chalk-deep bg-sheet/70 p-8 text-center text-ink-soft">
          Nothing checked yet. Add supplier PDFs above to see an answer and the exact text behind it.
        </p>
      ) : (
        <div className="mt-4 overflow-x-auto rounded-xl border border-chalk bg-sheet">
          <table className="w-full min-w-[56rem] text-left text-sm">
            <thead className="border-b border-chalk bg-paper/60 text-ink-soft">
              <tr>
                <th className="px-4 py-3 font-medium">Supplier</th>
                <th className="px-4 py-3 font-medium">Item</th>
                <th className="px-4 py-3 text-right font-medium">Price vs maximum</th>
                <th className="px-4 py-3 text-right font-medium">Quantity</th>
                <th className="px-4 py-3 font-medium">Answer</th>
                <th className="px-4 py-3 font-medium">Why, with the exact text</th>
                <th className="px-4 py-3 font-medium">
                  <span className="sr-only">Actions</span>
                </th>
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
                      {r.decision === "Needs a person to check" && !r.review && <span className="mt-1 block text-xs text-check">Waiting for a person</span>}
                      {r.review && <span className={`mt-1 block text-xs ${DECISION[r.finalDecision].text}`}>{r.finalDecision === "Approve" ? "Accepted" : "Rejected"} by a person</span>}
                      <PersonDecision row={r} />
                    </td>
                    <td className="max-w-sm px-4 py-3">
                      {!r.review && <WhyList row={r} />}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <DeleteButton id={r.id} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
