#!/usr/bin/env python3
"""
Derive findings from the *differences* between the three observed views.

Why this exists
===============
A single view can only support checklist findings: "no h1", "missing alt".
Those are already well covered by the other skills in this toolkit. The
findings that matter most are invisible to any single view, because they are
disagreements:

    raw != rendered      information that only exists once JavaScript runs
    markup != visible    structured data promising text the page never shows
    source != delivered  the component responsible for either of the above

This script consumes a snapshot from fix_observe.py and emits findings that
carry evidence from every view involved, plus -- when the source view is
present -- the file and line responsible. A finding that cannot be traced to
a source location is reported as OBSERVED, never as FIXABLE. Guessing where a
symptom comes from is how automated tools corrupt codebases.

Nothing here mutates anything. Correlation is a read-only step by contract.

Usage
=====
    python3 fix_correlate.py snapshot.json
    python3 fix_correlate.py snapshot.json --out findings.json
    python3 fix_correlate.py snapshot.json --min-severity high
    python3 fix_correlate.py snapshot.json --format markdown
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from html.parser import HTMLParser
from typing import Any, Dict, Iterable, List, Optional

SCHEMA_VERSION = "1.0"

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

# How much of a markup string must appear verbatim in visible text before we
# accept that the page actually shows what its structured data claims.
MATCH_PREFIX_CHARS = 60
# Below this word count a raw view is a candidate for "shell only".
THIN_RAW_WORDS = 120
# A raw/rendered delta smaller than this is treated as formatting noise.
NOISE_FLOOR_WORDS = 30
# Rendered/raw ratio at which the raw view stops being a version of the page
# and becomes a different page.
SHELL_RATIO = 3.0
# Ratio at which a meaningful share of the page is JavaScript-dependent.
PARTIAL_RATIO = 1.5


# ---------------------------------------------------------------------------
# Text normalisation
# ---------------------------------------------------------------------------


def normalise(text: str) -> str:
    """Fold text so that formatting differences do not create false positives."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = re.sub(r"[‘’“”]", "'", text)
    text = re.sub(r"[^a-z0-9' ]+", " ", text)
    return " ".join(text.split())


class _ClaimTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in {"p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3"}:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"p", "div", "li", "ul", "ol", "h1", "h2", "h3"}:
            self.parts.append(" ")


def contained(needle: str, haystack_norm: str) -> bool:
    """True when a meaningful prefix of `needle` appears in the normalised text."""
    # Answer.text peut contenir du HTML : comparer les deux projections textuelles.
    parser = _ClaimTextParser()
    parser.feed(needle)
    parser.close()
    n = normalise("".join(parser.parts))
    if not n:
        return True  # nothing claimed, nothing to show
    probe = n[:MATCH_PREFIX_CHARS] if len(n) > MATCH_PREFIX_CHARS else n
    if len(probe) < 12:
        # Too short to be a reliable probe; require the whole string.
        return n in haystack_norm
    return probe in haystack_norm


# ---------------------------------------------------------------------------
# JSON-LD traversal
# ---------------------------------------------------------------------------


def iter_nodes(payload: Any) -> Iterable[Dict[str, Any]]:
    """Yield every dict node in a JSON-LD payload, flattening @graph and arrays."""
    if isinstance(payload, list):
        for item in payload:
            yield from iter_nodes(item)
    elif isinstance(payload, dict):
        yield payload
        for key, value in payload.items():
            if key == "@context":
                continue
            if isinstance(value, (dict, list)):
                yield from iter_nodes(value)


def node_type(node: Dict[str, Any]) -> List[str]:
    t = node.get("@type")
    if isinstance(t, str):
        return [t]
    if isinstance(t, list):
        return [x for x in t if isinstance(x, str)]
    return []


