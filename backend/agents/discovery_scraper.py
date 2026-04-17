import feedparser
import requests
import time
import traceback
import random
from datetime import datetime

TRENDING_RSS_URL = "https://trends.google.com/trending/rss?geo=US"


def fetch_trending_now():
    print("[discovery] Fetching trending RSS from Google Trends")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; WiingyBot/1.0)',
            'Accept': 'application/rss+xml, application/xml, text/xml'
        }

        response = requests.get(
            TRENDING_RSS_URL,
            headers=headers,
            timeout=15
        )
        print(f"[discovery] RSS response status: {response.status_code}")

        if response.status_code != 200:
            print(f"[discovery] RSS request failed with status {response.status_code}")
            return []

        feed = feedparser.parse(response.text)
        print(f"[discovery] RSS feed entries: {len(feed.entries)}")

        if not feed.entries:
            print("[discovery] No entries in RSS feed")
            return []

        results = []
        for i, entry in enumerate(feed.entries[:20]):
            title = entry.get('title', '')

            traffic = ''
            if hasattr(entry, 'ht_approx_traffic'):
                traffic = entry.ht_approx_traffic

            articles = []
            news_items = []
            for key in entry.keys():
                if 'news_item_title' in key.lower():
                    val = entry.get(key, '')
                    if val and val not in news_items:
                        news_items.append(str(val))
            if news_items:
                articles = news_items[:3]
            elif hasattr(entry, 'ht_news_item_title'):
                articles = [entry.ht_news_item_title]

            started = ''
            if entry.get('published', ''):
                started = entry.published[:16]

            picture = ''
            if hasattr(entry, 'ht_picture'):
                picture = entry.ht_picture

            results.append({
                "rank": i + 1,
                "query": title,
                "category": "",
                "traffic": traffic,
                "started": started,
                "articles": articles,
                "picture": picture,
            })

            print(f"[discovery] Parsed trend {i+1}: {title} (traffic: {traffic})")

        print(f"[discovery] fetch_trending_now returning {len(results)} items")
        return results

    except Exception as e:
        print(f"[discovery] fetch_trending_now error: {e}")
        traceback.print_exc()
        return []


def fetch_realtime_trends():
    print("[discovery] fetch_realtime_trends: using trending RSS data only")
    return []


def build_discovery_data():
    print("[discovery] Starting build_discovery_data")
    start = time.time()

    top20 = fetch_trending_now()

    error = None
    if not top20:
        error = "Google Trends RSS returned no data. Please try again."

    quadrant_data = []
    for item in top20:
        rank = item["rank"]

        velocity = max(95 - ((rank - 1) * 4), 15)

        article_count = len(item.get("articles", []))
        if article_count == 0:
            coverage = 15
        elif article_count == 1:
            coverage = 30
        elif article_count == 2:
            coverage = 50
        else:
            coverage = min(65 + ((article_count - 3) * 10), 90)

        random.seed(rank)
        velocity = min(100, max(5, velocity + random.randint(-8, 8)))
        coverage = min(100, max(5, coverage + random.randint(-5, 5)))

        quadrant_data.append({
            "query": item["query"],
            "velocity": velocity,
            "coverage": coverage,
            "articles": item.get("articles", []),
            "traffic": item.get("traffic", ""),
            "started": item.get("started", ""),
            "rank": rank,
        })

    result = {
        "quadrant_data": quadrant_data,
        "top20": top20,
        "cached_at": datetime.utcnow().isoformat(),
        "error": error,
    }

    print(f"[discovery] Completed in {time.time()-start:.1f}s — "
          f"{len(top20)} trends, {len(quadrant_data)} quadrant points")
    return result
