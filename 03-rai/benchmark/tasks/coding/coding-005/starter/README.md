# Schema migrations

The service keeps its SQLite schema as numbered SQL files in `migrations/`. Until now someone ran
them by hand with the `sqlite3` shell. We want a small runner that knows what is applied, applies
the rest in order and refuses to run when history was edited.
