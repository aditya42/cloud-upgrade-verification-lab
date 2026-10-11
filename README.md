# Cloud Upgrade Verification Lab

A production-style reference project for validating **fresh installs and state-preserving upgrades** of a cloud application across multiple GA releases.

The lab deliberately models the upgrade risks that are easy to miss in ordinary API or UI regression suites:

- fresh installation of the latest GA release
- upgrade from previous GA releases (`v1.0 → v1.1 → v2.0`)
- PostgreSQL persistence across Kubernetes pod replacement
- tenant configuration preservation
- user and permission preservation
- external connection preservation
- model-setting preservation
- indexed-document preservation
- forward schema migrations with safe defaults
- CI release gate using Docker + Kubernetes + Helm + kind + pytest

## Architecture

```text
                          GitHub Actions
                               |
                               v
                    build v1.0 / v1.1 / v2.0
                               |
                               v
                         kind cluster
                               |
                  +------------+-------------+
                  |                          |
                  v                          v
          Fresh-install lane          Upgrade lane
               v2.0                 v1.0 -> v1.1 -> v2.0
                  |                          |
                  +------------+-------------+
                               |
                               v
                        Helm deployment
                               |
                 +-------------+-------------+
                 |                           |
                 v                           v
          FastAPI release             PostgreSQL PVC
                 |                           |
                 +-------------+-------------+
                               |
                               v
                      pytest state oracle
                               |
                     PASS = releasable
                     FAIL = block release
```

## Version behavior

| Release | Schema behavior |
|---|---|
| `v1.0` | Base tenant/user/permissions/connections/model/index tables |
| `v1.1` | Adds `connections.connection_type` with safe default `generic` |
| `v2.0` | Adds `indexed_documents.namespace` with safe default `default` |

The same persistent database is intentionally retained while the application Deployment changes versions. This makes the tests exercise a real upgrade path instead of recreating state on every release.

## Preservation oracle

The e2e suite captures state before an upgrade and compares invariant customer state after every release transition:

```python
assert connections_before == connections_after
assert permissions_before == permissions_after
assert settings_before == settings_after
assert indexed_documents_before == indexed_documents_after
```

Version-specific fields are validated separately so schema evolution does not create false failures.

## Prerequisites

- Python 3.11+
- Docker
- kubectl
- Helm 3
- kind

On macOS with Homebrew:

```bash
brew install python@3.11 kubectl helm kind
```

## Fastest demo

```bash
git clone <your-repo-url>
cd cloud-upgrade-verification-lab
python3 -m venv .venv
source .venv/bin/activate
make install
make verify
```

`make verify`:

1. builds `cloud-upgrade-lab:v1.0`, `v1.1`, and `v2.0`
2. creates a local kind Kubernetes cluster
3. loads all release images into kind
4. deploys the fresh-install test lane
5. deploys `v1.0`, seeds realistic tenant state, upgrades to `v1.1`, then `v2.0`
6. fails if state, permissions, model configuration, connections, or indexed data are lost

Cleanup:

```bash
make clean
```

## Local Docker-only smoke run

```bash
RELEASE_VERSION=v1.0 docker compose up --build
curl http://localhost:8000/health
```

To reset local state:

```bash
docker compose down -v
```

## Key APIs

```text
GET  /health
GET  /version
POST /api/tenants
POST /api/users
POST /api/connections
PUT  /api/tenants/{tenant_id}/model-settings
POST /api/documents
GET  /api/state/{tenant_id}
```

## CI release gate

`.github/workflows/upgrade-verification.yml` creates a disposable kind cluster in GitHub Actions and runs both:

```text
Fresh install: v2.0
Upgrade path : v1.0 -> v1.1 -> v2.0
```

A failed preservation assertion blocks the workflow.

## What this demonstrates on a resume

- release engineering and upgrade qualification
- Kubernetes workload lifecycle testing
- Helm install/upgrade automation
- persistent-state and backward-compatibility validation
- database migration verification
- Docker image versioning
- CI quality gates
- API-level test orchestration
- deterministic release evidence

## Suggested next extensions

The repository is intentionally small enough to understand in one sitting but structured to grow. Strong additions are backup/restore verification, rollback testing, multi-node PostgreSQL, RBAC policy changes, secrets rotation, large-index integrity checks, performance SLO comparison across releases, and an LLM-generated upgrade risk plan that remains subordinate to deterministic assertions.

## Troubleshooting: disconnected port-forward during Helm upgrade

The port-forward tunnel targets a specific pod even when its argument names a
Service. A Helm upgrade replaces the application pod and invalidates the tunnel.
The upgrade-preservation test therefore **closes and reopens** the tunnel at
each release boundary (`v1.0`, `v1.1`, `v2.0`). If a previous download failed
with `RemoteDisconnected` after upgrading, use this updated project and rerun
`make verify`.

For manual inspection, use `kubectl -n upgrade-path get pods` and
`kubectl -n upgrade-path get events --sort-by=.metadata.creationTimestamp`.

