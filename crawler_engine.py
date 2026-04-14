"""SEO Audit Crawler Engine — the core analysis module."""
import requests, re, ssl, time, concurrent.futures
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from collections import Counter

HEADERS = {"User-Agent": "SEO-Audit-App/2.0 (Python)"}
TIMEOUT = 12

class CrawlResult:
    def __init__(self):
        self.pages = {}          # url -> PageData
        self.broken_links = []   # {source, target, status}
        self.meta_issues = []    # {page, issue, current_value}
        self.orphan_pages = []   # pages with <3 in-content internal links
        self.hub_pages = []      # pages with 20+ internal links
        self.table_opportunities = []
        self.ai_readiness = {}
        self.health_score = 0
        self.stats = {"total": 0, "crawled": 0, "errors": 0}

    def to_dict(self):
        return {
            "pages": {url: p.__dict__ for url, p in self.pages.items()},
            "broken_links": self.broken_links,
            "meta_issues": self.meta_issues,
            "orphan_pages": self.orphan_pages,
            "hub_pages": self.hub_pages,
            "table_opportunities": self.table_opportunities,
            "ai_readiness": self.ai_readiness,
            "health_score": self.health_score,
            "stats": self.stats,
        }

class PageData:
    def __init__(self, url):
        self.url = url
        self.status = 0
        self.title = None
        self.title_len = 0
        self.description = None
        self.desc_len = 0
        self.h1 = None
        self.og_title = None
        self.og_description = None
        self.canonical = None
        self.internal_links = []
        self.external_links = []
        self.internal_link_count = 0
        self.external_link_count = 0
        self.has_table = False
        self.list_count = 0
        self.word_count = 0
        self.images_total = 0
        self.images_no_alt = 0

def fetch_page(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, verify=False, allow_redirects=True)
        return resp.status_code, resp.text, resp.url
    except requests.exceptions.Timeout:
        return 0, "", url
    except Exception as e:
        return 0, "", url

def check_url_status(url):
    try:
        resp = requests.head(url, headers=HEADERS, timeout=8, verify=False, allow_redirects=True)
        if resp.status_code == 405:
            resp = requests.get(url, headers=HEADERS, timeout=8, verify=False, allow_redirects=True, stream=True)
        return resp.status_code
    except:
        return 0

def extract_meta(soup):
    data = {}
    title_tag = soup.find("title")
    data["title"] = title_tag.get_text(strip=True) if title_tag else None
    data["title_len"] = len(data["title"]) if data["title"] else 0

    desc_tag = soup.find("meta", attrs={"name": "description"})
    data["description"] = desc_tag.get("content", "").strip() if desc_tag else None
    data["desc_len"] = len(data["description"]) if data["description"] else 0

    h1_tag = soup.find("h1")
    data["h1"] = h1_tag.get_text(strip=True) if h1_tag else None

    og_title = soup.find("meta", attrs={"property": "og:title"})
    data["og_title"] = og_title.get("content", "").strip() if og_title else None

    og_desc = soup.find("meta", attrs={"property": "og:description"})
    data["og_description"] = og_desc.get("content", "").strip() if og_desc else None

    canonical = soup.find("link", attrs={"rel": "canonical"})
    data["canonical"] = canonical.get("href", "").strip() if canonical else None

    return data

def extract_links(soup, base_url, site_domain):
    internal, external = [], []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        try:
            resolved = urljoin(base_url, href)
            parsed = urlparse(resolved)
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if clean_url in seen:
                continue
            seen.add(clean_url)
            if parsed.netloc == site_domain or parsed.netloc == f"www.{site_domain}":
                internal.append(clean_url)
            else:
                external.append(clean_url)
        except:
            pass
    return internal, external

def extract_content_stats(soup):
    has_table = bool(soup.find("table"))
    lists = soup.find_all("li")
    body = soup.find("body")
    text = body.get_text(" ", strip=True) if body else ""
    word_count = len(text.split())
    images = soup.find_all("img")
    images_no_alt = [img for img in images if not img.get("alt")]
    return {
        "has_table": has_table,
        "list_count": len(lists),
        "word_count": word_count,
        "images_total": len(images),
        "images_no_alt": len(images_no_alt),
    }

def detect_table_opportunity(page_data, html_text):
    if page_data.has_table:
        return False
    if page_data.list_count < 6:
        return False
    keywords = ['тариф', 'прайс', 'цена', 'стоимость', 'сравнен', 'характеристик',
                'преимущества', 'различи', 'перечень', 'этап', 'шаг', 'план',
                'услуг', 'функции', 'возможности', 'tariff', 'price', 'feature',
                'comparison', 'benefit', 'step', 'advantage']
    lower = html_text.lower()
    return any(k in lower for k in keywords)

