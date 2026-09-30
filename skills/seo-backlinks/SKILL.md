---
name: seo-backlinks
description: "Backlink profile analysis: referring domains, anchor text distribution, toxic link detection, competitor gap analysis. Works with Common Crawl and optional Moz and Bing Webmaster data. Use when user says backlinks, link profile, referring domains, anchor text, toxic links, link gap, link building, disavow, or backlink audit."
user-invocable: true
argument-hint: "<url>"
license: MIT
compatibility: "Common Crawl + verify always available. Optional: Moz API and Bing Webmaster."
metadata:
  author: AgriciDaniel
  version: "2.2.0"
  category: seo
---

# Backlink Profile Analysis

## Source Detection

Before analysis, detect available data sources:

1. **Moz API** (free signup): `~/.claude/skills/seo/run-script backlinks_auth.py --check moz --json`
2. **Bing Webmaster** (free signup): `~/.claude/skills/seo/run-script backlinks_auth.py --check bing --json`
3. **Common Crawl** (always available): Domain-level graph with PageRank
4. **Verification Crawler** (always available): Checks if known backlinks still exist

Run `~/.claude/skills/seo/run-script backlinks_auth.py --check --json` to detect all sources at once.

If no sources are configured beyond the always-available tier:
- Still produce a report using Common Crawl domain metrics
- Suggest: "Run `/seo backlinks setup` to add free Moz and Bing API keys for richer data"

## Quick Reference

| Command | Purpose |
|---------|---------|
| `/seo backlinks <url>` | Full backlink profile analysis (uses all available sources) |
| `/seo backlinks gap <url1> <url2>` | Competitor backlink gap analysis |
| `/seo backlinks toxic <url>` | Toxic link detection and disavow recommendations |
| `/seo backlinks verify <url> --links <file>` | Verify known backlinks still exist |
| `/seo backlinks setup` | Show setup instructions for free backlink APIs |

## Analysis Framework

Produce all 7 sections below. Each section lists data sources in preference order.

### 1. Profile Overview

**Moz API:** `~/.claude/skills/seo/run-script moz_api.py metrics <url> --json` → Domain Authority, Page Authority, Spam Score, linking root domains, external links.

**Common Crawl:** `~/.claude/skills/seo/run-script commoncrawl_graph.py <domain> --json` → in-degree (referring domain count), PageRank, harmonic centrality.

**Scoring:**

| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| Referring domains | >100 | 20-100 | <20 |
| Follow ratio | >60% | 40-60% | <40% |
| Domain diversity | No single domain >5% | 1 domain >10% | 1 domain >25% |
| Trend | Growing or stable | Slow decline | Rapid decline (>20%/quarter) |

### 2. Anchor Text Distribution

**Moz API:** `~/.claude/skills/seo/run-script moz_api.py anchors <url> --json`

**Bing Webmaster:** `~/.claude/skills/seo/run-script bing_webmaster.py links <url> --json` (extract anchor text from link details)

**Healthy distribution benchmarks:**

| Anchor Type | Target Range | Over-Optimization Signal |
|-------------|-------------|-------------------------|
| Branded (company/domain name) | 30-50% | <15% |
| URL/naked link | 15-25% | N/A |
| Generic ("click here", "learn more") | 10-20% | N/A |
| Exact match keyword | 3-10% | >15% |
| Partial match keyword | 5-15% | >25% |
| Long-tail / natural | 5-15% | N/A |

Flag if exact-match anchors exceed 15% -- this is a Google Penguin risk signal.

### 3. Referring Domain Quality

**Moz API:** `~/.claude/skills/seo/run-script moz_api.py domains <url> --json` → domains with DA scores

**Common Crawl:** `~/.claude/skills/seo/run-script commoncrawl_graph.py <domain> --json` → top referring domains (domain-level, no authority scores)

