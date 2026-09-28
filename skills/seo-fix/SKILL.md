---
name: seo-fix
description: >
  Scan a site for machine-readability gaps and close them at the source. Correlates
  three views -- raw HTML with no JavaScript, the hydrated DOM, and the codebase that
  produces both -- to find defects no single view can see, traces each one to the file
  and line responsible, applies guarded fixes, and re-measures to prove the gap closed.
  Works on a local codebase, a git repository, a live URL, or all three together. Use
  when the user says "fix my SEO", "corriger le SEO", "find the gaps", "why don't AI
  crawlers see my content", "audit and fix", "scan my repo", "close the SEO issues",
  or asks why a page looks fine in a browser but not to a crawler.
user-invocable: true
argument-hint: "[url and/or path] [--scan|--fix|--verify]"
license: MIT
metadata:
  author: AgriciDaniel
  version: "1.0.1"
  category: seo
---

# SEO Fix: Correlate, Trace, Repair, Prove

**Invocation:** `/seo-fix $1` where `$1` is any mix of a URL, a local path, and a git
remote. Modes are inferred; nothing needs to be declared.

**Scripts:** at the plugin root `scripts/` — `fix_observe.py`, `fix_correlate.py`,
`fix_verify.py`.

---

## What makes this skill different from the other 23

Every other skill in this toolkit answers *what does this page look like?* with **one**
view. Before v2.0.0 that view was raw HTML, which produced false negatives on SPAs.
v2.0.0 moved every subagent onto the headless renderer, which fixed those false
negatives — and lost the raw view in the process.

Both views are true. A renderer sees what a **browser** sees. It no longer sees what a
**retrieval crawler** sees when it does not execute JavaScript. The defects that matter
most live in the *disagreement* between them, and in the disagreement between either one
and the source that emits them.

This skill is the only one that holds all three at once, and the only one that **changes
files**. It ends with a re-measurement, not a report.

| Question | Answerable from one view? |
| --- | --- |
| Does this page have an `h1`? | Yes — any existing skill does this |
| Does content exist before JavaScript runs? | **No** — needs raw *vs* rendered |
| Does the markup promise text the page never shows? | **No** — needs markup *vs* visible text |
| Which component is responsible? | **No** — needs the codebase |
| Did the fix actually work? | **No** — needs a second observation |

---

## The loop

```
DETECT → OBSERVE → CORRELATE → RANK → PATCH → VERIFY ─┐
   ↑                                                   │
   └──────────────── while regressions or unclosed ────┘
```

Never skip VERIFY. A fix that has been applied but not re-measured is a claim, not a
result. This skill is not permitted to make claims.

---

## Step 1 — DETECT

Work out what you have been pointed at. Do not ask the user for what you can determine.

| Input | Mode | Views available |
| --- | --- | --- |
| Only a path, or cwd is a repo | `codebase` | source |
| Only a URL | `browser` | raw + rendered |
| A git remote | `repo` | source (after a shallow clone to a temp dir) |
| A path **and** a URL | `correlated` | all three — **the only mode that yields `file:line`** |

Always push toward `correlated`. If the user gives you only a URL, check whether the cwd
is a repository for that site and say so. If they give you only a path, look for the
deployed URL in `README`, `package.json` `homepage`, `.env*`, CI config, or a sitemap —
propose it, do not assume it.

Detect the framework before reading anything else; it decides where routes, metadata and
markup live. `fix_observe.py` reports this as `views.source.framework`. See
`references/framework-adapters.md`.

---

## Step 2 — OBSERVE

```bash
python3 scripts/fix_observe.py \
  --url https://example.com \
  --codebase ~/dev/site \
  --out .seo-fix/snapshot.json --summary
```

Options that matter: `--no-render` (skip Playwright), `--timeout`, `--user-agent`.

**Dependencies degrade explicitly, and that is a feature.** Raw view works on stdlib
alone. `requests` + `beautifulsoup4` improve it. `playwright` unlocks the rendered view.
When a view is unavailable the snapshot records *why*. Never treat an absent view as a
clean result — `fix_correlate.py` prints a bounded-result banner for exactly this reason,
and you must carry that caveat into whatever you tell the user.

If the rendered view is missing and the site is a SPA, say so plainly: the most important
correlation is unavailable and the run is partial. Offer:
`pip install playwright && playwright install chromium`.

### Multi-page runs

`fix_observe.py` observes one URL. For a site sweep, take the route list from the source
view (`views.source.routes`) or a sitemap, snapshot each route into
`.seo-fix/<slug>.json`, and correlate each. Prefer routes that carry information —
content, offers, FAQ, service and location pages — over dashboards and authenticated
areas. Cap the sweep and **say what you capped**: a silent limit reads as full coverage.

---

## Step 3 — CORRELATE

```bash
python3 scripts/fix_correlate.py .seo-fix/snapshot.json \
  --out .seo-fix/findings.json --format markdown
```

