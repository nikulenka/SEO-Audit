/* SEO Audit Pro — Frontend Logic */

let currentData = null;
let currentTab = 'broken';
let pollInterval = null;

async function startAudit(e) {
    e.preventDefault();
    const url = document.getElementById('urlInput').value.trim();
    const maxPages = document.getElementById('maxPages').value;
    if (!url) return;

    // UI state
    document.getElementById('submitBtn').disabled = true;
    document.querySelector('.btn-text').style.display = 'none';
    document.querySelector('.btn-loader').style.display = 'inline';
    document.getElementById('progressSection').style.display = 'block';
    document.getElementById('dashboard').style.display = 'none';
    document.getElementById('exportBtn').style.display = 'none';
    document.getElementById('exportJsonBtn').style.display = 'none';

    try {
        const resp = await fetch('/api/audit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, max_pages: parseInt(maxPages) })
        });
        const data = await resp.json();
        if (data.error) { alert(data.error); resetUI(); return; }
        pollProgress(data.job_id);
    } catch (err) {
        alert('Ошибка подключения к серверу: ' + err.message);
        resetUI();
    }
}

function pollProgress(jobId) {
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(async () => {
        try {
            const resp = await fetch(`/api/status/${jobId}`);
            const data = await resp.json();
            updateProgress(data.progress, data.message);

            if (data.status === 'done') {
                clearInterval(pollInterval);
                pollInterval = null;
                currentData = data;
                renderDashboard(data);
                resetUI();
            } else if (data.status === 'error') {
                clearInterval(pollInterval);
                pollInterval = null;
                alert('Ошибка аудита: ' + data.message);
                resetUI();
            }
        } catch (err) {
            // Network error, keep trying
        }
    }, 1500);
}

function updateProgress(pct, msg) {
    document.getElementById('progressBar').style.width = pct + '%';
    document.getElementById('progressPct').textContent = pct + '%';
    document.getElementById('progressMessage').textContent = msg;
}

function resetUI() {
    document.getElementById('submitBtn').disabled = false;
    document.querySelector('.btn-text').style.display = 'inline';
    document.querySelector('.btn-loader').style.display = 'none';
}

// ========== DASHBOARD RENDERING ==========

function renderDashboard(data) {
    const cr = data.crawl_result;
    const ai = data.ai_analysis || {};

    document.getElementById('progressSection').style.display = 'none';
    document.getElementById('dashboard').style.display = 'block';
    document.getElementById('exportBtn').style.display = 'flex';
    document.getElementById('exportJsonBtn').style.display = 'flex';

    // Stats
    document.getElementById('statPages').textContent = cr.stats.crawled;
    document.getElementById('statBroken').textContent = cr.broken_links.length;
    document.getElementById('statMeta').textContent = cr.meta_issues.length;
    document.getElementById('statTables').textContent = cr.table_opportunities.length;

    // Health gauge
    drawHealthGauge(cr.health_score);
    animateNumber('scoreNumber', cr.health_score);

    // Render active tab
    switchTab('broken');
}

function animateNumber(id, target) {
    const el = document.getElementById(id);
    let current = 0;
    const step = Math.max(1, Math.floor(target / 40));
    const timer = setInterval(() => {
        current += step;
        if (current >= target) { current = target; clearInterval(timer); }
        el.textContent = current;
    }, 30);
}

function drawHealthGauge(score) {
    const canvas = document.getElementById('healthGauge');
    const ctx = canvas.getContext('2d');
    const size = 180;
    const cx = size / 2, cy = size / 2, r = 70;

    canvas.width = size;
    canvas.height = size;
    ctx.clearRect(0, 0, size, size);

    // Background arc
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0.75 * Math.PI, 2.25 * Math.PI);
    ctx.strokeStyle = 'rgba(255,255,255,0.06)';
    ctx.lineWidth = 12;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Colored arc
    const pct = score / 100;
    const endAngle = 0.75 * Math.PI + pct * 1.5 * Math.PI;
    let color;
    if (score >= 80) color = '#22c55e';
    else if (score >= 50) color = '#eab308';
    else color = '#ef4444';

    ctx.beginPath();
    ctx.arc(cx, cy, r, 0.75 * Math.PI, endAngle);
    ctx.strokeStyle = color;
    ctx.lineWidth = 12;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Glow
    ctx.shadowColor = color;
    ctx.shadowBlur = 20;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0.75 * Math.PI, endAngle);
    ctx.strokeStyle = color;
    ctx.lineWidth = 4;
    ctx.stroke();
    ctx.shadowBlur = 0;

    document.getElementById('scoreNumber').style.color = color;
}

