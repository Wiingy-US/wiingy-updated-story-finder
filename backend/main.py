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
)
from backend.agents.news_scraper import fetch_google_news_rss
from backend.agents.relevance_scorer import score_story
from backend.agents.angle_generator import generate_angle


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
        fieldnames.append("wiingy_angle")
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for story in stories:
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
    save_content_angle(story_id, angled["wiingy_angle"])
    result = get_story_by_id(story_id)
    result = dict(result)
    result["wiingy_angle"] = angled["wiingy_angle"]
    return result


@app.post("/api/stories/{story_id}/favourite")
async def api_toggle_favourite(story_id: int):
    story = get_story_by_id(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    new_value = toggle_favourite(story_id)
    return {"story_id": story_id, "is_favourite": bool(new_value)}


@app.get("/api/favourites")
async def api_favourites():
    favourites = get_all_favourites()
    for fav in favourites:
        angle = get_angle_by_story_id(fav["id"])
        fav["wiingy_angle"] = angle["wiingy_angle"] if angle else None
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
            story["wiingy_angle"] = angle["wiingy_angle"]
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
        angle = get_angle_by_story_id(fav["id"])
        fav["wiingy_angle"] = angle["wiingy_angle"] if angle else None
    output = _stories_to_csv(favourites, include_angle=True)
    filename = f"wiingy-favourites-{date.today().isoformat()}.csv"
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
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
