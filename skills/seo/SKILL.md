---
name: seo
description: "Comprehensive SEO analysis for any website or business type. Full site audits, single-page analysis, technical SEO (crawlability, indexability, Core Web Vitals with INP), schema markup, content quality (E-E-A-T), image optimization, sitemap analysis, and GEO for AI Overviews/ChatGPT/Perplexity. Industry detection for SaaS, e-commerce, local, publishers, agencies. Triggers on: SEO, audit, schema, Core Web Vitals, sitemap, E-E-A-T, AI Overviews, GEO, technical SEO, content quality, page speed, structured data."
user-invocable: true
argument-hint: "[command] [url]"
license: MIT
metadata:
  author: AgriciDaniel
  version: "2.2.1"
  category: seo
---

# SEO: Universal SEO Analysis Skill

**Invocation:** `/seo $1 $2` where `$1` is the command and `$2` is the URL or argument.

**Scripts:** Run installed scripts from any working directory with
`~/.claude/skills/seo/run-script <script-name.py> [arguments...]`. The launcher
uses the Python environment installed under `~/.claude/skills/seo/.venv`.

Comprehensive SEO analysis across all industries (SaaS, local services,
e-commerce, publishers, agencies). Orchestrates 23 sub-skills and 16 sub-agents.
For source-level repairs that correlate raw HTML, rendered DOM and code, use the
separate `/seo-fix` skill.

## Quick Reference

| Command | What it does |
|---------|-------------|
| `/seo audit <url>` | Full website audit with parallel subagent delegation |
| `/seo page <url>` | Deep single-page analysis |
| `/seo sitemap <url or generate>` | Analyze or generate XML sitemaps |
| `/seo schema <url>` | Detect, validate, and generate Schema.org markup |
| `/seo images <url or optimize>` | Image SEO: on-page audit, SERP analysis, file optimization |
| `/seo technical <url>` | Technical SEO audit (9 categories) |
| `/seo content <url>` | E-E-A-T and content quality analysis |
| `/seo content-brief <topic or url>` | Generate detailed SEO content brief with target keywords, outline, internal links |
| `/seo geo <url>` | AI Overviews / Generative Engine Optimization |
| `/seo plan <business-type>` | Strategic SEO planning |
| `/seo programmatic [url\|plan]` | Programmatic SEO analysis and planning |
| `/seo competitor-pages [url\|generate]` | Competitor comparison page generation |
| `/seo local <url>` | Local SEO analysis (GBP, citations, reviews, map pack) |
| `/seo maps [command] [args]` | Public maps presence, NAP, and nearby businesses |
| `/seo hreflang [url]` | Hreflang/i18n SEO audit and generation |
| `/seo google [command] [url]` | Google SEO APIs (GSC, PageSpeed, CrUX, Indexing, GA4) |
| `/seo backlinks <url>` | Backlink profile analysis (Moz, Bing, Common Crawl) |
| `/seo cluster <seed-keyword>` | SERP-based semantic clustering and content architecture |
| `/seo sxo <url>` | Search Experience Optimization: page-type analysis, user stories, personas |
| `/seo drift baseline <url>` | Capture SEO baseline for change monitoring |
| `/seo drift compare <url>` | Compare current state to stored baseline |
| `/seo drift history <url>` | Show drift history over time |
| `/seo ecommerce <url>` | E-commerce SEO: product page and schema analysis |
| `/seo flow [stage] [url\|topic]` | FLOW framework: evidence-led prompts for Find, Leverage, Optimize, Win, or Local stages |

## Orchestration Logic

### Contrat de rapport du projet

Lire les instructions du projet avant de déléguer. Si elles interdisent les
scores agrégés, chaque spécialiste rend des constats individuels avec statut,
entrées, sources, date, preuve et limites ; le rapport omet les scores SEO,
E-E-A-T, GEO et visibilité, ainsi que leurs pondérations. Transmettre ce contrat
à chaque sous-agent. Une erreur ou une donnée absente porte un état explicite,
jamais un zéro. GSC, GA4, GBP et Bing restent des instruments distincts.
Les commandes de soumission Indexing/IndexNow requièrent une autorisation
nommée correspondant aux URL et à l'action, indépendamment des accès techniques.

Les poids ci-dessous s'appliquent uniquement lorsque le contrat du projet
autorise ces heuristiques ; ils ne constituent pas une mesure officielle.

