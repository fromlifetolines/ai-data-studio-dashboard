/* SEO Intelligence (Page 8) — appended module */

let _rankTrackerData = null;

function switchSeoTab(tab) {
  const panels = ['rank', 'keyword', 'audit', 'competitor'];
  panels.forEach(p => {
    const panel = document.getElementById('seo-panel-' + p);
    const btn   = document.getElementById('seo-tab-' + p);
    if (panel) panel.style.display = (p === tab) ? '' : 'none';
    if (btn)   btn.classList.toggle('active', p === tab);
  });
}

async function loadSeoRankTracker() {
  const btn = document.getElementById('btn-load-rank');
  const placeholder = document.getElementById('rank-tracker-placeholder');
  const loading     = document.getElementById('rank-tracker-loading');
  const tableWrap   = document.getElementById('rank-tracker-table');
  const summaryDiv  = document.getElementById('rank-tracker-summary');
  if (!btn) return;

  btn.disabled = true;
  placeholder.style.display = 'none';
  tableWrap.style.display   = 'none';
  summaryDiv.style.display  = 'none';
  loading.style.display     = 'block';

  try {
    const resp = await fetch(API_BASE + '/api/seo/rank-tracker', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || '排名追蹤失敗');
    }
    const result = await resp.json();
    const data = result.data;
    _rankTrackerData = data;

    document.getElementById('rank-total-kw').textContent    = data.summary.total_keywords.toLocaleString();
    document.getElementById('rank-avg-pos').textContent     = '#' + data.summary.avg_position;
    document.getElementById('rank-top3').textContent        = data.summary.top3_count;
    document.getElementById('rank-top10').textContent       = data.summary.top10_count;
    document.getElementById('rank-total-clicks').textContent = data.summary.total_clicks.toLocaleString();

    summaryDiv.style.display  = 'grid';
    renderRankTable(data.keywords);
    loading.style.display     = 'none';
    tableWrap.style.display   = '';
  } catch (err) {
    loading.style.display    = 'none';
    placeholder.style.display = '';
    placeholder.innerHTML = '<i class="ti ti-alert-circle" style="font-size:40px;display:block;margin-bottom:12px;color:var(--danger);opacity:0.6;"></i><div style="font-size:14px;color:var(--danger);">' + err.message + '</div><div style="font-size:11px;margin-top:6px;opacity:0.6;">請先到「串接資料源」完成 Google Search Console 設定</div>';
  } finally {
    btn.disabled = false;
  }
}

function renderRankTable(keywords) {
  const tbody = document.getElementById('rank-kw-tbody');
  if (!tbody) return;
  tbody.innerHTML = keywords.map(function(kw) {
    return '<tr style="border-bottom:1px solid var(--border);">' +
      '<td style="padding:9px 4px;font-size:12px;color:var(--text-primary);max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="' + kw.keyword + '">' + kw.keyword + '</td>' +
      '<td style="padding:9px 4px;text-align:center;"><span class="rank-badge ' + kw.position_class + '">' + kw.position_badge + '</span></td>' +
      '<td style="padding:9px 4px;text-align:right;font-size:12px;">' + kw.clicks.toLocaleString() + '</td>' +
      '<td style="padding:9px 4px;text-align:right;font-size:12px;color:var(--text-secondary);">' + kw.impressions.toLocaleString() + '</td>' +
      '<td style="padding:9px 4px;text-align:right;font-size:12px;color:var(--muted);">' + (kw.ctr * 100).toFixed(1) + '%</td>' +
      '</tr>';
  }).join('');
}

function filterRankKeywords() {
  if (!_rankTrackerData) return;
  const query     = (document.getElementById('rank-filter-input') ? document.getElementById('rank-filter-input').value : '').toLowerCase();
  const posFilter = document.getElementById('rank-filter-pos') ? document.getElementById('rank-filter-pos').value : 'all';
  const filtered  = _rankTrackerData.keywords.filter(function(kw) {
    return (!query || kw.keyword.toLowerCase().indexOf(query) >= 0) &&
           (posFilter === 'all' || kw.position_class === posFilter);
  });
  renderRankTable(filtered);
}

