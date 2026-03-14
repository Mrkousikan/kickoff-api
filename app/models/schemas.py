from pydantic import BaseModel
from typing import Optional, List


class TeamInfo(BaseModel):
    id: int
    name: str
    logo: Optional[str] = None


class GoalInfo(BaseModel):
    home: Optional[int] = None
    away: Optional[int] = None


class FixtureStatus(BaseModel):
    long: str
    short: str
    elapsed: Optional[int] = None


class FixtureInfo(BaseModel):
    id: int
    date: str
    venue: Optional[str] = None
    status: FixtureStatus


class MatchEvent(BaseModel):
    time: int
    team: str
    player: str
    type: str
    detail: str


class LiveMatch(BaseModel):
    fixture: FixtureInfo
    home_team: TeamInfo
    away_team: TeamInfo
    goals: GoalInfo
    league_name: str
    league_logo: Optional[str] = None
    events: List[MatchEvent] = []


class Standing(BaseModel):
    rank: int
    team: TeamInfo
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    goal_diff: int
    points: int
    form: Optional[str] = None


class PlayerStat(BaseModel):
    id: int
    name: str
    photo: Optional[str] = None
    team: str
    goals: int
    assists: int
    appearances: int
    rating: Optional[float] = None


class NewsItem(BaseModel):
    title: str
    summary: str
    url: str
    source: str
    published: str
    image: Optional[str] = None


class PredictionResult(BaseModel):
    fixture_id: int
    home_team: str
    away_team: str
    home_win_pct: float
    draw_pct: float
    away_win_pct: float
    prediction: str
    confidence: str
    advice: str


class WSMessage(BaseModel):
    type: str
    data: dict
