# Wiingy Story Finder — Part 1

## What this builds
Internal web tool for the Wiingy PR team. Searches Google News RSS and
The Guardian API for trending education/edtech stories, scores each story
via AI on three dimensions, generates Wiingy Newsroom content angles on
demand, lets editors save favourites and download CSV exports.

## This is Part 1 only
No Google Docs. No email. No writing. Just find, score, angle, review.
Approved stories saved with is_favourite=1 for Part 2 to consume later.

## Stack — backend
- Python 3.11, FastAPI, SQLite (sqlite3 standard library, no ORM)
- google-generativeai SDK, model: gemini-2.5-flash-lite
- feedparser for Google News RSS (no API key needed)
- requests + Guardian content API for The Guardian news (requires GUARDIAN_API_KEY)
- pytrends for Google Trends data (no API key, may rate-limit)
- python-dotenv for env vars, uvicorn for local server

## Stack — frontend
- Single frontend/index.html file, React 18 + Tailwind CSS via CDN
- No npm, no build step. Served by FastAPI / Vercel.

## Hosting
- Vercel serverless. Entry point: api/index.py
- SQLite MUST use /tmp/stories.db (only writable dir on Vercel)
- requirements.txt MUST be in repo root (not in backend/)

## Env vars needed
GEMINI_API_KEY -- from aistudio.google.com (free tier)
NEWS_API_KEY -- from newsapi.org (free tier, not used in RSS path)
GUARDIAN_API_KEY -- from open-platform.theguardian.com (free tier)

## News agents
- fetch_google_news_rss() — RSS scraper, no key needed
- fetch_guardian_news() — Guardian content API, US-edition, education sections
- fetch_all_news() — runs both scrapers, merges, deduplicates (Guardian wins
  on title overlap), sorts by date descending

## Wiingy brand context for AI prompts
Global tutoring marketplace. 4,500+ vetted tutors. 20,000+ students.
350+ subjects. 50+ countries. Rated 4.8/5. Top 3% of applicants accepted.
Strong in: SAT/ACT, coding, math, science, languages, music, test prep.
Brand voice: authoritative, data-led, student-outcome focused, never promotional.

## Scoring rubric (three dimensions, each 1-10)
Brand relevance: intersects tutoring/edtech/AI learning/parenting/test prep/coding
Journalistic value: credible, data-backed, publishable in a newsroom
Timeliness: published in last 24 hours, actively trending

## Discovery tab (Google Trends via pytrends)
backend/agents/discovery_scraper.py with three functions:
- fetch_trending_now() — top 20 trending searches via trending_searches()
- fetch_realtime_trends() — up to 13 real-time story clusters via
  realtime_trending_searches()
- build_discovery_data() — combines both, calculates velocity/coverage
  scores, returns quadrant_data + top20 arrays
backend/discovery_cache.py — in-memory cache with 30-minute TTL. Persists
within a single Vercel function instance; empty on cold starts.
Two endpoints:
- GET /api/discovery — returns cached data or fetches fresh
- GET /api/discovery/refresh — forces a fresh fetch
Frontend renders a Pitch Quadrant scatter chart (Chart.js) plotting
velocity vs coverage, and a sortable Top 20 Trending table. Clicking
any trend hands off the query to the Search tab.

## Article fetcher (on-demand)
backend/agents/article_fetcher.py with two functions:
- fetch_article_content(url) — fetches full HTML, extracts text via
  BeautifulSoup (article > main > class-based > paragraph fallback),
  caps at 8000 chars. Returns (content, None) on success or
  (None, "scraper_blocked") on failure. Graceful for 403/401/429.
- generate_article_summary(title, content) — Gemini 4-6 sentence
  summary of the article content.
POST /api/stories/{id}/fetch-article — fetches + summarises, caches
result. Returns cached if already fetched.
When article_content is available, the scorer uses it instead of the
RSS description for more accurate scoring.

## Do NOT build in Part 1
No Google Docs API. No email/SMTP. No GitHub Actions cron.
No authentication. No Reddit scraping.
