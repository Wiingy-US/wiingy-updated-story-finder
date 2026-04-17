import time
import traceback
from datetime import datetime


def fetch_trending_now():
    print("[discovery] Starting fetch_trending_now")
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl='en-US', tz=360, timeout=(10, 25))
        print("[discovery] TrendReq initialized")

        df = pytrends.trending_searches(pn='united_states')
        print(f"[discovery] trending_searches returned: type={type(df)}")

        if df is None:
            print("[discovery] trending_searches returned None")
            return []

        if hasattr(df, 'empty') and df.empty:
            print("[discovery] trending_searches returned empty dataframe")
            return []

        print(f"[discovery] dataframe shape: {df.shape}")
        print(f"[discovery] dataframe columns: {list(df.columns)}")

        results = []
        col = df.columns[0]
        for i, val in enumerate(df[col].tolist()[:20]):
            results.append({
                "rank": i + 1,
                "query": str(val),
                "category": "",
                "traffic": "",
                "started": "",
            })

        print(f"[discovery] fetch_trending_now returning {len(results)} items")
        return results

    except Exception as e:
        print(f"[discovery] fetch_trending_now error: {e}")
        traceback.print_exc()
        return []


def fetch_realtime_trends():
    print("[discovery] Starting fetch_realtime_trends")
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl='en-US', tz=360, timeout=(10, 25))
        print("[discovery] TrendReq initialized for realtime")
        time.sleep(1)

        df = pytrends.realtime_trending_searches(pn='US')
        print(f"[discovery] realtime_trending_searches returned: type={type(df)}")

        if df is None:
            print("[discovery] realtime returned None")
            return []

        if hasattr(df, 'empty') and df.empty:
            print("[discovery] realtime returned empty dataframe")
            return []

        print(f"[discovery] realtime shape: {df.shape}")
        print(f"[discovery] realtime columns: {list(df.columns)}")

        results = []
        for i, row in df.iterrows():
            if i >= 13:
                break
            try:
                title = ""
                for col in ['title', 'query', 'entityNames', 'Title']:
                    if col in row and row[col]:
                        title = str(row[col])
                        break
                if not title:
                    title = str(row.iloc[0])

                articles = []
                for col in ['articles', 'news', 'Stories']:
                    if col in row and row[col]:
                        raw = row[col]
                        if isinstance(raw, list):
                            articles = [
                                str(a.get('articleTitle', a.get('title', str(a))))
                                for a in raw[:3] if isinstance(a, dict)
                            ]
                        elif isinstance(raw, str):
                            articles = [raw[:100]]
                        break

                traffic = ""
                for col in ['formattedTraffic', 'traffic', 'Traffic']:
                    if col in row and row[col]:
                        traffic = str(row[col])
                        break

                started = ""
                for col in ['startTime', 'started', 'pubDate']:
                    if col in row and row[col]:
                        started = str(row[col])[:16]
                        break

                results.append({
                    "title": title,
                    "articles": articles,
                    "traffic": traffic,
                    "started": started,
                })
            except Exception as row_err:
                print(f"[discovery] Error processing realtime row {i}: {row_err}")
                continue

        print(f"[discovery] fetch_realtime_trends returning {len(results)} items")
        return results

    except Exception as e:
        print(f"[discovery] fetch_realtime_trends error: {e}")
        traceback.print_exc()
        return []


def build_discovery_data():
    print("[discovery] Starting build_discovery_data")
    start = time.time()

    error_messages = []

    top20 = fetch_trending_now()
    if not top20:
        error_messages.append("trending_searches returned no data")

    time.sleep(2)

    realtime = fetch_realtime_trends()
    if not realtime:
        error_messages.append("realtime_trending_searches returned no data")

    quadrant_data = []
    for i, item in enumerate(realtime):
        velocity = max(95 - (i * 6), 20)
        article_count = len(item.get('articles', []))
        if article_count == 0:
            coverage = 10
        elif article_count == 1:
            coverage = 25
        elif article_count == 2:
            coverage = 45
        else:
            coverage = min(70 + ((article_count - 3) * 10), 95)

        quadrant_data.append({
            "query": item["title"],
            "velocity": velocity,
            "coverage": coverage,
            "articles": item.get("articles", []),
            "traffic": item.get("traffic", ""),
            "started": item.get("started", ""),
        })

    realtime_titles = [q["query"].lower() for q in quadrant_data]
    for item in top20:
        if item["query"].lower() not in realtime_titles:
            velocity = max(60 - (item["rank"] * 2), 20)
            quadrant_data.append({
                "query": item["query"],
                "velocity": velocity,
                "coverage": 20,
                "articles": [],
                "traffic": item.get("traffic", ""),
                "started": item.get("started", ""),
            })

    result = {
        "quadrant_data": quadrant_data,
        "top20": top20,
        "cached_at": datetime.utcnow().isoformat(),
        "error": "; ".join(error_messages) if error_messages else None,
    }

    print(f"[discovery] build_discovery_data completed in {time.time()-start:.1f}s")
    print(f"[discovery] quadrant_data count: {len(quadrant_data)}")
    print(f"[discovery] top20 count: {len(top20)}")

    return result
