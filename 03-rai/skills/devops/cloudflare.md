# Cloudflare

Deploy and manage Cloudflare Workers, MCP remote servers, and Pages.
All deployments use OAuth-based authentication (no API tokens in code).

## Deployment Types

### Workers
Serverless functions at the edge.

1. Write the Worker script (ES modules format)
2. Configure `wrangler.toml` with bindings (KV, D1, R2, etc.)
3. Deploy with `wrangler deploy`

### MCP Servers
Remote MCP servers running on Workers.

1. Scaffold with MCP server template
2. Define tools and resources
3. Configure OAuth for authentication
4. Deploy as a Worker with Durable Objects if needed

### Pages
Static sites and full-stack apps.

1. Build the project (framework-specific)
2. Configure `wrangler.toml` or connect git repo
3. Deploy with `wrangler pages deploy`

## Naming and URL Structure

- Worker names: lowercase, hyphens, descriptive. Example: `api-data-proxy`
- URLs: `[worker-name].[subdomain].workers.dev`
- Pages: `[project-name].pages.dev`
- Custom domains: configure in dashboard or via wrangler

## OAuth Setup

1. Configure OAuth provider in Worker
2. Set client ID/secret as Worker secrets (`wrangler secret put`)
3. Never hardcode credentials in source

## Process

1. **Determine type**: Worker, MCP server, or Pages
2. **Scaffold**: Create project structure with wrangler
3. **Implement**: Write code, configure bindings
4. **Test locally**: `wrangler dev` for local development
5. **Deploy**: `wrangler deploy` or `wrangler pages deploy`
6. **Verify**: Hit the deployed URL to confirm

## Examples

- "Deploy a Worker that proxies API requests"
- "Set up an MCP server on Cloudflare"
- "Deploy this React app to Cloudflare Pages"
- "Add a KV namespace to my existing Worker"
