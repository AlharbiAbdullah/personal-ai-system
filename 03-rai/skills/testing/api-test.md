## Purpose

Test existing APIs by their behavior and contract, not implementation. Treat the API as a black box.

## When to Use

- Existing APIs without tests
- After API is built, need to verify behavior
- Before refactoring API internals
- Documenting API contract

## What Makes This Different

```
/testing unit-test → Tests implementation (how it works)
/testing tdd       → Builds new code test-first
/testing api-test  → Tests API contract (what it promises)
```

## Process

### 1. List API Endpoints

Ask user or scan routes:
```
GET    /api/v1/queries
POST   /api/v1/queries
GET    /api/v1/queries/{id}
DELETE /api/v1/queries/{id}
POST   /api/v1/queries/{id}/run
```

### 2. For Each Endpoint, Identify Behaviors

```
POST /api/v1/queries

Behaviors:
- Creates new query with valid data
- Returns 201 with created resource
- Returns 422 if name missing
- Returns 422 if SQL invalid
- Returns 401 if not authenticated
- Returns 403 if user lacks permission
```

### 3. Write Tests by Category

For each endpoint, cover these categories:

**A. Happy Path (2xx)**
```python
def test_creates_query_with_valid_data(self, client, auth_headers):
    """POST /queries creates a new query."""
    response = client.post("/api/v1/queries",
        json={"name": "My Query", "sql": "SELECT 1"},
        headers=auth_headers
    )

    assert response.status_code == 201
    assert response.json()["name"] == "My Query"
    assert "id" in response.json()
```

**B. Validation Errors (4xx)**
```python
def test_requires_name_field(self, client, auth_headers):
    """POST /queries returns 422 if name missing."""
    response = client.post("/api/v1/queries",
        json={"sql": "SELECT 1"},
        headers=auth_headers
    )

    assert response.status_code == 422
    assert "name" in response.json()["detail"][0]["loc"]
```

**C. Authentication (401)**
```python
def test_requires_authentication(self, client):
    """POST /queries returns 401 without auth."""
    response = client.post("/api/v1/queries",
        json={"name": "Test", "sql": "SELECT 1"}
    )

    assert response.status_code == 401
```

**D. Authorization (403)**
```python
def test_cannot_access_other_users_query(self, client, auth_headers, other_user_query):
    """GET /queries/{id} returns 404 for other user's query."""
    response = client.get(
        f"/api/v1/queries/{other_user_query.id}",
        headers=auth_headers
    )

    # 404 not 403 - don't reveal existence
    assert response.status_code == 404
```

**E. Business Rules**
```python
def test_enforces_rate_limit(self, client, auth_headers):
    """POST /queries/run enforces 10/minute rate limit."""
    # Make 10 successful requests
    for _ in range(10):
        client.post("/api/v1/queries/run",
            json={"sql": "SELECT 1"},
            headers=auth_headers
        )

    # 11th should fail
    response = client.post("/api/v1/queries/run",
        json={"sql": "SELECT 1"},
        headers=auth_headers
    )

    assert response.status_code == 429
    assert "rate limit" in response.json()["detail"].lower()
```

### 4. Test File Structure

```python
# tests/api/test_queries_api.py

import pytest
from fastapi.testclient import TestClient

class TestCreateQuery:
    """POST /api/v1/queries"""

    def test_creates_with_valid_data(self): ...
    def test_returns_created_resource(self): ...
    def test_requires_name(self): ...
    def test_requires_valid_sql(self): ...
    def test_requires_auth(self): ...

class TestGetQuery:
    """GET /api/v1/queries/{id}"""

    def test_returns_query_by_id(self): ...
    def test_returns_404_if_not_found(self): ...
    def test_cannot_access_others_query(self): ...

class TestRunQuery:
    """POST /api/v1/queries/{id}/run"""

    def test_executes_query(self): ...
    def test_enforces_rate_limit(self): ...
    def test_enforces_row_limit(self): ...
```

### 5. Common Fixtures

```python
# tests/api/conftest.py

@pytest.fixture
def client(app):
    """Test client for API."""
    return TestClient(app)

@pytest.fixture
def auth_headers(test_user):
    """Auth headers for test user."""
    token = create_token(test_user)
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def test_query(test_user, db):
    """A query owned by test user."""
    query = Query(name="Test", sql="SELECT 1", owner=test_user)
    db.add(query)
    db.commit()
    return query
```

## Output Format

```
API TESTS WRITTEN
=================

Endpoint: POST /api/v1/queries

Tests Created:
- test_creates_with_valid_data (happy path)
- test_returns_201_with_location (happy path)
- test_requires_name (validation)
- test_requires_valid_sql (validation)
- test_requires_authentication (auth)
- test_requires_permission (authz)

File: tests/api/test_queries_api.py

Coverage by Category:
- Happy Path: 2 tests
- Validation: 2 tests
- Auth: 1 test
- Authz: 1 test
- Business Rules: 0 tests (none identified)

Run:
uv run pytest tests/api/test_queries_api.py -v
```

## Rules

1. Test behavior, not implementation
2. One assertion concept per test
3. Test all response codes the endpoint can return
4. Always test auth (401) and authz (403)
5. Use fixtures for test data
6. Mock external services, not the API itself
7. Test the contract - if behavior changes, test should fail
