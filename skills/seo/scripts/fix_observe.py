#!/usr/bin/env python3
"""
Capture the three views of a page into a single comparable snapshot.

Why this exists
===============
Every other script in this toolkit answers "what does this page look like?"
with exactly one view. Before v2.0.0 that view was raw HTML, which produced
false negatives on SPAs. v2.0.0 moved every subagent onto the headless
renderer, which fixed the false negatives -- and lost the raw view in the
process. A renderer sees what a browser sees. It no longer sees what a
retrieval crawler sees when it does not execute JavaScript.

Both views are true. The interesting facts live in the *difference* between
them, and in the difference between either one and the source that produced
them. So this script captures all three and refuses to collapse them:

    raw       -- HTTP response body, zero JavaScript executed
    rendered  -- DOM after the page has hydrated (Playwright/Chromium)
    source    -- the codebase that emits the two above

fix_correlate.py consumes the snapshot and derives findings from the deltas.
This script never judges: it observes and records, including recording that
a view was unavailable and why. An absent view is a stated gap, never a
silent zero.

Usage
=====
    python3 fix_observe.py --url https://example.com
    python3 fix_observe.py --url https://example.com --codebase ~/dev/site
    python3 fix_observe.py --codebase ~/dev/site            # source view only
    python3 fix_observe.py --url https://example.com --routes /,/about,/faq
    python3 fix_observe.py --url https://example.com --out snapshot.json

Dependencies degrade explicitly
===============================
    stdlib only        -> raw view works (urllib + html.parser)
    + requests/bs4     -> raw view gains redirect handling and robust parsing
    + playwright       -> rendered view becomes available
Nothing is required for the source view.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

SCHEMA_VERSION = "1.0"

# A retrieval-oriented UA. We are explicitly modelling the reader that does
# not run JavaScript, so we do not pretend to be a full browser here.
DEFAULT_UA = (
    "Mozilla/5.0 (compatible; claude-seo-fix/1.0; +https://github.com/GreggBen/claude-seo-clean)"
)

# ---------------------------------------------------------------------------
# Optional dependencies -- every one of them is allowed to be missing.
# ---------------------------------------------------------------------------

try:
    import requests  # type: ignore

    HAS_REQUESTS = True
except ImportError:  # pragma: no cover - environment dependent
    HAS_REQUESTS = False

try:
    from bs4 import BeautifulSoup  # type: ignore

    HAS_BS4 = True
except ImportError:  # pragma: no cover - environment dependent
    HAS_BS4 = False


# ---------------------------------------------------------------------------
# Fallback HTML extraction (stdlib only)
# ---------------------------------------------------------------------------

_VOID_OR_INVISIBLE = {"script", "style", "noscript", "template", "svg", "head"}


class _StdlibExtractor(HTMLParser):
    """Minimal visible-text + structure extractor used when bs4 is absent.

    Deliberately conservative: it is a fallback, so it prefers under-reporting
    to inventing structure that is not there.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_parts: List[str] = []
        self.headings: List[Dict[str, Any]] = []
        self.links: List[Dict[str, str]] = []
        self.jsonld_raw: List[str] = []
        self.title: Optional[str] = None
        self.meta: Dict[str, str] = {}
        self.canonical: Optional[str] = None
        self.lang: Optional[str] = None
        self.images: List[Dict[str, str]] = []
        self._skip_depth = 0
        self._capture: Optional[str] = None
        self._buffer: List[str] = []
        self._in_title = False
        self._in_jsonld = False

    # -- helpers ----------------------------------------------------------
    def _attrs(self, attrs: List[Tuple[str, Optional[str]]]) -> Dict[str, str]:
        return {k.lower(): (v or "") for k, v in attrs}

    # -- parser hooks -----------------------------------------------------
    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        tag = tag.lower()
        a = self._attrs(attrs)

        if tag == "html" and "lang" in a:
            self.lang = a["lang"]

        if tag == "script" and a.get("type", "").lower() == "application/ld+json":
            self._in_jsonld = True
            self._buffer = []
            return

        if tag in _VOID_OR_INVISIBLE:
            self._skip_depth += 1
            return

        if tag == "title":
            self._in_title = True
            self._buffer = []
        elif tag == "meta":
            key = a.get("name") or a.get("property")
            if key and "content" in a:
                self.meta[key.lower()] = a["content"]
        elif tag == "link" and a.get("rel", "").lower() == "canonical":
            self.canonical = a.get("href")
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._capture = tag
            self._buffer = []
        elif tag == "a" and a.get("href"):
            self._capture = "a"
            self._buffer = []
            self.links.append({"href": a["href"], "text": ""})
        elif tag == "img":
            self.images.append({"src": a.get("src", ""), "alt": a.get("alt", "")})

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()

        if tag == "script" and self._in_jsonld:
            self._in_jsonld = False
            blob = "".join(self._buffer).strip()
            if blob:
                self.jsonld_raw.append(blob)
            self._buffer = []
            return

        if tag in _VOID_OR_INVISIBLE:
            self._skip_depth = max(0, self._skip_depth - 1)
            return

        text = " ".join("".join(self._buffer).split())
        if tag == "title" and self._in_title:
            self.title = text
            self._in_title = False
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6") and self._capture == tag:
            if text:
                self.headings.append({"level": int(tag[1]), "text": text})
            self._capture = None
        elif tag == "a" and self._capture == "a":
            if self.links:
                self.links[-1]["text"] = text
            self._capture = None
        self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._in_jsonld:
            self._buffer.append(data)
            return
        if self._skip_depth:
            return
        if self._capture or self._in_title:
            self._buffer.append(data)
        stripped = data.strip()
        if stripped:
            self.text_parts.append(stripped)


