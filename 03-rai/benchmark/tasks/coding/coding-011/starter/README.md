# Access log stats

The API gateway writes one line per request to `logs/access.log`, in a combined-log style format
with the request duration in seconds appended. We want per-endpoint latency and error numbers
without shipping the logs to a SaaS tool.
