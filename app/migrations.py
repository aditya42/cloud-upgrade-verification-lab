from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

SUPPORTED = ("v1.0", "v1.1", "v2.0")

BASE_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(20) PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS tenants (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(200) NOT NULL
);
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(320) NOT NULL,
    role VARCHAR(80) NOT NULL,
    UNIQUE (tenant_id, email)
);
CREATE TABLE IF NOT EXISTS permissions (
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    permission VARCHAR(120) NOT NULL,
    PRIMARY KEY (user_id, permission)
);
CREATE TABLE IF NOT EXISTS connections (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    endpoint TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS model_settings (
    tenant_id VARCHAR(64) PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
    model_name VARCHAR(120) NOT NULL,
    temperature DOUBLE PRECISION NOT NULL,
    max_tokens INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS indexed_documents (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    external_id VARCHAR(200) NOT NULL,
    checksum VARCHAR(128) NOT NULL,
    status VARCHAR(40) NOT NULL,
    UNIQUE (tenant_id, external_id)
);
"""

MIGRATION_V11 = """
ALTER TABLE connections
    ADD COLUMN IF NOT EXISTS connection_type VARCHAR(80) NOT NULL DEFAULT 'generic';
"""

MIGRATION_V20 = """
ALTER TABLE indexed_documents
    ADD COLUMN IF NOT EXISTS namespace VARCHAR(120) NOT NULL DEFAULT 'default';
"""


def _record(conn, version: str) -> None:
    conn.execute(
        text(
            "INSERT INTO schema_migrations(version) VALUES (:version) "
            "ON CONFLICT (version) DO NOTHING"
        ),
        {"version": version},
    )


def migrate(engine: Engine, target: str) -> None:
    if target not in SUPPORTED:
        raise ValueError(f"Unsupported APP_VERSION={target}. Expected one of {SUPPORTED}")

    with engine.begin() as conn:
        for statement in [s.strip() for s in BASE_SCHEMA.split(";") if s.strip()]:
            conn.execute(text(statement))
        _record(conn, "v1.0")

        if target in {"v1.1", "v2.0"}:
            conn.execute(text(MIGRATION_V11))
            _record(conn, "v1.1")

        if target == "v2.0":
            conn.execute(text(MIGRATION_V20))
            _record(conn, "v2.0")
