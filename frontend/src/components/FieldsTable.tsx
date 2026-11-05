import type { QuoteFields, Sourced } from "@/lib/types";
import { sourceLabel } from "@/lib/format";

type Row = { label: string; f: Sourced<unknown> | null; show?: string };

export function FieldsTable({ fields }: { fields: QuoteFields }) {
  const del = fields.deliveryAmount && fields.deliveryUnit ? `Within ${fields.deliveryAmount.value} ${fields.deliveryUnit.value} of the purchase order` : undefined;
  const pay = fields.paymentMinDays && fields.paymentMaxDays
    ? fields.paymentMinDays.value === fields.paymentMaxDays.value
      ? `${fields.paymentMinDays.value} days after delivery`
      : `${fields.paymentMinDays.value} to ${fields.paymentMaxDays.value} days after delivery`
    : undefined;
  const rows: Row[] = [
    { label: "Supplier", f: fields.supplierName },
    { label: "Quotation number", f: fields.quotationNo },
    { label: "Quotation date", f: fields.quoteDate },
    { label: "Purchase request", f: fields.prReference },
    { label: "TIN", f: fields.tin },
    { label: "BIN", f: fields.bin },
    ...fields.items.map((i, n): Row => ({
      label: fields.items.length > 1 ? `Item ${n + 1}` : "Item",
      f: i,
      show: `${i.value.code ?? ""} ${i.value.description}: ${i.value.quantity} ${i.value.unit} at ${i.value.unitPrice} = ${i.value.lineAmount}`,
    })),
    { label: "Subtotal", f: fields.subtotal },
    { label: "VAT", f: fields.vatAmount, show: fields.vatRate && fields.vatAmount ? `${fields.vatRate.value}%: ${fields.vatAmount.value}` : undefined },
    { label: "Prices include VAT", f: fields.vatIncluded, show: fields.vatIncluded ? "Yes" : undefined },
    { label: "Total", f: fields.total },
    { label: "Advance payment", f: fields.advancePercent, show: fields.advancePercent ? `${fields.advancePercent.value}%` : undefined },
    { label: "Payment", f: fields.paymentMinDays, show: pay },
    { label: "Delivery promise", f: fields.deliveryAmount, show: del },
    { label: "Late-delivery penalty", f: fields.penaltyClause, show: fields.penaltyPercent ? `${fields.penaltyPercent.value}% ${fields.penaltyPeriod?.value ?? "(period not stated)"} ${fields.penaltyBasis?.value ?? "(basis not stated)"}` : undefined },
    { label: "Valid for", f: fields.validityDays, show: fields.validityDays ? `${fields.validityDays.value} days` : undefined },
  ];
  const shown = rows.filter((r) => r.f || r.label !== "Prices include VAT");
  return (
    <div className="overflow-x-auto rounded-lg border border-chalk bg-sheet">
      <table className="w-full min-w-[36rem] text-left text-sm">
        <thead className="border-b border-chalk bg-paper/60 text-ink-soft">
          <tr>
            <th className="w-40 px-3 py-2 font-medium">Field</th>
            <th className="px-3 py-2 font-medium">Value</th>
            <th className="px-3 py-2 font-medium">Exact text in the document</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-chalk">
          {shown.map((r, i) => (
            <tr key={i} className="align-top">
              <td className="px-3 py-2 text-ink-soft">{r.label}</td>
              <td className="px-3 py-2">
                {r.f ? (
                  <>
                    {r.show ?? String((r.f as Sourced<unknown>).value)}
                    <span className="block text-xs text-ink-soft">{sourceLabel(r.f.source)}</span>
                  </>
                ) : (
                  <span className="text-ink-soft">Not found</span>
                )}
              </td>
              <td className="px-3 py-2">{r.f ? <span className="quote">{r.f.quote}</span> : null}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
