# CreateCLI

Generate TypeScript CLI tools with type safety. Automatically selects
the right framework tier based on project complexity.

## Framework Tiers

### Minimal (80% of CLIs)
Plain TypeScript with `process.argv` or `parseArgs` (Node 18+).

- Single command, few flags
- No subcommands needed
- Examples: file converters, quick scripts, single-purpose tools

### Commander.js (15% of CLIs)
Structured CLI with subcommands and help generation.

- Multiple subcommands
- Complex flag parsing
- Automatic help text
- Examples: project management tools, multi-action utilities

### oclif (5% of CLIs)
Full framework for large, plugin-based CLIs.

- Plugin architecture needed
- Many subcommands with shared config
- Distribution as npm package
- Examples: platform CLIs, developer tools with extensions

## Process

1. **Assess complexity**: Number of commands, flags, input types
2. **Select tier**: Match to the simplest tier that fits
3. **Scaffold project**: `package.json`, `tsconfig.json`, entry point
4. **Implement commands**: Type-safe argument parsing, validation
5. **Add error handling**: Descriptive errors, exit codes, help text
6. **Build and test**: Compile, run against sample inputs

## Project Structure (Minimal)

```
my-cli/
  package.json
  tsconfig.json
  src/
    index.ts      # Entry point + arg parsing
    commands/     # Command handlers (if multiple)
    utils/        # Shared utilities
```

## Output Standards

- All arguments and options are typed
- Exit code 0 for success, 1 for user error, 2 for system error
- `--help` flag always available
- Colored output for errors (red) and success (green)
- stdin/stdout piping support where appropriate

## Examples

- "Create a CLI that converts CSV to JSON"
- "Build a CLI tool for managing Docker containers"
- "Make a CLI that checks broken links in markdown files"
