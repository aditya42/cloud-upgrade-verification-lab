from __future__ import annotations

import subprocess
import time
from contextlib import contextmanager

import requests

CHART = "helm/cloud-upgrade-lab"
SERVICE = "cloud-upgrade-lab"


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def deploy(namespace: str, version: str) -> None:
    run("kubectl", "create", "namespace", namespace)
    run(
        "helm", "install", "upgrade-lab", CHART,
        "--namespace", namespace,
        "--set", f"image.tag={version}",
        "--wait", "--timeout", "120s",
    )


def upgrade(namespace: str, version: str) -> None:
    run(
        "helm", "upgrade", "upgrade-lab", CHART,
        "--namespace", namespace,
        "--set", f"image.tag={version}",
        "--wait", "--timeout", "120s",
    )


def delete_namespace(namespace: str) -> None:
    subprocess.run(
        ["kubectl", "delete", "namespace", namespace, "--wait=true", "--ignore-not-found=true"],
        check=False,
    )


@contextmanager
def port_forward(namespace: str, local_port: int):
    proc = subprocess.Popen(
        ["kubectl", "-n", namespace, "port-forward", f"svc/{SERVICE}", f"{local_port}:8000"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{local_port}"
    try:
        for _ in range(60):
            if proc.poll() is not None:
                raise RuntimeError(f"kubectl port-forward exited early with code {proc.returncode}")
            try:
                if requests.get(f"{base}/health", timeout=1).ok:
                    break
            except requests.RequestException:
                pass
            time.sleep(1)
        else:
            raise RuntimeError(f"Service in namespace {namespace} did not become reachable")
        yield base
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)


def seed(base: str, tenant_id: str = "tenant-a") -> dict:
    calls = [
        ("post", "/api/tenants", {"id": tenant_id, "name": "Acme AI"}),
        (
            "post", "/api/users",
            {
                "id": "user-admin",
                "tenant_id": tenant_id,
                "email": "admin@example.test",
                "role": "admin",
                "permissions": ["models:read", "models:write", "indexes:manage"],
            },
        ),
        (
            "post", "/api/connections",
            {
                "id": "conn-primary",
                "tenant_id": tenant_id,
                "name": "Primary warehouse",
                "endpoint": "https://warehouse.example.test",
            },
        ),
        (
            "put", f"/api/tenants/{tenant_id}/model-settings",
            {"model_name": "gpt-compatible-model", "temperature": 0.2, "max_tokens": 2048},
        ),
        (
            "post", "/api/documents",
            {
                "id": "doc-1",
                "tenant_id": tenant_id,
                "external_id": "policy-001",
                "checksum": "sha256:abc123",
                "status": "indexed",
            },
        ),
    ]
    for method, path, payload in calls:
        response = getattr(requests, method)(f"{base}{path}", json=payload, timeout=5)
        response.raise_for_status()
    return requests.get(f"{base}/api/state/{tenant_id}", timeout=5).json()


def state(base: str, tenant_id: str = "tenant-a") -> dict:
    response = requests.get(f"{base}/api/state/{tenant_id}", timeout=5)
    response.raise_for_status()
    return response.json()


def invariant_projection(snapshot: dict) -> dict:
    return {
        "tenant": snapshot["tenant"],
        "users": snapshot["users"],
        "permissions": snapshot["permissions"],
        "connections": [
            {k: c[k] for k in ("id", "name", "endpoint")} for c in snapshot["connections"]
        ],
        "model_settings": snapshot["model_settings"],
        "indexed_documents": [
            {k: d[k] for k in ("id", "external_id", "checksum", "status")}
            for d in snapshot["indexed_documents"]
        ],
    }
