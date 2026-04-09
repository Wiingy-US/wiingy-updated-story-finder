import feedparser
from urllib.parse import quote


def fetch_google_news_rss(keywords, date_from, date_to):
    all_stories = []

    for keyword in keywords:
        try:
            url = (
                f"https://news.google.com/rss/search?"
                f"q={quote(keyword)}+after:{date_from}+before:{date_to}"
                f"&hl=en-US&gl=US&ceid=US:en"
            )
            feed = feedparser.parse(url)
            entries = feed.entries

            for entry in entries:
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    entry._sort_key = entry.published_parsed
                else:
                    entry._sort_key = (0,)

            entries.sort(key=lambda e: e._sort_key, reverse=True)
            entries = entries[:10]

            for entry in entries:
                source = ""
                if hasattr(entry, "source") and hasattr(entry.source, "title"):
                    source = entry.source.title
                elif " - " in entry.get("title", ""):
                    source = entry["title"].rsplit(" - ", 1)[-1]

                all_stories.append({
                    "title": entry.get("title", ""),
                    "source": source,
                    "url": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "description": entry.get("summary", ""),
                    "origin": "rss",
                    "keyword": keyword,
                })
        except Exception:
            continue

    seen = set()
    deduplicated = []
    for story in all_stories:
        key = story["title"][:80].lower()
        if key not in seen:
            seen.add(key)
            deduplicated.append(story)

    deduplicated.sort(
        key=lambda s: s.get("published", ""),
        reverse=True,
    )

    return deduplicated
