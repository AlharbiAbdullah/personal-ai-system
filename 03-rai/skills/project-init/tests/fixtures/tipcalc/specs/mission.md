<!-- mission.md: why the product exists, for whom, and what is in scope. Living, changed only on plan/ branches. No line cap. -->
# tipcalc

## One-liner
Tiny CLI that prints the tip for a bill.

## Who it is for
People at a terminal who want the tip for a bill without opening a calculator.

## Problem
Working out a tip by hand is slow and easy to get wrong.

## Why now
The happy path works, but every other input ends in a Python traceback.

## Scope
- In: the tip for one bill, at the default percent or the one set in TIPCALC_DEFAULT_PERCENT.
- Out: currency conversion, receipts, a GUI.

## Success
`tipcalc <bill>` prints the right tip, and every bad input gets a one-line error instead of a traceback.

## Glossary
- bill: the amount before the tip, given as the first argument.
- percent: the tip percent; TIPCALC_DEFAULT_PERCENT sets it, and 15 is the default.
