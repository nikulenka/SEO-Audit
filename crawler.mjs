// SEO Deep Crawler for CTT.BY
// Checks: broken links, internal linking, meta tags, table opportunities

import https from 'https';
import http from 'http';
import { URL } from 'url';

const SITE = 'https://ctt.by';
const TIMEOUT = 15000;

// All URLs from sitemaps (pages, posts, categories)
const PAGES = [
  // ---- KEY PAGES ----
  '/', '/register/', '/services/', '/services/edi-messages/', '/services/elektronnye-dokumenty/',
  '/services/elektronnye-akty/', '/services/elektronny-faktoring/', '/services/markirovka-odezhdy/',
  '/services/markirovka-postelnogo-belja/', '/services/web-versiya-edi-sistemy-stt/',
  '/services/mezhdunarodnyy-elektronnyy-dokumentooborot/',
  '/integracija-edi-sistemy-stt/', '/integratsiya-edi-sistemy-stt-s-1s/',
  '/integracija-edi-sistemy-stt/integracija-s-edi-sistemoj-stt-cherez-rest-api-i-soap-api/',
  '/integracija-edi-sistemy-stt/integracija-edi-sistemy-stt-cherez-edi-adapter-edi-connector/',
  '/company/partnership/', '/feedback/', '/user-guide/',
  '/rukovodstvo-polzovatelja-edi-sistemoj-stt/',
  '/poshagovyj-algoritm-zapuska-jelektronnyh-nakladnyh/',
  '/avtomaticheskaya-proverka-sroka-deystviya-gln-v-edi-sisteme-stt/',
  // ---- BLOG POSTS (sample) ----
  '/granit/', '/savushkin/', '/news10/', '/news11/', '/news12/', '/news13/', '/news14/',
  '/news15/', '/news16/', '/news17/', '/news19/', '/news2/', '/news1/',
  '/biznes-vstrecha-po-voprosam-razvitija-jelektronnoj-kommercii-v-roznichnoj-torgovle-2018/',
  '/biznes-vstrecha-po-voprosam-razvitija-jelektronnogo-dokumentooborota-v-belarusi-2019/',
  '/vebinar-jelektronnye-nakladnye-prakticheskij-kejs-almi-i-glavmolsnab-primer-realizacii-edi-v-1s-ot-misoft/',
  '/itogi-vebinara-jelektronnye-nakladnye-proslezhivaemost-i-markirovka-tovarov-v-2021g/',
  '/must-have-dlya-ritejla-edo/', '/chem-horosh-perekhod-na-edo-dlya-biznesa/',
  '/chto-takoe-ecp-i-kak-ee-poluchit/', '/kak-perejti-na-elektronnye-dokumenty/',
  '/9-prichin-pochemu-edo-nuzhen-imenno-vam/',
  '/edi-provayder-stt-lider-tsifrovoy-ekonomiki/',
  '/edi-sistema-stt-luchshaya-tsifrovaya-platforma/',
  '/novyy-preyskurant-na-dopolnitelnyye-uslugi/',
  '/benefits_buyer/', '/benefits_seller/',
  '/markirovka-molochnoj-produkcii-jelektronnye-nakladnye/',
  '/markirovka-i-proslezhivaemost-tovarov/',
  '/bezopasnost-edi-platformy-topby/', '/edi-provajder-ctt-rezident-pvt/',
  '/tehnicheskie-raboty/',
  // ---- CATEGORIES ----
  '/category/news/', '/category/news/actions/', '/category/news/blog/',
  '/category/news/webinars/', '/category/cases/', '/category/news/activity/',
  '/category/news/novosti-edi-platformy/', '/category/news/events/',
  '/category/uncategorized/',
  // ---- KNOWN IMPORTANT PAGES ----
  '/price', '/support', '/contacts/', '/pomoshh-klientam/',
];

function fetch(url) {
  return new Promise((resolve, reject) => {
    const mod = url.startsWith('https') ? https : http;
    const req = mod.get(url, { timeout: TIMEOUT, headers: { 'User-Agent': 'SEO-Audit-Bot/1.0' } }, (res) => {
      // Follow redirects
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        let loc = res.headers.location;
        if (loc.startsWith('/')) loc = SITE + loc;
        return fetch(loc).then(resolve).catch(reject);
      }
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve({ status: res.statusCode, html: data, url }));
    });
    req.on('error', e => reject(e));
    req.on('timeout', () => { req.destroy(); reject(new Error('timeout')); });
  });
}

