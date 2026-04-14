"""SEO Audit Web Application — Flask Server."""
import json, os, threading, time, uuid
from flask import Flask, render_template, request, jsonify
from crawler_engine import run_crawl, get_site_text_for_ai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY is not set. AI features will not work.")

# In-memory store for audit jobs
jobs = {}

def run_ai_analysis(site_text, site_url):
    """Run Gemini AI analysis for keywords, competitors, tables."""
    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)

        prompt = f"""You are an expert Enterprise SEO & RAG analyst. Analyze this website data and provide a deep GEO (Generative Engine Optimization) analysis:

1. **Top 15 Keywords**: The most relevant SEO keywords for this site, with estimated search volume (low/medium/high) and difficulty (low/medium/high). Output as JSON array: [{{"keyword": "...", "volume": "...", "difficulty": "..."}}]

2. **Top 5 Competitors**: REAL competitor websites in the same niche. You MUST use Google Search to find real, currently existing competitors. DO NOT invent or hallucinate URLs. Output as JSON array: [{{"name": "...", "url": "...", "strength": "..."}}]

3. **Table Recommendations**: Which pages would benefit most from having HTML tables (for AI snippets). Output as JSON array: [{{"page": "...", "table_type": "...", "columns": ["..."]}}]

4. **E-E-A-T Signals**: Assess Expertise, Authoritativeness, and Trust based on content/schemas. Output as object: {{"authors_found": true/false, "reputation_markers": ["..."], "score_1_to_10": 8}}

5. **RAG Readiness**: Evaluate how well an LLM can understand this site. Extract main entities and compute topical authority. Output as object: {{"entities_extracted": ["..."], "topical_authority_score": 7, "suggestions": ["..."]}}

Website URL: {site_url}
Website data (Title/H1/Desc/Schemas per page):
{site_text}

IMPORTANT: Return ONLY valid JSON in this exact format, no markdown:
{{
  "keywords": [...], 
  "competitors": [...], 
  "table_recommendations": [...],
  "eeat_signals": {{"authors_found": false, "reputation_markers": [], "score_1_to_10": 5}},
  "rag_readiness": {{"entities_extracted": [], "topical_authority_score": 5, "suggestions": []}}
}}"""

        from google.genai import types
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}]
            )
        )
        text = response.text.strip()
        # Clean up markdown code blocks if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        if text.startswith("json"):
            text = text[4:]
        return json.loads(text.strip())
    except Exception as e:
        return {
            "error": str(e), 
            "keywords": [], "competitors": [], "table_recommendations": [],
            "eeat_signals": {"authors_found": False, "reputation_markers": [], "score_1_to_10": 0},
            "rag_readiness": {"entities_extracted": [], "topical_authority_score": 0, "suggestions": []}
        }

def audit_worker(job_id, url, max_pages):
    """Background worker for audit job."""
    job = jobs[job_id]
    job["status"] = "running"

    def progress_cb(msg, pct):
        job["progress"] = pct
        job["message"] = msg

    try:
        # Phase 1: Crawl
        result = run_crawl(url, max_pages=max_pages, progress_callback=progress_cb)
        job["crawl_result"] = result.to_dict()

        # Phase 2: AI Analysis
        job["message"] = "Запуск AI-анализа (ключевые слова, конкуренты)..."
        job["progress"] = 92
        site_text = get_site_text_for_ai(result)
        ai_data = run_ai_analysis(site_text, url)
        job["ai_analysis"] = ai_data

        job["status"] = "done"
        job["progress"] = 100
        job["message"] = "Аудит завершён!"
    except Exception as e:
        job["status"] = "error"
        job["message"] = f"Ошибка: {str(e)}"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/audit", methods=["POST"])
def start_audit():
    data = request.get_json()
    url = data.get("url", "").strip()
    max_pages = int(data.get("max_pages", 50))

    if not url:
        return jsonify({"error": "URL is required"}), 400
    if not url.startswith("http"):
        url = "https://" + url

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "id": job_id,
        "url": url,
        "status": "queued",
        "progress": 0,
        "message": "В очереди...",
        "crawl_result": None,
        "ai_analysis": None,
    }

    thread = threading.Thread(target=audit_worker, args=(job_id, url, max_pages), daemon=True)
    thread.start()

    return jsonify({"job_id": job_id})

@app.route("/api/status/<job_id>")
def get_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify({
        "id": job["id"],
        "url": job["url"],
        "status": job["status"],
        "progress": job["progress"],
        "message": job["message"],
        "crawl_result": job["crawl_result"] if job["status"] == "done" else None,
        "ai_analysis": job["ai_analysis"] if job["status"] == "done" else None,
    })

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    port = int(os.environ.get("PORT", 5000))
    print(f"\n🔍 SEO Audit App running at http://0.0.0.0:{port}\n")
    app.run(debug=False, host="0.0.0.0", port=port)
