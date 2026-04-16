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


def _parse_response(text):
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
    return json.loads(cleaned)


def generate_angle(story):
    api_key = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)

    brand_context = _load_prompt("wiingy_brand_context.txt")

    system_prompt = (
        brand_context + "\n\n"
        "You are an education journalist and content strategist writing for "
        "the Wiingy Newsroom. Given a news story, produce two things:\n\n"
        "PART 1 — TOPIC REASONING (1-2 sentences):\n"
        "Why is this story worth covering from an education and learning "
        "perspective? What makes it timely for students, parents, or "
        "educators? This is internal guidance for the editor.\n\n"
        "PART 2 — FIVE CONTENT ANGLES:\n"
        "Write 5 content angles, each from a distinct lens. Each angle has "
        "three components:\n\n"
        "1. title: A punchy editorial headline for the article this angle "
        "would produce. Specific, compelling, not a question, not clickbait.\n\n"
        "2. learning_angle: 2-3 sentences on the core educational insight. "
        "Lead with what is happening in learning. What is shifting, why "
        "does it matter, what does it mean for students or parents.\n\n"
        "3. wiingy_link: Exactly 1 sentence closing the angle with a natural "
        "Wiingy connection. Reference tutor demand, subject trends, platform "
        "data, or tutor observations. Only write this sentence if it fits "
        "genuinely. If not, write: \"Wiingy tutors are well positioned to "
        "support students navigating this shift.\"\n\n"
        "The five lenses are:\n"
        "- Student: how this affects students directly\n"
        "- Parent: what this means for families and parenting decisions\n"
        "- Educator: how teachers and tutors are responding\n"
        "- System: the broader structural shift in education this represents\n"
        "- Opportunity: what students or parents can actively do in response\n\n"
        "Rules:\n"
        "- Never start title or learning_angle with Wiingy\n"
        "- Never sound promotional\n"
        "- Each angle must be genuinely distinct from the other four\n"
        "- learning_angle leads with education, never with Wiingy\n"
        "- wiingy_link is always the final sentence, never the opening\n\n"
        "Return ONLY a valid JSON object with exactly this structure, no "
        "markdown fences, no extra text:\n"
        "{\n"
        '  "topic_reasoning": "string",\n'
        '  "angles": [\n'
        '    {\n'
        '      "lens": "Student",\n'
        '      "title": "string",\n'
        '      "learning_angle": "string",\n'
        '      "wiingy_link": "string"\n'
        '    },\n'
        '    {\n'
        '      "lens": "Parent",\n'
        '      "title": "string",\n'
        '      "learning_angle": "string",\n'
        '      "wiingy_link": "string"\n'
        '    },\n'
        '    {\n'
        '      "lens": "Educator",\n'
        '      "title": "string",\n'
        '      "learning_angle": "string",\n'
        '      "wiingy_link": "string"\n'
        '    },\n'
        '    {\n'
        '      "lens": "System",\n'
        '      "title": "string",\n'
        '      "learning_angle": "string",\n'
        '      "wiingy_link": "string"\n'
        '    },\n'
        '    {\n'
        '      "lens": "Opportunity",\n'
        '      "title": "string",\n'
        '      "learning_angle": "string",\n'
        '      "wiingy_link": "string"\n'
        '    }\n'
        '  ]\n'
        "}"
    )

    user_message = (
        f"Story title: {story.get('title', '')}\n"
        f"Story description: {story.get('description', '')}"
    )

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-lite",
        system_instruction=system_prompt,
    )

    for attempt in range(2):
        try:
            response = model.generate_content(user_message)
            result = _parse_response(response.text)
            story["topic_reasoning"] = result.get("topic_reasoning", "")
            story["angles"] = result.get("angles", [])
            return story
        except Exception:
            if attempt == 1:
                story["topic_reasoning"] = "Reasoning generation failed"
                story["angles"] = []
                return story

    return story