Findings carry `id`, `severity`, `evidence` from every view involved, a `source` location
when one is credible, a `fix` strategy, and a `verify` procedure.

**`state` is the field that governs what you may do next:**

- `FIXABLE` — the responsible file and line are known. You may propose a patch.
- `OBSERVED` — the defect is real but its origin is not established. You may **not**
  patch it. Investigate to promote it to `FIXABLE`, or report it as observed.

Guessing which file causes a symptom is how automated tools corrupt codebases. The
`OBSERVED` state exists to make that guess impossible rather than merely discouraged.

Full catalogue and detection rules: `references/correlation-engine.md`.

Les textes déclarés en JSON-LD peuvent contenir du HTML, notamment `Answer.text`.
Le corrélateur compare leur projection textuelle (balises retirées, entités
décodées, limites de blocs conservées) au texte observé. Une réponse réellement
absente reste signalée. Après un changement du détecteur, reprendre la baseline :
la disparition d'un faux positif ne constitue pas une réparation du site.

---

## Step 4 — RANK

Order by **impact × confidence**, not by severity alone.

1. `critical` + `FIXABLE` — do first
2. `critical` + `OBSERVED` — investigate to locate the source
3. `high` + `FIXABLE`
4. everything else

Then apply judgement the scripts cannot: a `RENDER-ONLY-BODY` on a marketing landing page
outranks the same finding on an internal admin route. Ask what the page is *for* before
ranking it. If the user has told you what matters, that overrides the default order.

---

## Step 5 — PATCH

**Read `references/safety-contract.md` before your first edit. It is not optional.**

The five rules that govern every change:

1. **Diff first.** Show the proposed change and its rationale before applying it. On
   anything structural — a route, a layout, a shared component — get explicit agreement.
2. **Never patch markup to hide a divergence.** When JSON-LD promises text the page does
   not show, the repair is to *show the content*. Deleting the markup makes the two views
   agree on less and destroys a truthful declaration. This inversion is forbidden.
3. **One class of fix per commit.** A commit that mixes heading structure with JSON-LD
   emission cannot be reverted cleanly.
4. **Idempotent.** Running the fix twice changes nothing the second time. Check whether
   your change is already present before writing.
5. **Never generate a self-serving claim.** No `aggregateRating` the site awards itself,
   no invented review counts, no fabricated credentials, no keyword-stuffed alt text. A
   markup generator that invents facts is worse than missing markup.

Fix recipes per framework and per finding: `references/fix-catalog.md`.

---

## Step 6 — VERIFY

```bash
python3 scripts/fix_verify.py \
  --before .seo-fix/findings.json \
  --url https://example.com --codebase ~/dev/site \
  --out .seo-fix/verification.json
```

Re-observes, re-correlates, and classifies every finding as **CLOSED**, **PERSISTENT**,
or **REGRESSION**. Exit code is non-zero when a regression appears, so the loop stops
instead of grinding.

Two properties to respect:

- **A regression is a stop condition.** A repair that trades one defect for another has
  not improved anything. Revert or repair before continuing.
- **The soundness check overrides the counts.** If a view that existed before is missing
  now, findings can appear closed simply because nothing looked for them. The verifier
  says so. When it does, the numbers are not usable — re-run with the view restored.

For a codebase-only run, verify after rebuilding or restarting the dev server, otherwise
you are re-reading the same stale output.

---

## Reporting to the user

State three things, in this order:

1. **What was measured** — which views, which routes, and what was capped.
2. **What was found and fixed** — findings closed, with evidence from the verification.
3. **What was not measured** — the bounded-result banner, verbatim in substance.

Never present a partial run as a clean site. "No findings in the views I could capture"
is honest; "your site is clean" is not, when the rendered view failed to load.

### On scoring

This skill deliberately emits **no overall score**. The other skills in this toolkit
produce a 0–100 SEO Health Score, which is useful for tracking movement over time. A
number here would invite the reading that the site is *N%* machine-readable, which is a
claim about all machine readers — something no local instrument can support. Report
findings, severities and closures. If the user wants a score, run `/seo audit` and say
where the number comes from.

---

## Boundaries — what this skill does not do

- It does not measure whether any AI system reads, cites or recommends the site. It
  measures whether the information is **available** to a reader that does not execute
  JavaScript. Availability is a precondition, never a promise of consumption.
- It does not rank pages, predict traffic, or estimate positions.
- It does not touch content strategy, keywords or backlinks — `/seo content`,
  `/seo cluster` and `/seo backlinks` own those.
- It does not fix what it cannot trace. `OBSERVED` findings are reported, never patched.

---

## Related skills

| Need | Skill |
| --- | --- |
| Full URL-based audit with a score | `/seo audit` |
| Rendering, crawlability, headers | `/seo technical` |
| Structured data validation | `/seo schema` |
| AI Overview citability | `/seo geo` |
| Regression tracking over time | `/seo drift` |

`seo-fix` is the only one that reads the codebase and the only one that writes to it.
