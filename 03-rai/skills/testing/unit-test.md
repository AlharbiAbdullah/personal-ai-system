## Purpose

Add tests to existing code that was built without tests. Document what the code DOES, not what it SHOULD do.

## When to Use

- Existing code without tests
- Backend services, utilities, pipelines
- Before refactoring (safety net)
- Understanding legacy code

## Process

### 1. Understand the Code

Read the target file/module and identify:
- Public functions and methods
- Input parameters and types
- Return values
- Side effects (DB writes, API calls, file operations)
- Error conditions

### 2. Ask Clarifying Questions

```
Before writing tests, confirm:
- Which functions are most critical?
- Any known edge cases?
- Any functions that should NOT be tested? (deprecated, etc.)
```

### 3. Write Tests by Category

For each function, write tests in this order:

**A. Happy Path**
- Normal inputs, expected outputs
- Most common use case

**B. Edge Cases**
- Empty inputs ([], "", None)
- Boundary values (0, -1, max)
- Single item vs many items

**C. Error Cases**
- Invalid inputs
- Missing required params
- Expected exceptions

### 4. Test File Structure

```python
# tests/test_<module_name>.py

import pytest
from module import function_under_test

class TestFunctionName:
    """Tests for function_name."""

    # Happy path
    def test_returns_expected_result(self):
        """Describe the normal behavior."""
        result = function_under_test(valid_input)
        assert result == expected

    # Edge cases
    def test_handles_empty_input(self):
        """Empty input returns empty result."""
        result = function_under_test([])
        assert result == []

    # Error cases
    def test_raises_on_invalid_input(self):
        """Invalid input raises ValueError."""
        with pytest.raises(ValueError):
            function_under_test(invalid_input)
```

### 5. Use Fixtures for Setup

```python
# conftest.py or top of test file

@pytest.fixture
def sample_data():
    """Provide sample data for tests."""
    return {"id": 1, "name": "test"}

@pytest.fixture
def db_connection(tmp_path):
    """Provide test database connection."""
    # Setup
    conn = create_test_db(tmp_path)
    yield conn
    # Teardown
    conn.close()
```

## Output Format

After writing tests, report:

```
TESTS WRITTEN
=============

Target: src/services/query_parser.py

Tests Created:
- tests/services/test_query_parser.py

Coverage:
- parse_query(): 4 tests (happy, empty, invalid, complex)
- validate_sql(): 3 tests (happy, injection, syntax)
- extract_tables(): 2 tests (happy, nested)

Not Tested (explain why):
- _internal_helper(): private method

Run tests:
uv run pytest tests/services/test_query_parser.py -v
```

## Rules

1. Test PUBLIC interfaces, not private methods
2. One assertion concept per test
3. Descriptive test names: `test_<behavior>_when_<condition>`
4. Use fixtures, avoid test interdependence
5. Mock external dependencies (DB, API, filesystem)
6. Run tests after writing to verify they pass