def collect_claimed_text(payload: Any) -> List[Dict[str, str]]:
    """Extract text a page's structured data asserts the page contains.

    Only properties whose entire purpose is to mirror on-page prose are
    collected. Identifiers, URLs and enumerations are deliberately excluded --
    they are not expected to appear as visible text.
    """
    prose_props = {
        "text": "text",
        "description": "description",
        "headline": "headline",
        "articleBody": "articleBody",
        "reviewBody": "reviewBody",
        "name": "name",
    }
    claims: List[Dict[str, str]] = []

    for node in iter_nodes(payload):
        types = node_type(node)
        for prop, label in prose_props.items():
            value = node.get(prop)
            if not isinstance(value, str) or len(value.strip()) < 25:
                continue
            # `name` is only prose-like on question/answer style nodes.
            if prop == "name" and not any(
                t in ("Question", "FAQPage", "HowToStep") for t in types
            ):
                continue
            claims.append(
                {
                    "type": types[0] if types else "?",
                    "property": label,
                    "value": value.strip(),
                }
            )
    return claims


# ---------------------------------------------------------------------------
# Finding construction
# ---------------------------------------------------------------------------


def make_finding(
    fid: str,
    severity: str,
    title: str,
    explanation: str,
    evidence: Dict[str, Any],
    *,
    source: Optional[Dict[str, Any]] = None,
    fix: Optional[str] = None,
    verify: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "id": fid,
        "severity": severity,
        "title": title,
        "explanation": explanation,
        "evidence": evidence,
        "source": source,
        # A finding is only FIXABLE once we know which file produces it.
        "state": "FIXABLE" if source else "OBSERVED",
        "fix": fix,
        "verify": verify,
    }


# ---------------------------------------------------------------------------
# Correlators
# ---------------------------------------------------------------------------


