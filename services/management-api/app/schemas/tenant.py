from pydantic import BaseModel
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from uuid import UUID

from app.core.permissions import Role


class TenantCreate(BaseModel):
    name : str = Field(max_length=100)


class TenantRead(BaseModel):
    id : UUID
    name : str = Field(max_length=100)
    created_at : datetime

    model_config = ConfigDict(from_attributes=True)

class TenantWithRole(BaseModel):
    id: UUID
    name: str = Field(max_length=100)
    created_at: datetime
    role : str

    model_config = ConfigDict(from_attributes=True)