---
name: audit-moc
description: Check a MOC for drift — missing notes it should link, broken wiki-links, coverage gaps
allowed-tools: Read, Bash, AskUserQuestion
---

# Audit MOC

MOC drift is the failure mode. A MOC that doesn't keep up with its topic is worse than no MOC.

## Instructions

### Step 1: Identify MOC

Ask John which MOC (or list `~/helm/10-knowledge/_mocs/*.md`).

Read the MOC file. Extract all wiki-links.

### Step 2: Find its topic cluster

From the MOC's frontmatter `domain` and body content, determine what topic cluster it represents (e.g., "AI / LLMs", "Data Engineering").

Locate the corresponding folder: `~/helm/10-knowledge/{domain}/`.

### Step 3: List notes in the cluster

```bash
ls ~/helm/10-knowledge/{domain}/*.md
```

### Step 4: Compare

For each note in the folder:
- Is it linked from the MOC? If not → missing link.

For each wiki-link in the MOC:
- Does the target note exist? If not → broken link.

For each major concept the topic implies (hint: use WebSearch if uncertain):
- Is there a note covering it? If not → coverage gap.

### Step 5: Audit Agent Breadcrumbs

Read the MOC's `## Agent Breadcrumbs` section (if present). Are the breadcrumbs still current, or do they reference deleted/moved files?

### Step 6: Report

```markdown
# MOC Audit: {moc-name}

## Missing links
- `[[Note A]]` (exists in folder, not linked from MOC)
- `[[Note B]]` (exists, not linked)

## Broken links
- `[[Deleted Note]]` — target missing. Remove or update.
- `[[Renamed Thing]]` — target missing. Check if it was renamed.

## Coverage gaps
- No note on {subtopic X}. Consider: create via `/knowledge new-topic-note`.

## Breadcrumbs
- Breadcrumb from YYYY-MM-DD references `Note Z` which no longer exists. Prune.

## Overall
{up-to-date | needs N fixes | major drift}
```

### Step 7: Offer to fix

For missing links: offer to add them to the MOC. John confirms.
For broken links: offer to remove or propose replacements.
For coverage gaps: offer to scaffold via `/knowledge new-topic-note`.

## Rules

- Never auto-add links without confirmation — some notes may be intentionally excluded.
- Never auto-delete broken links without confirmation — the target may have been renamed.
- Keep breadcrumbs honest. Stale breadcrumbs mislead future sessions.