async function runKeywordResearch() {
  const input = document.getElementById('kw-research-input');
  const keyword = input ? input.value.trim() : '';
  if (!keyword) { alert('請輸入關鍵字'); return; }

  const btn         = document.getElementById('btn-kw-research');
  const loading     = document.getElementById('kw-research-loading');
  const resultDiv   = document.getElementById('kw-research-result');
  const placeholder = document.getElementById('kw-research-placeholder');

  btn.disabled = true;
  loading.style.display     = 'block';
  resultDiv.style.display   = 'none';
  placeholder.style.display = 'none';

  try {
    const resp = await fetch(API_BASE + '/api/seo/keyword-research', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ keyword: keyword })
    });
    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || '關鍵字研究失敗');
    }
    const res  = await resp.json();
    const data = res.data;

    document.getElementById('kw-tw-volume').textContent     = (data.monthly_searches_tw || 0).toLocaleString();
    document.getElementById('kw-global-volume').textContent = (data.monthly_searches_global || 0).toLocaleString();
    const diff = data.difficulty || 0;
    const diffEl = document.getElementById('kw-difficulty');
    diffEl.textContent = diff;
    diffEl.style.color = diff >= 70 ? '#ef4444' : diff >= 40 ? '#f59e0b' : '#10b981';
    document.getElementById('kw-cpc').textContent    = '$' + (data.cpc_usd || 0).toFixed(2);
    document.getElementById('kw-intent').textContent = data.intent_zh || data.intent || '未知';

    const tbody = document.getElementById('kw-related-tbody');
    tbody.innerHTML = (data.related_keywords || []).map(function(rk) {
      const d = rk.difficulty || 0;
      const barColor = d >= 70 ? '#ef4444' : d >= 40 ? '#f59e0b' : '#10b981';
      return '<tr style="border-bottom:1px solid var(--border);">' +
        '<td style="padding:7px 4px;font-size:11px;color:var(--text-primary);">' + rk.keyword + '</td>' +
        '<td style="padding:7px 4px;text-align:right;font-size:11px;color:var(--text-secondary);">' + (rk.monthly_searches || 0).toLocaleString() + '</td>' +
        '<td style="padding:7px 4px;text-align:right;min-width:80px;">' +
          '<div class="difficulty-bar-wrap"><div class="difficulty-bar"><div class="difficulty-bar-fill" style="width:' + d + '%;background:' + barColor + ';"></div></div><span style="color:' + barColor + ';">' + d + '</span></div>' +
        '</td></tr>';
    }).join('');

    const compList = document.getElementById('kw-competitors-list');
    compList.innerHTML = (data.top_competitors || []).map(function(c, i) {
      return '<div style="padding:8px 12px;border:1px solid var(--border);border-radius:8px;margin-bottom:8px;display:flex;align-items:center;gap:8px;background:var(--bg);">' +
        '<div style="width:20px;height:20px;background:var(--accent);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:10px;color:white;font-weight:700;flex-shrink:0;">' + (i + 1) + '</div>' +
        '<div><div style="font-size:11px;font-weight:600;color:var(--text-primary);">' + c.domain + '</div><div style="font-size:10px;color:var(--text-secondary);">' + (c.title || '') + '</div></div>' +
        '</div>';
    }).join('');

    loading.style.display   = 'none';
    resultDiv.style.display = '';
  } catch (err) {
    loading.style.display     = 'none';
    placeholder.style.display = '';
    placeholder.innerHTML = '<i class="ti ti-alert-circle" style="font-size:40px;display:block;margin-bottom:12px;color:var(--danger);opacity:0.6;"></i><div style="font-size:14px;color:var(--danger);">' + err.message + '</div>';
  } finally {
    btn.disabled = false;
  }
}

