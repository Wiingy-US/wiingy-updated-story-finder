import feedparser
import requests
import time
import traceback
import random
import re
from datetime import datetime

CATEGORY_FEEDS = [
    ("education", "https://trends.google.com/trending/rss?geo=US&cat=0-174"),
    ("science_tech", "https://trends.google.com/trending/rss?geo=US&cat=0-107"),
    ("music", "https://trends.google.com/trending/rss?geo=US&cat=0-35"),
    ("communities", "https://trends.google.com/trending/rss?geo=US&cat=0-299"),
    ("jobs_education", "https://trends.google.com/trending/rss?geo=US&cat=0-60"),
]

FEED_LABELS = {
    "education": "Education",
    "science_tech": "Tech & AI",
    "music": "Music",
    "communities": "Communities",
    "jobs_education": "Skills",
}

EDUCATION_KEYWORDS = [
    'school', 'college', 'university', 'student', 'teacher',
    'education', 'learning', 'study', 'tutor', 'tutoring',
    'classroom', 'degree', 'course', 'curriculum', 'exam',
    'test', 'SAT', 'ACT', 'GRE', 'GMAT', 'LSAT', 'AP',
    'homework', 'scholarship', 'campus', 'academy', 'training',
    'lecture', 'lesson', 'graduate', 'undergraduate', 'PhD',
    'STEM', 'literacy', 'reading', 'math', 'science',
    'AI', 'artificial intelligence', 'ChatGPT', 'GPT',
    'machine learning', 'coding', 'programming', 'Python',
    'edtech', 'online learning', 'e-learning', 'Khan',
    'Duolingo', 'Coursera', 'bootcamp', 'tech',
    'robot', 'algorithm', 'data science', 'computer',
    'music', 'song', 'album', 'concert', 'band', 'artist',
    'singer', 'piano', 'guitar', 'violin', 'instrument',
    'orchestra', 'choir', 'melody', 'rhythm', 'musical',
    'Grammy', 'performance', 'composition', 'musician',
    'pop', 'jazz', 'classical', 'hip hop', 'rap', 'indie',
    'streaming', 'Spotify', 'Apple Music', 'playlist',
    'child', 'children', 'kids', 'parent', 'parenting',
    'toddler', 'teen', 'teenager', 'youth', 'kindergarten',
    'preschool', 'homeschool', 'daycare',
    'skill', 'career', 'job', 'hire', 'hiring', 'workforce',
    'internship', 'resume', 'interview', 'certification',
]

_KEYWORD_PATTERNS = None


def _get_keyword_patterns():
    global _KEYWORD_PATTERNS
    if _KEYWORD_PATTERNS is None:
        _KEYWORD_PATTERNS = [re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE) for kw in EDUCATION_KEYWORDS]
    return _KEYWORD_PATTERNS


def _matches_keyword(title):
    for pat in _get_keyword_patterns():
        if pat.search(title):
            return True
    return False


def _parse_traffic(traffic_str):
    if not traffic_str:
        return 0
    s = traffic_str.replace('+', '').replace(',', '').strip().upper()
    try:
        if 'M' in s:
            return int(float(s.replace('M', '')) * 1_000_000)
        if 'K' in s:
            return int(float(s.replace('K', '')) * 1_000)
        return int(s)
    except (ValueError, TypeError):
        return 0


def _parse_entry(entry, feed_source):
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

    return {
        "query": title,
        "category": FEED_LABELS.get(feed_source, feed_source),
        "traffic": traffic,
        "started": started,
        "articles": articles,
        "picture": picture,
        "feed_source": feed_source,
    }


def fetch_trending_now():
    print("[discovery] Fetching from 5 category feeds")
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; WiingyBot/1.0)',
        'Accept': 'application/rss+xml, application/xml, text/xml',
    }

    all_entries = []
    feed_counts = {}

    for feed_name, feed_url in CATEGORY_FEEDS:
        try:
            print(f"[discovery] Fetching {feed_name}: {feed_url}")
            resp = requests.get(feed_url, headers=headers, timeout=15)
            print(f"[discovery] {feed_name} status: {resp.status_code}")
            if resp.status_code == 200:
                feed = feedparser.parse(resp.text)
                count = len(feed.entries)
                feed_counts[feed_name] = count
                print(f"[discovery] {feed_name}: {count} entries")
                for entry in feed.entries:
                    all_entries.append((entry, feed_name))
            else:
                feed_counts[feed_name] = 0
        except Exception as e:
            print(f"[discovery] {feed_name} failed: {e}")
            feed_counts[feed_name] = 0
        time.sleep(0.5)

    total_raw = len(all_entries)
    print(f"[discovery] Total raw entries across all feeds: {total_raw}")

    # Parse all entries
    parsed = [_parse_entry(entry, src) for entry, src in all_entries]

    # Keyword filter
    filtered = [item for item in parsed if _matches_keyword(item["query"])]
    filter_relaxed = False
    print(f"[discovery] After keyword filter: {len(filtered)} (from {len(parsed)})")

    if len(filtered) < 20:
        print(f"[discovery] Only {len(filtered)} after filter, relaxing to include all entries")
        filtered = parsed
        filter_relaxed = True

    # Deduplicate by full title lowercased
    seen = set()
    deduped = []
    for item in filtered:
        key = item["query"].lower().strip()
        if key and key not in seen:
            seen.add(key)
            deduped.append(item)
    print(f"[discovery] After dedup: {len(deduped)}")

    # Sort by traffic descending
    deduped.sort(key=lambda x: _parse_traffic(x.get("traffic", "")), reverse=True)

    # Take top 50 and assign ranks
    results = deduped[:50]
    for i, item in enumerate(results):
        item["rank"] = i + 1

    print(f"[discovery] fetch_trending_now returning {len(results)} items")
    return results, feed_counts, len(filtered) if not filter_relaxed else len(parsed), len(deduped), filter_relaxed


def build_discovery_data():
    print("[discovery] Starting build_discovery_data")
    start = time.time()

    error = None
    feed_counts = {}
    after_filter = 0
    after_dedup = 0
    filter_relaxed = False

    try:
        top_items, feed_counts, after_filter, after_dedup, filter_relaxed = fetch_trending_now()
    except Exception as e:
        print(f"[discovery] fetch_trending_now failed: {e}")
        traceback.print_exc()
        top_items = []
        error = f"Google Trends RSS failed: {str(e)}"

    if not top_items and not error:
        error = "Google Trends RSS returned no data. Please try again."

    quadrant_data = []
    for item in top_items:
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

        random.seed(rank)
        velocity = min(100, max(5, velocity + random.randint(-8, 8)))
        coverage = min(100, max(5, coverage + random.randint(-5, 5)))

        quadrant_data.append({
            "query": item["query"],
            "velocity": int(velocity),
            "coverage": int(coverage),
            "articles": item.get("articles", []),
            "traffic": item.get("traffic", ""),
            "started": item.get("started", ""),
            "rank": rank,
            "feed_source": item.get("feed_source", ""),
        })

    result = {
        "quadrant_data": quadrant_data,
        "top20": top_items,
        "cached_at": datetime.utcnow().isoformat(),
        "error": error,
        "debug_info": {
            "feed_counts": feed_counts,
            "after_keyword_filter": after_filter,
            "after_deduplication": after_dedup,
            "filter_relaxed": filter_relaxed,
            "total_results": len(top_items),
        },
    }

    print(f"[discovery] Completed in {time.time()-start:.1f}s — "
          f"{len(top_items)} trends, {len(quadrant_data)} quadrant points")
    return result