def correlate_raw_vs_rendered(raw: Dict, rendered: Dict, source: Dict) -> List[Dict]:
    """Findings born from what JavaScript adds or changes."""
    out: List[Dict] = []
    if not (raw.get("available") and rendered.get("available")):
        return out

    raw_words = raw.get("word_count", 0)
    rendered_words = rendered.get("word_count", 0)
    delta = rendered_words - raw_words
    ratio = rendered_words / max(raw_words, 1)

    # 1. Body content that only exists after hydration.
    #
    # Absolute word counts alone are a poor test: they miss a short page whose
    # raw view is an empty shell, and they fire on long pages where the delta is
    # only boilerplate. So the rule combines a noise floor (a delta small enough
    # to be whitespace is never a finding) with a proportion (how much of the
    # page depends on JavaScript), and only then with size.
    if delta >= NOISE_FLOOR_WORDS:
        shell = raw_words < THIN_RAW_WORDS and (ratio >= SHELL_RATIO or delta >= 100)
        if shell:
            out.append(
                make_finding(
                    "RENDER-ONLY-BODY",
                    "critical",
                    "The page has no substantive content before JavaScript runs",
                    "A retrieval crawler that does not execute JavaScript receives a shell. "
                    "Everything a machine reader needs to identify, quote or act on this page "
                    "arrives only after hydration.",
                    {
                        "raw_word_count": raw_words,
                        "rendered_word_count": rendered_words,
                        "delta": delta,
                        "ratio": round(ratio, 2),
                        "rule": f"raw < {THIN_RAW_WORDS} words and (ratio >= {SHELL_RATIO} or delta >= 100)",
                    },
                    source=_first_source(source, "client_gated"),
                    fix="Move the content into the server-rendered response (RSC, SSR, SSG "
                    "or prerender). JavaScript may change presentation; it must not gate access.",
                    verify="Re-observe; the raw view must carry the page's information.",
                )
            )
        elif delta >= 100 or (ratio >= PARTIAL_RATIO and delta >= NOISE_FLOOR_WORDS * 2):
            out.append(
                make_finding(
                    "RENDER-ONLY-PARTIAL",
                    "high",
                    f"{delta} words appear only after JavaScript executes",
                    "A meaningful share of this page is invisible to non-executing readers. "
                    "Identify which block it is and whether it carries information a machine "
                    "needs, or only presentation.",
                    {
                        "raw_word_count": raw_words,
                        "rendered_word_count": rendered_words,
                        "delta": delta,
                        "ratio": round(ratio, 2),
                    },
                    source=_first_source(source, "conditional_render"),
                    fix="Server-render the missing block, or confirm it is presentational only.",
                    verify="Re-observe; delta should fall to presentation-only differences.",
                )
            )

    # 2. Directives that disagree between the two views.
    for field, fid, sev, why in (
        (
            "canonical",
            "CANONICAL-DIVERGENCE",
            "high",
            "When a canonical in raw HTML differs from the one JavaScript injects, a "
            "search engine may honour either. The choice is not yours.",
        ),
        (
            "meta_robots",
            "ROBOTS-DIVERGENCE",
            "critical",
            "A robots directive present in raw HTML can be honoured even if JavaScript "
            "later removes it. A raw-side noindex can deindex a page that looks fine in a browser.",
        ),
        (
            "title",
            "TITLE-DIVERGENCE",
            "medium",
            "The title differs between the raw response and the hydrated DOM.",
        ),
    ):
        rv, dv = raw.get(field), rendered.get(field)
        if rv != dv:
            out.append(
                make_finding(
                    fid,
                    sev,
                    f"`{field}` differs between raw and rendered",
                    why,
                    {"raw": rv, "rendered": dv},
                    fix=f"Emit one identical `{field}` server-side; stop mutating it client-side.",
                    verify="Re-observe; both views must report the same value.",
                )
            )

    # 3. Structured data that only exists after hydration.
    if rendered.get("jsonld_count", 0) > raw.get("jsonld_count", 0):
        out.append(
            make_finding(
                "RENDER-ONLY-JSONLD",
                "high",
                "Structured data is injected by JavaScript",
                "JSON-LD added client-side may be processed late or not at all. Markup that "
                "matters -- identity, offers, availability -- belongs in the initial response.",
                {
                    "raw_jsonld_count": raw.get("jsonld_count", 0),
                    "rendered_jsonld_count": rendered.get("jsonld_count", 0),
                },
                source=_first_source(source, "jsonld_emitters"),
                fix="Emit the JSON-LD from the server component or template.",
                verify="Re-observe; raw_jsonld_count must equal rendered_jsonld_count.",
            )
        )

    # 4. Navigation a non-executing crawler cannot follow.
    raw_internal = sum(1 for l in raw.get("links", []) if l.get("kind") == "internal")
    rendered_internal = sum(1 for l in rendered.get("links", []) if l.get("kind") == "internal")
    if rendered_internal > raw_internal * 2 and rendered_internal - raw_internal >= 5:
        out.append(
            make_finding(
                "RENDER-ONLY-LINKS",
                "high",
                f"{rendered_internal - raw_internal} internal links exist only after hydration",
                "Links that materialise client-side are a crawl dead-end for readers that do "
                "not execute JavaScript. Pages reachable only through them may never be discovered.",
                {"raw_internal_links": raw_internal, "rendered_internal_links": rendered_internal},
                source=_first_source(source, "js_only_nav"),
                fix="Render real `<a href>` elements server-side for primary navigation.",
                verify="Re-observe; the internal link counts should converge.",
            )
        )

    # 5. Heading structure that disagrees.
    if raw.get("h1_count") != rendered.get("h1_count"):
        out.append(
            make_finding(
                "H1-DIVERGENCE",
                "medium",
                "The number of `h1` elements differs between raw and rendered",
                "The document outline a machine reader builds depends on which view it gets.",
                {"raw_h1": raw.get("h1_count"), "rendered_h1": rendered.get("h1_count")},
                fix="Emit exactly one server-rendered `h1` per route.",
                verify="Re-observe; both views must report the same count.",
            )
        )

    return out


