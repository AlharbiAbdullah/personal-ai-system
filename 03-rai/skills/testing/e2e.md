## Purpose

Test something end-to-end. Adapts to what you're testing.

## Usage

```bash
/e2e                      # Test what we just worked on
/e2e test this            # Test current file/module
/e2e ingestion pipeline   # Test specific pipeline
/e2e user auth flow       # Test specific flow
/e2e POST /api/v1/queries # Test specific API
```

## Process

### 1. Identify Target

If no target specified:
- Look at recent conversation context
- What files were edited?
- What feature was discussed?

Ask if unclear:
```
What should I test end-to-end?
- The ingestion pipeline we just built?
- The API endpoint we modified?
- Something else?
```

### 2. Detect Type

| Target Contains | Type | Test Approach |
|-----------------|------|---------------|
| `/api/`, endpoint, route | API | Request → Response chain |
| pipeline, etl, ingestion | Data Pipeline | Source → Destination |
| flow, journey, process | User Flow | Step 1 → Step N |
| job, dag, task | Orchestration | Trigger → Completion |

### 3. Run E2E Based on Type

---

## Type: API

```
Test the full request lifecycle:

1. Setup
   - Test database/state
   - Auth tokens

2. Execute
   - Send request
   - Include auth, headers, body

3. Verify
   - Status code correct
   - Response body matches schema
   - Side effects occurred (DB updated, event fired)
   - Error cases handled

4. Cleanup
   - Reset test state
```

Example test:
```python
def test_query_execution_e2e(client, auth_user, test_db):
    """E2E: User creates and runs a query."""
    # Create query
    create_resp = client.post("/api/v1/queries", json={
        "name": "Test Query",
        "sql": "SELECT * FROM analytics.users LIMIT 10"
    })
    assert create_resp.status_code == 201
    query_id = create_resp.json()["id"]

    # Run query
    run_resp = client.post(f"/api/v1/queries/{query_id}/run")
    assert run_resp.status_code == 200
    assert len(run_resp.json()["rows"]) <= 10

    # Verify in database
    saved = test_db.get_query(query_id)
    assert saved.last_run_at is not None
```

---

## Type: Data Pipeline (ETL/Ingestion)

```
Test source to destination:

1. Setup
   - Prepare test data at source
   - Clear destination
   - Note expected row count

2. Execute
   - Run pipeline (dagster, dbt, script)
   - Wait for completion

3. Verify
   - Data arrived at destination
   - Row count matches
   - Schema correct
   - Data quality checks pass
   - No orphaned records

4. Cleanup
   - Remove test data
```

Example test:
```python
def test_user_ingestion_e2e(source_db, target_db, dagster_client):
    """E2E: Ingest users from source to warehouse."""
    # Setup: Insert test records
    source_db.execute("""
        INSERT INTO users (id, name) VALUES
        (9901, 'Test User 1'),
        (9902, 'Test User 2')
    """)

    # Execute pipeline
    result = dagster_client.run_job("user_ingestion")
    assert result.success

    # Verify destination
    rows = target_db.query("SELECT * FROM warehouse.users WHERE id IN (9901, 9902)")
    assert len(rows) == 2

    # Verify data quality
    assert all(row["name"] is not None for row in rows)

    # Cleanup
    source_db.execute("DELETE FROM users WHERE id IN (9901, 9902)")
    target_db.execute("DELETE FROM warehouse.users WHERE id IN (9901, 9902)")
```

---

## Type: Orchestration (Jobs/DAGs)

```
Test job execution:

1. Setup
   - Prepare dependencies
   - Clear previous runs

2. Execute
   - Trigger job/DAG
   - Wait for completion

3. Verify
   - Job succeeded
   - All tasks completed
   - Outputs generated
   - Downstream triggered (if applicable)

4. Cleanup
   - Archive test run
```

Example test:
```python
def test_daily_etl_dag_e2e(dagster_client, test_db):
    """E2E: Daily ETL DAG completes successfully."""
    # Execute
    result = dagster_client.run_job(
        "daily_etl",
        run_config={"date": "2024-01-15"}
    )

    # Verify all steps
    assert result.success
    assert result.steps_completed == ["extract", "transform", "load", "validate"]

    # Verify outputs
    assert test_db.table_exists("daily_metrics_2024_01_15")
    assert test_db.row_count("daily_metrics_2024_01_15") > 0
```

---

## Type: User Flow

```
Test multi-step process:

1. Identify steps in flow
2. Execute each step
3. Verify state after each step
4. Verify final outcome
```

Example test:
```python
def test_self_service_query_flow_e2e(client, auth_user):
    """E2E: User self-service query flow."""
    # Step 1: User logs in
    login_resp = client.post("/auth/login", json=auth_user.credentials)
    assert login_resp.status_code == 200
    token = login_resp.json()["token"]

    # Step 2: User creates query
    headers = {"Authorization": f"Bearer {token}"}
    create_resp = client.post("/api/v1/queries",
        json={"name": "My Query", "sql": "SELECT 1"},
        headers=headers
    )
    query_id = create_resp.json()["id"]

    # Step 3: User runs query
    run_resp = client.post(f"/api/v1/queries/{query_id}/run", headers=headers)
    assert run_resp.status_code == 200

    # Step 4: User exports results
    export_resp = client.get(f"/api/v1/queries/{query_id}/export?format=csv", headers=headers)
    assert export_resp.status_code == 200
    assert "text/csv" in export_resp.headers["content-type"]
```

---

## Output Format

```
E2E TEST: [Target Name]
========================

Type: API | Pipeline | Orchestration | Flow

Steps:
1. [Setup] - Prepared test data
2. [Execute] - Ran [what]
3. [Verify] - Checked [what]
4. [Cleanup] - Removed test data

Results:
- Total steps: N
- Passed: N
- Failed: N

Details:
- [Step]: PASS/FAIL - [details]

Run command:
uv run pytest tests/e2e/test_[target].py -v
```

## Rules

1. Always setup test data (don't use production)
2. Always cleanup after test
3. Test the FULL flow, not parts
4. Verify side effects, not just responses
5. Use realistic test data
6. Isolate from other tests

## External-service mocking

Real e2e tests call real systems. But some systems can't be called in CI:
payment processors (Stripe), transactional email (SendGrid), SMS (Twilio),
OAuth providers, third-party APIs with rate limits or costs. Mock these
at the network boundary, not in application code.

### Preferred: wiremock / mockoon / msw
Run a mock HTTP server that responds to the real URLs (use DNS rewriting
or env-configurable endpoints). Define expected interactions as fixtures;
fail the test if the mock wasn't called as expected.

```python
# Example with pytest + responses
import responses

@responses.activate
def test_payment_flow():
    responses.add(
        responses.POST,
        "https://api.stripe.com/v1/charges",
        json={"id": "ch_test_123", "status": "succeeded"},
        status=200,
    )
    result = checkout_flow(cart, card)
    assert result.status == "paid"
    assert len(responses.calls) == 1
```

### Provider sandboxes
Most serious SaaS has a test environment (Stripe test mode, Twilio trial,
SendGrid sandbox). Prefer sandboxes over mocks when the provider offers
one — you catch API schema changes, mocks stay stale.

### What NOT to mock
- Your own databases — use a test DB with migrations
- Your own services — call them for real in e2e
- File system — use a tmpdir
- Time — use freezegun or similar, not a mock layer

### Verification
After the test, assert against what the mock saw: did we POST the right
payload? Did we retry on 500? Did we respect the rate limit? Behavioral
assertions beat "test passed because mock responded."