def _extract_with_bs4(html: str) -> Dict[str, Any]:
    parser = "lxml"
    try:
        soup = BeautifulSoup(html, parser)
    except Exception:  # pragma: no cover - lxml missing
        soup = BeautifulSoup(html, "html.parser")

    for node in soup(["script", "style", "noscript", "template"]):
        # Keep JSON-LD payloads before dropping script nodes from the text pass.
        node.extract() if node.name != "script" else None

    jsonld_raw: List[str] = []
    for node in soup.find_all("script", attrs={"type": re.compile("ld\\+json", re.I)}):
        if node.string:
            jsonld_raw.append(node.string.strip())
        elif node.text:
            jsonld_raw.append(node.text.strip())

    for node in soup(["script", "style", "noscript", "template", "svg"]):
        node.decompose()

    meta: Dict[str, str] = {}
    for node in soup.find_all("meta"):
        key = node.get("name") or node.get("property")
        if key and node.get("content") is not None:
            meta[key.lower()] = node.get("content", "")

    canonical_node = soup.find("link", attrs={"rel": re.compile("^canonical$", re.I)})
    html_node = soup.find("html")
    title_node = soup.find("title")

    headings = [
        {"level": int(h.name[1]), "text": " ".join(h.get_text(" ").split())}
        for h in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
        if h.get_text(strip=True)
    ]
    links = [
        {"href": a.get("href", ""), "text": " ".join(a.get_text(" ").split())}
        for a in soup.find_all("a", href=True)
    ]
    images = [
        {"src": img.get("src", ""), "alt": img.get("alt", "")}
        for img in soup.find_all("img")
    ]

    text = " ".join(soup.get_text(" ").split())

    return {
        "title": " ".join(title_node.get_text(" ").split()) if title_node else None,
        "meta": meta,
        "canonical": canonical_node.get("href") if canonical_node else None,
        "lang": html_node.get("lang") if html_node else None,
        "headings": headings,
        "links": links,
        "images": images,
        "jsonld_raw": jsonld_raw,
        "text": text,
    }


def _extract_with_stdlib(html: str) -> Dict[str, Any]:
    p = _StdlibExtractor()
    try:
        p.feed(html)
        p.close()
    except Exception:
        pass
    return {
        "title": p.title,
        "meta": p.meta,
        "canonical": p.canonical,
        "lang": p.lang,
        "headings": p.headings,
        "links": p.links,
        "images": p.images,
        "jsonld_raw": p.jsonld_raw,
        "text": " ".join(" ".join(p.text_parts).split()),
    }


