# Sales reports

`salesdb.py` creates the `sales` table and can fill it with demo data:

    python -c "import sqlite3, salesdb; c = sqlite3.connect('demo.db'); salesdb.create(c); salesdb.load(c, salesdb.demo_rows()); c.commit()"

`reports.py` holds the reports the regional managers asked for. They are not written yet.
