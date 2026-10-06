# Customer merge

Customers live in two systems: the CRM (export: `data/crm.csv`) and billing (export:
`data/billing.json`). The same person often appears several times, with emails in different
spellings and phone numbers in different formats. We need one golden record per person.
