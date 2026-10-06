import random

import client
import errors
import pytest
from retry import RetryError, retry, retry_call


class Flaky:
    """Callable that raises the scripted exceptions, then returns the value."""

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def __call__(self):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class Sleeps(list):
    def __call__(self, seconds):
        self.append(seconds)


def test_first_success_does_not_sleep():
    sleep = Sleeps()
    fn = Flaky("ok")
    assert retry_call(fn, sleep=sleep) == "ok"
    assert fn.calls == 1 and sleep == []


def test_falsy_results_are_results():
    assert retry_call(Flaky(None), sleep=Sleeps()) is None
    assert retry_call(Flaky(0), sleep=Sleeps()) == 0


def test_retries_with_default_exponential_delays():
    sleep = Sleeps()
    fn = Flaky(OSError("a"), OSError("b"), 42)
    assert retry_call(fn, sleep=sleep) == 42
    assert fn.calls == 3
    assert sleep == pytest.approx([0.1, 0.2])


def test_gives_up_with_retry_error():
    sleep = Sleeps()
    last = TimeoutError("4th")
    fn = Flaky(TimeoutError("1st"), TimeoutError("2nd"), TimeoutError("3rd"), last)
    with pytest.raises(RetryError) as err:
        retry_call(fn, attempts=4, base_delay=0.5, factor=2.0, sleep=sleep)
    assert fn.calls == 4
    assert sleep == pytest.approx([0.5, 1.0, 2.0])
    assert err.value.attempts == 4
    assert err.value.last_exception is last
    assert err.value.__cause__ is last


def test_single_attempt_never_sleeps():
    sleep = Sleeps()
    with pytest.raises(RetryError) as err:
        retry_call(Flaky(OSError("x")), attempts=1, sleep=sleep)
    assert err.value.attempts == 1
    assert sleep == []


def test_delays_are_capped():
    sleep = Sleeps()
    with pytest.raises(RetryError):
        retry_call(
            Flaky(*[OSError()] * 6),
            attempts=6,
            base_delay=1.0,
            factor=3.0,
            max_delay=5.0,
            sleep=sleep,
        )
    assert sleep == pytest.approx([1.0, 3.0, 5.0, 5.0, 5.0])


def test_factor_one_is_constant_delay():
    sleep = Sleeps()
    retry_call(
        Flaky(OSError(), OSError(), "ok"), base_delay=0.25, factor=1.0, sleep=sleep
    )
    assert sleep == pytest.approx([0.25, 0.25])


def test_non_retryable_exception_propagates_at_once():
    sleep = Sleeps()
    boom = ValueError("bug")
    fn = Flaky(boom, "never")
    with pytest.raises(ValueError) as err:
        retry_call(fn, retry_on=(KeyError, OSError), sleep=sleep)
    assert err.value is boom
    assert fn.calls == 1 and sleep == []


def test_retry_on_accepts_subclasses():
    sleep = Sleeps()
    assert (
        retry_call(
            Flaky(ConnectionResetError(), "ok"), retry_on=(OSError,), sleep=sleep
        )
        == "ok"
    )


def test_keyboard_interrupt_is_never_retried():
    fn = Flaky(KeyboardInterrupt(), "never")
    with pytest.raises(KeyboardInterrupt):
        retry_call(fn, sleep=Sleeps())
    assert fn.calls == 1


def test_giveup_stops_immediately():
    sleep = Sleeps()
    fatal = OSError("fatal: disk gone")
    fn = Flaky(OSError("flaky"), fatal, "never")
    with pytest.raises(OSError) as err:
        retry_call(fn, giveup=lambda exc: "fatal" in str(exc), sleep=sleep)
    assert err.value is fatal
    assert fn.calls == 2
    assert sleep == pytest.approx([0.1])


@pytest.mark.parametrize("seed", [0, 7, 1234])
def test_full_jitter_uses_the_given_rng(seed):
    sleep = Sleeps()
    with pytest.raises(RetryError):
        retry_call(
            Flaky(*[OSError()] * 5),
            attempts=5,
            base_delay=1.0,
            factor=2.0,
            max_delay=6.0,
            jitter=True,
            rng=random.Random(seed),
            sleep=sleep,
        )
    replay = random.Random(seed)
    assert sleep == pytest.approx([replay.uniform(0, d) for d in [1.0, 2.0, 4.0, 6.0]])
    assert all(0 <= s <= 6.0 for s in sleep)


