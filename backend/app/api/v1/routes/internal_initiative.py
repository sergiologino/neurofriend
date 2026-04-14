"""Внутренние эндпоинты для cron/воркера (не для публичного клиента)."""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.config import get_settings
from app.services.initiative_runner import run_initiative_sweep

router = APIRouter()


@router.post("/initiative/sweep")
async def post_initiative_sweep(
    session: AsyncSession = Depends(get_session),
    x_initiative_sweep_key: str | None = Header(None, alias="X-Initiative-Sweep-Key"),
) -> dict:
    """Перебор нейродрузей и отправка инициативы при выполнении условий. Требует секрет в заголовке."""
    settings = get_settings()
    if not settings.initiative_sweep_secret:
        raise HTTPException(status_code=404, detail="Not found")
    if not x_initiative_sweep_key or x_initiative_sweep_key != settings.initiative_sweep_secret:
        raise HTTPException(status_code=404, detail="Not found")
    return await run_initiative_sweep(session)
