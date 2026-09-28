# Explain Simply

Make a complex idea land by showing what it actually is and actually does, then building
up from there. John does not keep a label or an analogy on its own. It has to make
sense at the mechanism level first. Analogy is a memory aid offered after the mechanism,
never the lead.

## Structure

1. **One-sentence summary** - What is it, in plain English?
2. **Mechanism** - What is it made of, what does it do, at a level he could check himself
   (a file on disk, a process, a call over the network, a lock, a row in a table). This is
   the step that makes it click. Never skip it or jump past it to a comparison.
3. **Diagram** - Draw the real mechanism, not a stand-in for it.
4. **Step-by-step** - Walk through how it works, in order.
5. **Analogy, optional, last** - Once the mechanism is understood, a comparison to something
   familiar can peg it in memory. If he is still confused at this point, the gap is in the
   mechanism: go one level more concrete, do not add an analogy.
6. **Check** - "Does this make sense?" or "Want me to go deeper?"

## Diagram Types

Pick the right diagram for the concept:

### Flow (for processes)
```
Input → Process → Output

Request → Validate → Save → Response
```

### Layers (for stacks/hierarchy)
```
┌─────────────────┐
│   Frontend      │
├─────────────────┤
│   API Layer     │
├─────────────────┤
│   Database      │
└─────────────────┘
```

### Relationship (for connections)
```
    ┌───────┐
    │ User  │
    └───┬───┘
        │ has many
        ▼
    ┌───────┐
    │ Posts │
    └───────┘
```

### Before/After (for transformations)
```
BEFORE          AFTER
───────         ─────
[1,2,3]   →    [2,4,6]
 raw           doubled
```

### Timeline (for sequences)
```
1. User clicks login
       ↓
2. Frontend sends credentials
       ↓
3. Backend validates
       ↓
4. Token returned
       ↓
5. User redirected
```

## Analogy Patterns

For step 5 only, after the mechanism has landed. Never open with one of these.

| Concept | Analogy |
|---------|---------|
| API | Waiter between you and the kitchen |
| Database index | Book index - jump to page instead of reading everything |
| Cache | Keeping milk on counter instead of fridge - faster but expires |
| Queue | Line at coffee shop - first in, first out |
| Stack | Plates - last on, first off |
| Recursion | Russian nesting dolls - same thing inside itself |
| Docker | Shipping container - same box works everywhere |
| Git branch | Parallel universe - experiment without affecting main timeline |

## Rules

1. **Mechanism before analogy** - A bare analogy or label is unfinished, not a stopping point.
2. **No jargon** - If you must use a technical term, define it on first use.
3. **Concrete over abstract** - Specific examples, not general descriptions.
4. **One concept at a time** - Add one more only after the previous one landed.
5. **Check understanding** - Pause and ask before going deeper.

## Example

**User:** "How does async/await work?"

**Response:**

Async/await lets one program make progress on other work while it waits on something slow.

**Mechanism:**

```
SYNC (blocking)           ASYNC (non-blocking)
─────────────────         ──────────────────────
Start request             Start request
   ↓                         ↓
Wait... wait...           Do other stuff
   ↓                         ↓
Wait... wait...           Do more stuff
   ↓                         ↓
Response arrives          Response arrives ← notified
   ↓                         ↓
Continue                  Continue
```

**How it works:**
1. `await` hands control back to the event loop, a single loop that owns every task.
2. The loop runs whichever other task is ready. Nothing runs in parallel: one task at a
   time, switching only at `await` points.
3. When the awaited result arrives, the loop resumes the paused task where it left off.

**Analogy, last:** like a restaurant with one waiter. He takes an order and, instead of
standing at the kitchen door until it is ready, serves other tables and comes back when the
kitchen calls. One waiter, many tables, never two at once. Offered only because the
mechanism above already carries it.

Does this make sense, or want me to show a code example?

## Failure Mode

If he is still confused after the mechanism and the diagram, decompose further: one level
more concrete, not a different analogy. An analogy patches over a gap; it does not close one.
If an analogy was offered before the mechanism and did not land, that is the exact failure
this skill exists to prevent. Go back and show the real thing.
