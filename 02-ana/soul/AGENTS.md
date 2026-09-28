# Soul Notes — Claude Instructions

When the user wants to add a note to `soul/`:

1. **Ask questions first.** Before writing anything, use `AskUserQuestion` to ask multiple questions about the topic. The goal is to help the user think deeply and cover all aspects so nothing gets missed. Ask about the why, the experience behind it, what changed, what it means now. Keep asking until the topic feels fully explored.
2. **Rewrite, don't expand.** Take what the user said and rewrite it clearly: fix spelling, fix grammar, rephrase for clarity. Do not make it longer. Do not make it shorter. Just rewrite what was said.
3. **No commentary.** Don't add your own thoughts, interpretations, or extra ideas. The user's thinking is the content.
4. **English only.** The user may write in Arabic. Always rewrite in English. Never write in any other language.
5. **Use the Soul Note template** from `12-system/templates/Soul Note.md`.
