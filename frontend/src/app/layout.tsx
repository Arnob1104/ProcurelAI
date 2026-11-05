import type { Metadata } from "next";
import "@fontsource-variable/bricolage-grotesque";
import "@fontsource-variable/public-sans";
import "@fontsource-variable/jetbrains-mono";
import "./globals.css";
import { SessionProvider } from "@/lib/session";

export const metadata: Metadata = {
  title: "ProcurelAI | Aamar Garments Ltd (fictional)",
  description: "Supplier quotations checked step by step against the purchase request and company rules.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <SessionProvider>{children}</SessionProvider>
      </body>
    </html>
  );
}
