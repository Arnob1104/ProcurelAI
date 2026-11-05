"use client";

// Results live only in this browser tab's memory. A full page reload starts empty.
// (The provider sits in the root layout, so moving between the list and a detail page keeps them.)

import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { StoredAnalysis } from "./types";

type Session = {
  rows: StoredAnalysis[];
  /** Load one saved result by id and add it to the top of the list. */
  add: (id: string) => Promise<void>;
  /** Put in a changed row (after a person decided, changed or undid an answer). */
  replace: (row: StoredAnalysis) => void;
  /** Delete on the server (result and its review), then drop it from the list. */
  remove: (id: string) => Promise<void>;
  /** Approve or Reject a document the system stopped on. Reason is optional. */
  decide: (id: string, decision: "Approve" | "Reject", note?: string, reviewer?: string) => Promise<void>;
  /** Take a person's answer back so the document waits for a person again. */
  undo: (id: string) => Promise<void>;
};

const Ctx = createContext<Session | null>(null);

async function call(url: string, init?: RequestInit) {
  const res = await fetch(url, init);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.error ?? "Something went wrong.");
  return body;
}

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [rows, setRows] = useState<StoredAnalysis[]>([]);

  const replace = useCallback((row: StoredAnalysis) => {
    setRows((rs) => (rs.some((r) => r.id === row.id) ? rs.map((r) => (r.id === row.id ? row : r)) : [row, ...rs]));
  }, []);

  const value = useMemo<Session>(
    () => ({
      rows,
      replace,
      async add(id) {
        replace(await call(`/api/analyses/${encodeURIComponent(id)}`));
      },
      async remove(id) {
        await call(`/api/analyses/${encodeURIComponent(id)}`, { method: "DELETE" });
        setRows((rs) => rs.filter((r) => r.id !== id));
      },
      async decide(id, decision, note, reviewer) {
        const body = await call(`/api/analyses/${encodeURIComponent(id)}/review`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ decision, note: note ?? "", reviewer: reviewer ?? "" }),
        });
        replace(body.row);
      },
      async undo(id) {
        const body = await call(`/api/analyses/${encodeURIComponent(id)}/review`, { method: "DELETE" });
        replace(body.row);
      },
    }),
    [rows, replace],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSession(): Session {
  const v = useContext(Ctx);
  if (!v) throw new Error("useSession must be used inside SessionProvider.");
  return v;
}
