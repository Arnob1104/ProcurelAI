"use client";

import { useState } from "react";
import { useSession } from "@/lib/session";

/** Deletes the result and the person's review for it. Asks once first. */
export function DeleteButton({ id, onDeleted, className = "" }: { id: string; onDeleted?: () => void; className?: string }) {
  const session = useSession();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function del() {
    if (!window.confirm("Delete this result and its review? This cannot be undone.")) return;
    setBusy(true);
    setError(null);
    try {
      await session.remove(id);
      onDeleted?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not delete.");
      setBusy(false);
    }
  }

  return (
    <span className={className}>
      <button
        type="button"
        onClick={del}
        disabled={busy}
        className="rounded-md border border-chalk-deep px-3 py-1 text-xs font-medium text-ink-soft hover:border-reject hover:text-reject disabled:opacity-50"
      >
        {busy ? "Deleting" : "Delete"}
      </button>
      {error && <span className="ml-2 text-xs text-reject">{error}</span>}
    </span>
  );
}
