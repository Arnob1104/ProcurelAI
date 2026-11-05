import type { TraceStep } from "@/lib/types";

const MARK: Record<TraceStep["status"], string> = {
  done: "bg-indigo text-white border-indigo",
  skipped: "bg-sheet text-ink-soft border-chalk-deep",
  stopped: "bg-check text-white border-check",
};

/** The fixed steps as a stitched thread. The order is real: each step runs after the one above it. */
export function Seam({ trace }: { trace: TraceStep[] }) {
  return (
    <ol className="relative">
      <span aria-hidden className="seam-thread seam-draw absolute bottom-4 left-[15px] top-4 w-[2px]" />
      {trace.map((t, i) => (
        <li key={t.step} className="relative flex gap-3 pb-5 last:pb-0">
          <span
            className={`relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 text-sm font-semibold ${MARK[t.status]}`}
          >
            {t.status === "stopped" ? "!" : i + 1}
          </span>
          <div className="min-w-0 pt-0.5">
            <p className="font-medium leading-snug">{t.label}</p>
            <p className="text-sm text-ink-soft">
              {t.status === "skipped" && t.summary !== "Not run." ? t.summary : t.status === "skipped" ? "Not needed for this document." : t.summary}
              {t.status === "done" && t.ms > 0 ? <span className="text-chalk-deep"> {t.ms} ms</span> : null}
            </p>
          </div>
        </li>
      ))}
    </ol>
  );
}