function switchTab(tab) {
    currentTab = tab;
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    const tabs = document.querySelectorAll('.tab');
    const tabMap = ['broken', 'meta', 'tech_seo', 'linking', 'keywords', 'competitors', 'tables', 'ai'];
    tabMap.forEach((t, i) => { if (t === tab) tabs[i]?.classList.add('active'); });

    const container = document.getElementById('tabContent');
    if (!currentData) { container.innerHTML = '<div class="empty-state">Данных пока нет</div>'; return; }

    const cr = currentData.crawl_result;
    const ai = currentData.ai_analysis || {};

    switch (tab) {
        case 'broken': renderBrokenLinks(container, cr); break;
        case 'meta': renderMetaIssues(container, cr); break;
        case 'tech_seo': renderTechSEO(container, cr); break;
        case 'linking': renderLinking(container, cr); break;
        case 'keywords': renderKeywords(container, ai); break;
        case 'competitors': renderCompetitors(container, ai); break;
        case 'tables': renderTables(container, cr, ai); break;
        case 'ai': renderAIReadiness(container, cr, ai); break;
    }
}

function renderBrokenLinks(el, cr) {
    if (cr.broken_links.length === 0) {
        el.innerHTML = `<h2>🔗 Битые ссылки</h2>
            <div class="empty-state">
                <span style="font-size:3rem">✅</span>
                <p style="margin-top:1rem">Битых ссылок не обнаружено! Все проверенные ссылки работают.</p>
            </div>`;
        return;
    }
    let rows = cr.broken_links.map(b => `
        <tr>
            <td class="url">${esc(b.source)}</td>
            <td class="url">${esc(b.target)}</td>
            <td class="status-err">${b.status || 'timeout'}</td>
            <td>${b.status >= 400 ? '301 redirect' : 'Проверить'}</td>
        </tr>`).join('');
    el.innerHTML = `<h2>🔗 Битые ссылки <span class="badge badge-red">${cr.broken_links.length}</span></h2>
        <p style="color:var(--text-secondary);margin-bottom:1rem">Страницы с нерабочими ссылками. Рекомендуется настроить 301-редиректы.</p>
        <table class="data-table">
            <thead><tr><th>Откуда (страница)</th><th>Куда (битая ссылка)</th><th>Статус</th><th>Рекомендация</th></tr></thead>
            <tbody>${rows}</tbody>
        </table>`;
}

function renderMetaIssues(el, cr) {
    if (cr.meta_issues.length === 0) {
        el.innerHTML = `<h2>📝 Мета-теги</h2><div class="empty-state"><span style="font-size:3rem">✅</span><p>Все мета-теги корректны!</p></div>`;
        return;
    }
    // Group by severity
    const critical = cr.meta_issues.filter(m => m.issue.includes('Нет'));
    const warnings = cr.meta_issues.filter(m => !m.issue.includes('Нет'));
    let rows = cr.meta_issues.map(m => `
        <tr>
            <td class="url">${esc(m.page)}</td>
            <td class="issue">${esc(m.issue)}</td>
            <td>${esc(m.current || m.current_value || '—')}</td>
            <td>${m.issue.includes('Нет') ? '<span class="badge badge-red">Critical</span>' : '<span class="badge badge-yellow">Warning</span>'}</td>
        </tr>`).join('');
    el.innerHTML = `<h2>📝 Ошибки мета-тегов <span class="badge badge-yellow">${cr.meta_issues.length}</span></h2>
        <p style="color:var(--text-secondary);margin-bottom:1rem">Критические: <strong style="color:var(--red)">${critical.length}</strong> (отсутствуют теги) | Предупреждения: <strong style="color:var(--yellow)">${warnings.length}</strong> (длина)</p>
        <table class="data-table">
            <thead><tr><th>Страница</th><th>Проблема</th><th>Текущее значение</th><th>Уровень</th></tr></thead>
            <tbody>${rows}</tbody>
        </table>`;
}

