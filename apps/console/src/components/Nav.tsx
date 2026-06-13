"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

/**
 * Primary cockpit navigation. Every phase-2 route is listed here now so the
 * links exist before the pages land. The active route gets an animated
 * underline indicator (shared-layout style, CSS-only).
 */
const LINKS = [
  { href: "/", label: "Catalog" },
  { href: "/network", label: "Fleet" },
  { href: "/orchestrate", label: "Mission" },
  { href: "/negotiate", label: "Negotiate" },
  { href: "/chat", label: "Ask" },
  { href: "/approvals", label: "Gates" },
  { href: "/telemetry", label: "Telemetry" },
  { href: "/runs", label: "Audit" },
  { href: "/studio", label: "Studio" },
] as const;

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function Nav() {
  const pathname = usePathname();
  return (
    <nav className="flex flex-wrap items-center gap-x-0.5 gap-y-1 text-sm">
      {LINKS.map(({ href, label }) => {
        const active = isActive(pathname, href);
        return (
          <Link
            key={href}
            href={href}
            aria-current={active ? "page" : undefined}
            className={`focus-ring relative rounded-md px-3 py-1.5 transition-colors ${
              active
                ? "text-ink"
                : "text-ink-muted hover:bg-panel-2 hover:text-ink"
            }`}
          >
            {label}
            <span
              aria-hidden
              className="pointer-events-none absolute inset-x-3 -bottom-px h-px origin-center transition-transform duration-300"
              style={{
                background: "linear-gradient(to right, transparent, var(--accent), transparent)",
                transform: active ? "scaleX(1)" : "scaleX(0)",
              }}
            />
          </Link>
        );
      })}
    </nav>
  );
}
