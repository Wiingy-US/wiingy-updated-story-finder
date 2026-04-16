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
        "1. title: A punchy editorial headline for the article this angle "
        "would produce. Specific, data-forward where possible. Not a question. "
        "Not clickbait. Written like a real editorial headline.\n\n"
        "2. learning_angle: 2-3 sentences on the core educational insight. "
        "Lead with what is happening in learning or education. What is "
        "shifting, why does it matter, what does it mean for students or "
        "parents. Never start with Wiingy.\n\n"
        "3. wiingy_link: Exactly 1 sentence connecting back to Wiingy. The "
        "tone of this sentence must match the recommended style:\n"
        "   - If POLICY IMPACT: be explicit — position Wiingy as the "
        "affordable, fast path to act on the opportunity. Reference price "
        "($20-$28/hr), free trial, or the <3% acceptance rate.\n"
        "   - If CULTURAL THINK-PIECE: be implied — describe what effective "
        "learning support looks like. Reference Wiingy's <3% acceptance rate "
        "or 1-on-1 human approach as evidence, not as a pitch.\n"
        "   - If NEWS CONSEQUENCE: be matter-of-fact — show how fully online "
        "tutoring removes the specific barrier the news created. Reference "
        "free trial, pay-per-lesson flexibility, or 24/7 support.\n\n"
        "4. suggested_sources: A comma-separated list of 2-3 sources the "
        "writer should look up when writing this article (e.g. BLS, Pew "
        "Research, UNESCO). Choose sources that would genuinely have data "
        "for this angle.\n\n"
        "The five lenses are:\n"
        "- Student: how this affects students directly\n"
        "- Parent: what this means for families and parenting decisions\n"
        "- Educator: how teachers and tutors are responding\n"
        "- System: the broader structural shift in education this represents\n"
        "- Opportunity: what students or parents can actively do in response\n\n"
        "Rules for all five angles:\n"
        "- Never start title or learning_angle with Wiingy\n"
        "- Each angle must be genuinely distinct from the other four\n"
        "- wiingy_link must match the tone of the recommended style\n"
        "- learning_angle leads with education, Wiingy never appears until wiingy_link\n\n"
        "Return ONLY a valid JSON object with exactly this structure, no "
        "markdown fences, no extra text:\n"
        "{\n"
        '  "topic_reasoning": "string",\n'
        '  "recommended_style": "POLICY IMPACT" or "CULTURAL THINK-PIECE" or "NEWS CONSEQUENCE",\n'
        '  "style_reason": "string",\n'
        '  "angles": [\n'
        '    {\n'
        '      "lens": "Student",\n'
        '      "title": "string",\n'
        '      "learning_angle": "string",\n'
        '      "wiingy_link": "string",\n'
        '      "suggested_sources": "string"\n'
        '    },\n'
        '    {\n'
        '      "lens": "Parent",\n'
        '      "title": "string",\n'
        '      "learning_angle": "string",\n'
        '      "wiingy_link": "string",\n'
        '      "suggested_sources": "string"\n'
        '    },\n'
        '    {\n'
        '      "lens": "Educator",\n'
        '      "title": "string",\n'
        '      "learning_angle": "string",\n'
        '      "wiingy_link": "string",\n'
        '      "suggested_sources": "string"\n'
        '    },\n'
        '    {\n'
        '      "lens": "System",\n'
        '      "title": "string",\n'
        '      "learning_angle": "string",\n'
        '      "wiingy_link": "string",\n'
        '      "suggested_sources": "string"\n'
        '    },\n'
        '    {\n'
        '      "lens": "Opportunity",\n'
        '      "title": "string",\n'
        '      "learning_angle": "string",\n'
        '      "wiingy_link": "string",\n'
        '      "suggested_sources": "string"\n'
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
            story["recommended_style"] = result.get("recommended_style", "")
            story["style_reason"] = result.get("style_reason", "")
            story["angles"] = result.get("angles", [])
            return story
        except Exception:
            if attempt == 1:
                story["topic_reasoning"] = "Generation failed"
                story["recommended_style"] = "UNKNOWN"
                story["style_reason"] = ""
                story["angles"] = []
                return story

    return story
