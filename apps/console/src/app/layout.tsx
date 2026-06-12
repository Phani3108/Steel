import type { Metadata } from "next";
import Link from "next/link";

import { Nav } from "../components/Nav";
import "./globals.css";

export const metadata: Metadata = {
  title: "JAI Console",
  description:
    "Cockpit of the JAI agentic procurement platform — parts catalog, costs, and run audit trails.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex min-h-full flex-col bg-zinc-950 text-zinc-200">
        <header className="sticky top-0 z-10 border-b border-zinc-800 bg-zinc-950/90 backdrop-blur">
          <div className="mx-auto flex w-full max-w-6xl items-center gap-8 px-6 py-3.5">
            <Link href="/" className="font-mono text-base font-semibold tracking-tight">
              <span className="text-zinc-50">JAI</span>{" "}
              <span className="text-emerald-400">console</span>
            </Link>
            <Nav />
            <span className="ml-auto hidden font-mono text-[11px] tracking-widest text-zinc-600 sm:block">
              COCKPIT
            </span>
          </div>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-8">{children}</main>
        <footer className="border-t border-zinc-900 py-4 text-center font-mono text-[11px] text-zinc-700">
          jai-console · personal research platform · all data synthetic
        </footer>
      </body>
    </html>
  );
}
