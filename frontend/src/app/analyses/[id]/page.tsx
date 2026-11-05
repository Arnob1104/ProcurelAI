import { DetailView } from "@/components/DetailView";

// Results live in the browser session (see lib/session.tsx), so the page itself needs no server data.
export default async function Detail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <DetailView id={id} />;
}