async function runSiteAudit() {
  const input = document.getElementById('audit-url-input');
  const url   = input ? input.value.trim() : '';
  if (!url) { alert('請輸入網站網址'); return; }

  const btn         = document.getElementById('btn-audit');
  const loading     = document.getElementById('audit-loading');
  const resultDiv   = document.getElementById('audit-result');
  const placeholder = document.getElementById('audit-placeholder');

  btn.disabled = true;
  loading.style.display     = 'block';
  resultDiv.style.display   = 'none';
  placeholder.style.display = 'none';

  try {
    const resp = await fetch(API_BASE + '/api/seo/site-audit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: url })
    });
    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || '健檢失敗');
    }
    const res  = await resp.json();
    const ps   = res.pagespeed || {};
    const tSeo = res.technical_seo || {};

    function renderScores(containerId, scores, label) {
      const el = document.getElementById(containerId);
      if (!el || !scores) return;
      const items = [
        { key: 'performance',    label: '效能' },
        { key: 'seo',            label: 'SEO' },
        { key: 'accessibility',  label: '無障礙' },
        { key: 'best_practices', label: '最佳實踐' }
      ];
      el.innerHTML = '<div style="font-size:11px;font-weight:600;color:var(--text-secondary);margin-bottom:10px;text-align:center;">' + label + '</div>' +
        '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px;">' +
        items.map(function(item) {
          const score = scores[item.key] != null ? scores[item.key] : 0;
          const cls   = score >= 90 ? 'good' : score >= 50 ? 'average' : 'poor';
          return '<div class="ps-score-ring"><div class="ps-score-circle ' + cls + '">' + score + '</div><div class="ps-score-label">' + item.label + '</div></div>';
        }).join('') + '</div>';
    }

    renderScores('audit-mobile-scores',  (ps.mobile  || {}).scores, 'Mobile');
    renderScores('audit-desktop-scores', (ps.desktop || {}).scores, 'Desktop');

    const cwv     = (ps.mobile || {}).cwv || {};
    const cwvGrid = document.getElementById('audit-cwv-grid');
    const cwvItems = [
      { key: 'lcp',         label: 'LCP',         desc: '最大內容繪製' },
      { key: 'tbt',         label: 'TBT',         desc: '總阻塞時間' },
      { key: 'cls',         label: 'CLS',         desc: '累積版面偏移' },
      { key: 'fcp',         label: 'FCP',         desc: '首次內容繪製' },
      { key: 'ttfb',        label: 'TTFB',        desc: '伺服器回應' },
      { key: 'speed_index', label: 'Speed Index', desc: '速度指數' }
    ];
    const gradeTextMap = { good: '良好', 'needs-improvement': '需改進', poor: '不良', unknown: '—' };
    cwvGrid.innerHTML = cwvItems.map(function(item) {
      const d = cwv[item.key] || {};
      const grade = d.grade || 'unknown';
      const gradeText = gradeTextMap[grade] || '—';
      const color = grade === 'good' ? '#10b981' : grade === 'needs-improvement' ? '#f59e0b' : grade === 'poor' ? '#ef4444' : 'var(--text-secondary)';
      return '<div class="cwv-card"><div class="cwv-label">' + item.label + '<br><span style="opacity:0.6;">' + item.desc + '</span></div>' +
        '<div class="cwv-value" style="color:' + color + ';">' + (d.value || '—') + '</div>' +
        '<span class="cwv-badge ' + grade + '">' + gradeText + '</span></div>';
    }).join('');

    const techSeoEl = document.getElementById('audit-tech-seo');
    if (tSeo && tSeo.success && tSeo.scores) {
      var seoScore = tSeo.scores.seo || 0;
      var geoScore = tSeo.scores.geo || 0;
      var aeoScore = tSeo.scores.aeo || 0;
      var seoItems = tSeo.seo_report || [];

      function scoreColor(s) { return s >= 80 ? '#10b981' : s >= 60 ? '#f59e0b' : '#ef4444'; }
      function scoreLabel(s) { return s >= 80 ? '優良' : s >= 60 ? '待改進' : '需立即處理'; }

      techSeoEl.innerHTML =
        // 三維評分橫排
        '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:16px;">' +
          '<div style="text-align:center;padding:14px;background:var(--bg);border-radius:8px;border:1px solid var(--border);">' +
            '<div style="font-size:28px;font-weight:700;color:' + scoreColor(seoScore) + ';">' + seoScore + '</div>' +
            '<div style="font-size:10px;color:var(--text-secondary);">傳統 SEO</div>' +
            '<div style="font-size:10px;color:' + scoreColor(seoScore) + ';">' + scoreLabel(seoScore) + '</div>' +
          '</div>' +
          '<div style="text-align:center;padding:14px;background:var(--bg);border-radius:8px;border:1px solid var(--border);">' +
            '<div style="font-size:28px;font-weight:700;color:' + scoreColor(geoScore) + ';">' + geoScore + '</div>' +
            '<div style="font-size:10px;color:var(--text-secondary);">AI 搜尋 GEO</div>' +
            '<div style="font-size:10px;color:' + scoreColor(geoScore) + ';">' + scoreLabel(geoScore) + '</div>' +
          '</div>' +
          '<div style="text-align:center;padding:14px;background:var(--bg);border-radius:8px;border:1px solid var(--border);">' +
            '<div style="font-size:28px;font-weight:700;color:' + scoreColor(aeoScore) + ';">' + aeoScore + '</div>' +
            '<div style="font-size:10px;color:var(--text-secondary);">回答引擎 AEO</div>' +
            '<div style="font-size:10px;color:' + scoreColor(aeoScore) + ';">' + scoreLabel(aeoScore) + '</div>' +
          '</div>' +
        '</div>' +
        // SEO 子項目清單
        '<div style="display:flex;flex-direction:column;gap:6px;">' +
        seoItems.map(function(item) {
          var score = item.score || 0;
          var maxScore = item.max || 20;
          var pct = Math.round((score / maxScore) * 100);
          var ic = pct >= 80 ? '✅' : pct >= 50 ? '⚠️' : '❌';
          var bc = pct >= 80 ? '#10b981' : pct >= 50 ? '#f59e0b' : '#ef4444';
          return '<div style="padding:10px 12px;border:1px solid var(--border);border-radius:6px;display:flex;align-items:center;gap:10px;">' +
            '<span style="font-size:14px;">' + ic + '</span>' +
            '<div style="flex:1;">' +
              '<div style="font-size:11px;font-weight:600;color:var(--text-primary);">' + (item.label || '') + '</div>' +
              '<div style="font-size:10px;color:var(--text-secondary);margin-top:2px;">' + (item.desc || '') + '</div>' +
            '</div>' +
            '<div style="text-align:right;flex-shrink:0;">' +
              '<span style="font-size:12px;font-weight:700;color:' + bc + ';">' + score + '/' + maxScore + '</span>' +
            '</div>' +
          '</div>';
        }).join('') + '</div>' +
        // AI 建議（如果有）
        (tSeo.ai_advice ? '<div style="margin-top:14px;padding:14px;background:rgba(124,58,237,0.04);border:1px solid rgba(124,58,237,0.1);border-radius:8px;font-size:11px;color:var(--text-primary);line-height:1.7;">' +
          '<div style="font-weight:600;font-size:12px;margin-bottom:8px;color:var(--accent);">✨ AI 優化建議</div>' + tSeo.ai_advice.replace(/\n/g, '<br>') + '</div>' : '');
    } else if (tSeo && tSeo.error) {
      techSeoEl.innerHTML = '<div style="font-size:12px;color:var(--danger);padding:12px;">技術 SEO 評測失敗：' + tSeo.error + '</div>';
    } else {
      techSeoEl.innerHTML = '<div style="font-size:12px;color:var(--text-secondary);padding:12px;">技術 SEO 數據未取得。</div>';
    }


    loading.style.display   = 'none';
    resultDiv.style.display = '';
  } catch (err) {
    loading.style.display     = 'none';
    placeholder.style.display = '';
    placeholder.innerHTML = '<i class="ti ti-alert-circle" style="font-size:40px;display:block;margin-bottom:12px;color:var(--danger);opacity:0.6;"></i><div style="font-size:14px;color:var(--danger);">' + err.message + '</div>';
  } finally {
    btn.disabled = false;
  }
}