function renderLinking(el, cr) {
    let html = '<h2>🔀 Анализ перелинковки</h2>';

    // Orphan pages
    html += `<h3 style="margin:1.5rem 0 0.5rem; color:var(--red)">📭 Страницы-сироты (< 3 внутренних ссылок)</h3>`;
    if (cr.orphan_pages.length === 0) {
        html += '<p style="color:var(--green);margin-bottom:1.5rem">✅ Все страницы имеют достаточную перелинковку.</p>';
    } else {
        let rows = cr.orphan_pages.map(p => `<tr><td class="url">${esc(p.page)}</td><td class="status-err">${p.links}</td></tr>`).join('');
        html += `<table class="data-table"><thead><tr><th>Страница</th><th>Внутренних ссылок</th></tr></thead><tbody>${rows}</tbody></table>`;
    }

    // Hub pages
    html += `<h3 style="margin:1.5rem 0 0.5rem; color:var(--blue)">🔗 Хаб-страницы (20+ внутренних ссылок)</h3>`;
    if (cr.hub_pages.length === 0) {
        html += '<p style="color:var(--text-muted)">Нет страниц с большим количеством внутренних ссылок.</p>';
    } else {
        // Sort by link count desc
        const sorted = [...cr.hub_pages].sort((a, b) => b.links - a.links);
        let rows = sorted.map(p => `<tr><td class="url">${esc(p.page)}</td><td><strong>${p.links}</strong></td></tr>`).join('');
        html += `<table class="data-table"><thead><tr><th>Страница</th><th>Внутренних ссылок</th></tr></thead><tbody>${rows}</tbody></table>`;
    }

    el.innerHTML = html;
}

function renderKeywords(el, ai) {
    if (!ai.keywords || ai.keywords.length === 0) {
        el.innerHTML = `<h2>🔑 Ключевые слова</h2><div class="empty-state">AI-анализ не вернул данных. Проверьте API-ключ.</div>`;
        return;
    }
    let cards = ai.keywords.map(k => `
        <div class="keyword-card">
            <div>
                <div class="kw">${esc(k.keyword)}</div>
                <div class="vol">Объём: ${esc(k.volume || '—')} | Сложность: ${esc(k.difficulty || '—')}</div>
            </div>
            <span class="badge ${k.difficulty === 'low' ? 'badge-green' : k.difficulty === 'high' ? 'badge-red' : 'badge-yellow'}">${esc(k.difficulty || '—')}</span>
        </div>`).join('');
    el.innerHTML = `<h2>🔑 Ключевые слова (AI-анализ) <span class="badge badge-green">${ai.keywords.length}</span></h2>
        <p style="color:var(--text-secondary);margin-bottom:1rem">Релевантные ключевые слова, определённые с помощью Gemini AI на основе контента сайта.</p>
        <div class="keyword-grid">${cards}</div>`;
}

function renderCompetitors(el, ai) {
    if (!ai.competitors || ai.competitors.length === 0) {
        el.innerHTML = `<h2>🏆 Конкуренты</h2><div class="empty-state">AI-анализ не вернул данных.</div>`;
        return;
    }
    let cards = ai.competitors.map(c => `
        <div class="competitor-card">
            <h3>${esc(c.name)}</h3>
            <div class="comp-url">${esc(c.url || '')}</div>
            <div class="comp-str">${esc(c.strength || '')}</div>
        </div>`).join('');
    el.innerHTML = `<h2>🏆 Конкуренты в нише <span class="badge badge-yellow">${ai.competitors.length}</span></h2>
        <p style="color:var(--text-secondary);margin-bottom:1rem">Потенциальные конкуренты, определённые AI на основе тематики и ключевых слов сайта.</p>
        ${cards}`;
}

function renderTables(el, cr, ai) {
    const tablRecs = ai.table_recommendations || [];
    let html = `<h2>📊 Страницы для таблиц (AI-оптимизация) <span class="badge badge-yellow">${cr.table_opportunities.length}</span></h2>
        <p style="color:var(--text-secondary);margin-bottom:1rem">AI-поисковики (ChatGPT, Google AI Overview, Perplexity) предпочитают структурированные данные. Эти страницы содержат списки, которые лучше оформить таблицами.</p>`;

    if (tablRecs.length > 0) {
        html += `<h3 style="margin:1rem 0 0.5rem; color:var(--accent)">🤖 Рекомендации Gemini AI</h3>`;
        let aiRows = tablRecs.map(t => `
            <tr>
                <td class="url">${esc(t.page)}</td>
                <td>${esc(t.table_type || '—')}</td>
                <td>${Array.isArray(t.columns) ? t.columns.map(esc).join(', ') : esc(t.columns || '—')}</td>
            </tr>`).join('');
        html += `<table class="data-table"><thead><tr><th>Страница</th><th>Тип таблицы</th><th>Рекомендуемые колонки</th></tr></thead><tbody>${aiRows}</tbody></table>`;
    }

    if (cr.table_opportunities.length > 0) {
        html += `<h3 style="margin:1.5rem 0 0.5rem; color:var(--yellow)">📋 Найдено краулером (эвристика)</h3>`;
        let rows = cr.table_opportunities.map(t => `
            <tr>
                <td class="url">${esc(t.page)}</td>
                <td>${t.list_count || '—'} списков</td>
                <td>${t.word_count || '—'} слов</td>
            </tr>`).join('');
        html += `<table class="data-table"><thead><tr><th>Страница</th><th>Списков на странице</th><th>Объём текста</th></tr></thead><tbody>${rows}</tbody></table>`;
    }

    el.innerHTML = html;
}

