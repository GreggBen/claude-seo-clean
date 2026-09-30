# Correlation engine — findings catalogue

Every finding below is derived from a **disagreement between views**, or is a
single-view baseline reported at low severity so it never crowds out a correlation.

Emitted by `scripts/fix_correlate.py`. Each carries `evidence` from the views involved,
a `source` location when one is credible, and a `state`:

- **`FIXABLE`** — responsible file and line known. A patch may be proposed.
- **`OBSERVED`** — defect real, origin unestablished. **No patch permitted.**

---

## The three views

| View | How it is captured | The reader it models |
| --- | --- | --- |
| `raw` | HTTP response body, zero JS executed | Retrieval crawlers, non-executing fetchers, `curl` |
| `rendered` | DOM after hydration (Playwright/Chromium) | A browser, and crawlers that render |
| `source` | Codebase walk: framework, routes, gates, emitters | The thing that produces the other two |

A view that is unavailable is recorded with its reason. **An absent view is a stated gap,
never a silent zero.**

---

## A. raw ↔ rendered

### `RENDER-ONLY-BODY` — critical
The raw view is a shell; the page's information arrives only after hydration.

**Rule:** `delta ≥ 30` **and** `raw < 120 words` **and** (`ratio ≥ 3.0` **or** `delta ≥ 100`).

Why a ratio and not a fixed threshold: an absolute word count misses a short page whose
raw view is empty, and fires on long pages where the delta is boilerplate. The ratio asks
the right question — *how much of this page depends on JavaScript?*

### `RENDER-ONLY-PARTIAL` — high
A meaningful block is JS-dependent, but the page is not a shell.
**Rule:** `delta ≥ 100`, or `ratio ≥ 1.5` with `delta ≥ 60`.

Below `delta = 30` nothing fires: that is the formatting-noise floor.

### `CANONICAL-DIVERGENCE` — high
`canonical` differs between raw and rendered. A search engine may honour either; the
choice stops being yours.

### `ROBOTS-DIVERGENCE` — critical
`meta robots` differs. A `noindex` present in raw HTML can be honoured even when
JavaScript removes it — a page that looks healthy in a browser can be deindexed.

### `TITLE-DIVERGENCE` — medium
The title differs between views.

### `RENDER-ONLY-JSONLD` — high
More JSON-LD blocks after hydration than before. Client-injected structured data may be
processed late or not at all.

### `RENDER-ONLY-LINKS` — high
Internal links materialise only after hydration.
**Rule:** `rendered_internal > 2 × raw_internal` **and** `delta ≥ 5`.
A crawl dead-end: destinations reachable only through these links may never be found.

### `H1-DIVERGENCE` — medium
`h1` count differs between views. The outline a machine builds depends on which view it
receives.

---

## B. markup ↔ visible text

Run against the **raw** view when available — that is the reader being protected. Falls
back to rendered.

### `MARKUP-WITHOUT-SUBSTANCE-FAQ` — critical
`FAQPage` / `Question` nodes declare answers absent from the page text.

Highest-signal case in the catalogue: it is simultaneously a divergence between two
projections of the same truth, and the shape search engines treat as markup not matching
visible content.

> **The repair is to show the answers.** Deleting the markup is forbidden — see
> `safety-contract.md` §2.

A closed `<details>` element **passes**: hidden by CSS is fine, absent from the document
is not.

### `MARKUP-WITHOUT-SUBSTANCE` — high
Other prose-bearing properties (`description`, `headline`, `articleBody`, `reviewBody`,
`text`) with no counterpart in visible text.

**Matching method.** Text is normalised — Unicode-folded, accent-stripped, lowercased,
punctuation removed, whitespace collapsed — then the first 60 characters of the claim are
sought in the page text. Prefix matching tolerates truncation and formatting without
demanding byte equality. Strings under 25 characters are skipped: too short to match
reliably, too noisy to report.

Only prose properties are checked. Identifiers, URLs, enums and dates are excluded —
they are not expected to appear as visible text, and checking them manufactures false
positives. `name` counts as prose only on `Question`, `FAQPage` and `HowToStep` nodes.

---

## C. source-derived

Available whenever a codebase is supplied — no URL required. Severity rises when a URL
confirms the symptom.

### `SOURCE-CONDITIONAL-GATE` — high (medium without a URL)
Components rendering content behind runtime state:
`isOpen`, `isExpanded`, `showMore`, `expanded`, `isVisible`, `activeTab`.

Reports `file:line` and the gate variable. **Judgement required:** gating *presentation*
is legitimate; gating *information* is the defect. The script cannot tell them apart —
you must read the component.

### `SOURCE-JS-ONLY-NAV` — high
`onClick` handlers calling `router.push` / `navigate` / `history.push` with no
accompanying `<a href>`. Invisible to any reader that does not execute JavaScript.

### `SOURCE-CLIENT-GATED-ROUTE` — medium
A route entrypoint is a client component, pushing its whole subtree past the server
boundary. Legitimate for genuinely interactive routes, costly for content routes.
Verify which this is.

---

## D. single-view baselines

Reported at low severity so they never crowd out correlations. The other skills in this
toolkit cover this ground more thoroughly.

| ID | Severity | Condition |
| --- | --- | --- |
| `NO-H1` | medium | no `h1` in the view |
| `MULTIPLE-H1` | low | more than one `h1` |
| `JSONLD-INVALID` | high | a JSON-LD block does not parse |
| `NO-META-DESCRIPTION` | low | no meta description |

---

## Extending the catalogue

A new finding earns its place only if it satisfies all four:

1. **It is a disagreement.** If one view answers it, an existing skill already owns it.
2. **It has a defensible rule.** Thresholds are named constants with a stated rationale,
   not magic numbers. Ratios beat absolutes wherever page size varies.
3. **It discriminates.** Before adding it, build one fixture that triggers it and one
   correct page that must stay clean. A detector that fires on correct code is worse than
   no detector — it trains the user to ignore output.
4. **Its fix is safe.** If the obvious repair is "remove the thing that disagrees", the
   finding needs an explicit correct-repair note, or it does not ship.
