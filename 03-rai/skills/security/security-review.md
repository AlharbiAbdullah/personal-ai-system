# Security Review

Review code for security vulnerabilities. Principles-based checklist for any stack.

This is PASSIVE analysis — reading code. No authorization gate required. For active penetration testing, see web-assessment.md.

## When to use

Before deployment of a new feature, before opening a service to external traffic, when onboarding a new reviewer, on demand. For every PR: overkill — use ad-hoc focused review instead.

## Usage

```bash
/security-review                    # Review current file/module
/security-review src/api/           # Review specific path
/security-review auth flow          # Review specific feature
```

## Process

1. Identify what to review
2. Run through relevant checklists
3. Report findings with severity
4. Suggest fixes

---

## API Security

### Authentication

```
[ ] Passwords hashed with strong algorithm (bcrypt, argon2, scrypt)
[ ] Never MD5/SHA1 for passwords
[ ] Tokens have expiration
[ ] Refresh token rotation implemented
[ ] Failed login attempts limited (brute force protection)
[ ] Password requirements enforced
[ ] No credentials in URLs
```

### Authorization

```
[ ] Every endpoint checks permissions
[ ] No Insecure Direct Object References (IDOR)
[ ] Admin routes protected
[ ] Resource ownership verified before access
[ ] Return 404 (not 403) to hide resource existence
[ ] Principle of least privilege applied
```

### Input Validation

```
[ ] All inputs validated at boundary
[ ] SQL injection prevented (parameterized queries)
[ ] Path traversal prevented (no ../ in file paths)
[ ] File uploads restricted (type, size, renamed)
[ ] No user input in shell commands
[ ] XSS prevented (output encoding)
```

### Rate Limiting

```
[ ] API endpoints rate limited
[ ] Auth endpoints have stricter limits
[ ] Rate limit headers returned
[ ] Graceful degradation under load
```

### Secrets Management

```
[ ] No secrets in code
[ ] No secrets in logs
[ ] Environment variables or secrets manager used
[ ] Secrets files in .gitignore
[ ] Different secrets per environment
[ ] Secrets rotated periodically
```

---

## Data Security

### Credentials

```
[ ] Database credentials from env/secrets manager
[ ] No hardcoded connection strings
[ ] Credentials never logged
[ ] Separate credentials per environment
[ ] Service accounts have minimal permissions
```

### Data Protection

```
[ ] PII identified and tagged
[ ] Sensitive data masked in logs
[ ] PII not in error messages
[ ] Data retention policies applied
[ ] Encryption at rest for sensitive data
[ ] Encryption in transit (TLS)
```

### Query Safety

```
[ ] Dynamic table/column names whitelisted
[ ] User-provided filters parameterized
[ ] No string interpolation in queries
[ ] No code execution from data (eval, exec)
```

---

## Dependency Security

```
[ ] No known vulnerabilities in dependencies
[ ] Dependencies pinned to specific versions
[ ] Lock file committed
[ ] Regular dependency updates scheduled
[ ] Dependencies from trusted sources only
```

---

## Severity Levels

| Level | Description | Action |
|-------|-------------|--------|
| HIGH | Exploitable vulnerability | Fix immediately |
| MEDIUM | Potential risk | Fix before deploy |
| LOW | Best practice violation | Fix when possible |
| INFO | Suggestion | Consider improving |

---

## Output Format

```
SECURITY REVIEW
===============

Target: [path or feature]
Risk Level: HIGH / MEDIUM / LOW

FINDINGS
--------

[HIGH] SQL Injection
  Location: file:line
  Issue: User input directly in query
  Fix: Use parameterized queries

[MEDIUM] Missing rate limit
  Location: auth endpoint
  Issue: Brute force attacks possible
  Fix: Add rate limiting

PASSED
------
- Authentication: Strong hashing ✓
- Authorization: Ownership checks ✓
- Secrets: Environment variables ✓

SUMMARY
-------
- High: 1
- Medium: 1
- Low: 0
- Passed: 3

PRIORITY FIXES
--------------
1. [HIGH] Fix SQL injection
2. [MEDIUM] Add rate limiting
```

## Rules

1. Check both application and data layer
2. Report severity honestly
3. Provide specific fix suggestions
4. Show exact locations for issues
5. Acknowledge what passed
6. No false positives - verify before reporting