function renderTechSEO(el, cr) {
    let rows = Object.values(cr.pages).map(p => `
        <tr>
            <td class="url">${esc(p.url)}</td>
            <td>${p.ttfb ? p.ttfb.toFixed(2) + 's' : '—'}</td>
            <td class="${p.mixed_content_issues > 0 ? 'status-err' : 'status-ok'}">${p.mixed_content_issues > 0 ? p.mixed_content_issues + ' ош.' : 'OK'}</td>
            <td>${p.schema_org_types && p.schema_org_types.length > 0 ? esc(p.schema_org_types.join(', ')) : 'Нет'}</td>
            <td>${p.hreflangs && p.hreflangs.length > 0 ? esc(p.hreflangs.join(', ')) : 'Нет'}</td>
        </tr>`).join('');
    el.innerHTML = `<h2>🔐 Техническое SEO & Отклик Сервера</h2>
        <p style="color:var(--text-secondary);margin-bottom:1rem">Анализ Mixed Content (загрузка http по https), TTFB ответа и разметки Schema.org.</p>
        <table class="data-table">
            <thead><tr><th>Страница</th><th>TTFB (Отклик)</th><th>Mixed Content</th><th>Schema.org</th><th>Hreflang</th></tr></thead>
            <tbody>${rows}</tbody>
        </table>`;
}

function renderAIReadiness(el, cr, ai_analysis) {
    const ai = cr.ai_readiness || {};
    const robots = ai.robots_txt || {};
    const llms = ai.llms_txt || {};
    const eeat = ai_analysis.eeat_signals || {};
    const rag = ai_analysis.rag_readiness || {};

    const check = (val) => val ? '✅' : '❌';
    const checkClass = (val) => val ? 'status-ok' : 'status-err';

    el.innerHTML = `<h2>🤖 AI Readiness & E-E-A-T (Generative Engine Optimization)</h2>
        <p style="color:var(--text-secondary);margin-bottom:1.5rem">Анализ авторитетности, тематического охвата (RAG-экстракция) и доступности для AI-ботов.</p>

        <h3 style="margin:1rem 0;color:var(--accent)">1. Доступность для AI-Ботов (Crawler Logic)</h3>
        <div class="ai-check"><span class="icon">📄</span><span class="label">robots.txt</span><span class="value ${checkClass(robots.exists)}">${check(robots.exists)} ${robots.exists ? 'Найден' : 'Отсутствует'}</span></div>
        <div class="ai-check"><span class="icon">🤖</span><span class="label">GPTBot (ChatGPT) в robots.txt</span><span class="value ${checkClass(robots.has_gptbot)}">${check(robots.has_gptbot)}</span></div>
        <div class="ai-check"><span class="icon">🤖</span><span class="label">ClaudeBot в robots.txt</span><span class="value ${checkClass(robots.has_claudebot)}">${check(robots.has_claudebot)}</span></div>
        <div class="ai-check"><span class="icon">🤖</span><span class="label">PerplexityBot в robots.txt</span><span class="value ${checkClass(robots.has_perplexitybot)}">${check(robots.has_perplexitybot)}</span></div>
        <div class="ai-check"><span class="icon">🤖</span><span class="label">Google-Extended в robots.txt</span><span class="value ${checkClass(robots.has_google_extended)}">${check(robots.has_google_extended)}</span></div>
        <div class="ai-check"><span class="icon">🗺️</span><span class="label">Sitemap в robots.txt</span><span class="value ${checkClass(robots.has_sitemap)}">${check(robots.has_sitemap)}</span></div>
        <div class="ai-check"><span class="icon">📋</span><span class="label">llms.txt</span><span class="value ${checkClass(llms.exists)}">${check(llms.exists)} ${llms.exists ? \`(\${llms.size} bytes)\` : 'Отсутствует'}</span></div>

        <h3 style="margin:2rem 0 1rem;color:var(--blue)">2. E-E-A-T Сигналы (Опыт, Авторитетность, Надежность)</h3>
        <div class="ai-check"><span class="icon">⭐</span><span class="label">Оценка E-E-A-T (1-10)</span><span class="value status-ok" style="font-weight:bold">${eeat.score_1_to_10 || 0} / 10</span></div>
        <div class="ai-check"><span class="icon">✍️</span><span class="label">Авторство контента</span><span class="value ${checkClass(eeat.authors_found)}">${check(eeat.authors_found)}</span></div>
        <div class="ai-check"><span class="icon">🏅</span><span class="label">Маркеры репутации</span><span class="value" style="color:var(--text-secondary)">${(eeat.reputation_markers || []).join(', ') || 'Нет'}</span></div>

        <h3 style="margin:2rem 0 1rem;color:var(--green)">3. RAG Усвояемость (Topical Authority)</h3>
        <div class="ai-check"><span class="icon">🧠</span><span class="label">Сложность понимания LLM (1-10)</span><span class="value status-ok" style="font-weight:bold">${rag.topical_authority_score || 0} / 10</span></div>
        <div class="ai-check" style="flex-direction:column;align-items:flex-start">
            <span class="label" style="margin-bottom:0.5rem">🔑 Извлеченные сущности (Entities):</span>
            <span class="value" style="color:var(--text-muted)">${(rag.entities_extracted || []).join(', ') || 'Нет'}</span>
        </div>
        <div class="ai-check" style="flex-direction:column;align-items:flex-start">
            <span class="label" style="margin-bottom:0.5rem">💡 Рекомендации по RAG:</span>
            <ul style="color:var(--yellow);margin-left:1rem;line-height:1.5">
                ${(rag.suggestions || []).map(s => \`<li>\${esc(s)}</li>\`).join('') || '<li>Нет рекомендаций</li>'}
            </ul>
        </div>
    `;
}

