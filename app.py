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


        prompt = f"""You are an expert SEO analyst. Analyze this website data and provide:

1. **Top 15 Keywords**: The most relevant SEO keywords for this site, with estimated search volume (low/medium/high) and difficulty (low/medium/high). Output as JSON array: [{{"keyword": "...", "volume": "...", "difficulty": "..."}}]

2. **Top 5 Competitors**: Likely competitor websites in the same niche. Output as JSON array: [{{"name": "...", "url": "...", "strength": "..."}}]

3. **Table Recommendations**: Which pages would benefit most from having HTML tables (for AI search optimization). Output as JSON array: [{{"page": "...", "table_type": "...", "columns": ["..."]}}]

Website URL: {site_url}
Website data:
{site_text}

IMPORTANT: Return ONLY valid JSON in this exact format, no markdown:
{{"keywords": [...], "competitors": [...], "table_recommendations": [...]}}"""

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
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
        return {"error": str(e), "keywords": [], "competitors": [], "table_recommendations": []}

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
    print("\n🔍 SEO Audit App running at http://127.0.0.1:5000\n")
    app.run(debug=False, host="127.0.0.1", port=5000)
