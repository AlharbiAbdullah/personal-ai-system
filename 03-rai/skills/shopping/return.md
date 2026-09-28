---
name: return
description: Fight a vendor over an order that went wrong — missing item, damaged goods, used sold as new, or a refund promised and never paid
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion, mcp__claude-in-chrome__*
---

# Return

Build the case, open the channel, let them make the first offer, hold them to it.
The shape works for any online retailer.

## The two rules that override everything

**1. Never send a message without John's explicit go.**
Draft it, print it in the terminal, stop. He reads it, he says go, then click send.
This holds even after he has said "start" or "go ahead" on the task. Starting a
task is not approval of the specific words. One message at a time.

**2. Never name the remedy.**
State the facts and end with "How are you going to resolve this?" Then stop typing.
Target figures live in an internal acceptance table used to judge their offer,
never in the message. Vendors routinely volunteer more than the item was worth
when the remedy is left open; naming a figure first only caps their offer at it.

## Honesty boundary

The claim describes exactly what arrived. Never widen it over goods that came
fine, and never imply damage that did not happen, even when asked directly.
Say it plainly once, then write the accurate version, which is usually stronger
anyway: a narrow true claim beats a wide shaky one.

## Step 1: Pull the facts from the vendor, not from him

Open the order page and read it. Never work from memory of what he said. Capture:

- Order number, date placed, date and **time** delivered
- The vendor's own delivery wording, verbatim
- Every item with its **seller** and its **price**
- The money block: subtotal, shipping, promotions, gift card, grand total
- Return window end date
- Whether the order shipped as one delivery group or several

## Step 2: Write the case file

`02-ana/admin/{vendor}-{short-description}-{month}{day}.md`, frontmatter:
`status`, `opened`, `order`, `amount_at_stake`.

Sections, in this order:

1. **The claim, stated exactly.** One table: item, what happened, amount.
2. **Facts on record**, with the vendor's own wording quoted.
3. **What is strong.** Their own records first, pattern second.
4. **What is weak, and the counter.** Every hole they can poke, pre-answered.
5. **Acceptance criteria (INTERNAL, never stated upfront).** A table of what
   their offer would mean: accept, push back, refuse.
6. **Channel.**
7. **Opening message**, in the language the agent is using.
8. **If they push back**, a table of their move to his response.
9. **Do not do.**
10. **Live ammunition held in reserve.** Anything they still owe from before.

## Step 3: Know the traps before they are used

**The wait-it-out stall.** Some self-service flows park a "delivered but
missing" report until a date several days out before they let him reach a
human. Pre-empt it in the opening: the package is not late, it was delivered,
and the item was not in it.

**The promotion clawback.** When a promotion or apology certificate was applied
at order level, a partial refund can be pro-rated, refunding less than the item
price. Work the arithmetic in advance and know the shortfall. If the promotion
was itself an apology credit from a *previous* failure, name that: they are
funding this failure with the apology for the last one.

**The third-party punt.** Items sold by a marketplace seller get routed to the
seller. The counter is that the vendor delivered it on the vendor's own tracking
record, and the A-to-z Guarantee exists for exactly this, inside its window.

**Refund held until return received.** For goods that arrived damaged or used,
that puts the wait on him for their error. Raise it as a fact, then ask what
they will do about it.

**Bundling.** Never let one settlement quietly close a separate outstanding debt.

## Step 4: Reach a human

Find the retailer's direct-message or live-chat entry point rather than its
general contact-us page — the latter often opens a popup the browser tool
cannot drive, while a message/chat URL loads in-tab. Path through the bot:
confirm the item, pick the accurate issue button, then escalate ("I need
more help" / "talk to a person") until a free-text box appears. That box is
where the opening statement goes.

## Step 5: Match the human

Write like a person with a real problem, because he is one.

- **One language.** Whichever the agent opened in. Never send the same content
  twice in two languages, it reads as a machine.
- **Short.** One point per message. A wall of text plus its own translation is
  the single clearest tell that a bot is typing.
- **Plain.** No structure markers, no bullet lists, no bold. Chat prose.

> Sending the same statement twice, once per language, to an agent who opened
> in a single language is one of the clearest tells that a bot is typing —
> match the one language they opened in instead.

## Step 6: Evidence

Photos: convert to a normal, widely-supported format before anything else
(e.g. HEIC to JPEG on macOS: `sips -s format jpeg -s formatOptions 85 -Z 2000
IMG_XXXX.HEIC --out descriptive-name.jpg`). Keep the original, it carries the
capture timestamp. **Read the image yourself** before offering it as evidence
and say what it actually shows.

If the chat channel has no attachment control, ask the agent for an upload
link or a case email address instead of assuming there is none.

## Step 7: Close the loop

Get the amount and the date in writing before agreeing to anything. Then
record in the case file what was promised, by whom, and when it should land.
Set `status: awaiting` with the date, and check back if the date passes with
a short amount unaccounted for — a promise is not a payment.

## Rules

- Read the order page before writing a word of the claim.
- Never claim an order failed when part of it arrived fine.
- Never accept a bundled settlement that closes a separate open debt.
- Never ship a return back before confirming the reason recorded on it is
  accurate and the shipping is on the vendor.
- If the extension drops mid-session, say so and say what could not be verified.
