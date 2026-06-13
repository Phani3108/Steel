"use client";

import { Fragment } from "react";

import { COLORS } from "@/lib/theme";

/**
 * YamlPreview — a hairline mono pane that renders an AgentManifest YAML with
 * light, hand-rolled syntax tinting (keys in aqua, scalars in ink, list
 * bullets faint). Read-only by design: the form is the source of truth.
 */
export function YamlPreview({ yaml }: { yaml: string }) {
  const lines = yaml.replace(/\n$/, "").split("\n");

  return (
    <div className="panel-2 telem-grid overflow-hidden">
      <pre className="metric overflow-x-auto px-4 py-3 text-[12px] leading-[1.7]">
        <code>
          {lines.map((line, i) => (
            <Fragment key={i}>
              <Line text={line} />
              {i < lines.length - 1 && "\n"}
            </Fragment>
          ))}
        </code>
      </pre>
    </div>
  );
}

function Line({ text }: { text: string }) {
  const indentMatch = text.match(/^(\s*)/);
  const indent = indentMatch ? indentMatch[1] : "";
  const rest = text.slice(indent.length);

  // List item:  "- value"
  if (rest.startsWith("- ")) {
    return (
      <span>
        {indent}
        <span style={{ color: COLORS.inkFaint }}>- </span>
        <Scalar text={rest.slice(2)} />
      </span>
    );
  }

  // "key: value"  /  "key:"
  const kv = rest.match(/^([\w.-]+):(.*)$/);
  if (kv) {
    const [, key, after] = kv;
    const value = after.replace(/^\s+/, "");
    return (
      <span>
        {indent}
        <span style={{ color: COLORS.accent }}>{key}</span>
        <span style={{ color: COLORS.inkFaint }}>:</span>
        {value ? (
          <>
            {" "}
            <Scalar text={value} />
          </>
        ) : null}
      </span>
    );
  }

  return <span style={{ color: COLORS.ink }}>{text}</span>;
}

/** Tint numbers, the api_version sentinel, and quoted strings distinctly. */
function Scalar({ text }: { text: string }) {
  if (/^-?\d+(\.\d+)?$/.test(text)) {
    return <span style={{ color: COLORS.warn }}>{text}</span>;
  }
  if (text === "jai/v1") {
    return <span style={{ color: COLORS.autonomy }}>{text}</span>;
  }
  if (text === "[]") {
    return <span style={{ color: COLORS.inkFaint }}>{text}</span>;
  }
  if (/^".*"$/.test(text)) {
    return <span style={{ color: COLORS.ok }}>{text}</span>;
  }
  return <span style={{ color: COLORS.ink }}>{text}</span>;
}
