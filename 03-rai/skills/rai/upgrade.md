---
name: upgrade
description: >
  System improvement extraction and recommendation.
  USE WHEN the user wants to improve Rai, review new AI capabilities,
  or find ways to upgrade the agent system.
---

# Rai Upgrade

Extract improvement opportunities from multiple sources and rank them
by impact on the Rai system. Three parallel analysis threads converge
into a prioritized recommendation list.

## Three Threads

### 1. User Context Analysis
Query ChromaDB for recent friction:
- Run `/recall --search "stuck OR error OR manual OR painful OR repeated"` to surface friction phrases
- Look for sessions tagged `outcome: blocked` or with `open:` items unresolved across multiple sessions
- Check `~/helm/03-rai/semantic-memory/learned.md` (ACTIVE preferences) and `identity/learned.md` for recent feedback patterns

### 2. Source Collection
- Anthropic release notes: https://docs.claude.com/en/release-notes (use WebFetch)
- Claude Code releases: https://github.com/anthropics/claude-code/releases
- GitHub Trending agents/MCP: https://github.com/trending?since=weekly (filter for `mcp`, `agent`, `claude`)
- HN top items in last 7 days mentioning Claude/MCP/agents
- r/ClaudeAI weekly highlights

### 3. Internal Reflections
- Inventory every skill + sub-skill: `find ~/helm/03-rai/skills -maxdepth 2 -name "*.md" | sort`
- Audit for: missing USE WHEN triggers, stale references, last-touched > 90 days
- Check `~/helm/03-rai/skills/GAPS.md` for documented gaps
- Audit hooks: `ls ~/helm/03-rai/hooks/` — are any failing? check error logs
- Run `/recall --search "friction OR manual OR repeated"` to surface pain

## Process

1. **Scan**: Run all three threads in parallel (parallel WebFetch / Bash / Glob calls)
2. **Discover**: Collect findings into a unified list
3. **Classify**: Tag each as `capability` (new ability), `performance` (faster/cheaper), `UX` (smoother flow), or `config` (settings drift)
4. **Score**: Impact × (1 / Effort). Use the matrix:

   | Impact | Score | Definition |
   |--------|-------|------------|
   | High | 3 | Eliminates a recurring pain point or unlocks a new workflow |
   | Medium | 2 | Improves an existing flow noticeably |
   | Low | 1 | Polish, marginal improvement |

   | Effort | Divisor | Definition |
   |--------|---------|------------|
   | Easy | 1 | <1 hour, single-file edit |
   | Medium | 2 | 1–4 hours, multi-file or new skill |
   | Hard | 4 | >4 hours, architectural change |

   Final score = Impact / Effort. Higher is better.

5. **Recommend**: Present top 5–10 sorted by score with rationale
6. **Plan**: For approved items, run `/grill "<item>"`. In helm it writes a decisions and plan pair under `.agent/`, with a `-<slug>` suffix when another task's pair is already there, and `/compile <slug>` carries it out.

## Output

- Discoveries: raw findings from each thread
- Ranked recommendations: sorted by impact-to-effort score
- Implementation plan for approved items

### Sample output

```
RAI UPGRADE — 2026-04-22

## Top recommendations (score = impact / effort)

1. [score 3.0] Add /multi-file-research skill
   Impact: HIGH (recurring need to gather across vault folders)
   Effort: EASY (~30 min, one new skill file)
   Why: Last 5 sessions involved manual multi-folder grep

2. [score 1.5] Migrate to Sonnet 4.6 in news-digest
   Impact: MEDIUM (faster digest generation)
   Effort: EASY (config change in skill frontmatter)
```

## Examples

- "Upgrade Rai: what improvements should we make?"
- "Check for new Anthropic features we should adopt"
- "Review our skills for gaps and outdated patterns"
- "What MCP tools are we missing?"
