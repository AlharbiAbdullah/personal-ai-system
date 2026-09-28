## Scope

Python-only. TypeScript, Go and Rust have their own files in this router: `typescript.md`, `go.md`, `rust.md`.

## Purpose

Deep review of code against coding standards. Use when you want to verify compliance or check code quality.

## Usage

```bash
/coding-standards                    # Review current file
/coding-standards src/services/      # Review specific path
/coding-standards check imports      # Check specific aspect
```

---

## REVIEW CHECKLIST

### 1. File Structure

```
[ ] File under 500 lines
[ ] Functions under 50 lines
[ ] Classes under 100 lines
[ ] One concept per file
[ ] Clear module boundaries
```

### 2. Naming

```
[ ] Variables/functions: snake_case
[ ] Classes: PascalCase
[ ] Constants: UPPER_SNAKE_CASE
[ ] Private: _leading_underscore
[ ] Descriptive names (no x, temp, data)
```

**Check for:**
```python
# BAD
def proc(d):
    x = d["val"]

# GOOD
def process_user_data(user_data: dict):
    user_value = user_data["value"]
```

### 3. Type Hints

```
[ ] All function parameters typed
[ ] All return types specified
[ ] Complex types use TypeAlias
[ ] Optional values marked Optional[]
[ ] No Any unless justified
```

**Check for:**
```python
# BAD
def get_user(id):
    return db.find(id)

# GOOD
def get_user(user_id: int) -> Optional[User]:
    return db.find(user_id)
```

### 4. Docstrings

```
[ ] All public functions documented
[ ] Google-style format
[ ] Args, Returns, Raises documented
[ ] Examples for complex functions
```

**Template:**
```python
def function_name(param: Type) -> ReturnType:
    """
    Short description.

    Args:
        param: Description of param

    Returns:
        Description of return value

    Raises:
        ValueError: When param is invalid
    """
```

### 5. Imports

```
[ ] Sorted: stdlib → third-party → local
[ ] No unused imports
[ ] No wildcard imports (from x import *)
[ ] Absolute imports preferred
```

**Order:**
```python
# Standard library
import os
from datetime import datetime

# Third-party
import pandas as pd
from pydantic import BaseModel

# Local
from src.services import UserService
from src.models import User
```

### 6. Error Handling

```
[ ] Specific exceptions caught
[ ] Custom exceptions for domain errors
[ ] No bare except:
[ ] Errors logged with context
[ ] Fail fast on invalid input
```

**Check for:**
```python
# BAD
try:
    do_something()
except:
    pass

# GOOD
try:
    do_something()
except ValidationError as e:
    logger.error(f"Validation failed: {e}")
    raise
```

### 7. Code Patterns

```
[ ] KISS - Simple solutions preferred
[ ] YAGNI - No speculative features
[ ] DRY - No duplicated logic (3+ times)
[ ] Single Responsibility - One purpose per unit
[ ] Dependency Injection - Dependencies passed in
```

### 8. Data Validation

```
[ ] Pydantic models for input/output
[ ] Validation at boundaries
[ ] Strict mode enabled
[ ] Field constraints defined
```

**Check for:**
```python
# BAD
def create_user(data: dict):
    name = data.get("name")  # No validation

# GOOD
class CreateUserRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)

def create_user(request: CreateUserRequest):
    ...
```

### 9. Testing

```
[ ] Tests next to code (feature/tests/)
[ ] Descriptive test names
[ ] Fixtures for setup
[ ] Edge cases covered
[ ] No test interdependence
```

### 10. Comments

```
[ ] Code is self-documenting
[ ] Comments explain WHY, not WHAT
[ ] No commented-out code
[ ] TODO format: # TODO(name): description
```

### 11. Tooling

**uv** — the only project driver. **Ruff** — lint + format. **ty** — type check (replaced mypy, decision 2026-08-31).

**uv, no exception:**

```
[ ] Every Python project is uv-driven: pyproject.toml + uv.lock, run via uv run
[ ] Dependencies added with uv add, never pip install
[ ] No poetry, no pipenv, no requirements.txt, no system python
[ ] One-off scripts: #!/usr/bin/env -S uv run --script + PEP 723 inline deps
[ ] ruff, ty, marimo: uv add --dev per project, never uv tool install (decided 2026-09-09)
```

**Ruff coverage rule — match rules to imports:**

For every library the project imports, extend-select its ruff rule set in pyproject.toml. Coverage follows the dependency list: when `uv add` brings in a lib, add its rules in the same change.

| Import | Rule set |
| --- | --- |
| (always) | `I` (import sort), `UP` (modern syntax) |
| fastapi | `FAST` |
| pytest | `PT` |
| pandas | `PD` |
| numpy | `NPY` |
| django | `DJ` |
| airflow | `AIR` |
| asyncio / anyio / trio | `ASYNC` |
| logging | `LOG`, `G` |
| datetime | `DTZ` |

Not exhaustive: for any other lib, check the ruff rules list for a matching set before deciding none exists.

```
[ ] ruff check passes clean (no ignores without a reason comment)
[ ] ruff format applied
[ ] ty check passes clean
[ ] Every import has its matching rule set in extend-select
[ ] Config lives in pyproject.toml, not scattered dotfiles
[ ] line-length under [tool.ruff] (both formatter and linter read it)
[ ] extend-select under [tool.ruff.lint], never [tool.ruff]
```

**Config template (FastAPI project example):**
```toml
[tool.ruff]
line-length = 100

[tool.ruff.lint]
extend-select = ["I", "UP", "FAST", "ASYNC", "PT"]
```

**Run:**
```bash
uv run ruff check .
uv run ruff format .
uv run ty check
```

Ruff's default rule set targets real defects (e.g. B006 mutable default argument fires by default), so keep the default set and extend on top of it per the table.

---

## OUTPUT FORMAT

```
CODING STANDARDS REVIEW
=======================

Target: src/services/user_service.py
Lines: 245

VIOLATIONS
----------

[STRUCTURE] Function too long
  Location: user_service.py:45-120 (75 lines)
  Rule: Functions should be under 50 lines
  Fix: Split into smaller functions

[NAMING] Non-descriptive variable
  Location: user_service.py:67
  Code: x = user.get_data()
  Fix: Use descriptive name like user_data

[TYPES] Missing return type
  Location: user_service.py:89
  Code: def process_users(users):
  Fix: def process_users(users: list[User]) -> list[dict]:

[IMPORTS] Unused import
  Location: user_service.py:3
  Code: from datetime import timedelta
  Fix: Remove unused import

COMPLIANT
---------
- Docstrings: Google-style ✓
- Error handling: Specific exceptions ✓
- Validation: Pydantic models ✓
- Testing: Tests exist ✓

SUMMARY
-------
- Violations: 4
- Compliant: 4
- File health: GOOD (minor issues)

PRIORITY FIXES
--------------
1. Split long function (lines 45-120)
2. Add return types to functions
3. Remove unused imports
```

---

## QUICK CHECKS

Run specific checks:

```bash
/coding-standards check types      # Type hints only
/coding-standards check imports    # Import order only
/coding-standards check naming     # Naming conventions only
/coding-standards check structure  # File/function length only
/coding-standards check tooling    # Ruff + ty config and clean runs
```

---

## RULES

1. Be specific - show exact line numbers
2. Prioritize violations by impact
3. Acknowledge what's compliant
4. Provide concrete fixes
5. Don't nitpick - focus on real issues
6. Reference project standards from AGENTS.md
