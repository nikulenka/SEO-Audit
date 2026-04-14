import sys, os
import json
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("NO API KEY")
    sys.exit(1)

from google import genai
client = genai.Client(api_key=GEMINI_API_KEY)

prompt = """You are an expert Enterprise SEO & RAG analyst. Analyze this website data and provide a deep GEO (Generative Engine Optimization) analysis:

1. **Top 15 Keywords**: The most relevant SEO keywords for this site, with estimated search volume (low/medium/high) and difficulty (low/medium/high). Output as JSON array: [{"keyword": "...", "volume": "...", "difficulty": "..."}]

2. **Top 5 Competitors**: Likely competitor websites in the same niche. Output as JSON array: [{"name": "...", "url": "...", "strength": "..."}]

3. **Table Recommendations**: Which pages would benefit most from having HTML tables (for AI snippets). Output as JSON array: [{"page": "...", "table_type": "...", "columns": ["..."]}]

4. **E-E-A-T Signals**: Assess Expertise, Authoritativeness, and Trust based on content/schemas. Output as object: {"authors_found": true/false, "reputation_markers": ["..."], "score_1_to_10": 8}

5. **RAG Readiness**: Evaluate how well an LLM can understand this site. Extract main entities and compute topical authority. Output as object: {"entities_extracted": ["..."], "topical_authority_score": 7, "suggestions": ["..."]}

Website URL: https://example.com
Website data (Title/H1/Desc/Schemas per page):
Title: Example Domain | URL: https://example.com/
Desc: This domain is for use in illustrative examples in documents.

IMPORTANT: Return ONLY valid JSON in this exact format, no markdown:
{
  "keywords": [...], 
  "competitors": [...], 
  "table_recommendations": [...],
  "eeat_signals": {"authors_found": false, "reputation_markers": [], "score_1_to_10": 5},
  "rag_readiness": {"entities_extracted": [], "topical_authority_score": 5, "suggestions": []}
}"""

try:
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    print("Raw text:")
    text = response.text.strip()
    print(text)
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    if text.startswith("json"):
        text = text[4:]
    print("\nParsed json:")
    print(json.loads(text.strip()))
except Exception as e:
    print(f"Exception: {e}")
