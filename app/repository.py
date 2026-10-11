from __future__ import annotations

from sqlalchemy import text

from app.config import settings
from app.db import engine
from app.schemas import ConnectionCreate, DocumentCreate, ModelSettingsUpsert, TenantCreate, UserCreate


def create_tenant(payload: TenantCreate) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO tenants(id, name) VALUES (:id, :name) ON CONFLICT (id) DO NOTHING"),
            payload.model_dump(),
        )


def create_user(payload: UserCreate) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users(id, tenant_id, email, role) VALUES "
                "(:id, :tenant_id, :email, :role) ON CONFLICT (id) DO NOTHING"
            ),
            payload.model_dump(exclude={"permissions"}),
        )
        for permission in payload.permissions:
            conn.execute(
                text(
                    "INSERT INTO permissions(user_id, permission) VALUES (:user_id, :permission) "
                    "ON CONFLICT DO NOTHING"
                ),
                {"user_id": payload.id, "permission": permission},
            )


def create_connection(payload: ConnectionCreate) -> None:
    values = payload.model_dump()
    with engine.begin() as conn:
        if settings.app_version == "v1.0":
            conn.execute(
                text(
                    "INSERT INTO connections(id, tenant_id, name, endpoint) VALUES "
                    "(:id, :tenant_id, :name, :endpoint) ON CONFLICT (id) DO NOTHING"
                ),
                values,
            )
        else:
            conn.execute(
                text(
                    "INSERT INTO connections(id, tenant_id, name, endpoint, connection_type) VALUES "
                    "(:id, :tenant_id, :name, :endpoint, :connection_type) "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                values,
            )


def upsert_model_settings(tenant_id: str, payload: ModelSettingsUpsert) -> None:
    values = payload.model_dump() | {"tenant_id": tenant_id}
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO model_settings(tenant_id, model_name, temperature, max_tokens) VALUES "
                "(:tenant_id, :model_name, :temperature, :max_tokens) "
                "ON CONFLICT (tenant_id) DO UPDATE SET model_name = EXCLUDED.model_name, "
                "temperature = EXCLUDED.temperature, max_tokens = EXCLUDED.max_tokens"
            ),
            values,
        )


def index_document(payload: DocumentCreate) -> None:
    values = payload.model_dump()
    with engine.begin() as conn:
        if settings.app_version in {"v1.0", "v1.1"}:
            conn.execute(
                text(
                    "INSERT INTO indexed_documents(id, tenant_id, external_id, checksum, status) VALUES "
                    "(:id, :tenant_id, :external_id, :checksum, :status) "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                values,
            )
        else:
            conn.execute(
                text(
                    "INSERT INTO indexed_documents(id, tenant_id, external_id, checksum, status, namespace) "
                    "VALUES (:id, :tenant_id, :external_id, :checksum, :status, :namespace) "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                values,
            )


def get_state(tenant_id: str) -> dict:
    with engine.begin() as conn:
        tenant = conn.execute(
            text("SELECT id, name FROM tenants WHERE id = :tenant_id"), {"tenant_id": tenant_id}
        ).mappings().one()
        users = conn.execute(
            text("SELECT id, email, role FROM users WHERE tenant_id = :tenant_id ORDER BY id"),
            {"tenant_id": tenant_id},
        ).mappings().all()
        permissions = conn.execute(
            text(
                "SELECT p.user_id, p.permission FROM permissions p JOIN users u ON p.user_id = u.id "
                "WHERE u.tenant_id = :tenant_id ORDER BY p.user_id, p.permission"
            ),
            {"tenant_id": tenant_id},
        ).mappings().all()

        connection_columns = "id, name, endpoint"
        if settings.app_version != "v1.0":
            connection_columns += ", connection_type"
        connections = conn.execute(
            text(
                f"SELECT {connection_columns} FROM connections "
                "WHERE tenant_id = :tenant_id ORDER BY id"
            ),
            {"tenant_id": tenant_id},
        ).mappings().all()

        model_settings = conn.execute(
            text(
                "SELECT model_name, temperature, max_tokens FROM model_settings "
                "WHERE tenant_id = :tenant_id"
            ),
            {"tenant_id": tenant_id},
        ).mappings().one_or_none()

        document_columns = "id, external_id, checksum, status"
        if settings.app_version == "v2.0":
            document_columns += ", namespace"
        documents = conn.execute(
            text(
                f"SELECT {document_columns} FROM indexed_documents "
                "WHERE tenant_id = :tenant_id ORDER BY id"
            ),
            {"tenant_id": tenant_id},
        ).mappings().all()

        migrations = conn.execute(
            text("SELECT version FROM schema_migrations ORDER BY applied_at, version")
        ).scalars().all()

    return {
        "release": settings.app_version,
        "tenant": dict(tenant),
        "users": [dict(x) for x in users],
        "permissions": [dict(x) for x in permissions],
        "connections": [dict(x) for x in connections],
        "model_settings": dict(model_settings) if model_settings else None,
        "indexed_documents": [dict(x) for x in documents],
        "schema_migrations": list(migrations),
    }
