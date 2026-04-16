import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "prompts")


def _load_prompt(filename):
    path = os.path.join(PROMPTS_DIR, filename)
    with open(path, "r") as f:
        return f.read()


def generate_angle(story):
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=api_key)

        brand_context = _load_prompt("wiingy_brand_context.txt")

        system_prompt = (
            brand_context + "\n\n"
            "You are an education journalist writing a content angle for the "
            "Wiingy Newsroom. Your job is to find the genuine learning insight "
            "in this news story and express it in 2-3 sentences.\n\n"
            "Follow this structure strictly:\n"
            "- Lead with the broader educational truth or trend the story reveals\n"
            "- Connect it to what students, parents, or learners are experiencing\n"
            "- Only in the final sentence, and only if it fits naturally, add a "
            "brief Wiingy tie-in referencing tutor demand, subject trends, or "
            "platform observations. If a Wiingy reference does not fit naturally, "
            "write only 2 sentences and omit it entirely.\n\n"
            "Never start with Wiingy. Never lead with statistics. Never sound "
            "promotional. Write like a journalist, not a marketer. The angle "
            "should read as an interesting educational observation that stands "
            "on its own merit.\n\n"
            "Return only the angle text. No labels, no preamble, no explanation."
        )

        user_message = (
            f"Story title: {story.get('title', '')}\n"
            f"Story description: {story.get('description', '')}"
        )

        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash-lite",
            system_instruction=system_prompt,
        )

        response = model.generate_content(user_message)
        story["wiingy_angle"] = response.text.strip()
    except Exception:
        story["wiingy_angle"] = "Angle generation failed"

    return story
