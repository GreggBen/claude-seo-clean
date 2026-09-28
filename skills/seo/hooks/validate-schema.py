#!/usr/bin/env python3
"""Post-edit schema validation hook for Claude Code.

Validates JSON-LD schema after file edits. Returns exit code 2 to block
if critical validation errors found.

Hook configuration in ~/.claude/settings.json:
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "node",
            "args": [
              "${CLAUDE_PLUGIN_ROOT}/hooks/run-python-hook.js",
              "${CLAUDE_PLUGIN_ROOT}/hooks/validate-schema.py",
              "${tool_input.file_path}"
            ]
          }
        ]
      }
    ]
  }
}

Note: matcher filters by tool name only (Edit, Write). The script itself
checks if the file contains schema markup before validating.
"""

import argparse
import json
import os
import re
import sys
from html.parser import HTMLParser
from typing import List


class _JsonLdParser(HTMLParser):
    def __init__(self, source=False):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.blocks = []
        self.parts = None
        self.dynamic = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "script" and self._dynamic_type():
            self.dynamic += 1
            return
        if tag == "script" and (attributes.get("type") or "").lower() == "application/ld+json":
            if "dangerouslysetinnerhtml" in attributes:
                self.dynamic += 1
            else:
                self.parts = []

    def handle_startendtag(self, tag, attrs):
        if tag == "script" and ((dict(attrs).get("type") or "").lower() == "application/ld+json" or self._dynamic_type()):
            self.dynamic += 1

    def _dynamic_type(self):
        return self.source and bool(re.search(
            r'''\btype\s*=\s*\{\s*["']application/ld\+json["']\s*\}''',
            self.get_starttag_text() or "", re.IGNORECASE,
        ))

    def handle_data(self, data):
        if self.parts is not None:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.parts is not None:
            self.blocks.append("".join(self.parts))
            self.parts = None


def inspect_jsonld(content: str, source: bool = False) -> dict:
    """Distingue validation du HTML et émission dynamique non mesurable en source."""
    parser = _JsonLdParser(source=source)
    parser.feed(content)
    parser.close()
    errors = []
    source_expressions = 0
    if parser.parts is not None:
        errors.append("Unclosed JSON-LD script")
    for i, block in enumerate(parser.blocks, 1):
        try:
            data = json.loads(block.strip())
        except json.JSONDecodeError as e:
            if source and re.match(r"\s*\{\s*[A-Za-z_$]", block):
                source_expressions += 1
                parser.dynamic += 1
                continue
            errors.append(f"Block {i}: Invalid JSON; {e}")
            continue
        if isinstance(data, list):
            for index, item in enumerate(data):
                errors.extend(_validate_schema_object(item, i, location=f"[{index}]"))
        else:
            errors.extend(_validate_schema_object(data, i))
    status = (
        "INVALID" if errors else
        "NOT_MEASURED" if parser.dynamic else
        "VALID" if parser.blocks else "NOT_APPLICABLE"
    )
    return {"status": status, "blocks": len(parser.blocks) - source_expressions, "dynamic_blocks": parser.dynamic, "errors": errors}


def validate_jsonld(content: str) -> List[str]:
    return inspect_jsonld(content)["errors"]


