import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.routers import scores, news
from app.services.websocket import live_score_broadcaster

settings = get_settings()
_broadcaster_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _broadcaster_task
    print("KickOff API starting up...")
    _broadcaster_task = asyncio.create_task(live_score_broadcaster())
    yield
    print("KickOff API shutting down...")
    if _broadcaster_task:
        _broadcaster_task.cancel()


app = FastAPI(
    title="KickOff API",
    description="Real-time football scores, news, stats & AI features",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scores.router, prefix="/api/v1")
app.include_router(news.router,   prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "app": "KickOff API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "live_scores":   "/api/v1/scores/live",
            "today":         "/api/v1/scores/today",
            "standings":     "/api/v1/scores/standings/{league_id}",
            "top_scorers":   "/api/v1/scores/top-scorers/{league_id}",
            "prediction":    "/api/v1/scores/prediction/{fixture_id}",
            "news":          "/api/v1/news/",
            "websocket":     "ws://localhost:8000/api/v1/scores/ws/{room}",
        }
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "app": "KickOff"}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(status_code=500, content={"status": "error", "message": str(exc)})