def analyse_html(html: str, base_url: Optional[str] = None) -> Dict[str, Any]:
    """Turn an HTML string into the comparable shape used by every view."""
    raw = _extract_with_bs4(html) if HAS_BS4 else _extract_with_stdlib(html)

    parsed_jsonld: List[Any] = []
    invalid_jsonld: List[Dict[str, str]] = []
    for blob in raw.get("jsonld_raw", []):
        try:
            parsed_jsonld.append(json.loads(blob))
        except json.JSONDecodeError as exc:
            invalid_jsonld.append({"error": str(exc), "excerpt": blob[:200]})

    links = raw.get("links", [])
    if base_url:
        host = urlparse(base_url).netloc
        for link in links:
            href = link.get("href", "")
            if href.startswith(("mailto:", "tel:", "javascript:", "#")):
                link["kind"] = "non-navigational"
                continue
            absolute = urljoin(base_url, href)
            link["absolute"] = absolute
            link["kind"] = "internal" if urlparse(absolute).netloc == host else "external"

    text = raw.get("text", "") or ""
    return {
        "title": raw.get("title"),
        "meta_description": raw.get("meta", {}).get("description"),
        "meta_robots": raw.get("meta", {}).get("robots"),
        "canonical": raw.get("canonical"),
        "lang": raw.get("lang"),
        "headings": raw.get("headings", []),
        "h1_count": sum(1 for h in raw.get("headings", []) if h["level"] == 1),
        "links": links,
        "link_count": len(links),
        "images": raw.get("images", []),
        "images_without_alt": sum(1 for i in raw.get("images", []) if not i.get("alt")),
        "jsonld": parsed_jsonld,
        "jsonld_invalid": invalid_jsonld,
        "jsonld_count": len(parsed_jsonld),
        "text": text,
        "word_count": len(text.split()),
        "html_bytes": len(html.encode("utf-8", errors="ignore")),
        "parser": "bs4" if HAS_BS4 else "stdlib",
    }


# ---------------------------------------------------------------------------
# View 1 -- raw (no JavaScript)
# ---------------------------------------------------------------------------


_META_CHARSET = re.compile(
    rb"""<meta[^>]+charset\s*=\s*["']?\s*([a-zA-Z0-9_\-]+)""", re.I
)


def decode_body(body: bytes, declared: Optional[str]) -> str:
    """Decode a response body, preferring the document's own declaration.

    Servers frequently omit `charset` from Content-Type. HTTP says to assume
    ISO-8859-1 in that case, which mangles every accented character on a UTF-8
    page -- the failure mode that turns "délais" into "dÃ©lais" and quietly
    breaks every downstream text comparison. So: trust an explicit header,
    then the document's own `<meta charset>`, then UTF-8, and only then fall
    back to Latin-1, which cannot raise.
    """
    candidates: List[str] = []
    if declared:
        candidates.append(declared)
    m = _META_CHARSET.search(body[:4096])
    if m:
        try:
            candidates.append(m.group(1).decode("ascii"))
        except UnicodeDecodeError:
            pass
    candidates += ["utf-8", "latin-1"]

    for enc in candidates:
        try:
            return body.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return body.decode("utf-8", errors="replace")


def _declared_charset(content_type: Optional[str]) -> Optional[str]:
    if not content_type or "charset=" not in content_type.lower():
        return None
    return content_type.lower().split("charset=", 1)[1].split(";")[0].strip() or None


def capture_raw(url: str, timeout: int = 30, user_agent: str = DEFAULT_UA) -> Dict[str, Any]:
    """Fetch the HTTP response body without executing any JavaScript."""
    headers = {"User-Agent": user_agent, "Accept": "text/html,application/xhtml+xml"}
    try:
        if HAS_REQUESTS:
            resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            resp_headers = {k.lower(): v for k, v in resp.headers.items()}
            html = decode_body(
                resp.content, _declared_charset(resp_headers.get("content-type"))
            )
            status = resp.status_code
            final_url = resp.url
        else:
            import urllib.request

            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as fh:  # noqa: S310
                body = fh.read()
                html = decode_body(body, fh.headers.get_content_charset())
                status = fh.status
                final_url = fh.geturl()
                resp_headers = {k.lower(): v for k, v in fh.headers.items()}
    except Exception as exc:
        return {
            "available": False,
            "reason": f"{type(exc).__name__}: {exc}",
            "url": url,
        }

    view = analyse_html(html, base_url=final_url)
    view.update(
        {
            "available": True,
            "url": final_url,
            "requested_url": url,
            "status": status,
            "redirected": final_url.rstrip("/") != url.rstrip("/"),
            "x_robots_tag": resp_headers.get("x-robots-tag"),
            "content_type": resp_headers.get("content-type"),
            "html": html,
        }
    )
    return view


