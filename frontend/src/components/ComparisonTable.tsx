import type { ComparisonRow } from "@/lib/types";
import { D, fmt } from "@/lib/money";

const signed = (p: string | null) => (p === null ? "-" : `${D(p).gt(0) ? "+" : ""}${p}%`);

export function ComparisonTable({ rows }: { rows: ComparisonRow[] }) {
  if (!rows.length) return <p className="text-sm text-ink-soft">No item rows were compared.</p>;
  return (
    <div className="overflow-x-auto rounded-lg border border-chalk bg-sheet">
      <table className="w-full min-w-[34rem] text-left text-sm">
        <thead className="border-b border-chalk bg-paper/60 text-ink-soft">
          <tr>
            <th className="px-3 py-2 font-medium">Item</th>
            <th className="px-3 py-2 text-right font-medium">Quantity asked</th>
            <th className="px-3 py-2 text-right font-medium">Quantity quoted</th>
            <th className="px-3 py-2 text-right font-medium">Maximum price</th>
            <th className="px-3 py-2 text-right font-medium">Price quoted</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-chalk">
          {rows.map((r, i) => {
            const qtyOff = r.qtyDiffPercent !== null && D(r.qtyDiffPercent).abs().gt(5);
            const over = r.priceOverPercent !== null && D(r.priceOverPercent).gt(0);
            return (
              <tr key={i} className="align-top">
                <td className="px-3 py-2">
                  <span className="font-semibold">{r.code}</span> {r.description}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">{r.requestedQty !== null ? fmt(D(r.requestedQty), 0) : "-"}</td>
                <td className={`px-3 py-2 text-right tabular-nums ${qtyOff ? "font-semibold text-check" : ""}`}>
                  {r.quotedQty}
                  <span className="block text-xs font-normal text-ink-soft">{signed(r.qtyDiffPercent)}</span>
                </td>
                <td className="px-3 py-2 text-right tabular-nums">{r.maxUnitPrice ?? "-"}</td>
                <td className={`px-3 py-2 text-right tabular-nums ${over ? "font-semibold text-reject" : ""}`}>
                  {r.quotedUnitPrice}
                  <span className="block text-xs font-normal text-ink-soft">{signed(r.priceOverPercent)}</span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