def correlate_markup_vs_visible(view: Dict, view_name: str, source: Dict) -> List[Dict]:
    """Findings born from structured data promising text the page never shows."""
    out: List[Dict] = []
    if not view.get("available"):
        return out

    haystack = normalise(view.get("text", ""))
    if not haystack:
        return out

    unmatched: List[Dict[str, str]] = []
    total = 0
    for payload in view.get("jsonld", []):
        for claim in collect_claimed_text(payload):
            total += 1
            if not contained(claim["value"], haystack):
                unmatched.append(claim)

    if not unmatched:
        return out

    by_type: Dict[str, int] = {}
    for c in unmatched:
        by_type[c["type"]] = by_type.get(c["type"], 0) + 1

    # FAQPage is the highest-signal case: answers declared, answers not shown.
    faq_unmatched = [c for c in unmatched if c["type"] in ("Question", "FAQPage")]
    if faq_unmatched:
        out.append(
            make_finding(
                "MARKUP-WITHOUT-SUBSTANCE-FAQ",
                "critical",
                f"{len(faq_unmatched)} FAQ answers are declared in JSON-LD but absent from the {view_name} text",
                "The structured data asserts content the page does not show in this view. "
                "This is a divergence between two projections of the same truth, and it is the "
                "shape search engines treat as markup that does not match visible content. "
                "The correct repair is to make the page show the answers -- never to delete the "
                "markup so the two agree on less.",
                {
                    "view": view_name,
                    "unmatched_count": len(faq_unmatched),
                    "total_claims_checked": total,
                    "examples": [c["value"][:160] for c in faq_unmatched[:3]],
                },
                source=_first_source(source, "conditional_render"),
                fix="Render the answers in the initial HTML. A closed `<details>` element is "
                "compliant: hidden by CSS is fine, absent from the document is not.",
                verify="Re-observe; every declared answer must appear in the raw text.",
            )
        )

    other = [c for c in unmatched if c["type"] not in ("Question", "FAQPage")]
    if other:
        out.append(
            make_finding(
                "MARKUP-WITHOUT-SUBSTANCE",
                "high",
                f"{len(other)} structured-data strings have no counterpart in the {view_name} text",
                "Markup asserts prose the page does not display. Either surface the content or "
                "correct the markup to describe what the page really contains.",
                {
                    "view": view_name,
                    "unmatched_count": len(other),
                    "total_claims_checked": total,
                    "by_type": by_type,
                    "examples": [f"{c['type']}.{c['property']}: {c['value'][:120]}" for c in other[:3]],
                },
                fix="Surface the content, or align the markup with the real page.",
                verify="Re-observe; unmatched_count should reach zero.",
            )
        )

    return out


def correlate_source(source: Dict, raw: Dict) -> List[Dict]:
    """Findings the codebase reveals on its own, independent of any URL."""
    out: List[Dict] = []
    if not source.get("available"):
        return out

    gates = source.get("conditional_render", [])
    if gates:
        out.append(
            make_finding(
                "SOURCE-CONDITIONAL-GATE",
                "high" if raw.get("available") else "medium",
                f"{len(gates)} components gate content behind runtime state",
                "Each of these renders content only when a state flag is true. If the gated "
                "content is information rather than presentation, it does not exist for a reader "
                "that never sets that flag.",
                {
                    "count": len(gates),
                    "locations": [f"{g['file']}:{g['line']} ({g['gate']})" for g in gates[:10]],
                },
                source={"file": gates[0]["file"], "line": gates[0]["line"], "all": gates},
                fix="Render the content unconditionally and let CSS or a native `<details>` "
                "handle visibility. Reserve conditional rendering for genuinely presentational state.",
                verify="Re-observe the affected routes; the content must appear in the raw view.",
            )
        )

    nav = source.get("js_only_nav", [])
    if nav:
        out.append(
            make_finding(
                "SOURCE-JS-ONLY-NAV",
                "high",
                f"{len(nav)} navigation handlers have no crawlable `<a href>`",
                "Programmatic navigation is invisible to a reader that does not execute "
                "JavaScript. Any destination reachable only this way is undiscoverable.",
                {"count": len(nav), "locations": [f"{n['file']}:{n['line']}" for n in nav[:10]]},
                source={"file": nav[0]["file"], "line": nav[0]["line"], "all": nav},
                fix="Wrap the target in a real anchor, or add one alongside the handler.",
                verify="Re-observe; the destinations must appear as internal links in the raw view.",
            )
        )

    # Routes whose page component is a client component.
    client_routes = [r for r in source.get("routes", []) if r.get("client_component")]
    if client_routes:
        out.append(
            make_finding(
                "SOURCE-CLIENT-GATED-ROUTE",
                "medium",
                f"{len(client_routes)} route entrypoints are client components",
                "A route whose entrypoint is a client component pushes its whole subtree past "
                "the server boundary. This is legitimate for genuinely interactive routes and "
                "costly for content routes -- verify which of these is which.",
                {
                    "count": len(client_routes),
                    "routes": [f"{r['route']} -> {r['file']}" for r in client_routes[:10]],
                },
                source={"file": client_routes[0]["file"], "line": 1, "all": client_routes},
                fix="Keep the route a server component and push `use client` down to the "
                "smallest interactive leaf.",
                verify="Re-observe each route; the raw view must carry the page's information.",
            )
        )

    return out


