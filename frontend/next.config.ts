import type { NextConfig } from "next";

// The Python API. The browser only ever talks to this app; /api/* is forwarded to FastAPI,
// so no CORS setup is needed. Set API_URL when you build (it is read at build time).
const API_URL = process.env.API_URL ?? "http://localhost:8000";

const config: NextConfig = {
  // Groq's free tier can make a check take a while. Allow up to two minutes per file.
  experimental: { proxyTimeout: 120_000 },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/api/:path*` }];
  },
};

export default config;
