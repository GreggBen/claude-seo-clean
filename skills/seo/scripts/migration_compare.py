#!/usr/bin/env python3
"""Compare deux sites par manifeste, sans modifier leurs contenus ni leurs URL."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from fetch_page import fetch_page
from fix_observe import analyse_html
from parse_html import parse_html


VERSION = "1.0.0"
FIELDS = (
    "status_code", "final_path", "final_origin", "redirects", "title", "meta_description",
    "canonical", "meta_robots", "h1", "h2", "h3", "schema", "open_graph",
    "x_robots_tag", "cache_control", "content_type",
)


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _origin(base: str) -> str:
    if not isinstance(base, str):
        raise ValueError("Base URL must be a string")
    parsed = urlsplit(base)
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or parsed.path not in {"", "/"} or parsed.query or parsed.fragment):
        raise ValueError("Base URL must be an http(s) origin without credentials")
    return f"{parsed.scheme}://{parsed.netloc}"


def _path(value: str) -> str:
    if (not isinstance(value, str) or not value.startswith("/")
            or value.startswith("//") or "\\" in value or "#" in value
            or any(ord(character) < 33 for character in value)):
        raise ValueError("Page path must be an absolute path without a fragment or host override")
    return value


def _path_query(url: str) -> str:
    parsed = urlsplit(url)
    return (parsed.path or "/") + (f"?{parsed.query}" if parsed.query else "")


def _observed_origin(url: str, requested_url: str) -> str:
    parsed = urlsplit(url)
    requested = urlsplit(requested_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    return "EXPECTED_ORIGIN" if (parsed.scheme, parsed.netloc) == (requested.scheme, requested.netloc) else origin


def _validate_manifest(manifest: dict) -> None:
    if not isinstance(manifest, dict):
        raise ValueError("Manifest must be an object")
    _origin(manifest.get("source_base"))
    _origin(manifest.get("target_base"))
    pages = manifest.get("pages")
    if not isinstance(pages, list) or not pages:
        raise ValueError("Manifest must contain a nonempty pages array")
    seen = set()
    for page in pages:
        if not isinstance(page, dict):
            raise ValueError("Each page must be an object")
        path = _path(page.get("path"))
        _path(page.get("target_path", path))
        if path in seen:
            raise ValueError(f"Duplicate page path: {path}")
        seen.add(path)
        approvals = page.get("approved_differences", {})
        if not isinstance(approvals, dict):
            raise ValueError("approved_differences must be an object")
        for field, approval in approvals.items():
            if field not in FIELDS or not isinstance(approval, dict):
                raise ValueError(f"Invalid approved field: {field}")
            if not all(key in approval for key in ("source", "target", "authority", "evidence")):
                raise ValueError(f"Approval needs values, authority and evidence: {field}")
            if not all(isinstance(approval[key], str) and approval[key].strip()
                       for key in ("authority", "evidence")):
                raise ValueError(f"Approval authority and evidence must be nonempty: {field}")
    frozen = manifest.get("source_frozen_at")
    if frozen is not None:
        if not isinstance(frozen, str) or datetime.fromisoformat(frozen.replace("Z", "+00:00")).tzinfo is None:
            raise ValueError("source_frozen_at must be an ISO timestamp with timezone")


def _error(status: str, reason: str) -> dict:
    return {"status": status, "reason": reason, "fields": None}


def _observe(url: str, capture_name: str | None, directory: Path, timeout: int) -> dict:
    capture_hash = None
    if capture_name is not None:
        if not isinstance(capture_name, str):
            return _error("ERROR", "Capture path must be a string")
        path = (directory / capture_name).resolve()
        if not path.is_relative_to(directory.resolve()):
            return _error("ERROR", "Capture path is outside the manifest directory")
        try:
            data = path.read_bytes()
            capture = json.loads(data)
        except (OSError, ValueError) as exc:
            return _error("ERROR", f"Capture unavailable: {type(exc).__name__}")
        capture_hash = _digest(data)
    else:
        capture = fetch_page(url, timeout=timeout)
        capture["requested_url"] = url
        capture["captured_at"] = datetime.now(timezone.utc).isoformat()
    if not isinstance(capture, dict):
        return _error("ERROR", "Capture must be an object")
    if capture.get("error"):
        return _error("ERROR", str(capture["error"]))
    redirects = capture.get("redirect_details")
    if (not isinstance(redirects, list)
            or any(not isinstance(hop, dict) or not isinstance(hop.get("url"), str)
                   or not isinstance(hop.get("status_code"), int) for hop in redirects)):
        return _error("ERROR", "Invalid redirect capture")
    requested = capture.get("requested_url") or (redirects[0].get("url") if redirects else capture.get("url"))
    if requested != url:
        return _error("ERROR", "Capture does not match the requested URL")
    status_code = capture.get("status_code")
    if status_code in {401, 403}:
        return _error("NOT_AVAILABLE", f"HTTP {status_code}: page access unavailable")
    if not isinstance(status_code, int) or not isinstance(capture.get("content"), str):
        return _error("ERROR", "HTTP status or HTML body was not captured")
    if not capture["content"].strip():
        return _error("ERROR", "Captured HTML body is empty")
    headers = capture.get("headers")
    if not isinstance(headers, dict) or any(not isinstance(key, str) for key in headers):
        return _error("ERROR", "HTTP headers were not captured")
    headers = {key.lower(): value for key, value in headers.items()}
    content_type = headers.get("content-type")
    if not isinstance(content_type, str) or content_type.split(";", 1)[0].strip().lower() not in {"text/html", "application/xhtml+xml"}:
        return _error("ERROR", "HTML Content-Type was not captured")
    final_url = capture.get("url")
    if not isinstance(final_url, str) or not urlsplit(final_url).hostname:
        return _error("ERROR", "Final URL was not captured")
    raw = analyse_html(capture["content"], base_url=final_url)
    if raw["jsonld_invalid"]:
        return _error("ERROR", "Invalid JSON-LD in captured HTML")
    parsed = parse_html(capture["content"], base_url=final_url)
    if len(parsed["canonical_urls"]) > 1:
        return _error("ERROR", "Multiple canonical declarations in captured HTML")
    fields = {
        "status_code": status_code,
        "final_path": _path_query(final_url),
        "final_origin": _observed_origin(final_url, url),
        "redirects": [{"path": _path_query(hop["url"]), "origin": _observed_origin(hop["url"], url),
                       "status_code": hop["status_code"]} for hop in redirects],
        **{field: parsed[field] for field in ("title", "meta_description", "canonical", "meta_robots", "h1", "h2", "h3", "open_graph")},
        "schema": raw["jsonld"],
        "x_robots_tag": headers.get("x-robots-tag"),
        "cache_control": headers.get("cache-control"),
        "content_type": headers.get("content-type"),
    }
    return {
        "status": "OBSERVED",
        "url": final_url,
        "captured_at": capture.get("captured_at", "NOT_VERIFIED_IN_SESSION"),
        "capture_sha256": capture_hash,
        "html_sha256": _digest(capture["content"].encode("utf-8")),
        "fields": fields,
    }


def compare_manifest(manifest: dict, directory: Path, timeout: int = 30) -> dict:
    """Chaque exemption exige les valeurs exactes et une référence d'approbation."""
    _validate_manifest(manifest)
    pages = []
    for page in manifest["pages"]:
        source_url = _origin(manifest["source_base"]) + page["path"]
        target_url = _origin(manifest["target_base"]) + page.get("target_path", page["path"])
        source = _observe(source_url, page.get("source_capture"), directory, timeout)
        target = _observe(target_url, page.get("target_capture"), directory, timeout)
        differences = []
        unused = []
        approvals = page.get("approved_differences", {})
        status = "NOT_MEASURED"
        if source["status"] == target["status"] == "OBSERVED":
            for field in FIELDS:
                old, new = source["fields"][field], target["fields"][field]
                approval = approvals.get(field)
                if old == new:
                    if approval:
                        unused.append(field)
                    continue
                approved = bool(approval and approval["source"] == old and approval["target"] == new)
                difference = {"field": field, "source": old, "target": new,
                              "state": "APPROVED" if approved else "UNEXPECTED"}
                if approved:
                    difference["approval"] = {key: approval[key] for key in ("authority", "evidence")}
                differences.append(difference)
            status = (
                "DIFFERENCES" if unused or any(d["state"] == "UNEXPECTED" for d in differences)
                else "MATCH_WITH_APPROVED_DIFFERENCES" if differences else "MATCH"
            )
        pages.append({"path": page["path"], "status": status, "source": source,
                      "target": target, "differences": differences, "unused_approvals": unused})
    statuses = {page["status"] for page in pages}
    status = (
        "NOT_MEASURED" if "NOT_MEASURED" in statuses else
        "DIFFERENCES" if "DIFFERENCES" in statuses else
        "MATCH_WITH_APPROVED_DIFFERENCES" if "MATCH_WITH_APPROVED_DIFFERENCES" in statuses else "MATCH"
    )
    return {
        "status": status,
        "tool": {"id": "migration_compare", "version": VERSION,
                 "sha256": _digest(Path(__file__).read_bytes())},
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "source_frozen_at": manifest.get("source_frozen_at", "NOT_VERIFIED_IN_SESSION"),
        "pages": pages,
        "limits": [
            "Comparaison du HTML brut et des en-têtes ; rendu JavaScript NOT_MEASURED.",
            "Les références d'approbation et le gel sont déclarés par le manifeste, non authentifiés.",
            "Périmètre limité aux URL du manifeste ; aucun constat de crawl, indexation ou trafic.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    try:
        data = args.manifest.read_bytes()
        report = compare_manifest(json.loads(data), args.manifest.parent, args.timeout)
        report["manifest_sha256"] = _digest(data)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "ERROR", "reason": str(exc)}), file=sys.stderr)
        return 2
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 2 if report["status"] == "NOT_MEASURED" else 1 if report["status"] == "DIFFERENCES" else 0


if __name__ == "__main__":
    sys.exit(main())
