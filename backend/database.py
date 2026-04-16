import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join('/tmp', 'stories.db')


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keywords TEXT,
            date_from TEXT,
            date_to TEXT,
            us_state TEXT DEFAULT 'all',
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            search_id INTEGER,
            title TEXT,
            source TEXT,
            url TEXT,
            published TEXT,
            description TEXT,
            keyword TEXT,
            origin TEXT,
            brand_relevance_score REAL,
            brand_relevance_reason TEXT,
            journalistic_value_score REAL,
            journalistic_value_reason TEXT,
            timeliness_score REAL,
            timeliness_reason TEXT,
            overall_score REAL,
            category TEXT,
            is_favourite INTEGER DEFAULT 0,
            run_date TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS content_angles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id INTEGER,
            topic_reasoning TEXT,
            angles TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_search(keywords, date_from, date_to, us_state="all"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO searches (keywords, date_from, date_to, us_state, created_at) VALUES (?, ?, ?, ?, ?)",
        (json.dumps(keywords), date_from, date_to, us_state, datetime.utcnow().isoformat())
    )
    search_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return search_id


def save_stories(search_id, stories):
    conn = get_connection()
    cursor = conn.cursor()
    inserted_ids = []
    for story in stories:
        cursor.execute(
            """INSERT INTO stories
               (search_id, title, source, url, published, description, keyword, origin, run_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                search_id,
                story.get("title"),
                story.get("source"),
                story.get("url"),
                story.get("published"),
                story.get("description"),
                story.get("keyword"),
                story.get("origin"),
                datetime.utcnow().strftime("%Y-%m-%d"),
            )
        )
        inserted_ids.append(cursor.lastrowid)
    conn.commit()
    conn.close()
    return inserted_ids


def update_story_scores(story_id, scores_dict):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE stories SET
           brand_relevance_score = ?,
           brand_relevance_reason = ?,
           journalistic_value_score = ?,
           journalistic_value_reason = ?,
           timeliness_score = ?,
           timeliness_reason = ?,
           overall_score = ?,
           category = ?
           WHERE id = ?""",
        (
            scores_dict.get("brand_relevance_score"),
            scores_dict.get("brand_relevance_reason"),
            scores_dict.get("journalistic_value_score"),
            scores_dict.get("journalistic_value_reason"),
            scores_dict.get("timeliness_score"),
            scores_dict.get("timeliness_reason"),
            scores_dict.get("overall_score"),
            scores_dict.get("category"),
            story_id,
        )
    )
    conn.commit()
    conn.close()


def save_content_angle(story_id, topic_reasoning, angles):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO content_angles (story_id, topic_reasoning, angles, created_at) VALUES (?, ?, ?, ?)",
        (story_id, topic_reasoning, json.dumps(angles or []), datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


def toggle_favourite(story_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_favourite FROM stories WHERE id = ?", (story_id,))
    row = cursor.fetchone()
    new_value = 0 if row["is_favourite"] == 1 else 1
    cursor.execute("UPDATE stories SET is_favourite = ? WHERE id = ?", (new_value, story_id))
    conn.commit()
    conn.close()
    return new_value


def get_stories_by_search(search_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stories WHERE search_id = ?", (search_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_all_favourites():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stories WHERE is_favourite = 1")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_recent_searches(limit=20):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT s.*, COUNT(st.id) AS story_count
           FROM searches s
           LEFT JOIN stories st ON s.id = st.search_id
           GROUP BY s.id
           ORDER BY s.created_at DESC
           LIMIT ?""",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_story_by_id(story_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stories WHERE id = ?", (story_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_angle_by_story_id(story_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM content_angles WHERE story_id = ? ORDER BY created_at DESC LIMIT 1",
        (story_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    result = dict(row)
    try:
        result["angles"] = json.loads(result["angles"]) if result.get("angles") else []
    except (json.JSONDecodeError, TypeError):
        result["angles"] = []
    return result
