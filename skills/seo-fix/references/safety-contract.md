# Safety contract

Binding rules for any change `seo-fix` makes. A skill that edits source code has a
failure mode no read-only auditor has: it can make things worse, silently, at scale.
These rules exist to make that outcome structurally difficult rather than merely
unlikely.

---

## 1. Never assert without measuring

A fix that has been *applied* is not a fix that *worked*. The only evidence a gap closed
is a fresh observation in which it is absent.

- Never write "fixed" in a report before `fix_verify.py` has run.
- Never say "should now be visible to crawlers" — say what the verifier returned.
- When the verifier reports the comparison is **not sound** (a view present before is
  missing now), the counts are unusable. Restore the view and re-run. Do not report the
  numbers with a caveat; do not report them at all.

The failure this prevents: a loop that reports progress it never achieved, on a codebase
that is quietly getting worse.

---

## 2. Never patch markup to hide a divergence

When structured data promises text the page does not show, there are two ways to make the
two agree.

| Repair | Effect |
| --- | --- |
| **Show the content** | Both projections now carry the truth. Correct. |
| **Delete the markup** | Both projections now carry less. **Forbidden.** |

The second is faster, passes the same check, and destroys a truthful declaration to
silence a detector. It is the single most tempting wrong move available to an automated
fixer, which is why it is named and banned rather than left to judgement.

The same inversion in other guises, equally forbidden:

- Removing an `h1` because two exist, when the real defect is a layout emitting a second.
- Deleting a `hreflang` cluster because one entry 404s.
- Dropping a `canonical` because raw and rendered disagree, instead of emitting one
  server-side.

**Rule:** when two surfaces disagree, first establish which one is right. Never resolve a
divergence by amputating the more truthful side.

---

## 3. Never invent a fact

A markup generator that fabricates is worse than no markup, because it launders invention
into a machine-readable assertion.

Never generate:

- `aggregateRating` or `review` the site awards itself
- review counts, star ratings, or testimonials not present in the source data
- `priceRange`, `openingHours`, `areaServed` not stated by the site or its owner
- credentials, certifications, awards, or `knowsAbout` claims
- alt text describing an image you have not seen, or stuffed with keywords
- `datePublished` / `dateModified` inferred from a git timestamp and presented as
  editorial fact

When a required property has no truthful source, **leave it out and say why**. Incomplete
markup is a bounded statement. Invented markup is a lie with a schema attached.

---

## 4. Diff before write

- Show the proposed change and the finding it closes, before applying.
- For anything structural — a route file, a layout, a shared component, a metadata
  helper, a build config — get explicit agreement first. Blast radius, not file size,
  decides what counts as structural.
- Never edit generated output: `.next/`, `dist/`, `build/`, `out/`, `.svelte-kit/`,
  `.nuxt/`. Fix the source that produces it. A patched artifact is erased by the next
  build and hides the real defect in the meantime.
- Never edit a file with uncommitted changes you did not make. Stop and say so — you
  cannot tell whether you are about to overwrite someone's work in progress.

---

## 5. One class of fix per commit

A commit mixing heading structure with JSON-LD emission cannot be reverted cleanly. Group
by finding class, not by file.

Suggested message shape:

```
seo-fix: <FINDING-ID> — <what changed>

<Which finding, which routes, which files.>
Verified: <closed|persistent> per fix_verify.py.
```

Never claim `Verified: closed` without the verifier output to back it.

---

## 6. Idempotence

Running the same fix twice must change nothing the second time. Before writing, check
whether the change is already present. Fixers that append rather than reconcile produce
duplicate JSON-LD blocks, stacked meta tags and repeated imports — each of which is a new
defect.

---

## 7. Stop conditions

Stop the loop and hand back to the user when:

- **A regression appears.** Trading one defect for another is not progress.
- **The same finding persists after two fix attempts.** The model of the problem is
  wrong. Report what was tried and what the evidence shows.
- **A fix would require a design decision** — changing a rendering strategy, adding a
  dependency, restructuring routes, altering what the site claims about itself. Propose;
  do not decide.
- **The codebase has unrelated uncommitted changes.** Another session may be working.
- **A finding is `OBSERVED`, not `FIXABLE`.** Investigate or report. Never guess the
  source.

---

## 8. Scope discipline

This skill fixes machine-readability defects it can trace and verify. It does not:

- refactor for style, rename things, or reorganise files
- upgrade dependencies or change build configuration
- rewrite editorial content or alter what the site says about itself
- touch authentication, payment, or data-handling code

If a genuine defect sits outside that scope, report it with evidence and leave it.
Scaling the work down is the user's call; scaling it *up* uninvited is not yours.

---

## 9. What to do with what you cannot fix

Every run ends with three lists, and the third is not optional:

1. **Closed** — verified, with evidence.
2. **Persistent** — attempted, still present, with what was tried.
3. **Not attempted** — `OBSERVED` findings, out-of-scope findings, views that could not
   be captured, and anything the sweep capped.

A silent cap reads as full coverage. Say what you did not look at.
