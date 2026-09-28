---
name: vet
description: Verify a product before John spends — generation, specs, price floor, local availability, listing traps
allowed-tools: Read, Write, Edit, Bash, WebSearch, WebFetch, mcp__claude-in-chrome__*
---

# Vet

Everything that happens before the money leaves. Output goes into the relevant
`02-ana/shopping/{thing}-plan.md`, which is the source of truth for that search.

## Verify live, never from memory

Prices, stock, model generations and availability change weekly. Every claim in
a recommendation must come from a page checked in this session. If a fetch is
blocked, say so and mark the row unverified rather than filling it from training
data.

## Hardware rules are personal, not defaults

Any standing rule about what generation, spec floor or age is acceptable
belongs to the user, not this skill. Read it from the category's plan file
(e.g. `02-ana/shopping/laptop-plan.md`) before recommending anything, and
apply it verbatim. If no rule file exists yet for the category, ask once
and write the answer down there so it never has to be re-asked. Example
shape of such a rule: "CPU, RAM and storage must be the latest generation
available"; "newest is not automatically best, verify series/launch
date/benchmarks"; "nothing older than N years."

## Local availability first

A product the user cannot actually order to where they live is not a
candidate, however good it is. Confirm real orderability (ships to the
user's country/region, not just listed) before it enters a shortlist, not
after — a cross-border storefront that looks cheaper often can't ship there
at all.

## Listing traps

Marketplace listings lie, in patterns worth checking every time:

| Trap | Tell |
|------|------|
| International model | "International model", "no national warranty" in the description |
| Wrong variant | Title says one config, the selected variant is another. Check the variant selector, not the title |
| Ghost stock | Third-party seller, "only 1 left", price well under every other listing |
| Wrong fit | Accessories mislabeled for a nearby model (a Pro/Plus/Max case sold as the base model) |
| Reseller markup | Same SKU at multiples of the direct price, usually an unrelated storefront |

A price that beats every other listing by a wide margin is a reason to look
harder, not a reason to buy.

## Price floor

Check across the retailers that actually serve the user's country (record
which those are once, per category) plus the manufacturer direct. Record the
floor and where it was found, with the link and the date checked. Note when a
promotional certificate only applies to a specific seller, because that
changes which listing is genuinely cheapest.

## Output

Update the plan file in `02-ana/shopping/`. Keep verified purchase links per
model. Keep rejected candidates in the file **labelled as rejected with the
reason**, so the same trap is not re-evaluated in three months.

Do not create a new plan file when one exists for that category.

## Rules

- One recommendation, with the reasoning, not a survey of everything on the market.
- Every spec claim carries its source and the date it was checked.
- Say what is still unverified rather than implying it was checked.
- Never invent a requirement that forces a purchase he did not ask for.
