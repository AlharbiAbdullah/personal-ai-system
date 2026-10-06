# Event stream summary

The mobile app ships events as JSON Lines (`data/events.jsonl`). `aggregate.py` turns them into a
per-day and per-user summary for the product dashboard. It was a quick first version; product
reports that its numbers are wrong (days split at the wrong hour, revenue off by a cent, replayed
events counted twice, and it crashes on some lines).
