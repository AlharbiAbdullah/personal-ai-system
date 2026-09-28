---
type: learning
created: <% tp.file.creation_date("YYYY-MM-DD HH:mm") %>
category: <% await tp.system.suggester(["tool", "framework", "concept", "book", "course", "language"], ["tool", "framework", "concept", "book", "course", "language"]) %>
status: <% await tp.system.suggester(["queued", "in-progress", "completed", "paused"], ["queued", "in-progress", "completed", "paused"]) %>
priority: <% await tp.system.suggester(["high", "medium", "low"], ["high", "medium", "low"]) %>
---

**Tags:** learning, <% tp.frontmatter.category %>

---

# <% tp.file.title %>

<!--
DESTINATION: 06-learning/
When completed, fold key insights into the matching 10-knowledge/ topic note.
-->

## What Is It?
<% tp.file.cursor() %>

## Why Learn This?


## Learning Goals
- [ ]

## Resources
-

## Progress Log

### <% tp.date.now("YYYY-MM-DD") %>
- Started:

## Key Takeaways
<!-- Fold these into the matching 10-knowledge/ topic note when done -->

