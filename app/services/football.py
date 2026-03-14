import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from app.core.config import get_settings
from app.core.cache import cache_get, cache_set
from app.models.schemas import (
    LiveMatch, TeamInfo, GoalInfo, FixtureInfo, FixtureStatus,
    MatchEvent, Standing, PlayerStat, PredictionResult
)

settings = get_settings()

BASE_URL = "https://api-football-v1.p.rapidapi.com/v3"
HEADERS = {
    "X-RapidAPI-Key": settings.api_football_key,
    "X-RapidAPI-Host": settings.api_football_host,
}

# Popular league IDs
LEAGUES = {
    "premier_league": 39,
    "la_liga": 140,
    "serie_a": 135,
    "bundesliga": 78,
    "ligue_1": 61,
    "champions_league": 2,
    "isl": 323,           # Indian Super League
}


async def _fetch(endpoint: str, params: Dict[str, Any]) -> Optional[Dict]:
    if not settings.api_football_key or settings.api_football_key == "your_rapidapi_key_here":
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{BASE_URL}/{endpoint}", headers=HEADERS, params=params)
            r.raise_for_status()
            return r.json()
    except Exception as e:
        print(f"API fetch error [{endpoint}]: {e}")
        return None


def _parse_live_match(item: Dict) -> LiveMatch:
    f = item["fixture"]
    teams = item["teams"]
    goals = item["goals"]
    league = item["league"]
    events_raw = item.get("events", [])

    events = []
    for ev in events_raw:
        events.append(MatchEvent(
            time=ev["time"]["elapsed"] or 0,
            team=ev["team"]["name"],
            player=ev["player"]["name"] or "Unknown",
            type=ev["type"],
            detail=ev["detail"],
        ))

    return LiveMatch(
        fixture=FixtureInfo(
            id=f["id"],
            date=f["date"],
            venue=f.get("venue", {}).get("name"),
            status=FixtureStatus(
                long=f["status"]["long"],
                short=f["status"]["short"],
                elapsed=f["status"].get("elapsed"),
            ),
        ),
        home_team=TeamInfo(id=teams["home"]["id"], name=teams["home"]["name"], logo=teams["home"]["logo"]),
        away_team=TeamInfo(id=teams["away"]["id"], name=teams["away"]["name"], logo=teams["away"]["logo"]),
        goals=GoalInfo(home=goals["home"], away=goals["away"]),
        league_name=league["name"],
        league_logo=league.get("logo"),
        events=events,
    )


async def get_live_scores(league_id: Optional[int] = None) -> List[Dict]:
    cache_key = f"live:{league_id or 'all'}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    params = {"live": "all"}
    if league_id:
        params["league"] = league_id

    data = await _fetch("fixtures", params)
    if not data:
        return _mock_live_scores()

    result = [_parse_live_match(item).model_dump() for item in data.get("response", [])]
    await cache_set(cache_key, result, settings.live_score_ttl)
    return result


async def get_fixtures_today(league_id: Optional[int] = None) -> List[Dict]:
    today = date.today().isoformat()
    cache_key = f"fixtures:{today}:{league_id or 'all'}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    params = {"date": today, "timezone": "Asia/Kolkata"}
    if league_id:
        params["league"] = league_id
        params["season"] = datetime.now().year

    data = await _fetch("fixtures", params)
    if not data:
        return []

    result = [_parse_live_match(item).model_dump() for item in data.get("response", [])]
    await cache_set(cache_key, result, settings.fixtures_ttl)
    return result


async def get_standings(league_id: int, season: Optional[int] = None) -> List[Dict]:
    season = season or datetime.now().year
    cache_key = f"standings:{league_id}:{season}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    data = await _fetch("standings", {"league": league_id, "season": season})
    if not data or not data.get("response"):
        return []

    standings_raw = data["response"][0]["league"]["standings"][0]
    result = []
    for item in standings_raw:
        s = Standing(
            rank=item["rank"],
            team=TeamInfo(id=item["team"]["id"], name=item["team"]["name"], logo=item["team"]["logo"]),
            played=item["all"]["played"],
            won=item["all"]["win"],
            drawn=item["all"]["draw"],
            lost=item["all"]["lose"],
            goals_for=item["all"]["goals"]["for"],
            goals_against=item["all"]["goals"]["against"],
            goal_diff=item["goalsDiff"],
            points=item["points"],
            form=item.get("form"),
        )
        result.append(s.model_dump())

    await cache_set(cache_key, result, settings.standings_ttl)
    return result