# ---------------------------------------------------------------------------
# View 2 -- rendered (JavaScript executed)
# ---------------------------------------------------------------------------


def capture_rendered(url: str, timeout: int = 30, wait_ms: int = 1500) -> Dict[str, Any]:
    """Return the DOM after hydration, or an explicit unavailability record."""
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError:
        return {
            "available": False,
            "reason": "playwright not installed",
            "remedy": "pip install playwright && playwright install chromium",
            "url": url,
        }

    executable = None
    for candidate in ("/opt/pw-browsers/chromium", os.environ.get("CHROMIUM_PATH")):
        if candidate and os.path.exists(candidate):
            executable = candidate
            break

    try:
        with sync_playwright() as pw:
            launch_kwargs: Dict[str, Any] = {"headless": True}
            if executable:
                launch_kwargs["executable_path"] = executable
            browser = pw.chromium.launch(**launch_kwargs)
            page = browser.new_page(user_agent=DEFAULT_UA)
            response = page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")
            try:
                page.wait_for_load_state("networkidle", timeout=timeout * 1000)
            except Exception:
                pass  # networkidle is a nicety, not a requirement
            page.wait_for_timeout(wait_ms)
            html = page.content()
            final_url = page.url
            status = response.status if response else None
            browser.close()
    except Exception as exc:
        return {
            "available": False,
            "reason": f"{type(exc).__name__}: {exc}",
            "url": url,
        }

    view = analyse_html(html, base_url=final_url)
    view.update(
        {
            "available": True,
            "url": final_url,
            "requested_url": url,
            "status": status,
            "html": html,
        }
    )
    return view


# ---------------------------------------------------------------------------
# View 3 -- source (the codebase that emits the other two)
# ---------------------------------------------------------------------------

SKIP_DIRS = {
    ".git", "node_modules", ".next", ".nuxt", "dist", "build", "out",
    ".svelte-kit", "vendor", "__pycache__", ".venv", "venv", "coverage",
    ".turbo", ".cache", "target", ".output",
}

SOURCE_EXT = {".tsx", ".jsx", ".ts", ".js", ".vue", ".svelte", ".astro", ".mdx", ".php", ".html"}


def detect_framework(root: str) -> Dict[str, Any]:
    """Identify the framework so route and metadata conventions can be applied."""
    signals: List[str] = []
    framework = "unknown"
    router = None

    pkg_path = os.path.join(root, "package.json")
    deps: Dict[str, str] = {}
    if os.path.exists(pkg_path):
        try:
            with open(pkg_path, "r", encoding="utf-8") as fh:
                pkg = json.load(fh)
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        except (json.JSONDecodeError, OSError):
            pass

    def has(name: str) -> bool:
        return name in deps

    if has("next"):
        framework = "nextjs"
        signals.append(f"next@{deps.get('next')}")
        if os.path.isdir(os.path.join(root, "app")) or os.path.isdir(os.path.join(root, "src/app")):
            router = "app"
        elif os.path.isdir(os.path.join(root, "pages")) or os.path.isdir(os.path.join(root, "src/pages")):
            router = "pages"
    elif has("nuxt") or has("nuxt3"):
        framework = "nuxt"
    elif has("@sveltejs/kit"):
        framework = "sveltekit"
    elif has("astro"):
        framework = "astro"
    elif has("gatsby"):
        framework = "gatsby"
    elif has("remix") or has("@remix-run/react"):
        framework = "remix"
    elif has("vue"):
        framework = "vue-spa"
    elif has("react"):
        framework = "react-spa"

    if framework == "unknown":
        if os.path.exists(os.path.join(root, "wp-config.php")):
            framework = "wordpress"
        elif os.path.isdir(os.path.join(root, "_layouts")):
            framework = "jekyll"
        elif os.path.exists(os.path.join(root, "config.toml")) or os.path.exists(os.path.join(root, "hugo.toml")):
            framework = "hugo"

    return {"framework": framework, "router": router, "signals": signals, "dependency_count": len(deps)}


