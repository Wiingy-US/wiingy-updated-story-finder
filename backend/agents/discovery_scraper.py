import feedparser
import requests
import time
import traceback
import re
import random
from datetime import datetime

FEEDS = [
    {
        "url": "https://trends.google.com/trending/rss?geo=US",
        "source": "US General",
        "category": "Trending"
    },
    {
        "url": "https://trends.google.com/trending/rss?geo=US&sort=search-volume",
        "source": "US Volume",
        "category": "Trending"
    },
    {
        "url": "https://news.google.com/rss/search?q=AI+education+learning&hl=en-US&gl=US&ceid=US:en",
        "source": "Google News AI Education",
        "category": "Tech & AI"
    },
    {
        "url": "https://news.google.com/rss/search?q=music+education+learning&hl=en-US&gl=US&ceid=US:en",
        "source": "Google News Music",
        "category": "Music"
    },
    {
        "url": "https://news.google.com/rss/search?q=edtech+online+learning+students&hl=en-US&gl=US&ceid=US:en",
        "source": "Google News Edtech",
        "category": "Education"
    },
    {
        "url": "https://news.google.com/rss/search?q=artificial+intelligence+students+schools&hl=en-US&gl=US&ceid=US:en",
        "source": "Google News AI Schools",
        "category": "Tech & AI"
    },
    {
        "url": "https://news.google.com/rss/search?q=SAT+ACT+college+admission+test+prep&hl=en-US&gl=US&ceid=US:en",
        "source": "Google News Test Prep",
        "category": "Education"
    },
    {
        "url": "https://news.google.com/rss/search?q=music+lessons+instrument+practice&hl=en-US&gl=US&ceid=US:en",
        "source": "Google News Music Lessons",
        "category": "Music"
    },
    {
        "url": "https://news.google.com/rss/search?q=coding+bootcamp+programming+kids&hl=en-US&gl=US&ceid=US:en",
        "source": "Google News Coding",
        "category": "Tech & AI"
    },
    {
        "url": "https://news.google.com/rss/search?q=homeschool+tutoring+parenting+education&hl=en-US&gl=US&ceid=US:en",
        "source": "Google News Homeschool",
        "category": "Education"
    }
]

INCLUDE_KEYWORDS = [
    'school', 'college', 'university', 'student', 'students', 'teacher',
    'education', 'learning', 'study', 'tutor', 'tutoring', 'classroom',
    'degree', 'course', 'exam', 'test prep', 'SAT', 'ACT', 'GRE', 'GMAT',
    'homework', 'scholarship', 'academy', 'training', 'lesson', 'lessons',
    'graduate', 'STEM', 'literacy', 'math', 'reading', 'curriculum',
    'edtech', 'online learning', 'e-learning', 'homeschool', 'preschool',
    'kindergarten', 'AP class', 'campus', 'admission',
    'AI', 'artificial intelligence', 'ChatGPT', 'machine learning',
    'coding', 'programming', 'Python', 'bootcamp', 'algorithm',
    'data science', 'computer science', 'Coursera', 'Khan Academy',
    'Duolingo', 'robot', 'tech skills',
    'music', 'song', 'album', 'concert', 'band', 'artist', 'singer',
    'piano', 'guitar', 'violin', 'instrument', 'orchestra', 'choir',
    'musical', 'Grammy', 'musician', 'music lesson', 'music school',
    'composition', 'jazz', 'classical', 'music education',
    'child', 'children', 'kids', 'parent', 'parenting', 'toddler',
    'teen', 'teenager', 'youth',
    'skill', 'skills', 'career', 'certification', 'upskill', 'workforce',
    'internship', 'job training',
]

EXCLUDE_KEYWORDS = [
    'nfl', 'nba', 'mlb', 'nhl', 'soccer', 'football', 'basketball',
    'baseball', 'tennis tournament', 'golf tournament', 'olympics',
    'super bowl', 'world cup', 'championship game', 'playoffs',
    'election', 'senator', 'congress', 'president', 'governor',
    'stock market', 'crypto', 'bitcoin', 'ethereum',
    'celebrity', 'kardashian', 'weather', 'hurricane', 'earthquake',
    'atp', 'wta', 'ufc', 'boxing', 'nascar', 'f1 ',
]


def is_relevant(title):
    title_lower = title.lower()
    for kw in EXCLUDE_KEYWORDS:
        if kw.lower() in title_lower:
            return False, "excluded"
    for kw in INCLUDE_KEYWORDS:
        if kw.lower() in title_lower:
            return True, "matched"
    return False, "no_match"


