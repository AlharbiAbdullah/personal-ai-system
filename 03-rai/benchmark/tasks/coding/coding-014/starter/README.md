# Reporting API client

`client.fetch_report` pulls finished reports from the internal reporting API through a transport
object (`transport.get(path) -> dict`). The API is flaky under load: it fails with temporary
errors, sometimes asks callers to slow down (HTTP 429 with a Retry-After header, surfaced as
`errors.RateLimited`), and some failures are permanent. The current retry loop retries everything,
waits a fixed second and silently returns `None` when it gives up.
