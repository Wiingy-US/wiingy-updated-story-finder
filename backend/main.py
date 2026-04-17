import io
import os
import csv
import json
import traceback
import feedparser
from datetime import date
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from backend.database import (
    init_db,
    save_search,
    save_stories,
    update_story_scores,
    update_article_content,
    save_content_angle,
    toggle_favourite,
    get_stories_by_search,
    get_all_favourites,
    get_recent_searches,
    get_story_by_id,
    get_angle_by_story_id,
)
from backend.agents.article_fetcher import fetch_article_content, generate_article_summary
from backend.agents.news_scraper import fetch_all_news
from backend.agents.relevance_scorer import score_story
from backend.agents.angle_generator import generate_angle
from backend.agents.discovery_scraper import build_discovery_data
from backend.discovery_cache import (
    get_cached_discovery,
    set_cached_discovery,
    get_cache_age_seconds,
)


@asynccontextmanager
async def lifespan(app):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    keywords: list[str]
    date_from: str
    date_to: str
    us_state: str = "all"


def _serialize(result):
    try:
        json.dumps(result)
        return result
    except (TypeError, ValueError):
        def _clean(v):
            if isinstance(v, dict):
                return {str(k): _clean(val) for k, val in v.items()}
            if isinstance(v, list):
                return [_clean(item) for item in v]
            try:
                json.dumps(v)
                return v
            except (TypeError, ValueError):
                return str(v)
        return _clean(result)


def _stories_to_csv(stories, include_angle=False):
    output = io.StringIO()
    fieldnames = [
        "id", "title", "source", "url", "published", "description",
        "keyword", "origin", "brand_relevance_score", "brand_relevance_reason",
        "journalistic_value_score", "journalistic_value_reason",
        "timeliness_score", "timeliness_reason", "overall_score", "category",
        "is_favourite",
    ]
    if include_angle:
        for i in range(1, 6):
            fieldnames.extend([
                f"angle_{i}_title",
                f"angle_{i}_angle",
                f"angle_{i}_wiingy_data_point",
            ])
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for story in stories:
        if include_angle:
            angles = story.get("angles") or []
            for i in range(1, 6):
                a = angles[i - 1] if i - 1 < len(angles) else {}
                story[f"angle_{i}_title"] = a.get("title", "")
                story[f"angle_{i}_angle"] = a.get("angle", "")
                story[f"angle_{i}_wiingy_data_point"] = a.get("wiingy_data_point", "")
        writer.writerow(story)
    output.seek(0)
    return output


@app.post("/api/search")
async def api_search(req: SearchRequest):
    stories = fetch_all_news(req.keywords, req.date_from, req.date_to, req.us_state)
    search_id = save_search(req.keywords, req.date_from, req.date_to, req.us_state)
    inserted_ids = save_stories(search_id, stories)
    saved_stories = get_stories_by_search(search_id)
    return {"search_id": search_id, "stories": saved_stories, "total": len(saved_stories)}


@app.get("/api/searches")
async def api_searches():
    searches = get_recent_searches()
    for s in searches:
        if isinstance(s.get("keywords"), str):
            try:
                s["keywords"] = json.loads(s["keywords"])
            except (json.JSONDecodeError, TypeError):
                pass
    return searches


@app.get("/api/search/{search_id}/stories")
async def api_search_stories(search_id: int):
    stories = get_stories_by_search(search_id)
    return stories


