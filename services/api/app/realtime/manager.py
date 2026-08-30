"""WebSocket connection manager backed by Redis pub/sub.

Architecture:
  ML service (or ingest in Phase 2) → PUBLISH to redis channel predictions:{train}
  Any API instance → SUBSCRIBEs to that channel → pushes to connected WebSocket clients

This means multiple API instances can run behind a load balancer and every
connected client still gets every update — no session affinity needed.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from typing import Any

import redis.asyncio as aioredis
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and routes Redis pub/sub updates to them."""

    def __init__(self) -> None:
        # train_number → set of WebSocket connections
        self._train_connections: dict[str, set[WebSocket]] = defaultdict(set)
        # Fleet connections (all trains)
        self._fleet_connections: set[WebSocket] = set()
        self._redis: aioredis.Redis | None = None
        self._pubsub: aioredis.client.PubSub | None = None
        self._listener_task: asyncio.Task | None = None

    async def startup(self, redis_url: str) -> None:
        """Call during FastAPI lifespan startup."""
        self._redis = aioredis.from_url(redis_url, decode_responses=True)
        self._pubsub = self._redis.pubsub()
        # Subscribe to fleet channel — individual train channels added on demand
        await self._pubsub.psubscribe("predictions:*")
        self._listener_task = asyncio.create_task(self._listen())
        logger.info("WebSocket manager started — subscribed to predictions:*")

    async def shutdown(self) -> None:
        """Call during FastAPI lifespan shutdown."""
        if self._listener_task:
            self._listener_task.cancel()
        if self._pubsub:
            await self._pubsub.punsubscribe()
            await self._pubsub.close()
        if self._redis:
            await self._redis.aclose()

    async def connect_fleet(self, ws: WebSocket) -> None:
        await ws.accept()
        self._fleet_connections.add(ws)
        logger.debug("Fleet WS connected, total: %d", len(self._fleet_connections))

    async def connect_train(self, ws: WebSocket, train_number: str) -> None:
        await ws.accept()
        self._train_connections[train_number].add(ws)
        logger.debug("Train WS connected: %s, total: %d", train_number, len(self._train_connections[train_number]))

    def disconnect_fleet(self, ws: WebSocket) -> None:
        self._fleet_connections.discard(ws)

    def disconnect_train(self, ws: WebSocket, train_number: str) -> None:
        self._train_connections[train_number].discard(ws)

    async def publish(self, train_number: str, payload: dict[str, Any]) -> None:
        """Publish a prediction update to Redis so all API instances relay it."""
        if self._redis:
            await self._redis.publish(
                f"predictions:{train_number}", json.dumps(payload)
            )

    async def _listen(self) -> None:
        """Background task that relays Redis pub/sub messages to WebSocket clients."""
        if not self._pubsub:
            return
        try:
            async for message in self._pubsub.listen():
                if message["type"] not in ("pmessage", "message"):
                    continue
                channel: str = message.get("channel", "")
                data_str: str = message.get("data", "{}")
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                train_number = channel.replace("predictions:", "")
                await self._broadcast(train_number, data)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("WebSocket listener error: %s", exc)

    async def _broadcast(self, train_number: str, payload: dict) -> None:
        """Send to all interested connections — handle disconnects gracefully."""
        dead_fleet: set[WebSocket] = set()
        dead_train: set[WebSocket] = set()

        # Send to train-specific connections
        for ws in list(self._train_connections.get(train_number, set())):
            try:
                await ws.send_json(payload)
            except Exception:
                dead_train.add(ws)

        # Send to fleet connections
        for ws in list(self._fleet_connections):
            try:
                await ws.send_json(payload)
            except Exception:
                dead_fleet.add(ws)

        # Clean up dead connections
        for ws in dead_train:
            self._train_connections[train_number].discard(ws)
        for ws in dead_fleet:
            self._fleet_connections.discard(ws)


# Singleton — created once, shared across the process
manager = ConnectionManager()
