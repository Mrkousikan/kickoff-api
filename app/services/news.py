import feedparser
import httpx
from typing import List, Dict, Optional
from datetime import datetime
from app.core.cache import cache_get, cache_set
from app.core.config import get_settings

settings = get_settings()

RSS_FEEDS = [
    {"name": "BBC Sport Football", "url": "https://feeds.bbci.co.uk/sport/football/rss.xml"},
    {"name": "Sky Sports Football", "url": "https://www.skysports.com/rss/12040"},
    {"name": "Goal.com",            "url": "https://www.goal.com/feeds/en/news"},
    {"name": "The Guardian Football","url": "https://www.theguardian.com/football/rss"},
]


def _parse_date(entry) -> str:
    try:
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            return datetime(*entry.published_parsed[:6]).isoformat()
    except Exception:
        pass
    return datetime.now().isoformat()


def _extract_image(entry) -> Optional[str]:
    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        return entry.media_thumbnail[0].get("url")
    if hasattr(entry, "media_content") and entry.media_content:
        return entry.media_content[0].get("url")
    if hasattr(entry, "links"):
        for link in entry.links:
            if link.get("type", "").startswith("image"):
                return link.get("href")
    return None


async def _fetch_rss(feed_url: str, source_name: str) -> List[Dict]:
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(feed_url, follow_redirects=True,
                headers={"User-Agent": "KickOff/1.0 Football News Aggregator"})
            feed = feedparser.parse(resp.text)
    except Exception:
        return []

    items = []
    for entry in feed.entries[:10]:
        summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
        summary = summary[:300].strip() if summary else ""

        items.append({
            "title": getattr(entry, "title", ""),
            "summary": summary,
            "url": getattr(entry, "link", ""),
            "source": source_name,
            "published": _parse_date(entry),
            "image": _extract_image(entry),
        })
    return items


async def get_football_news(query: Optional[str] = None) -> List[Dict]:
    cache_key = f"news:{query or 'all'}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    all_items: List[Dict] = []
    for feed in RSS_FEEDS:
        items = await _fetch_rss(feed["url"], feed["name"])
        all_items.extend(items)

    all_items.sort(key=lambda x: x["published"], reverse=True)

    if query:
        q = query.lower()
        all_items = [i for i in all_items if q in i["title"].lower() or q in i["summary"].lower()]

    result = all_items[:40]

    if not result:
        result = _mock_news()

    await cache_set(cache_key, result, settings.news_ttl)
    return result


def _mock_news() -> List[Dict]:
    return [
        {
            "title": "Mbappé hat-trick fires Real Madrid into Champions League semis",
            "summary": "Kylian Mbappé scored three times as Real Madrid demolished their opponents in a stunning European night at the Bernabéu.",
            "url": "https://example.com/news/1",
            "source": "BBC Sport Football",
            "published": datetime.now().isoformat(),
            "image": None,
        },
        {
            "title": "Premier League title race hots up with five games to go",
            "summary": "The top four teams are separated by just three points as the most competitive Premier League season in years enters its final stretch.",
            "url": "https://example.com/news/2",
            "source": "Sky Sports Football",
            "published": datetime.now().isoformat(),
            "image": None,
        },
        {
            "title": "Salah signs historic long-term deal at Liverpool",
            "summary": "Mohamed Salah has committed his future to Liverpool, signing an extension that keeps him at Anfield until 2027.",
            "url": "https://example.com/news/3",
            "source": "The Guardian Football",
            "published": datetime.now().isoformat(),
            "image": None,
        },
    ]
