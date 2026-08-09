# Fix catalogue

Concrete repairs per finding. Every recipe assumes `safety-contract.md` is in force:
diff before write, idempotent, one class per commit, never invent a fact, never amputate
the truthful side of a divergence.

---

## `MARKUP-WITHOUT-SUBSTANCE-FAQ`

**Defect.** JSON-LD declares answers the page does not show.

**Correct repair: render the answers.** The accordion pattern below is wrong not because
it collapses content, but because it *withholds* it until a click.

```tsx
// ✗ The answer does not exist until state flips.
{isOpen && <p>{answer}</p>}
```

Two correct patterns:

```tsx
// ✓ A. Native <details> — closed by default, always in the document.
<details>
  <summary>{question}</summary>
  <p>{answer}</p>
</details>
```

```tsx
// ✓ B. Keep the custom UI, always render, hide with CSS.
<div id={panelId} role="region" hidden={!isOpen}>
  <p>{answer}</p>
</div>
```

Pattern B keeps ARIA wiring (`aria-expanded`, `aria-controls`) and animation. The `hidden`
attribute and `display:none` both keep the text in the DOM and in the raw HTML — which is
what the finding is about. What matters is that the node is *rendered*, not that it is
*visible*.

Radix / Headless UI: pass `forceMount` on the content primitive and control visibility
with `data-state` styling, rather than letting the primitive unmount closed panels.

**Never** delete the `FAQPage` markup to make the two views agree.

**Verify.** Every `acceptedAnswer.text` must appear in the raw view's text.

---

## `RENDER-ONLY-BODY` / `RENDER-ONLY-PARTIAL`

**Defect.** The page's information exists only after hydration.

| Framework | Repair |
| --- | --- |
| Next.js App Router | Keep `page.tsx` a server component. Fetch on the server; push `'use client'` down to the smallest interactive leaf. |
| Next.js Pages Router | `getStaticProps` / `getServerSideProps` instead of `useEffect` fetching. |
| Nuxt | `useAsyncData` / `useFetch` at setup, not `onMounted`. |
| SvelteKit | `+page.server.ts` `load`, not `onMount`. |
| Astro | Content in the `.astro` component; `client:*` directives only on islands that need them. |
| Remix | Route `loader`. |
| React/Vue SPA | Add prerendering or SSR. Without it the raw view cannot carry content — say so plainly rather than patching around it. |

The common anti-pattern, all frameworks:

```tsx
// ✗ Content arrives on the client, after the crawler has left.
const [data, setData] = useState(null)
useEffect(() => { fetch('/api/x').then(r => r.json()).then(setData) }, [])
if (!data) return <Skeleton />
```

**Verify.** `raw_word_count` rises; `ratio` approaches 1.

---

## `RENDER-ONLY-JSONLD`

**Defect.** Structured data injected client-side.

```tsx
// ✓ Server component — the script is in the initial response.
export default async function Page() {
  const data = await getData()
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(buildJsonLd(data)) }}
      />
      <Article data={data} />
    </>
  )
}
```

Build the object from the **same source** that renders the visible content. Two
independent builders drift, and drift is what produced `MARKUP-WITHOUT-SUBSTANCE`.

**Verify.** `raw_jsonld_count == rendered_jsonld_count`.

---

## `RENDER-ONLY-LINKS` / `SOURCE-JS-ONLY-NAV`

**Defect.** Navigation a non-executing reader cannot follow.

```tsx
// ✗ No href — nothing to crawl.
<div onClick={() => router.push(`/produits/${slug}`)}>{title}</div>

// ✓ A real anchor. Framework Link components render one.
<Link href={`/produits/${slug}`}>{title}</Link>
```

Where a click handler must stay (analytics, interception), keep it *on* the anchor rather
than replacing it.

**Verify.** Internal link counts converge between raw and rendered.

---

## `ROBOTS-DIVERGENCE` — treat as urgent

**Defect.** A `noindex` in raw HTML that JavaScript later removes. The page looks healthy
in a browser and can be dropped from the index.

Find what emits the raw-side directive: middleware, a server-side header (`X-Robots-Tag`),
a default in a layout, an environment-conditional meta tag. Staging guards leaking into
production are the usual cause.

**Verify.** Raw and rendered report the same `meta_robots`; check `X-Robots-Tag` too — a
header cannot be undone by client code.

---

## `CANONICAL-DIVERGENCE`

Emit one canonical server-side and stop mutating it client-side.

```tsx
// Next.js App Router
export const metadata = { alternates: { canonical: 'https://example.com/page' } }
```

Never resolve this by deleting the canonical.

---

## `H1-DIVERGENCE` / `MULTIPLE-H1` / `NO-H1`

Usually a shared layout emitting an `h1` that page components also emit. Fix the layout,
not the pages — the finding will otherwise reappear on every new route.

**Verify.** Both views report exactly one `h1`.

---

## `SOURCE-CONDITIONAL-GATE`

**Read the component before touching it.** The rule to apply:

| Gated thing | Verdict |
| --- | --- |
| An FAQ answer, spec table, description, price, availability | **Information** — must render |
| A tooltip, modal, dropdown menu, tab *chrome*, loading state | **Presentation** — gating is fine |
| Tab *content* carrying distinct information | Render all panels; hide inactive with CSS |

Lazy-loading is for images, video, maps, embeds and animation — **never for the
information itself**.

---

## `SOURCE-CLIENT-GATED-ROUTE`

Move `'use client'` from the route entrypoint down to the interactive leaf.

```tsx
// ✓ page.tsx stays a server component
import { InteractiveFilter } from './interactive-filter'   // 'use client' lives there
export default async function Page() {
  const items = await getItems()
  return <><ItemList items={items} /><InteractiveFilter /></>
}
```

`ItemList` renders server-side, so the content is in the raw HTML while the filter stays
interactive.

---

## `JSONLD-INVALID`

Fix the syntax **at the emitter**, not in the output. The usual causes: unescaped quotes
in interpolated strings, trailing commas, and `undefined` reaching `JSON.stringify`.

Prefer `JSON.stringify(object)` over hand-assembled template literals — it escapes
correctly by construction.

---

## `NO-META-DESCRIPTION`

Write one only where a truthful source exists — an existing summary, excerpt or intro
paragraph. Do not invent a description for a page you have not read. When no source
exists, report the finding and leave it.

---

## After any fix

1. Re-run `fix_verify.py`.
2. Read the **regressions** section before the closed section.
3. Commit one class of fix, with the verifier's verdict in the message.
4. If a finding persists after two attempts, stop and report — the model of the problem
   is wrong.
