from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from typing import Optional
import asyncio
import json
from app.services.football import (
    get_live_scores, get_fixtures_today, get_standings,
    get_top_scorers, get_prediction, LEAGUES
)
from app.services.websocket import manager

router = APIRouter(prefix="/scores", tags=["scores"])


@router.get("/live")
async def live_scores(league: Optional[int] = Query(None, description="Filter by league ID")):
    """Get all currently live matches."""
    matches = await get_live_scores(league)
    return {"status": "ok", "count": len(matches), "matches": matches}


@router.get("/today")
async def today_fixtures(league: Optional[int] = Query(None)):
    """Get all fixtures scheduled for today."""
    fixtures = await get_fixtures_today(league)
    return {"status": "ok", "count": len(fixtures), "fixtures": fixtures}


@router.get("/standings/{league_id}")
async def standings(league_id: int, season: Optional[int] = None):
    """Get league table for a given league."""
    data = await get_standings(league_id, season)
    return {"status": "ok", "league_id": league_id, "standings": data}


@router.get("/top-scorers/{league_id}")
async def top_scorers(league_id: int, season: Optional[int] = None):
    """Top goal scorers for a league this season."""
    data = await get_top_scorers(league_id, season)
    return {"status": "ok", "league_id": league_id, "players": data}


@router.get("/prediction/{fixture_id}")
async def match_prediction(fixture_id: int):
    """AI-powered win/draw/loss prediction for a fixture."""
    data = await get_prediction(fixture_id)
    if not data:
        return {"status": "error", "message": "Prediction not available for this fixture"}
    return {"status": "ok", "prediction": data}


@router.get("/leagues")
async def get_leagues():
    """List of supported league IDs."""
    return {"leagues": LEAGUES}


@router.websocket("/ws/{room}")
async def websocket_scores(ws: WebSocket, room: str = "all"):
    """
    WebSocket endpoint for real-time score updates.
    Connect to /ws/all  for all leagues
    Connect to /ws/39   for Premier League only
    On connect: immediately sends current live scores.
    Then receives updates every 30 seconds.
    """
    await manager.connect(ws, room)
    try:
        # Send current scores immediately on connect
        league_id = int(room) if room.isdigit() else None
        scores = await get_live_scores(league_id)
        await ws.send_text(json.dumps({
            "type": "live_scores",
            "data": {"matches": scores, "count": len(scores)}
        }))

        # Keep connection alive — client can send pings
        while True:
            try:
                data = await asyncio.wait_for(ws.receive_text(), timeout=60)
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await ws.send_text(json.dumps({"type": "pong"}))
                elif msg.get("type") == "refresh":
                    scores = await get_live_scores(league_id)
                    await ws.send_text(json.dumps({
                        "type": "live_scores",
                        "data": {"matches": scores, "count": len(scores)}
                    }))
            except asyncio.TimeoutError:
                await ws.send_text(json.dumps({"type": "ping"}))

    except WebSocketDisconnect:
        await manager.disconnect(ws, room)
