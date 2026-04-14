#!/usr/bin/env python3
"""SEO Deep Crawler for CTT.BY — checks broken links, meta tags, interlinking, table opportunities."""
import urllib.request, urllib.error, re, json, sys, ssl
from urllib.parse import urljoin, urlparse
from html.parser import HTMLParser

SITE = "https://ctt.by"
TIMEOUT = 15
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

PAGES = [
    "/","/register/","/services/","/services/edi-messages/","/services/elektronnye-dokumenty/",
    "/services/elektronnye-akty/","/services/elektronny-faktoring/","/services/markirovka-odezhdy/",
    "/services/markirovka-postelnogo-belja/","/services/web-versiya-edi-sistemy-stt/",
    "/services/mezhdunarodnyy-elektronnyy-dokumentooborot/",
    "/integracija-edi-sistemy-stt/","/integratsiya-edi-sistemy-stt-s-1s/",
    "/integracija-edi-sistemy-stt/integracija-s-edi-sistemoj-stt-cherez-rest-api-i-soap-api/",
    "/integracija-edi-sistemy-stt/integracija-edi-sistemy-stt-cherez-edi-adapter-edi-connector/",
    "/company/partnership/","/feedback/","/user-guide/",
    "/rukovodstvo-polzovatelja-edi-sistemoj-stt/",
    "/poshagovyj-algoritm-zapuska-jelektronnyh-nakladnyh/",
    "/avtomaticheskaya-proverka-sroka-deystviya-gln-v-edi-sisteme-stt/",
    "/price","/support","/contacts/","/pomoshh-klientam/",
    # Blog posts (sample)
    "/granit/","/savushkin/","/news10/","/news11/","/news12/","/news13/","/news14/",
    "/news15/","/news16/","/news17/","/news19/","/news1/","/news2/",
    "/must-have-dlya-ritejla-edo/","/chem-horosh-perekhod-na-edo-dlya-biznesa/",
    "/chto-takoe-ecp-i-kak-ee-poluchit/","/kak-perejti-na-elektronnye-dokumenty/",
    "/9-prichin-pochemu-edo-nuzhen-imenno-vam/",
    "/edi-provayder-stt-lider-tsifrovoy-ekonomiki/",
    "/edi-sistema-stt-luchshaya-tsifrovaya-platforma/",
    "/novyy-preyskurant-na-dopolnitelnyye-uslugi/",
    "/benefits_buyer/","/benefits_seller/",
    "/markirovka-molochnoj-produkcii-jelektronnye-nakladnye/",
    "/markirovka-i-proslezhivaemost-tovarov/",
    "/bezopasnost-edi-platformy-topby/","/edi-provajder-ctt-rezident-pvt/",
    "/tehnicheskie-raboty/",
    "/biznes-vstrecha-po-voprosam-razvitija-jelektronnoj-kommercii-v-roznichnoj-torgovle-2018/",
    "/biznes-vstrecha-po-voprosam-razvitija-jelektronnogo-dokumentooborota-v-belarusi-2019/",
    "/itogi-vebinara-jelektronnye-nakladnye-proslezhivaemost-i-markirovka-tovarov-v-2021g/",
    # Categories
    "/category/news/","/category/news/actions/","/category/news/blog/",
    "/category/news/webinars/","/category/cases/","/category/news/activity/",
    "/category/news/novosti-edi-platformy/","/category/news/events/",
    "/category/uncategorized/",
]

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "SEO-Audit-Bot/1.0"})
    try:
        resp = urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx)
        return resp.getcode(), resp.read().decode("utf-8", errors="replace"), resp.geturl()
    except urllib.error.HTTPError as e:
        return e.code, "", url
    except Exception as e:
        return 0, "", url

def head_check(url):
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "SEO-Audit-Bot/1.0"})
    try:
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        return resp.getcode()
    except urllib.error.HTTPError as e:
        return e.code
    except:
        return 0

def extract_meta(html):
    title_m = re.search(r'<title[^>]*>(.*?)</title>', html, re.S|re.I)
    desc_m = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', html, re.S|re.I) or \
             re.search(r'<meta\s+content=["\'](.*?)["\']\s+name=["\']description["\']', html, re.S|re.I)
    og_title_m = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\'](.*?)["\']', html, re.S|re.I)
    og_desc_m = re.search(r'<meta\s+property=["\']og:description["\']\s+content=["\'](.*?)["\']', html, re.S|re.I)
    h1_m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S|re.I)
    canonical_m = re.search(r'<link\s+rel=["\']canonical["\']\s+href=["\'](.*?)["\']', html, re.S|re.I)
    clean = lambda s: re.sub(r'<[^>]+>', '', s).strip() if s else None
    return {
        "title": clean(title_m.group(1)) if title_m else None,
        "title_len": len(clean(title_m.group(1))) if title_m else 0,
        "description": desc_m.group(1).strip() if desc_m else None,
        "desc_len": len(desc_m.group(1).strip()) if desc_m else 0,
        "og_title": og_title_m.group(1).strip() if og_title_m else None,
        "og_description": og_desc_m.group(1).strip() if og_desc_m else None,
        "h1": clean(h1_m.group(1)) if h1_m else None,
        "canonical": canonical_m.group(1).strip() if canonical_m else None,
    }

