# Docker Best Practices

Apply these guidelines when creating Dockerfiles, docker-compose configs, and container architecture.

---

## Dockerfile Structure

### Multi-Stage Build Template

```dockerfile
# Stage 1: Build
FROM python:3.12-slim AS builder

WORKDIR /app
COPY pyproject.toml uv.lock ./

RUN pip install uv && uv sync --frozen --no-dev

COPY src/ ./src/

# Stage 2: Production
FROM python:3.12-slim AS production

WORKDIR /app

# Non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

# Copy only what's needed
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

ENV PATH="/app/.venv/bin:$PATH"

HEALTHCHECK --interval=30s --timeout=3s \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

EXPOSE 8000
CMD ["python", "-m", "src.main"]
```

---

## Core Principles

### 1. Minimal Base Images
```
python:3.12        → 886 MB  ❌
python:3.12-slim   → 145 MB  ✓
python:3.12-alpine →  48 MB  ✓✓ (if compatible)
```

### 2. Non-Root User (REQUIRED)
```dockerfile
RUN useradd --create-home app
USER app
```
58% of images run as root. Don't be one of them.

### 3. One Process Per Container
- ✅ One service = one container
- ❌ Multiple services in one container

### 4. Layer Optimization
```dockerfile
# ❌ Bad: Cache invalidated on any file change
COPY . .
RUN pip install -r requirements.txt

# ✅ Good: Dependencies cached separately
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
```

Put frequently changing files LAST.

### 5. COPY over ADD
```dockerfile
# ✅ Use COPY for local files
COPY src/ /app/src/

# Only use ADD for:
# - Remote URLs
# - Auto-extracting archives
```

---

## Security Checklist

### Image Security
- [ ] Use official/trusted base images
- [ ] Pin image versions (no `:latest`)
- [ ] Scan images for vulnerabilities (Trivy, Snyk)
- [ ] Sign images with Docker Content Trust
- [ ] Use `.dockerignore` to exclude secrets

### Runtime Security
- [ ] Run as non-root user
- [ ] Drop unnecessary capabilities
- [ ] Set resource limits (CPU, memory)
- [ ] Read-only filesystem where possible
- [ ] No privileged mode unless required

### Secrets Management
```dockerfile
# ❌ NEVER do this (example of an anti-pattern — do not copy)
ENV API_KEY=placeholder
COPY .env /app/.env

# ✅ Inject at runtime (example placeholders shown)
# docker run -e API_KEY=$API_KEY ...
# docker run with BuildKit mount-at-build flag (example only)
```

---

## Docker Compose Patterns

### Development vs Production

```yaml
# docker-compose.yml (base)
services:
  app:
    build:
      context: .
      target: production
    environment:
      - DATABASE_URL

# docker-compose.override.yml (dev, auto-loaded)
services:
  app:
    build:
      target: development
    volumes:
      - .:/app
    ports:
      - "8000:8000"
```

### Service Architecture

```yaml
services:
  api:
    build: .
    depends_on:
      db:
        condition: service_healthy
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M

  db:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

---

## .dockerignore Template

```
# Git
.git
.gitignore

# Python
__pycache__
*.pyc
*.pyo
.pytest_cache
.mypy_cache
.ruff_cache
.venv
venv

# IDE
.idea
.vscode
*.swp

# Docker
Dockerfile*
docker-compose*

# Secrets (CRITICAL)
.env
.env.*
*.pem
*.key
secrets/

# Build artifacts
dist
build
*.egg-info

# Docs/Tests (unless needed)
docs
tests
README.md
```

---

## HEALTHCHECK Patterns

```dockerfile
# HTTP service
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Python without curl
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Database connection
HEALTHCHECK CMD pg_isready -U postgres || exit 1

# Custom script
HEALTHCHECK CMD /app/healthcheck.sh
```

---

## Python-Specific Patterns

### UV with Docker

```dockerfile
FROM python:3.12-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.12-slim
WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY src/ ./src/

