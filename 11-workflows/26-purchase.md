# Purchase

**Use when:** buying hardware or goods: deciding what to buy, placing the order, or fighting a vendor when an order goes wrong. Wrong means a missing or damaged item, a used item sold as new, or a refund promised and never paid.
**Not for:** payday and bills, which is 09 monthly money close. A research write-up with no purchase, which is 18 research to home. Setting up a machine once it arrives, which is 16 machines.
**Done when:** he placed the order himself, and its plan is in `13-archive/shopping/` marked purchased. For a dispute: the money is verified in his account, and the case file is archived.

Money leaves only on his click. The research serves his one use case, stays inside what his city can deliver, and lands in one plan file that states today only.

```d2
direction: down

size: "1. Size it" {shape: diamond}
umbrella: "2. Setup plan first"
constraints: "3. The use case\nand the hard constraints"
search: "4. Search by category\nlocal first"
plan: "5. The plan states today"
pick: "6. He picks" {shape: hexagon}
buy: "7. Buy\nstop before Place Order" {shape: hexagon}
after: "8. Archive the plan"
wrong: "9. It went wrong\nreturn and dispute"

size -> umbrella -> constraints -> search -> plan -> pick -> buy -> after
size -> buy: "a small, simple buy" {style.stroke-dash: 3}
buy -> wrong: "the order goes wrong" {style.stroke-dash: 3}
```

---

## Steps

### 1. Size it

> **Decision Point**: what kind of buy is it?
> - A small, simple buy: keep it simple. Name the use case in one line, then go straight to step 7.
> - A repeat order: confirm which seller he wants before going on.
> - Anything that needs a choice: steps 2 to 6.
> - He asks for the specs to look for, not for listings: write the spec list, and search nothing.

- [ ] A plan file already exists for the item: read it, and never re-derive what it settled.
- [ ] "Don't execute anything" means documentation only, until he gives a fresh go.

### 2. Read the umbrella first

- [ ] Read the umbrella plan in `02-ana/shopping/` before any component verdict, if there is one. It owns the purchase rules, the sequencing, and the items only the whole setup asks for.
- [ ] Each item gets one plan file under the umbrella. Never open a second plan file for a category that has one.
- [ ] The setup plan's sequencing holds across every item.

### 3. Name the use case and the hard constraints

- [ ] Name the one axis the use case lives on. Drop every spec it never touches, and say so in the plan. Never soften that axis.
- [ ] Write his standing hard constraints into the umbrella plan once (build type, which OS it is judged on, any health constraint from `02-ana/health/`), and apply them verbatim.
- [ ] What he owns comes from the machine (`/sys/class/dmi/id`, `lspci`, `lsblk`), never from a plan's pick.
- [ ] Never raise his budget on a claim that nothing good exists at that price, unless the evidence is hard.
- [ ] A spec he never ruled out is never a hard disqualifier.
- [ ] No bloat: a component does one job, and extra features are no tiebreaker.
- [ ] He adds and drops constraints mid-search. Rewrite the plan to the new constraints at once.
- [ ] The budget is his cap per item, stated in its plan. Rai never raises it without hard evidence.

### 4. Search

- [ ] Search by category first and brand second. Say so if a brand name drove the first pass.
- [ ] Check that each candidate can be ordered to his city before it enters a shortlist. Keep an ordered list of local channels: the big local retailers first, then the national Amazon store, then specialist importers.
- [ ] A store abroad is not a route unless it ships here with a warranty. Some vendors have no local consumer channel at all. A configured machine with a local warranty comes from a distributor, by a phone quote.
- [ ] Verify the model code, never the product name.
- [ ] Prices come only from listings checked within the last week. Each row carries its source link and the date it was checked.
- [ ] `/shopping → vet` runs the checks: live verification, the listing traps and the price floor.
- [ ] A wide sweep goes to the `researcher` agent. Its inputs are the use-case axis, the hard constraints and the local channel list. It returns candidates with model codes, listing links, prices and dates, and writes nothing.
- [ ] Rai re-checks each candidate's listing live before it enters the shortlist.

### 5. Write the plan

- [ ] The plan states today only: no "was X, now Y", no banners, no strikethrough. When a decision changes, rewrite the whole file as if it always said so.
- [ ] Dates in the plan only mark when data was gathered.
- [ ] Delete rejected options. Two short prose lines are allowed: a "cut from this list" line, and a "not sold here" line.
- [ ] Keep the candidates side by side until he picks. Never write the plan as decided before he says so.
- [ ] Give one recommendation with its reasoning, as 2 or 3 options with one Recommended.
- [ ] Keep a verified purchase link for each model.

### 6. He picks

- [ ] The pick is his. Rai's lean is a recommendation, never the decision.
- [ ] He may watch the market before buying. The plan stays live while he does.
- [ ] A plan records the choice. It never authorizes a purchase.

### 7. Buy

- [ ] `/shopping → buy` runs the checkout: the seller check, certificates and gift-card balance, the address, and a live price and stock check.
- [ ] Stop before Place Order. Report the item, the price, the seller, what covers the charge, the address and the arrival date.
- [ ] He clicks, or he says the word for that order. A go on the task is not a go on the money step.
- [ ] Payment details are his to enter. Never accept terms or an upsell on his behalf.

### 8. After the purchase

- [ ] Move the plan to `13-archive/shopping/`, marked `status: purchased`, with a closing note naming what he bought.
- [ ] The setup plan states today: the item is owned now.
- [ ] A machine that arrives is stood up through [[16-machines]] step 10.

### 9. When it goes wrong

- [ ] `/shopping → return` builds the case: the facts from the vendor's own order page, the case file in `02-ana/admin/`, and a route to a human.
- [ ] Never name the remedy. State the problem and its impact, ask how they will resolve it, and stop.
- [ ] Every message waits for his go, one message at a time.
- [ ] The claim says exactly what arrived. Rai refuses to widen it over goods that came fine.
- [ ] Match the agent's language, in short messages with one point each. Move fast, and do not drag it out.
- [ ] A promise is not a payment. Record who promised what, and when it should land.
- [ ] Verify a refund by its confirmation email and its entry on the transactions page, both.
- [ ] A partial refund: diff the promised item list against the refund emails, and the order's Refund Total against its Grand Total.
- [ ] Escalate in order: the chat follow-up, then a letter that enforces the decision already made. A complaint to the consumer-protection authority is the last resort.
- [ ] When they claim a refund was issued, ask for its refund reference number.
- [ ] The case file moves to `13-archive/shopping/` only when its own text marks it closed or resolved.

### 10. Sync

- [ ] Vault edits follow the commit rule in `11-workflows/AGENTS.md`.

---

## Connections

- Skills: `/shopping → vet` (checks before the money leaves), `/shopping → buy` (the checkout, up to the stop), `/shopping → return` (the dispute).
- Agents: the `researcher` agent (the category sweep across local channels).
- Workflows: [[16-machines]] sets up a machine that arrives. [[13-capture-sweep]] and [[18-deep-research-to-home]] route purchase research into its plan here.
