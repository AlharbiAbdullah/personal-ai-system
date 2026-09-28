---
name: kubernetes
description: >
  Kubernetes manifests, Helm charts, kubectl patterns. USE WHEN the user
  deploys, debugs, or scales on k8s. Covers Pods, Deployments, Services,
  Ingress, ConfigMaps, Secrets, RBAC, Helm.
---

# Kubernetes

Orchestration for containerized workloads. Use when docker-compose isn't
enough: multi-host, auto-scaling, rolling updates, service discovery.

## When to use

- Multi-host deployment at steady load
- Auto-scaling based on CPU/memory/custom metrics
- Need service discovery, health checks, rolling updates
- Existing org standard is k8s

## When NOT to use

- Single-host deployment — docker-compose is simpler
- Serverless workload — Lambda / Cloud Run / Cloudflare Workers fit better
- Early-stage product, small team — operational cost doesn't pay off

## Core resources

### Pod
- Smallest deployable unit. Usually 1 container per Pod; sidecars for tightly-coupled aux containers.
- Ephemeral. Don't rely on Pod identity.

### Deployment
- Manages a set of Pods (a ReplicaSet).
- Rolling updates by default.
- Scale with `replicas: N` or HPA.

### StatefulSet
- For stateful workloads (databases, queues) needing stable network identity + persistent volumes.
- Ordered deploy + scale.

### Service
- Stable network endpoint for a set of Pods.
- Types: ClusterIP (internal), NodePort (port on each node), LoadBalancer (cloud LB), ExternalName (DNS CNAME).

### Ingress
- HTTP/HTTPS routing to Services. Needs an ingress controller (NGINX, Traefik, cloud-native).
- TLS termination, host-based + path-based routing.

### ConfigMap / Secret
- ConfigMap: non-sensitive config (env vars, config files).
- Secret: sensitive (API keys, TLS certs). Base64-encoded, NOT encrypted at rest by default — enable encryption-at-rest on the cluster.
- Mount into Pods as env vars or files.

### Namespace
- Logical separation. Default namespaces: `default`, `kube-system`, `kube-public`.
- Per-team, per-env (dev/staging/prod in separate namespaces or clusters).

### RBAC
- Role + RoleBinding (namespaced) or ClusterRole + ClusterRoleBinding.
- Service Accounts for workload identity.
- Principle of least privilege — never give workloads cluster-admin.

## Common Deployment manifest

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: prod
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
      - name: api
        image: registry.example.com/api:1.2.3
        ports:
        - containerPort: 8000
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8000
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /readyz
            port: 8000
          periodSeconds: 5
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
```

## Helm

Package manager for k8s manifests. Templates + values file.

```bash
helm install myapp ./chart -f values.prod.yaml
helm upgrade myapp ./chart -f values.prod.yaml
helm rollback myapp 1
helm list -n prod
```

Chart structure:
```
chart/
  Chart.yaml
  values.yaml        # defaults
  values.prod.yaml   # per-env overrides
  templates/
    deployment.yaml
    service.yaml
    ingress.yaml
    _helpers.tpl
```

## kubectl cheatsheet

```bash
# Context
kubectl config use-context prod
kubectl config current-context

# Inspect
kubectl get pods -n prod
kubectl describe pod <name> -n prod
kubectl logs <pod> -n prod --tail=100 -f
kubectl exec -it <pod> -n prod -- sh

# Apply / delete
kubectl apply -f deployment.yaml
kubectl delete -f deployment.yaml

# Debug
kubectl get events -n prod --sort-by='.lastTimestamp'
kubectl top pods -n prod  # needs metrics-server
kubectl rollout status deploy/api -n prod
kubectl rollout undo deploy/api -n prod

# Port-forward for local access
kubectl port-forward svc/api 8000:8000 -n prod
```

## Scaling

- **HPA** — horizontal pod autoscaler, based on CPU/memory/custom metrics
- **VPA** — vertical pod autoscaler, adjusts resource requests
- **Cluster autoscaler** — adds/removes nodes
- Keep requests + limits realistic — over-requesting wastes money, under-requesting triggers OOMKill

## Observability

- Logs: stdout/stderr → collected by DaemonSet (Fluentd, Vector, Loki)
- Metrics: Prometheus scrape pods + kube-state-metrics
- Traces: OpenTelemetry Collector → Tempo / Jaeger
- Dashboard: Grafana for all three

## Anti-patterns

- Baking secrets into images
- Using `latest` tag — untracked versions, can't roll back
- No resource requests/limits — noisy neighbor problem
- No liveness/readiness probes — traffic hits broken pods
- Privileged containers — huge blast radius
- `hostNetwork: true` except for specific infra workloads
- Huge monolithic manifests — split by resource type

## Examples

- "Write k8s manifests for Helios chat service"
- "Helm chart for OpenKit with dev + prod values"
- "Debug why my Pods keep restarting"
- "Set up HPA for the Matchbox API"
