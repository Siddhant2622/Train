"""WebSocket realtime gateway router."""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.realtime.manager import manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["realtime"])


@router.websocket("/ws/fleet")
async def ws_fleet(websocket: WebSocket) -> None:
    """Stream live updates for the entire active fleet.
    
    Clients receive a JSON message every time any train's position or ETA changes.
    Message format: see IngestRouter → ws_payload structure.
    """
    await manager.connect_fleet(websocket)
    try:
        while True:
            # Keep connection alive — client sends pings, we echo
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect_fleet(websocket)
        logger.debug("Fleet WS disconnected")


@router.websocket("/ws/trains/{train_number}")
async def ws_train(websocket: WebSocket, train_number: str) -> None:
    """Stream live updates for a single train.
    
    Clients receive position + ETA updates every time a new position ping
    is processed for this train. Much lower message volume than /ws/fleet.
    """
    await manager.connect_train(websocket, train_number)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect_train(websocket, train_number)
        logger.debug("Train WS disconnected: %s", train_number)
