---
name: seo-ecommerce
description: >
  E-commerce SEO analysis of product pages, Product schema, offers, images,
  content, and internal links. Use when the user asks for product SEO,
  merchant listing markup, or an e-commerce page audit.
user-invocable: true
argument-hint: "<url>"
license: MIT
metadata:
  author: AgriciDaniel
  original_author: "Matej Marjanovic (Pro Hub Challenge)"
  version: "2.2.0"
  category: seo
---

# E-commerce SEO Analysis

Product page optimization from the page and its structured data. Do not report
live marketplace position or competitor pricing without a verified data source.

## Commands

| Command | Purpose |
|---------|---------|
| `/seo ecommerce <url>` | On-page and Product schema analysis |
| `/seo ecommerce schema <url>` | Product schema validation and enhancement |

---

## 1. Product Page Analysis

Fetch and parse any product page for on-page SEO quality.

### Workflow

```
1. ~/.claude/skills/seo/run-script render_page.py <url> --mode auto → raw/rendered HTML
2. ~/.claude/skills/seo/run-script parse_html.py --url <url>   → SEO elements
3. Analyze product-specific signals (below)
```

### Product SEO Checklist

#### Title Tag
- [ ] Contains primary product keyword
- [ ] Includes brand name
- [ ] Under 60 characters (no truncation in SERPs)
- [ ] Format: `[Product Name] - [Key Feature] | [Brand]`

#### Meta Description
- [ ] Contains product keyword + benefit
- [ ] Includes price or "from $XX" (triggers rich snippet interest)
- [ ] Call-to-action present (Shop now, Buy, Free shipping)
- [ ] Under 155 characters

#### Heading Structure
- [ ] Single H1 matching primary product name
- [ ] H2s for: Features, Specifications, Reviews, Related Products
- [ ] No duplicate H1 tags across product variants

#### Product Images
- [ ] Alt text includes product name + distinguishing feature
- [ ] File names are descriptive (not `IMG_001.jpg`)
- [ ] WebP format served (with JPEG fallback)
- [ ] At least 3 images per product (hero, detail, lifestyle)
- [ ] Image dimensions >= 800px for Google Shopping eligibility
- [ ] Lazy loading on below-fold images only

#### Internal Linking
- [ ] Breadcrumb navigation: Home > Category > Subcategory > Product
- [ ] Related products section (cross-sell / upsell)
- [ ] Link back to category page with keyword-rich anchor
- [ ] Reviews section links to full review page (if separate)

#### Content Quality
- [ ] Unique product description (not manufacturer copy-paste)
- [ ] Word count >= 200 for product description body
- [ ] Specs table present (not just prose)
- [ ] User reviews on-page (UGC signals)

### Scoring

| Category | Weight | Criteria |
|----------|--------|----------|
| Schema completeness | 25% | Required + recommended Product fields |
| Title & meta | 15% | Keyword placement, length, format |
| Image optimization | 20% | Alt text, format, sizing, count |
| Content quality | 20% | Unique description, specs, reviews |
| Internal linking | 10% | Breadcrumbs, related products, categories |
| Technical | 10% | Page speed, mobile rendering, canonical |

---

## 2. Product Schema Enhancement

Validate and generate Product schema following Google's current requirements.

### Required Properties (Google Merchant)

```json
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "",
  "image": [""],
  "description": "",
  "brand": { "@type": "Brand", "name": "" },
  "offers": {
    "@type": "Offer",
    "url": "",
    "priceCurrency": "USD",
    "price": "0.00",
    "availability": "https://schema.org/InStock",
    "seller": { "@type": "Organization", "name": "" }
  }
}
```

### Recommended Properties (Enhance Rich Results)

- `sku` -- product identifier
- `gtin13` / `gtin14` / `mpn` -- global trade identifiers
- `aggregateRating` -- star rating + review count
- `review` -- individual reviews (minimum 1)
- `color`, `material`, `size` -- variant attributes
- `shippingDetails` -- ShippingDetails with rate and delivery time
- `hasMerchantReturnPolicy` -- MerchantReturnPolicy with type and days

### Validation Rules

1. `price` must be a number string, not "$29.99" (no currency symbol)
2. `availability` must use full Schema.org URL enum
3. `image` should be array with >= 1 high-res image URL
4. `priceCurrency` must be ISO 4217 (USD, EUR, GBP)
5. `brand.name` must not be empty or "N/A"
6. Dates in `priceValidUntil` must be ISO 8601
7. If `aggregateRating` present: `ratingValue` and `reviewCount` required

### Schema Scoring

| Completeness | Score |
|-------------|-------|
| All required fields | 50/100 |
| + aggregateRating | 65/100 |
| + sku/gtin/mpn | 75/100 |
| + shippingDetails | 85/100 |
| + merchantReturnPolicy | 90/100 |
| + reviews (3+) | 100/100 |

---

## Cross-Skill Integration

| Skill | Integration Point |
|-------|------------------|
| **seo-schema** | Delegates Product schema generation; reuses validation logic |
| **seo-images** | Product image audit (alt text, format, dimensions) — plus `DigitalSourceType: TrainedAlgorithmicMedia` IPTC label for AI-generated product images (Merchant Center requirement) |
| **seo-content** | Product description E-E-A-T and uniqueness analysis |
| **seo-technical** | Core Web Vitals for product pages (LCP on hero image) |
| **seo-google** | Search Console indexation and PageSpeed data for the product URL |

## UCP — Universal Commerce Protocol (forward-looking)

Google-led standard (co-developed with Shopify, Etsy, Walmart, Wayfair, Visa,
Mastercard, etc.) for letting AI agents discover, negotiate, and transact with
merchants without one-off integrations. Already powers direct buying from AI
Mode and Gemini.

Merchants already on **Google Merchant Center** with clean Product schema can
declare a UCP profile at `/.well-known/ucp` listing capabilities
(`dev.ucp.shopping.checkout`, `.fulfillment`, `.discount`). See
`references/ucp-universal-commerce-protocol.md` for audit criteria,
capability examples, and the relationship to AP2 (Agent Payments Protocol).

### Audit command

```bash
# Discover and validate the UCP profile
~/.claude/skills/seo/run-script ucp_check.py https://store.example.com --json

# With endpoint reachability probes (HEAD each declared capability)
~/.claude/skills/seo/run-script ucp_check.py https://store.example.com --probe-endpoints --json
```

The script returns: profile presence, version, declared capabilities,
structural issues (missing fields, unknown capability IDs), and (with
`--probe-endpoints`) per-endpoint reachability. SSRF-blocked endpoints are
reported explicitly. Missing profile is reported as opportunity, not failure
— UCP adoption is early.

---

## Error Handling

| Error | Cause | Response |
|-------|-------|----------|
| No Product schema found | Page lacks JSON-LD | Analyze page content, generate recommended schema |
| Invalid URL | Malformed input | Validate via `google_auth.validate_url()`, show error |
| Non-product page | URL is category/homepage | Detect page type, suggest `/seo ecommerce schema` instead |

---

## Output Template

```
## E-commerce SEO Report: [URL or Keyword]

### Overall Score: XX/100

### Product Page SEO
- Schema Completeness: XX/100
- Title & Meta: XX/100
- Image Optimization: XX/100
- Content Quality: XX/100
- Internal Linking: XX/100

### Top Recommendations
1. [Critical] ...
2. [High] ...
3. [Medium] ...

Generate a PDF report? Use `/seo google report`
```
