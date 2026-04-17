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
    save_content_angle,
    toggle_favourite,
    get_stories_by_search,
    get_all_favourites,
    get_recent_searches,
    get_story_by_id,
    get_angle_by_story_id,
)
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
        fieldnames.extend(["topic_reasoning", "recommended_style", "style_reason"])
        for i in range(1, 6):
            fieldnames.extend([
                f"angle_{i}_lens",
                f"angle_{i}_title",
                f"angle_{i}_learning_angle",
                f"angle_{i}_wiingy_link",
                f"angle_{i}_suggested_sources",
            ])
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for story in stories:
        if include_angle:
            angles = story.get("angles") or []
            for i in range(1, 6):
                a = angles[i - 1] if i - 1 < len(angles) else {}
                story[f"angle_{i}_lens"] = a.get("lens", "")
                story[f"angle_{i}_title"] = a.get("title", "")
                story[f"angle_{i}_learning_angle"] = a.get("learning_angle", "")
                story[f"angle_{i}_wiingy_link"] = a.get("wiingy_link", "")
                story[f"angle_{i}_suggested_sources"] = a.get("suggested_sources", "")
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


@app.post("/api/stories/{story_id}/score")
async def api_score_story(story_id: int):
    story = get_story_by_id(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    scored = score_story(dict(story))
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
    topic_reasoning = angled.get("topic_reasoning", "")
    recommended_style = angled.get("recommended_style", "")
    style_reason = angled.get("style_reason", "")
    angles = angled.get("angles", [])
    save_content_angle(story_id, topic_reasoning, recommended_style, style_reason, angles)
    result = dict(get_story_by_id(story_id))
    result["topic_reasoning"] = topic_reasoning
    result["recommended_style"] = recommended_style
    result["style_reason"] = style_reason
    result["angles"] = angles
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
        target["topic_reasoning"] = angle.get("topic_reasoning")
        target["recommended_style"] = angle.get("recommended_style")
        target["style_reason"] = angle.get("style_reason")
        target["angles"] = angle.get("angles") or []
    else:
        target["topic_reasoning"] = None
        target["recommended_style"] = None
        target["style_reason"] = None
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
    import requests as req_lib

    debug = {"feed_results": {}}
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; WiingyBot/1.0)',
        'Accept': 'application/rss+xml',
    }

    feeds = {
        "education": "https://trends.google.com/trending/rss?geo=US&cat=0-174",
        "science_tech": "https://trends.google.com/trending/rss?geo=US&cat=0-107",
        "music": "https://trends.google.com/trending/rss?geo=US&cat=0-35",
        "communities": "https://trends.google.com/trending/rss?geo=US&cat=0-299",
        "jobs_education": "https://trends.google.com/trending/rss?geo=US&cat=0-60",
    }

    for name, url in feeds.items():
        try:
            r = req_lib.get(url, headers=headers, timeout=15)
            feed = feedparser.parse(r.text) if r.status_code == 200 else None
            debug["feed_results"][name] = {
                "status": r.status_code,
                "entries": len(feed.entries) if feed else 0,
                "first_title": feed.entries[0].get('title', '') if feed and feed.entries else None,
            }
        except Exception as e:
            debug["feed_results"][name] = {"error": str(e)}

    try:
        data = build_discovery_data()
        di = data.get("debug_info") or {}
        debug["after_keyword_filter"] = di.get("after_keyword_filter", 0)
        debug["after_deduplication"] = di.get("after_deduplication", 0)
        debug["filter_relaxed"] = di.get("filter_relaxed", False)
        debug["total_results"] = di.get("total_results", 0)
        debug["top_5_queries"] = [item["query"] for item in (data.get("top20") or [])[:5]]
    except Exception as e:
        debug["build_error"] = str(e)

    return debug


@app.get("/api/debug/guardian")
async def api_debug_guardian():
    import requests as req_lib
    from datetime import datetime, timedelta

    api_key = os.getenv("GUARDIAN_API_KEY", "")
    result = {
        "guardian_api_key_set": bool(api_key),
        "guardian_api_key_length": len(api_key),
    }

    if not api_key:
        result["error"] = "GUARDIAN_API_KEY not set"
        return result

    today = datetime.utcnow().strftime("%Y-%m-%d")
    week_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")

    try:
        resp = req_lib.get(
            "https://content.guardianapis.com/search",
            params={
                "q": "education",
                "from-date": week_ago,
                "to-date": today,
                "edition": "us",
                "page-size": 5,
                "api-key": api_key,
            },
            timeout=15,
        )
        result["status_code"] = resp.status_code
        result["response_ok"] = resp.ok

        if resp.ok:
            data = resp.json()
            response_body = data.get("response", {})
            result["total_results"] = response_body.get("total", 0)
            results_list = response_body.get("results", [])
            result["results_returned"] = len(results_list)
            if results_list:
                result["first_title"] = results_list[0].get("webTitle", "")
        else:
            result["error"] = resp.text[:500]
    except Exception as e:
        result["error"] = str(e)

    return result


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