def parse_traffic(traffic_str):
    if not traffic_str:
        return 0
    s = traffic_str.upper().replace('+', '').replace(',', '').strip()
    try:
        if 'M' in s:
            return int(float(s.replace('M', '')) * 1_000_000)
        if 'K' in s:
            return int(float(s.replace('K', '')) * 1_000)
        return int(s)
    except (ValueError, TypeError):
        return 0


def fetch_feed(feed_info):
    url = feed_info["url"]
    source = feed_info["source"]
    category = feed_info["category"]

    print(f"[discovery] Fetching feed: {source}")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; WiingyBot/1.0)',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
        }
        response = requests.get(url, headers=headers, timeout=15)
        print(f"[discovery] {source} status: {response.status_code}, length: {len(response.text)}")

        if response.status_code != 200:
            return []

        feed = feedparser.parse(response.text)
        print(f"[discovery] {source} entries: {len(feed.entries)}")

        results = []
        for entry in feed.entries:
            title = entry.get('title', '').strip()
            if not title:
                continue

            title = re.sub(r'\s*-\s*[A-Z][^-]{2,40}$', '', title).strip()

            traffic = ''
            traffic_num = 0
            if hasattr(entry, 'ht_approx_traffic'):
                traffic = entry.ht_approx_traffic
                traffic_num = parse_traffic(traffic)

            articles = []
            for key in entry.keys():
                if 'news_item_title' in key.lower():
                    val = entry.get(key, '')
                    if val and str(val) not in articles:
                        articles.append(str(val))
            if not articles and entry.get('summary'):
                articles = [entry.summary[:100]]

            started = ''
            if entry.get('published', ''):
                started = entry.published[:16]

            results.append({
                "query": title,
                "category": category,
                "traffic": traffic,
                "traffic_num": traffic_num,
                "started": started,
                "articles": articles[:3],
                "feed_source": source,
            })

        return results

    except Exception as e:
        print(f"[discovery] Feed {source} error: {e}")
        traceback.print_exc()
        return []


def fetch_trending_now():
    print("[discovery] Starting multi-feed fetch")
    all_results = []

    for feed_info in FEEDS:
        results = fetch_feed(feed_info)
        all_results.extend(results)
        time.sleep(0.5)

    print(f"[discovery] Total raw results before filter: {len(all_results)}")

    filtered = []
    for item in all_results:
        relevant, reason = is_relevant(item["query"])
        if relevant:
            filtered.append(item)

    print(f"[discovery] After relevance filter: {len(filtered)}")

    if len(filtered) < 20:
        print("[discovery] Less than 20 after filter — relaxing to include all targeted feeds")
        filtered = [r for r in all_results
                    if r["feed_source"] != "US General"
                    and r["feed_source"] != "US Volume"]
        print(f"[discovery] After relaxing filter: {len(filtered)}")

    seen = set()
    deduped = []
    for item in filtered:
        key = item["query"].lower()[:60]
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    print(f"[discovery] After deduplication: {len(deduped)}")

    deduped.sort(key=lambda x: x.get("traffic_num", 0), reverse=True)

    final = []
    for i, item in enumerate(deduped[:50]):
        item["rank"] = i + 1
        final.append(item)

    print(f"[discovery] Final result count: {len(final)}")
    return final


def fetch_realtime_trends():
    return []


def build_discovery_data():
    print("[discovery] Starting build_discovery_data")
    start = time.time()

    top_results = fetch_trending_now()

    error = None
    if not top_results:
        error = "No relevant trending topics found. Please try again."

    quadrant_data = []
    for item in top_results:
        rank = item["rank"]
        velocity = max(95 - ((rank - 1) * 1.5), 15)

        article_count = len(item.get("articles", []))
        if article_count == 0:
            coverage = 15
        elif article_count == 1:
            coverage = 30
        elif article_count == 2:
            coverage = 50
        else:
            coverage = min(65 + ((article_count - 3) * 10), 90)

        random.seed(rank * 7)
        velocity = min(100, max(5, int(velocity) + random.randint(-10, 10)))
        coverage = min(100, max(5, coverage + random.randint(-8, 8)))

        quadrant_data.append({
            "query": item["query"],
            "velocity": velocity,
            "coverage": coverage,
            "articles": item.get("articles", []),
            "traffic": item.get("traffic", ""),
            "started": item.get("started", ""),
            "rank": rank,
            "category": item.get("category", ""),
        })

    result = {
        "quadrant_data": quadrant_data,
        "top20": top_results,
        "cached_at": datetime.utcnow().isoformat(),
        "error": error,
    }

    elapsed = time.time() - start
    print(f"[discovery] Completed in {elapsed:.1f}s")
    return result
