# Required env vars: GEMINI_API_KEY, NEWS_API_KEY, GUARDIAN_API_KEY
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.main import app
