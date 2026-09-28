---
type: capture
created: <% tp.file.creation_date("YYYY-MM-DD HH:mm") %>
source: <% await tp.system.suggester(["twitter", "linkedin", "github", "blog", "youtube", "podcast", "paper", "conversation", "idea", "other"], ["twitter", "linkedin", "github", "blog", "youtube", "podcast", "paper", "conversation", "idea", "other"]) %>
action: <% await tp.system.suggester(["to-read", "to-try", "to-learn", "to-build"], ["to-read", "to-try", "to-learn", "to-build"]) %>
status: inbox
---

**Tags:** <% tp.frontmatter.action %>

---

# <% tp.file.title %>

<!--
DESTINATION: see 01-inbox/AGENTS.md Routing table (reading -> 07-reading/, curriculum ->
06-learning/, tool/concept -> 10-knowledge/, idea/project -> 09-ideas/ as a Seed, work -> 04-work/).
-->

## What Is It?
<% tp.file.cursor() %>

## Link / Source


## What Problem Does It Solve?


## How Is It Relevant To Me?


## Related To
<!-- Weave links into text above instead of listing here -->


## Next Action
- [ ]

## Notes

