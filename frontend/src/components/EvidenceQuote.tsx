import type { Evidence } from "@/lib/types";

/** Shows exact document text, or says plainly what was missing. */
export function EvidenceQuote({ evidence, tone = "indigo" }: { evidence: Evidence; tone?: "indigo" | "reject" | "check" }) {
  const edge = tone === "reject" ? "border-reject" : tone === "check" ? "border-check" : "border-indigo";
  return (
    <figure className={`border-l-4 ${edge} bg-paper/70 py-2 pl-3 pr-2`}>
      {evidence.quote ? (
        <blockquote className="quote text-ink">{evidence.quote}</blockquote>
      ) : (
        <p className="text-sm italic text-ink-soft">Nothing in the document to quote.</p>
      )}
      {evidence.note && <figcaption className="mt-1 text-sm text-ink-soft">{evidence.note}</figcaption>}
    </figure>
  );
}
