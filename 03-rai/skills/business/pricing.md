---
name: pricing
description: >
  Pricing page / pricing one-pager / packaging narrative. USE WHEN the user
  needs to communicate price + plan structure to customers — whether as a
  live web page, a sales one-pager, or a strategic packaging decision.
---

# Pricing

Design pricing that customers understand and that supports the business.

## When to use

- Ship or refresh a public pricing page
- Draft a pricing one-pager for sales use
- Decide or refine packaging (tiers, units, bundles)
- Explain WHY the pricing is what it is (internal rationale + public narrative)

## When NOT to use

- Individual proposal pricing for one client → `/business/proposals`
- Sales narrative / deck → `/business/sales`

## Three decisions before writing anything

1. **Value metric** — what unit does the customer pay for?
   - Seats (per-user SaaS)
   - Usage (API calls, storage, compute hours)
   - Outcome (per shipped report, per case closed)
   - Flat (one price, unlimited use)

   The right metric grows naturally with customer value. Bad metrics cap growth or misalign incentives.

2. **Tier shape** — how many plans? What's different between them?
   - **3-tier default**: Starter, Pro, Enterprise. Works for most SaaS.
   - **Single plan**: One price, one experience. Works for narrow products.
   - **Usage-only**: Pay-as-you-go. Works for developer tools + infra.
   - **Hybrid**: Base plan + usage overage. Works when a minimum is required.

3. **Anchor price** — what's the highest-priced plan (visible or not)?
   - An Enterprise "Contact Us" anchor makes Pro feel reasonable
   - A cheap Starter anchor makes Pro feel premium
   - The anchor sets expectations before any feature comparison

## Pricing page structure

1. **Headline** — one sentence on the value promise (not the price)
2. **Plan cards** — side-by-side, max 4. Features listed, differences obvious.
3. **Comparison table** — detailed feature-by-feature matrix (below the fold)
4. **FAQ** — 5–10 questions addressing: cancellation, billing, limits, upgrades
5. **CTA** — "Start free", "Book a demo", "Contact sales" per tier
6. **Trust signals** — customer logos, testimonials, security badges

## Pricing page copy rules

- State the price clearly. Hidden prices kill conversion.
- Anchor the most popular tier (usually middle) visually + say "Most popular"
- Feature lists: outcomes over features ("unlimited exports" beats "exports module")
- Show annual + monthly billing; annual should be 15–20% cheaper
- Explicit "what's included" — no surprises at checkout

## One-pager (sales use)

One page, 4 sections:
1. **Plans side by side** — 3–4 tiers with price + top 3 features
2. **Usage examples** — "For a team of X, Plan Y costs $Z/month"
3. **Enterprise call-out** — "For X+ users, contact sales for custom pricing"
4. **Contact** — sales rep, email, phone

## Anti-patterns

- "Contact us for pricing" on ALL tiers — huge friction
- Too many tiers (5+) — decision paralysis
- Feature toggles that differ arbitrarily — customers can't pick
- Hiding enterprise price when your competitors publish theirs
- Pricing that doesn't match what's in the order form

## Output

- A markdown mockup of the pricing page (converted to web by designer/engineer)
- A PDF/slide one-pager for sales
- An internal rationale memo explaining the packaging decisions

## Examples

- "Draft the Matchbox pricing page: 3 tiers, seat-based"
- "One-pager for OpenKit enterprise sales team"
- "Should GeoContext charge per API call or per dataset subscription?"
- "Rewrite the Helios pricing to emphasize air-gap guarantee"
