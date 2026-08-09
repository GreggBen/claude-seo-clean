# Framework adapters

Where routes, metadata and markup live, per framework. `fix_observe.py` detects the
framework from `package.json` and directory layout, and reports it as
`views.source.framework` / `views.source.router`.

Detection is a **starting hypothesis**, not a verdict. Confirm against the actual tree
before relying on it — monorepos, custom servers and hybrid setups defeat any signature.

---

## Detection signals

| Framework | Signal | Router |
| --- | --- | --- |
| `nextjs` | `next` in dependencies | `app/` → App Router · `pages/` → Pages Router |
| `nuxt` | `nuxt` / `nuxt3` | file-based |
| `sveltekit` | `@sveltejs/kit` | `src/routes` |
| `astro` | `astro` | `src/pages` |
| `remix` | `remix` / `@remix-run/react` | `app/routes` |
| `gatsby` | `gatsby` | `src/pages` + createPages |
| `react-spa` / `vue-spa` | `react` / `vue`, no meta-framework | client-side |
| `wordpress` | `wp-config.php` | themes |
| `hugo` | `config.toml` / `hugo.toml` | content/ |
| `jekyll` | `_layouts/` | `_posts` |

A `*-spa` result is itself a finding: without prerendering or SSR, the raw view *cannot*
carry content. Say so rather than patching around it.

---

## Route mapping

Implemented in `_route_from_path()`:

| Framework | File | Route |
| --- | --- | --- |
| Next App | `app/faq/page.tsx` | `/faq` |
| Next App | `app/(marketing)/pricing/page.tsx` | `/pricing` — group segments dropped |
| Next App | `app/page.tsx` | `/` |
| Next Pages | `pages/about.tsx` | `/about` |
| Next Pages | `pages/blog/index.tsx` | `/blog` |
| Astro | `src/pages/contact.astro` | `/contact` |
| SvelteKit | `src/routes/faq/+page.svelte` | `/faq` |

`src/` prefixes are handled. API routes and `_`-prefixed files are excluded.

**Dynamic segments** (`[slug]`, `[...rest]`) map to a literal path containing the
brackets — they cannot be resolved without data. Treat them as *templates*: pick real
URLs from the sitemap or the live site to observe, and remember that a defect in a
dynamic route affects every instance of it. Fixing one template can close hundreds of
pages at once, which also means breaking one breaks hundreds.

---

## Where metadata lives

| Framework | Title / description | Canonical | JSON-LD |
| --- | --- | --- | --- |
| Next App | `export const metadata` or `generateMetadata` | `metadata.alternates.canonical` | `<script type="application/ld+json">` in a server component |
| Next Pages | `next/head` | `<link rel="canonical">` in Head | same, in the page |
| Nuxt | `useHead` / `definePageMeta` | `useHead({link:[…]})` | `useHead({script:[…]})` |
| SvelteKit | `<svelte:head>` | in `<svelte:head>` | `+page.server.ts` → template |
| Astro | frontmatter + `<head>` | `<link>` in layout | `<script>` in the `.astro` file |
| Remix | `meta` export | `links` export | in the route component |

---

## Rendering-strategy hazards

**Next.js App Router.** `'use client'` at a route entrypoint pushes the whole subtree past
the server boundary — the most common cause of `RENDER-ONLY-BODY`. Also: `dynamic(...,
{ ssr: false })` removes a component from the raw HTML entirely, which is correct for a
map or a chart and wrong for content.

**Streaming and Suspense.** Content inside `<Suspense>` may arrive in a later chunk. A
non-executing fetcher that reads only the first flush can miss it. If the raw view looks
thin on a streamed route, check what sits behind a Suspense boundary before assuming a
client-fetch bug.

**Nuxt / SvelteKit.** `onMounted` / `onMount` run only in the browser. Data fetched there
never reaches the raw HTML.

**Astro.** `client:only` renders nothing server-side. `client:load` and `client:visible`
do render server-side — the distinction decides whether content exists in the raw view.

**WordPress.** Markup usually comes from a plugin. Fix it in the plugin's settings or a
child theme; edits to core or to a parent theme are erased on update.

---

## Verification per framework

The raw view must be re-observed **after a rebuild**, not against a stale dev server.

| Framework | Before re-observing |
| --- | --- |
| Next.js | `next build && next start`, or trust dev-server SSR only for structural checks |
| Nuxt | `nuxt build && nuxt preview` |
| SvelteKit | `vite build && vite preview` |
| Astro | `astro build && astro preview` |
| Static hosts | wait for the deploy to land — a CDN cache can serve the old HTML |

A CDN with a long `s-maxage` will keep returning the pre-fix HTML. If the verifier reports
a finding as persistent immediately after a deploy, confirm you are not reading cache
before concluding the fix failed.
