---
name: rust
description: >
  Rust coding standards. USE WHEN reviewing or writing Rust. Covers
  ownership, traits, error handling, idioms, common gotchas.
---

# Rust Standards

## Ownership + borrowing

- Prefer borrowing (`&T`) over cloning unless cloning is cheap
- Avoid `.clone()` as a reflex — often a sign the ownership model needs rethinking
- Use `Rc<T>` for shared ownership in single-threaded code, `Arc<T>` for multi-threaded
- `Cow<'_, T>` when you sometimes own and sometimes borrow
- `&mut T` only when you genuinely mutate — many APIs accept `&T` via interior mutability (`RefCell`, `Mutex`)

## Errors

- **`Result<T, E>`** for recoverable errors, `panic!` only for unrecoverable bugs
- **`?` operator** for propagation — the default idiom
- **Custom error enums** for library code — variants per failure mode
- **`thiserror`** for ergonomic error derives in libraries
- **`anyhow`** for applications where error type doesn't need to be user-facing
- **Never swallow errors** — `.ok()` / `.unwrap_or(...)` only when the fallback is truly correct

## Traits

- **Prefer `impl Trait` in return position** for opaque types
- **`dyn Trait`** for runtime polymorphism; accept the vtable cost
- **Common derives**: `Debug`, `Clone`, `PartialEq`, `Eq`, `Hash` where applicable
- **`From`/`Into`** for conversions; avoid custom `to_x()` when `From` works
- **`Default`** for types that have a sensible zero value
- **Orphan rule**: implement YOUR trait on any type, or OUR trait on your type. Not both external.

## Async

- **`tokio`** for most runtime needs; `async-std` is fine; `smol` for minimal
- **`.await` everywhere** — no blocking calls in async contexts
- **`tokio::spawn`** for independent tasks; `JoinSet` for bounded parallelism
- **`select!`** for multiplexing; `join!` for concurrent awaits
- **`Send` + `Sync`** bounds: async code crossing thread boundaries needs them
- **`Pin`** — you usually don't touch it; crates handle it

## Naming

- `snake_case` functions, variables, modules
- `PascalCase` types + traits + enum variants
- `SCREAMING_SNAKE_CASE` constants + statics
- Short lifetimes `'a`, `'b`; descriptive only when needed for clarity (`'source`, `'input`)

## Modules + crates

- `src/lib.rs` for library crate, `src/main.rs` for binary
- `src/bin/*.rs` for multiple binaries in one package
- Workspace for multi-crate projects; `Cargo.toml` at root lists members
- `pub(crate)` to expose within crate but hide externally
- Re-export public API at crate root: `pub use inner::Type;`

## Testing

- `#[test]` functions in a `#[cfg(test)] mod tests` block
- `tests/` directory for integration tests
- `assert_eq!`, `assert!`, `matches!` are the defaults
- `proptest` or `quickcheck` for property-based testing
- `cargo test --all-features` + `cargo test --no-default-features` for crate authors

## Common idioms

- **Builder pattern** for structs with many optional fields
- **`match` exhaustive** — let the compiler enforce coverage
- **Iterator chains** over explicit loops when clearer
- **`.collect::<Result<Vec<_>, _>>()`** to propagate errors through iteration
- **`if let Some(x) = ...`** / **`while let`** / **`let else`** for pattern-matched extraction
- **Newtype wrappers** for unit safety: `struct UserId(u64)` beats raw `u64`

## Anti-patterns

- `.unwrap()` / `.expect()` in library code — use `?` or handle the error
- Over-use of lifetimes when owned values would do (reduces generic noise)
- `dyn Trait` in hot paths when `impl Trait` works — vtable cost
- `RefCell` / `Mutex` hiding borrow checker problems — sometimes the design needs fixing
- Premature `unsafe` — 99% of code doesn't need it
- `println!` for logging — use `tracing` or `log`

## Tooling

- `cargo fmt` — non-negotiable
- `cargo clippy -- -D warnings` — strict in CI
- `cargo deny` — license + audit
- `cargo machete` — unused dependencies
- `cargo nextest` — faster test runner

## Examples

- "Review this Rust module against idioms"
- "Is my error type well-designed?"
- "Should this be `impl Trait` or `dyn Trait`?"
- "Clean up the lifetimes in this function signature"