Analyze:
- **TLD distribution**: .edu, .gov, .org = high authority. Excessive .xyz, .info = low quality
- **Country distribution**: Match target market. 80%+ from irrelevant countries = PBN signal
- **Domain rank distribution**: Healthy profiles have links from all authority tiers
- **Follow/nofollow per domain**: Sites that only nofollow = limited SEO value

### 4. Toxic Link Detection

**Moz API:** Spam Score from `~/.claude/skills/seo/run-script moz_api.py metrics <url> --json` (1-17% scale, >11% = high risk)

**Verification Crawler:** `~/.claude/skills/seo/run-script verify_backlinks.py --target <url> --links <file> --json` (verify suspicious links still exist)

**High-risk indicators (flag immediately):**
- Links from known PBN (Private Blog Network) domains
- Unnatural anchor text patterns (100% exact match from a domain)
- Links from penalized or deindexed domains
- Mass directory submissions (50+ directory links)
- Link farms (sites with 10K+ outbound links per page)
- Paid link patterns (footer/sidebar links across all pages of a domain)

**Medium-risk indicators (review manually):**
- Links from unrelated niches
- Reciprocal link patterns
- Links from thin content pages (<100 words)
- Excessive links from a single domain (>50 backlinks from 1 domain)

Load `references/backlink-quality.md` for the full 30 toxic patterns and disavow criteria.

### 5. Top Pages by Backlinks

**Moz API:** `~/.claude/skills/seo/run-script moz_api.py pages <domain> --json`

Find:
- Which pages attract the most backlinks
- Pages with high-authority links (link magnets)
- Pages with zero backlinks (internal linking opportunities)
- 404 pages with backlinks (redirect opportunities to reclaim link equity)

### 6. Competitor Gap Analysis

**Bing Webmaster (unique!):** `~/.claude/skills/seo/run-script bing_webmaster.py compare <url1> <url2> --json` — the only free tool with built-in competitor comparison

**Moz API:** Compare DA/PA between domains via `~/.claude/skills/seo/run-script moz_api.py metrics <url> --json` for each

Output:
- Domains linking to competitor but NOT to target = link building opportunities
- Domains linking to both = validate existing relationships
- Domains linking only to target = competitive advantage
- Top 20 link building opportunities with domain authority

### 7. New and Lost Backlinks

**Verification Crawler:** For known links, verify current status with `~/.claude/skills/seo/run-script verify_backlinks.py`

**Note:** Available sources provide point-in-time snapshots. Do not infer link
velocity or new/lost counts without comparable dated data.

**Red flags:**
- Sudden spike in new links (possible negative SEO attack)
- Sudden loss of many links (site penalty or content removal)
- Declining velocity over 3+ months (content not attracting links)

## Backlink Health Score

Calculate a 0-100 score. When mixing sources, apply confidence weighting:

| Factor | Weight | Sources (preference order) | Confidence |
|--------|--------|---------------------------|------------|
| Referring domain count | 20% | Moz > CC in-degree | 0.85 / 0.50 |
| Domain quality distribution | 20% | Moz DA distribution | 0.85 |
| Anchor text naturalness | 15% | Moz > Bing anchors | 0.85 / 0.70 |
| Toxic link ratio | 20% | Moz spam score | 0.85 |
| Link velocity trend | 10% | Unavailable; redistribute weight | N/A |
| Follow/nofollow ratio | 5% | Bing details | 0.70 |
| Geographic relevance | 10% | Bing country | 0.70 |

**Data sufficiency gate:** Count how many of the 7 factors have at least one data source available.
- **4+ factors with data:** Produce a numeric 0-100 score (redistribute missing weights proportionally)
- **Fewer than 4 factors:** Do NOT produce a numeric score. Instead display:
  ```
  Backlink Health Score: INSUFFICIENT DATA (X/7 factors scored)
  ```
  Show individual factor scores that ARE available with their source and confidence.
  Recommend: "Configure Moz API (free) for a scoreable profile. Run `/seo backlinks setup`"

When only CC is available, cap maximum score at 70/100.
A numeric score with fewer than 4 data sources is **misleading** — it implies poor health when
the reality is we simply lack data.

