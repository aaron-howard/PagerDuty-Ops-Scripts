#!/usr/bin/env python3
"""Export PagerDuty Event Orchestration rules to JSON files for review-in-PR.

Writes one file per orchestration to the output directory:

    <output_dir>/<orchestration_id>__<slugified_name>.json

Each file contains the orchestration metadata, its router config, and its
global catch-all rules. Commit the directory to git and diffs against future
exports show every rule change in a code-review-friendly format.
"""

import argparse
import json
import os
import re
import sys

from pd_common import fetch_all, add_token_arguments, get_pd_api_token, make_api_request


def parse_arguments():
    parser = argparse.ArgumentParser(description="Export PagerDuty Event Orchestration rules to JSON.")
    add_token_arguments(parser)
    parser.add_argument(
        "-o",
        "--output-dir",
        default="event_orchestrations",
        help="Directory to write JSON files into (default: event_orchestrations).",
    )
    return parser.parse_args()


def slugify(name):
    slug = re.sub(r"[^A-Za-z0-9]+", "-", name or "").strip("-").lower()
    return slug or "unnamed"


def main():
    args = parse_arguments()
    token = get_pd_api_token(args.token, allow_prompt=args.prompt)

    orchestrations = fetch_all("event_orchestrations", token, label="event_orchestrations")
    os.makedirs(args.output_dir, exist_ok=True)

    written = 0
    for orch in orchestrations:
        orch_id = orch.get("id")
        if not orch_id:
            continue
        router = make_api_request(f"event_orchestrations/{orch_id}/router", token)
        global_rules = make_api_request(f"event_orchestrations/{orch_id}/global", token)
        payload = {
            "orchestration": orch,
            "router": (router or {}).get("orchestration_path"),
            "global": (global_rules or {}).get("orchestration_path"),
        }
        filename = f"{orch_id}__{slugify(orch.get('name'))}.json"
        path = os.path.join(args.output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
            f.write("\n")
        written += 1
        print(f"Wrote {path}")

    print(f"\nExported {written} orchestrations to {args.output_dir}/", file=sys.stderr)


if __name__ == "__main__":
    main()