// ========== PDF EXPORT ==========

function exportPDF() {
    if (!currentData) return;
    
    // Temporarily show all tabs for full export
    const container = document.getElementById('tabContent');
    const originalHTML = container.innerHTML;
    
    const allTabs = ['broken', 'meta', 'linking', 'keywords', 'competitors', 'tables', 'ai'];
    const cr = currentData.crawl_result;
    const ai = currentData.ai_analysis || {};

    const tempDiv = document.createElement('div');
    allTabs.forEach(tab => {
        const section = document.createElement('div');
        section.style.marginBottom = '2rem';
        section.style.pageBreakInside = 'avoid';
        switch (tab) {
            case 'broken': renderBrokenLinks(section, cr); break;
            case 'meta': renderMetaIssues(section, cr); break;
            case 'linking': renderLinking(section, cr); break;
            case 'keywords': renderKeywords(section, ai); break;
            case 'competitors': renderCompetitors(section, ai); break;
            case 'tables': renderTables(section, cr, ai); break;
            case 'ai': renderAIReadiness(section, cr); break;
        }
        tempDiv.appendChild(section);
    });
    container.innerHTML = tempDiv.innerHTML;
    
    // Hide tabs during export
    const tabsElement = document.querySelector('.tabs');
    tabsElement.style.display = 'none';

    // Allow DOM to update before triggering print dialog
    setTimeout(() => {
        // Native print dialog is robust and allows selectable text PDF export
        window.print();
        
        // Restore tab state after printing dialog closes
        container.innerHTML = originalHTML;
        tabsElement.style.display = 'flex';
        switchTab(currentTab);
    }, 500);
}

function exportJSON() {
    if (!currentData) return;
    const jsonStr = JSON.stringify(currentData, null, 2);
    const blob = new Blob([jsonStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    
    // Create a safe filename from the crawled url
    let filename = 'seo-audit.json';
    try {
        const crawlUrl = Object.keys(currentData.crawl_result.pages)[0];
        if (crawlUrl) {
            const tempUrl = new URL(crawlUrl);
            filename = `seo-audit-${tempUrl.hostname}.json`;
        }
    } catch(e) {}

    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// ========== UTILS ==========

function esc(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = String(str);
    return div.innerHTML;
}
