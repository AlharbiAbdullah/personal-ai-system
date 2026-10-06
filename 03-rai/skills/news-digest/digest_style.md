# Bawaba Digest: House Style

The digest is the short version of the daily: what John needs to know today, in one short read. A second headless run writes it right after a complete daily (`scheduled/run-news-ubuntu.sh`, `digest` mode), and this file is its whole brief.

## Input and output

- Input: `~/helm/08-bawaba/daily/YYYY-MM-DD.md`, today's daily. Missing or empty: write nothing and stop.
- Output: `~/helm/08-bawaba/digest/YYYY-MM-DD.md`. Write that one file only.
- Never edit the daily. Never commit. Never archive: the runner moves older digests.

## Reader

John, a data engineer: data platforms, DevOps, AI agents, system design. He runs Claude Code every day with his own memory system, Rai. His rule: "don't pass tokens to me like I am AI, I am human. The less the better."

## Facts

- Read the whole daily first. It runs past 60 KB, so read it in pages. No web, no outside facts.
- Every number, name and product matches the daily exactly.
- Keep the daily's hedges: reportedly, allegedly, claims. Never firm them up. Once the source is gone, the hedge alone carries the doubt.
- One hedge per claim, on the claim it belongs to. Never stack them in one item.
- The takeaway line may draw on the reader profile above, never on new facts.

## No sources, no authors

He does not care where a fact came from or who wrote it.

- Drop links, @handles, poster and author names, and the outlet that reported a fact.
- Drop platforms ("on Hacker News", subreddit names, "trending on GitHub") and points, stars or comment counts. No "a developer said".
- State each item as the fact itself. Companies and products that are the news stay.
- A project, company or person named only because it posted or reported the item is a source. Drop the name.
- Strip the daily's scaffolding: source IDs like `[x-9]`, grade badges, `[AI]`-style tags, the stats table, the coverage and sections lines.

## Pick

- Every item answers two questions: what happened, and what it changes for him (his work, his tools, his setup, his region). No real answer to the second: drop the item. Fewer items is fine.
- News Wire: up to 5. Model releases and pricing, his vendors, data, infra and agent tooling. Skip an item a Hot Topic already covers.
- Hot Topics: one per hot topic in the daily, up to 3.
- Gems: up to 3, from the top shelf only, never from Feed. Spread them across data, DevOps or infra, and agents.
- Wisdom: exactly 1.
- Deep Dive: the daily's one deep dive.
- No Feed section. No story twice.

## Shape

Frontmatter, exactly:

```
---
date: YYYY-MM-DD
daily: "[[08-bawaba/daily/YYYY-MM-DD]]"
---
```

Then six Obsidian callouts in this order, with one blank line between them:

| Callout | Title |
|---|---|
| `> [!abstract]` | Bottom line |
| `> [!info]` | News Wire |
| `> [!tip]` | Hot Topics |
| `> [!success]` | Gems |
| `> [!quote]` | Wisdom |
| `> [!example]` | Deep Dive |

- No `#` headings anywhere. No numbered lists. No `For you:` label: the arrow line carries the takeaway.
- Bottom line: 2 or 3 short sentences. First the biggest news, then the day's theme. Does the daily name something that touches his own setup, such as Claude Code, Rai, the vault or the news run? Then add a second paragraph of one sentence. It starts "Closest to home:" and carries its number.
- Every other item is three lines inside its callout, then a bare `>` line before the next item:

```
> **The topic, as a short bold sentence.**
> The explanation: at most two short sentences, about 25 words in all.
> *→ The takeaway for him, in one sentence: what to do or what to watch.*
```

- One number per explanation where it can: the number that carries the point.
- The takeaway is about him. Tie it to his own setup when the daily allows: Rai, Claude Code, his data platforms, his DevOps work, his region. A generic best practice is the last resort.
- Wisdom: the quote in bold inside straight double quotes, cut to its core sentence word for word, then what it means, then the arrow line.
- Deep Dive: the subject in bold, one sentence on what it is, then the arrow line.
- An empty section keeps its callout with the one line `> Nothing today.`

## Words

- Short sentences, one idea each, plain words.
- At most 600 words of text.
- English only. No em or en dashes: use . , : instead. No emojis. The arrow `→` is the one symbol.

## Check once, then stop

1. Re-read the digest against the daily: every number, name and hedge matches.
2. Leak check, which prints nothing: `grep -nE '^#|https?://|@[A-Za-z0-9_]|\[(x|r|hn|gh|sub|m)-[0-9]|—|–|For you' <digest>`.
3. From `~/helm`, `vale --filter='.Name matches "^Rai"' 08-bawaba/digest/YYYY-MM-DD.md` reports no alert.
4. Count the text words. Over 600: cut the weakest News Wire item, then the weakest Gem.
