---
name: seo-drift
description: >
  SEO drift monitoring: capture baselines of SEO-critical elements, detect changes,
  and track regressions over time. Git for SEO — baseline, diff, and track changes
  to your on-page SEO. Use when user says "SEO drift", "baseline", "track changes",
  "did anything break", "SEO regression", "compare SEO", "before and after",
  "monitor SEO changes", or "deployment check".
user-invocable: true
argument-hint: "baseline|compare|history <url>"
license: MIT
metadata:
  author: AgriciDaniel
  original_author: "Dan Colta (Pro Hub Challenge)"
  version: "2.3.0"
  category: seo
---

# SEO Drift Monitor (April 2026)

Git for your SEO. Capture baselines, detect regressions, track changes over time.

---

## Commands

| Command | Purpose |
|---------|---------|
| `/seo drift baseline <url>` | Capture current SEO state as a "known good" snapshot |
| `/seo drift compare <url>` | Compare current page state to stored baseline |
| `/seo drift history <url>` | Show change history and past comparisons |
| `/seo drift migration <manifest.json>` | Comparer deux sites par URL et écarts approuvés |

## Comparaison de migration

```bash
~/.claude/skills/seo/run-script migration_compare.py manifest.json --output rapport.json
```

Le manifeste désigne les origines et les chemins exacts, sans supprimer les
slashes ni remplacer automatiquement les domaines dans les canonical ou graphes.
Chaque exemption porte ses deux valeurs attendues, son autorité et sa preuve :

```json
{
  "source_base": "https://source.example",
  "target_base": "https://preview.example",
  "pages": [{
    "path": "/offres/",
    "approved_differences": {
      "x_robots_tag": {
        "source": null,
        "target": "noindex, nofollow",
        "authority": "GREGG",
        "evidence": "Référence de la décision autorisant la protection de la preview"
      }
    }
  }]
}
```

`source_frozen_at` peut renseigner le gel déclaré (ISO 8601 avec fuseau).
Sans date, le rapport conserve `NOT_VERIFIED_IN_SESSION`. `target_path` permet
de désigner un chemin cible différent. Les URL hors manifeste restent hors
périmètre : aucune découverte exhaustive n'est revendiquée.

Pour une preview protégée ou une reproduction hors réseau, ajouter
`source_capture` et `target_capture` à chaque page : fichiers JSON relatifs au
dossier du manifeste, issus de `fetch_page.fetch_page()`, avec `captured_at`
et `requested_url` renseignés lors de la capture. Les captures et rapports
restent dans un dossier privé ou ignoré par Git. Les en-têtes de session ne
sont pas repris dans le rapport ; aucun contournement d'authentification n'est effectué.

Le rapport compare statut HTTP, chemin et origine finaux, redirections, titre,
description, canonical, robots HTML/HTTP, h1–h3, JSON-LD, Open Graph, cache et
type de contenu. Une absence observée demeure `null` ; un accès 401/403, une
capture manquante ou un JSON-LD invalide empêche un résultat de parité.

- Code 0 : `MATCH` ou `MATCH_WITH_APPROVED_DIFFERENCES`.
- Code 1 : `DIFFERENCES` (écart inattendu ou exemption devenue inutilisée).
- Code 2 : `NOT_MEASURED` ou erreur de manifeste.

Le rapport fournit version/hash du script, hash du manifeste et des captures,
dates, écarts et références d'approbation. Il valide uniquement les éléments
observés ; rendu JavaScript, crawl, indexation et audience restent non mesurés.
Les références d'approbation sont déclarées, non authentifiées par l'outil.

---

## What It Captures

Every baseline records these SEO-critical elements:

| Element | Field | Source |
|---------|-------|--------|
| Title tag | `title` | `parse_html.py` |
| Meta description | `meta_description` | `parse_html.py` |
| Canonical URL | `canonical` | `parse_html.py` |
| Robots directives | `meta_robots` | `parse_html.py` |
| H1 headings | `h1` (array) | `parse_html.py` |
| H2 headings | `h2` (array) | `parse_html.py` |
| H3 headings | `h3` (array) | `parse_html.py` |
| JSON-LD schema | `schema` (array) | `parse_html.py` |
| Open Graph tags | `open_graph` (dict) | `parse_html.py` |
| Core Web Vitals | `cwv` (dict) | `pagespeed_check.py` |
| HTTP status code | `status_code` | `fetch_page.py` |
| HTML content hash | `html_hash` (SHA-256) | Computed |
| Schema content hash | `schema_hash` (SHA-256) | Computed |

---

## How Comparison Works

The comparison engine applies **17 rules across 3 severity levels**. Load
`references/comparison-rules.md` for the full rule set with thresholds,
recommended actions, and cross-skill references.

### Severity Levels

