import time
import traceback
from datetime import datetime, timezone


def fetch_trending_now():
    print("[discovery] fetch_trending_now: starting")
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl='en-US', tz=360, timeout=(10, 25), retries=2, backoff_factor=0.5)
        print("[discovery] fetch_trending_now: calling trending_searches(pn='united_states')")
        df = pytrends.trending_searches(pn='united_states')
        print(f"[discovery] fetch_trending_now: got dataframe shape={df.shape}, columns={list(df.columns)}")
        time.sleep(1)

        results = []
        for rank, (_, row) in enumerate(df.head(20).iterrows(), start=1):
            query = str(row.iloc[0]) if len(row) > 0 else str(row)
            results.append({
                "rank": rank,
                "query": query.strip(),
                "category": "",
            })
        print(f"[discovery] fetch_trending_now: returning {len(results)} items")
        return results
    except Exception as e:
        print(f"[discovery] fetch_trending_now FAILED: {e}")
        traceback.print_exc()
        return []


def fetch_realtime_trends():
    print("[discovery] fetch_realtime_trends: starting")
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl='en-US', tz=360, timeout=(10, 25), retries=2, backoff_factor=0.5)
        print("[discovery] fetch_realtime_trends: calling realtime_trending_searches(pn='US')")
        df = pytrends.realtime_trending_searches(pn='US')
        print(f"[discovery] fetch_realtime_trends: got dataframe shape={df.shape}, columns={list(df.columns)}")
        time.sleep(1)

        results = []
        for _, row in df.head(13).iterrows():
            title = ""
            if 'title' in row:
                title = str(row['title'])
            elif 'entityNames' in row:
                val = row['entityNames']
                title = str(val[0]) if isinstance(val, list) and val else str(val)

            articles = []
            for col in ['articles', 'articleTitles']:
                if col in row and row[col] is not None:
                    val = row[col]
                    if isinstance(val, list):
                        articles = [str(a) if not isinstance(a, dict) else a.get('articleTitle', str(a)) for a in val[:3]]
                    break

            traffic = ""
            if 'formattedTraffic' in row and row['formattedTraffic']:
                traffic = str(row['formattedTraffic'])

            started = ""
            for col in ['time', 'startTime']:
                if col in row and row[col]:
                    started = str(row[col])[:19]
                    break

            if title:
                results.append({
                    "title": title.strip(),
                    "articles": articles,
                    "traffic": traffic,
                    "started": started,
                })

        print(f"[discovery] fetch_realtime_trends: returning {len(results)} clusters")
        return results
    except Exception as e:
        print(f"[discovery] fetch_realtime_trends FAILED: {e}")
        traceback.print_exc()
        return []


def build_discovery_data():
    print("[discovery] build_discovery_data: starting")
    error = None

    try:
        top20 = fetch_trending_now()
    except Exception as e:
        top20 = []
        error = str(e)

    try:
        realtime = fetch_realtime_trends()
    except Exception as e:
        realtime = []
        if not error:
            error = str(e)

    quadrant_data = []
    realtime_titles = set()

    for rank_idx, cluster in enumerate(realtime):
        title = cluster.get("title", "")
        realtime_titles.add(title.lower().strip())

        velocity = max(95 - (rank_idx * 7), 20)
        num_articles = len(cluster.get("articles", []))
        if num_articles == 0:
            coverage = 10
        elif num_articles == 1:
            coverage = 25
        elif num_articles == 2:
            coverage = 45
        else:
            coverage = min(70 + (num_articles - 3) * 10, 95)

        quadrant_data.append({
            "query": title,
            "velocity": velocity,
            "coverage": coverage,
            "articles": cluster.get("articles", []),
            "traffic": cluster.get("traffic", ""),
            "started": cluster.get("started", ""),
        })

    for item in top20:
        query = item.get("query", "")
        if query.lower().strip() in realtime_titles:
            continue
        rank = item.get("rank", 10)
        quadrant_data.append({
            "query": query,
            "velocity": max(60 - (rank * 2), 20),
            "coverage": 20,
            "articles": [],
            "traffic": item.get("traffic", ""),
            "started": item.get("started", ""),
        })

    for item in top20:
        item["traffic"] = item.get("traffic", "")
        item["started"] = item.get("started", "")

    result = {
        "quadrant_data": quadrant_data,
        "top20": top20,
        "cached_at": datetime.now(timezone.utc).isoformat(),
        "error": error,
    }
    print(f"[discovery] build_discovery_data: {len(quadrant_data)} quadrant points, {len(top20)} top20 items, error={error}")
    return result
