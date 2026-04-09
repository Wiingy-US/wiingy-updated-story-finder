import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "prompts")


def _load_prompt(filename):
    path = os.path.join(PROMPTS_DIR, filename)
    with open(path, "r") as f:
        return f.read()


def _parse_scores(text):
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
    return json.loads(cleaned)


def score_story(story):
    api_key = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)

    brand_context = _load_prompt("wiingy_brand_context.txt")
    scoring_rubric = _load_prompt("scoring_rubric.txt")

    system_prompt = brand_context + "\n\n" + scoring_rubric

    user_message = (
        f"Score this story:\n\n"
        f"Title: {story.get('title', '')}\n"
        f"Description: {story.get('description', '')}\n\n"
        f"Return ONLY a valid JSON object with exactly these keys:\n"
        f"brand_relevance_score, brand_relevance_reason, "
        f"journalistic_value_score, journalistic_value_reason, "
        f"timeliness_score, timeliness_reason, "
        f"overall_score, category\n\n"
        f"overall_score must be the float average of the three dimension scores.\n"
        f"category must be one of: Education, Test Prep, EdTech, Parenting, Workforce\n"
        f"Return ONLY valid JSON. No markdown fences. No extra text."
    )

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-lite",
        system_instruction=system_prompt,
    )

    for attempt in range(2):
        try:
            response = model.generate_content(user_message)
            scores = _parse_scores(response.text)

            story["brand_relevance_score"] = scores["brand_relevance_score"]
            story["brand_relevance_reason"] = scores["brand_relevance_reason"]
            story["journalistic_value_score"] = scores["journalistic_value_score"]
            story["journalistic_value_reason"] = scores["journalistic_value_reason"]
            story["timeliness_score"] = scores["timeliness_score"]
            story["timeliness_reason"] = scores["timeliness_reason"]
            story["overall_score"] = scores["overall_score"]
            story["category"] = scores["category"]
            return story
        except Exception:
            if attempt == 1:
                story["brand_relevance_score"] = None
                story["brand_relevance_reason"] = None
                story["journalistic_value_score"] = None
                story["journalistic_value_reason"] = None
                story["timeliness_score"] = None
                story["timeliness_reason"] = None
                story["overall_score"] = None
                story["category"] = None
                return story

    return story
