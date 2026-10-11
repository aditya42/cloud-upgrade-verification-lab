import pytest

from tests.e2e.helpers import delete_namespace, deploy, port_forward, seed

pytestmark = pytest.mark.e2e


def test_fresh_install_latest_release():
    namespace = "fresh-install"
    delete_namespace(namespace)
    try:
        deploy(namespace, "v2.0")
        with port_forward(namespace, 18001) as base:
            snapshot = seed(base, tenant_id="fresh-tenant")
            assert snapshot["release"] == "v2.0"
            assert snapshot["tenant"]["name"] == "Acme AI"
            assert snapshot["users"][0]["role"] == "admin"
            assert "indexes:manage" in {p["permission"] for p in snapshot["permissions"]}
            assert snapshot["model_settings"]["model_name"] == "gpt-compatible-model"
            assert snapshot["indexed_documents"][0]["namespace"] == "default"
    finally:
        delete_namespace(namespace)
