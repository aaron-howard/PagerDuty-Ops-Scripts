"""Rendering and output: rows -> table/csv/json, written to a file or stdout.

Only data ever goes to stdout; row counts and 'wrote file' notices go to the
logger (stderr).
"""

from __future__ import annotations

import csv
import io
import json
import sys

from .log import get_logger

log = get_logger("output")


def render_rows(rows: list[dict], fieldnames: list[str], fmt: str, raw: list | None = None) -> str:
    """Render rows in 'table', 'csv', or 'json'.

    If `raw` is given, json mode dumps the raw API objects (full fidelity)
    instead of the flattened rows.
    """
    if fmt == "json":
        return json.dumps(raw if raw is not None else rows, indent=2) + "\n"
    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        return buf.getvalue()
    # table
    try:
        from tabulate import tabulate
    except ImportError:  # graceful fallback: TSV
        lines = ["\t".join(fieldnames)]
        lines += ["\t".join(str(r.get(f, "")) for f in fieldnames) for r in rows]
        return "\n".join(lines) + "\n"
    return (
        tabulate(
            [[r.get(f, "") for f in fieldnames] for r in rows],
            headers=fieldnames,
            tablefmt="github",
        )
        + f"\n\nTotal: {len(rows)}\n"
    )


def write_payload(payload: str, path: str | None = None) -> None:
    if path:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(payload)
        log.info("Wrote output to %s", path)
    else:
        sys.stdout.write(payload)
