import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "prompts")

MUSIC_KEYWORDS = [
    'music', 'song', 'album', 'artist', 'concert', 'band',
    'singer', 'piano', 'guitar', 'violin', 'grammy', 'festival',
    'musician', 'orchestra', 'choir', 'instrument', 'musical',
    'hip hop', 'rap', 'jazz', 'classical', 'pop star', 'playlist',
    'spotify', 'record label', 'music video', 'lyrics', 'melody',
    'rhythm', 'composition', 'soundcheck', 'tour', 'debut album',
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
    cat = str(story.get("category", "")).lower().strip()
    is_music_by_category = cat == "music"

    combined_text = (
        str(story.get("title", "")) + " " +
        str(story.get("description", ""))
    ).lower()
    matched = [kw for kw in MUSIC_KEYWORDS if kw in combined_text]
    is_music_by_keywords = len(matched) >= 2

    print(f"[angle] Music detection: category='{story.get('category')}', "
          f"cat_match={is_music_by_category}, keywords_matched={matched}, "
          f"kw_match={is_music_by_keywords}")

    return is_music_by_category or is_music_by_keywords


def _build_music_prompt(brand_context):
    return (
        "THIS IS A MUSIC STORY. You must use the Music Content Framework "
        "ONLY. DO NOT generate 5 lens-based angles. DO NOT use the standard "
        "5-lens format. Follow the music framework steps exactly.\n\n"
        + brand_context + "\n\n"
        "Work through all 5 steps of the MUSIC CONTENT FRAMEWORK in order:\n"
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
        '  "no_angle": false,\n'
        '  "no_angle_reason": null,\n'
        '  "recommended_style": "CULTURAL THINK-PIECE",\n'
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
        "bridge_reason to null, and angle to null.\n"
        "IMPORTANT: The 'angles' field must be null. Do NOT return an array of 5 angles."
    )


def _build_standard_prompt(brand_context):
    return (
        "THIS IS A NON-MUSIC STORY. Use the standard 5-lens system. "
        "DO NOT use the music framework.\n\n"
        + brand_context + "\n\n"
        "You are a content strategist for the Wiingy Newsroom. Given a news "
        "story, you must do three things:\n\n"
        "STEP 1 — TOPIC REASONING (1-2 sentences):\n"
        "Why is this story worth covering from an education and learning "
        "perspective?\n\n"
        "STEP 2 — RECOMMENDED STYLE:\n"
        "Choose one: POLICY IMPACT, CULTURAL THINK-PIECE, or NEWS CONSEQUENCE. "
        "Explain why in one sentence.\n\n"
        "STEP 3 — FIVE CONTENT ANGLES:\n"
        "Write 5 angles, each from a different lens. Each has:\n"
        "1. title: Punchy editorial headline. Not a question.\n"
        "2. learning_angle: 2-3 sentences. Never start with Wiingy.\n"
        "3. wiingy_link: 1 sentence. Tone matches style.\n"
        "4. suggested_sources: 2-3 sources.\n\n"
        "Lenses: Student, Parent, Educator, System, Opportunity.\n\n"
        "Return ONLY valid JSON, no markdown fences:\n"
        "{\n"
        '  "is_music": false,\n'
        '  "no_angle": false,\n'
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
        '  ],\n'
        '  "angle": null\n'
        "}\n"
        "IMPORTANT: The 'angle' field must be null. Return an array of 5 angles."
    )


def generate_angle(story):
    print(f"[angle] === generate_angle START ===")
    print(f"[angle] Story category: {story.get('category')}")
    print(f"[angle] Story title: {story.get('title')}")
    print(f"[angle] Routing check starting...")

    api_key = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)

    brand_context = _load_prompt("wiingy_brand_context.txt")
    is_music = _is_music_story(story)
    print(f"[angle] FINAL is_music decision: {is_music}")

    if is_music:
        print("[angle] ROUTING TO: Music Content Framework")
        system_prompt = _build_music_prompt(brand_context)
    else:
        print("[angle] ROUTING TO: Standard 5-lens system")
        system_prompt = _build_standard_prompt(brand_context)

    print(f"[angle] System prompt preview: {system_prompt[:200]}")

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
            raw = response.text
            print(f"[angle] Raw Gemini response preview: {raw[:300]}")

            result = _parse_response(raw)
            print(f"[angle] Parsed JSON keys: {list(result.keys())}")
            print(f"[angle] is_music in response: {result.get('is_music')}")
            print(f"[angle] 'angles' in response: {'angles' in result}")
            print(f"[angle] 'angle' in response: {'angle' in result}")

            # Validate response format matches routing
            if is_music:
                if result.get("angle") is None and not result.get("no_angle"):
                    print("[angle] WARNING: Music response missing angle field — retrying")
                    if attempt == 0:
                        continue
                if result.get("angles") is not None and isinstance(result.get("angles"), list):
                    print("[angle] WARNING: Music response has 5-lens angles array — wrong format")
                    if attempt == 0:
                        continue

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
                if not isinstance(result.get("angles"), list):
                    print("[angle] WARNING: Non-music response missing angles array — retrying")
                    if attempt == 0:
                        continue
                if result.get("angle") is not None:
                    print("[angle] WARNING: Non-music response has single angle — wrong format")

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

            print(f"[angle] === generate_angle DONE (attempt {attempt + 1}) ===")
            return story
        except Exception as e:
            print(f"[angle] Attempt {attempt + 1} failed: {e}")
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