def correlate_single_view(view: Dict, view_name: str) -> List[Dict]:
    """Baseline checks that need only one view -- reported at low severity."""
    out: List[Dict] = []
    if not view.get("available"):
        return out

    if view.get("h1_count", 0) == 0:
        out.append(
            make_finding(
                "NO-H1",
                "medium",
                f"No `h1` in the {view_name} view",
                "The document has no primary heading, so its main subject is not declared.",
                {"view": view_name},
                fix="Add exactly one `h1` describing the page subject.",
                verify="Re-observe; h1_count must be 1.",
            )
        )
    elif view.get("h1_count", 0) > 1:
        out.append(
            make_finding(
                "MULTIPLE-H1",
                "low",
                f"{view['h1_count']} `h1` elements in the {view_name} view",
                "Competing primary headings blur the document outline.",
                {"view": view_name, "headings": [h["text"] for h in view.get("headings", []) if h["level"] == 1]},
                fix="Keep one `h1`; demote the rest.",
                verify="Re-observe; h1_count must be 1.",
            )
        )

    if view.get("jsonld_invalid"):
        out.append(
            make_finding(
                "JSONLD-INVALID",
                "high",
                f"{len(view['jsonld_invalid'])} JSON-LD block(s) do not parse",
                "Malformed structured data is ignored entirely; the page gets no benefit from it.",
                {"view": view_name, "errors": view["jsonld_invalid"][:3]},
                fix="Fix the JSON syntax at the emitter.",
                verify="Re-observe; jsonld_invalid must be empty.",
            )
        )

    if not view.get("meta_description"):
        out.append(
            make_finding(
                "NO-META-DESCRIPTION",
                "low",
                f"No meta description in the {view_name} view",
                "The page offers no authored summary of itself.",
                {"view": view_name},
                fix="Add a meta description that reflects the page content.",
                verify="Re-observe; meta_description must be present.",
            )
        )

    return out


