---
name: social-media
description: >
  Short-form post drafting for X (Twitter), LinkedIn, and Substack notes.
  USE WHEN the user wants to publish a tweet, thread, LinkedIn post, or
  Substack note. Three sub-modes inside (one per platform), distinct cadence
  rules per platform.
---

# Social media

Draft short-form posts that don't read like LinkedIn-influencer slop. Each platform has its own physics.

## Voice mandate

Read `references/voice.md` first. The 20 banned words are especially lethal here: social platforms are where AI-generated text gets called out fastest.

## Pick a platform first

| Platform | Length | Vibe | Audience |
|----------|--------|------|----------|
| **X / Twitter** | ≤ 280 chars per tweet, threads up to 8-12 | Punchy, opinionated, one idea per tweet | Tech / builder audience, the region + global |
| **LinkedIn** | 100-400 words | Professional context, but not corporate | the region tech professionals, recruiters, future clients |
| **Substack notes** | 50-200 words | Conversational, between tweet and blog | Existing readers of johndoe.substack.com |

If unsure, ask which platform. Don't write platform-agnostic: they're not interchangeable.

## X / Twitter mode

**Tweet shape:**
- One idea per tweet. No "1/n" unless it's a real thread.
- Hook in the first 5 words. Cold reader stops scrolling or doesn't.
- Thread = sequence of complete tweets, each readable alone.
- No hashtag stuffing. 0-1 hashtag. Use only if it's a real community tag.
- No "What do you think?" closers. They sound like AI.

**Hooks that work:**
- Specific number ("3 silent failures cost us 2 days")
- Strong claim ("The Helios merge wasn't a tech failure")
- Question that's actually a take ("Why does every air-gap stack reinvent the wheel?")

**Hooks that don't:**
- "Let me share my thoughts on..."
- "Here's an interesting observation about..."
- "Today I learned that..."

## LinkedIn mode

**Shape:**
- Strong first line (cold readers see only this in the feed).
- Concrete story or example, 2-3 short paragraphs.
- One specific takeaway. Not five.
- No emojis except sparingly (and only if John explicitly opts in).
- No "agree?" or "thoughts?" closers.

**the region context layer:**
- Real the region project names land harder than abstract examples (Helios, OpenKit, Matchbox when allowed).
- Don't broadcast confidential client info. Sanitize when needed.

**Avoid the LinkedIn-AI tells:**
- "🚀" / "💡" emoji at start of every line
- "I'm thrilled to share..."
- "After much reflection..."
- Three-line setup with one-line punchline cliché
- "Here's what I learned" → cut, just say what you learned

## Substack notes mode

**Shape:**
- More thinking than X, less polish than blog.
- 50-200 words.
- Conversational, like a smart friend's text message.
- Can reference older posts on the substack.
- One idea per note. Not a mini-essay.

**Voice anchor:** read 2-3 of your existing notes at johndoe.substack.com before drafting. Match cadence.

## Process (any platform)

1. **Pick platform**: confirm before drafting.
2. **State the one idea** in a single sentence. If you can't, you don't have a post yet.
3. **Pick the hook**: first 5-10 words. The rest serves the hook.
4. **Draft**: fast. Aim for under 2 minutes for X, under 5 for LinkedIn.
5. **Cut**: first draft is always 30% too long. Trim until it bleeds.
6. **Self-check** against `voice.md` gate.

## Anti-patterns (all platforms)

- "In today's fast-paced world..." → delete
- "I've been thinking a lot about..." → just say it
- Bullet-point sermons disguised as posts
- Three-statement-and-the-third-one-is-the-twist structure (the AI default)
- Quoting yourself with "as I always say..."
- Inspiration-porn close ("keep building, friends")

## Output

Single post text, ready to paste. For threads: numbered tweets separated by blank lines. No markdown formatting in the output unless the platform supports it (LinkedIn doesn't render bold; Substack does).

## Voice anchors

- **X/threads**: existing posts at x.com/johndoe
- **LinkedIn**: TBD: John, drop 2-3 of your past LinkedIn posts at `~/helm/02-ana/voice-samples/linkedin/` for stronger anchoring
- **Substack notes**: johndoe.substack.com archive
- **Voice cadence baseline**: `~/helm/02-ana/journal/` (any recent file). His journal entries have the right rhythm for Substack notes.

## Examples

- "Tweet about the 3 silent failures in Helios pipeline v1/v2 overlap"
- "Twitter thread on why proposal-template platforms always fail"
- "LinkedIn post about the Helios retrospective without naming the client"
- "Substack note about the Acme Corp data lake thesis, riffing off last week's note"
- "Tweet promoting today's blog post"
