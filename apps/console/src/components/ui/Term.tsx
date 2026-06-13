"use client";

import { useId, useState, type ReactNode } from "react";

/**
 * Term — an inline jargon tooltip. Wraps a word in a dotted underline and reveals
 * a short plain-language definition on hover or keyboard focus, so a first-timer
 * never hits an unexplained piece of procurement / agent vocabulary.
 *
 *   <Term word="mandate" def="A hard spend ceiling an agent cannot exceed.">mandate</Term>
 *   <Term k="zopa" />            // pull both label + definition from the glossary
 *   <Term k="gate">approval gate</Term>   // glossary definition, custom label
 */

/** Built-in glossary so callers can do `<Term k="zopa" />` with no other props. */
export const GLOSSARY: Record<string, { word: string; def: string }> = {
  autonomy: {
    word: "autonomy",
    def: "How much an agent may do on its own — L1 advise → L5 act unattended. Higher levels need a passing scorecard.",
  },
  mandate: {
    word: "mandate",
    def: "A hard spend ceiling an agent cannot exceed. Cross it and the run pauses at a human gate.",
  },
  zopa: {
    word: "ZOPA",
    def: "Zone of Possible Agreement — the price band where both buyer and seller can say yes. The negotiator works inside it.",
  },
  a2a: {
    word: "A2A",
    def: "Agent-to-agent — the open protocol agents use to hand work to one another. Each handoff is a 'hop'.",
  },
  gate: {
    word: "gate",
    def: "A human-in-the-loop checkpoint. The run durably pauses here until a person approves or rejects it.",
  },
  scorecard: {
    word: "scorecard",
    def: "An agent's eval results — pass rate over a test suite. No scorecard, no promotion to higher autonomy.",
  },
  rag: {
    word: "RAG",
    def: "Retrieval-augmented generation — the agent answers from cited documents in the knowledge base, not from memory alone.",
  },
};

interface TermProps {
  /** Glossary key — supplies both the label and definition when present. */
  k?: keyof typeof GLOSSARY | string;
  /** The term being defined (used as label when no children given). */
  word?: string;
  /** The definition shown in the popover. Overrides the glossary entry. */
  def?: string;
  /** Custom visible label; defaults to children, then `word`, then glossary word. */
  children?: ReactNode;
  className?: string;
}

export function Term({ k, word, def, children, className = "" }: TermProps) {
  const [open, setOpen] = useState(false);
  const id = useId();

  const entry = k ? GLOSSARY[k] : undefined;
  const label = children ?? word ?? entry?.word ?? k ?? "";
  const definition = def ?? entry?.def ?? "";

  // No definition available → render the label plainly, no decoration.
  if (!definition) return <>{label}</>;

  return (
    <span
      className={`relative inline-block ${className}`}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        type="button"
        aria-describedby={open ? id : undefined}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        className="focus-ring cursor-help rounded-sm bg-transparent p-0 text-inherit"
        style={{
          textDecoration: "underline dotted",
          textDecorationColor: "color-mix(in srgb, var(--accent) 60%, transparent)",
          textUnderlineOffset: "3px",
        }}
      >
        {label}
      </button>
      {open && (
        <span
          role="tooltip"
          id={id}
          className="panel-2 absolute bottom-full left-1/2 z-30 mb-2 w-60 -translate-x-1/2 px-3 py-2 text-left text-[11.5px] leading-relaxed text-ink-muted shadow-[var(--shadow-pop)] animate-fade-in-up"
        >
          <span className="label-cap mb-1 block text-accent">
            {entry?.word ?? word ?? "definition"}
          </span>
          {definition}
          <span
            aria-hidden
            className="absolute left-1/2 top-full h-2 w-2 -translate-x-1/2 -translate-y-1 rotate-45 border-b border-r border-line bg-panel-2"
          />
        </span>
      )}
    </span>
  );
}
