# Wiingy Updated Story Finder

An internal web tool for the Wiingy PR and content team. It searches Google News RSS for trending education and edtech stories, scores each story using AI across three dimensions, generates Wiingy Newsroom content angles on demand, and lets editors save favourites and export everything as CSV.

This is Part 1 of a two-part system. Part 2 (not yet built) will take approved stories and automatically write full PR content packages — newsroom articles, press releases, and journalist pitch emails — saving them to Google Docs.

---

## What it does

1. **Search** — Enter up to 10 keywords and a date range. The tool fetches up to 10 recent stories per keyword from Google News RSS and displays them as cards.

2. **Score** — Each story is scored by Gemini AI on three dimensions: Brand Relevance, Journalistic Value, and Timeliness. Each score is out of 10 with a written reason explaining the score.

3. **Generate angles** — For any story, generate a 1-2 sentence Wiingy Newsroom content angle on demand. The angle positions Wiingy as a credible expert voice and references real platform data.

4. **Save favourites** — Heart any story to save it. Favourites persist across sessions and are stored in the database for Part 2 to consume.

5. **Export** — Download stories and angles as CSV files to share with the wider team.

---

## Tech stack

| Layer | Tool | Why |
|---|---|---|
| Backend language | Python 3.11 | All agent and API logic |
| Web framework | FastAPI | REST API server |
| Database | SQLite via sqlite3 | Built-in, no ORM needed |
| AI model | Gemini 2.5 Flash-Lite | Scoring and angle generation |
| News data | Google News RSS via feedparser | Free, no API key required |
| Frontend | React 18 + Tailwind CSS | Single HTML file, no build step |
| Hosting | Vercel serverless | Free tier, auto-deploys from GitHub |

---

## Folder structure

wiingy-updated-story-finder/
│
├── api/
│   └── index.py                  # Vercel entry point. Imports FastAPI app
│                                 # and serves frontend/index.html at root /
│
├── backend/
│   ├── agents/
│   │   ├── news_scraper.py       # fetch_google_news_rss() — fetches stories
│   │   │                         # from Google News RSS for each keyword
│   │   ├── relevance_scorer.py   # score_story() — scores one story via
│   │   │                         # Gemini on 3 dimensions, returns JSON
│   │   └── angle_generator.py    # generate_angle() — writes a Wiingy brand
│   │                             # hook for one story via Gemini
│   ├── database.py               # SQLite setup at /tmp/stories.db and all
│   │                             # database helper functions
│   └── main.py                   # FastAPI app with all 11 API endpoints
│
├── frontend/
│   └── index.html                # Complete React SPA. Three views: Search,
│                                 # Favourites, History. No build step.
│
├── prompts/
│   ├── wiingy_brand_context.txt  # Wiingy brand facts injected into every
│   │                             # Gemini prompt
│   └── scoring_rubric.txt        # Three scoring dimensions and criteria
│                                 # used by the relevance scorer
│
├── .env                          # Local secrets — never committed to GitHub
├── .env.example                  # Template showing required variable names
├── .gitignore                    # Excludes .env and credentials.json
├── CLAUDE.md                     # Project memory file read by Claude Code
│                                 # at the start of every session
├── requirements.txt              # Python dependencies — must be in root
└── vercel.json                   # Vercel routing config

---

## The three AI agents

### Agent 1 — News Scraper (backend/agents/news_scraper.py)
Accepts a list of keywords and a date range. For each keyword it builds a Google News RSS URL, fetches it using feedparser, and takes the 10 most recent results. Results from all keywords are merged into a single flat list and deduplicated by comparing the first 80 characters of each title (lowercased). Returns a clean list of story objects each with: title, source, url, published, description, origin, keyword.

### Agent 2 — Relevance Scorer (backend/agents/relevance_scorer.py)
Accepts one story at a time. Makes a single Gemini 2.5 Flash-Lite API call with the Wiingy brand context and scoring rubric as the system prompt. Returns the story with six new fields added: a score and a written reason for each of the three dimensions. Also calculates an overall score as the average of the three and assigns a category (Education, Test Prep, EdTech, Parenting, Workforce).

### Agent 3 — Angle Generator (backend/agents/angle_generator.py)
Accepts one story at a time. Makes a single Gemini API call instructed to write a 1-2 sentence brand hook that positions Wiingy as a credible expert voice on the story. The hook must reference Wiingy platform data or the tutor network. Returns the story with a new wiingy_angle field. If generation fails it sets wiingy_angle to 'Angle generation failed' and continues without crashing.

---

## API endpoints

