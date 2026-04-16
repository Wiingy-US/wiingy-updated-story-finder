import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()


def _strip_html(text):
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def fetch_guardian_news(keywords, date_from, date_to, us_state="all"):
    api_key = os.getenv("GUARDIAN_API_KEY", "")
    if not api_key:
        print("[guardian] WARNING: GUARDIAN_API_KEY not set, returning empty list")
        return []

    all_stories = []
    sections = (
        "education|higher-education|schools|technology|science|"
        "society|money|careers|us-news"
    )

    for keyword in keywords:
        try:
            query = keyword if us_state == "all" else f"{keyword} {us_state}"

            params = {
                "q": query,
                "from-date": date_from,
                "to-date": date_to,
                "edition": "us",
                "lang": "en",
                "order-by": "newest",
                "page-size": 10,
                "show-fields": "headline,byline,trailText,shortUrl,publication",
                "show-tags": "keyword",
                "section": sections,
                "api-key": api_key,
            }

            resp = requests.get(
                "https://content.guardianapis.com/search",
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            results = data.get("response", {}).get("results", [])
            for item in results:
                fields = item.get("fields") or {}
                published_raw = item.get("webPublicationDate", "")
                published = published_raw[:19].replace("T", " ") if published_raw else ""

                all_stories.append({
                    "title": fields.get("headline") or item.get("webTitle", ""),
                    "source": "The Guardian",
                    "url": item.get("webUrl", ""),
                    "published": published,
                    "description": _strip_html(fields.get("trailText", "")),
                    "origin": "guardian",
                    "keyword": keyword,
                    "guardian_id": item.get("id", ""),
                    "byline": fields.get("byline", ""),
                    "section": item.get("sectionName", ""),
                })
        except Exception as e:
            print(f"[guardian] WARNING: keyword '{keyword}' failed: {e}")
            continue

    seen_ids = set()
    deduplicated = []
    for story in all_stories:
        gid = story.get("guardian_id", "")
        if gid and gid in seen_ids:
            continue
        if gid:
            seen_ids.add(gid)
        deduplicated.append(story)

    deduplicated.sort(
        key=lambda s: s.get("published", ""),
        reverse=True,
    )

    return deduplicated
