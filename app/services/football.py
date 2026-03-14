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
BASE_URL = 'https://api.football-data.org/v4'

def _headers():
    return {'X-Auth-Token': settings.api_football_key}

LEAGUES = {
    'premier_league': 2021,
    'la_liga': 2014,
    'serie_a': 2019,
    'bundesliga': 2002,
    'ligue_1': 2015,
    'champions_league': 2001,
}

async def _fetch(endpoint: str, params: Dict = {}) -> Optional[Dict]:
    if not settings.api_football_key or settings.api_football_key in ('your_rapidapi_key_here', 'demo', ''):
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f'{BASE_URL}/{endpoint}', headers=_headers(), params=params)
            r.raise_for_status()
            return r.json()
    except Exception as e:
        print(f'API fetch error [{endpoint}]: {e}')
        return None

async def get_live_scores(league_id: Optional[int] = None) -> List[Dict]:
    cache_key = f'live:{league_id or "all"}'
    cached = await cache_get(cache_key)
    if cached:
        return cached
    data = await _fetch('matches', {'status': 'LIVE'})
    if not data:
        return _mock_live_scores()
    matches = []
    for m in data.get('matches', []):
        matches.append(_parse_match(m))
    await cache_set(cache_key, matches, settings.live_score_ttl)
    return matches

async def get_fixtures_today(league_id: Optional[int] = None) -> List[Dict]:
    today = date.today().isoformat()
    cache_key = f'fixtures:{today}'
    cached = await cache_get(cache_key)
    if cached:
        return cached
    data = await _fetch('matches', {'dateFrom': today, 'dateTo': today})
    if not data:
        return []
    result = [_parse_match(m) for m in data.get('matches', [])]
    await cache_set(cache_key, result, settings.fixtures_ttl)
    return result

def _parse_match(m: Dict) -> Dict:
    home = m.get('homeTeam', {})
    away = m.get('awayTeam', {})
    score = m.get('score', {}).get('fullTime', {})
    status = m.get('status', 'SCHEDULED')
    elapsed = None
    short = 'NS'
    if status == 'IN_PLAY': short = '1H'
    elif status == 'PAUSED': short = 'HT'
    elif status == 'FINISHED': short = 'FT'
    elif status == 'SCHEDULED': short = 'NS'
    return {
        'fixture': {'id': m.get('id', 0), 'date': m.get('utcDate', ''), 'venue': None, 'status': {'long': status, 'short': short, 'elapsed': elapsed}},
        'home_team': {'id': home.get('id', 0), 'name': home.get('name', ''), 'logo': home.get('crest', '')},
        'away_team': {'id': away.get('id', 0), 'name': away.get('name', ''), 'logo': away.get('crest', '')},
        'goals': {'home': score.get('home'), 'away': score.get('away')},
        'league_name': m.get('competition', {}).get('name', ''),
        'league_logo': m.get('competition', {}).get('emblem', ''),
        'events': [],
    }

async def get_standings(league_id: int, season: Optional[int] = None) -> List[Dict]:
    cache_key = f'standings:{league_id}'
    cached = await cache_get(cache_key)
    if cached:
        return cached
    data = await _fetch(f'competitions/{league_id}/standings')
    if not data:
        return []
    table = data.get('standings', [{}])[0].get('table', [])
    result = []
    for item in table:
        team = item.get('team', {})
        result.append({
            'rank': item.get('position', 0),
            'team': {'id': team.get('id', 0), 'name': team.get('name', ''), 'logo': team.get('crest', '')},
            'played': item.get('playedGames', 0),
            'won': item.get('won', 0),
            'drawn': item.get('draw', 0),
            'lost': item.get('lost', 0),
            'goals_for': item.get('goalsFor', 0),
            'goals_against': item.get('goalsAgainst', 0),
            'goal_diff': item.get('goalDifference', 0),
            'points': item.get('points', 0),
            'form': item.get('form', ''),
        })
    await cache_set(cache_key, result, settings.standings_ttl)
    return result

