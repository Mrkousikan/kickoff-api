from fastapi import APIRouter, Query
from typing import Optional
from app.services.news import get_football_news

router = APIRouter(prefix='/news', tags=['news'])

@router.get('/')
async def football_news(q: Optional[str] = Query(None)):
    items = await get_football_news(q)
    return {'status': 'ok', 'count': len(items), 'news': items}
