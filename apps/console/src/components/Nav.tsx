"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

/**
 * Primary cockpit navigation. The flat 9-item bar is now grouped into the four
 * phases of the work — Run · Review · Explore · Govern — so the critical path
 * reads first. The active route keeps its animated underline. Below 640px the
 * bar collapses into a hamburger drawer instead of wrapping into ugly rows.
 */

interface NavLink {
  href: string;
  label: string;
  /** Tiny cockpit kicker shown in the mobile drawer. */
  kicker: string;
}

interface NavGroup {
  label: string;
  links: NavLink[];
}

const GROUPS: NavGroup[] = [
  {
    label: "Run",
    links: [
      { href: "/orchestrate", label: "Mission", kicker: "orchestrate a procurement" },
      { href: "/negotiate", label: "Negotiate", kicker: "agent vs. seller" },
    ],
  },
  {
    label: "Review",
    links: [
      { href: "/approvals", label: "Gates", kicker: "human-in-the-loop" },
      { href: "/runs", label: "Audit", kicker: "the flight recorder" },
      { href: "/telemetry", label: "Telemetry", kicker: "fleet vitals & cost" },
    ],
  },
  {
    label: "Explore",
    links: [
      { href: "/network", label: "Fleet", kicker: "the a2a mesh" },
      { href: "/catalog", label: "Catalog", kicker: "platform architecture" },
      { href: "/chat", label: "Ask", kicker: "query the data" },
    ],
  },
  {
    label: "Govern",
    links: [{ href: "/studio", label: "Studio", kicker: "manifests & maturity" }],
  },
];

const ALL_LINKS = GROUPS.flatMap((g) => g.links);

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function Nav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  // Close the mobile drawer on route change.
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  return (
    <>
      {/* ---- desktop: grouped horizontal bar ---- */}
      <nav className="hidden items-center gap-2 text-sm sm:flex" aria-label="Primary">
        {GROUPS.map((group, gi) => (
          <div key={group.label} className="flex items-center gap-2">
            {gi > 0 && (
              <span className="h-4 w-px bg-line/80" aria-hidden />
            )}
            <span
              className="label-cap hidden select-none lg:inline"
              aria-hidden
              title={group.label}
            >
              {group.label}
            </span>
            <div className="flex items-center gap-x-0.5">
              {group.links.map(({ href, label, kicker }) => {
                const active = isActive(pathname, href);
                return (
                  <Link
                    key={href}
                    href={href}
                    title={kicker}
                    aria-current={active ? "page" : undefined}
                    className={`focus-ring relative rounded-md px-2.5 py-1.5 transition-colors ${
                      active
                        ? "text-ink"
                        : "text-ink-muted hover:bg-panel-2 hover:text-ink"
                    }`}
                  >
                    {label}
                    <span
                      aria-hidden
                      className="pointer-events-none absolute inset-x-2.5 -bottom-px h-px origin-center transition-transform duration-300"
                      style={{
                        background:
                          "linear-gradient(to right, transparent, var(--accent), transparent)",
                        transform: active ? "scaleX(1)" : "scaleX(0)",
                      }}
                    />
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* ---- mobile: hamburger + drawer ---- */}
      <div className="sm:hidden">
        <button
          type="button"
          aria-label={open ? "Close navigation" : "Open navigation"}
          aria-expanded={open}
          onClick={() => setOpen((o) => !o)}
          className="focus-ring flex h-9 w-9 items-center justify-center rounded-md border border-line bg-panel-2 text-ink-muted hover:text-ink"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
            {open ? (
              <path
                d="M6 6l12 12M18 6L6 18"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
              />
            ) : (
              <path
                d="M4 7h16M4 12h16M4 17h16"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
              />
            )}
          </svg>
        </button>

        {open && (
          <>
            <button
              type="button"
              aria-hidden
              tabIndex={-1}
              onClick={() => setOpen(false)}
              className="fixed inset-0 top-[57px] z-30 bg-base/70 backdrop-blur-sm"
            />
            <div className="animate-fade-in-up fixed inset-x-0 top-[57px] z-40 max-h-[calc(100vh-57px)] overflow-y-auto border-b border-line bg-base/95 px-6 py-4 backdrop-blur-xl">
              <Link
                href="/"
                aria-current={pathname === "/" ? "page" : undefined}
                className="focus-ring mb-3 flex items-center justify-between rounded-md border border-line bg-panel-2 px-3 py-2.5 text-sm text-ink"
              >
                <span className="font-medium">Home</span>
                <span className="label-cap">overview</span>
              </Link>
              <div className="grid grid-cols-1 gap-4">
                {GROUPS.map((group) => (
                  <div key={group.label}>
                    <div className="label-cap mb-1.5">{group.label}</div>
                    <div className="flex flex-col gap-0.5">
                      {group.links.map(({ href, label, kicker }) => {
                        const active = isActive(pathname, href);
                        return (
                          <Link
                            key={href}
                            href={href}
                            aria-current={active ? "page" : undefined}
                            className={`focus-ring flex items-center justify-between rounded-md px-3 py-2 text-sm transition-colors ${
                              active
                                ? "bg-accent/10 text-ink"
                                : "text-ink-muted hover:bg-panel-2 hover:text-ink"
                            }`}
                          >
                            <span>{label}</span>
                            <span className="text-[11px] text-ink-faint">{kicker}</span>
                          </Link>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </>
  );
}

export { ALL_LINKS };