async def get_top_scorers(league_id: int, season: Optional[int] = None) -> List[Dict]:
    season = season or datetime.now().year
    cache_key = f"scorers:{league_id}:{season}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    data = await _fetch("players/topscorers", {"league": league_id, "season": season})
    if not data:
        return []

    result = []
    for item in data.get("response", [])[:20]:
        p = item["player"]
        stats = item["statistics"][0]
        ps = PlayerStat(
            id=p["id"],
            name=p["name"],
            photo=p.get("photo"),
            team=stats["team"]["name"],
            goals=stats["goals"]["total"] or 0,
            assists=stats["goals"]["assists"] or 0,
            appearances=stats["games"]["appearences"] or 0,
            rating=float(stats["games"]["rating"]) if stats["games"].get("rating") else None,
        )
        result.append(ps.model_dump())

    await cache_set(cache_key, result, settings.standings_ttl)
    return result


async def get_prediction(fixture_id: int) -> Optional[Dict]:
    cache_key = f"prediction:{fixture_id}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    data = await _fetch("predictions", {"fixture": fixture_id})
    if not data or not data.get("response"):
        return None

    pred = data["response"][0]
    teams = pred["teams"]
    winner = pred["predictions"].get("winner", {})
    percent = pred["predictions"].get("percent", {})

    def pct(v):
        return float(str(v).replace("%", "") or 0)

    result = PredictionResult(
        fixture_id=fixture_id,
        home_team=teams["home"]["name"],
        away_team=teams["away"]["name"],
        home_win_pct=pct(percent.get("home", "0%")),
        draw_pct=pct(percent.get("draws", "0%")),
        away_win_pct=pct(percent.get("away", "0%")),
        prediction=winner.get("name", "Draw") if winner else "Draw",
        confidence="High" if max(pct(percent.get("home","0%")), pct(percent.get("away","0%"))) > 60 else "Medium",
        advice=pred["predictions"].get("advice", ""),
    ).model_dump()

    await cache_set(cache_key, result, settings.fixtures_ttl)
    return result


def _mock_live_scores() -> List[Dict]:
    """Returns mock data when no API key is configured — for dev/demo purposes."""
    return [
        {
            "fixture": {"id": 1001, "date": "2025-03-14T18:00:00+00:00", "venue": "Old Trafford", "status": {"long": "First Half", "short": "1H", "elapsed": 34}},
            "home_team": {"id": 33, "name": "Manchester United", "logo": "https://media.api-sports.io/football/teams/33.png"},
            "away_team": {"id": 40, "name": "Liverpool", "logo": "https://media.api-sports.io/football/teams/40.png"},
            "goals": {"home": 1, "away": 2},
            "league_name": "Premier League",
            "league_logo": "https://media.api-sports.io/football/leagues/39.png",
            "events": [
                {"time": 12, "team": "Liverpool", "player": "M. Salah", "type": "Goal", "detail": "Normal Goal"},
                {"time": 28, "team": "Manchester United", "player": "R. Højlund", "type": "Goal", "detail": "Normal Goal"},
                {"time": 31, "team": "Liverpool", "player": "L. Díaz", "type": "Goal", "detail": "Normal Goal"},
            ],
        },
        {
            "fixture": {"id": 1002, "date": "2025-03-14T20:00:00+00:00", "venue": "Santiago Bernabéu", "status": {"long": "Second Half", "short": "2H", "elapsed": 67}},
            "home_team": {"id": 541, "name": "Real Madrid", "logo": "https://media.api-sports.io/football/teams/541.png"},
            "away_team": {"id": 529, "name": "Barcelona", "logo": "https://media.api-sports.io/football/teams/529.png"},
            "goals": {"home": 2, "away": 1},
            "league_name": "La Liga",
            "league_logo": "https://media.api-sports.io/football/leagues/140.png",
            "events": [
                {"time": 22, "team": "Real Madrid", "player": "K. Mbappé", "type": "Goal", "detail": "Normal Goal"},
                {"time": 45, "team": "Barcelona", "player": "R. Lewandowski", "type": "Goal", "detail": "Normal Goal"},
                {"time": 58, "team": "Real Madrid", "player": "V. Jr.", "type": "Goal", "detail": "Normal Goal"},
            ],
        },
    ]