@app.post("/api/stories/{story_id}/fetch-article")
async def api_fetch_article(story_id: int):
    print(f"[fetch-article] Called for story_id: {story_id}")
    story = get_story_by_id(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    story = dict(story)
    print(f"[fetch-article] Story URL: {story.get('url', 'NO URL')}")
    print(f"[fetch-article] Current fetch status: {story.get('article_fetch_status', 'NOT SET')}")
    if story.get("article_fetch_status") == "success":
        print("[fetch-article] Returning cached result")
        return {
            "story_id": story_id,
            "cached": True,
            "summary": story.get("article_summary"),
            "status": "success",
        }
    content, err = fetch_article_content(story.get("url", ""))
    if err:
        update_article_content(story_id, None, None, err)
        print(f"[fetch-article] Fetch failed: {err}")
        return {
            "story_id": story_id,
            "status": err,
            "message": "This source blocks automated readers. Summary not available."
            if err == "scraper_blocked" else f"Fetch failed: {err}",
        }
    summary = generate_article_summary(story.get("title", ""), content)
    update_article_content(story_id, content, summary, "success")
    print(f"[fetch-article] Success: summary={len(summary) if summary else 0} chars")
    return {
        "story_id": story_id,
        "status": "success",
        "summary": summary,
        "cached": False,
    }


@app.post("/api/stories/{story_id}/score")
async def api_score_story(story_id: int):
    story = get_story_by_id(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    story = dict(story)
    if story.get("article_fetch_status") == "success" and story.get("article_content"):
        story["article_content"] = story["article_content"]
    scored = score_story(story)
    update_story_scores(story_id, scored)
    return get_story_by_id(story_id)


@app.post("/api/stories/{story_id}/angle")
async def api_generate_angle(story_id: int):
    story = get_story_by_id(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    story = dict(story)
    if story.get("overall_score") is None:
        scored = score_story(dict(story))
        update_story_scores(story_id, scored)
        story = get_story_by_id(story_id)
        story = dict(story)
    angled = generate_angle(dict(story))
    angles = angled.get("angles", [])
    save_content_angle(story_id, angles)
    result = dict(get_story_by_id(story_id))
    result["angles"] = angles
    result["angle_error"] = angled.get("angle_error")
    return result


@app.post("/api/stories/{story_id}/favourite")
async def api_toggle_favourite(story_id: int):
    story = get_story_by_id(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    new_value = toggle_favourite(story_id)
    return {"story_id": story_id, "is_favourite": bool(new_value)}


def _attach_angle(target, angle):
    if angle:
        target["angles"] = angle.get("angles") or []
    else:
        target["angles"] = []


@app.get("/api/favourites")
async def api_favourites():
    favourites = get_all_favourites()
    for fav in favourites:
        _attach_angle(fav, get_angle_by_story_id(fav["id"]))
    return favourites


@app.get("/api/export/stories/{search_id}")
async def api_export_stories(search_id: int):
    stories = get_stories_by_search(search_id)
    output = _stories_to_csv(stories)
    filename = f"wiingy-stories-{date.today().isoformat()}.csv"
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/api/export/angles/{search_id}")
async def api_export_angles(search_id: int):
    stories = get_stories_by_search(search_id)
    stories_with_angles = []
    for story in stories:
        angle = get_angle_by_story_id(story["id"])
        if angle:
            _attach_angle(story, angle)
            stories_with_angles.append(story)
    output = _stories_to_csv(stories_with_angles, include_angle=True)
    filename = f"wiingy-angles-{date.today().isoformat()}.csv"
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/api/export/favourites")
async def api_export_favourites():
    favourites = get_all_favourites()
    for fav in favourites:
        _attach_angle(fav, get_angle_by_story_id(fav["id"]))
    output = _stories_to_csv(favourites, include_angle=True)
    filename = f"wiingy-favourites-{date.today().isoformat()}.csv"
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/api/discovery")
async def api_discovery():
    try:
        cached = get_cached_discovery()
        if cached is not None:
            cached["cache_age_seconds"] = get_cache_age_seconds()
            result = _serialize(cached)
            print(f"[discovery] /api/discovery returning cached: quadrant={len(result.get('quadrant_data') or [])}, top20={len(result.get('top20') or [])}, error={result.get('error')}")
            return result
        data = build_discovery_data()
        set_cached_discovery(data)
        data["cache_age_seconds"] = 0
        result = _serialize(data)
        print(f"[discovery] /api/discovery returning fresh: quadrant={len(result.get('quadrant_data') or [])}, top20={len(result.get('top20') or [])}, error={result.get('error')}")
        return result
    except Exception as e:
        traceback.print_exc()
        return {
            "quadrant_data": [],
            "top20": [],
            "error": f"Discovery unavailable: {str(e)}",
            "cached_at": None,
            "cache_age_seconds": None,
        }


@app.get("/api/discovery/refresh")
async def api_discovery_refresh():
    try:
        data = build_discovery_data()
        set_cached_discovery(data)
        data["cache_age_seconds"] = 0
        result = _serialize(data)
        print(f"[discovery] /api/discovery/refresh returning: quadrant={len(result.get('quadrant_data') or [])}, top20={len(result.get('top20') or [])}, error={result.get('error')}")
        return result
    except Exception as e:
        traceback.print_exc()
        return {
            "quadrant_data": [],
            "top20": [],
            "error": f"Discovery refresh failed: {str(e)}",
            "cached_at": None,
            "cache_age_seconds": None,
        }


@app.get("/api/discovery/debug")
async def api_discovery_debug():
    import time as _time
    from backend.agents.discovery_scraper import FEEDS, fetch_feed

    debug = {"feeds": []}
    total = 0
    for feed_info in FEEDS:
        results = fetch_feed(feed_info)
        total += len(results)
        debug["feeds"].append({
            "source": feed_info["source"],
            "category": feed_info["category"],
            "count": len(results),
            "sample_titles": [r["query"] for r in results[:3]],
        })
        _time.sleep(0.3)

    debug["total_raw"] = total
    return debug


@app.get("/api/debug/fetch-article")
async def api_debug_fetch_article(url: str = ""):
    import requests as req_lib

    if not url:
        return {"error": "No URL provided. Add ?url=https://example.com"}

    debug = {}

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/120.0.0.0 Safari/537.36'
        }
        r = req_lib.get(url, headers=headers, timeout=15, allow_redirects=True)
        debug["http_status"] = r.status_code
        debug["content_type"] = r.headers.get("Content-Type", "unknown")
        debug["content_length"] = len(r.text)
        debug["first_500_chars"] = r.text[:500]
    except Exception as e:
        debug["http_error"] = str(e)

    try:
        content, status = fetch_article_content(url)
        debug["fetch_status"] = status
        debug["extracted_length"] = len(content) if content else 0
        debug["content_preview"] = content[:300] if content else None
    except Exception as e:
        debug["fetch_function_error"] = str(e)

    try:
        from bs4 import BeautifulSoup
        debug["beautifulsoup4_installed"] = True
    except ImportError:
        debug["beautifulsoup4_installed"] = False

    return debug


@app.get("/api/debug/guardian")
async def api_debug_guardian():
    import requests as req_lib
    from datetime import datetime, timedelta

    api_key = os.getenv("GUARDIAN_API_KEY", "NOT_SET")
    date_to = datetime.utcnow().strftime("%Y-%m-%d")
    date_from = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")

    tests = {}

    def _run(name, params):
        try:
            r = req_lib.get(
                "https://content.guardianapis.com/search",
                params={**params, "api-key": api_key},
                timeout=15,
            )
            if r.status_code == 200:
                body = r.json().get("response", {})
                tests[name] = {"status": r.status_code, "total": body.get("total", 0)}
            else:
                tests[name] = {"status": r.status_code, "error": r.text[:200]}
        except Exception as e:
            tests[name] = {"error": str(e)}

    _run("test1_no_extra_params", {
        "q": "education", "from-date": date_from, "to-date": date_to,
        "lang": "en", "order-by": "newest", "page-size": 5,
        "show-fields": "headline,trailText",
    })

    _run("test2_with_production_office", {
        "q": "education", "from-date": date_from, "to-date": date_to,
        "lang": "en", "order-by": "newest", "page-size": 5,
        "show-fields": "headline,trailText", "production-office": "usa",
    })

    _run("test3_us_news_section", {
        "q": "education", "from-date": date_from, "to-date": date_to,
        "lang": "en", "order-by": "newest", "page-size": 5,
        "show-fields": "headline,trailText", "section": "us-news",
    })

    _run("test4_minimal", {"q": "education"})

    tests["api_key_set"] = api_key != "NOT_SET"
    tests["api_key_preview"] = (api_key[:6] + "...") if api_key != "NOT_SET" else "NOT SET"
    return tests


@app.get("/api/status")
async def api_status():
    return {"status": "idle"}


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    html_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "frontend", "index.html"
    )
    with open(html_path, "r") as f:
        return HTMLResponse(content=f.read())
