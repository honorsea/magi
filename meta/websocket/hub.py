"""
MAGI Meta Layer — WebSocket Hub.

Manages WebSocket connections and routes events from SimulationManager
bridges to connected frontend clients.
"""

import asyncio
import json
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from magi.meta.services.sim_manager import get_manager

router = APIRouter()


class ConnectionManager:
    """Manages a set of active WebSocket connections per channel."""

    def __init__(self):
        # sim_id → set of active WebSocket connections
        self._sim_connections: Dict[str, Set[WebSocket]] = {}

    async def connect_sim(self, sim_id: str, ws: WebSocket) -> None:
        await ws.accept()
        if sim_id not in self._sim_connections:
            self._sim_connections[sim_id] = set()
        self._sim_connections[sim_id].add(ws)

    def disconnect_sim(self, sim_id: str, ws: WebSocket) -> None:
        if sim_id in self._sim_connections:
            self._sim_connections[sim_id].discard(ws)

    async def broadcast_sim(self, sim_id: str, message: dict) -> None:
        conns = self._sim_connections.get(sim_id, set()).copy()
        dead = set()
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self._sim_connections.get(sim_id, set()).discard(ws)


_manager = ConnectionManager()


@router.websocket("/ws/simulation/{sim_id}")
async def simulation_ws(sim_id: str, websocket: WebSocket):
    """
    WebSocket endpoint for real-time simulation event streaming.

    The client connects here after starting a simulation. Events are
    pushed as JSON objects: {"type": "...", "data": {...}}.
    """
    await _manager.connect_sim(sim_id, websocket)
    sim_manager = get_manager()

    try:
        # Stream events from the simulation bridge
        async for event in sim_manager.subscribe(sim_id):
            await _manager.broadcast_sim(sim_id, event)
            # Also echo to the current connection in case broadcast missed it
            # (broadcast covers all connections, which is correct)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        _manager.disconnect_sim(sim_id, websocket)
