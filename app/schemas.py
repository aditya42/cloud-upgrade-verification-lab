from pydantic import BaseModel, Field


class TenantCreate(BaseModel):
    id: str
    name: str


class UserCreate(BaseModel):
    id: str
    tenant_id: str
    email: str
    role: str
    permissions: list[str] = Field(default_factory=list)


class ConnectionCreate(BaseModel):
    id: str
    tenant_id: str
    name: str
    endpoint: str
    connection_type: str = "generic"


class ModelSettingsUpsert(BaseModel):
    model_name: str
    temperature: float = Field(ge=0, le=2)
    max_tokens: int = Field(gt=0)


class DocumentCreate(BaseModel):
    id: str
    tenant_id: str
    external_id: str
    checksum: str
    status: str = "indexed"
    namespace: str = "default"
