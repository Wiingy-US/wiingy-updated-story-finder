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
            "Write a 1-2 sentence Wiingy Newsroom content angle that positions "
            "Wiingy as a credible expert voice on this story. The angle must "
            "reference a specific Wiingy platform data point or the tutor network. "
            "It must sound journalistic and authoritative, never promotional. "
            "Return only the angle text, nothing else."
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
