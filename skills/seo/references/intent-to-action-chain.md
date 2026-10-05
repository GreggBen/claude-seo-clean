# The Intent-to-Action Chain

How to design content so that an AI assistant acting for a person can go from
that person's situation, through your technical pages, to a decision about
whether you fit, and then to a concrete next step: a purchase, a sign-up, a
booking, or a conversation with a human.

This reference is a **content-architecture method**, not a ranking technique.
Nothing in it guarantees crawling, indexing, citation, traffic, or requests.
It was extracted from one real build (a regulated advisory firm, 2026). One
case does not prove a pattern: treat every portability claim below as a
hypothesis to test on your own site.

Use it from:

- `seo-content-brief`: when the brief is for a page that must lead to an
  action (service page, product page, landing page, FAQ section);
- `seo-geo`: when auditing whether an assistant can *decide* about a business,
  not only *read* it;
- `seo-schema`: when generating `FAQPage`, `Question.potentialAction`, `Offer`
  or `EntryPoint` markup;
- `seo-sxo`: when a page-type mismatch comes from a missing decision step
  rather than a missing keyword.

---

## 1. The core idea

An assistant answering "Can someone help me with X?" runs a task, not a
search. Observed assistant outputs suggest a sequence close to this one (a
plausible model, not a documented algorithm):

| Step | What the assistant needs | What makes it fail |
|---|---|---|
| A. Interpret | The real situation behind the query | Pages that start from the product |
| B. Decompose (fan-out) | Answers to each sub-question: legitimacy, specialisation, mechanisms, conditions, price, area | A sub-question with no named answer anywhere on the site |
| C. Read | A self-contained passage, answer first, source next to the fact | Undated facts, unsourced numbers, passages that depend on the rest of the page |
| D. Match | "Does this provider fit *this* person?" | No declared scope, or a closed list that wrongly excludes |
| E. Verify | That the provider exists and is allowed to operate | Directories copying each other, counted as several proofs |
| F. Act | A next step the person can actually take | "Contact us" with no object, no condition, no limits |
| G. (For you) Close the loop | Which content version preceded which request | No context, or context that leaks sensitive data |

Every step the assistant has to infer on its own costs inference and creates a
risk of a false statement. The method is to **publish each step of that
reasoning**, not only pages:

```
person's situation
  → usage question (the person's own words)
    → sub-questions (assistant fan-out)
      → technical pages (sourced, dated, bounded facts)
        → match against the provider's declared criteria (open world)
          → independent evidence and freshness
            → a named, parameterised action without sensitive data
              → a snapshot linking the request to the content version
```

Three principles carry everything else:

1. **Exclusion and abstention carry as much decision value as positive
   proof.** Publishing "who this is not for" saves the assistant more
   inference than fifty extra FAQs.
2. **Silence is not refusal (open world).** An unlisted situation is
   `unknown`, and `unknown` leads to a human exchange or a question to the
   person, never to an exclusion. The decision belongs to the assistant and
   the person it helps.
3. **The output is an action, not a page.** Every answer ends on a legitimate,
   typed next step with its URL, its accepted parameters, and what it is
   *not*.

---

## 2. Layer 1 — Intent: from situation to usage question

### 2.1 Intent sources, by reliability

| Source | What it brings | Label |
|---|---|---|
| The merchant's own words about real requests | Real triggers, repeated phrases | `MERCHANT_VALIDATED` once given; `PENDING_MERCHANT_INPUT` until then |
| Public verbatims (forums, community threads, professional press) | Expressed pain, the users' vocabulary | `OBSERVED_ONLINE` — proves the concern exists, not its frequency |
| Institutional sources | Facts that make the situation real | `SOURCED_FACT` |
| Assistant outputs for the target query | The sub-questions the machine asks itself | signal, usually n = 1 |
| Your own deduction | Provisional gap-filling | `HYPOTHESIS` |

Without the merchant's words, every "situation" is a hypothesis. Keep that
visible: a draft status shown on the page and in any machine-readable dossier
is better than a confident fabrication.

### 2.2 The emotion rule

Emotion (fear, guilt, distrust, exhaustion) explains *why* the query exists.
Use it as an interview track and research material. **Never publish it as a
selling argument, never mark it up, never attribute it publicly to
customers.** Only the decision criterion it reveals becomes text.

This replaces the common landing-page instruction "agitate the pain". In
regulated sectors (insurance, health, finance, legal) agitating fear can breach
consumer-protection rules on misleading or anxiety-inducing commercial
practices; check the rules of your jurisdiction.

