from __future__ import annotations

import asyncio
import signal

from app.config import settings
from app.database import async_session, init_db
from app.observability import configure_logging, get_logger
from app.services.job_runner import ResearchJobWorker

configure_logging(
    service_name=f"{settings.APP_NAME}-worker",
    environment=settings.APP_ENV,
    log_level=settings.LOG_LEVEL,
    json_logs=settings.LOG_JSON,
)
logger = get_logger(__name__)


async def _run():
    await init_db()
    worker = ResearchJobWorker(async_session)
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(worker.shutdown()))

    await worker.run_forever()


def main():
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        logger.info("jobs.worker.interrupted")


if __name__ == "__main__":
    main()
