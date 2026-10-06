"""Retry with exponential backoff, optional full jitter and Retry-After support."""

from __future__ import annotations

import functools
import random
import time
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


class RetryError(Exception):
    """Every attempt failed with a retryable exception."""

    def __init__(self, attempts: int, last_exception: BaseException) -> None:
        super().__init__(f"gave up after {attempts} attempts: {last_exception!r}")
        self.attempts = attempts
        self.last_exception = last_exception


def _retry_after(exc: BaseException) -> float | None:
    value = getattr(exc, "retry_after", None)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        return None
    return float(value)


def retry_call(
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    base_delay: float = 0.1,
    factor: float = 2.0,
    max_delay: float = 5.0,
    jitter: bool = False,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
    giveup: Callable[[BaseException], bool] | None = None,
    on_retry: Callable[[int, BaseException, float], Any] | None = None,
    sleep: Callable[[float], Any] = time.sleep,
    rng: random.Random | None = None,
) -> T:
    if attempts < 1 or base_delay < 0 or factor < 1 or max_delay < 0:
        raise ValueError(
            "need attempts >= 1, base_delay >= 0, factor >= 1, max_delay >= 0"
        )
    rng = rng or random.Random()
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except retry_on as exc:
            if giveup is not None and giveup(exc):
                raise
            if attempt == attempts:
                raise RetryError(attempts, exc) from exc
            delay = min(max_delay, base_delay * factor ** (attempt - 1))
            server_delay = _retry_after(exc)
            if server_delay is not None:
                delay = min(max_delay, server_delay)
            elif jitter:
                delay = rng.uniform(0, delay)
            if on_retry is not None:
                on_retry(attempt, exc, delay)
            sleep(delay)
    raise AssertionError("unreachable")


def retry(**options: Any) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def decorate(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return retry_call(lambda: func(*args, **kwargs), **options)

        return wrapper

    return decorate
