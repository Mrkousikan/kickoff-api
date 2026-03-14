import asyncio
import json
from typing import Dict, Set
from fastapi import WebSocket
from app.services.football import get_live_scores


class ConnectionManager:
    def __init__(self):
        # Maps league_id (or "all") -> set of connected websockets
        self._rooms: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket, room: str = "all"):
        await ws.accept()
        async with self._lock:
            if room not in self._rooms:
                self._rooms[room] = set()
            self._rooms[room].add(ws)
        print(f"[WS] Client connected to room '{room}' | total in room: {len(self._rooms[room])}")

    async def disconnect(self, ws: WebSocket, room: str = "all"):
        async with self._lock:
            self._rooms.get(room, set()).discard(ws)
        print(f"[WS] Client disconnected from room '{room}'")

    async def broadcast(self, room: str, message: dict):
        payload = json.dumps(message)
        dead: Set[WebSocket] = set()
        for ws in list(self._rooms.get(room, set())):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)
        async with self._lock:
            self._rooms.get(room, set()).difference_update(dead)

    async def broadcast_all(self, message: dict):
        for room in list(self._rooms.keys()):
            await self.broadcast(room, message)

    def room_size(self, room: str) -> int:
        return len(self._rooms.get(room, set()))

    def total_connections(self) -> int:
        return sum(len(v) for v in self._rooms.values())


manager = ConnectionManager()


async def live_score_broadcaster():
    """Background task — fetches live scores every 30s and pushes to all WS clients."""
    while True:
        await asyncio.sleep(30)
        if manager.total_connections() == 0:
            continue
        try:
            scores = await get_live_scores()
            msg = {"type": "live_scores", "data": {"matches": scores, "count": len(scores)}}
            await manager.broadcast_all(msg)
            print(f"[WS] Broadcast live scores to {manager.total_connections()} clients")
        except Exception as e:
            print(f"[WS] Broadcast error: {e}")
