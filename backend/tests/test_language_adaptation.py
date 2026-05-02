"""v4.6 — эвристики домена и речевого профиля."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.language_adaptation import UserDomainProfile, UserLanguageProfile
from app.models.neurofriend import NeuroFriendProfile
from app.models.relationship_state import RelationshipModel
from app.models.user import User
from app.services import profession_context_service
from app.services.language_adaptation_service import (
    compute_adaptation_mode,
    extract_lexical_markers,
    filter_overimitation,
    ingest_user_message,
)


def test_detect_software_markers() -> None:
    m = profession_context_service.detect_domain_markers("задеплоим в прод, там баг после миграции")
    assert "software_engineering" in m
    assert any("баг" in x for x in m["software_engineering"])


def test_direct_self_report() -> None:
    hits = profession_context_service.direct_self_report_hits("я программист, работаю удалённо")
    assert any(d == "software_engineering" for d, _ in hits)


def test_fillers_extracted() -> None:
    x = extract_lexical_markers("короче, по факту надо докрутить")
    assert "короче" in x["fillers"]
    assert "по факту" in x["fillers"]


def test_adaptation_mode_thresholds() -> None:
    assert compute_adaptation_mode(primary_confidence=0.1) == "almost_neutral"
    assert compute_adaptation_mode(primary_confidence=0.4) == "light_adaptation"
    assert compute_adaptation_mode(primary_confidence=0.8) == "contextual_domain"


def test_filter_overimitation() -> None:
    assert filter_overimitation(["деплой", "баг"], ["баг"]) == ["деплой"]


async def test_ingest_builds_domain_row() -> None:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    user_id = None
    async with factory() as session:
        u = User(display_name="u1", timezone="UTC")
        session.add(u)
        await session.flush()
        user_id = u.id
        nf = NeuroFriendProfile(user_id=user_id, name="N", archetype="companion")
        session.add(nf)
        await session.flush()
        session.add(RelationshipModel(neurofriend_id=nf.id, person_ref="user_main"))
        await session.flush()
        await ingest_user_message(
            session,
            neurofriend_id=nf.id,
            user_id=user_id,
            user_text="я программист, костыль в проде после деплоя",
        )
        await session.commit()

    assert user_id is not None
    async with factory() as session:
        r = await session.execute(select(UserLanguageProfile).where(UserLanguageProfile.user_id == user_id))
        lang = r.scalar_one()
        assert lang.primary_profession_confidence > 0.2
        r2 = await session.execute(select(UserDomainProfile).where(UserDomainProfile.user_id == user_id))
        domains = r2.scalars().all()
        assert any(d.domain_name == "software_engineering" for d in domains)

    await engine.dispose()
