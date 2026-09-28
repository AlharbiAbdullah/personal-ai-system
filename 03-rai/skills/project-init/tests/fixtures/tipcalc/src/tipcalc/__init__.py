import os
import sys


def tip(bill: float, percent: float) -> float:
    return round(bill * percent / 100, 2)


def main() -> None:
    percent = float(os.environ.get("TIPCALC_DEFAULT_PERCENT", "15"))
    bill = float(sys.argv[1])
    print(f"tip: {tip(bill, percent)}")
