---
name: deploy
description: >
  Deploy {NAME} to Cloudflare with wrangler. USE WHEN asked to deploy, to preview a deploy, or
  to check what a deploy would upload.
---

# deploy

The deploy is configured by `{DEPLOY_CONFIG}`. Run every command below from `{DEPLOY_DIR}`.

## Steps

1. `mise run verify` is green on the default branch.
2. Dry run: `npx --no-install wrangler deploy --dry-run --outdir "$TMPDIR/wrangler"`. project-init's selftest runs it and fails unless it exits 0. It builds and checks without uploading.
3. Deploy: `npx --no-install wrangler deploy`. A person runs it, because it changes production.

## Failure modes

- `Authentication error`: a person runs `npx wrangler login` once per machine.
- `could not determine executable to run`: wrangler is not installed here. Install the locked dependencies first.
