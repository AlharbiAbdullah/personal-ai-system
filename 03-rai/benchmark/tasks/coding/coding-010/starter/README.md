# billing

Monthly invoices for the hosted API product. All amounts are integer cents.
`billing.compute_invoice(customer, usage, period)` is called by the invoicing job and by support
tooling; both import it as `from billing import compute_invoice`.

Run the tests with `python -m pytest tests`.
