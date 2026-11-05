"use client";

import { useState } from "react";
import { useSession } from "@/lib/session";
import type { StoredAnalysis } from "@/lib/types";

export function ReviewForm({ row }: { row: StoredAnalysis }) {
  const session = useSession();
  const [decision, setDecision] = useState<"Approve" | "Reject" | "">(row.review?.decision ?? "");
  const [note, setNote] = useState(row.review?.note ?? "");
  const [reviewer, setReviewer] = useState(row.review?.reviewer ?? "");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!decision) return setError("Choose Approve or Reject.");
    setBusy(true);
    setError(null);
    try {
      await session.decide(row.id, decision, note, reviewer);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save your answer.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <fieldset>
        <legend className="mb-2 text-sm font-medium">Your decision</legend>
        <div className="flex flex-wrap gap-3">
          {(["Approve", "Reject"] as const).map((d) => (
            <label
              key={d}
              className={`flex cursor-pointer items-center gap-2 rounded-lg border-2 px-4 py-2 text-sm font-medium has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-indigo ${
                decision === d
                  ? d === "Approve" ? "border-approve bg-approve-wash text-approve" : "border-reject bg-reject-wash text-reject"
                  : "border-chalk bg-sheet"
              }`}
            >
              <input type="radio" name="decision" value={d} checked={decision === d} onChange={() => setDecision(d)} className="sr-only" />
              {d}
            </label>
          ))}
        </div>
      </fieldset>
      <div>
        <label htmlFor="note" className="mb-1 block text-sm font-medium">
          Reason (optional)
        </label>
        <textarea
          id="note"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={3}
          className="w-full rounded-lg border border-chalk-deep bg-sheet px-3 py-2 text-sm"
          placeholder="For example: supplier confirmed the 16,500 pieces by phone and the shortfall is covered by stock."
        />
      </div>
      <div>
        <label htmlFor="who" className="mb-1 block text-sm font-medium">
          Your name (optional)
        </label>
        <input id="who" value={reviewer} onChange={(e) => setReviewer(e.target.value)} className="w-full max-w-xs rounded-lg border border-chalk-deep bg-sheet px-3 py-2 text-sm" />
      </div>
      {error && (
        <p className="text-sm text-reject" role="alert">
          {error}
        </p>
      )}
      <button type="submit" disabled={busy} className="rounded-lg bg-indigo px-5 py-2.5 text-sm font-medium text-white hover:bg-ink disabled:opacity-50">
        {row.review ? "Save changed decision" : "Save decision"}
      </button>
      {row.review && (
        <button
          type="button"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              await session.undo(row.id);
              setDecision("");
              setNote("");
            } catch (err) {
              setError(err instanceof Error ? err.message : "Could not undo.");
            } finally {
              setBusy(false);
            }
          }}
          className="ml-3 text-sm text-ink-soft underline underline-offset-2 hover:text-ink"
        >
          Undo my decision
        </button>
      )}
    </form>
  );
}
