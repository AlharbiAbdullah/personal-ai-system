# Customer dimension history

Every month the CRM sends a full snapshot of all active customers (`data/snapshot-*.json`). The
warehouse keeps the customer dimension as a type 2 slowly changing dimension, so reports can ask
"what did we know about this customer on that day?". The warehouse is SQLite, used through the
stdlib `sqlite3` module.
