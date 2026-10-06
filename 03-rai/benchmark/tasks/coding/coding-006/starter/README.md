# Log rotation

The ingest box writes `*.log` files into one directory and never rotates them. We want a small
bash script that cron can run nightly. `sample-logs/` has a few files to try it on.