def _walk_source(root: str, max_files: int = 6000) -> List[str]:
    found: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for name in filenames:
            if os.path.splitext(name)[1] in SOURCE_EXT:
                found.append(os.path.join(dirpath, name))
                if len(found) >= max_files:
                    return found
    return found


def _route_from_path(rel: str, framework: str, router: Optional[str]) -> Optional[str]:
    """Best-effort mapping from a file path to the URL path it serves."""
    parts = rel.replace(os.sep, "/")
    if framework == "nextjs" and router == "app":
        m = re.match(r"^(?:src/)?app/(.*)/page\.(tsx|jsx|ts|js)$", parts)
        if m:
            segs = [s for s in m.group(1).split("/") if s and not (s.startswith("(") and s.endswith(")"))]
            return "/" + "/".join(segs) if segs else "/"
        if re.match(r"^(?:src/)?app/page\.(tsx|jsx|ts|js)$", parts):
            return "/"
    if framework == "nextjs" and router == "pages":
        m = re.match(r"^(?:src/)?pages/(.*)\.(tsx|jsx|ts|js)$", parts)
        if m and not m.group(1).startswith("_") and "/api/" not in parts:
            route = m.group(1)
            route = re.sub(r"/index$", "", route)
            return "/" + route if route and route != "index" else "/"
    if framework == "astro":
        m = re.match(r"^(?:src/)?pages/(.*)\.astro$", parts)
        if m:
            route = re.sub(r"/index$", "", m.group(1))
            return "/" + route if route and route != "index" else "/"
    if framework == "sveltekit":
        m = re.match(r"^(?:src/)?routes/(.*)/\+page\.svelte$", parts)
        if m:
            return "/" + m.group(1)
        if re.match(r"^(?:src/)?routes/\+page\.svelte$", parts):
            return "/"
    return None


def capture_source(root: str, max_files: int = 6000) -> Dict[str, Any]:
    """Index the codebase: framework, routes, client-gating and markup emitters."""
    root = os.path.abspath(os.path.expanduser(root))
    if not os.path.isdir(root):
        return {"available": False, "reason": f"not a directory: {root}"}

    detected = detect_framework(root)
    framework = detected["framework"]
    router = detected["router"]

    files = _walk_source(root, max_files=max_files)
    routes: List[Dict[str, Any]] = []
    client_gated: List[Dict[str, Any]] = []
    jsonld_emitters: List[Dict[str, Any]] = []
    js_only_nav: List[Dict[str, Any]] = []
    conditional_render: List[Dict[str, Any]] = []

    for path in files:
        rel = os.path.relpath(path, root)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except OSError:
            continue

        lines = content.splitlines()
        head = "\n".join(lines[:5])
        is_client = bool(re.search(r"^\s*['\"]use client['\"]", head, re.M))

        route = _route_from_path(rel, framework, router)
        if route is not None:
            routes.append({"route": route, "file": rel, "client_component": is_client})

        if is_client:
            # The directive sits at the top of the file, so line 1 is the honest
            # anchor -- never emit a null line, it renders as "file:None".
            client_gated.append({"file": rel, "line": 1, "route": route})

        for i, line in enumerate(lines, start=1):
            if "application/ld+json" in line or "jsonLd" in line or "json-ld" in line.lower():
                jsonld_emitters.append({"file": rel, "line": i, "excerpt": line.strip()[:180]})
            # Navigation that a non-JS reader cannot follow.
            if re.search(r"onClick=\{[^}]*(router\.push|navigate|history\.push)", line):
                js_only_nav.append({"file": rel, "line": i, "excerpt": line.strip()[:180]})
            # Content whose presence in the DOM depends on runtime state.
            m = re.search(r"\b(isOpen|isExpanded|showMore|expanded|isVisible|activeTab)\b\s*&&", line)
            if m:
                conditional_render.append(
                    {"file": rel, "line": i, "gate": m.group(1), "excerpt": line.strip()[:180]}
                )

    # Deduplicate routes discovered through several conventions.
    seen: set = set()
    unique_routes = []
    for r in sorted(routes, key=lambda x: x["route"]):
        if r["route"] not in seen:
            seen.add(r["route"])
            unique_routes.append(r)

    return {
        "available": True,
        "root": root,
        **detected,
        "file_count": len(files),
        "truncated": len(files) >= max_files,
        "routes": unique_routes,
        "route_count": len(unique_routes),
        "client_gated": client_gated,
        "jsonld_emitters": jsonld_emitters,
        "js_only_nav": js_only_nav,
        "conditional_render": conditional_render,
    }


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def observe(
    url: Optional[str] = None,
    codebase: Optional[str] = None,
    timeout: int = 30,
    skip_rendered: bool = False,
    user_agent: str = DEFAULT_UA,
) -> Dict[str, Any]:
    snapshot: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "target": {"url": url, "codebase": codebase},
        "views": {},
        "capabilities": {
            "requests": HAS_REQUESTS,
            "bs4": HAS_BS4,
            "playwright": None,  # resolved below
        },
    }

    if url:
        snapshot["views"]["raw"] = capture_raw(url, timeout=timeout, user_agent=user_agent)
        if skip_rendered:
            snapshot["views"]["rendered"] = {
                "available": False,
                "reason": "skipped by --no-render",
                "url": url,
            }
        else:
            snapshot["views"]["rendered"] = capture_rendered(url, timeout=timeout)
        snapshot["capabilities"]["playwright"] = snapshot["views"]["rendered"].get(
            "reason"
        ) != "playwright not installed"
    else:
        snapshot["views"]["raw"] = {"available": False, "reason": "no --url provided"}
        snapshot["views"]["rendered"] = {"available": False, "reason": "no --url provided"}

    if codebase:
        snapshot["views"]["source"] = capture_source(codebase)
    else:
        snapshot["views"]["source"] = {"available": False, "reason": "no --codebase provided"}

    available = [name for name, v in snapshot["views"].items() if v.get("available")]
    snapshot["mode"] = {
        "views_available": available,
        "correlated": len(available) >= 2,
        "full": len(available) == 3,
    }
    return snapshot


