# Order export cleanup

`data/orders_raw.csv` is a raw export from the web shop. The rows are messy: stray spaces,
mixed-case emails, amounts with a dollar sign and thousands separators, several date formats and
free-text statuses. The finance warehouse needs one clean file plus a file of rejected rows with
the reason for each rejection.