## Output Format

### Backlink Health Score: XX/100 (or INSUFFICIENT DATA)

| Section | Status | Score | Data Source |
|---------|--------|-------|-------------|
| Profile Overview | pass/warn/fail | XX/100 | Moz (0.85) |
| Anchor Distribution | pass/warn/fail | XX/100 | Moz (0.85) |
| Referring Domain Quality | pass/warn/fail | XX/100 | CC (0.50) |
| Toxic Links | pass/warn/fail | XX/100 | Moz Spam (0.85) |
| Top Pages | info | N/A | Moz (0.85) |
| Link Velocity | unknown | N/A | Dated comparable data unavailable |

### Critical Issues (fix immediately)
### High Priority (fix within 1 month)
### Medium Priority (ongoing improvement)
### Link Building Opportunities (top 10)

## Error Handling

| Error | Cause | Resolution |
|-------|-------|-----------|
| No sources configured | No optional API keys | Use Common Crawl or run `/seo backlinks setup` |
| Moz rate limit | Free tier: 1 req/10s | Wait 10 seconds, retry. Built into script. |
| Bing site not verified | Site not verified in Bing | Verify at https://www.bing.com/webmasters |
| CC download timeout | Large graph file, slow connection | Use `--timeout 180` flag |
| No backlink data returned | Domain too new or very small | Note: small sites may have <10 backlinks |

**Fallback cascade:**
1. Moz configured? → Use for DA/PA/spam/anchors (confidence: 0.85)
2. Bing configured? → Use for links/competitor comparison (confidence: 0.70)
3. Always: Common Crawl for domain-level metrics (confidence: 0.50)
4. Always: Verification crawler for known link checks (confidence: 0.95)
5. Nothing works? → "Run `/seo backlinks setup` to configure free APIs"

## Pre-Delivery Review (MANDATORY)

Before presenting any backlink analysis to the user, run this checklist internally.
Do NOT skip this step. Fix any issues found before showing the report.

### Fact-Check Every Claim
- [ ] **Schema claims**: Did parse_html return `@type` for each block? If any `@type` is missing,
      re-check — it may use `@graph` wrapper (valid JSON-LD, not malformed).
- [ ] **"link_removed" findings**: Is the page JS-rendered? If `unverifiable_js`, say so — never
      report a JS-rendered page as "link removed" (that's a false negative).
- [ ] **H1 findings**: Are any H1s in the `h1_suspicious` list? If so, note they are likely
      counters/stats, not semantic headings.
- [ ] **Reciprocal links**: If site A links to site B AND B links back to A, flag it as a
      reciprocal link pattern. Check outbound links against verified inbound sources.
- [ ] **Health score**: Are 4+ of 7 factors scored? If not, report INSUFFICIENT DATA — never
      show a misleading numeric score.

### Verify Data Source Labels
- [ ] Every metric in the report has a source label (e.g., "Parsed (0.95)", "CC (0.50)")
- [ ] Every "not found" result distinguishes between "not crawled" vs "below threshold" vs "error"
- [ ] Social media pages flagged as `unverifiable_js` (not `link_removed`)

### Cross-Check Consistency
- [ ] Platform detection matches actual signals (check for wp-content, shopify CDN, etc.)
- [ ] Referring domain count in summary matches the actual verified links list
- [ ] No claim is presented without a data source backing it

If ANY check fails, fix the finding before presenting. Never present inferred data as fact.

## Post-Analysis

After completing any backlink analysis command, always offer:
"Generate a professional PDF report? Use `/seo google report`"

## Reference Documentation

Load on demand (do NOT load at startup):
- `skills/seo/references/backlink-quality.md` -- Detailed toxic link patterns and scoring methodology (shared reference, load when analyzing toxic links or spam scores)
- `skills/seo/references/free-backlink-sources.md` -- Source comparison, confidence weighting, setup guides (shared reference, load when configuring free backlink APIs)