def test_retry_after_overrides_backoff():
    sleep = Sleeps()
    fn = Flaky(errors.RateLimited(2.5), errors.RateLimited(100), OSError(), "ok")
    assert (
        retry_call(
            fn,
            attempts=5,
            base_delay=0.1,
            max_delay=10.0,
            jitter=True,
            rng=random.Random(1),
            sleep=sleep,
        )
        == "ok"
    )
    assert sleep[:2] == pytest.approx([2.5, 10.0])
    assert 0 <= sleep[2] <= 0.4


@pytest.mark.parametrize("bad", [-1, True, "3", None])
def test_invalid_retry_after_is_ignored(bad):
    exc = OSError("x")
    exc.retry_after = bad
    sleep = Sleeps()
    retry_call(Flaky(exc, "ok"), base_delay=0.3, sleep=sleep)
    assert sleep == pytest.approx([0.3])


def test_on_retry_is_called_before_each_sleep():
    events = []
    first, second = OSError("1"), OSError("2")

    def on_retry(attempt, exc, delay):
        events.append(("retry", attempt, exc, delay))

    def sleep(seconds):
        events.append(("sleep", seconds))

    retry_call(
        Flaky(first, second, "ok"), base_delay=1.0, on_retry=on_retry, sleep=sleep
    )
    assert events == [
        ("retry", 1, first, 1.0),
        ("sleep", 1.0),
        ("retry", 2, second, 2.0),
        ("sleep", 2.0),
    ]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"attempts": 0},
        {"attempts": -2},
        {"base_delay": -0.1},
        {"factor": 0.5},
        {"max_delay": -1},
    ],
)
def test_invalid_settings(kwargs):
    fn = Flaky("ok")
    with pytest.raises(ValueError):
        retry_call(fn, sleep=Sleeps(), **kwargs)
    assert fn.calls == 0


def test_decorator_passes_arguments_and_keeps_metadata():
    sleep = Sleeps()
    seen = []

    @retry(attempts=3, base_delay=0.2, retry_on=(OSError,), sleep=sleep)
    def load(path, *, mode="r"):
        """Load something."""
        seen.append((path, mode))
        if len(seen) < 3:
            raise OSError("busy")
        return f"{path}:{mode}"

    assert load("a.txt", mode="rb") == "a.txt:rb"
    assert seen == [("a.txt", "rb")] * 3
    assert sleep == pytest.approx([0.2, 0.4])
    assert load.__name__ == "load"
    assert load.__doc__ == "Load something."


class Transport:
    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.paths = []

    def get(self, path):
        self.paths.append(path)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def test_client_retries_transient_errors():
    sleep = Sleeps()
    t = Transport(
        errors.TransientError("502"), errors.TransientError("503"), {"id": "r-9"}
    )
    assert client.fetch_report(t, "r-9", sleep=sleep) == {"id": "r-9"}
    assert t.paths == ["/reports/r-9"] * 3
    assert sleep == pytest.approx([0.5, 1.0])


def test_client_gives_up_after_five_attempts():
    sleep = Sleeps()
    t = Transport(*[errors.TransientError("down")] * 6)
    with pytest.raises(RetryError) as err:
        client.fetch_report(t, 7, sleep=sleep)
    assert err.value.attempts == 5
    assert len(t.paths) == 5
    assert sleep == pytest.approx([0.5, 1.0, 2.0, 4.0])


def test_client_permanent_and_unexpected_errors_are_not_retried():
    sleep = Sleeps()
    t = Transport(errors.PermanentError("404"), {"id": "x"})
    with pytest.raises(errors.PermanentError):
        client.fetch_report(t, "x", sleep=sleep)
    t = Transport(KeyError("bug"), {"id": "x"})
    with pytest.raises(KeyError):
        client.fetch_report(t, "x", sleep=sleep)
    assert sleep == []


def test_client_honours_retry_after_up_to_the_cap():
    sleep = Sleeps()
    t = Transport(errors.RateLimited(3), errors.RateLimited(30), {"id": "ok"})
    assert client.fetch_report(t, "ok", sleep=sleep) == {"id": "ok"}
    assert sleep == pytest.approx([3.0, 4.0])
