"""Simulator entry point — run as a background daemon.

Starts the engine, runs the tick loop, and handles graceful shutdown.
"""

import asyncio
import logging
import os
import signal
import sys

from engine import SimulatorEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

API_BASE = os.getenv("API_BASE_URL", "http://api:8000")
INTERNAL_KEY = os.getenv("INTERNAL_API_KEY", "dev-internal-key-change-in-production")
TICK_SECONDS = int(os.getenv("TICK_INTERVAL_SECONDS", "30"))

# Startup delay — wait for the API to be ready
STARTUP_DELAY_SECONDS = int(os.getenv("SIMULATOR_STARTUP_DELAY", "30"))


async def run() -> None:
    logger.info("Simulator starting up — waiting %ds for API to be ready…", STARTUP_DELAY_SECONDS)
    await asyncio.sleep(STARTUP_DELAY_SECONDS)

    engine = SimulatorEngine(api_base=API_BASE, internal_key=INTERNAL_KEY)
    await engine.startup()

    stop_event = asyncio.Event()

    def _handle_signal(*_):
        logger.info("Shutdown signal received")
        stop_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _handle_signal)

    logger.info("Simulator running — tick every %ds", TICK_SECONDS)
    while not stop_event.is_set():
        try:
            await engine.tick()
        except Exception as exc:
            logger.error("Tick error: %s", exc)
        await asyncio.sleep(TICK_SECONDS)

    await engine.shutdown()
    logger.info("Simulator shut down cleanly")


if __name__ == "__main__":
    asyncio.run(run())
