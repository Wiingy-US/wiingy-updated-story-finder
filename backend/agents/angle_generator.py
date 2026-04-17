import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "prompts")

MUSIC_SIGNALS = [
    'music', 'song', 'album', 'artist', 'concert', 'band',
    'singer', 'piano', 'guitar', 'violin', 'grammy', 'festival',
    'musician', 'orchestra', 'choir', 'instrument', 'musical',
]


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


def _is_music_story(story):
    cat = str(story.get("category", "")).lower()
    if "music" in cat:
        return True
    text = (str(story.get("title", "")) + " " + str(story.get("description", ""))).lower()
    hits = sum(1 for kw in MUSIC_SIGNALS if kw in text)
    return hits >= 3


def _build_music_prompt(brand_context):
    return (
        brand_context + "\n\n"
        "This story is categorised as MUSIC. Follow the MUSIC CONTENT "
        "FRAMEWORK from the brand context exactly. Do not use the standard "
        "5-lens system.\n\n"
        "Work through all 5 steps in order:\n"
        "1. NEWS TYPE CLASSIFICATION\n"
        "2. GENUINE ANGLE GATE — if the story fails, stop and return "
        "no_angle=true with a reason\n"
        "3. BOTTOM-UP REASONING CHAIN (all 4 steps)\n"
        "4. BRIDGE SELECTION\n"
        "5. WIINGY DATA HOOK\n\n"
        "Do not skip the reasoning chain. Do not jump to the angle before "
        "completing all 4 reasoning steps.\n\n"
        "You must also select a recommended_style (POLICY IMPACT, CULTURAL "
        "THINK-PIECE, or NEWS CONSEQUENCE) and provide a style_reason.\n\n"
        "Return ONLY valid JSON with exactly this structure, no markdown "
        "fences, no extra text:\n"
        "{\n"
        '  "is_music": true,\n'
        '  "music_news_type": "one of: Festival/Event, Artist News, '
        'Industry Trend, Chart/Data, Music Tech, Film/Soundtrack, '
        'Music Education, Awards",\n'
        '  "no_angle": true or false,\n'
        '  "no_angle_reason": "string or null",\n'
        '  "recommended_style": "CULTURAL THINK-PIECE" or "POLICY IMPACT" '
        'or "NEWS CONSEQUENCE",\n'
        '  "style_reason": "string",\n'
        '  "topic_reasoning": "string",\n'
        '  "reasoning_chain": {\n'
        '    "step1_specific_observation": "string",\n'
        '    "step2_invisible_audience": "string",\n'
        '    "step3_underlying_mechanism": "string",\n'
        '    "step4_generalizable_truth": "string"\n'
        '  },\n'
        '  "bridge": "one of the 7 bridge keys",\n'
        '  "bridge_reason": "string",\n'
        '  "angle": {\n'
        '    "title": "string",\n'
        '    "learning_angle": "string",\n'
        '    "wiingy_link": "string",\n'
        '    "wiingy_data_hook": "string"\n'
        '  },\n'
        '  "angles": null\n'
        "}\n\n"
        "If no_angle is true, set reasoning_chain to null, bridge to null, "
        "bridge_reason to null, and angle to null."
    )


