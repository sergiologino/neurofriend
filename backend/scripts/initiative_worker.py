from __future__ import annotations

import argparse
import asyncio
import logging

from app.core.database import async_session_factory
from app.services.initiative_runner import run_initiative_sweep

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("initiative_worker")


async def _run_loop(interval_seconds: float) -> None:
    while True:
        async with async_session_factory() as session:
            result = await run_initiative_sweep(session)
            logger.info("initiative sweep result: %s", result)
        await asyncio.sleep(interval_seconds)


def main() -> int:
    parser = argparse.ArgumentParser(description="Long-running NeuroFriend initiative worker.")
    parser.add_argument("--interval-seconds", type=float, default=300.0)
    args = parser.parse_args()
    asyncio.run(_run_loop(args.interval_seconds))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
