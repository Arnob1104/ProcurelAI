"use client";

import { useRef, useState } from "react";
import type { Decision } from "@/lib/types";
import { DECISION } from "@/lib/format";
import { useSession } from "@/lib/session";

type Job = {
  name: string;
  state: "waiting" | "checking" | "done" | "error";
  decision?: Decision;
  id?: string;
  error?: string;
};

export function UploadPanel({ ready, samples }: { ready: boolean; samples: string[] }) {
  const session = useSession();
  const input = useRef<HTMLInputElement>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [busy, setBusy] = useState(false);
  const [over, setOver] = useState(false);

  async function run(items: { name: string; send: () => Promise<Response> }[]) {
    setBusy(true);
    setJobs(items.map((i) => ({ name: i.name, state: "waiting" })));
    // One file at a time: the Groq free tier allows few tokens per minute.
    for (let n = 0; n < items.length; n++) {
      setJobs((j) => j.map((x, k) => (k === n ? { ...x, state: "checking" } : x)));
      try {
        const res = await items[n].send();
        const body = await res.json();
        if (!res.ok) throw new Error(body.error ?? "The check failed.");
        await session.add(body.id);
        setJobs((j) => j.map((x, k) => (k === n ? { ...x, state: "done", decision: body.decision, id: body.id } : x)));
      } catch (e) {
        setJobs((j) => j.map((x, k) => (k === n ? { ...x, state: "error", error: e instanceof Error ? e.message : "The check failed." } : x)));
      }
    }
    setBusy(false);
  }

  function uploadFiles(files: FileList | File[]) {
    const pdfs = Array.from(files).filter((f) => f.name.toLowerCase().endsWith(".pdf"));
    if (!pdfs.length) return;
    run(
      pdfs.map((f) => ({
        name: f.name,
        send: () => {
          const fd = new FormData();
          fd.append("file", f);
          return fetch("/api/analyze", { method: "POST", body: fd });
        },
      })),
    );
  }

  function runSamples() {
    run(
      samples.map((s) => ({
        name: s,
        send: () => fetch("/api/analyze", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ sample: s }) }),
      })),
    );
  }

  return (
    <section aria-labelledby="upload-h" className="rounded-xl border border-chalk bg-sheet p-5">
      <h2 id="upload-h" className="text-xl font-semibold">
        Check quotations
      </h2>
      <p className="mt-1 text-sm text-ink-soft">Add one or more supplier PDFs. Each one goes through the same eight steps.</p>

      <label
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setOver(false);
          if (ready && !busy) uploadFiles(e.dataTransfer.files);
        }}
        className={`mt-4 flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-4 py-8 text-center has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-indigo ${
          over ? "border-indigo bg-indigo-wash" : "border-chalk-deep bg-paper/50"
        } ${!ready || busy ? "pointer-events-none opacity-60" : ""}`}
      >
        <span className="font-medium">Drop PDF files here or choose them</span>
        <span className="mt-1 text-sm text-ink-soft">PDF only, up to 10 MB each</span>
        <input
          ref={input}
          type="file"
          accept="application/pdf,.pdf"
          multiple
          className="sr-only"
          disabled={!ready || busy}
          onChange={(e) => {
            if (e.target.files) uploadFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </label>

      {!ready && <p className="mt-3 text-sm text-check">Load the purchase request first. Without it, price and quantity cannot be compared.</p>}

      {samples.length > 0 && (
        <button
          type="button"
          onClick={runSamples}
          disabled={!ready || busy}
          className="mt-3 rounded-lg border border-indigo px-4 py-2 text-sm font-medium text-indigo hover:bg-indigo-wash disabled:cursor-not-allowed disabled:opacity-50"
        >
          Check the {samples.length} sample quotations
        </button>
      )}

      {jobs.length > 0 && (
        <ul className="mt-4 space-y-1.5 text-sm" aria-live="polite">
          {jobs.map((j, i) => (
            <li key={i} className="flex items-center justify-between gap-3 rounded-md bg-paper/60 px-3 py-1.5">
              <span className="truncate">{j.name}</span>
              <span className="shrink-0">
                {j.state === "waiting" && <span className="text-ink-soft">Waiting</span>}
                {j.state === "checking" && <span className="text-indigo">Checking</span>}
                {j.state === "done" && j.decision && <span className={`font-semibold ${DECISION[j.decision].text}`}>{DECISION[j.decision].short}</span>}
                {j.state === "error" && <span className="text-reject">{j.error}</span>}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