def _first_source(source: Dict, key: str) -> Optional[Dict[str, Any]]:
    """Attach a source location when the codebase view offers a credible one."""
    if not source.get("available"):
        return None
    items = source.get(key) or []
    if not items:
        return None
    first = items[0]
    return {"file": first.get("file"), "line": first.get("line"), "all": items}


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def correlate(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    views = snapshot.get("views", {})
    raw = views.get("raw", {})
    rendered = views.get("rendered", {})
    source = views.get("source", {})

    findings: List[Dict] = []
    findings += correlate_raw_vs_rendered(raw, rendered, source)
    findings += correlate_source(source, raw)

    # Prefer the raw view for the markup-vs-visible test: it is the view that
    # models the reader we are protecting. Fall back to rendered when raw is absent.
    if raw.get("available"):
        findings += correlate_markup_vs_visible(raw, "raw", source)
        findings += correlate_single_view(raw, "raw")
    elif rendered.get("available"):
        findings += correlate_markup_vs_visible(rendered, "rendered", source)
        findings += correlate_single_view(rendered, "rendered")

    findings.sort(key=lambda f: (SEVERITY_ORDER.get(f["severity"], 9), f["id"]))

    counts: Dict[str, int] = {}
    for f in findings:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1

    available = [n for n, v in views.items() if v.get("available")]
    return {
        "schema_version": SCHEMA_VERSION,
        "correlated_at": snapshot.get("captured_at"),
        "target": snapshot.get("target"),
        "views_available": available,
        # What this run could not see is part of the result, not an omission.
        "coverage": {
            "correlated": len(available) >= 2,
            "full": len(available) == 3,
            "unavailable": {
                n: v.get("reason") for n, v in views.items() if not v.get("available")
            },
            "note": "Findings requiring an absent view were not evaluated. "
            "This is a bounded result, not a clean bill of health.",
        },
        "counts": counts,
        "total": len(findings),
        "fixable": sum(1 for f in findings if f["state"] == "FIXABLE"),
        "findings": findings,
    }


def to_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Correlated findings\n")
    tgt = report.get("target", {})
    lines.append(f"- **URL**: `{tgt.get('url') or '--'}`")
    lines.append(f"- **Codebase**: `{tgt.get('codebase') or '--'}`")
    lines.append(f"- **Views**: {', '.join(report['views_available']) or 'none'}")
    lines.append(f"- **Findings**: {report['total']} ({report['fixable']} traceable to source)\n")

    unavailable = report["coverage"]["unavailable"]
    if unavailable:
        lines.append("> **Bounded result.** Views not captured in this run:")
        for name, reason in unavailable.items():
            lines.append(f"> - `{name}`: {reason}")
        lines.append("> Findings that depend on them were not evaluated.\n")

    for f in report["findings"]:
        lines.append(f"## [{f['severity'].upper()}] {f['title']}")
        lines.append(f"`{f['id']}` — state: **{f['state']}**\n")
        lines.append(f"{f['explanation']}\n")
        if f.get("source"):
            src = f["source"]
            lines.append(f"**Source**: `{src.get('file')}:{src.get('line')}`\n")
        lines.append("**Evidence**")
        lines.append("```json")
        lines.append(json.dumps(f["evidence"], indent=2, ensure_ascii=False))
        lines.append("```\n")
        if f.get("fix"):
            lines.append(f"**Fix**: {f['fix']}\n")
        if f.get("verify"):
            lines.append(f"**Verify**: {f['verify']}\n")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Correlate observed views into findings.")
    parser.add_argument("snapshot", help="Path to a snapshot produced by fix_observe.py")
    parser.add_argument("--out", "-o", help="Write findings JSON here")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument(
        "--min-severity",
        choices=list(SEVERITY_ORDER),
        help="Drop findings less severe than this",
    )
    args = parser.parse_args()

    try:
        with open(args.snapshot, "r", encoding="utf-8") as fh:
            snapshot = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"cannot read snapshot: {exc}", file=sys.stderr)
        return 1

    report = correlate(snapshot)

    if args.min_severity:
        ceiling = SEVERITY_ORDER[args.min_severity]
        report["findings"] = [
            f for f in report["findings"] if SEVERITY_ORDER.get(f["severity"], 9) <= ceiling
        ]
        report["total"] = len(report["findings"])
        report["fixable"] = sum(1 for f in report["findings"] if f["state"] == "FIXABLE")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, ensure_ascii=False)

    if args.format == "markdown":
        print(to_markdown(report))
    elif not args.out:
        json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
        print()
    else:
        print(f"{report['total']} findings ({report['fixable']} traceable) -> {args.out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
