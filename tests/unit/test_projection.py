from tests.e2e.helpers import invariant_projection


def test_invariant_projection_ignores_version_specific_fields():
    state = {
        "tenant": {"id": "t", "name": "n"},
        "users": [],
        "permissions": [],
        "connections": [
            {"id": "c", "name": "n", "endpoint": "e", "connection_type": "generic"}
        ],
        "model_settings": None,
        "indexed_documents": [
            {
                "id": "d",
                "external_id": "x",
                "checksum": "z",
                "status": "indexed",
                "namespace": "default",
            }
        ],
    }
    projected = invariant_projection(state)
    assert "connection_type" not in projected["connections"][0]
    assert "namespace" not in projected["indexed_documents"][0]
