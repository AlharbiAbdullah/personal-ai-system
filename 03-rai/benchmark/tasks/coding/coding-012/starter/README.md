# Bank file ingest

The bank drops transaction exports as CSV files into an `inbox/` folder. The drop job sometimes
re-sends a file, sometimes under a new name, and the ingest box reboots without warning, so the
ingest step must be safe to run again at any time. `sample-root/` shows the folder layout with one
file waiting in the inbox.
