"""Errors raised by the transport layer."""


class TransientError(Exception):
    """A temporary failure; the same request may succeed later."""


class RateLimited(TransientError):
    """The server asked us to wait `retry_after` seconds before trying again."""

    def __init__(self, retry_after: float, message: str = "rate limited") -> None:
        super().__init__(message)
        self.retry_after = retry_after


class PermanentError(Exception):
    """Retrying the same request will not help."""
