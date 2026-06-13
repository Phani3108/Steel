import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";

import { GovernanceNotice } from "@/components/GovernanceNotice";
import { Nav } from "@/components/Nav";
import { TelemetryStrip } from "@/components/TelemetryStrip";
import "./globals.css";

const geistSans = Geist({
  subsets: ["latin"],
  variable: "--font-geist-sans",
  display: "swap",
});

const geistMono = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-geist-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "JAI Console — Cockpit",
  description:
    "Mission control for the JAI agentic procurement fleet — catalog, network, orchestration, gates, telemetry, and tamper-evident audit.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`h-full ${geistSans.variable} ${geistMono.variable} antialiased`}
    >
      <body className="flex min-h-full flex-col bg-base text-ink">
        <header className="sticky top-0 z-20 border-b border-line bg-base/80 backdrop-blur-xl">
          <div className="mx-auto flex w-full max-w-7xl items-center gap-6 px-6 py-3">
            {/* instrument-badge wordmark */}
            <Link
              href="/"
              className="focus-ring group flex items-center gap-2.5 rounded-md"
              aria-label="JAI console home"
            >
              <span
                aria-hidden
                className="relative flex h-7 w-7 items-center justify-center rounded-md border border-accent/40 bg-accent/10"
              >
                <span className="absolute inset-0 rounded-md glow opacity-60 transition-opacity group-hover:opacity-100" />
                <span className="metric relative text-[11px] font-bold tracking-tight text-accent">
                  JAI
                </span>
              </span>
              <span className="hidden flex-col leading-none sm:flex">
                <span className="metric text-[13px] font-semibold tracking-tight text-ink">
                  console
                </span>
                <span className="label-cap mt-0.5">cockpit</span>
              </span>
            </Link>

            <span className="hidden h-5 w-px bg-line lg:block" aria-hidden />

            <Nav />

            <div className="ml-auto">
              <TelemetryStrip />
            </div>
          </div>
        </header>

        <main className="mx-auto w-full max-w-7xl flex-1 px-6 py-8">{children}</main>

        <footer className="border-t border-line/70">
          <div className="mx-auto flex w-full max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-6 py-4 font-mono text-[10px] tracking-wider text-ink-ghost">
            <span>jai-console · personal research platform · all data synthetic</span>
            <span className="hidden lg:inline">built like a car — six systems, one cockpit</span>
            <div className="ml-auto">
              <GovernanceNotice />
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