def extract_links(html, base_url):
    links = re.findall(r'<a\s+[^>]*href=["\']([^"\'#]+)["\']', html, re.I)
    internal, external = [], []
    seen = set()
    for href in links:
        if href.startswith(("mailto:", "tel:", "javascript:")): continue
        try:
            resolved = urljoin(base_url, href)
            parsed = urlparse(resolved)
            if parsed.hostname in ("ctt.by", "www.ctt.by"):
                path = parsed.path
                if path not in seen:
                    seen.add(path)
                    internal.append(resolved)
            else:
                external.append(resolved)
        except: pass
    return internal, external

def table_opportunity(html):
    has_table = bool(re.search(r'<table', html, re.I))
    li_count = len(re.findall(r'<li', html, re.I))
    keywords = ['тариф','прайс','цена','стоимость','сравнен','характеристик',
                'преимущества','различи','перечень','этап','шаг','план','услуг']
    lower = html.lower()
    has_kw = any(k in lower for k in keywords)
    return (not has_table) and li_count > 6 and has_kw

def main():
    broken_links = []
    no_internal = []
    meta_issues = []
    table_opps = []
    stats = {"total": len(PAGES), "crawled": 0, "errors": 0}
    checked_urls = set()  # avoid re-checking same broken link

    for i, path in enumerate(PAGES):
        url = SITE + path
        sys.stdout.write(f"[{i+1}/{len(PAGES)}] {path} ... ")
        sys.stdout.flush()

        status, html, final_url = fetch(url)
        if status != 200:
            print(f"HTTP {status}")
            broken_links.append({"page": path, "broken_url": url, "status": status, "type": "self"})
            stats["errors"] += 1
            continue

        stats["crawled"] += 1
        meta = extract_meta(html)

        # --- META TAG ISSUES ---
        issues = []
        if not meta["title"]:
            issues.append("Нет <title>")
        elif meta["title_len"] < 10:
            issues.append(f"Title короткий ({meta['title_len']} симв.)")
        elif meta["title_len"] > 70:
            issues.append(f"Title длинный ({meta['title_len']} симв.)")

        if not meta["description"]:
            issues.append("Нет meta description")
        elif meta["desc_len"] < 50:
            issues.append(f"Description короткий ({meta['desc_len']} симв.)")
        elif meta["desc_len"] > 160:
            issues.append(f"Description длинный ({meta['desc_len']} симв.)")

        if not meta["h1"]:
            issues.append("Нет <h1>")
        if not meta["og_title"]:
            issues.append("Нет og:title")
        if not meta["og_description"]:
            issues.append("Нет og:description")

        for issue in issues:
            meta_issues.append({"page": path, "issue": issue, "title": meta["title"], "h1": meta["h1"]})

        # --- INTERNAL LINKS ---
        internal, external = extract_links(html, url)
        if len(internal) < 3:
            no_internal.append({"page": path, "internal_link_count": len(internal)})

        # --- BROKEN LINKS (sample first 5 internal) ---
        for link in internal[:5]:
            if link in checked_urls: continue
            checked_urls.add(link)
            ls = head_check(link)
            if ls >= 400 or ls == 0:
                broken_links.append({"page": path, "broken_url": link, "status": ls})

        # --- TABLE OPPORTUNITIES ---
        if table_opportunity(html):
            table_opps.append({"page": path, "reason": "Содержит списки и ключевые слова — кандидат для таблицы"})

        meta_flag = "✓" if not issues else f"✗({len(issues)})"
        print(f"OK links:{len(internal)} meta:{meta_flag}")

    # --- OUTPUT ---
    results = {
        "summary": stats,
        "broken_links": broken_links,
        "pages_without_internal_links": no_internal,
        "meta_tag_issues": meta_issues,
        "table_opportunities": table_opps,
    }
    
    out_path = "/Users/vitalyn/00 Antigravity/SEO Audit/reports/crawl_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n\n=== RESULTS SAVED TO {out_path} ===")
    print(f"Total: {stats['total']}, Crawled: {stats['crawled']}, Errors: {stats['errors']}")
    print(f"Broken links found: {len(broken_links)}")
    print(f"Pages with poor interlinking: {len(no_internal)}")
    print(f"Meta tag issues: {len(meta_issues)}")
    print(f"Table opportunities: {len(table_opps)}")

if __name__ == "__main__":
    main()
