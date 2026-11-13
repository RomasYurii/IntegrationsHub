from typing import List
from uuid import UUID
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User, Tenant, Membership
from app.schemas.tenant import TenantWithRole


class TenantDoesntExist(Exception):
    pass

async def create_tenant(db: AsyncSession, user: User, name: str) -> Tenant:

    new_tenant = Tenant(name=name)
    db.add(new_tenant)

    await db.flush()

    new_membership = Membership(user_id=user.id, tenant_id=new_tenant.id, role="owner")
    db.add(new_membership)

    await db.commit()

    await db.refresh(new_tenant)
    return new_tenant


async def get_tenant_by_id(db: AsyncSession, tenant_id: UUID) -> Tenant:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    result = result.scalar()
    if not result:
        raise TenantDoesntExist()

    return result

async def list_user_tenants(db: AsyncSession, user: User) -> List[TenantWithRole]:

    result = await db.execute(
        select(
            Membership.tenant_id.label("id"),
            Tenant.name,
            Tenant.created_at,
            Membership.role,)
        .join(Tenant, Membership.tenant_id == Tenant.id)
        .where(Membership.user_id == user.id)
    )

    return [
        TenantWithRole(
            id=row.id,
            name=row.name,
            created_at=row.created_at,
            role=row.role,
        )
        for row in result.all()
    ]


async def rename_tenant(db: AsyncSession, tenant: Tenant, new_name: str) -> Tenant:

    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant.id)
    )
    result = result.one_or_none()

    if result is None:
        raise TenantDoesntExist from None

    new_tenant = await db.execute(
        update(Tenant).where(Tenant.id == tenant.id).values(name=new_name).returning(Tenant)
    )
    await db.commit()
    return new_tenant.scalar_one_or_none()

async def delete_tenant(db: AsyncSession, tenant: Tenant) -> None:

    try:

        await db.execute(
            delete(Tenant).where(Tenant.id == tenant.id)
        )
        await db.commit()

    except Exception:
        raise TenantDoesntExist from None