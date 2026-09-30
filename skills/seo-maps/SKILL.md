---
name: seo-maps
description: >
  Maps presence analysis for local businesses using free public sources:
  Overpass and OpenStreetMap competitor discovery, optional Geoapify POI search,
  Nominatim geocoding, visible GBP signals, cross-platform NAP checks, and
  LocalBusiness schema recommendations. Use when the user asks for maps presence,
  a GBP audit, local competitors, or NAP consistency.
user-invocable: true
argument-hint: "[command] [url|business|location]"
license: MIT
compatibility: "Public Overpass and Nominatim APIs; optional Geoapify key"
metadata:
  author: AgriciDaniel
  version: "2.2.0"
  category: seo
---

# Maps Presence Analysis

This skill assesses evidence visible on public pages and free data sources.
Report live local-pack rank, geo-grid position, review velocity, and private
GBP fields as unknown unless a trustworthy source actually provides them.

## Commands

| Command | Analysis |
|---------|----------|
| `/seo maps <url>` | Public maps presence and NAP audit |
| `/seo maps competitors <keyword> <location>` | Nearby POIs by OSM category |
| `/seo maps nap <business-name>` | Cross-platform NAP consistency |
| `/seo maps schema <business-name>` | LocalBusiness JSON-LD from verified facts |
| `/seo maps gbp <business> <location>` | Visible GBP signals and manual checklist |

## Sources

1. Identify the business name, public address or service area, and category from
   the target website or user-provided details.
2. Use Nominatim to geocode a public address, respecting its usage policy and
   1 request/second limit.
3. Query Overpass for nearby businesses with matching OSM tags. Geoapify is
   optional when the user already has a key.
4. Check visible Google, Bing, Apple, and OSM listings. Mark unavailable fields
   unknown; a search result snippet does not prove ownership or completeness.

Load `../seo/references/maps-free-apis.md`, `../seo/references/maps-gbp-checklist.md`,
and `../seo/references/local-schema-types.md` as needed. `seo-local` handles the
website's own local content; keep this analysis focused on maps and listings.

## Analysis

### GBP profile

Apply the checklist only to fields visible from public sources. Report the
observed fields and unknown fields separately; score completeness only when
the needed fields are observable. Do not invent a GBP category, opening hours,
review count, or verification status.

### Competitors

Use business category and distance to build a nearby POI table. Show source,
search radius, and data timestamp. OSM coverage varies by location and is not
a measure of local-pack rank or market share.

### NAP consistency

Compare observed name, public address, and phone across platforms. For a
service-area business with a hidden address, do not penalize the absence of a
street address. Label each comparison as match, partial match, conflict, or
unknown. Recommend claiming or correcting listings only from observed evidence.

### Schema

Recommend the most specific justified `LocalBusiness` subtype. Use only
verified public facts in generated JSON-LD. Omit unknown properties. Do not
generate self-serving review markup for the business's own site.

## Output

Write `MAPS-ANALYSIS-{domain}.md` with the observed sources, GBP checklist,
NAP comparison, nearby POIs, schema recommendations, prioritized actions, and
the data that could not be assessed. If the audit orchestrator supplies an
`output_dir`, write `output_dir/findings/maps.md` and JSON-compatible findings
for its Maps Visibility category.

## Error Handling

| Scenario | Action |
|----------|--------|
| Business identity ambiguous | Ask for a specific location or public listing URL. |
| Nominatim or Overpass rate limited | Stop requests, report partial data and retry guidance. |
| Listing unavailable | Mark platform status unknown; do not infer absence. |
| No public address for a service-area business | Analyze service area and visible NAP fields. |