| Level | Meaning | Response Time |
|-------|---------|---------------|
| **CRITICAL** | SEO-breaking change, likely traffic loss | Immediate |
| **WARNING** | Potential impact, needs investigation | Within 1 week |
| **INFO** | Awareness only, may be intentional | Review at convenience |

---

## Storage

All data is stored locally in SQLite:

```
~/.cache/claude-seo/drift/baselines.db
```

### Tables

- **baselines**: Captured snapshots with all SEO elements
- **comparisons**: Diff results with triggered rules and severities

URL normalization ensures consistent matching: lowercase scheme/host, strip
default ports (80/443), sort query parameters, remove UTM parameters, strip
trailing slashes.

---

## Command: `baseline`

Captures the current state of a page and stores it.

**Steps:**
1. Validate URL (SSRF protection via `google_auth.validate_url()`)
2. Fetch page via `scripts/fetch_page.py`
3. Parse HTML via `scripts/parse_html.py`
4. Optionally fetch CWV via `scripts/pagespeed_check.py` (use `--skip-cwv` to skip)
5. Hash HTML body and schema content (SHA-256)
6. Store snapshot in SQLite

**Execution:**
```bash
~/.claude/skills/seo/run-script drift_baseline.py <url>
~/.claude/skills/seo/run-script drift_baseline.py <url> --skip-cwv
```

**Output:** JSON with baseline ID, timestamp, URL, and summary of captured elements.

---

## Command: `compare`

Fetches the current page state and diffs it against the most recent baseline.

**Steps:**
1. Validate URL
2. Load most recent baseline from SQLite (or specific `--baseline-id`)
3. Fetch and parse current page state
4. Run all 17 comparison rules
5. Classify findings by severity
6. Store comparison result
7. Output JSON diff report

**Execution:**
```bash
~/.claude/skills/seo/run-script drift_compare.py <url>
~/.claude/skills/seo/run-script drift_compare.py <url> --baseline-id 5
~/.claude/skills/seo/run-script drift_compare.py <url> --skip-cwv
```

**Output:** JSON with all triggered rules, old/new values, severity, and actions.

After comparison, offer to generate an HTML report:
```bash
~/.claude/skills/seo/run-script drift_report.py <comparison_json_file> --output drift-report.html
```

---

## Command: `history`

Shows all baselines and comparisons for a URL.

**Execution:**
```bash
~/.claude/skills/seo/run-script drift_history.py <url>
~/.claude/skills/seo/run-script drift_history.py <url> --limit 10
```

**Output:** JSON array of baselines (newest first) with timestamps and comparison summaries.

---

## Cross-Skill Integration

When drift is detected, recommend the appropriate specialized skill:

| Finding | Recommendation |
|---------|----------------|
| Schema removed or modified | Run `/seo schema <url>` for full validation |
| CWV regression | Run `/seo technical <url>` for performance audit |
| Title or meta description changed | Run `/seo page <url>` for content analysis |
| Canonical changed or removed | Run `/seo technical <url>` for indexability check |
| Noindex added | Run `/seo technical <url>` for crawlability audit |
| H1/heading structure changed | Run `/seo content <url>` for E-E-A-T review |
| OG tags removed | Run `/seo page <url>` for social sharing analysis |
| Status code changed to error | Run `/seo technical <url>` for full diagnostics |

---

## Error Handling

| Scenario | Action |
|----------|--------|
| URL unreachable | Report error from `fetch_page.py`. Do not guess state. Suggest user verify URL. |
| No baseline exists for URL | Inform user and suggest running `baseline` first. |
| SSRF blocked (private IP) | Report `validate_url()` rejection. Never bypass. |
| SQLite database missing | Auto-create on first use. No error. |
| CWV fetch fails (no API key) | Store `null` for CWV fields. Skip CWV rules during comparison. |
| Page returns 4xx/5xx | Still capture as baseline (status code IS a tracked field). |
| Multiple baselines exist | Use most recent unless `--baseline-id` specified. |

---

## Security

- **All URL fetching** goes through `scripts/fetch_page.py` which enforces SSRF protection
  (blocks private IPs, loopback, reserved ranges, GCP metadata endpoints)
- **No curl, no subprocess HTTP calls** -- only the project's validated fetch pipeline
- **All SQLite queries** use parameterized placeholders (`?`), never string interpolation
- **TLS always verified** -- no `verify=False` anywhere in the pipeline

---

## Typical Workflows

### Pre/Post Deployment Check
```
/seo drift baseline https://example.com     # Before deploy
# ... deploy happens ...
/seo drift compare https://example.com      # After deploy
```

### Ongoing Monitoring
```
/seo drift baseline https://example.com     # Initial capture
# ... weeks later ...
/seo drift compare https://example.com      # Check for drift
/seo drift history https://example.com      # Review all changes
```

### Investigating a Traffic Drop
```
/seo drift compare https://example.com      # What changed?
/seo drift history https://example.com      # When did it change?
```
