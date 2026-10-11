import pytest

from tests.e2e.helpers import (
    delete_namespace,
    deploy,
    invariant_projection,
    port_forward,
    seed,
    state,
    upgrade,
)

pytestmark = pytest.mark.e2e


def test_previous_ga_upgrade_preserves_customer_state():
    namespace = "upgrade-path"
    delete_namespace(namespace)
    try:
        deploy(namespace, "v1.0")
        # Port forwarding is pod-bound. Each Helm upgrade replaces the app pod,
        # so reconnect after every deployment to avoid a stale tunnel.
        with port_forward(namespace, 18000) as base:
            before = seed(base)
            assert before["release"] == "v1.0"

        upgrade(namespace, "v1.1")
        with port_forward(namespace, 18000) as base:
            after_v11 = state(base)
        assert after_v11["release"] == "v1.1"
        assert invariant_projection(after_v11) == invariant_projection(before)
        assert after_v11["connections"][0]["connection_type"] == "generic"
        assert "v1.1" in after_v11["schema_migrations"]

        upgrade(namespace, "v2.0")
        with port_forward(namespace, 18000) as base:
            after_v20 = state(base)
        assert after_v20["release"] == "v2.0"
        assert invariant_projection(after_v20) == invariant_projection(before)
        assert after_v20["connections"][0]["connection_type"] == "generic"
        assert after_v20["indexed_documents"][0]["namespace"] == "default"
        assert set(after_v20["schema_migrations"]) >= {"v1.0", "v1.1", "v2.0"}
    finally:
        delete_namespace(namespace)
