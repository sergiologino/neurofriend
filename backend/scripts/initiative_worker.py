from __future__ import annotations

import asyncio

import argparse
import logging

from app.core.database import async_session_factory
from app.services.initiative_runner import run_initiative_sweep
from app.services.memory_consolidation import run_consolidation_all_neurofriends

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("initiative_worker")


async def _run_cycle(*, consolidate_memory_first: bool) -> dict:
    out: dict = {}
    if consolidate_memory_first:
        async with async_session_factory() as session:
            out["memory_consolidation"] = await run_consolidation_all_neurofriends(session)
            await session.commit()
            logger.info("memory consolidation sweep: %s", out["memory_consolidation"])
    async with async_session_factory() as session:
        out["initiative"] = await run_initiative_sweep(session)
        logger.info("initiative sweep result: %s", out["initiative"])
    return out


async def _run_loop(interval_seconds: float, *, consolidate_memory_first: bool) -> None:
    while True:
        await _run_cycle(consolidate_memory_first=consolidate_memory_first)
        await asyncio.sleep(interval_seconds)


def main() -> int:
    parser = argparse.ArgumentParser(description="Long-running NeuroFriend initiative worker.")
    parser.add_argument("--interval-seconds", type=float, default=300.0)
    parser.add_argument(
        "--consolidate-memory-first",
        action="store_true",
        help="Перед каждым sweep инициативы прогнать SQL memory consolidation для всех нейродрузей.",
    )
    args = parser.parse_args()
    asyncio.run(_run_loop(args.interval_seconds, consolidate_memory_first=args.consolidate_memory_first))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
