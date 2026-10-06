from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfoNotFoundError

import pytest
import tzutil

UTC = timezone.utc
NY, LON, LHI = "America/New_York", "Europe/London", "Australia/Lord_Howe"


def utc(*args):
    return datetime(*args, tzinfo=UTC)


def hours(h):
    return timedelta(hours=h)


@pytest.mark.parametrize(
    "naive,zone,offset",
    [
        (datetime(2026, 7, 1, 12, 0), NY, hours(-4)),
        (datetime(2026, 1, 15, 12, 0), NY, hours(-5)),
        (datetime(2026, 3, 8, 1, 59), NY, hours(-5)),
        (datetime(2026, 3, 8, 3, 0), NY, hours(-4)),
        (datetime(2026, 11, 1, 2, 0), NY, hours(-5)),
        (datetime(2026, 3, 29, 2, 0), LON, hours(1)),
        (datetime(2026, 10, 4, 2, 30), LHI, hours(11)),
        (datetime(2026, 6, 1, 9, 0), "Asia/Riyadh", hours(3)),
        (datetime(2026, 6, 1, 9, 0), "Asia/Kolkata", timedelta(hours=5, minutes=30)),
    ],
)
def test_localize_unambiguous(naive, zone, offset):
    got = tzutil.localize(naive, zone)
    assert got.utcoffset() == offset
    assert got.replace(tzinfo=None) == naive
    assert got.astimezone(UTC) == (naive - offset).replace(tzinfo=UTC)


@pytest.mark.parametrize(
    "naive,zone",
    [
        (datetime(2026, 3, 8, 2, 30), NY),
        (datetime(2026, 3, 8, 2, 0), NY),
        (datetime(2026, 3, 29, 1, 30), LON),
        (datetime(2026, 10, 4, 2, 15), LHI),
    ],
)
def test_localize_nonexistent(naive, zone):
    with pytest.raises(tzutil.NonexistentTimeError):
        tzutil.localize(naive, zone)
    assert issubclass(tzutil.NonexistentTimeError, ValueError)


@pytest.mark.parametrize(
    "naive,zone,earlier,later",
    [
        (
            datetime(2026, 11, 1, 1, 30),
            NY,
            utc(2026, 11, 1, 5, 30),
            utc(2026, 11, 1, 6, 30),
        ),
        (
            datetime(2026, 11, 1, 1, 0),
            NY,
            utc(2026, 11, 1, 5, 0),
            utc(2026, 11, 1, 6, 0),
        ),
        (
            datetime(2026, 10, 25, 1, 15),
            LON,
            utc(2026, 10, 25, 0, 15),
            utc(2026, 10, 25, 1, 15),
        ),
        (
            datetime(2026, 4, 5, 1, 45),
            LHI,
            utc(2026, 4, 4, 14, 45),
            utc(2026, 4, 4, 15, 15),
        ),
    ],
)
def test_localize_ambiguous(naive, zone, earlier, later):
    assert tzutil.localize(naive, zone).astimezone(UTC) == earlier
    assert tzutil.localize(naive, zone, ambiguous="earlier").astimezone(UTC) == earlier
    assert tzutil.localize(naive, zone, ambiguous="later").astimezone(UTC) == later
    with pytest.raises(tzutil.AmbiguousTimeError):
        tzutil.localize(naive, zone, ambiguous="raise")
    assert issubclass(tzutil.AmbiguousTimeError, ValueError)


def test_localize_argument_errors():
    with pytest.raises(ValueError):
        tzutil.localize(datetime(2026, 1, 1, 9, 0), NY, ambiguous="first")
    with pytest.raises(ValueError):
        tzutil.localize(datetime(2026, 1, 1, 9, 0, tzinfo=UTC), NY)
    with pytest.raises(ZoneInfoNotFoundError):
        tzutil.localize(datetime(2026, 1, 1, 9, 0), "Mars/Olympus_Mons")


def test_raise_policy_does_not_affect_normal_times():
    got = tzutil.localize(datetime(2026, 11, 2, 1, 30), NY, ambiguous="raise")
    assert got.astimezone(UTC) == utc(2026, 11, 2, 6, 30)


