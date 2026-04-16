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
        "You are an education journalist writing for the Wiingy Newsroom. "
        "Given a news story, you must produce two things:\n\n"
        "PART 1 — TOPIC REASONING (1-2 sentences):\n"
        "Explain why this story is worth covering from an education and "
        "learning perspective. What makes it timely and relevant to students, "
        "parents, or educators right now? This is internal guidance for the "
        "editor, not published content.\n\n"
        "PART 2 — FIVE CONTENT ANGLES:\n"
        "Write 5 distinct content angles for this story. Each angle must be "
        "2-3 sentences. Each one must approach the story from a genuinely "
        "different perspective — do not write 5 variations of the same point.\n\n"
        "The 5 angles must follow these five distinct lenses:\n\n"
        "Angle 1 — THE STUDENT LENS:\n"
        "Focus on how this story affects students directly. What does it mean "
        "for how they learn, study, or prepare?\n\n"
        "Angle 2 — THE PARENT LENS:\n"
        "Focus on what parents are experiencing or deciding in response to "
        "this trend. What concern or opportunity does this raise for families?\n\n"
        "Angle 3 — THE EDUCATOR LENS:\n"
        "Focus on how teachers, tutors, or education professionals are "
        "responding to or driving this trend.\n\n"
        "Angle 4 — THE SYSTEM LENS:\n"
        "Focus on the broader structural shift in education this story "
        "represents. What is changing about how learning is organised or "
        "delivered at scale?\n\n"
        "Angle 5 — THE OPPORTUNITY LENS:\n"
        "Focus on what students or parents can do in response to this trend. "
        "What is the actionable learning insight here?\n\n"
        "Rules for all five angles:\n"
        "- Lead with the educational truth, never with Wiingy\n"
        "- Only include a Wiingy reference in the final sentence if it fits "
        "naturally — tutoring demand, subject trends, or tutor observations\n"
        "- Never start with Wiingy. Never sound promotional.\n"
        "- Each angle must be genuinely distinct from the other four\n"
        "- Write like a journalist, not a marketer\n\n"
        "Return ONLY a valid JSON object with exactly this structure and no "
        "markdown fences:\n"
        "{\n"
        '  "topic_reasoning": "string",\n'
        '  "angles": [\n'
        '    { "lens": "Student", "angle": "string" },\n'
        '    { "lens": "Parent", "angle": "string" },\n'
        '    { "lens": "Educator", "angle": "string" },\n'
        '    { "lens": "System", "angle": "string" },\n'
        '    { "lens": "Opportunity", "angle": "string" }\n'
        "  ]\n"
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
