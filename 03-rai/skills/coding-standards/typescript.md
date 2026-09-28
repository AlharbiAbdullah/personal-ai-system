---
name: typescript
description: >
  TypeScript / JavaScript coding standards. USE WHEN reviewing or writing
  TS/JS code. Covers types, modules, naming, error handling, async patterns.
---

# TypeScript / JavaScript Standards

## Types

- **Strict mode ON** in `tsconfig.json`: `strict: true`, `noUncheckedIndexedAccess: true`, `exactOptionalPropertyTypes: true`
- **No `any`** — use `unknown` + type guards, or reach for the real type
- **Prefer `interface` for object shapes**, `type` for unions/utilities
- **Narrow with `as const`** for literal objects + arrays when widening is wrong
- **Return types on exported functions** — explicit, not inferred
- **Discriminated unions** over flag fields: `type Result = { ok: true; value: T } | { ok: false; error: E }`
- **Branded types** for IDs: `type UserId = string & { readonly __brand: 'UserId' }`

## Modules

- **ESM everywhere** — no `require`, no CommonJS
- **Barrel files (`index.ts`) sparingly** — only at package boundaries; not in every folder
- **Explicit imports**: `import { foo } from './x'`, not `import * as X`
- **Path aliases** via `tsconfig.json` `paths:` — `@lib/...` instead of `../../../lib/...`
- **No circular imports** — if you have one, a shared types file is the usual fix

## Naming

- `camelCase` variables + functions
- `PascalCase` types, classes, interfaces, enums, React components
- `SCREAMING_SNAKE_CASE` module-level constants
- `kebab-case` filenames (except React components: `PascalCase.tsx`)
- Boolean vars start with `is`, `has`, `can`, `should`
- Event handlers start with `handle` (internal) or `on` (prop)

## Async

- `async/await` over `.then()` chains
- `Promise.all` for independent parallel ops; `Promise.allSettled` when some may fail
- Always await or return — never forget to handle the promise
- `AbortSignal` for cancellable work (fetch, timeouts)
- No `async` in loops — batch with `Promise.all` or process sequentially with `for...of`

## Errors

- Throw `Error` (or subclass), not strings
- Custom error classes for distinct failure modes
- Never `catch` + silently return — log, rethrow, or convert to a Result type
- Validate at the edge (incoming API / parsed JSON) with Zod or similar; trust internal types

## React / Next.js specifics (when applicable)

- Function components + hooks, no class components in new code
- `useState` for local UI, `useReducer` for state machines, Zustand/Jotai for cross-tree
- Memoization: `useMemo` / `useCallback` only for measured perf wins, not prophylactically
- Server components for data, client components for interaction
- Error boundaries at route roots + anywhere third-party code could throw

## Tooling

- **ESLint** + **typescript-eslint** — strict rules, fix-on-save
- **Prettier** for formatting — no style debates
- **Vitest** or **Jest** for tests
- **pnpm** preferred over npm/yarn for monorepos + disk efficiency
- **tsc --noEmit** in CI as type gate

## Anti-patterns

- `any` as an escape hatch
- `!` non-null assertion without checking (only OK when type system can't know, rare)
- Mutating props / state — always produce new objects
- Deeply nested ternaries — extract to a function or early returns
- `JSON.parse` without `try/catch` or type validation
- Default exports in libraries — named exports play better with refactoring

## Examples

- "Review this TS file against standards"
- "Fix the types in src/api/client.ts"
- "Is this React component idiomatic?"
- "Migrate this JS file to TS"