@pytest.mark.parametrize(
    "hhmm,zone,start,days,expected",
    [
        (
            "02:30",
            NY,
            date(2026, 3, 7),
            3,
            [utc(2026, 3, 7, 7, 30), utc(2026, 3, 8, 7, 30), utc(2026, 3, 9, 6, 30)],
        ),
        (
            "01:30",
            NY,
            date(2026, 10, 31),
            3,
            [
                utc(2026, 10, 31, 5, 30),
                utc(2026, 11, 1, 5, 30),
                utc(2026, 11, 2, 6, 30),
            ],
        ),
        (
            "01:30",
            LON,
            date(2026, 3, 28),
            3,
            [utc(2026, 3, 28, 1, 30), utc(2026, 3, 29, 1, 30), utc(2026, 3, 30, 0, 30)],
        ),
        (
            "02:15",
            LHI,
            date(2026, 10, 3),
            3,
            [
                utc(2026, 10, 2, 15, 45),
                utc(2026, 10, 3, 15, 45),
                utc(2026, 10, 4, 15, 15),
            ],
        ),
        (
            "23:59",
            "Asia/Kolkata",
            date(2026, 12, 31),
            2,
            [utc(2026, 12, 31, 18, 29), utc(2027, 1, 1, 18, 29)],
        ),
        ("09:00", NY, date(2026, 1, 1), 0, []),
    ],
)
def test_daily_at(hhmm, zone, start, days, expected):
    got = tzutil.daily_at(hhmm, zone, start, days)
    assert got == expected
    for instant in got:
        assert instant.utcoffset() == timedelta(0)


def test_daily_at_long_range_is_consistent():
    got = tzutil.daily_at("08:00", LON, date(2026, 1, 1), 365)
    assert len(got) == 365
    summer = [g for g in got if g.hour == 7]
    winter = [g for g in got if g.hour == 8]
    assert len(summer) + len(winter) == 365
    assert summer[0] == utc(2026, 3, 29, 7, 0)
    assert summer[-1] == utc(2026, 10, 24, 7, 0)


@pytest.mark.parametrize(
    "hhmm", ["24:00", "7:30", "07:60", "0730", "ab:cd", "07:30:00", ""]
)
def test_daily_at_bad_time(hhmm):
    with pytest.raises(ValueError):
        tzutil.daily_at(hhmm, NY, date(2026, 1, 1), 1)


def test_daily_at_negative_days():
    with pytest.raises(ValueError):
        tzutil.daily_at("09:00", NY, date(2026, 1, 1), -1)


@pytest.mark.parametrize(
    "start,end,zone,expected",
    [
        (datetime(2026, 3, 8, 0, 0), datetime(2026, 3, 8, 4, 0), NY, hours(3)),
        (datetime(2026, 11, 1, 0, 0), datetime(2026, 11, 1, 3, 0), NY, hours(4)),
        (datetime(2026, 11, 1, 1, 30), datetime(2026, 11, 1, 1, 30), NY, hours(0)),
        (datetime(2026, 10, 24, 12, 0), datetime(2026, 10, 25, 12, 0), LON, hours(25)),
        (datetime(2026, 10, 25, 12, 0), datetime(2026, 10, 24, 12, 0), LON, hours(-25)),
        (
            datetime(2026, 10, 3, 12, 0),
            datetime(2026, 10, 4, 12, 0),
            LHI,
            timedelta(hours=23, minutes=30),
        ),
        (
            datetime(2026, 7, 1, 8, 0),
            datetime(2026, 7, 1, 17, 45),
            "Asia/Riyadh",
            timedelta(hours=9, minutes=45),
        ),
    ],
)
def test_elapsed_is_real_time(start, end, zone, expected):
    assert tzutil.elapsed(start, end, zone) == expected


def test_elapsed_rejects_nonexistent():
    with pytest.raises(tzutil.NonexistentTimeError):
        tzutil.elapsed(datetime(2026, 3, 8, 2, 30), datetime(2026, 3, 8, 5, 0), NY)


@pytest.mark.parametrize(
    "instant,zone,expected",
    [
        (utc(2026, 3, 8, 7, 30), NY, "2026-03-08T03:30:00-04:00"),
        (utc(2026, 3, 8, 6, 59, 59), NY, "2026-03-08T01:59:59-05:00"),
        (utc(2026, 1, 1, 0, 0), "Asia/Kolkata", "2026-01-01T05:30:00+05:30"),
        (utc(2026, 10, 3, 15, 45), LHI, "2026-10-04T02:45:00+11:00"),
        (
            datetime(2026, 1, 1, 0, 0, 0, 999999, tzinfo=UTC),
            "Asia/Riyadh",
            "2026-01-01T03:00:00+03:00",
        ),
        (
            datetime(2026, 6, 1, 12, 0, tzinfo=timezone(hours(3))),
            LON,
            "2026-06-01T10:00:00+01:00",
        ),
    ],
)
def test_format_local(instant, zone, expected):
    assert tzutil.format_local(instant, zone) == expected


def test_format_local_rejects_naive():
    with pytest.raises(ValueError):
        tzutil.format_local(datetime(2026, 1, 1, 12, 0), NY)
