#!/usr/bin/env python3
"""
Google Search Console Search Analytics query helper.

Queries the GSC Search Analytics API for clicks, impressions, CTR, and position
data. Supports filtering by dimensions, auto-pagination, and quick-win detection.

Usage:
    python gsc_query.py --property sc-domain:example.com
    python gsc_query.py --property sc-domain:example.com --days 90 --dimensions query
    python gsc_query.py sitemaps --property sc-domain:example.com
    python gsc_query.py sites
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from typing import Optional

try:
    from googleapiclient.discovery import build
except ImportError:
    print(
        "Error: google-api-python-client required. "
        "Install with: pip install google-api-python-client",
        file=sys.stderr,
    )
    sys.exit(1)

try:
    from google_auth import get_oauth_credentials, load_config
except ImportError:
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from google_auth import get_oauth_credentials, load_config

GSC_SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
INDEXATION_NOTE = (
    "Sitemaps API contents[].submitted reflects submitted URL counts only. "
    "Use the URL Inspection API as the indexation truth for whether specific "
    "URLs are indexed."
)
METRIC_KEYS = ("clicks", "impressions", "ctr", "position")
ROW_SUM_LIMIT = (
    "La somme des lignes dimensionnelles peut exclure les requêtes anonymisées "
    "et les lignes non retournées par GSC ; elle ne constitue pas le total de la propriété."
)


def _metrics(row: dict) -> dict:
    impressions = row.get("impressions")
    ctr = row.get("ctr")
    position = row.get("position")
    return {
        "clicks": row.get("clicks"),
        "impressions": impressions,
        "ctr": round(ctr * 100, 2) if ctr is not None and impressions != 0 else None,
        "position": round(position, 1) if position is not None and impressions != 0 else None,
    }


def _display_metric(value, suffix: str = "") -> str:
    return f"{value:,}{suffix}" if value is not None else "NOT_AVAILABLE"


def _build_gsc_service():
    """Build the Search Console API service."""
    credentials = get_oauth_credentials(GSC_SCOPES)
    if not credentials:
        return None
    try:
        return build("searchconsole", "v1", credentials=credentials)
    except Exception as e:
        print(f"Error building GSC service: {e}", file=sys.stderr)
        return None


def _query_site_totals(
    service,
    site_url: str,
    start_date: str,
    end_date: str,
    search_type: str,
    data_state: str,
    filters: Optional[list],
) -> dict:
    """Fetch true site-wide totals via a dimensionless query.

    GSC anonymizes click data for low-volume ("rare") queries, so summing
    the per-query rows undercounts clicks (often to exactly 0) and
    impressions. A query with an empty ``dimensions`` array returns a
    single aggregate row carrying the real site totals (issue #130).
    Retourne séparément les métriques, leur état et l'erreur d'agrégation.
    """
    body = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": [],
        "type": search_type,
        "rowLimit": 1,
        "dataState": data_state,
    }
    if filters:
        body["dimensionFilterGroups"] = [{"filters": filters}]
    try:
        response = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
    except Exception as exc:
        return {"totals": dict.fromkeys(METRIC_KEYS), "status": "ERROR", "error": str(exc)}
    rows = response.get("rows", [])
    if not rows:
        return {"totals": dict.fromkeys(METRIC_KEYS), "status": "NOT_AVAILABLE", "error": None}
    totals = _metrics(rows[0])
    required = ("clicks", "impressions") if totals["impressions"] == 0 else METRIC_KEYS
    status = "OK" if all(totals[key] is not None for key in required) else "PARTIAL"
    return {"totals": totals, "status": status, "error": None}


def query_search_analytics(
    site_url: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    dimensions: Optional[list] = None,
    search_type: str = "web",
    row_limit: int = 1000,
    filters: Optional[list] = None,
    data_state: str = "final",
) -> dict:
    """
    Query GSC Search Analytics API.

    Args:
        site_url: GSC property (e.g., 'sc-domain:example.com' or 'https://example.com/').
        start_date: Start date (YYYY-MM-DD). Default: 28 days ago.
        end_date: End date (YYYY-MM-DD). Default: 3 days ago (data lag).
        dimensions: List of dimensions: query, page, country, device, date, searchAppearance.
        search_type: web, image, video, news, discover, googleNews.
        row_limit: Max rows per request (1-25000). Auto-paginates if more.
        filters: List of filter dicts with dimension, operator, expression.
        data_state: 'final' or 'all' (includes fresh/unfinalized data).

    Returns:
        Dictionary with rows, totals, states, totals provenance, and quick_wins.
        CTR values are percentage points (``ctr_unit="percent"``), including legacy consumers.
    """
    result = {
        "property": site_url,
        "rows": [],
        "status": "ERROR",
        "totals": dict.fromkeys(METRIC_KEYS),
        "totals_status": "ERROR",
        "totals_source": None,
        "totals_error": None,
        "ctr_unit": "percent",
        "limits": [],
        "quick_wins": [],
        "row_count": None,
        "error": None,
    }

    service = _build_gsc_service()
    if not service:
        result["error"] = "Could not build GSC service. Check service account credentials."
        return result

    if not start_date:
        start_date = (datetime.now() - timedelta(days=28)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    if dimensions is None:
        dimensions = ["query", "page"]

    result["date_range"] = {"start": start_date, "end": end_date}

    body = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": dimensions,
        "type": search_type,
        "rowLimit": min(row_limit, 25000),
        "dataState": data_state,
    }

    if filters:
        body["dimensionFilterGroups"] = [{"filters": filters}]

    # Auto-paginate
    all_rows = []
    start_row = 0
    page_size = min(row_limit, 25000)

    try:
        while True:
            body["startRow"] = start_row
            body["rowLimit"] = page_size

            response = service.searchanalytics().query(
                siteUrl=site_url, body=body
            ).execute()

            rows = response.get("rows", [])
            all_rows.extend(rows)

            if len(rows) < page_size:
                break

            start_row += page_size

            # Safety: cap at 100,000 rows
            if start_row >= 100000:
                break

    except Exception as e:
        error_str = str(e)
        if "403" in error_str:
            result["error"] = (
                f"Permission denied for property '{site_url}'. "
                "Ensure the service account email is added as a user in "
                "Google Search Console > Settings > Users and permissions."
            )
        elif "404" in error_str:
            result["error"] = (
                f"Property '{site_url}' not found. "
                "Use 'sc-domain:example.com' for domain properties or "
                "'https://example.com/' for URL-prefix properties."
            )
        else:
            result["error"] = f"GSC API error: {e}"
        return result

    # Process rows
    for row in all_rows:
        keys = row.get("keys", [])
        processed = {
            "keys": keys,
            **_metrics(row),
        }

        # Label keys by dimension name
        for i, dim in enumerate(dimensions):
            if i < len(keys):
                processed[dim] = keys[i]

        result["rows"].append(processed)

    result["row_count"] = len(all_rows)

    # Site totals come from a dimensionless aggregate query, NOT from summing
    # the per-dimension rows. Summing query-dimension rows undercounts clicks
    # because GSC anonymizes low-volume queries, producing a false "0 clicks"
    # site total (issue #130). Fall back to the row sum only if the aggregate
    # query fails.
    site_totals = _query_site_totals(
        service, site_url, start_date, end_date, search_type, data_state, filters
    )
    result["totals_error"] = site_totals["error"]
    if site_totals["status"] != "ERROR":
        result["totals"] = site_totals["totals"]
        result["totals_status"] = site_totals["status"]
        result["totals_source"] = "dimensionless_aggregate"
        result["status"] = site_totals["status"]
        if site_totals["status"] == "NOT_AVAILABLE" and all_rows:
            result["status"] = "PARTIAL"
    elif all_rows:
        result["status"] = "PARTIAL"
        result["totals_status"] = "PARTIAL"
        result["totals_source"] = "dimension_row_sum"
        result["limits"].append(ROW_SUM_LIMIT)
        for key in ("clicks", "impressions"):
            values = [row[key] for row in result["rows"]]
            if all(value is not None for value in values):
                result["totals"][key] = sum(values)
        total_clicks = result["totals"]["clicks"]
        total_impressions = result["totals"]["impressions"]
        if total_clicks is not None and total_impressions is not None and total_impressions > 0:
            result["totals"]["ctr"] = round((total_clicks / total_impressions) * 100, 2)
    else:
        result["error"] = f"GSC aggregate query error: {site_totals['error']}"

    # Quick wins: position 4-10 with high impressions
    if "query" in dimensions:
        sorted_by_impressions = sorted(result["rows"], key=lambda r: r["impressions"] or 0, reverse=True)
        for row in sorted_by_impressions[:200]:
            pos = row["position"]
            impressions = row["impressions"]
            if pos is not None and 4 <= pos <= 10 and impressions is not None and impressions > 50:
                result["quick_wins"].append({
                    "keys": row.get("keys", []),
                    "position": round(pos, 1),
                    "impressions": impressions,
                    "clicks": row["clicks"],
                    "ctr": row["ctr"],
                    "opportunity": "Position 4-10 with high impressions -- candidate for review; traffic gain is not established",
                })

        result["quick_wins"] = result["quick_wins"][:20]

    return result


def list_sitemaps(site_url: str) -> dict:
    """
    List sitemaps for a GSC property.

    Args:
        site_url: GSC property URL.

    Returns:
        Dictionary with sitemaps list.
    """
    result = {"property": site_url, "sitemaps": [], "error": None}

    service = _build_gsc_service()
    if not service:
        result["error"] = "Could not build GSC service."
        return result

    try:
        response = service.sitemaps().list(siteUrl=site_url).execute()
        for sm in response.get("sitemap", []):
            contents = [
                {k: v for k, v in item.items() if k != "indexed"}
                for item in sm.get("contents", [])
            ]
            result["sitemaps"].append({
                "path": sm.get("path"),
                "last_submitted": sm.get("lastSubmitted"),
                "is_pending": sm.get("isPending"),
                "is_index": sm.get("isSitemapsIndex"),
                "type": sm.get("type"),
                "warnings": sm.get("warnings", 0),
                "errors": sm.get("errors", 0),
                "contents": contents,
                "indexation_note": INDEXATION_NOTE,
            })
    except Exception as e:
        result["error"] = f"Error listing sitemaps: {e}"

    return result


def list_sites() -> dict:
    """
    List all verified GSC properties.

    Returns:
        Dictionary with sites list.
    """
    result = {"sites": [], "error": None}

    service = _build_gsc_service()
    if not service:
        result["error"] = "Could not build GSC service."
        return result

    try:
        response = service.sites().list().execute()
        for site in response.get("siteEntry", []):
            result["sites"].append({
                "url": site.get("siteUrl"),
                "permission": site.get("permissionLevel"),
            })
    except Exception as e:
        result["error"] = f"Error listing sites: {e}"

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Google Search Console Search Analytics query helper"
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="query",
        choices=["query", "sitemaps", "sites"],
        help="Command: query (default), sitemaps, sites",
    )
    parser.add_argument(
        "--property", "-p",
        help="GSC property (e.g., sc-domain:example.com). Uses default from config if not specified.",
    )
    parser.add_argument("--days", "-d", type=int, default=28, help="Number of days (default: 28)")
    parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")
    parser.add_argument(
        "--dimensions",
        default="query,page",
        help="Comma-separated dimensions (default: query,page)",
    )
    parser.add_argument("--type", default="web", help="Search type (default: web)")
    parser.add_argument("--limit", type=int, default=1000, help="Row limit (default: 1000)")
    parser.add_argument(
        "--device",
        choices=["desktop", "mobile", "tablet"],
        help="Filter by device type",
    )
    parser.add_argument("--country", help="Filter by country (ISO 3166-1 alpha-3, e.g., USA)")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    # Resolve property
    prop = args.property
    if not prop:
        config = load_config()
        prop = config.get("default_property")
    if not prop and args.command != "sites":
        print("Error: No property specified. Use --property or set default_property in config.", file=sys.stderr)
        sys.exit(1)

    if args.command == "sites":
        result = list_sites()
    elif args.command == "sitemaps":
        result = list_sitemaps(prop)
    else:
        start = args.start_date or (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
        end = args.end_date or (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        dims = [d.strip() for d in args.dimensions.split(",")]
        filters = []
        if args.device:
            filters.append({
                "dimension": "device",
                "operator": "equals",
                "expression": args.device.upper(),
            })
        if args.country:
            filters.append({
                "dimension": "country",
                "operator": "equals",
                "expression": args.country.upper(),
            })
        result = query_search_analytics(
            prop, start_date=start, end_date=end,
            dimensions=dims, search_type=args.type, row_limit=args.limit,
            filters=filters if filters else None,
        )

    if result.get("error"):
        print(f"Error: {result['error']}", file=sys.stderr)
        if not args.json:
            sys.exit(1)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if args.command == "sites":
            print("=== Verified GSC Properties ===")
            for site in result.get("sites", []):
                print(f"  {site['url']} ({site['permission']})")
        elif args.command == "sitemaps":
            print(f"=== Sitemaps for {prop} ===")
            for sm in result.get("sitemaps", []):
                status = "pending" if sm.get("is_pending") else "processed"
                print(f"  {sm['path']} [{status}] errors={sm.get('errors', 0)} warnings={sm.get('warnings', 0)}")
            if result.get("sitemaps"):
                print(f"\nNote: {INDEXATION_NOTE}")
        else:
            totals = result.get("totals", {})
            print(f"=== Search Analytics: {prop} ===")
            print(f"Period: {result.get('date_range', {}).get('start')} to {result.get('date_range', {}).get('end')}")
            print(f"Status: {result['status']} | Totals: {result['totals_status']} | Source: {result['totals_source'] or 'NOT_AVAILABLE'}")
            print(f"Clicks: {_display_metric(totals.get('clicks'))} | Impressions: {_display_metric(totals.get('impressions'))} | CTR: {_display_metric(totals.get('ctr'), '%')} | Rows: {_display_metric(result.get('row_count'))}")
            if result["totals_error"]:
                print(f"Aggregate error: {result['totals_error']}", file=sys.stderr)
            for limit in result["limits"]:
                print(f"Limit: {limit}")

            qw = result.get("quick_wins", [])
            if qw:
                print(f"\nQuick Wins ({len(qw)} found):")
                for w in qw[:10]:
                    keys = " | ".join(w.get("keys", []))
                    print(f"  Pos {w['position']} | {w['impressions']:,} imp | {_display_metric(w['clicks'])} clicks | {keys}")

    if result.get("error"):
        sys.exit(1)


if __name__ == "__main__":
    main()
