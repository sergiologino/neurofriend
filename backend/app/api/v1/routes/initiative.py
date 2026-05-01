import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models.neurofriend import NeuroFriendProfile
from app.schemas.initiative import InitiativeStatusRead
from app.services import initiative_service

router = APIRouter()


@router.get("/{neurofriend_id}/initiative/status", response_model=InitiativeStatusRead)
async def get_initiative_status(
    neurofriend_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> InitiativeStatusRead:
    """Сводка для отладки и будущего UI: gap, тихие часы, условная готовность инициативы."""
    rnf = await session.execute(select(NeuroFriendProfile).where(NeuroFriendProfile.id == neurofriend_id))
    if rnf.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="NeuroFriend not found")
    data = await initiative_service.build_initiative_status(session, neurofriend_id)
    return InitiativeStatusRead(**data)