async function runCompetitorSEO() {
  const myInput   = document.getElementById('comp-my-domain');
  const compInput = document.getElementById('comp-competitor-domain');
  const myDomain   = myInput   ? myInput.value.trim()   : '';
  const compDomain = compInput ? compInput.value.trim() : '';
  if (!myDomain || !compDomain) { alert('請填入我方網域與競品網域'); return; }

  const btn         = document.getElementById('btn-comp-seo');
  const loading     = document.getElementById('comp-seo-loading');
  const resultDiv   = document.getElementById('comp-seo-result');
  const placeholder = document.getElementById('comp-seo-placeholder');

  btn.disabled = true;
  loading.style.display     = 'block';
  resultDiv.style.display   = 'none';
  placeholder.style.display = 'none';

  try {
    const resp = await fetch(API_BASE + '/api/seo/competitor-analysis', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ my_domain: myDomain, competitor_domain: compDomain })
    });
    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || '競品分析失敗');
    }
    const res  = await resp.json();
    const data = res.data;

    function renderSideCard(elId, info, isComp) {
      const el = document.getElementById(elId);
      if (!el) return;
      const color = isComp ? '#ef4444' : 'var(--accent)';
      el.innerHTML =
        '<div style="font-size:12px;font-weight:600;margin-bottom:12px;color:' + color + ';">' + (info.domain || '—') + '</div>' +
        '<div class="comp-stat">' + (info.monthly_organic_traffic || 0).toLocaleString() + '</div><div class="comp-stat-label">月自然流量</div>' +
        '<div class="comp-stat">' + (info.keyword_count || 0).toLocaleString() + '</div><div class="comp-stat-label">關鍵字覆蓋數</div>' +
        '<div class="comp-stat">' + (info.domain_strength || 0) + '</div><div class="comp-stat-label">域名強度</div>';
    }

    renderSideCard('comp-my-card',    data.my_domain   || {}, false);
    renderSideCard('comp-their-card', data.competitor  || {}, true);

    const topKws = (data.competitor || {}).top_keywords || [];
    document.getElementById('comp-top-kws-tbody').innerHTML = topKws.map(function(kw) {
      var cls = kw.position <= 3 ? 'top3' : kw.position <= 10 ? 'top10' : 'top30';
      return '<tr style="border-bottom:1px solid var(--border);">' +
        '<td style="padding:7px 4px;font-size:11px;">' + kw.keyword + '</td>' +
        '<td style="padding:7px 4px;text-align:center;"><span class="rank-badge ' + cls + '">#' + kw.position + '</span></td>' +
        '<td style="padding:7px 4px;text-align:right;font-size:11px;color:var(--text-secondary);">' + (kw.monthly_searches || 0).toLocaleString() + '</td>' +
        '</tr>';
    }).join('');

    const gaps = (data.gap_analysis || {}).keyword_gaps || [];
    document.getElementById('comp-keyword-gaps').innerHTML = gaps.map(function(g) {
      return '<div class="kw-gap-card">' +
        '<div style="font-size:12px;font-weight:600;color:var(--text-primary);margin-bottom:4px;">' + g.keyword + '</div>' +
        '<div style="display:flex;gap:12px;font-size:10px;color:var(--text-secondary);">' +
          '<span>搜尋量：<strong>' + (g.monthly_searches || 0).toLocaleString() + '</strong></span>' +
          '<span>難度：<strong>' + g.difficulty + '</strong></span>' +
          '<span style="color:#10b981;">機會分：<strong>' + g.opportunity_score + '</strong></span>' +
        '</div></div>';
    }).join('');

    const gap = data.gap_analysis || {};
    document.getElementById('comp-gap-analysis').innerHTML =
      '<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">' +
      '<div><div style="font-size:11px;font-weight:600;color:var(--danger);margin-bottom:8px;">竞品優勢</div>' +
        (gap.competitor_advantages || []).map(function(a) { return '<div style="font-size:11px;color:var(--text-secondary);padding:4px 0;border-bottom:1px solid var(--border);">- ' + a + '</div>'; }).join('') +
      '</div>' +
      '<div><div style="font-size:11px;font-weight:600;color:#10b981;margin-bottom:8px;">你的機會點</div>' +
        (gap.my_opportunities || []).map(function(o) { return '<div style="font-size:11px;color:var(--text-secondary);padding:4px 0;border-bottom:1px solid var(--border);">- ' + o + '</div>'; }).join('') +
      '</div></div>';

    loading.style.display   = 'none';
    resultDiv.style.display = '';
  } catch (err) {
    loading.style.display     = 'none';
    placeholder.style.display = '';
    placeholder.innerHTML = '<i class="ti ti-alert-circle" style="font-size:40px;display:block;margin-bottom:12px;color:var(--danger);opacity:0.6;"></i><div style="font-size:14px;color:var(--danger);">' + err.message + '</div>';
  } finally {
    btn.disabled = false;
  }
}
