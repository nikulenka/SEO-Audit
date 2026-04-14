import sys, os, json
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

from google import genai
from google.genai import types

client = genai.Client(api_key=GEMINI_API_KEY)

prompt = """Find 3 actual competitors for byedi.by in Belarus. Return ONLY valid JSON:
[{"name": "...", "url": "..."}]
DO NOT hallucinate URLs."""

try:
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[{"google_search": {}}]
        )
    )
    print(response.text)
except Exception as e:
    print(f"Exception: {e}")
