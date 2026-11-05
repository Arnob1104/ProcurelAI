"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function ReviewForm({ id }: { id: string }) {
  const router = useRouter();
  const [decision, setDecision] = useState<"Approve" | "Reject" | "">("");
  const [note, setNote] = useState("");
  const [reviewer, setReviewer] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!decision) return setError("Choose Approve or Reject.");
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`/api/analyses/${id}/review`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ decision, note, reviewer }),
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body.error);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save your answer.");
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
          Reason
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
        Save decision
      </button>
    </form>
  );
}
