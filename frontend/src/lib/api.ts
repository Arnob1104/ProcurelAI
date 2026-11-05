// Server-side reads from the FastAPI service. Browser calls use relative /api/* URLs (proxied by next.config.ts).

export const API_URL = process.env.API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  } catch {
    throw new ApiError(`Cannot reach the API at ${API_URL}. Start the backend: cd backend && uvicorn app.main:app --port 8000`, 503);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(body.error ?? res.statusText, res.status);
  }
  return res.json() as Promise<T>;
}

export interface Health {
  storage: "supabase" | "memory";
  ai: { enabled: boolean; model: string | null };
  requestItems: number;
  samples: string[];
  hasSampleRequest: boolean;
  error: string | null;
}