async def get_top_scorers(league_id: int, season: Optional[int] = None) -> List[Dict]:
    cache_key = f'scorers:{league_id}'
    cached = await cache_get(cache_key)
    if cached:
        return cached
    data = await _fetch(f'competitions/{league_id}/scorers')
    if not data:
        return []
    result = []
    for item in data.get('scorers', []):
        p = item.get('player', {})
        team = item.get('team', {})
        result.append({
            'id': p.get('id', 0),
            'name': p.get('name', ''),
            'photo': None,
            'team': team.get('name', ''),
            'goals': item.get('goals', 0),
            'assists': item.get('assists', 0) or 0,
            'appearances': item.get('playedMatches', 0),
            'rating': None,
        })
    await cache_set(cache_key, result, settings.standings_ttl)
    return result

async def get_prediction(fixture_id: int) -> Optional[Dict]:
    return None

def _mock_live_scores() -> List[Dict]:
    return [
        {
            'fixture': {'id': 1001, 'date': '2025-03-14T18:00:00+00:00', 'venue': 'Old Trafford', 'status': {'long': 'First Half', 'short': '1H', 'elapsed': 34}},
            'home_team': {'id': 33, 'name': 'Manchester United', 'logo': 'https://crests.football-data.org/66.png'},
            'away_team': {'id': 40, 'name': 'Liverpool', 'logo': 'https://crests.football-data.org/64.png'},
            'goals': {'home': 1, 'away': 2},
            'league_name': 'Premier League',
            'league_logo': '',
            'events': [
                {'time': 12, 'team': 'Liverpool', 'player': 'M. Salah', 'type': 'Goal', 'detail': 'Normal Goal'},
                {'time': 28, 'team': 'Manchester United', 'player': 'R. Hojlund', 'type': 'Goal', 'detail': 'Normal Goal'},
                {'time': 31, 'team': 'Liverpool', 'player': 'L. Diaz', 'type': 'Goal', 'detail': 'Normal Goal'},
            ],
        },
        {
            'fixture': {'id': 1002, 'date': '2025-03-14T20:00:00+00:00', 'venue': 'Santiago Bernabeu', 'status': {'long': 'Second Half', 'short': '2H', 'elapsed': 67}},
            'home_team': {'id': 541, 'name': 'Real Madrid', 'logo': 'https://crests.football-data.org/86.png'},
            'away_team': {'id': 529, 'name': 'Barcelona', 'logo': 'https://crests.football-data.org/81.png'},
            'goals': {'home': 2, 'away': 1},
            'league_name': 'La Liga',
            'league_logo': '',
            'events': [
                {'time': 22, 'team': 'Real Madrid', 'player': 'K. Mbappe', 'type': 'Goal', 'detail': 'Normal Goal'},
                {'time': 45, 'team': 'Barcelona', 'player': 'R. Lewandowski', 'type': 'Goal', 'detail': 'Normal Goal'},
                {'time': 58, 'team': 'Real Madrid', 'player': 'V. Jr.', 'type': 'Goal', 'detail': 'Normal Goal'},
            ],
        },
    ]

async def get_match_detail(match_id: int) -> dict:
    cache_key = f'match:{match_id}'
    cached = await cache_get(cache_key)
    if cached:
        return cached
    data = await _fetch(f'matches/{match_id}')
    if not data:
        return None
    m = data
    home = m.get('homeTeam', {})
    away = m.get('awayTeam', {})
    score = m.get('score', {})
    ft = score.get('fullTime', {})
    ht = score.get('halfTime', {})
    status = m.get('status', 'SCHEDULED')
    short = 'NS'
    if status == 'IN_PLAY': short = '1H'
    elif status == 'PAUSED': short = 'HT'
    elif status == 'FINISHED': short = 'FT'
    goals = m.get('goals', [])
    bookings = m.get('bookings', [])
    substitutions = m.get('substitutions', [])
    events = []
    for g in goals:
        events.append({'minute': g.get('minute', 0), 'type': 'Goal', 'team': g.get('team', {}).get('name', ''), 'player': g.get('scorer', {}).get('name', ''), 'detail': 'Normal Goal'})
    for b in bookings:
        events.append({'minute': b.get('minute', 0), 'type': 'Card', 'team': b.get('team', {}).get('name', ''), 'player': b.get('player', {}).get('name', ''), 'detail': b.get('card', '')})
    for s in substitutions:
        events.append({'minute': s.get('minute', 0), 'type': 'Sub', 'team': s.get('team', {}).get('name', ''), 'player': s.get('playerOut', {}).get('name', ''), 'detail': s.get('playerIn', {}).get('name', '')})
    events.sort(key=lambda x: x['minute'])
    home_lineup = [p.get('name', '') for p in m.get('lineups', [{}])[0].get('lineup', []) if m.get('lineups')]
    away_lineup = [p.get('name', '') for p in m.get('lineups', [{}])[1].get('lineup', []) if len(m.get('lineups', [])) > 1]
    result = {
        'fixture': {'id': m.get('id', 0), 'date': m.get('utcDate', ''), 'venue': m.get('venue', ''), 'status': {'long': status, 'short': short, 'elapsed': None}},
        'home_team': {'id': home.get('id', 0), 'name': home.get('name', ''), 'logo': home.get('crest', '')},
        'away_team': {'id': away.get('id', 0), 'name': away.get('name', ''), 'logo': away.get('crest', '')},
        'goals': {'home': ft.get('home'), 'away': ft.get('away')},
        'half_time': {'home': ht.get('home'), 'away': ht.get('away')},
        'league_name': m.get('competition', {}).get('name', ''),
        'league_logo': m.get('competition', {}).get('emblem', ''),
        'events': events,
        'home_lineup': home_lineup,
        'away_lineup': away_lineup,
        'referee': m.get('referees', [{}])[0].get('name', '') if m.get('referees') else '',
    }
    await cache_set(cache_key, result, 60)
    return result