When the user invokes `/seo audit`, delegate to subagents in parallel:
1. Detect business type (SaaS, local, ecommerce, publisher, agency, other)
2. Spawn subagents: seo-technical, seo-content, seo-schema, seo-sitemap, seo-performance, seo-visual, seo-geo
3. If Google API credentials detected (`~/.claude/skills/seo/run-script google_auth.py --check`), also spawn seo-google agent
4. If local business detected, also spawn seo-local agent
5. If local business detected, also spawn seo-maps agent for free map and listing checks
6. If backlink APIs detected (`~/.claude/skills/seo/run-script backlinks_auth.py --check`), also spawn seo-backlinks agent
7. Discover site URLs through the sitemap and internal links, respecting robots.txt
8. If content strategy signals detected (blog, pillar pages, topic clusters), also spawn seo-cluster agent
9. If e-commerce detected, also spawn seo-ecommerce agent
10. If drift baseline exists for this URL (`~/.claude/skills/seo/run-script drift_history.py <url>`), also spawn seo-drift agent
11. Always include seo-sxo in full audits (search experience applies to all sites)
12. Collect results and generate unified report with SEO Health Score (0-100)
13. **Synthesize via the 10-principle framework** (see "Synthesis Methodology" below) — walk PERCEIVE → ANALYZE → VALIDATE → ACT before bucketing findings into Critical / High / Medium / Low
14. Create prioritized action plan with dependency sequencing + falsifiability per recommendation
15. **Offer PDF report**: "Generate a professional PDF report? Use `/seo google report full`"

For individual commands, load the relevant sub-skill directly.
After any analysis command completes, offer to generate a PDF report via
`~/.claude/skills/seo/run-script google_report.py`.

## Synthesis Methodology

Audits are not just findings — they are findings synthesized into a coherent
strategy. claude-seo uses a 10-principle thinking framework grouped into four
phases: **PERCEIVE** (observe-external · observe-internal · listen),
**ANALYZE** (think · connect-lateral · connect-system), **VALIDATE** (feel ·
accept), **ACT** (create · grow).

Full audits (`/seo audit`, `/seo page`) walk every phase before emitting the
action plan. Narrower commands (`/seo schema`, `/seo images`, etc.) pass at
least THINK + ACCEPT before emitting (sound first principle, surfaced
falsifiability). The Critical / High / Medium / Low priority buckets are the
**output** of validation, not a substitute for it.

Full methodology + per-principle SEO mapping: `references/thinking-framework.md`.

Each emitted recommendation should carry:
- The first-principle observation it rests on (THINK)
- The dependency on / unblock relationship to other recommendations (CONNECT-system)
- An explicit "how would we know this failed?" check (ACCEPT)
- A leading indicator the user can monitor without re-running the audit (GROW)

## Industry Detection

Detect business type from homepage signals:
- **SaaS**: pricing page, /features, /integrations, /docs, "free trial", "sign up"
- **Local Service**: phone number, address, service area, "serving [city]", Google Maps embed --> auto-suggest `/seo local` for deeper analysis
- **E-commerce**: /products, /collections, /cart, "add to cart", product schema
- **Publisher**: /blog, /articles, /topics, article schema, author pages, publication dates
- **Agency**: /case-studies, /portfolio, /industries, "our work", client logos

## Quality Gates

Read `references/quality-gates.md` for thin content thresholds per page type.
Hard rules:
- WARNING at 30+ location pages (enforce 60%+ unique content)
- HARD STOP at 50+ location pages (require user justification)
- Never recommend HowTo schema (deprecated Sept 2023)
- FAQ schema: Google retired FAQ rich results for ALL sites on May 7, 2026 (no SERP feature anymore; supersedes the Aug 2023 gov/health restriction). Flag existing FAQPage at Info (not Critical) for its AI/LLM citation benefit; do not recommend removal; do not recommend new FAQPage for Google SERP benefit; use QAPage for genuine user Q&A
- All Core Web Vitals references use INP, never FID

## Reference Files

Load these on-demand as needed (do NOT load all at startup):
- `references/cwv-thresholds.md`: Current Core Web Vitals thresholds and measurement details
- `references/schema-types.md`: All supported schema types with deprecation status
- `references/eeat-framework.md`: E-E-A-T evaluation criteria (Sept 2025 QRG update)
- `references/quality-gates.md`: Content length minimums, uniqueness thresholds
- `references/local-seo-signals.md`: Local ranking factors, review benchmarks, citation tiers, GBP status
- `references/local-schema-types.md`: LocalBusiness subtypes, industry-specific schema and citation sources

Maps-specific references (loaded by seo-maps skill, not at startup):
- `references/maps-gbp-checklist.md`, `references/maps-free-apis.md`

## Scoring Methodology

### SEO Health Score (0-100)
Weighted aggregate of all categories:

Treat this score as a bounded heuristic over observed checks, never a measure
of actual E-E-A-T or AI citations. For each observation, record source and
date. Report publication, discoverability, indexation, citation, and visits
separately; mark a stage unknown when it has no direct instrument. A sitemap
or `llms.txt` proves neither indexation nor citation.

