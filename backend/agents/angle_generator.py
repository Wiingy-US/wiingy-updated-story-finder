import os
import json
import traceback
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()


def generate_angle(story):
    print(f"[angle] Generating angles for: {story.get('title', '')[:80]}")

    try:
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("[angle] ERROR: GEMINI_API_KEY not set")
            return {**story, "angles": [], "angle_error": "API key not set"}

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash-lite')

        title = story.get('title', '')
        description = story.get('description', '')
        source = story.get('source', '')
        published = story.get('published', '')

        prompt = f"""Consider this news article, and share 5 PR worthy content \
angles, on Wiingy's behalf, that will help cement Wiingy's relevance \
in the online tutoring space.

Article Title: {title}
Source: {source}
Published: {published}
Summary: {description}

For each of the 5 angles return:
1. title: A punchy article headline (not a question, not clickbait)
2. angle: 2-3 sentences of the content angle
3. wiingy_data_point: One specific Wiingy fact or data point \
that makes this angle credible. Choose from:
- Less than 3% of tutor applicants are accepted
- Lessons start at $20-$28/hour vs industry average of $60-$150/hour
- Free trial lesson, no credit card required
- No subscriptions, pay per lesson
- Perfect Match Guarantee, free tutor replacement
- 10-day no-questions-asked refund
- 24/7 support with dedicated student success advisor
- Fully online with interactive whiteboards and code editors
- 20,000+ students served
- 350+ subjects taught
- 4,500+ expert-vetted tutors
- 50+ countries served
- Rated 4.8/5 by students and parents

Return ONLY a valid JSON object with no markdown fences:
{{
  "angles": [
    {{
      "number": 1,
      "title": "string",
      "angle": "string",
      "wiingy_data_point": "string"
    }},
    {{
      "number": 2,
      "title": "string",
      "angle": "string",
      "wiingy_data_point": "string"
    }},
    {{
      "number": 3,
      "title": "string",
      "angle": "string",
      "wiingy_data_point": "string"
    }},
    {{
      "number": 4,
      "title": "string",
      "angle": "string",
      "wiingy_data_point": "string"
    }},
    {{
      "number": 5,
      "title": "string",
      "angle": "string",
      "wiingy_data_point": "string"
    }}
  ]
}}"""

        response = model.generate_content(prompt)
        raw = response.text.strip()
        print(f"[angle] Raw response preview: {raw[:200]}")

        raw = raw.replace('```json', '').replace('```', '').strip()

        parsed = json.loads(raw)
        angles = parsed.get('angles', [])

        print(f"[angle] Successfully parsed {len(angles)} angles")
        return {**story, "angles": angles, "angle_error": None}

    except json.JSONDecodeError as e:
        print(f"[angle] JSON parse error: {e}")
        try:
            response = model.generate_content(
                prompt + "\n\nIMPORTANT: Return ONLY raw JSON. "
                "No markdown. No backticks. Start with { and end with }"
            )
            raw = response.text.strip()
            raw = raw.replace('```json', '').replace('```', '').strip()
            parsed = json.loads(raw)
            angles = parsed.get('angles', [])
            print(f"[angle] Retry succeeded: {len(angles)} angles")
            return {**story, "angles": angles, "angle_error": None}
        except Exception as retry_err:
            print(f"[angle] Retry failed: {retry_err}")
            return {**story, "angles": [],
                    "angle_error": "Generation failed after retry"}

    except Exception as e:
        print(f"[angle] Error: {e}")
        traceback.print_exc()
        return {**story, "angles": [], "angle_error": str(e)}