def _build_standard_prompt(brand_context):
    return (
        brand_context + "\n\n"
        "You are a content strategist for the Wiingy Newsroom. Given a news "
        "story, you must do three things:\n\n"
        "STEP 1 — TOPIC REASONING (1-2 sentences):\n"
        "Why is this story worth covering from an education and learning "
        "perspective? What makes it timely for students, parents, or educators "
        "right now? This is internal guidance for the editor only.\n\n"
        "STEP 2 — RECOMMENDED STYLE:\n"
        "Decide which of the three content styles best fits this story. Choose "
        "exactly one and explain why in one sentence.\n\n"
        "The three styles are:\n"
        "- POLICY IMPACT: for government policy, job market shifts, economic "
        "changes, industry disruption, workforce trends\n"
        "- CULTURAL THINK-PIECE: for viral trends, cultural moments, tech "
        "behavior, social media, generational debates, AI controversy\n"
        "- NEWS CONSEQUENCE: for geopolitical events, natural disasters, "
        "economic shocks, health crises, or external events with indirect "
        "effects on students\n\n"
        "STEP 3 — FIVE CONTENT ANGLES:\n"
        "Write 5 distinct content angles, each from a different lens. All five "
        "must use the recommended style you selected in Step 2.\n\n"
        "Each angle has four parts:\n\n"
        "1. title: A punchy editorial headline. Not a question. Not clickbait.\n"
        "2. learning_angle: 2-3 sentences on the core educational insight. "
        "Never start with Wiingy.\n"
        "3. wiingy_link: Exactly 1 sentence connecting back to Wiingy. Tone "
        "matches the recommended style.\n"
        "4. suggested_sources: 2-3 sources the writer should look up.\n\n"
        "The five lenses: Student, Parent, Educator, System, Opportunity.\n\n"
        "Rules: Never start title or learning_angle with Wiingy. Each angle "
        "genuinely distinct. wiingy_link matches style tone.\n\n"
        "Return ONLY valid JSON, no markdown fences:\n"
        "{\n"
        '  "topic_reasoning": "string",\n'
        '  "recommended_style": "POLICY IMPACT" or "CULTURAL THINK-PIECE" or "NEWS CONSEQUENCE",\n'
        '  "style_reason": "string",\n'
        '  "angles": [\n'
        '    { "lens": "Student", "title": "string", "learning_angle": "string", '
        '"wiingy_link": "string", "suggested_sources": "string" },\n'
        '    { "lens": "Parent", "title": "string", "learning_angle": "string", '
        '"wiingy_link": "string", "suggested_sources": "string" },\n'
        '    { "lens": "Educator", "title": "string", "learning_angle": "string", '
        '"wiingy_link": "string", "suggested_sources": "string" },\n'
        '    { "lens": "System", "title": "string", "learning_angle": "string", '
        '"wiingy_link": "string", "suggested_sources": "string" },\n'
        '    { "lens": "Opportunity", "title": "string", "learning_angle": "string", '
        '"wiingy_link": "string", "suggested_sources": "string" }\n'
        "  ]\n"
        "}"
    )


def generate_angle(story):
    api_key = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)

    brand_context = _load_prompt("wiingy_brand_context.txt")
    is_music = _is_music_story(story)

    if is_music:
        system_prompt = _build_music_prompt(brand_context)
    else:
        system_prompt = _build_standard_prompt(brand_context)

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

            if is_music:
                story["is_music"] = True
                story["music_news_type"] = result.get("music_news_type", "")
                story["no_angle"] = bool(result.get("no_angle", False))
                story["no_angle_reason"] = result.get("no_angle_reason")
                story["topic_reasoning"] = result.get("topic_reasoning", "")
                story["recommended_style"] = result.get("recommended_style", "")
                story["style_reason"] = result.get("style_reason", "")
                story["reasoning_chain"] = result.get("reasoning_chain")
                story["bridge"] = result.get("bridge")
                story["bridge_reason"] = result.get("bridge_reason")
                story["angle"] = result.get("angle")
                story["angles"] = None
            else:
                story["is_music"] = False
                story["no_angle"] = False
                story["no_angle_reason"] = None
                story["music_news_type"] = None
                story["reasoning_chain"] = None
                story["bridge"] = None
                story["bridge_reason"] = None
                story["angle"] = None
                story["topic_reasoning"] = result.get("topic_reasoning", "")
                story["recommended_style"] = result.get("recommended_style", "")
                story["style_reason"] = result.get("style_reason", "")
                story["angles"] = result.get("angles", [])
            return story
        except Exception:
            if attempt == 1:
                story["is_music"] = is_music
                story["no_angle"] = False
                story["no_angle_reason"] = None
                story["music_news_type"] = None
                story["reasoning_chain"] = None
                story["bridge"] = None
                story["bridge_reason"] = None
                story["angle"] = None
                story["topic_reasoning"] = "Generation failed"
                story["recommended_style"] = "UNKNOWN"
                story["style_reason"] = ""
                story["angles"] = [] if not is_music else None
                return story

    return story
