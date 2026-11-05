// The company rules, word for word where possible. One place so the UI and the engine agree.

export interface RuleDef {
  id: string;
  severity: "reject" | "check";
  label: string;
  /** True for rules we added from the "Other notes" section, where the rules do not say what happens when broken. */
  assumed?: boolean;
}

export const RULES: RuleDef[] = [
  { id: "R1", severity: "reject", label: "Unit price is more than 3% above the maximum in the purchase request" },
  { id: "R2", severity: "reject", label: "Advance payment is more than 20%" },
  { id: "R3", severity: "reject", label: "The contract has no late-delivery penalty clause" },
  { id: "R4", severity: "reject", label: "The supplier's TIN or BIN is missing" },
  { id: "R5", severity: "reject", label: "Delivery is promised later than 45 days after the purchase order" },
  { id: "C1", severity: "check", label: "Unit price is above the maximum, but by no more than 3%" },
  { id: "C2", severity: "check", label: "Quantity differs from the quantity requested by more than 5%" },
  { id: "C3", severity: "check", label: "Payment terms are unclear, or outside 30 to 60 days after delivery" },
  { id: "C4", severity: "check", label: "Delivery is promised in 31 to 45 days" },
  { id: "C5", severity: "check", label: "VAT is not shown separately at 15%" },
  { id: "C6", severity: "check", label: "The numbers do not add up" },
  { id: "C7", severity: "check", label: "The quotation is valid for less than 30 days" },
  {
    id: "N1",
    severity: "check",
    label: "Late-delivery penalty is at least 0.5% of order value per week of delay",
    assumed: true,
  },
];

export const ruleDef = (id: string): RuleDef => {
  const r = RULES.find((x) => x.id === id);
  if (!r) throw new Error(`Unknown rule ${id}`);
  return r;
};
