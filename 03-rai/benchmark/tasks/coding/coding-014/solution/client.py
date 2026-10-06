"""Client for the internal reporting API."""

import time

from errors import TransientError
from retry import retry_call


def fetch_report(transport, report_id, *, sleep=time.sleep):
    """Fetch /reports/<report_id> through transport.get(path) -> dict.

    Transient errors are retried (5 attempts, backoff 0.5s doubling up to 4s, honouring
    Retry-After); anything else propagates at once; RetryError when every attempt failed.
    """
    return retry_call(
        lambda: transport.get(f"/reports/{report_id}"),
        attempts=5,
        base_delay=0.5,
        factor=2.0,
        max_delay=4.0,
        retry_on=(TransientError,),
        sleep=sleep,
    )
