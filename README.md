# KickOff API — Phase 1

Real-time football backend built with FastAPI, WebSockets, and Redis.

## Features
- Live scores via WebSocket (auto-broadcast every 30s)
- Today's fixtures
- League standings
- Top scorers
- Match predictions
- Football news aggregated from RSS feeds
- Redis caching to stay within free API tier limits
- Mock data fallback when no API key is configured

## Quick Start

### 1. Clone and set up
```bash
cd kickoff
cp .env.example .env
# Edit .env and add your API_FOOTBALL_KEY
```

### 2. Get a free API key
- Go to https://rapidapi.com/api-sports/api/api-football
- Subscribe to the free plan (100 requests/day)
- Copy your RapidAPI key into `.env`

### 3. Run with Docker (recommended)
```bash
docker-compose up
```

### 3b. Run without Docker
```bash
pip install -r requirements.txt
# Start Redis separately, or skip (app works without Redis, just no caching)
uvicorn app.main:app --reload
```

### 4. Open the docs
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/scores/live` | All live matches right now |
| GET | `/api/v1/scores/today` | Today's fixtures |
| GET | `/api/v1/scores/standings/{league_id}` | League table |
| GET | `/api/v1/scores/top-scorers/{league_id}` | Top goal scorers |
| GET | `/api/v1/scores/prediction/{fixture_id}` | Match prediction |
| GET | `/api/v1/scores/leagues` | Supported league IDs |
| GET | `/api/v1/news/` | Football news feed |
| WS  | `/api/v1/scores/ws/all` | Live scores WebSocket |
| WS  | `/api/v1/scores/ws/39` | Premier League only |

## League IDs
| League | ID |
|--------|----|
| Premier League | 39 |
| La Liga | 140 |
| Serie A | 135 |
| Bundesliga | 78 |
| Ligue 1 | 61 |
| Champions League | 2 |
| ISL (India) | 323 |

## Test WebSocket
```bash
pip install websockets
python tests/test_ws.py
```

## Project Structure
```
kickoff/
├── app/
│   ├── main.py              # FastAPI app + startup
│   ├── core/
│   │   ├── config.py        # Settings from .env
│   │   └── cache.py         # Redis async client
│   ├── models/
│   │   └── schemas.py       # Pydantic models
│   ├── services/
│   │   ├── football.py      # API-Football integration
│   │   ├── news.py          # RSS news aggregator
│   │   └── websocket.py     # WS manager + broadcaster
│   └── routers/
│       ├── scores.py        # Score/fixture/prediction routes
│       └── news.py          # News routes
├── tests/
│   └── test_ws.py           # WebSocket test client
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Next: Phase 2
Run `npm create vite@latest kickoff-pwa -- --template react` to scaffold the React PWA frontend.