| Method | Path | What it does |
|---|---|---|
| POST | /api/search | Search Google News RSS with keywords and date range |
| GET | /api/searches | List last 20 searches with story counts |
| GET | /api/search/{id}/stories | All stories for a past search |
| POST | /api/stories/{id}/score | Score one story using Gemini |
| POST | /api/stories/{id}/angle | Generate Wiingy angle for one story |
| POST | /api/stories/{id}/favourite | Toggle favourite on or off |
| GET | /api/favourites | All favourited stories with angles |
| GET | /api/export/stories/{id} | Download all stories for a search as CSV |
| GET | /api/export/angles/{id} | Download stories with angles as CSV |
| GET | /api/export/favourites | Download all favourites with angles as CSV |
| GET | /api/status | Health check |

---

## The three frontend views

### Search (default view)
Enter keywords as pill tags and set a date range. Click Search to fetch stories. Each story card shows the title, source, published date, and keyword. Click Get Score to score an individual story, or Get All Scores to score everything in one batch. Click Get Content Angle to generate a Wiingy brand hook for that story. Heart any story to save it to Favourites.

### Favourites
All hearted stories in one place. Use Get Angles for All to generate angles in batch with a live progress counter. Download everything as CSV to share with the team.

### History
A log of every past search showing the keywords used, date range, story count, and time of search. Click View Stories on any past search to reload its results into the Search view.

---

## Scoring dimensions

| Dimension | High score (8-10) | Low score (1-4) |
|---|---|---|
| Brand relevance | Directly intersects tutoring, edtech, AI in learning, parenting, test prep, coding, math, languages, music | General business news, no clear Wiingy connection |
| Journalistic value | Data-backed, credible outlet (NYT, EdSurge, Pew Research), publishable as a newsroom piece | Opinion piece, no data, clickbait |
| Timeliness | Published in last 24 hours, actively trending | Older than 3 days, no current hook |

---

## Wiingy brand context (used in every AI prompt)

Wiingy is a global tutoring marketplace founded in 2021.

- 4,500+ expert-vetted tutors
- 20,000+ students helped
- 350+ subjects taught
- 50+ countries served
- Rated 4.8/5 by students and parents
- Only the top 3% of tutor applicants are accepted

Strong in: SAT/ACT prep, coding, Python, math, science, languages (Spanish, English, French), music (piano, guitar, singing), test prep (GRE, GMAT, GCSE), homework help.

Brand voice: authoritative, data-led, student-outcome focused, never promotional. Always journalistic in tone.

---

## Environment variables

| Variable | Required | Where to get it |
|---|---|---|
| GEMINI_API_KEY | Yes | aistudio.google.com — free tier, 1,500 req/day |
| NEWS_API_KEY | Yes | newsapi.org — free tier, 100 req/day |

Copy .env.example to .env and fill in both values before running locally.

---

## Running locally

Install dependencies:
pip install -r requirements.txt

Add your API keys:
cp .env.example .env
Open .env and paste your GEMINI_API_KEY and NEWS_API_KEY

Start the server:
uvicorn backend.main:app --reload

Open in browser:
http://localhost:8000

---

## Deploying to Vercel

1. Push this repository to GitHub
2. Go to vercel.com and click Add New Project
3. Import the wiingy-updated-story-finder repository
4. Under Environment Variables add GEMINI_API_KEY and NEWS_API_KEY
5. Click Deploy

Vercel reads vercel.json automatically. The entry point is api/index.py. Your live URL will be wiingy-updated-story-finder.vercel.app.

Important: Vercel's free tier stores the SQLite database in /tmp which resets on cold starts. Data does not persist indefinitely. For production use, replace SQLite with a hosted database such as Supabase.

---

## Cost

| Scenario | API calls per run | Cost per run | Cost per month |
|---|---|---|---|
| Score 15 stories + 1 angle | ~17 calls | ~$0.003 | ~$0.09 |
| Score all 15 + angle all 15 | ~31 calls | ~$0.006 | ~$0.18 |

Gemini 2.5 Flash-Lite free tier covers 1,500 requests per day. At 17 calls per run this covers approximately 88 runs per day at zero cost.

---

## What is NOT in Part 1

- No Google Docs API
- No email or SMTP
- No GitHub Actions cron schedule
- No authentication or login
- No Reddit or Google Trends scraping

These are all planned for Part 2.

---

## Part 2 — coming next

Part 2 takes the stories saved as favourites and automatically generates full PR content packages. For each approved story it will write a 450-550 word Wiingy Newsroom article, an AP Style press release, and a 150-word journalist pitch email. Each package is saved as a Google Doc and a summary email is sent via Gmail.