def _strip_html(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Drop the bulky html payloads for terminal display."""
    clone = json.loads(json.dumps(snapshot))
    for view in clone.get("views", {}).values():
        view.pop("html", None)
        view.pop("text", None)
    return clone


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture raw, rendered and source views into one snapshot."
    )
    parser.add_argument("--url", help="URL to observe (raw + rendered views)")
    parser.add_argument("--codebase", help="Path to the repository that produces the site")
    parser.add_argument("--out", "-o", help="Write the full snapshot JSON here")
    parser.add_argument("--timeout", "-t", type=int, default=30, help="Per-request timeout (s)")
    parser.add_argument("--no-render", action="store_true", help="Skip the rendered view")
    parser.add_argument("--user-agent", default=DEFAULT_UA, help="UA for the raw fetch")
    parser.add_argument("--summary", action="store_true", help="Print a human summary, not JSON")
    args = parser.parse_args()

    if not args.url and not args.codebase:
        parser.error("provide at least one of --url or --codebase")

    snapshot = observe(
        url=args.url,
        codebase=args.codebase,
        timeout=args.timeout,
        skip_rendered=args.no_render,
        user_agent=args.user_agent,
    )

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(snapshot, fh, indent=2, ensure_ascii=False)

    if args.summary:
        views = snapshot["views"]
        print(f"captured_at : {snapshot['captured_at']}")
        print(f"mode        : {', '.join(snapshot['mode']['views_available']) or 'none'}")
        for name in ("raw", "rendered", "source"):
            v = views.get(name, {})
            if not v.get("available"):
                print(f"  {name:<9}: UNAVAILABLE -- {v.get('reason')}")
                continue
            if name == "source":
                print(
                    f"  {name:<9}: {v['framework']}"
                    + (f"/{v['router']}" if v.get("router") else "")
                    + f", {v['route_count']} routes, {v['file_count']} files"
                )
            else:
                print(
                    f"  {name:<9}: {v['word_count']} words, {v['h1_count']} h1, "
                    f"{v['jsonld_count']} json-ld, {v['link_count']} links"
                )
        if args.out:
            print(f"\nsnapshot -> {args.out}")
    elif not args.out:
        json.dump(_strip_html(snapshot), sys.stdout, indent=2, ensure_ascii=False)
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
