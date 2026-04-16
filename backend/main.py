import io
import os
import csv
import json
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
    save_trend_search,
    get_recent_trend_searches,
)
from backend.agents.news_scraper import fetch_google_news_rss
from backend.agents.relevance_scorer import score_story
from backend.agents.angle_generator import generate_angle
from backend.agents.trend_scraper import fetch_google_trends


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


class TrendSearchRequest(BaseModel):
    keywords: list[str]
    timeframe: str = "today 7-d"
    us_state: str = "all"


DEFAULT_TREND_KEYWORDS = [
    "online tutoring",
    "edtech",
    "AI in education",
    "SAT prep",
    "coding for kids",
]


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
    stories = fetch_google_news_rss(req.keywords, req.date_from, req.date_to, req.us_state)
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


@app.post("/api/trends/search")
async def api_trends_search(req: TrendSearchRequest):
    try:
        result = fetch_google_trends(
            req.keywords, req.timeframe, "US", req.us_state
        )
        trend_search_id = save_trend_search(req.keywords, req.timeframe, req.us_state)
        result["trend_search_id"] = trend_search_id
        return result
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Google Trends unavailable: {str(e)}"
        )


@app.get("/api/trends/searches")
async def api_trends_searches():
    searches = get_recent_trend_searches()
    for s in searches:
        if isinstance(s.get("keywords"), str):
            try:
                s["keywords"] = json.loads(s["keywords"])
            except (json.JSONDecodeError, TypeError):
                pass
    return searches


@app.get("/api/trends/default")
async def api_trends_default():
    try:
        return fetch_google_trends(
            DEFAULT_TREND_KEYWORDS, "today 7-d", "US", "all"
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Google Trends unavailable: {str(e)}"
        )


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
