from google import genai

GEMINI_API_KEY = "AIzaSyAIYgJ6dzJMWk8uwLB8Mbm4S866T9B6_Ic"
client = genai.Client(api_key=GEMINI_API_KEY)

prompt = """You are an expert SEO analyst. Analyze this website data and provide:

1. **Top 15 Keywords**: The most relevant SEO keywords for this site, with estimated search volume (low/medium/high) and difficulty (low/medium/high). Output as JSON array: [{"keyword": "...", "volume": "...", "difficulty": "..."}]

2. **Top 5 Competitors**: Likely competitor websites in the same niche. Output as JSON array: [{"name": "...", "url": "...", "strength": "..."}]

3. **Table Recommendations**: Which pages would benefit most from having HTML tables (for AI search optimization). Output as JSON array: [{"page": "...", "table_type": "...", "columns": ["..."]}]

Website URL: https://ctt.by
Website data:
Title: Welcome

IMPORTANT: Return ONLY valid JSON in this exact format, no markdown:
{"keywords": [...], "competitors": [...], "table_recommendations": [...]}"""

try:
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    print("Response text:", response.text)
except Exception as e:
    print("Exception:", str(e))