function extractMeta(html) {
  const titleMatch = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
  const descMatch = html.match(/<meta\s+name=["']description["']\s+content=["']([\s\S]*?)["']/i)
    || html.match(/<meta\s+content=["']([\s\S]*?)["']\s+name=["']description["']/i);
  const ogTitleMatch = html.match(/<meta\s+property=["']og:title["']\s+content=["']([\s\S]*?)["']/i);
  const ogDescMatch = html.match(/<meta\s+property=["']og:description["']\s+content=["']([\s\S]*?)["']/i);
  const h1Match = html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/i);
  const canonicalMatch = html.match(/<link\s+rel=["']canonical["']\s+href=["']([\s\S]*?)["']/i);

  return {
    title: titleMatch ? titleMatch[1].trim().replace(/<[^>]+>/g, '') : null,
    description: descMatch ? (descMatch[1] || '').trim() : null,
    ogTitle: ogTitleMatch ? ogTitleMatch[1].trim() : null,
    ogDescription: ogDescMatch ? ogDescMatch[1].trim() : null,
    h1: h1Match ? h1Match[1].trim().replace(/<[^>]+>/g, '') : null,
    canonical: canonicalMatch ? canonicalMatch[1].trim() : null,
  };
}

function extractLinks(html, pageUrl) {
  const linkRegex = /<a\s+[^>]*href=["']([^"'#]+)["'][^>]*>/gi;
  const links = [];
  let match;
  while ((match = linkRegex.exec(html)) !== null) {
    let href = match[1].trim();
    if (href.startsWith('mailto:') || href.startsWith('tel:') || href.startsWith('javascript:')) continue;
    try {
      const resolved = new URL(href, pageUrl);
      links.push({
        href: resolved.href,
        isInternal: resolved.hostname === 'ctt.by' || resolved.hostname === 'www.ctt.by',
      });
    } catch(e) {}
  }
  return links;
}

function hasTables(html) {
  return (html.match(/<table/gi) || []).length;
}

function tableOpportunity(html, path) {
  // Pages that discuss pricing, comparison, features, or lists are table candidates
  const keywords = ['тариф', 'прайс', 'цена', 'стоимость', 'сравнен', 'характеристик',
    'преимущества', 'различи', 'услуг', 'перечень', 'список', 'этап', 'шаг', 'план'];
  const lower = html.toLowerCase();
  const listCount = (html.match(/<li/gi) || []).length;
  const hasKeyword = keywords.some(k => lower.includes(k));
  // If there are many list items and relevant keywords, it's a candidate
  return (listCount > 6 && hasKeyword && hasTables(html) === 0);
}

async function checkLink(url) {
  return new Promise((resolve) => {
    const mod = url.startsWith('https') ? https : http;
    const req = mod.request(url, { method: 'HEAD', timeout: 10000, headers: { 'User-Agent': 'SEO-Audit-Bot/1.0' } }, (res) => {
      resolve(res.statusCode);
    });
    req.on('error', () => resolve(0));
    req.on('timeout', () => { req.destroy(); resolve(0); });
    req.end();
  });
}

async function run() {
  const results = {
    brokenLinks: [],       // { page, brokenUrl, status }
    noInternalLinks: [],   // { page, internalLinkCount }
    metaIssues: [],        // { page, issue }
    tableOpportunities: [], // { page, reason }
    summary: { total: 0, crawled: 0, errors: 0 },
  };

  results.summary.total = PAGES.length;

  for (let i = 0; i < PAGES.length; i++) {
    const path = PAGES[i];
    const fullUrl = SITE + path;
    process.stdout.write(`[${i+1}/${PAGES.length}] ${path} ... `);

    try {
      const { status, html } = await fetch(fullUrl);
      if (status !== 200) {
        console.log(`HTTP ${status}`);
        results.brokenLinks.push({ page: path, brokenUrl: fullUrl, status, type: 'self' });
        results.summary.errors++;
        continue;
      }

      results.summary.crawled++;

      // 1. Meta tags check
      const meta = extractMeta(html);
      if (!meta.title) results.metaIssues.push({ page: path, issue: 'Отсутствует <title>' });
      else if (meta.title.length < 10) results.metaIssues.push({ page: path, issue: `Title слишком короткий: "${meta.title}"` });
      else if (meta.title.length > 70) results.metaIssues.push({ page: path, issue: `Title слишком длинный (${meta.title.length} симв.)` });

      if (!meta.description) results.metaIssues.push({ page: path, issue: 'Отсутствует meta description' });
      else if (meta.description.length < 50) results.metaIssues.push({ page: path, issue: `Description слишком короткий (${meta.description.length} симв.)` });
      else if (meta.description.length > 160) results.metaIssues.push({ page: path, issue: `Description слишком длинный (${meta.description.length} симв.)` });

      if (!meta.h1) results.metaIssues.push({ page: path, issue: 'Отсутствует <h1>' });
      if (!meta.ogTitle) results.metaIssues.push({ page: path, issue: 'Отсутствует og:title' });
      if (!meta.ogDescription) results.metaIssues.push({ page: path, issue: 'Отсутствует og:description' });

      // 2. Links extraction & internal link count
      const links = extractLinks(html, fullUrl);
      const internalLinks = links.filter(l => l.isInternal);
      const externalLinks = links.filter(l => !l.isInternal);

      // Exclude navigation/footer links - count only in-content links
      // We consider < 3 unique internal links as "poor interlinking"
      const uniqueInternalPaths = [...new Set(internalLinks.map(l => new URL(l.href).pathname))];
      if (uniqueInternalPaths.length < 3) {
        results.noInternalLinks.push({ page: path, internalLinkCount: uniqueInternalPaths.length });
      }

      // 3. Check a sample of internal links for broken ones (first 5 unique per page)
      const sampled = [...new Set(internalLinks.map(l => l.href))].slice(0, 5);
      for (const link of sampled) {
        try {
          const linkStatus = await checkLink(link);
          if (linkStatus >= 400 || linkStatus === 0) {
            results.brokenLinks.push({ page: path, brokenUrl: link, status: linkStatus });
          }
        } catch(e) {}
      }

      // 4. Table opportunities
      const tableCount = hasTables(html);
      if (tableOpportunity(html, path)) {
        results.tableOpportunities.push({ page: path, existingTables: tableCount, reason: 'Содержит списки и ключевые слова, подходящие для таблиц' });
      }

      console.log(`OK (links:${uniqueInternalPaths.length}, meta:${meta.title ? '✓' : '✗'}/${meta.description ? '✓' : '✗'})`);

    } catch(e) {
      console.log(`ERROR: ${e.message}`);
      results.summary.errors++;
    }
  }

  // Output results as JSON
  const output = JSON.stringify(results, null, 2);
  process.stdout.write('\n\n=== RESULTS JSON ===\n');
  console.log(output);
}

run();
