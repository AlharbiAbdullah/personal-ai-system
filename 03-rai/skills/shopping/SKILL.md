---
name: shopping
description: >
  Shopping router. USE WHEN John is buying something, placing an order, or
  fighting a vendor over an order that went wrong: an item missing from a
  delivery, damaged goods, a used item sold as new, a refund promised but never
  paid, or a purchase decision that needs the specs verified before he spends.
  Routes between vet (before the money leaves), buy (the ordering run itself),
  and return (after it goes wrong). Plans live in `02-ana/shopping/`, live
  disputes in `02-ana/admin/`.
---

# Shopping

Three phases of one thing: money leaving the account for physical goods.

## Routing table

| Task | Sub-skill | File to Read |
|------|-----------|--------------|
| Verify a product before buying: specs, generation, price floor, local availability, listing traps | vet | `vet.md` |
| Place an order: seller check, promo and gift-card handling, address confirm, stop before Place Order | buy | `buy.md` |
| Item missing, damaged, used-sold-as-new, or a refund promised and never paid | return | `return.md` |

## How to use

1. Pick the sub-skill by which phase he is in.
2. `Read` that file in this directory.
3. Follow it.

## Rules that hold across all three

**Never send without his go.** Any message that leaves the machine, in any
channel, gets drafted and shown first. Starting a task is not approval of the
words that get sent. Draft, show, wait, then click.

**Never name the remedy first.** State facts, ask how they will resolve it. A
figure named first caps the outcome. See `return.md` for the full reasoning.

**Never misrepresent what arrived.** Claims describe exactly what was received.
Two items failing out of four is a two-item claim, and its strength comes from
being exact. Refuse to widen a claim over goods that arrived fine, even when
asked.

**Verify live, never from training data.** Prices, stock, model generations and
availability change. Check the retailer, do not recall.
