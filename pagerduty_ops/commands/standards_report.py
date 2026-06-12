"""Export PagerDuty service-standards adoption (read-only compliance report)."""

from __future__ import annotations

from ..api import request
from ..cli import init, standard_parser
from ..log import get_logger
from ..output import render_rows, write_payload

log = get_logger("standards_report")

FIELDNAMES = ["resource_id", "resource_name", "passing", "total", "failing_standards"]


def build_parser():
    p = standard_parser(
        "Export PagerDuty standards adoption.", formats=("table", "csv")
    )
    p.add_argument("--resource-type", default="technical_services",
                   choices=["technical_services", "teams"])
    p.add_argument("--failing-only", action="store_true",
                   help="Only resources with at least one failing standard.")
    return p


def score_rows(raw, failing_only=False) -> list[dict]:
    rows = []
    for entry in raw:
        resource = entry.get("resource") or entry
        score = entry.get("score") or entry
        passing = score.get("passing") if isinstance(score, dict) else None
        total = score.get("total") if isinstance(score, dict) else None
        standards = entry.get("standards") or []
        failing = [s.get("name", "") for s in standards if not s.get("pass", True)]
        if failing_only and not failing:
            continue
        rows.append({
            "resource_id": resource.get("id", ""),
            "resource_name": resource.get("name", "") or resource.get("summary", ""),
            "passing": passing if passing is not None else len(standards) - len(failing),
            "total": total if total is not None else len(standards),
            "failing_standards": "; ".join(failing),
        })
    rows.sort(
        key=lambda r: (r["total"] - r["passing"])
        if isinstance(r["passing"], int) and isinstance(r["total"], int) else 0,
        reverse=True,
    )
    return rows


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    token = init(args)
    log.info("Fetching standards scores for %s...", args.resource_type)
    data = request(f"standards/scores/{args.resource_type}", token)
    raw = data.get("resources") or data.get("scores") or []
    log.info("Got %d resources.", len(raw))
    rows = score_rows(raw, failing_only=args.failing_only)
    write_payload(render_rows(rows, FIELDNAMES, args.format), args.output)
    return 0
