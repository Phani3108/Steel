"""steel-manifest CLI: validate manifests, export JSON Schemas.

Schemas exported here are the public contracts other systems (and the TypeScript
console) build against — the one-way type flow starts at these pydantic models.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from steel_manifest.context import RunContext
from steel_manifest.events import AuditEvent
from steel_manifest.manifest import AgentManifest, load_manifest

SCHEMAS = {
    "agent-manifest.schema.json": AgentManifest,
    "run-context.schema.json": RunContext,
    "audit-event.schema.json": AuditEvent,
}


def export_schemas(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for filename, model in SCHEMAS.items():
        schema = model.model_json_schema()
        (out / filename).write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
        print(f"wrote {out / filename}")


def validate(path: Path) -> int:
    try:
        manifest = load_manifest(path)
    except Exception as exc:  # noqa: BLE001 — CLI boundary, report everything
        print(f"INVALID {path}: {exc}", file=sys.stderr)
        return 1
    print(f"OK {path}: {manifest.name} (autonomy L{int(manifest.autonomy_level)})")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="steel-manifest")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_export = sub.add_parser("export-schemas", help="export JSON Schemas")
    p_export.add_argument("--out", type=Path, default=Path("schemas"))

    p_validate = sub.add_parser("validate", help="validate manifest YAML file(s)")
    p_validate.add_argument("paths", nargs="+", type=Path)

    args = parser.parse_args()
    if args.cmd == "export-schemas":
        export_schemas(args.out)
    elif args.cmd == "validate":
        sys.exit(max(validate(p) for p in args.paths))


if __name__ == "__main__":
    main()
