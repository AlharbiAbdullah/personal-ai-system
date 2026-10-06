# tzutil

The scheduler stores job times as local wall-clock times plus an IANA zone name, and keeps breaking
twice a year when daylight saving time starts or ends. `tzutil` is the one place that turns local
wall times into instants, using the standard library `zoneinfo` module.

Teams that use it run jobs in New York, London, Riyadh, Kolkata and on Lord Howe Island (whose DST
shift is 30 minutes, not an hour).