async def get_match_detail(match_id: int) -> dict:
    cache_key = f'match:{match_id}'
    cached = await cache_get(cache_key)
    if cached:
        return cached
    data = await _fetch(f'matches/{match_id}')
    if not data:
        return None
    m = data
    home = m.get('homeTeam', {})
    away = m.get('awayTeam', {})
    score = m.get('score', {})
    ft = score.get('fullTime', {})
    ht = score.get('halfTime', {})
    status = m.get('status', 'SCHEDULED')
    short = 'NS'
    if status == 'IN_PLAY': short = '1H'
    elif status == 'PAUSED': short = 'HT'
    elif status == 'FINISHED': short = 'FT'
    goals = m.get('goals', [])
    bookings = m.get('bookings', [])
    substitutions = m.get('substitutions', [])
    events = []
    for g in goals:
        events.append({'minute': g.get('minute', 0), 'type': 'Goal', 'team': g.get('team', {}).get('name', ''), 'player': g.get('scorer', {}).get('name', ''), 'detail': 'Normal Goal'})
    for b in bookings:
        events.append({'minute': b.get('minute', 0), 'type': 'Card', 'team': b.get('team', {}).get('name', ''), 'player': b.get('player', {}).get('name', ''), 'detail': b.get('card', '')})
    for s in substitutions:
        events.append({'minute': s.get('minute', 0), 'type': 'Sub', 'team': s.get('team', {}).get('name', ''), 'player': s.get('playerOut', {}).get('name', ''), 'detail': s.get('playerIn', {}).get('name', '')})
    events.sort(key=lambda x: x['minute'])
    home_lineup = [p.get('name', '') for p in m.get('lineups', [{}])[0].get('lineup', []) if m.get('lineups')]
    away_lineup = [p.get('name', '') for p in m.get('lineups', [{}])[1].get('lineup', []) if len(m.get('lineups', [])) > 1]
    result = {
        'fixture': {'id': m.get('id', 0), 'date': m.get('utcDate', ''), 'venue': m.get('venue', ''), 'status': {'long': status, 'short': short, 'elapsed': None}},
        'home_team': {'id': home.get('id', 0), 'name': home.get('name', ''), 'logo': home.get('crest', '')},
        'away_team': {'id': away.get('id', 0), 'name': away.get('name', ''), 'logo': away.get('crest', '')},
        'goals': {'home': ft.get('home'), 'away': ft.get('away')},
        'half_time': {'home': ht.get('home'), 'away': ht.get('away')},
        'league_name': m.get('competition', {}).get('name', ''),
        'league_logo': m.get('competition', {}).get('emblem', ''),
        'events': events,
        'home_lineup': home_lineup,
        'away_lineup': away_lineup,
        'referee': m.get('referees', [{}])[0].get('name', '') if m.get('referees') else '',
    }
    await cache_set(cache_key, result, 60)
    return result
