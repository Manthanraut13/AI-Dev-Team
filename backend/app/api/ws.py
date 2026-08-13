import asyncio
from typing import Dict, Set
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self._connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, project_id: str, ws: WebSocket):
        await ws.accept()
        if project_id not in self._connections:
            self._connections[project_id] = set()
        self._connections[project_id].add(ws)
        logger.info(f"WS connected: {project_id}")

    def disconnect(self, project_id: str, ws: WebSocket):
        if project_id in self._connections:
            self._connections[project_id].discard(ws)
            if not self._connections[project_id]:
                del self._connections[project_id]
        logger.info(f"WS disconnected: {project_id}")

    async def broadcast(self, project_id: str, data: dict):
        if project_id not in self._connections:
            return
        msg = json.dumps(data, default=str)
        dead = []
        for ws in self._connections[project_id]:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections[project_id].discard(ws)

    def is_connected(self, project_id: str) -> bool:
        return bool(self._connections.get(project_id))


manager = ConnectionManager()
