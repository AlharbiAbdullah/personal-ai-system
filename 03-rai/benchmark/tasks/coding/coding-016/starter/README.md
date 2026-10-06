# CSV validation

Partner teams upload CSV extracts that land in the warehouse. Each extract has a small JSON schema
(`schema.json` is the one for `data/users.csv`). We want a validator that runs in CI before a load
and tells the uploader exactly which cells are wrong.
