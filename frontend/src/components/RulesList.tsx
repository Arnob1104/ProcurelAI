import type { RuleResult } from "@/lib/types";
import { RULES } from "@/lib/rules/catalog";

const ICON = {
  pass: { mark: "✓", cls: "bg-approve-wash text-approve", word: "Not triggered" },
  fail: { mark: "✕", cls: "bg-reject-wash text-reject", word: "Triggered" },
  unknown: { mark: "?", cls: "bg-check-wash text-check", word: "Could not be tested" },
} as const;

export function RulesList({ rules }: { rules: RuleResult[] }) {
  const byId = new Map(rules.map((r) => [r.ruleId, r]));
  const group = (severity: "reject" | "check", heading: string) => (
    <div>
      <h3 className="mb-2 text-base font-semibold">{heading}</h3>
      <ul className="divide-y divide-chalk rounded-lg border border-chalk bg-sheet">
        {RULES.filter((r) => r.severity === severity).map((def) => {
          const res = byId.get(def.id);
          const st = res ? ICON[res.status] : null;
          return (
            <li key={def.id} className="flex items-start gap-3 px-3 py-2.5">
              <span
                className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-sm font-bold ${st?.cls ?? "bg-paper text-ink-soft"}`}
                aria-hidden
              >
                {st?.mark ?? "-"}
              </span>
              <div className="min-w-0 text-sm">
                <p>
                  <span className="font-semibold">{def.id}</span> {def.label}
                </p>
                <p className="text-ink-soft">
                  {st ? st.word : "Not run"}
                  {def.assumed ? ". From the company notes; the rules do not say what happens when broken, so it goes to a person." : ""}
                </p>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
  return (
    <div className="grid gap-5 md:grid-cols-2">
      {group("reject", "Reject rules")}
      {group("check", "Needs a person to check rules")}
    </div>
  );
}
