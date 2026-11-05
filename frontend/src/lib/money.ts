import Decimal from "decimal.js";

Decimal.set({ precision: 40, rounding: Decimal.ROUND_HALF_UP });

export const D = (v: Decimal.Value) => new Decimal(v);

/** Parse "5,664,000.00" or "12,000" or "0.5". Returns null if it is not a plain number. */
export function parseNumber(text: string | null | undefined): Decimal | null {
  if (text == null) return null;
  const cleaned = String(text).trim().replace(/,/g, "");
  if (!/^-?\d+(\.\d+)?$/.test(cleaned)) return null;
  return new Decimal(cleaned);
}

export function fmt(d: Decimal, dp = 2): string {
  const [i, f] = d.toFixed(dp).split(".");
  const withCommas = i.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return f ? `${withCommas}.${f}` : withCommas;
}

/** True when two money amounts are equal within one paisa (rounding on printed documents). */
export function sameMoney(a: Decimal, b: Decimal): boolean {
  return a.minus(b).abs().lte(new Decimal("0.01"));
}
