import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Read API key
API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()

# Gemini Active & Fallback Models
# Verified active models: gemini-3.5-flash, gemini-3.8-flash, gemini-3.7-flash, gemini-3.1-flash-lite
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
FALLBACK_MODELS = [
    DEFAULT_MODEL,
    "gemini-3.5-flash",
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash"
]

client = None
if API_KEY:
    try:
        from google import genai
        client = genai.Client(api_key=API_KEY)
    except Exception as e:
        print(f"Warning: Failed to initialize Google GenAI client: {e}")
        client = None

MODEL_NAME = DEFAULT_MODEL
