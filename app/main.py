from fastapi import FastAPI, HTTPException
from sqlalchemy import text

from app.config import settings
from app.db import engine
from app.migrations import migrate
from app.repository import (
    create_connection,
    create_tenant,
    create_user,
    get_state,
    index_document,
    upsert_model_settings,
)
from app.schemas import ConnectionCreate, DocumentCreate, ModelSettingsUpsert, TenantCreate, UserCreate

migrate(engine, settings.app_version)
app = FastAPI(title="Cloud Upgrade Verification Lab", version=settings.app_version)


@app.get("/health")
def health() -> dict:
    try:
        with engine.begin() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "release": settings.app_version}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/version")
def version() -> dict:
    return {"release": settings.app_version}


@app.post("/api/tenants", status_code=201)
def tenants(payload: TenantCreate) -> dict:
    create_tenant(payload)
    return {"created": payload.id}


@app.post("/api/users", status_code=201)
def users(payload: UserCreate) -> dict:
    create_user(payload)
    return {"created": payload.id}


@app.post("/api/connections", status_code=201)
def connections(payload: ConnectionCreate) -> dict:
    create_connection(payload)
    return {"created": payload.id}


@app.put("/api/tenants/{tenant_id}/model-settings")
def model_settings(tenant_id: str, payload: ModelSettingsUpsert) -> dict:
    upsert_model_settings(tenant_id, payload)
    return {"updated": tenant_id}


@app.post("/api/documents", status_code=201)
def documents(payload: DocumentCreate) -> dict:
    index_document(payload)
    return {"created": payload.id}


@app.get("/api/state/{tenant_id}")
def state(tenant_id: str) -> dict:
    try:
        return get_state(tenant_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Tenant state unavailable: {exc}") from exc
