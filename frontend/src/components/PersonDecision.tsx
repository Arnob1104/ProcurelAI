"use client";

import { useState } from "react";
import { useSession } from "@/lib/session";
import type { StoredAnalysis } from "@/lib/types";

/** Approve / Reject buttons for a document the system stopped on. The person can change the answer any time. */
export function PersonDecision({ row }: { row: StoredAnalysis }) {
  const session = useSession();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [changing, setChanging] = useState(false);
  if (row.decision !== "Needs a person to check") return null;

  const chosen = row.review?.decision ?? null;

  async function run(fn: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      setChanging(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save.");
    } finally {
      setBusy(false);
    }
  }

  const style = (d: "Approve" | "Reject") =>
    chosen === d
      ? d === "Approve" ? "border-approve bg-approve text-white" : "border-reject bg-reject text-white"
      : d === "Approve" ? "border-approve text-approve hover:bg-approve-wash" : "border-reject text-reject hover:bg-reject-wash";

  if (chosen && !changing) {
    return (
      <button type="button" onClick={() => setChanging(true)} className="mt-1 text-xs text-ink-soft underline underline-offset-2 hover:text-ink">
        Change decision
      </button>
    );
  }

  return (
    <div className="mt-2">
      <p className="mb-1 text-xs text-ink-soft">{chosen ? `Currently ${chosen === "Approve" ? "accepted" : "rejected"}. Change it:` : "A person must decide:"}</p>
      <div className="flex flex-wrap items-center gap-2">
        {(["Approve", "Reject"] as const).map((d) => (
          <button
            key={d}
            type="button"
            disabled={busy || chosen === d}
            aria-pressed={chosen === d}
            onClick={() => run(() => session.decide(row.id, d))}
            className={`rounded-md border-2 px-3 py-1 text-xs font-semibold disabled:cursor-default ${style(d)} ${busy ? "opacity-60" : ""}`}
          >
            {d === "Approve" ? "Accept" : "Reject"}
          </button>
        ))}
        {chosen && (
          <button
            type="button"
            disabled={busy}
            onClick={() => setChanging(false)}
            className="text-xs text-ink-soft underline underline-offset-2 hover:text-ink"
          >
            Cancel
          </button>
        )}
        {chosen && (
          <button
            type="button"
            disabled={busy}
            onClick={() => run(() => session.undo(row.id))}
            className="text-xs text-ink-soft underline underline-offset-2 hover:text-ink"
          >
            Undo
          </button>
        )}
      </div>
      {error && (
        <p className="mt-1 text-xs text-reject" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
