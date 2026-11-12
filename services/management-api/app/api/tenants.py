import asyncio
import logging
import redis

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import current_user
from sqlalchemy.util import await_

from app.api.deps import get_current_user, require_role
from app.core.database import get_db
from app.core.permissions import Role
from app.core.redis import redis_client
from app.models import User, Membership, Tenant
from app.schemas.tenant import TenantRead, TenantCreate, TenantWithRole
from app.services.tenant_service import create_tenant, list_user_tenants, rename_tenant, delete_tenant, \
    get_tenant_by_id, TenantDoesntExist

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post("/", status_code=201, response_model=TenantCreate)
async def create_tenants(
    name: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),

):

    tenant = await create_tenant(db, user, name)

    return tenant

@router.get("/")
async def get_tenants(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):

    list_tenants = await list_user_tenants(db, user)

    return list_tenants

@router.get("/{tenant_id}", response_model=TenantRead)
async def get_tenants(
        db: AsyncSession = Depends(get_db),
        membership: Membership = Depends(require_role(Role.viewer))
):
    tenant = await db.get(Tenant, membership.tenant_id)
    return tenant

"""
PATCH /tenants/{tenant_id} (перейменування) із роллю admin і вище;
DELETE /tenants/{tenant_id} лише для owner, відповідь 204.
"""

@router.patch("/{tenant_id}", response_model=TenantRead)
async def update_tenants(
        name: str,
        db: AsyncSession = Depends(get_db),
        membership: Membership = Depends(require_role(Role.admin))
):
    try:
        tenant = await get_tenant_by_id(db, membership.tenant_id)
        result = await rename_tenant(db, tenant, name)

    except TenantDoesntExist:
        raise HTTPException(status_code=404, detail="Tenant doesnt exist")

    return result

@router.delete("/{tenant_id}", status_code=204)
async def delete_tenants(
        db: AsyncSession = Depends(get_db),
        membership: Membership = Depends(require_role(Role.owner))
):
    try:
        tenant = await get_tenant_by_id(db, membership.tenant_id)

        await delete_tenant(db, tenant)
    except TenantDoesntExist:
        raise HTTPException(status_code=404, detail="Tenant doesnt exist")