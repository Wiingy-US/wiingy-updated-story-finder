# Wiingy Story Finder — Part 1

## What this builds
Internal web tool for the Wiingy PR team. Searches Google News RSS for
trending education/edtech stories, scores each story via AI on three
dimensions, generates Wiingy Newsroom content angles on demand, lets
editors save favourites and download CSV exports.

## This is Part 1 only
No Google Docs. No email. No writing. Just find, score, angle, review.
Approved stories saved with is_favourite=1 for Part 2 to consume later.

## Stack — backend
- Python 3.11, FastAPI, SQLite (sqlite3 standard library, no ORM)
- google-generativeai SDK, model: gemini-2.5-flash-lite
- feedparser for Google News RSS (no API key needed)
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

## Wiingy brand context for AI prompts
Global tutoring marketplace. 4,500+ vetted tutors. 20,000+ students.
350+ subjects. 50+ countries. Rated 4.8/5. Top 3% of applicants accepted.
Strong in: SAT/ACT, coding, math, science, languages, music, test prep.
Brand voice: authoritative, data-led, student-outcome focused, never promotional.

## Scoring rubric (three dimensions, each 1-10)
Brand relevance: intersects tutoring/edtech/AI learning/parenting/test prep/coding
Journalistic value: credible, data-backed, publishable in a newsroom
Timeliness: published in last 24 hours, actively trending

## Trends tab (Google Trends via pytrends)
Live Google Trends data for education/edtech keywords. Three endpoints:
- POST /api/trends/search — fetch trends for user keywords, timeframe, state
- GET /api/trends/searches — last 10 trend searches
- GET /api/trends/default — preloads online tutoring/edtech/AI in education/
  SAT prep/coding for kids for the Trends tab on first open
Returns three data sections: interest_over_time (line chart), related_queries
(rising + top per keyword), interest_by_region (top US states).
Frontend renders line chart + horizontal bar chart via Chart.js CDN.

## Do NOT build in Part 1
No Google Docs API. No email/SMTP. No GitHub Actions cron.
No authentication. No Reddit scraping.
