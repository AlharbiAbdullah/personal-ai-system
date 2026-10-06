"""Client for the internal reporting API."""

import time


def fetch_report(transport, report_id, *, sleep=time.sleep):
    """Fetch /reports/<report_id> through transport.get(path) -> dict."""
    for _ in range(3):
        try:
            return transport.get(f"/reports/{report_id}")
        except Exception:
            sleep(1)
    return None
