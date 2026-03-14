from fastapi import APIRouter
from app.services.football import get_match_detail
router = APIRouter(prefix='/matches', tags=['matches'])
@router.get('/{match_id}')
async def match_detail(match_id: int):
    data = await get_match_detail(match_id)
    if not data:
        return {'status': 'error', 'message': 'Match not found'}
    return {'status': 'ok', 'match': data}
