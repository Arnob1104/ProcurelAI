import type { Decision } from "./types";

export const DECISION: Record<Decision, { patch: string; text: string; wash: string; edge: string; short: string }> = {
  Approve: { patch: "bg-approve-wash text-approve", text: "text-approve", wash: "bg-approve-wash", edge: "border-approve", short: "Approve" },
  Reject: { patch: "bg-reject-wash text-reject", text: "text-reject", wash: "bg-reject-wash", edge: "border-reject", short: "Reject" },
  "Needs a person to check": {
    patch: "bg-check-wash text-check", text: "text-check", wash: "bg-check-wash", edge: "border-check", short: "Needs a person to check",
  },
};

export function sourceLabel(s: "regex" | "llm" | "both"): string {
  return s === "both" ? "AI and fixed reader agree" : s === "regex" ? "Fixed reader" : "AI";
}

export function when(iso: string): string {
  return new Date(iso).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}
