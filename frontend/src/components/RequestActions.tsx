"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function RequestActions({ hasSample, hasRequest }: { hasSample: boolean; hasRequest: boolean }) {
  const router = useRouter();
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  async function send(init: RequestInit) {
    setBusy(true);
    setMsg(null);
    try {
      const res = await fetch("/api/purchase-request", { method: "POST", ...init });
      const body = await res.json();
      if (!res.ok) throw new Error(body.error);
      setMsg({ ok: true, text: `Loaded ${body.items} lines.` });
      router.refresh();
    } catch (e) {
      setMsg({ ok: false, text: e instanceof Error ? e.message : "Could not load the file." });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-4 flex flex-wrap items-center gap-3">
      {hasSample && (
        <button
          type="button"
          disabled={busy}
          onClick={() => send({ headers: { "content-type": "application/json" }, body: JSON.stringify({ sample: true }) })}
          className="rounded-lg bg-indigo px-4 py-2 text-sm font-medium text-white hover:bg-ink disabled:opacity-50"
        >
          {hasRequest ? "Reload the sample purchase request" : "Load the sample purchase request"}
        </button>
      )}
      <label className="cursor-pointer rounded-lg border border-indigo px-4 py-2 text-sm font-medium text-indigo hover:bg-indigo-wash has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-indigo">
        Upload a CSV
        <input
          type="file"
          accept=".csv,text/csv"
          className="sr-only"
          disabled={busy}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (!f) return;
            const fd = new FormData();
            fd.append("file", f);
            send({ body: fd });
            e.target.value = "";
          }}
        />
      </label>
      {msg && (
        <p className={`text-sm ${msg.ok ? "text-approve" : "text-reject"}`} role="status">
          {msg.text}
        </p>
      )}
    </div>
  );
}
