import type { Decision } from "@/lib/types";
import { DECISION } from "@/lib/format";

export function DecisionPatch({ decision, large = false }: { decision: Decision; large?: boolean }) {
  return (
    <span className={`patch ${DECISION[decision].patch} ${large ? "px-5 py-3 text-xl" : "px-3 py-1.5 text-sm"}`}>
      {DECISION[decision].short}
    </span>
  );
}
