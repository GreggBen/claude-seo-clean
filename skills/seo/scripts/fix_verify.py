#!/usr/bin/env python3
"""
Re-measure after a fix and report what actually closed.

Why this exists
===============
A tool that reports "fixed" without re-measuring is asserting something it has
not tested. This script exists so that no fix in this skill can ever be
declared successful on the strength of having been applied. The only evidence
that a gap closed is a fresh observation in which it is absent.

It re-runs the observe + correlate pipeline and diffs the result against the
findings recorded before the change:

    CLOSED       present before, absent now      -- the fix worked
    PERSISTENT   present before, present now     -- the fix did not work
    REGRESSION   absent before, present now      -- the fix broke something

REGRESSION is the reason this script returns a non-zero exit code: a repair
that trades one defect for another has not improved the page, and a loop that
cannot detect that will happily grind a codebase down over several passes.

Usage
=====
    python3 fix_verify.py --before findings.json --url https://example.com
    python3 fix_verify.py --before findings.json --url https://x.com --codebase ~/dev/site
    python3 fix_verify.py --before before.json --after after.json   # compare two reports
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from fix_observe import observe  # type: ignore
    from fix_correlate import correlate, SEVERITY_ORDER  # type: ignore
except ImportError as exc:  # pragma: no cover
    print(f"fix_verify must sit beside fix_observe.py and fix_correlate.py: {exc}", file=sys.stderr)
    raise

SCHEMA_VERSION = "1.0"


def index_findings(report: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Key findings by id so two reports can be compared."""
    return {f["id"]: f for f in report.get("findings", [])}


def _severity_rank(f: Dict[str, Any]) -> int:
    return SEVERITY_ORDER.get(f.get("severity", "info"), 9)


def compare(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    b = index_findings(before)
    a = index_findings(after)

    closed = [b[k] for k in b.keys() - a.keys()]
    persistent = [a[k] for k in b.keys() & a.keys()]
    regressions = [a[k] for k in a.keys() - b.keys()]

    for bucket in (closed, persistent, regressions):
        bucket.sort(key=_severity_rank)

    # A view that was available before and is missing now makes the comparison
    # unsound: findings can "close" simply because nothing looked for them.
    before_views = set(before.get("views_available", []))
    after_views = set(after.get("views_available", []))
    lost_views = sorted(before_views - after_views)

    return {
        "schema_version": SCHEMA_VERSION,
        "target": after.get("target"),
        "views": {
            "before": sorted(before_views),
            "after": sorted(after_views),
            "lost": lost_views,
        },
        "sound": not lost_views,
        "soundness_note": (
            "Comparison is sound: every view present before was captured again."
            if not lost_views
            else f"Comparison is NOT sound: {', '.join(lost_views)} view(s) available before are "
            "missing now, so some findings may appear closed only because nothing looked for them."
        ),
        "closed": closed,
        "persistent": persistent,
        "regressions": regressions,
        "counts": {
            "closed": len(closed),
            "persistent": len(persistent),
            "regressions": len(regressions),
            "before_total": len(b),
            "after_total": len(a),
        },
    }


def render(result: Dict[str, Any]) -> str:
    lines: List[str] = []
    c = result["counts"]
    lines.append("# Verification\n")
    tgt = result.get("target") or {}
    lines.append(f"- **URL**: `{tgt.get('url') or '--'}`")
    lines.append(f"- **Codebase**: `{tgt.get('codebase') or '--'}`")
    lines.append(
        f"- **Before**: {c['before_total']} findings — **After**: {c['after_total']} findings\n"
    )

    if not result["sound"]:
        lines.append(f"> ⚠️ {result['soundness_note']}\n")

    def block(title: str, items: List[Dict[str, Any]], empty: str) -> None:
        lines.append(f"## {title} ({len(items)})")
        if not items:
            lines.append(f"_{empty}_\n")
            return
        for f in items:
            src = f.get("source") or {}
            loc = f" — `{src.get('file')}:{src.get('line')}`" if src.get("file") else ""
            lines.append(f"- **[{f['severity'].upper()}]** `{f['id']}` {f['title']}{loc}")
        lines.append("")

    block("✅ Closed", result["closed"], "Nothing closed in this pass.")
    block("⏳ Persistent", result["persistent"], "Nothing persisted.")
    block("🔴 Regressions", result["regressions"], "No regression introduced.")

    if result["regressions"]:
        lines.append(
            "\n**A regression means the change traded one defect for another.** "
            "Revert or repair before continuing the loop."
        )
    return "\n".join(lines)


def load_report(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-measure and prove what a fix closed.")
    parser.add_argument("--before", required=True, help="findings.json captured before the change")
    parser.add_argument("--after", help="findings.json captured after (skips re-observation)")
    parser.add_argument("--url", help="URL to re-observe")
    parser.add_argument("--codebase", help="Codebase to re-observe")
    parser.add_argument("--out", "-o", help="Write the comparison JSON here")
    parser.add_argument("--timeout", "-t", type=int, default=30)
    parser.add_argument("--no-render", action="store_true")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    args = parser.parse_args()

    try:
        before = load_report(args.before)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"cannot read --before: {exc}", file=sys.stderr)
        return 2

    if args.after:
        try:
            after = load_report(args.after)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"cannot read --after: {exc}", file=sys.stderr)
            return 2
    else:
        target = before.get("target") or {}
        url = args.url or target.get("url")
        codebase = args.codebase or target.get("codebase")
        if not url and not codebase:
            print(
                "nothing to re-observe: pass --url/--codebase, or --after with a second report",
                file=sys.stderr,
            )
            return 2
        snapshot = observe(
            url=url, codebase=codebase, timeout=args.timeout, skip_rendered=args.no_render
        )
        after = correlate(snapshot)

    result = compare(before, after)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2, ensure_ascii=False)

    if args.format == "json":
        json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
        print()
    else:
        print(render(result))

    # Non-zero on regression so a loop or CI step stops instead of grinding on.
    return 1 if result["regressions"] else 0


if __name__ == "__main__":
    sys.exit(main())