ENV PATH="/app/.venv/bin:$PATH"
CMD ["python", "-m", "src.main"]
```

### pip with Docker

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (cached)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["python", "main.py"]
```

---

## Anti-Patterns to Avoid

| Anti-Pattern | Why It's Bad | Fix |
|--------------|--------------|-----|
| `:latest` tag | Non-reproducible | Pin versions |
| Running as root | Security risk | `USER app` |
| Secrets in image | Leaked credentials | Runtime injection |
| No `.dockerignore` | Large images, secrets | Add one |
| No healthcheck | Silent failures | Add `HEALTHCHECK` |
| One Dockerfile per env | Duplication | Multi-stage |
| `apt-get` without cleanup | Bloated layers | `rm -rf /var/lib/apt/lists/*` |

---

## Build Commands

```bash
# Build with specific target
docker build --target production -t myapp:1.0 .

# Build with BuildKit (faster, parallel)
DOCKER_BUILDKIT=1 docker build -t myapp .

# Build for multiple platforms
docker buildx build --platform linux/amd64,linux/arm64 -t myapp .

# Scan for vulnerabilities
docker scout cves myapp:latest
trivy image myapp:latest
```

---

## When to Use This Skill

Invoke /docker when:
- Creating new Dockerfiles
- Setting up docker-compose
- Reviewing container security
- Optimizing image size
- Debugging container issues

---

## Multi-arch builds (amd64 + arm64)

Modern fleets mix Apple Silicon dev machines with amd64 cloud hosts. Build
multi-arch images once, deploy anywhere.

```bash
# Ensure buildx is available (example commands)
docker buildx create --use --name multiarch

# Build and push both arches (example registry path)
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    --tag registry.example.com/myapp:1.0 \
    --push \
    .

# Inspect the manifest — should list both architectures
docker buildx imagetools inspect registry.example.com/myapp:1.0
```

Pitfalls:
- Native arch builds are fast; cross-arch emulation is slow. For CI, use
  matrix strategy with native runners per arch instead of QEMU emulation.
- Test actual runtime behavior on each target arch (some C libs misbehave
  under cross-compile).
- `FROM --platform=$BUILDPLATFORM` for builder stages + `FROM --platform=$TARGETPLATFORM`
  for the final stage is the idiomatic dual-arch Dockerfile pattern.

## Secrets management

Never bake a credential into an image. Options in order of preference:

**1. BuildKit mount-at-build** — mount at build time, nothing persists in the image (example placeholder names below — replace with your own).

See [BuildKit secrets docs](https://docs.docker.com/build/building/secrets/) for the exact Dockerfile syntax using `RUN --mount=type=secret,id=<YOUR_ID>`. Pair with `docker build --secret id=<YOUR_ID>,env=<YOUR_ENV>` at build time. Example IDs and envs shown are placeholders only.

**2. Runtime injection via orchestrator** — Kubernetes Secrets, AWS Secrets Manager, HashiCorp Vault, GCP Secret Manager. Injected into container env at pod start, not baked in.

**3. Docker Compose secret references** — for local + small deploys, use Compose's `secrets:` block to read from a file on the host (the `file:` field points to a local path that is NEVER committed). See [Compose secrets docs](https://docs.docker.com/compose/how-tos/use-secrets/) for the schema; example values shown in docs are placeholders.

**4. Avoid**: baking a credential via `ENV`, copying a `.env` file, or hardcoding literals. Scan built images with `docker history` + `dive` to verify no leak.

Sources:
- [Docker Best Practices 2026 - Thinksys](https://thinksys.com/devops/docker-best-practices/)
- [Dockerfile Best Practices - Sysdig](https://www.sysdig.com/learn-cloud-native/dockerfile-best-practices)
- [Docker Security Best Practices - Anchore](https://anchore.com/blog/docker-security-best-practices-a-complete-guide/)
- [Multi-Stage Builds - Docker Docs](https://docs.docker.com/build/building/multi-stage/)
- [BuildKit Secrets - Docker Docs](https://docs.docker.com/build/building/secrets/)