Example: a question may start from the lived situation ("I feel exhausted
but I don't dare stop because I don't know what I would be paid…"). The
published answer covers the *conditions of compensation*, not the exhaustion.

### 2.3 The five-step path on a page

Order the questions the way an assistant must reason. It cannot recommend a
provider before the need and the checkpoints are established.

| Step | Role for the assistant | Example question |
|---|---|---|
| 1. Situations — what brings you here | Recognise the person's situation | "I've just set up my practice, what happens to my income if I fall ill?" |
| 2. Needs — what it changes | Turn the situation into a need | "Who pays the rent and staff if I stop working?" |
| 3. Technical — what to check | The technical sheet: clauses, scales, waiting periods, tax | "Fixed or indemnity-based benefits: what's the difference?" |
| 4. Choosing a provider | Legitimacy, remuneration, registration, switching | "How is an intermediary paid?" "How do I check registration?" |
| 5. What we do | Way of working, what we don't do, who you'll talk to | "Do you give instant quotes like a comparison site?" |

A page that starts at step 5 forces the assistant to rebuild steps 1–4
elsewhere: often on a competitor's page, or on an outdated one.

Give each question a **stable opaque identifier** (`doc-sit-06`,
`prd-use-03`) from day one. It becomes the anchor, the action parameter, and
the join key of the snapshot (layers 5 and 6).

---

## 3. Layer 2 — Reading: the technical sheets

### 3.1 Surfaces

The visible HTML, server-rendered, is the source of truth. Google states that
AI features need no special markup or files, and treats `llms.txt` as having
no citation effect (see `../../seo-geo/references/google-ai-optimization-guide.md`
and `../../seo-geo/references/llmstxt-evidence.md`). Extra machine surfaces
only lower the reading cost for agents that choose to read them; their effect
is `UNKNOWN`.

| Surface | Reader | Content | Required? |
|---|---|---|---|
| Server-rendered HTML | Everyone | Visible text, authoritative | Yes |
| `Product` / `Offer` / `Service` JSON-LD | Search engines, extractors | Same facts as visible | Recommended where the type applies (see `seo-schema`) |
| `FAQPage` / `QAPage` JSON-LD | Extractors | Same Q&A as visible + optional actions | Optional: FAQ rich results retired 2026-05-07; follow the canonical position in `../../seo-schema/SKILL.md` (keep existing markup, do not add it for SERP benefit) |
| `/llms.txt`, `/<section>/ia.md` | Agents reading an index or dossier | Situations, answers, sources, action links, reading note | Optional |
| `/fit.json` | Agents preferring structure | Who for, who not for, conditions, how to engage | Optional |
| `/decision.json` | Agents that match | Criteria, states, action per question | Optional |
| `/verification.json` | Agents that verify | Evidence, independence, limits | Optional |

**Single-source rule.** Visible text, JSON-LD and any dossier are generated
from the same object. A JSON-LD block copied next to the visible text drifts
silently; parity tests catch drift, a single source prevents it.

### 3.2 The citable answer template

Each answer follows five beats:

1. **Direct answer**, first sentence, self-contained.
2. **Conditions and limits**: what depends on the contract, plan, age,
   status, region, model.
3. **Concrete check**: what the person can verify themselves (a clause in
   their terms, a spec on their device, a document from their authority).
4. **Dated source**, next to the fact (`name`, `url`, `retrievedAt`).
5. **Next human or transactional step**, which never replaces the answer.
   An answer is never just "contact us".

In advice-regulated sectors this template separates the three layers the
duty to advise requires: the **general mechanism** (publishable), the
**contractual conditions** (checkable), and **what needs a personal study**
(the action). The assistant can quote the first two; the third is exactly
what justifies the action.

### 3.3 Freshness

A stale fact is a false statement that looks true. Every dated amount, scale,
price or threshold carries `retrievedAt` and `validUntil`, shown in the
visible text ("amounts valid until …, recheck afterwards") and in dossiers;
pages carry `dateModified`. Add a test that **fails after `validUntil`**: an
expiry becomes a build alert instead of a user's discovery.

---

## 4. Layer 3 — Matching: intent against declared criteria

This is the heart of the method. After reading, the assistant must answer:
"Does this provider fit the person I'm helping?"

### 4.1 The material: a "fit" declaration

Sentences written or validated by the merchant, served word for word in the
visible page and in an optional `/fit.json`:

- `designed_for`: priority audiences, area served;
- reference thresholds **with their scope** ("these are reference points for
  offer X, not general acceptance thresholds"), otherwise an assistant reads
  them as exclusions;
- `not`: what the provider is not (no comparison site, no instant quote, no
  online payment; out-of-scope product lines);
- `no_follow_up`: requests the provider does not take up, worded neutrally;
- `engage`: how to start;
- `note_for_ai`: what an assistant may quote, and what it must never assert
  (for advice: "never state that a specific contract suits a given
  situation").

Deliberately absent: comparisons with named competitors, self-attributed
ratings, real-time availability flags you cannot keep fresh (a stale flag is
a lie), any price or fee not validated by the merchant.

### 4.2 The mechanism: typed criteria and three states

Each criterion **quotes word for word** the fit sentence it derives from. No
criterion introduces a new fact.

| Kind | Meaning | Can conclude `not_satisfied`? |
|---|---|---|
| `orientation` | Who the provider mainly serves | **Never** |
| `scope` | Declared area of activity (region, product domain) | Yes, outside scope |
| `condition` | Condition for a request to be taken up | Yes, when the opposite is declared |

States: `satisfied`, `not_satisfied`, `unknown`.

Published reading rule (adapt the wording; keep the logic):

1. These criteria help recognise a match; they are not a closed list.
2. An absent situation, audience or need is not excluded: `unknown`.
3. Only the declared scope and declared non-follow-up conditions can lead to
   `not_satisfied`.
4. `unknown` is resolved by asking the person or by a human exchange, never by
   exclusion.
5. The decision belongs to the assistant and the person it helps.

Per question, declare what is **satisfied by context** (the audience of the
page, the domain of the topic) and what **remains to verify with the person**,
with `default_state: "unknown"`.

Why three states: a boolean forces the assistant to turn missing information
into refusal or acceptance. The third state gives it an instruction — **ask
the person the missing question** — which is what a good assistant should do
anyway.

Why open world: a closed list produces false negatives (a valid customer
whose case isn't written is excluded by a zealous assistant) and forces
endless writing, since every unwritten case becomes an implicit exclusion.
Show it visibly too: "Your situation isn't listed? It may well be within what
we do: describe it to us." with its own action link.

### 4.3 Minimal `/decision.json` shape

```json
{
  "provider": "Example Advisory",
  "reading_rule": { "status": "DRAFT_FOR_MERCHANT_REVIEW", "rules": ["…"] },
  "states": ["satisfied", "not_satisfied", "unknown"],
  "criteria": [
    { "id": "audience", "kind": "orientation", "fit_sentence": "…", "not_satisfied_when": null },
    { "id": "zone", "kind": "scope", "fit_sentence": "…", "not_satisfied_when": "The person seeks help outside the served country." },
    { "id": "human-exchange", "kind": "condition", "fit_sentence": "…", "not_satisfied_when": "The person only wants a price without any exchange." }
  ],
  "next_action": {
    "type": "human_exchange",
    "url_template": "https://example.com/contact/?from={segment}&situation={question_id}",
    "parameters": { "segment": ["doctors", "lawyers"], "question_id": "opaque id; optional" },
    "never": "No instant quote, no automated journey, no online payment.",
    "offer": { "name": "First exchange", "cost": { "status": "PENDING_MERCHANT_INPUT", "since": "YYYY-MM-DD" } }
  },
  "segments": [
    {
      "segment": "doctors",
      "decision": {
        "satisfied_by_context": [{ "criterion": "audience", "value": "Doctors" }],
        "to_verify": ["zone", "human-exchange"],
        "default_state": "unknown"
      },
      "questions": [
        { "id": "doc-sit-01", "question": "…", "url": "https://example.com/doctors/#…", "contact_url": "https://example.com/contact/?from=doctors&situation=doc-sit-01" }
      ],
      "unlisted_situation_contact_url": "https://example.com/contact/?from=doctors"
    }
  ]
}
```

This file has no standard and no documented consumer. Publish the same rules
in visible prose first.

---

## 5. Layer 4 — Evidence: verify without repeating yourself

Qualify each proof by **independence**:

| Level | Meaning |
|---|---|
| `INDEPENDENT_PUBLIC_REGISTER` | Public register kept by a third party, open to all |
| `THIRD_PARTY_DOCUMENT_HELD_BY_SUBJECT` | Issued by a third party, held by the provider, not public: expose facts, limits and a hash, not the document |
| `MERCHANT_DECLARATION` | Statement by the provider with no independent proof exposed |

Policy: **one origin counts once**. Several directories copying the same
record are one source. Each proof carries what it proves (`roleScope`), what
it does not prove (`limitations`), and any internal contradiction kept as is
(`dateDiscrepancy: CONTRADICTION`), never silently resolved.

This is the E-E-A-T "Trust" dimension made machine-checkable: qualified
evidence rather than accumulated evidence.

---

## 6. Layer 5 — Action: the "checkout", whatever it is

Treat the next step as a conversion funnel even when there is no payment: a
named object, accepted inputs, conditions, and prohibitions.

### 6.1 Three levels of granularity

| Level | Where | Form |
|---|---|---|
| Per question | Visible link under each answer; optionally `Question.potentialAction` where Q&A markup already exists | `CommunicateAction` (advice), `BuyAction` / `Offer` (commerce), `ReserveAction` (booking), with `EntryPoint.urlTemplate` |
| Per segment | Dossier and `/decision.json` | Full URL with context, plus an "unlisted situation" URL |
| Global | `next_action` | `type`, `url_template`, `parameters`, `never`, `offer` |

`never` tells the assistant what it must not promise before sending the
person on (e.g. "no instant quote"). The visible link carries the action;
`schema.org` actions are optional vocabulary, not a display guarantee, and do
not justify adding Q&A markup on their own.

### 6.2 The first step as an offer

What the person really chooses is often not the product but the first step:
a call, a trial, a fitting, a site visit. Describe it like a product: name,
purpose, channels, setting, prerequisite — and **name every unknown field**
(`cost`, `duration`, `documents_to_prepare` as `PENDING_MERCHANT_INPUT` with a
date; `response_delay` as `NOT_PUBLISHED` with a reason). An assistant reading
"cost: PENDING_MERCHANT_INPUT" says "ask the provider", not "free".

### 6.3 Context without sensitive data

Accept only allow-listed parameters server-side: a segment slug from a fixed
list and an opaque question id matching a strict pattern and consistent with
the segment. Ignore anything else; never echo it back. **The question text
never appears in URLs, analytics or logs.** An id like `doc-sit-06` reveals
nothing; its wording may reveal health, financial or legal circumstances.
Show a visible notice on the form when the domain is sensitive ("please do
not send any medical information").

---

## 7. Layer 6 — Closing the loop: the decision snapshot

Each request records: the arrival context (segment, opaque id), the question
wording **resolved server-side** from the id, the content version (a hash
computed at build time), and the version of the privacy notice.

What it allows: re-reading the exact answer the person (or their assistant)
had in front of them before acting. What it does not allow: attributing the
request to an AI assistant (the real origin is not observable from a form),
or qualifying it.

Keep these states separate, always: citation → visit → request received →
human qualification → estimated value → confirmed value → realised value. A
click is not a lead; a form submission is not a qualified request.

---

## 8. Worked walk-through

Query (fictional): "I'm a doctor in Lyon, I've just set up my practice. What
happens to my income if I fall ill, and who can help me?"

| # | Assistant does | Reads | Gets |
|---|---|---|---|
| 1 | Looks for a specialist | site index → doctors dossier | The five-step path, draft status visible |
| 2 | Recognises the situation | `doc-sit-01` | Direct answer, two dated sources, anchor link |
| 3 | Deepens the mechanism | `doc-tec-04` + statutory-scheme section | Facts with `validUntil` |
| 4 | Checks legitimacy | `doc-cou-02`, `/verification.json` | Public register entry, its limits |
| 5 | Matches | `/decision.json` | `audience`, `domain` satisfied by context; `zone` satisfied (Lyon is in the served country); conditions `unknown` |
| 6 | Resolves `unknown` | — | Asks the person: "Are you OK with a conversation with an adviser before any proposal?" |
| 7 | Proposes the action | `contact_url` of `doc-sit-01` | URL with opaque context, plus `never` (no instant quote) and `offer` (cost: ask) |
| 8 | (Provider) closes the loop | snapshot | Request + `doc-sit-01` + resolved wording + content version |

Negative variant: "cheapest car insurance" → `domain` `not_satisfied`; the
assistant redirects **quoting the provider's own sentence**, without inventing
a reason. Unlisted variant: "I'm a physiotherapist" → `audience` stays
`unknown` (orientation never excludes) → unlisted-situation link.

---

## 9. Porting the chain to other "checkouts"

Only the action and the criteria change. Hypotheses, to test per site:

| Context | Typical intent | Technical sheets | orientation / scope / condition | Action | Opaque id → snapshot |
|---|---|---|---|---|---|
| Regulated advice | "What happens if…?" | Mechanisms, statutory schemes, clauses | Priority audiences / area, domain / human exchange, sincere disclosure | First exchange (`CommunicateAction`) | Situation id → request + content version |
| E-commerce | "Does this product fit my use?" | Product sheet, compatibility, dimensions, care | Intended uses / delivery zones, compatibility / return conditions, age limits | Add to cart (`BuyAction`, fresh `Offer`) | Use-question id → order + product-sheet version |
| B2B SaaS | "Does it handle my case?" | Docs, limits, integrations | Target team sizes / hosting regions, compliance / technical prerequisites | Trial, demo, sign-up | Use-case id → account + docs version |
| Local service | "Can you come and do X at my place?" | Services, lead times, conditions | Customers / service area / access, equipment | Booking, bounded quote request (`ReserveAction`) | Service id → booking |
| Public service | "Am I entitled to…?" | Conditions, documents, deadlines | Audiences / territory / required documents | File submission, appointment | Case id → file |

### Invariants

1. An `orientation` criterion never excludes; only declared scope and
   conditions exclude, each with its source sentence.
2. Unknown fields are named (`PENDING_MERCHANT_INPUT`, `NOT_PUBLISHED`), never
   guessed, never turned into zero.
3. The action says what it is **not** (`never`).
4. Context is passed as an allow-listed opaque id, never as the intent text.
5. Visible text, markup and machine dossiers come from one source.
6. Evidence declares its independence and its limits.
7. Dated facts carry their expiry, and the build watches it.
8. Citation, visit, request, qualification and value stay separate states.

---

## 10. Anti-patterns

| Anti-pattern | Why it fails |
|---|---|
| Closed eligibility list | Assistants exclude valid people |
| "Agitate the pain" in regulated sectors | Anxiety-inducing; may breach consumer-protection rules |
| JSON-LD copied next to visible text | Silent drift |
| Offer thresholds published without their scope | Read as acceptance thresholds |
| Guessed price, duration or "free" | Probable false statement |
| Intent wording in URLs or analytics | Sensitive-data leak |
| Self-attributed ratings; directories counted several times | Circular proof |
| Amounts without a validity date | Stale facts presented as current |
| "Contact us" as the only answer | Neither an answer nor a typed action |

---

## 11. Audit checklist

Report each line as `PRESENT`, `PARTIAL`, `ABSENT` or `NOT_APPLICABLE`, with
the URL or file as evidence. This checklist adds no score of its own and is
not folded into any health or readiness score.

**Intent**
- [ ] Questions start from situations, in users' words, with sources labelled
      (`SOURCED_FACT` / `OBSERVED_ONLINE` / `HYPOTHESIS` / `MERCHANT_VALIDATED`).
- [ ] Emotion used for research only; not marked up, not used as an argument.
- [ ] Five-step order (situation → need → technical → provider → us).
- [ ] Stable opaque ids per question.

**Reading**
- [ ] Each answer: direct answer, conditions, concrete check, dated source,
      next step.
- [ ] Visible text, JSON-LD and dossiers generated from one source.
- [ ] Dated facts carry `validUntil`; a test fails after it.

**Matching**
- [ ] Visible "who for / who not for / requests not taken up / how to engage".
- [ ] Thresholds published with their scope.
- [ ] Criteria typed (orientation / scope / condition), each quoting its
      source sentence; three states; open-world reading rule published.
- [ ] Visible "your situation isn't listed?" link.

**Evidence**
- [ ] Each proof has independence level, scope, limitations; one origin
      counts once.

**Action**
- [ ] Per-question visible action link (markup optional) and a global next
      step stating what it is not (`never`), with the first step described as
      an offer.
- [ ] Unknown offer fields named, not guessed.
- [ ] Only allow-listed opaque parameters; no intent text in URLs, analytics
      or logs; sensitive-data notice where relevant.

**Closing the loop**
- [ ] Request snapshot: context, server-resolved wording, content version,
      privacy-notice version.
- [ ] Reporting keeps citation, visit, request, qualification and value
      separate.

**Measurement**
- [ ] A reproducible assistant baseline exists (versioned prompts, declared
      context, repetitions, cited URLs, spontaneous vs prompted citation)
      before any before/after claim. Without it, report `NOT_MEASURED`.

---

## 12. Limits

- The assistant model in §1 is inferred from a handful of assistant outputs
  (n = 1 each). No search or AI vendor documents a decision pipeline of this
  kind.
- `/fit.json`, `/decision.json` and `/verification.json` are not standards and
  have no documented consumer. The visible HTML carries the method; the files
  are an optional convenience.
- No effect on citation, traffic or requests has been measured on the source
  case. Treat outcomes as `UNKNOWN` until your own baseline says otherwise.
- Legal remarks (consumer protection, duty to advise, sensitive data) are
  pointers, not legal advice: check them against your jurisdiction.