def check_ai_readiness(site_url):
    result = {"robots_txt": {}, "llms_txt": {}}
    parsed = urlparse(site_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    # Check robots.txt
    try:
        resp = requests.get(f"{base}/robots.txt", headers=HEADERS, timeout=8, verify=False)
        if resp.status_code == 200:
            txt = resp.text.lower()
            result["robots_txt"]["exists"] = True
            result["robots_txt"]["has_gptbot"] = "gptbot" in txt
            result["robots_txt"]["has_claudebot"] = "claudebot" in txt
            result["robots_txt"]["has_perplexitybot"] = "perplexitybot" in txt
            result["robots_txt"]["has_google_extended"] = "google-extended" in txt
            result["robots_txt"]["has_sitemap"] = "sitemap" in txt
        else:
            result["robots_txt"]["exists"] = False
    except:
        result["robots_txt"]["exists"] = False

    # Check llms.txt
    try:
        resp = requests.get(f"{base}/llms.txt", headers=HEADERS, timeout=8, verify=False)
        result["llms_txt"]["exists"] = resp.status_code == 200
        if result["llms_txt"]["exists"]:
            result["llms_txt"]["size"] = len(resp.text)
    except:
        result["llms_txt"]["exists"] = False

    return result

def calculate_health_score(result):
    score = 100
    total_pages = max(result.stats["crawled"], 1)

    # Broken links penalty: -5 per broken link (max -30)
    score -= min(len(result.broken_links) * 5, 30)

    # Meta issues penalty: -1 per issue (max -30)
    score -= min(len(result.meta_issues) * 1, 30)

    # Orphan pages penalty: -3 per orphan (max -15)
    score -= min(len(result.orphan_pages) * 3, 15)

    # AI readiness bonus
    ai = result.ai_readiness
    if not ai.get("robots_txt", {}).get("has_gptbot", False):
        score -= 5
    if not ai.get("llms_txt", {}).get("exists", False):
        score -= 5

    # Errors penalty
    score -= min(result.stats["errors"] * 5, 15)

    return max(0, min(100, score))

def run_crawl(site_url, max_pages=50, progress_callback=None):
    """Main crawl function. Returns CrawlResult."""
    import warnings
    warnings.filterwarnings("ignore")

    result = CrawlResult()
    parsed = urlparse(site_url)
    site_domain = parsed.netloc.replace("www.", "")
    base = f"{parsed.scheme}://{parsed.netloc}"

    # Normalize start URL
    if not site_url.endswith("/"):
        site_url = site_url + "/"

    to_crawl = [site_url]
    crawled = set()
    all_internal_urls = set()
    checked_links = set()

    def update_progress(msg, pct):
        if progress_callback:
            progress_callback(msg, pct)

    update_progress("Начинаем обход сайта...", 5)

    # Phase 1: Try to get sitemap URLs first
    try:
        sitemap_resp = requests.get(f"{base}/sitemap.xml", headers=HEADERS, timeout=10, verify=False)
        if sitemap_resp.status_code == 200:
            sitemap_soup = BeautifulSoup(sitemap_resp.text, "html.parser")
            for loc in sitemap_soup.find_all("loc"):
                url = loc.get_text(strip=True)
                if site_domain in url and url not in crawled:
                    to_crawl.append(url)
            # Check sub-sitemaps
            for sitemap_tag in sitemap_soup.find_all("sitemap"):
                loc = sitemap_tag.find("loc")
                if loc:
                    sub_resp = requests.get(loc.get_text(strip=True), headers=HEADERS, timeout=10, verify=False)
                    if sub_resp.status_code == 200:
                        sub_soup = BeautifulSoup(sub_resp.text, "html.parser")
                        for sub_loc in sub_soup.find_all("loc"):
                            url = sub_loc.get_text(strip=True)
                            if site_domain in url:
                                to_crawl.append(url)
    except:
        pass

    # Deduplicate
    to_crawl = list(dict.fromkeys(to_crawl))[:max_pages]
    result.stats["total"] = len(to_crawl)
    update_progress(f"Найдено {len(to_crawl)} страниц для проверки", 10)

    # Phase 2: Crawl pages
    for i, url in enumerate(to_crawl):
        if url in crawled:
            continue
        crawled.add(url)

        pct = 10 + int((i / len(to_crawl)) * 60)
        update_progress(f"[{i+1}/{len(to_crawl)}] {urlparse(url).path or '/'}", pct)

        status, html, final_url = fetch_page(url)
        page = PageData(url)
        page.status = status

        if status != 200:
            result.stats["errors"] += 1
            result.broken_links.append({
                "source": "(sitemap/direct)",
                "target": url,
                "status": status,
                "type": "page_error"
            })
            result.pages[url] = page
            continue

        result.stats["crawled"] += 1
        soup = BeautifulSoup(html, "html.parser")

        # Extract meta
        meta = extract_meta(soup)
        for k, v in meta.items():
            setattr(page, k, v)

        # Check meta issues
        path = urlparse(url).path or "/"
        if not meta["title"]:
            result.meta_issues.append({"page": path, "issue": "Нет <title>", "current": ""})
        elif meta["title_len"] > 70:
            result.meta_issues.append({"page": path, "issue": f"Title длинный ({meta['title_len']} симв.)", "current": meta["title"]})
        elif meta["title_len"] < 10:
            result.meta_issues.append({"page": path, "issue": f"Title короткий ({meta['title_len']} симв.)", "current": meta["title"]})

        if not meta["description"]:
            result.meta_issues.append({"page": path, "issue": "Нет meta description", "current": ""})
        elif meta["desc_len"] > 160:
            result.meta_issues.append({"page": path, "issue": f"Description длинный ({meta['desc_len']} симв.)", "current": meta["description"][:80] + "..."})
        elif meta["desc_len"] < 50:
            result.meta_issues.append({"page": path, "issue": f"Description короткий ({meta['desc_len']} симв.)", "current": meta["description"]})

        if not meta["h1"]:
            result.meta_issues.append({"page": path, "issue": "Нет <h1>", "current": ""})
        if not meta["og_title"]:
            result.meta_issues.append({"page": path, "issue": "Нет og:title", "current": ""})
        if not meta["og_description"]:
            result.meta_issues.append({"page": path, "issue": "Нет og:description", "current": ""})

        # Extract links
        internal, external = extract_links(soup, url, site_domain)
        page.internal_links = internal
        page.external_links = external
        page.internal_link_count = len(internal)
        page.external_link_count = len(external)
        all_internal_urls.update(internal)

        # Content stats
        stats = extract_content_stats(soup)
        page.has_table = stats["has_table"]
        page.list_count = stats["list_count"]
        page.word_count = stats["word_count"]
        page.images_total = stats["images_total"]
        page.images_no_alt = stats["images_no_alt"]

        # Table opportunity
        if detect_table_opportunity(page, html):
            result.table_opportunities.append({
                "page": path,
                "list_count": page.list_count,
                "word_count": page.word_count,
                "reason": "Содержит списки и ключевые слова — кандидат для таблицы"
            })

        # Interlinking analysis
        if page.internal_link_count < 3:
            result.orphan_pages.append({"page": path, "links": page.internal_link_count})
        if page.internal_link_count > 20:
            result.hub_pages.append({"page": path, "links": page.internal_link_count})

        result.pages[url] = page

        # Discover new internal links to crawl
        for link in internal:
            if link not in crawled and link not in to_crawl and len(to_crawl) < max_pages:
                to_crawl.append(link)

    # Phase 3: Check for broken links via HEAD requests
    update_progress("Проверяем ссылки на битые...", 75)
    links_to_check = []
    for url, page in result.pages.items():
        for link in page.internal_links[:10]:  # sample 10 per page
            if link not in checked_links and link not in crawled:
                links_to_check.append((urlparse(url).path or "/", link))
                checked_links.add(link)

    # Check in parallel
    links_to_check = links_to_check[:100]  # cap at 100
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {}
        for source, target in links_to_check:
            futures[executor.submit(check_url_status, target)] = (source, target)
        for future in concurrent.futures.as_completed(futures):
            source, target = futures[future]
            try:
                status = future.result()
                if status >= 400 or status == 0:
                    result.broken_links.append({
                        "source": source,
                        "target": target,
                        "status": status,
                        "type": "broken_link"
                    })
            except:
                pass

    # Phase 4: AI readiness
    update_progress("Проверяем AI-готовность...", 90)
    result.ai_readiness = check_ai_readiness(site_url)

    # Calculate health score
    result.health_score = calculate_health_score(result)
    result.stats["total"] = len(to_crawl)

    update_progress("Аудит завершён!", 100)
    return result

def get_site_text_for_ai(result, max_chars=4000):
    """Extract key text from crawled pages for AI analysis."""
    texts = []
    for url, page in list(result.pages.items())[:10]:
        parts = []
        if page.title:
            parts.append(f"Title: {page.title}")
        if page.h1:
            parts.append(f"H1: {page.h1}")
        if page.description:
            parts.append(f"Desc: {page.description}")
        parts.append(f"URL: {url}")
        texts.append(" | ".join(parts))
    return "\n".join(texts)[:max_chars]