| Category | Weight |
|----------|--------|
| Technical SEO | 22% |
| Content Quality | 23% |
| On-Page SEO | 20% |
| Schema / Structured Data | 10% |
| Performance (CWV) | 10% |
| AI Search Readiness | 10% |
| Images | 5% |

### Priority Levels
- **Critical**: Blocks indexing or causes penalties (immediate fix required)
- **High**: Significantly impacts rankings (fix within 1 week)
- **Medium**: Optimization opportunity (fix within 1 month)
- **Low**: Nice to have (backlog)

## Sub-Skills

This skill orchestrates 22 sub-skills. The orchestrator itself (`seo`) is the 23rd in `skills/`, but does not
orchestrate itself, so it is not enumerated below.

1. **seo-audit** -- Full website audit with parallel delegation
2. **seo-page** -- Deep single-page analysis
3. **seo-technical** -- Technical SEO (9 categories)
4. **seo-content** -- E-E-A-T and content quality
5. **seo-content-brief** -- Detailed SEO content brief generation (contributed by puneetindersingh)
6. **seo-schema** -- Schema markup detection and generation
7. **seo-images** -- Image optimization, SERP analysis, file optimization
8. **seo-sitemap** -- Sitemap analysis and generation
9. **seo-geo** -- AI Overviews / GEO optimization
10. **seo-plan** -- Strategic planning with templates
11. **seo-programmatic** -- Programmatic SEO analysis and planning
12. **seo-competitor-pages** -- Competitor comparison page generation
13. **seo-hreflang** -- Hreflang/i18n SEO audit, cultural profiles, content parity
14. **seo-local** -- Local SEO (GBP, NAP, citations, reviews, local schema, multi-location)
15. **seo-maps** -- Public maps presence, NAP, and nearby POI analysis
16. **seo-google** -- Google SEO APIs (GSC, PageSpeed, CrUX, Indexing API, GA4)
17. **seo-backlinks** -- Backlink profile analysis (Moz, Bing, Common Crawl)
18. **seo-cluster** -- SERP-based semantic clustering (contributed by Lutfiya Miller)
19. **seo-sxo** -- Search Experience Optimization (contributed by Florian Schmitz)
20. **seo-drift** -- SEO drift monitoring (contributed by Dan Colta)
21. **seo-ecommerce** -- E-commerce SEO intelligence (contributed by Matej Marjanovic)
22. **seo-flow** -- FLOW framework integration (Find -> Leverage -> Optimize -> Win, 41 AI prompts, CC BY 4.0)

## Subagents

For parallel analysis during audits:
- `seo-technical` -- Crawlability, indexability, security, CWV
- `seo-content` -- E-E-A-T, readability, thin content
- `seo-schema` -- Detection, validation, generation
- `seo-sitemap` -- Structure, coverage, quality gates
- `seo-performance` -- Core Web Vitals measurement
- `seo-visual` -- Screenshots, mobile testing, above-fold
- `seo-geo` -- AI crawler access, llms.txt, citability, brand mention signals
- `seo-local` -- GBP signals, NAP consistency, reviews, local schema, industry-specific local factors (conditional: spawned when Local Service detected)
- `seo-maps` -- Free listing, NAP, and competitor checks (conditional: spawned when Local Service detected)
- `seo-google` -- CWV field data, URL indexation status, organic traffic trends (conditional: spawned when Google API credentials detected)
- `seo-backlinks` -- Backlink profile data: DA/PA, referring domains, anchor text, toxic links (conditional: spawned when Moz/Bing API keys detected or always for CC domain-level metrics)
- `seo-cluster` -- Semantic clustering analysis (conditional: content strategy detected)
- `seo-sxo` -- Page-type mismatch, user stories, persona scoring (always in full audits)
- `seo-drift` -- Baseline comparison (conditional: drift baseline exists for URL)
- `seo-ecommerce` -- Product page and schema analysis (conditional: e-commerce detected)
- `seo-flow` -- FLOW framework prompts (conditional: spawned for content strategy workflows)

## Error Handling

| Scenario | Action |
|----------|--------|
| Unrecognized command | List available commands from the Quick Reference table. Suggest the closest matching command. |
| URL unreachable | Report the error and suggest the user verify the URL. Do not attempt to guess site content. |
| Sub-skill fails during audit | Report partial results from successful sub-skills. Clearly note which sub-skill failed and why. Suggest re-running the failed sub-skill individually. |
| Ambiguous business type detection | Present the top two detected types with supporting signals. Ask the user to confirm before proceeding with industry-specific recommendations. |
