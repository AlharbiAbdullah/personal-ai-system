---
name: buy
description: Run the ordering flow — seller check, promo and gift-card handling, address confirm, hard stop before Place Order
allowed-tools: Read, Bash, AskUserQuestion, mcp__claude-in-chrome__*
---

# Buy

Driving a checkout on his behalf. The whole point of this file is the last step.

## Hard stop

**Never click Place Order.** Fill the cart, apply what should apply, verify the
address, then stop and report what is about to be charged, to what payment
method, arriving when. He clicks, or he says the word and then it is clicked.

This is the same rule as never sending a message without his go, and it is not
waived by "go ahead" on the overall task.

## Before checkout

**Seller.** Check who sells each item. A promotional certificate that only
applies to items sold directly by the retailer is worth nothing on a
marketplace listing, so the seller line decides which listing is actually
cheaper. Marketplace sellers also change what happens if the order goes
wrong, see `return.md`.

**Certificates and gift-card balance.** A promotional certificate does not appear
under Gift Cards and Balance and applies automatically at checkout only on
qualifying items. Gift card balance applies unless deselected. Report which is
covering what, and what actually hits the card.

**Address.** Confirm the delivery address is the intended one. He has more than
one and the account default is not always right for the order.

**Recency.** If the item came off a plan file, confirm the price and stock are
still live rather than trusting the file's snapshot.

## Report before the stop

State plainly: item and quantity, price, seller, what covers it (card, gift card,
certificate), delivery address, arrival date. Then stop.

## Rules

- Never enter card numbers, CVVs, or any payment credential. If a payment method
  needs adding, he does that himself.
- Never accept terms, consent banners, or subscription upsells on his behalf.
- Never place the order without an explicit yes for that specific order.
- If a promotion silently fails to apply, say so before he decides.
