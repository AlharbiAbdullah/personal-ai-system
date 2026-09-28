---
name: go
description: >
  Go coding standards. USE WHEN reviewing or writing Go. Covers error
  handling, packages, goroutines, naming, idiomatic patterns.
---

# Go Standards

## Errors

- **Return `error` as the last return value** — always
- **Check every error** — `if err != nil { return fmt.Errorf("context: %w", err) }`
- **Wrap with `%w`** — preserves the chain for `errors.Is` + `errors.As`
- **Sentinel errors** for expected failure modes: `var ErrNotFound = errors.New("not found")`
- **Custom error types** for errors carrying data: implement the `error` interface
- **No panics** in library code. Panic is for truly unrecoverable state (init failures).
- **Don't ignore errors with `_`** unless there's a comment explaining why

## Naming

- `MixedCaps` for exported names, `mixedCaps` for unexported — never underscores in names
- Short names for short scopes: `i` in a loop, `err` for error, `r` for reader
- Long names for long scopes: package-level vars get descriptive names
- Package names: short, lowercase, no underscores. `utf8`, not `utf8_encoding`
- Avoid stutter: `http.Request` not `http.HTTPRequest`; inside package `http`, just `Request`
- Interface names: ending in `-er` for single-method interfaces (`Reader`, `Writer`); otherwise descriptive (`io.ReadWriter`)

## Packages

- One concept per package — not "utils" or "helpers"
- Package path matches directory name (mostly)
- Dependencies flow inward: `cmd/` → `internal/` → `pkg/`
- `internal/` for types the package author doesn't want exposed
- No circular imports — Go enforces this; if you hit it, your abstraction is wrong

## Goroutines + channels

- **Don't leak goroutines** — every goroutine needs a clear exit path
- **Channels for signaling, mutexes for state** — pick the right primitive
- **`context.Context` everywhere async** — first parameter, always passed down
- **`select` with `ctx.Done()`** for cancellation
- **Buffered channels** only when you have a specific reason (backpressure, fan-out); default unbuffered
- **`sync.WaitGroup` or errgroup** for coordinating parallel work
- **Don't close receiver-only channels** — only the sender closes

## Testing

- Table-driven tests by default
- Test files: `foo_test.go` next to `foo.go`
- `t.Helper()` in test utilities
- `t.Parallel()` where safe
- `testify` is fine but standard library is often enough
- Benchmarks: `BenchmarkX` with `b.ResetTimer()` after setup

## Struct + method style

- Pointer receivers unless the type is small + immutable
- Consistent receivers across methods of a type — don't mix value + pointer receivers
- Zero value should be useful when possible: `var x MyType` should be ready to use
- Constructor `NewX()` returns `*X` when fields need initialization
- Embedding over inheritance when composing types

## Anti-patterns

- Generic `interface{}` / `any` everywhere — Go has real types, use them
- Ignoring errors or wrapping with just `return err` — lose context
- Global state — pass explicitly where possible
- `init()` side effects beyond constant computation
- Overly-clever channel patterns when a mutex would read cleaner
- Naked returns in long functions
- Exported methods that aren't needed externally

## Tooling

- `gofmt` / `goimports` — non-negotiable
- `go vet` — catches common mistakes
- `staticcheck` — stronger linter
- `golangci-lint` — aggregates many linters
- `go test -race` — race detector, run in CI

## Examples

- "Review this Go service for idiom"
- "Is this goroutine leak-safe?"
- "Refactor this error handling to use wrapping"
- "Does this package structure make sense?"