def _validate_schema_object(obj, block_num: int, inherited_context=None, location="") -> List[str]:
    """Validate a single schema object."""
    errors = []
    prefix = f"Block {block_num}{location}"
    if not isinstance(obj, dict):
        return [f"{prefix}: Expected JSON-LD object"]

    context = obj.get("@context", inherited_context)
    if context is None:
        errors.append(f"{prefix}: Missing @context")
    elif context not in ("https://schema.org", "http://schema.org"):
        errors.append(f"{prefix}: @context should be 'https://schema.org'")

    if "@graph" in obj:
        graph = obj["@graph"]
        if not isinstance(graph, list):
            errors.append(f"{prefix}: @graph must be an array")
        else:
            for index, node in enumerate(graph):
                errors.extend(_validate_schema_object(
                    node, block_num, context, f"{location}.@graph[{index}]",
                ))
    elif "@type" not in obj:
        errors.append(f"{prefix}: Missing @type")

    schema_type = obj.get("@type", [])
    types = [schema_type] if isinstance(schema_type, str) else schema_type
    if not isinstance(types, list) or any(not isinstance(item, str) or not item for item in types):
        errors.append(f"{prefix}: Invalid @type")
        types = []
    elif "@type" in obj and not types:
        errors.append(f"{prefix}: Invalid @type")

    # Check for placeholder text
    placeholders = [
        "[Business Name]",
        "[City]",
        "[State]",
        "[Phone]",
        "[Address]",
        "[Your",
        "[INSERT",
        "REPLACE",
        "[URL]",
        "[Email]",
    ]
    text = json.dumps(obj)
    for p in placeholders:
        if p.lower() in text.lower():
            errors.append(f"{prefix}: Contains placeholder text: {p}")

    # Check for deprecated types
    deprecated = {
        "HowTo": "deprecated September 2023",
        "SpecialAnnouncement": "deprecated July 31, 2025",
        "CourseInfo": "retired June 2025",
        "EstimatedSalary": "retired June 2025",
        "LearningVideo": "retired June 2025",
        "ClaimReview": "retired June 2025; fact-check rich results discontinued",
        "VehicleListing": "retired June 2025; vehicle listing structured data discontinued",
    }
    for item in types:
        if item in deprecated:
            errors.append(f"{prefix}: @type '{item}' is {deprecated[item]}")

    # Check for restricted types used incorrectly.
    # FAQPage is intentionally NOT flagged: Google retired FAQ rich results for
    # all sites (May 7, 2026), but the markup still aids AI Mode / AI Overviews
    # entity resolution, so it is valid to ship. See skills/seo-schema/SKILL.md.
    restricted: dict = {}
    for item in types:
        if item in restricted:
            errors.append(f"{prefix}: @type '{item}' is {restricted[item]}; verify site qualifies")

    return errors


def main():
    if len(sys.argv) < 2:
        sys.exit(0)

    parser = argparse.ArgumentParser(description="Validate JSON-LD in HTML or report dynamic source limits")
    parser.add_argument("filepath")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    filepath = args.filepath

    if not os.path.isfile(filepath):
        sys.exit(0)

    # Only validate HTML-like files
    valid_extensions = (".html", ".htm", ".jsx", ".tsx", ".vue", ".svelte", ".php", ".ejs")
    if not filepath.lower().endswith(valid_extensions):
        sys.exit(0)

    # File-size guard: skip files >10MB to bound memory + hook latency.
    # Real source files almost never exceed this; bigger inputs are typically
    # generated, minified bundles or accidental binary writes.
    MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MiB
    try:
        if os.path.getsize(filepath) > MAX_FILE_BYTES:
            sys.exit(0)
    except OSError:
        sys.exit(0)

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except (OSError, IOError):
        sys.exit(0)

    source_file = filepath.lower().endswith((".jsx", ".tsx", ".vue", ".svelte", ".php", ".ejs"))
    report = inspect_jsonld(content, source=source_file)
    errors = report["errors"]

    if args.json:
        print(json.dumps(report, ensure_ascii=False))
        sys.exit(1 if errors else 0)

    if report["dynamic_blocks"]:
        print("NOT_MEASURED: dynamic JSON-LD source; validate the server-rendered HTML.")

    if not errors:
        sys.exit(0)

    # Categorize errors
    critical_keywords = ["placeholder", "deprecated", "retired"]
    critical = [e for e in errors if any(kw in e.lower() for kw in critical_keywords)]
    warnings = [e for e in errors if e not in critical]

    if warnings:
        print("⚠️  Schema validation warnings:")
        for w in warnings:
            print(f"  - {w}")

    if critical:
        print("🛑 Schema validation ERRORS (blocking):")
        for e in critical:
            print(f"  - {e}")
        sys.exit(2)  # Block the edit

    sys.exit(1)  # Warnings only; proceed


if __name__ == "__main__":
    main()
