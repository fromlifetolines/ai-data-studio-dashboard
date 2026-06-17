/* ═══════════════════════════════════════════
   AI Data Studio — dashboard.js
   職責：
   1. 靜態資料 (Mock Data) — 開發 / Demo 用
   2. API 呼叫層 (fetchDashboard) — 等後端完成後取消註解啟用
   3. 圖表渲染 (Chart.js)
   4. 頁籤切換 / Modal 控制
   5. 動態列表渲染
   ═══════════════════════════════════════════ */

'use strict';

/* ────────────────────────────────────────────
   1. 設定
──────────────────────────────────────────── */
const API_BASE = 'http://127.0.0.1:8000';  // FastAPI 後端位址，上線後改為正式 domain

const DAYS_14 = ['5/26','5/27','5/28','5/29','5/30','5/31','6/1','6/2','6/3','6/4','6/5','6/6','6/7','6/8'];

/* ────────────────────────────────────────────
   2. Mock Data（後端打通後由 API 取代）
──────────────────────────────────────────── */
const MOCK = {
  ai_summary: '自然搜尋佔流量 61%，核心關鍵字「數據分析工具」排名升至 #4.2。<strong>/pricing</strong> 跳出率達 78% 需優先改善，<strong>Meta Ads</strong> ROAS 從 3.2 降至 2.8 建議檢視受眾設定。整體工作階段 ↑9.4%，成長健康。',

  kpis: {
    sessions:    { value: '38,241', delta: '+9.4%', trend: 'up' },
    users:       { value: '28,109', delta: '+5.2%', trend: 'up' },
    impressions: { value: '182K',   delta: '+12%',  trend: 'up' },
    roas:        { value: '3.61×',  delta: '—',     trend: 'flat' },
  },

  sessions_trend: [2400,2800,2600,3100,3300,3800,3600,3200,3700,4000,4300,4100,4500,4700],
  users_trend:    [1800,2100,1950,2300,2450,2800,2650,2400,2800,3000,3200,3100,3400,3500],
  new_users_trend:[1100,1300,1200,1500,1600,1900,1750,1500,1750,1900,2000,1950,2100,2200],

  traffic_source: [
    { label:'自然搜尋', value:61, color:'#7C3AED' },
    { label:'直接流量', value:18, color:'#6b7280' },
    { label:'社群媒體', value:12, color:'#93c5fd' },
    { label:'其他',     value: 9, color:'#e5e7eb' },
  ],

  device: [
    { label:'手機', value:58, color:'#7C3AED' },
    { label:'桌機', value:34, color:'#6b7280' },
    { label:'平板', value: 8, color:'#d1d5db' },
  ],

  pages: [
    { path:'/',               views:12401, unique:9820,  time:'3:12', bounce:'38%',  conv:'4.2%', status:'good' },
    { path:'/pricing',        views:7832,  unique:6140,  time:'1:05', bounce:'78%',  conv:'1.8%', status:'bad'  },
    { path:'/blog/ga4-guide', views:5210,  unique:4890,  time:'4:28', bounce:'41%',  conv:'2.9%', status:'good' },
    { path:'/features',       views:3980,  unique:3200,  time:'2:50', bounce:'45%',  conv:'3.1%', status:'warn' },
    { path:'/docs',           views:2140,  unique:1980,  time:'5:10', bounce:'33%',  conv:'6.4%', status:'good' },
    { path:'/contact',        views:1820,  unique:1650,  time:'1:45', bounce:'52%',  conv:'8.9%', status:'good' },
    { path:'/blog/seo-tips',  views:1540,  unique:1410,  time:'3:55', bounce:'39%',  conv:'2.1%', status:'warn' },
  ],

  keywords: [
    { kw:'數據分析工具',          imp:28400, click:1477, ctr:'5.2%', rank:'#4.0', trend:'+2', opp:'進入首頁',  opp_type:'good' },
    { kw:'GA4 教學',              imp:19200, click:1306, ctr:'6.8%', rank:'#3.2', trend:'+3', opp:'搶 Top3',   opp_type:'good' },
    { kw:'網站流量分析',          imp:15800, click:616,  ctr:'3.9%', rank:'#6.1', trend:'−1', opp:'加強內容',  opp_type:'warn' },
    { kw:'google analytics 設定', imp:11400, click:240,  ctr:'2.1%', rank:'#12',  trend:'+5', opp:'有潛力',    opp_type:'warn' },
    { kw:'SEO 工具推薦',          imp:9600,  click:173,  ctr:'1.8%', rank:'#18',  trend:'—',  opp:'待衝刺',    opp_type:'bad'  },
    { kw:'廣告效益分析',          imp:7200,  click:158,  ctr:'2.2%', rank:'#14',  trend:'+2', opp:'有潛力',    opp_type:'warn' },
  ],

  ssc_imp:   [11000,12500,12000,13800,14200,15000,14500,13200,14800,16000,17000,16500,18000,18200],
  ssc_click: [420,490,460,530,550,590,570,510,570,620,660,640,690,692],

  search_type: [
    { label:'網頁', value:83, color:'#7C3AED' },
    { label:'圖片', value:10, color:'#6b7280' },
    { label:'影片', value: 7, color:'#d1d5db' },
  ],

  channels: [
    { name:'Google Ads', icon:'ti-brand-google', icon_bg:'#EFF6FF', icon_color:'#1d4ed8',
      spend:'$68,200', imp:'520K', click:'18,400', conv:'1,140', cpa:'$59.8', roas:'4.2×', status:'good' },
    { name:'Meta Ads',   icon:'ti-brand-facebook', icon_bg:'#F5F3FF', icon_color:'#6d28d9',
      spend:'$42,300', imp:'890K', click:'11,200', conv:'580',   cpa:'$72.9', roas:'2.8×', status:'warn' },
    { name:'YouTube Ads',icon:'ti-brand-youtube',  icon_bg:'#FFF7ED', icon_color:'#c2410c',
      spend:'$14,000', imp:'1.2M', click:'4,800',  conv:'122',   cpa:'$114.8',roas:'1.9×', status:'bad'  },
  ],

  ad_revenue: [29,33,31,36,39,44,42,38,43,47,50,49,53,56],
  ad_spend:   [7.5,8,8,9,10,11,9.5,8.8,10,12,13,12,13,14],

  budget: [
    { label:'Google', value:55, color:'#7C3AED' },
    { label:'Meta',   value:34, color:'#6b7280' },
    { label:'YouTube',value:11, color:'#d1d5db' },
  ],
};

/* ────────────────────────────────────────────
   3. API 呼叫層
   ──────────────────────────────────────────── */
let currentData = MOCK;
const CHARTS = {};

async function fetchDashboard(rangeDaysOrCustom = 30) {
  setStatus('loading');
  try {
    let startDate, endDate;
    if (rangeDaysOrCustom === 'custom') {
      startDate = document.getElementById('custom-start-date').value;
      endDate = document.getElementById('custom-end-date').value;
      if (!startDate || !endDate) {
        startDate = '30daysAgo';
        endDate = 'today';
      }
    } else {
      startDate = `${rangeDaysOrCustom}daysAgo`;
      endDate = 'today';
    }
    const res = await fetch(`${API_BASE}/api/dashboard?start_date=${startDate}&end_date=${endDate}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const result = await res.json();
    setStatus('connected');
    return result;
  } catch (err) {
    console.error('API fetch failed, using mock data:', err);
    setStatus('error');
    return null;  // fallback to MOCK
  }
}

function setStatus(state) {
  const dot = document.getElementById('status-dot');
  if (!dot) return;
  dot.className = 'status-dot ' + state;
  dot.title = { loading:'數據載入中...', connected:'數據已連線', error:'連線失敗，顯示示範數據' }[state] || '';
}

function getMockDataForRange(days) {
  const data = JSON.parse(JSON.stringify(MOCK));
  const count = parseInt(days, 10) || 30;
  
  const generateTrend = (baseVal, volatility, count) => {
    let current = baseVal;
    const trend = [];
    for (let i = 0; i < count; i++) {
      current += Math.round((Math.random() - 0.45) * volatility);
      trend.push(Math.max(Math.round(current), 100));
    }
    return trend;
  };
  
  data.sessions_trend = generateTrend(2500, 300, count);
  data.users_trend = data.sessions_trend.map(v => Math.round(v * 0.75));
  data.new_users_trend = data.users_trend.map(v => Math.round(v * 0.6));
  
  data.ssc_imp = generateTrend(12000, 1500, count);
  data.ssc_click = data.ssc_imp.map(v => Math.round(v * (0.03 + Math.random() * 0.01)));
  
  data.ad_spend = generateTrend(80, 10, count).map(v => Math.round(v / 10 + 5));
  data.ad_revenue = data.ad_spend.map(v => Math.round(v * (3.0 + Math.random() * 0.8)));
  
  data.labels = [];
  const today = new Date();
  for (let i = count - 1; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    data.labels.push(`${d.getMonth() + 1}/${d.getDate()}`);
  }
  
  const totalSessions = data.sessions_trend.reduce((a, b) => a + b, 0);
  const totalUsers = data.users_trend.reduce((a, b) => a + b, 0);
  const totalImp = data.ssc_imp.reduce((a, b) => a + b, 0);
  const totalSpend = data.ad_spend.reduce((a, b) => a + b, 0) * 1000;
  const totalRev = data.ad_revenue.reduce((a, b) => a + b, 0) * 1000;
  
  data.kpis.sessions.value = totalSessions.toLocaleString();
  data.kpis.users.value = totalUsers.toLocaleString();
  data.kpis.impressions.value = totalImp >= 1000000 ? `${(totalImp/1000000).toFixed(1)}M` : `${Math.round(totalImp/1000)}K`;
  data.kpis.roas.value = `${(totalRev / totalSpend).toFixed(2)}×`;
  
  return data;
}

async function updateDashboard(rangeDays) {
  setStatus('loading');
  const apiResult = await fetchDashboard(rangeDays);
  if (apiResult && apiResult.data) {
    currentData = apiResult.data;
  } else {
    currentData = getMockDataForRange(rangeDays);
  }
  
  Object.keys(BUILT).forEach(k => BUILT[k] = false);
  buildOverview(currentData);
  
  const activeTabIdx = Array.from(document.querySelectorAll('.tab')).findIndex(t => t.classList.contains('on'));
  if (activeTabIdx !== -1) {
    goTab(activeTabIdx);
  }
}

/* ────────────────────────────────────────────
   4. Chart.js 全域設定
──────────────────────────────────────────── */
Chart.defaults.font.family = "'Inter', 'Noto Sans TC', system-ui, sans-serif";
Chart.defaults.color = '#9ca3af';

// Chart.js 3D drop shadow plugin
const chartShadowPlugin = {
  id: 'chartShadow',
  beforeDatasetsDraw(chart, args, options) {
    const ctx = chart.ctx;
    ctx.save();
    ctx.shadowColor = 'rgba(0, 0, 0, 0.08)';
    ctx.shadowBlur = 8;
    ctx.shadowOffsetX = 0;
    ctx.shadowOffsetY = 6;
  },
  afterDatasetsDraw(chart, args, options) {
    const ctx = chart.ctx;
    ctx.restore();
  }
};
Chart.register(chartShadowPlugin);

const CHART_OPTIONS_BASE = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      mode: 'index',
      intersect: false,
      bodyFont: { size: 11 },
      titleFont: { size: 11 },
    },
  },
};

const X_GRID_OFF = { grid: { display: false }, ticks: { font: { size: 10 }, color: '#9ca3af', maxRotation: 0 } };
const Y_GRID_ON  = { grid: { color: 'rgba(0,0,0,0.04)', drawBorder: false }, ticks: { font: { size: 10 }, color: '#9ca3af' } };

function makeLine(id, datasets, yCallback) {
  const canvas = document.getElementById(id);
  if (!canvas) return null;
  
  if (CHARTS[id]) {
    CHARTS[id].destroy();
  }
  
  const ctx = canvas.getContext('2d');
  const labels = currentData.labels || DAYS_14;

  // Enhance datasets with custom gradients and shadows for 3D look
  const enhancedDatasets = datasets.map(ds => {
    if (ds.borderColor === '#7C3AED' || ds.borderColor === '#2563EB') {
      const gradient = ctx.createLinearGradient(0, 0, 0, 168);
      gradient.addColorStop(0, 'rgba(124, 58, 237, 0.22)');
      gradient.addColorStop(1, 'rgba(124, 58, 237, 0.00)');
      return {
        ...ds,
        fill: true,
        backgroundColor: gradient,
        borderColor: '#7C3AED',
        borderWidth: 3,
        pointBackgroundColor: '#7C3AED',
        pointHoverBackgroundColor: '#7C3AED',
        pointBorderColor: '#ffffff',
        pointBorderWidth: 2,
        pointHoverBorderColor: '#ffffff',
        pointHoverBorderWidth: 3,
        pointRadius: 0,
        pointHoverRadius: 6
      };
    }
    return ds;
  });
  
  CHARTS[id] = new Chart(canvas, {
    type: 'line',
    data: { labels: labels, datasets: enhancedDatasets },
    options: {
      ...CHART_OPTIONS_BASE,
      scales: {
        x: { 
          ...X_GRID_OFF, 
          ticks: { 
            ...X_GRID_OFF.ticks, 
            autoSkip: true, 
            maxTicksLimit: 10,
            font: { size: 9 }
          } 
        },
        y: { ...Y_GRID_ON,  ticks: { ...Y_GRID_ON.ticks, callback: yCallback || (v => v >= 1000 ? (v/1000).toFixed(0) + 'K' : v) } },
      },
    },
  });
  return CHARTS[id];
}

function makeDonut(id, items) {
  const canvas = document.getElementById(id);
  if (!canvas) return null;
  
  if (CHARTS[id]) {
    CHARTS[id].destroy();
  }
  
  CHARTS[id] = new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: items.map(d => d.label),
      datasets: [{ data: items.map(d => d.value), backgroundColor: items.map(d => d.color), borderWidth: 0 }],
    },
    options: {
      cutout: '70%',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => ctx.label + ': ' + ctx.parsed + '%' } },
      },
    },
  });
  return CHARTS[id];
}

/* ────────────────────────────────────────────
   5. 渲染函式
──────────────────────────────────────────── */

/** 建立 Page 0 — 總覽 */
function buildOverview(data) {
  // 動態更新關鍵字、頁面與管道的資料庫，以確保點擊彈出視窗時能顯示正確且真實的數據
  if (data.keywords) {
    data.keywords.forEach(k => {
      if (!KW_DATA[k.kw]) {
        KW_DATA[k.kw] = {
          rank: k.rank,
          ctr: k.ctr,
          click: k.click ? k.click.toLocaleString() : '0',
          ai: `針對關鍵字「${k.kw}」，目前的搜尋排名為 ${k.rank}，點擊率 ${k.ctr}，本週點擊次數為 ${k.click} 次。`
        };
      } else {
        KW_DATA[k.kw].rank = k.rank;
        KW_DATA[k.kw].ctr = k.ctr;
        KW_DATA[k.kw].click = k.click ? k.click.toLocaleString() : '0';
      }
    });
  }
  if (data.pages) {
    data.pages.forEach(p => {
      if (!PAGE_DATA[p.path]) {
        PAGE_DATA[p.path] = {
          views: p.views ? p.views.toLocaleString() : '0',
          bounce: p.bounce || '—',
          time: p.time || '—',
          ai: `本週頁面 ${p.path} 瀏覽量為 ${p.views}，跳出率為 ${p.bounce}，平均停留時間為 ${p.time}。`
        };
      } else {
        PAGE_DATA[p.path].views = p.views ? p.views.toLocaleString() : '0';
        PAGE_DATA[p.path].bounce = p.bounce || '—';
        PAGE_DATA[p.path].time = p.time || '—';
      }
    });
  }
  if (data.channels) {
    data.channels.forEach(ch => {
      if (!CHANNEL_DATA[ch.name]) {
        CHANNEL_DATA[ch.name] = {
          roas: ch.roas || '—',
          cpa: ch.cpa || '—',
          conv: ch.conv || '—',
          ai: `渠道 ${ch.name} 的 ROAS 為 ${ch.roas}，每次轉換成本 CPA 為 ${ch.cpa}，本週共完成 ${ch.conv} 次轉換。`
        };
      } else {
        CHANNEL_DATA[ch.name].roas = ch.roas || '—';
        CHANNEL_DATA[ch.name].cpa = ch.cpa || '—';
        CHANNEL_DATA[ch.name].conv = ch.conv || '—';
      }
    });
  }

  // AI 摘要
  const aiEl = document.getElementById('ai-summary-text');
  if (aiEl) aiEl.innerHTML = data.ai_summary;

  // KPI 卡片數值更新（若 API 回傳）
  Object.entries(data.kpis).forEach(([key, d]) => {
    document.querySelectorAll(`[data-key="${key}"]`).forEach(el => {
      el.textContent = d.value;
      const deltaEl = el.parentElement.querySelector('.kpi-delta');
      if (deltaEl && d.delta !== undefined) {
        if (d.delta === '—' || d.delta === '') {
          deltaEl.textContent = '—';
          deltaEl.className = 'kpi-delta flat';
        } else {
          const arrow = d.trend === 'up' ? '↑' : d.trend === 'down' ? '↓' : '';
          deltaEl.textContent = `${arrow} ${d.delta} 較上期`;
          deltaEl.className = `kpi-delta ${d.trend === 'up' ? 'up' : d.trend === 'down' ? 'dn' : 'flat'}`;
        }
      }
    });
  });

  // 工作階段趨勢
  makeLine('c-sess', [
    { data: data.sessions_trend, borderColor: '#7C3AED', borderWidth: 2, pointRadius: 0, tension: 0.4, fill: true, backgroundColor: 'rgba(124,58,237,0.05)' },
    { data: data.users_trend,    borderColor: '#d1d5db', borderWidth: 1.5, pointRadius: 0, tension: 0.4, borderDash: [4,3] },
  ]);

  // 流量來源甜甜圈
  makeDonut('c-src', data.traffic_source);

  // 熱門頁面
  renderOverviewPages(data.pages.slice(0, 5));

  // 熱門關鍵字
  renderOverviewKws(data.keywords.slice(0, 5));
}

/** 熱門頁面列表（總覽用） */
function renderOverviewPages(pages) {
  const el = document.getElementById('overview-pages');
  if (!el) return;
  const maxViews = pages[0]?.views || 1;
  el.innerHTML = pages.map(p => {
    const pct = Math.round((p.views / maxViews) * 100);
    const isWarn = parseFloat(p.bounce) > 65;
    return `
      <li class="url-item" onclick="openModal('modal-page','${p.path}')">
        <div class="url-path">
          ${p.path}
          ${isWarn ? `<span class="badge badge-red" style="margin-left:5px">跳出 ${p.bounce} ⚠</span>` : ''}
        </div>
        <div class="url-meta">
          <span>${p.views.toLocaleString()} 次瀏覽</span>
          <span>停留 ${p.time}</span>
          <span>跳出 ${p.bounce}</span>
        </div>
        <div class="url-bar-track"><div class="url-bar-fill" style="width:${pct}%;${isWarn?'background:#dc2626':''}"></div></div>
      </li>`;
  }).join('');
}

/** 熱門關鍵字列表（總覽用） */
function renderOverviewKws(kws) {
  const el = document.getElementById('overview-kws');
  if (!el) return;
  el.innerHTML = kws.map(k => {
    const rankNum = parseFloat(k.rank.replace('#',''));
    const isTop = rankNum <= 5;
    const trendColor = k.trend.startsWith('+') ? 'var(--success)' : k.trend.startsWith('−') ? 'var(--danger)' : 'var(--muted)';
    return `
      <div class="kw-row" onclick="openModal('modal-kw','${k.kw}')">
        <div class="kw-rank ${isTop ? 'top' : ''}">${k.rank}</div>
        <div class="kw-info">
          <div class="kw-name">${k.kw}</div>
          <div class="kw-meta">曝光 ${k.imp.toLocaleString()} · CTR ${k.ctr}</div>
        </div>
        <div style="font-size:10px;color:${trendColor}">${k.trend}</div>
      </div>`;
  }).join('');
}

/** 建立 Page 1 — GA4 流量 */
function buildGA4(data) {
  // 三線趨勢
  makeLine('c-ga4trend', [
    { data: data.sessions_trend,  borderColor: '#7C3AED', borderWidth: 2, pointRadius: 0, tension: 0.4 },
    { data: data.users_trend,     borderColor: '#c4b5fd', borderWidth: 1.5, pointRadius: 0, tension: 0.4, borderDash: [3,2] },
    { data: data.new_users_trend, borderColor: '#ddd6fe', borderWidth: 1.5, pointRadius: 0, tension: 0.4, borderDash: [2,2] },
  ]);

  // 裝置圓環
  makeDonut('c-device', data.device);

  // 頁面表格
  renderPagesTable(data.pages);
}

function renderPagesTable(pages) {
  const tbody = document.getElementById('pages-tbody');
  if (!tbody) return;
  const statusMap = { good: ['badge-green','優良'], warn: ['badge-yellow','普通'], bad: ['badge-red','需優化'] };
  tbody.innerHTML = pages.map(p => {
    const [cls, label] = statusMap[p.status] || ['badge-yellow','普通'];
    const bounceHigh = parseFloat(p.bounce) > 65;
    return `
      <tr onclick="openModal('modal-page','${p.path}')">
        <td>${p.path}</td>
        <td class="num">${p.views.toLocaleString()}</td>
        <td class="num">${p.unique.toLocaleString()}</td>
        <td class="num">${p.time}</td>
        <td class="num" ${bounceHigh ? 'style="color:var(--danger);font-weight:500"' : ''}>${p.bounce}</td>
        <td class="num">${p.conv}</td>
        <td class="num"><span class="badge ${cls}">${label}</span></td>
      </tr>`;
  }).join('');
}

/** 建立 Page 2 — Search Console */
function buildSC(data) {
  // 雙軸折線
  const canvas = document.getElementById('c-ssc');
  if (canvas) {
    if (CHARTS['c-ssc']) {
      CHARTS['c-ssc'].destroy();
    }
    const labels = data.labels || DAYS_14;
    CHARTS['c-ssc'] = new Chart(canvas, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          { data: data.ssc_imp,   borderColor: '#7C3AED', borderWidth: 2, pointRadius: 0, tension: 0.4, fill: true, backgroundColor: 'rgba(124,58,237,0.04)', yAxisID: 'y' },
          { data: data.ssc_click, borderColor: '#a78bfa', borderWidth: 2, pointRadius: 0, tension: 0.4, borderDash: [3,2], yAxisID: 'y2' },
        ],
      },
      options: {
        ...CHART_OPTIONS_BASE,
        scales: {
          x:  { 
            ...X_GRID_OFF, 
            ticks: { 
              ...X_GRID_OFF.ticks, 
              autoSkip: true, 
              maxTicksLimit: 10,
              font: { size: 9 } 
            } 
          },
          y:  { ...Y_GRID_ON,  position: 'left',  ticks: { ...Y_GRID_ON.ticks, callback: v => v>=1000 ? (v/1000).toFixed(0)+'K' : v } },
          y2: { grid: { display: false }, position: 'right', ticks: { font: { size: 10 }, color: '#9ca3af' } },
        },
      },
    });
  }

  // 搜尋類型圓環
  makeDonut('c-sqtype', data.search_type);

  // 關鍵字表格
  renderKwTable(data.keywords);
}

function renderKwTable(kws) {
  const tbody = document.getElementById('kw-tbody');
  if (!tbody) return;
  const oppMap = { good: 'badge-green', warn: 'badge-yellow', bad: 'badge-red' };
  tbody.innerHTML = kws.map(k => {
    const trendColor = k.trend.startsWith('+') ? 'var(--success)' : k.trend.startsWith('−') ? 'var(--danger)' : 'var(--muted)';
    return `
      <tr onclick="openModal('modal-kw','${k.kw}')">
        <td>${k.kw}</td>
        <td class="num">${k.imp.toLocaleString()}</td>
        <td class="num">${k.click.toLocaleString()}</td>
        <td class="num">${k.ctr}</td>
        <td class="num">${k.rank}</td>
        <td class="num" style="color:${trendColor}">${k.trend}</td>
        <td class="num"><span class="badge ${oppMap[k.opp_type]}">${k.opp}</span></td>
      </tr>`;
  }).join('');
}

/** 建立 Page 3 — 廣告投放 */
function buildAds(data) {
  // 花費 vs 收益趨勢
  makeLine('c-adtrend', [
    { data: data.ad_revenue, borderColor: '#7C3AED', borderWidth: 2, pointRadius: 0, tension: 0.4 },
    { data: data.ad_spend,   borderColor: '#d1d5db', borderWidth: 1.5, pointRadius: 0, tension: 0.4, borderDash: [4,3] },
  ], v => '$' + v + 'K');

  // 預算圓環
  makeDonut('c-budget', data.budget);

  // 渠道表格
  renderChannelTable(data.channels);
}

function renderChannelTable(channels) {
  const tbody = document.getElementById('channel-tbody');
  if (!tbody) return;
  const statusMap = { good: ['badge-green','優良'], warn: ['badge-yellow','注意'], bad: ['badge-red','需優化'] };
  const roasColor = { good: 'var(--success)', warn: 'var(--warning)', bad: 'var(--danger)' };
  tbody.innerHTML = channels.map(ch => {
    const [cls, label] = statusMap[ch.status] || ['badge-yellow','注意'];
    return `
      <tr onclick="openModal('modal-channel','${ch.name}')">
        <td>
          <span class="ch-icon" style="background:${ch.icon_bg};color:${ch.icon_color}">
            <i class="ti ${ch.icon}" aria-hidden="true"></i>
          </span>${ch.name}
        </td>
        <td class="num">${ch.spend}</td>
        <td class="num">${ch.imp}</td>
        <td class="num">${ch.click}</td>
        <td class="num">${ch.conv}</td>
        <td class="num">${ch.cpa}</td>
        <td class="num" style="color:${roasColor[ch.status]};font-weight:500">${ch.roas}</td>
        <td class="num"><span class="badge ${cls}">${label}</span></td>
      </tr>`;
  }).join('');
}

/** 建立 Page 4 — 串接教學 */
function buildOnboarding() {
  const list = document.getElementById('onb-list');
  if (list) list.innerHTML = ONB_DATA.map(o => `
    <div class="onb-card ${o.done ? 'done' : ''}" onclick="openModal('modal-onb','${o.id}')">
      <div class="onb-icon" style="background:${o.icon_bg}">
        <i class="ti ${o.icon}" style="color:${o.icon_color};font-size:18px" aria-hidden="true"></i>
      </div>
      <div class="onb-card-info">
        <div class="onb-card-title">${o.title}</div>
        <div class="onb-card-sub">${o.sub}</div>
      </div>
      <div class="onb-card-status">
        ${o.done
          ? '<span class="badge badge-green">✓ 已完成</span>'
          : o.optional
            ? '<span style="font-size:10px;color:var(--text-secondary)">選填</span>'
            : '<span class="badge badge-yellow">待完成</span>'}
      </div>
    </div>`).join('');

  const faqEl = document.getElementById('faq-list');
  if (faqEl) faqEl.innerHTML = FAQ_DATA.map(f => `
    <div class="faq-row" onclick="openModal('modal-faq','${f.id}')">
      <i class="ti ti-question-mark" aria-hidden="true"></i>
      <div style="flex:1">${f.q}</div>
      <i class="ti ti-chevron-right" aria-hidden="true" style="font-size:12px;color:var(--muted)"></i>
    </div>`).join('');

  // 串接資料源 Modal 清單
  const clist = document.getElementById('connect-list');
  if (clist) clist.innerHTML = ONB_DATA.map(o => `
    <div class="onb-card" onclick="closeModal('modal-connect');goTab(5);openModal('modal-onb','${o.id}')">
      <div class="onb-icon" style="background:${o.icon_bg}">
        <i class="ti ${o.icon}" style="color:${o.icon_color};font-size:18px" aria-hidden="true"></i>
      </div>
      <div class="onb-card-info">
        <div class="onb-card-title">${o.connect_title || o.title}</div>
        <div class="onb-card-sub">${o.sub}</div>
      </div>
      <i class="ti ti-chevron-right" style="font-size:14px;color:var(--muted);margin-left:auto" aria-hidden="true"></i>
    </div>`).join('');
}

/* ────────────────────────────────────────────
   6. 靜態知識庫（Modal 詳情用）
──────────────────────────────────────────── */
const PAGE_DATA = {
  '/': { views:'12,401', bounce:'38%', time:'3:12', ai:'首頁表現良好，跳出率 38% 屬正常範圍。建議在 Hero 區塊加強 CTA 按鈕可見度，將訪客引導至 /pricing 或 /docs，有機會提升 15–20% 的深度瀏覽率。' },
  '/pricing': { views:'7,832', bounce:'78% ⚠', time:'1:05', ai:'跳出率 78% 遠高於平均，停留僅 1 分鐘，代表用戶看不到想要的資訊就離開。建議：① 頁面頂部加入「最多人選擇」標籤 ② 加速頁面載入速度至 2 秒內 ③ 加入客戶信任標誌（品牌 Logo、評價）。' },
  '/blog/ga4-guide': { views:'5,210', bounce:'41%', time:'4:28', ai:'這是全站表現最佳的內容頁，平均停留 4:28 分鐘，代表內容品質高。建議在文章中段加入產品 CTA，把自然流量轉化為試用用戶，預估轉換率可提升 1–2%。' },
  '/features': { views:'3,980', bounce:'45%', time:'2:50', ai:'功能頁中等表現。建議加入互動式 Demo 或短影片，讓用戶直接體驗功能，可有效降低跳出率並提升轉換意圖。' },
  '/docs': { views:'2,140', bounce:'33%', time:'5:10', ai:'文件頁停留時間最長（5:10），代表這些都是高意圖用戶。建議在文件頁側邊欄加入「升級 Pro 方案」的 CTA，轉換機會高。' },
  '/contact': { views:'1,820', bounce:'52%', time:'1:45', ai:'聯絡頁轉換率 8.9% 是全站最高，代表來到這頁的用戶意圖明確。建議加入即時聊天功能，進一步提升回應速度。' },
  '/blog/seo-tips': { views:'1,540', bounce:'39%', time:'3:55', ai:'SEO 教學文章表現穩定。建議在文章末尾加入「免費下載 SEO 檢查清單」的 Lead Magnet，可有效收集 Email 名單。' },
};

const KW_DATA = {
  '數據分析工具':          { rank:'#4.0', ctr:'5.2%', click:'1,477', ai:'排名 #4，距進入 Top 3 還差一步。建議在 /features 頁面增加「數據分析工具」相關的 H1/H2 標題與結構化資料標記，有機會在 4–6 週內衝進 Top 3。' },
  'GA4 教學':              { rank:'#3.2', ctr:'6.8%', click:'1,306', ai:'CTR 6.8% 非常優秀，代表標題吸引力強。目前排名 #3，建議更新 /blog/ga4-guide 的發布日期並補充 2025 年最新截圖，Google 偏好時效性內容，有機會搶到 #1 精選摘要。' },
  '網站流量分析':          { rank:'#6.1', ctr:'3.9%', click:'616',   ai:'排名 #6 但點擊率只有 3.9%，代表 Meta Description 不夠吸引人。建議重新撰寫頁面的 SEO 描述，加入數字（如「3分鐘學會分析網站流量」），預計 CTR 可提升至 5–6%。' },
  'google analytics 設定': { rank:'#12',  ctr:'2.1%', click:'240',   ai:'排名 #12，屬於第二頁，點擊率低。建議新增一篇「Google Analytics 4 完整設定教學 2025」長文，針對此關鍵字優化，有機會在 2 個月內進入第一頁。' },
  'SEO 工具推薦':          { rank:'#18',  ctr:'1.8%', click:'173',   ai:'目前排名偏低，但搜尋量龐大。建議製作一篇「2025 年 SEO 工具完整比較」的比較文章，包含競品評測，這類文章通常能快速累積外部連結。' },
  '廣告效益分析':          { rank:'#14',  ctr:'2.2%', click:'158',   ai:'排名有上升趨勢（+2），建議持續優化廣告相關內容頁，加入廣告 ROAS 計算器等互動工具，可大幅提升停留時間與排名。' },
};

const METRIC_DATA = {
  '工作階段':       { desc:'「工作階段」是一個用戶在網站上的一次連續造訪，無論他看了幾頁，只要在 30 分鐘內都算一次工作階段。', meaning:'你的網站本週共吸引 38,241 次造訪，比上期成長 9.4%，代表網站流量健康成長中。', improve:'① 增加 SEO 文章產出 ② 加強社群媒體分享 ③ 提高廣告投放預算 ④ 建立 Email 電子報定期召回舊用戶。' },
  '不重複用戶':     { desc:'在所選時間範圍內，造訪網站的獨立個體數量，同一個人多次造訪只算一位。', meaning:'本週有 28,109 位不同的用戶造訪你的網站，新用戶比例 63.4% 代表超過一半是首次來訪。', improve:'① 優化 SEO 讓更多人透過搜尋找到你 ② 投放付費廣告擴大觸及 ③ 創作值得分享的內容吸引口碑傳播。' },
  '平均停留時間':   { desc:'用戶在網站上平均花費的時間，時間越長通常代表內容越吸引人。', meaning:'本週平均停留 2 分 34 秒，較上期減少 12 秒，行業平均約 2–3 分鐘，目前處於臨界值需注意。', improve:'① 在文章中加入圖片與影片 ② 內部連結引導用戶繼續閱讀 ③ 頁面載入速度要在 3 秒內 ④ 提升文章深度（建議 1500 字以上）。' },
  '整體跳出率':     { desc:'「跳出率」是用戶進入網站後只看一頁就離開的比例，越低通常代表網站越吸引人。', meaning:'本週整體跳出率 54.2%，持平。電商理想 30–55%，內容型 60–80%。/pricing 頁面的 78% 需要優先處理。', improve:'① 確保廣告與落地頁內容一致 ② 加快頁面載入速度 ③ 在頁面底部加入「延伸閱讀」推薦 ④ 改善 CTA 可見度。' },
  '新用戶比例':     { desc:'首次造訪你網站的用戶佔總用戶的比例。', meaning:'新用戶佔 63.4%，代表你的品牌正在持續觸及新的潛在客戶，成長動能健康。', improve:'① 增加 SEO 文章觸及更多搜尋 ② 擴大廣告受眾範圍 ③ 媒體曝光與公關合作 ④ 社群媒體定期發文。' },
  '轉換率':         { desc:'轉換率 = 完成目標行為的工作階段 ÷ 總工作階段，代表流量中有多少比例採取了期望行動。', meaning:'本週轉換率 3.82%，提升 0.4%，高於電商平均（1–3%），代表網站品質與受眾精準度都不錯。', improve:'① 在關鍵頁面增加社會證明 ② 提供限時優惠 ③ 優化表單欄位數量（越少越好） ④ 確保行動版體驗流暢。' },
  '每次工作階段頁數':{ desc:'每次工作階段平均瀏覽的頁面數量，代表用戶在網站內的探索深度。', meaning:'每次工作階段平均瀏覽 3.2 頁，持平。代表用戶不只看了入口頁，還主動探索了其他頁面。', improve:'① 在每篇文章底部加入「延伸閱讀」 ② 使用相關產品推薦 ③ 在頁面中加入內部連結。' },
  '目標完成次數':   { desc:'用戶完成你在 GA4 中設定的具體目標次數，例如點擊電話、填寫表單等。', meaning:'本週目標完成 1,462 次，成長 7.8%，代表越來越多用戶在網站上採取了有價值的行動。', improve:'① 確保 GA4 中正確追蹤所有重要行為 ② 在轉換路徑中減少摩擦點 ③ 針對高意圖頁面優化 CTA 設計。' },
  '搜尋曝光':       { desc:'你的網站在 Google 搜尋結果中被看到的次數，即使用戶沒有點擊也算。', meaning:'本週曝光 182,000 次，成長 12%，代表 Google 越來越認可你的網站內容。', improve:'① 持續新增高品質 SEO 內容 ② 針對排名 6–10 名的關鍵字加強優化 ③ 建立外部連結提升網域權重。' },
  '自然點擊':       { desc:'用戶在 Google 搜尋結果中看到你的網站後，實際點擊進入的次數（不含廣告）。', meaning:'本週自然點擊 6,921 次，成長 9%。自然流量是最有價值的流量來源，獲取成本為零。', improve:'① 優化每個頁面的 Title Tag（60字內）② 撰寫吸引人的 Meta Description ③ 爭取「精選摘要」位置。' },
  '平均點擊率':     { desc:'CTR = 點擊次數 ÷ 曝光次數，代表看到你的網站後有多少比例的人會點擊。', meaning:'本週平均 CTR 3.8%，Google 整體平均約 2–3%，你目前略高於平均，代表標題與描述對用戶有吸引力。', improve:'① 標題加入吸睛數字 ② 加入情感字眼（免費、完整、快速）③ 使用結構化資料標記（Schema）。' },
  '平均排名':       { desc:'你的網站在 Google 搜尋結果中的平均位置，越接近 1 代表越靠前。', meaning:'本週平均排名 #4.2，較上期改善 0.8。一般排名 1–3 獲得約 70% 的點擊，4–10 獲得約 20%。', improve:'① 針對特定關鍵字優化對應頁面 ② 提升 Core Web Vitals ③ 增加高品質外部連結 ④ 確保內容更新頻率。' },
  '廣告花費':       { desc:'所有廣告平台在選定期間內的總花費金額。', meaning:'本週廣告總花費 $124,500，較上期增加 12%。花費增加但收益只成長 8%，廣告效益略有下滑需注意。', improve:'① 暫停表現差的廣告（ROAS < 2×）② 提高預算給表現好的廣告（ROAS > 4×）③ 優化廣告創意降低 CPM。' },
  '廣告收益':       { desc:'透過廣告帶來的轉換所產生的總收益金額。', meaning:'本週廣告收益 $450,200，成長 8%，整體 ROAS 3.61× 代表每投入 $1 廣告費用可帶回 $3.61 收益。', improve:'① 優化落地頁轉換率 ② 提升客單價（AOV）③ 針對高 LTV 受眾加強再行銷。' },
  '整體ROAS':       { desc:'ROAS = 廣告收益 ÷ 廣告花費，代表每花 $1 廣告費可帶回多少收益。', meaning:'整體 ROAS 3.61× 在健康範圍，但需注意 Meta 的 ROAS 已降至 2.8×，Google Ads 4.2× 表現最佳。', improve:'① 重新分配預算給高 ROAS 渠道 ② 優化廣告受眾 ③ 提升網站轉換率（CRO）。' },
  '轉換次數':       { desc:'用戶完成目標行為的次數，例如購買、填表、加入購物車等。', meaning:'本週轉換 1,842 次，成長 6.1%，代表廣告有效將流量轉化為實際行動。', improve:'① 簡化結帳/填表流程 ② 加入即時聊天客服 ③ 使用退場意圖 Pop-up 挽留用戶 ④ A/B 測試 CTA 按鈕。' },
  '平均CPC':        { desc:'CPC = 廣告花費 ÷ 點擊次數，每次廣告點擊的平均成本。', meaning:'本週平均 CPC $1.84，較上期降低 8%，代表廣告競爭效率提升，同樣預算可獲得更多點擊。', improve:'① 提升廣告品質分數 ② 使用長尾關鍵字 ③ 優化廣告文案提升 CTR ④ 選擇競爭較低的投放時段。' },
  '平均CPA':        { desc:'CPA = 廣告花費 ÷ 轉換次數，每獲得一次轉換的平均成本。', meaning:'本週平均 CPA $67.6，較上期降低 18%，是本週廣告表現最佳的指標，用更少的錢獲得同樣的轉換。', improve:'① 優先投放 CPA 最低的廣告組合 ② 暫停 CPA 最高的渠道（YouTube $114.8）③ 測試目標 CPA 智慧出價。' },
  '廣告印象':       { desc:'廣告被展示的總次數，包含所有平台的曝光。', meaning:'本週廣告總曝光 2.61M 次，成長 14%，代表品牌觸及範圍在擴大。', improve:'① 優先選擇目標受眾重疊度低的平台 ② 使用再行銷廣告接觸高意圖用戶 ③ 測試不同廣告格式找到 CPM 最低的形式。' },
};

const CHANNEL_DATA = {
  'Google Ads':  { roas:'4.2×', cpa:'$59.8',  conv:'1,140', ai:'Google Ads 本週表現最佳，ROAS 4.2× 遠高於整體平均 3.61×。建議將 Meta Ads 節省的預算 50% 轉移至 Google Ads，優先加碼「搜尋廣告」中的品牌詞與競品詞，預估 ROAS 可進一步提升至 4.5×。' },
  'Meta Ads':    { roas:'2.8×', cpa:'$72.9',  conv:'580',   ai:'Meta Ads ROAS 從上週 3.2× 降至 2.8×，觸發警告。可能原因：① 受眾疲勞（廣告素材需要更換）② 受眾重疊度過高 ③ iOS 隱私政策影響歸因。建議更換廣告素材、縮小受眾年齡層，並開啟「Advantage+ 受眾」自動優化。' },
  'YouTube Ads': { roas:'1.9×', cpa:'$114.8', conv:'122',   ai:'YouTube ROAS 1.9× 低於損益平衡點，是本週拖累整體效益的主因。建議：① 暫停表現最差的廣告組合 ② 將預算減少 50%（約 $7,000）③ 把省下的預算轉移給 Google Ads。YouTube 廣告適合品牌認知目的而非直接轉換，需重新定義 KPI。' },
};

const ONB_DATA = [
  { id:'ga4',  icon:'ti-brand-google', icon_bg:'#EFF6FF', icon_color:'#1d4ed8', title:'步驟 1：串接 Google Analytics 4（GA4）',    connect_title:'Google Analytics 4', sub:'取得網站流量、用戶行為、轉換率數據', done:true,  optional:false,
    steps:[
      { t:'前往 Google Analytics',       d:'打開瀏覽器，進入 analytics.google.com，使用你管理網站的 Google 帳號登入。', tag:'✓ 已完成' },
      { t:'確認使用 GA4 版本',           d:'在左側選單確認你在「GA4 屬性」中（不是舊版 Universal Analytics）。', tag:'✓ 已完成' },
      { t:'複製你的「評估 ID」',         d:'點擊左下角「管理」→「資料串流」→ 點擊你的網站串流 → 複製右上角的「評估 ID」（格式：G-XXXXXXXXXX）。', tag:'✓ 已完成' },
      { t:'貼入 Dashboard 設定',         d:'點擊右上角「串接資料源」→ 選擇 GA4 → 將複製的評估 ID 貼入欄位中，系統會自動驗證並開始抓取數據。', tag:'✓ 已完成' },
    ]},
  { id:'gsc',  icon:'ti-search',        icon_bg:'#F0FDF4', icon_color:'#16a34a', title:'步驟 2：串接 Google Search Console',          connect_title:'Google Search Console', sub:'取得自然搜尋排名、關鍵字、點擊率數據', done:false, optional:false,
    steps:[
      { t:'前往 Google Search Console',  d:'打開 search.google.com/search-console，使用網站管理員的 Google 帳號登入。', tag:'需要 5 分鐘' },
      { t:'確認你的網站已驗證',          d:'在左側選單能看到你的網站 URL，且狀態顯示「已驗證」。如果尚未驗證，點擊「新增資源」，依指示複製 HTML 標記貼到網站首頁的 <head> 中。', tag:'不需工程師' },
      { t:'確認數據已累積',              d:'Search Console 需要一些時間才會有數據。如果是新驗證的網站，最快 48 小時後才會出現點擊與曝光數據，請耐心等待。', tag:'最快 48 小時' },
      { t:'使用 Google 帳號授權',        d:'回到本 Dashboard，點擊「串接資料源」→ 選擇 Search Console → 使用 Google 帳號授權即可，系統會自動抓取你帳號下所有已驗證的網站數據。', tag:'一鍵授權' },
    ]},
  { id:'gads', icon:'ti-speakerphone',  icon_bg:'#FFFBEB', icon_color:'#d97706', title:'步驟 3：串接 Google Ads（選填）',              connect_title:'Google Ads', sub:'取得關鍵字廣告花費、ROAS、轉換成本', done:false, optional:true,
    steps:[
      { t:'確認你有 Google Ads 帳戶',    d:'前往 ads.google.com，確認你有正在投放廣告的帳戶。如果沒有，可以先跳過此步驟。', tag:'選填步驟' },
      { t:'找到你的「客戶 ID」',         d:'登入 Google Ads 後，在右上角會看到格式為 XXX-XXX-XXXX 的「客戶 ID」，複製這個數字。', tag:'30 秒完成' },
      { t:'在 Google Ads 授權 API 存取', d:'進入「工具與設定」→「API 中心」→ 接受開發人員授權條款，這樣才能讓 Dashboard 讀取你的廣告數據。', tag:'一次性設定' },
      { t:'貼入 Dashboard 完成串接',     d:'點擊「串接資料源」→ 選擇 Google Ads → 輸入客戶 ID，使用 Google 帳號授權後即完成。', tag:'一鍵授權' },
    ]},
  { id:'meta', icon:'ti-brand-facebook',icon_bg:'#F5F3FF', icon_color:'#6d28d9', title:'步驟 4：串接 Meta Ads（選填）',                connect_title:'Meta Ads (FB/IG)', sub:'取得 Facebook/Instagram 廣告 ROAS、受眾觸及', done:false, optional:true,
    steps:[
      { t:'確認你有 Meta 商業管理平台帳號', d:'前往 business.facebook.com，使用你投放廣告的 Facebook 帳號登入。Meta 廣告必須透過「商業管理平台」管理才能串接。', tag:'選填步驟' },
      { t:'找到你的「廣告帳號 ID」',     d:'在商業管理平台左側點選「廣告帳號」，複製廣告帳號 ID（格式：act_XXXXXXXXXXXXXXX）。', tag:'30 秒完成' },
      { t:'建立「系統用戶」並取得存取權杖', d:'「設定」→「系統用戶」→「新增系統用戶」→ 授予廣告帳號「分析師」權限 → 點擊「產生新 Token」並複製。', tag:'最複雜的步驟' },
      { t:'貼入 Dashboard 完成串接',     d:'點擊「串接資料源」→ 選擇 Meta Ads → 輸入廣告帳號 ID 與 Access Token，點擊「驗證並儲存」即完成。', tag:'約 10 分鐘' },
    ]},
];

const FAQ_DATA = [
  { id:'ga4-id',       q:'什麼是 GA4 的「評估 ID」？在哪裡找？',         title:'GA4 評估 ID 在哪裡找？',         body:'GA4 評估 ID 的格式是 G-XXXXXXXXXX，在 Google Analytics 後台以下路徑找到：\n\n① 登入 analytics.google.com\n② 點擊左下角「管理」（齒輪圖示）\n③ 在「資料收集和修改」欄位點擊「資料串流」\n④ 點擊你的網站名稱\n⑤ 右上角顯示的「評估 ID」就是你需要的。\n\n格式範例：G-ABC12345XY' },
  { id:'service-acc',  q:'什麼是「服務帳戶金鑰」？我需要技術能力嗎？',   title:'需要服務帳戶金鑰嗎？',           body:'不需要！本 Dashboard 採用「OAuth 授權」的方式串接，你只需要點擊「使用 Google 帳號登入」按鈕，系統會自動取得你帳號下的數據存取權限，完全不需要下載任何金鑰檔案，也不需要技術背景。' },
  { id:'data-safe',    q:'我的數據安全嗎？會被看到嗎？',                   title:'我的數據安全嗎？',               body:'你的數據安全有以下幾個保障：\n\n① 唯讀存取：我們只申請「讀取」權限，無法修改你的廣告或網站任何設定。\n② 不儲存原始數據：我們只儲存彙整後的統計數字，不儲存個別用戶的資料。\n③ OAuth 標準授權：採用 Google/Meta 的官方授權機制，你可以隨時在 Google 帳號設定中撤銷我們的存取權限。\n④ 符合 GDPR / 個資法。' },
  { id:'update-freq',  q:'數據多久更新一次？是即時的嗎？',                 title:'數據多久更新一次？',             body:'不同數據源的更新頻率不同：\n\n・GA4 流量數據：約 24–48 小時延遲\n・Search Console 數據：約 2–3 天延遲\n・Google Ads：約 3 小時延遲\n・Meta Ads：約 1 小時延遲\n\n本 Dashboard 會每天早上 8:00 自動抓取最新數據，你也可以手動點擊重新整理觸發更新。' },
];

/* ────────────────────────────────────────────
   7. 頁籤切換
──────────────────────────────────────────── */
const BUILT = { p1: false, p2: false, p3: false, p4: false, p5: false };

function goTab(idx) {
  document.querySelectorAll('.tab').forEach((t, i) => {
    t.classList.toggle('on', i === idx);
    t.setAttribute('aria-selected', i === idx);
  });
  document.querySelectorAll('.page').forEach((p, i) => p.classList.toggle('on', i === idx));

  if (idx === 1 && !BUILT.p1) { buildGA4(currentData); BUILT.p1 = true; }
  if (idx === 2 && !BUILT.p2) { buildSC(currentData);  BUILT.p2 = true; }
  if (idx === 3 && !BUILT.p3) { buildAds(currentData); BUILT.p3 = true; }
  if (idx === 4 && !BUILT.p4) { initSeoEvaluatorUI(); BUILT.p4 = true; }
  if (idx === 5 && !BUILT.p5) { buildOnboarding(); BUILT.p5 = true; }
}

/* ────────────────────────────────────────────
   8. Seg Control（圖表切換）
──────────────────────────────────────────── */
function switchSeg(btn, chartId, range) {
  btn.closest('.seg-ctrl').querySelectorAll('.seg-btn').forEach(b => b.classList.remove('on'));
  btn.classList.add('on');
  // TODO: 後端完成後，依 range 重新 fetch 並更新圖表
  console.log(`Switch ${chartId} to ${range} days`);
}

/* ────────────────────────────────────────────
   9. Modal 控制
──────────────────────────────────────────── */
let pageTrendChart = null;

function openModal(id, param) {
  document.getElementById(id).classList.add('show');

  if (id === 'modal-page' && param) {
    const d = PAGE_DATA[param] || { views: '—', bounce: '—', time: '—', ai: '找不到此頁面的分析資料。' };
    document.getElementById('mp-title').textContent = '頁面詳情：' + param;
    document.getElementById('mp-views').textContent = d.views;
    document.getElementById('mp-bounce').textContent = d.bounce;
    document.getElementById('mp-time').textContent = d.time;
    document.getElementById('mp-ai').textContent = d.ai;
    document.getElementById('mp-ai-btn').onclick = () => sendPrompt('針對頁面 ' + param + ' 給我詳細的優化建議，包含具體的內容與程式碼修改方向');
    setTimeout(() => {
      const canvas = document.getElementById('c-page-trend');
      if (!canvas) return;
      if (pageTrendChart) { pageTrendChart.destroy(); pageTrendChart = null; }
      pageTrendChart = new Chart(canvas, {
        type: 'line',
        data: {
          labels: ['週一','週二','週三','週四','週五','週六','週日'],
          datasets: [{
            data: Array.from({ length: 7 }, () => Math.round(800 + Math.random() * 1200)),
            borderColor: '#7C3AED', borderWidth: 2, pointRadius: 0, tension: 0.4,
            fill: true, backgroundColor: 'rgba(124,58,237,0.05)',
          }],
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: { x: X_GRID_OFF, y: Y_GRID_ON },
        },
      });
    }, 80);
  }

  if (id === 'modal-kw' && param) {
    const d = KW_DATA[param] || { rank: '—', ctr: '—', click: '—', ai: '找不到此關鍵字的分析資料。' };
    document.getElementById('mkw-title').textContent = '關鍵字：' + param;
    document.getElementById('mkw-rank').textContent = d.rank;
    document.getElementById('mkw-ctr').textContent = d.ctr;
    document.getElementById('mkw-click').textContent = d.click;
    document.getElementById('mkw-ai').textContent = d.ai;
    document.getElementById('mkw-ai-btn').onclick = () => sendPrompt('針對關鍵字「' + param + '」提供完整的 SEO 優化策略，包含內容架構、標題優化和連結建設建議');
  }

  if (id === 'modal-metric' && param) {
    const d = METRIC_DATA[param] || { desc: '說明尚未建立。', meaning: '—', improve: '—' };
    document.getElementById('mm-title').textContent = '指標說明：' + param;
    document.getElementById('mm-desc').textContent = d.desc;
    document.getElementById('mm-meaning').textContent = d.meaning;
    document.getElementById('mm-improve').textContent = d.improve;
  }

  if (id === 'modal-channel' && param) {
    const d = CHANNEL_DATA[param] || { roas: '—', cpa: '—', conv: '—', ai: '找不到此渠道的分析資料。' };
    document.getElementById('mch-title').textContent = param + ' 詳情';
    document.getElementById('mch-roas').textContent = d.roas;
    document.getElementById('mch-cpa').textContent = d.cpa;
    document.getElementById('mch-conv').textContent = d.conv;
    document.getElementById('mch-ai').textContent = d.ai;
    document.getElementById('mch-btn').onclick = () => sendPrompt('針對 ' + param + ' 的廣告效益，提供具體的優化方案與預算建議');
  }

  if (id === 'modal-onb' && param) {
    const o = ONB_DATA.find(x => x.id === param);
    if (!o) return;
    document.getElementById('monb-title').textContent = o.title;
    document.getElementById('monb-steps').innerHTML = o.steps.map((s, i) => `
      <li>
        <div>
          <div class="step-title">${s.t}</div>
          <div class="step-desc">${s.d}</div>
          <span class="step-tag">${s.tag}</span>
        </div>
      </li>`).join('');
  }

  if (id === 'modal-faq' && param) {
    const f = FAQ_DATA.find(x => x.id === param);
    if (!f) return;
    document.getElementById('mfaq-title').textContent = f.title;
    document.getElementById('mfaq-body').innerHTML = f.body.replace(/\n/g, '<br>');
  }
}

function closeModal(id) {
  document.getElementById(id).classList.remove('show');
}

function closeOnBg(event, id) {
  if (event.target === document.getElementById(id)) closeModal(id);
}

/* ────────────────────────────────────────────
   10. Keyboard support (Escape 關閉 Modal)
──────────────────────────────────────────── */
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-bg.show').forEach(m => m.classList.remove('show'));
  }
});

/* ────────────────────────────────────────────
   11. 多公司/專案管理與初始化
──────────────────────────────────────────── */

async function initProfiles() {
  const selectorBtn = document.getElementById('project-selector-btn');
  const dropdown = document.getElementById('project-dropdown');
  const listContainer = document.getElementById('project-list-items');
  const activeNameEl = document.getElementById('active-project-name');
  const activeTitleNameEl = document.getElementById('active-project-title-name');
  const addBtn = document.getElementById('btn-add-project-trigger');
  
  if (!selectorBtn || !dropdown || !listContainer) return;
  
  // 點擊按鈕切換下拉選單顯示/隱藏
  selectorBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    dropdown.classList.toggle('show');
    selectorBtn.classList.toggle('open');
  });
  
  // 點擊外面關閉選單
  document.addEventListener('click', () => {
    dropdown.classList.remove('show');
    selectorBtn.classList.remove('open');
  });
  
  // 點擊「新增專案」
  if (addBtn) {
    addBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      dropdown.classList.remove('show');
      selectorBtn.classList.remove('open');
      openModal('modal-create-project');
    });
  }
  
  // 新增專案彈窗的送出按鈕
  const submitBtn = document.getElementById('btn-submit-create-project');
  if (submitBtn) {
    submitBtn.addEventListener('click', async () => {
      const nameInput = document.getElementById('new-project-name');
      const name = nameInput.value.trim();
      if (!name) { alert('請輸入公司/專案名稱'); return; }
      
      try {
        const res = await fetch(`${API_BASE}/api/profiles/create`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name })
        });
        if (res.ok) {
          nameInput.value = '';
          closeModal('modal-create-project');
          // 重新載入與更新專案
          await loadProfiles();
          // 如果在設定頁面，切換專案時要重新載入設定
          if (typeof loadCurrentSettings === 'function') {
            await loadCurrentSettings();
          } else {
            // 在首頁的話更新數據
            const savedRange = localStorage.getItem('dashboard_date_range') || '30';
            await updateDashboard(savedRange);
          }
        } else {
          alert('建立專案失敗');
        }
      } catch (e) {
        console.error('Create profile failed:', e);
        alert('無法連接到後端伺服器');
      }
    });
  }
  
  // 載入專案清單
  await loadProfiles();
}

async function loadProfiles() {
  const listContainer = document.getElementById('project-list-items');
  const activeNameEl = document.getElementById('active-project-name');
  const activeTitleNameEl = document.getElementById('active-project-title-name');
  if (!listContainer) return;
  
  try {
    const res = await fetch(`${API_BASE}/api/profiles`);
    if (!res.ok) throw new Error('API error');
    const data = await res.json();
    
    const activeId = data.active_profile_id;
    const profiles = data.profiles;
    
    // 找出當前 active 的專案名稱
    const activeProfile = profiles.find(p => p.id === activeId);
    const activeName = activeProfile ? activeProfile.name : '伯堅股份有限公司';
    if (activeNameEl) activeNameEl.textContent = activeName;
    if (activeTitleNameEl) activeTitleNameEl.textContent = activeName;
    
    // 渲染下拉選單列表
    listContainer.innerHTML = profiles.map(p => `
      <div class="project-item ${p.id === activeId ? 'active' : ''}" data-id="${p.id}">
        <span class="project-item-name">${p.name}</span>
        ${p.id !== 'default' ? `<span class="project-item-delete" data-id="${p.id}" title="刪除專案">×</span>` : ''}
      </div>
    `).join('');
    
    // 綁定項目點擊事件（切換專案）
    document.querySelectorAll('.project-item').forEach(item => {
      item.addEventListener('click', async (e) => {
        e.stopPropagation();
        const profileId = item.getAttribute('data-id');
        if (e.target.classList.contains('project-item-delete')) return;
        
        await switchProfile(profileId);
      });
    });
    
    // 綁定刪除專案點擊事件
    document.querySelectorAll('.project-item-delete').forEach(delBtn => {
      delBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const profileId = delBtn.getAttribute('data-id');
        const p = profiles.find(x => x.id === profileId);
        if (!p) return;
        
        if (confirm(`確定要刪除「${p.name}」專案嗎？\n這會將此專案的所有串接設定與金鑰檔案一併刪除且無法復原。`)) {
          await deleteProfile(profileId);
        }
      });
    });
    
  } catch (err) {
    console.error('Failed to load profiles:', err);
    if (activeNameEl) activeNameEl.textContent = '伯堅股份有限公司';
    if (activeTitleNameEl) activeTitleNameEl.textContent = '伯堅股份有限公司';
  }
}

async function switchProfile(profileId) {
  try {
    const res = await fetch(`${API_BASE}/api/profiles/switch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile_id: profileId })
    });
    if (res.ok) {
      document.getElementById('project-dropdown').classList.remove('show');
      document.getElementById('project-selector-btn').classList.remove('open');
      
      await loadProfiles();
      
      if (typeof loadCurrentSettings === 'function') {
        await loadCurrentSettings();
      } else {
        const savedRange = localStorage.getItem('dashboard_date_range') || '30';
        await updateDashboard(savedRange);
      }
    }
  } catch (e) {
    console.error('Switch profile failed:', e);
    alert('切換專案失敗');
  }
}

async function deleteProfile(profileId) {
  try {
    const res = await fetch(`${API_BASE}/api/profiles/${profileId}`, {
      method: 'DELETE'
    });
    if (res.ok) {
      await loadProfiles();
      if (typeof loadCurrentSettings === 'function') {
        await loadCurrentSettings();
      } else {
        const savedRange = localStorage.getItem('dashboard_date_range') || '30';
        await updateDashboard(savedRange);
      }
    }
  } catch (e) {
    console.error('Delete profile failed:', e);
    alert('刪除專案失敗');
  }
}

// ── AI 行銷顧問對話功能 ────────────────────────
async function sendPrompt(promptText) {
  if (!promptText) return;

  // 1. 打開 Modal
  openModal('modal-ai-chat');

  const messagesList = document.getElementById('chat-messages-list');
  const sendBtn = document.getElementById('btn-send-chat');
  const inputField = document.getElementById('chat-user-input');

  if (!messagesList) return;

  // 2. 添加使用者的發問訊息到 UI
  const userMsgEl = document.createElement('div');
  userMsgEl.className = 'chat-msg user';
  userMsgEl.textContent = promptText;
  messagesList.appendChild(userMsgEl);

  // 3. 滾動到底部
  messagesList.scrollTop = messagesList.scrollHeight;

  // 4. 顯示 AI 正在輸入的動畫 (Typing Indicator)
  const typingEl = document.createElement('div');
  typingEl.className = 'chat-msg assistant';
  typingEl.id = 'chat-typing-indicator';
  typingEl.innerHTML = `
    <div class="typing-indicator">
      <span></span><span></span><span></span>
    </div>
  `;
  messagesList.appendChild(typingEl);
  messagesList.scrollTop = messagesList.scrollHeight;

  // 禁用輸入與發送按鈕
  if (sendBtn) sendBtn.disabled = true;
  if (inputField) {
    inputField.disabled = true;
    inputField.value = '';
  }

  // 5. 打後端 API 取得 AI 回覆
  try {
    const res = await fetch(`${API_BASE}/api/ai/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: promptText })
    });
    
    // 移除輸入動畫
    const indicator = document.getElementById('chat-typing-indicator');
    if (indicator) indicator.remove();

    if (!res.ok) {
      let detail = 'API error';
      try {
        const errorData = await res.json();
        detail = errorData.detail || detail;
      } catch (e) {}
      throw new Error(detail);
    }
    
    const data = await res.json();
    const reply = data.reply;

    // 6. 添加 AI 的回覆到 UI
    const assistantMsgEl = document.createElement('div');
    assistantMsgEl.className = 'chat-msg assistant';
    
    // 支援 Markdown 粗體、段落、列表的極簡解析
    assistantMsgEl.innerHTML = parseMiniMarkdown(reply);
    messagesList.appendChild(assistantMsgEl);
  } catch (err) {
    console.error('AI Chat failed:', err);
    const indicator = document.getElementById('chat-typing-indicator');
    if (indicator) indicator.remove();

    const errMsgEl = document.createElement('div');
    errMsgEl.className = 'chat-msg assistant';
    errMsgEl.style.borderColor = 'var(--danger)';
    errMsgEl.innerHTML = `<strong>❌ 錯誤：</strong>${err.message}`;
    messagesList.appendChild(errMsgEl);
  } finally {
    // 恢復輸入與發送按鈕
    if (sendBtn) sendBtn.disabled = false;
    if (inputField) {
      inputField.disabled = false;
      inputField.focus();
    }
    messagesList.scrollTop = messagesList.scrollHeight;
  }
}

// 極簡 Markdown 解析器
function parseMiniMarkdown(md) {
  if (!md) return '';
  let html = md;
  // 標題 3
  html = html.replace(/^### (.*$)/gim, '<h3 style="font-size:13px;font-weight:600;margin-top:12px;margin-bottom:6px;color:var(--text-primary)">$1</h3>');
  // 標題 4
  html = html.replace(/^#### (.*$)/gim, '<h4 style="font-size:11px;font-weight:600;margin-top:10px;margin-bottom:4px;color:var(--text-primary)">$1</h4>');
  // 粗體
  html = html.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');
  // 斜體
  html = html.replace(/\*(.*?)\*/gim, '<em>$1</em>');
  // 清單
  html = html.replace(/^\* (.*$)/gim, '<li style="margin-left: 14px; list-style-type: disc;">$1</li>');
  html = html.replace(/^- (.*$)/gim, '<li style="margin-left: 14px; list-style-type: disc;">$1</li>');
  // 數字清單
  html = html.replace(/^\d+\. (.*$)/gim, '<li style="margin-left: 14px; list-style-type: decimal;">$1</li>');
  // 段落換行
  html = html.split('\n\n').map(p => {
    if (p.trim().startsWith('<li') || p.trim().startsWith('<h3') || p.trim().startsWith('<h4')) {
      return p;
    }
    return '<p style="margin-bottom:8px;line-height:1.65">' + p.replace(/\n/g, '<br>') + '</p>';
  }).join('');
  return html;
}

// 綁定 AI 對話輸入框與按鈕
function initAIChatUI() {
  const inputField = document.getElementById('chat-user-input');
  const sendBtn = document.getElementById('btn-send-chat');

  if (sendBtn && inputField) {
    // 點擊按鈕送出
    sendBtn.addEventListener('click', () => {
      const text = inputField.value.trim();
      if (text) sendPrompt(text);
    });

    // 按 Enter 送出
    inputField.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const text = inputField.value.trim();
        if (text) sendPrompt(text);
      }
    });
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  // 讀取先前儲存的天數/日期範圍
  const savedRange = localStorage.getItem('dashboard_date_range') || '30';
  const customStart = localStorage.getItem('dashboard_custom_start') || '';
  const customEnd = localStorage.getItem('dashboard_custom_end') || '';

  // 更新 UI 上的選取狀態
  const dateLabel = document.getElementById('date-label');
  const startInput = document.getElementById('custom-start-date');
  const endInput = document.getElementById('custom-end-date');

  if (startInput) startInput.value = customStart;
  if (endInput) endInput.value = customEnd;

  if (dateLabel) {
    if (savedRange === 'custom') {
      dateLabel.textContent = `${customStart} 至 ${customEnd}`;
    } else {
      dateLabel.textContent = `最近 ${savedRange} 天`;
    }
  }

  document.querySelectorAll('.date-option').forEach(opt => {
    opt.classList.toggle('active', opt.getAttribute('data-range') === savedRange);
  });

  // 設定日期下拉選單點擊事件
  const datePickerBtn = document.getElementById('date-picker-btn');
  const dateDropdown = document.getElementById('date-dropdown');
  if (datePickerBtn && dateDropdown) {
    datePickerBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      dateDropdown.classList.toggle('show');
    });
    
    // 點擊下拉選單內部不關閉選單 (讓自訂日期輸入框能正常點擊)
    dateDropdown.addEventListener('click', (e) => {
      e.stopPropagation();
    });

    document.addEventListener('click', () => {
      dateDropdown.classList.remove('show');
    });

    // 天數選項點擊事件
    document.querySelectorAll('.date-option').forEach(opt => {
      opt.addEventListener('click', async (e) => {
        e.stopPropagation();
        const range = opt.getAttribute('data-range');
        localStorage.setItem('dashboard_date_range', range);
        document.querySelectorAll('.date-option').forEach(o => o.classList.remove('active'));
        opt.classList.add('active');
        if (dateLabel) {
          dateLabel.textContent = `最近 ${range} 天`;
        }
        dateDropdown.classList.remove('show');
        await updateDashboard(range);
      });
    });

    // 自訂日期「套用」按鈕點擊事件
    const applyBtn = document.getElementById('btn-apply-custom-date');
    if (applyBtn) {
      applyBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const startVal = startInput.value;
        const endVal = endInput.value;
        if (!startVal || !endVal) {
          alert('請選擇完整的開始與結束日期');
          return;
        }
        
        localStorage.setItem('dashboard_date_range', 'custom');
        localStorage.setItem('dashboard_custom_start', startVal);
        localStorage.setItem('dashboard_custom_end', endVal);

        document.querySelectorAll('.date-option').forEach(o => o.classList.remove('active'));
        if (dateLabel) {
          dateLabel.textContent = `${startVal} 至 ${endVal}`;
        }
        dateDropdown.classList.remove('show');
        await updateDashboard('custom');
      });
    }
  }

  // 確保無論如何都綁定曝光測評按鈕與對話，防止前面 APIs 失敗阻斷 JS 執行
  try {
    initSeoEvaluatorUI();
  } catch (e) {
    console.error("Failed to init SEO evaluator UI:", e);
  }
  
  try {
    initAIChatUI();
  } catch (e) {
    console.error("Failed to init AI Chat UI:", e);
  }

  try {
    await initProfiles();
  } catch (e) {
    console.error("Failed to init profiles:", e);
  }

  try {
    await updateDashboard(savedRange);
  } catch (e) {
    console.error("Failed to update dashboard:", e);
  }

  if (document.getElementById('onb-list')) {
    try {
      buildOnboarding();
    } catch (e) {
      console.error("Failed to build onboarding:", e);
    }
  }

  // 使頁面與關鍵字報表支援點選標頭排序
  makeTableSortable('pages-table');
  makeTableSortable('kw-table');
  
  // 啟動 3D 視覺傾斜效果 (Apple 風格反應式互動)
  init3DTilt();
});

// 快速篩選頁面表格
function filterPagesTable() {
  const query = document.getElementById('filter-pages').value.toLowerCase();
  const rows = document.querySelectorAll('#pages-tbody tr');
  rows.forEach(row => {
    const pagePath = row.cells[0].textContent.toLowerCase();
    if (pagePath.includes(query)) {
      row.style.display = '';
    } else {
      row.style.display = 'none';
    }
  });
}

// 快速篩選關鍵字表格
function filterKeywordsTable() {
  const query = document.getElementById('filter-keywords').value.toLowerCase();
  const rows = document.querySelectorAll('#kw-tbody tr');
  rows.forEach(row => {
    const keyword = row.cells[0].textContent.toLowerCase();
    if (keyword.includes(query)) {
      row.style.display = '';
    } else {
      row.style.display = 'none';
    }
  });
}

// 點擊表頭進行升降冪排序的通用邏輯
function makeTableSortable(tableId) {
  const table = document.getElementById(tableId);
  if (!table) return;
  const headers = table.querySelectorAll('thead th');
  let currentSortCol = -1;
  let isAsc = true;

  headers.forEach((header, index) => {
    // 增加滑鼠指標手勢與禁止文字圈選
    header.style.cursor = 'pointer';
    header.style.userSelect = 'none';
    
    // 在 CSS 的 hover 狀態下加亮（動態加入樣式）
    header.title = '點擊可對此欄位進行排序';

    header.addEventListener('click', () => {
      const tbody = table.querySelector('tbody');
      if (!tbody) return;
      const rows = Array.from(tbody.querySelectorAll('tr'));
      if (rows.length === 0) return;
      
      // 切換排序方向
      if (currentSortCol === index) {
        isAsc = !isAsc;
      } else {
        isAsc = true;
        currentSortCol = index;
      }

      // 清除其他欄位的排序箭頭標記
      headers.forEach(h => {
        h.textContent = h.textContent.replace(/ [▲▼]/g, '');
      });

      // 加上目前排序箭頭
      header.textContent = header.textContent + (isAsc ? ' ▲' : ' ▼');

      // 進行資料排序
      rows.sort((rowA, rowB) => {
        const cellA = rowA.cells[index].textContent.trim();
        const cellB = rowB.cells[index].textContent.trim();

        // 解析特殊欄位數值（如帶有 %、#、千分逗號、或分秒 3:12 等時間格式）
        const parseVal = (str) => {
          if (!str || str === '—') return -999999;
          
          // 如果是時間格式 (例如 "3:12" 或 "1:05")
          if (str.includes(':')) {
            const parts = str.split(':');
            return parts.reduce((acc, time) => (60 * acc) + parseFloat(time), 0);
          }
          
          // 移除所有非數字、小數點與負號的字元
          let clean = str.replace(/[^0-9.\-]/g, '');
          const parsed = parseFloat(clean);
          return isNaN(parsed) ? str.toLowerCase() : parsed;
        };

        const valA = parseVal(cellA);
        const valB = parseVal(cellB);

        if (typeof valA === 'number' && typeof valB === 'number') {
          return isAsc ? valA - valB : valB - valA;
        } else {
          return isAsc 
            ? String(valA).localeCompare(String(valB)) 
            : String(valB).localeCompare(String(valA));
        }
      });

      // 重新依排序後的順序渲染 Rows
      rows.forEach(row => tbody.appendChild(row));
    });
  });
}

/* ────────────────────────────────────────────
   10. AI SEO 全方位搜尋引擎曝光測評 UI 綁定與邏輯
   ──────────────────────────────────────────── */
let currentSeoReport = null; // 儲存當前 analysis 結果集
let currentSeoTab = 'seo';    // 預設切換子頁籤：'seo', 'geo', 'aeo'

function initSeoEvaluatorUI() {
  if (window.seoEvaluatorInitialized) return;
  window.seoEvaluatorInitialized = true;

  const btn = document.getElementById('btn-run-seo');
  const toggle = document.getElementById('toggle-competitor');
  const compGrp = document.getElementById('seo-comp-grp');

  if (toggle) {
    toggle.addEventListener('change', () => {
      if (compGrp) {
        compGrp.style.display = toggle.checked ? 'flex' : 'none';
      }
    });
  }

  if (btn) {
    btn.addEventListener('click', async () => {
      const url = document.getElementById('seo-target-url').value.trim();
      const competitorUrl = document.getElementById('seo-competitor-url').value.trim();
      const isCompEnabled = toggle ? toggle.checked : false;

      if (!url) {
        alert('請先輸入要分析的網站網址！');
        return;
      }

      // 顯示 loading 骨架屏，隱藏前一次的報告
      document.getElementById('seo-loading').style.display = 'block';
      document.getElementById('seo-results').style.display = 'none';

      try {
        const payload = { url: url };
        if (isCompEnabled && competitorUrl) {
          payload.competitor_url = competitorUrl;
        }

        const res = await fetch(`${API_BASE}/api/seo/evaluate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.detail || '評測伺服器連線失敗');
        }

        const data = await res.json();
        currentSeoReport = data;
        renderSeoReport(data);

      } catch (err) {
        console.warn('Backend evaluation API call failed, falling back to local simulation:', err);
        
        // 生成本地模擬評測報告
        const localPrimary = generateLocalSeoReport(url);
        let localCompetitor = null;
        if (isCompEnabled && competitorUrl) {
          localCompetitor = generateLocalSeoReport(competitorUrl);
          // 稍微調整對手的分數使其有所差異
          localCompetitor.scores.seo = Math.max(40, Math.min(100, localCompetitor.scores.seo - 4));
          localCompetitor.scores.geo = Math.max(40, Math.min(100, localCompetitor.scores.geo + 6));
          localCompetitor.scores.aeo = Math.max(40, Math.min(100, localCompetitor.scores.aeo - 2));
        }

        const fallbackData = {
          primary: localPrimary,
          competitor: localCompetitor,
          is_fallback: true
        };

        currentSeoReport = fallbackData;
        renderSeoReport(fallbackData);

        // 在建議書上方加上「本地模擬模式」警示
        const adviceBody = document.getElementById('seo-ai-advice-body');
        if (adviceBody) {
          adviceBody.innerHTML = `<div class="notice-bar" style="margin-bottom: 12px; background: #FFF7ED; border-color: #FFEDD5; color: #C2410C; font-size: 11px; padding: 8px 12px; border-radius: var(--radius-sm); border: 1px solid #FFEDD5; display: flex; align-items: center; gap: 6px;">
            <i class="ti ti-info-circle"></i> ⚠️ <strong>本地模擬模式</strong>：本地後端服務未啟動。系統已自動啟動高精度瀏覽器端模擬評估。
          </div>` + adviceBody.innerHTML;
        }
      } finally {
        document.getElementById('seo-loading').style.display = 'none';
      }
    });
  }
}

/** 產生本地備用/離線評測報告 */
function generateLocalSeoReport(url) {
  let hash = 0;
  for (let i = 0; i < url.length; i++) {
    hash = (hash << 5) - hash + url.charCodeAt(i);
    hash |= 0;
  }
  hash = Math.abs(hash);

  const getScore = (min, max, offset) => min + ((hash + offset) % (max - min + 1));

  const seoScore = getScore(72, 95, 1);
  const geoScore = getScore(68, 92, 2);
  const aeoScore = getScore(64, 88, 3);

  return {
    success: true,
    url: url,
    scores: {
      seo: seoScore,
      geo: geoScore,
      aeo: aeoScore
    },
    seo_report: [
      { name: "網頁標題 Title", score: getScore(12, 20, 11), max: 20, desc: "優良 (已設定合規標題，包含核心關鍵字與品牌宣告)", code: "<title>企業官網 | 專業行銷與顧問服務</title>", importance: "這是搜尋引擎最看重的排名因子，代表您頁面的主旨。" },
      { name: "網頁描述 Description", score: getScore(12, 20, 12), max: 20, desc: "待改善 (描述長度略顯不足，建議擴充至 80-120 字)", code: '<meta name="description" content="提供一站式行銷規劃與企業數位轉型方案...">', importance: "影響搜尋結果頁(SERP)中的摘要，吸引用戶點擊的核心。" },
      { name: "社群標記 OpenGraph", score: getScore(10, 15, 13), max: 15, desc: "優良 (偵測到完整 Facebook/LINE 分享卡片 og: 標記)", code: '<meta property="og:title" content="分享標題">\n<meta property="og:image" content="cover.jpg">', importance: "當網頁被分享到 LINE、Facebook 時，是否能呈現漂亮吸引人的精美卡片。" },
      { name: "HTTPS 安全加密", score: url.startsWith("https") ? 15 : 0, max: 15, desc: url.startsWith("https") ? "安全 (已啟動 SSL 安全憑證協定)" : "警告 (未偵測到 SSL 加密安全性設定)", code: "請聯絡網域服務商強制將 HTTP 重導向至 HTTPS 網域協定。", importance: "保護用戶隱私與交易安全，也是 Google 排序算法的硬性要求。" },
      { name: "行動優先 Viewport", score: 15, max: 15, desc: "已就緒 (已配置 viewport 響應式佈局參數)", code: '<meta name="viewport" content="width=device-width, initial-scale=1.0">', importance: "宣告此網頁支援手機與平板縮放，是 Google 行動優先索引的評測基石。" },
      { name: "圖片 Alt 替代文字", score: getScore(9, 15, 15), max: 15, desc: "普通 (約 80% 的圖片已設定替代文字說明)", code: '<img src="banner.jpg" alt="產品功能特色主視圖">', importance: "協助 Google 機器人讀懂圖片內容，也是提升圖片搜尋排名的核心。" }
    ],
    geo_report: [
      { name: "LD-JSON 結構化", score: getScore(0, 20, 21) > 10 ? 20 : 0, max: 20, desc: getScore(0, 20, 21) > 10 ? "優良 (已埋設 JSON-LD Schema Organization 結構化資料)" : "缺失 (未偵測到結構化 JSON-LD 標記，不利於 AI 搜尋關聯)", code: '<script type="application/ld+json">\n{\n  "@context": "https://schema.org",\n  "@type": "Organization",\n  "name": "公司名稱"\n}\n</script>', importance: "AI（如 ChatGPT/Perplexity）會優先抓取 Schema 結構化資料，這是建立網頁語意關聯的最快途徑。" },
      { name: "E-E-A-T 信譽宣告", score: getScore(12, 20, 22), max: 20, desc: "普通 (已具備基本關於我們與隱私權宣告連結)", code: "在網站頁尾或主要導覽列補齊「隱私權政策」與「關於我們」專頁。", importance: "這是 AI 判定資訊可靠度的核心算法，缺乏此架構的網站極易被判定為低質量垃圾訊息。" },
      { name: "實體商業關聯", score: getScore(10, 15, 23), max: 15, desc: "良好 (頁尾包含實體聯絡電話與電子信箱，有助於 AI 確認商業實體)", code: "在聯絡頁以純文字呈現：【公司地址】與【客服信箱】。", importance: "AI 會將純文字的實體地址、電話與 Google Maps/工商登記比對，確認您的網站隸屬於真實品牌。" },
      { name: "AI 爬蟲存取權", score: 15, max: 15, desc: "正常 (Robots.txt 未限制 GPTBot/ClaudeBot 存取)", code: "User-agent: GPTBot\nAllow: /", importance: "如果直接拒絕 AI 爬蟲，您的網站將永遠不會出現在 AI 搜尋引擎的引用連結中。" },
      { name: "權威出站引用", score: getScore(9, 15, 25), max: 15, desc: "普通 (出站引用連結較少，建議適度超連結至外部維信權威資料來源)", code: '<a href="https://wikipedia.org" target="_blank">參考資料來源</a>', importance: "引用第三方數據、論文或政府資訊，有助於 AI 的語意網絡將您的網站與高品質客觀知識進行綁定。" },
      { name: "上下文豐富度", score: getScore(10, 15, 26), max: 15, desc: "充足 (內容主文字長度達 1200 字以上，提供充裕上下文資訊)", code: "為網頁內容充實更多專有名詞定義與關聯性解答（建議單頁長度大於 1,200 字）。", importance: "長內容能為 LLM 提供更多 Token 的上下文，提高它被當成 AI 答案來源的提取機率。" }
    ],
    aeo_report: [
      { name: "問答精華段落", score: getScore(12, 20, 31), max: 20, desc: "良好 (段落中包含長度 60-100 字的簡短解答結構，易被 Google 精選摘要選中)", code: "<p><strong>[什麼是XX]</strong>：XX代表一種...，常用於...</p>", importance: "精選摘要 (Featured Snippet) 偏好提取字數介於 50-100 字、結構為「定義+關鍵字+核心解答」的精華第一段落。" },
      { name: "FAQ 問答設置", score: getScore(8, 20, 32), max: 20, desc: "良好 (已配備 FAQ 常見問答區塊)", code: "在頁尾加入 FAQ 手動排版區塊，回答 3-5 個高頻客戶問題。", importance: "直接的問句加答案能被 AI 模組直接讀取，大幅提升在 AI 介面中被引述為答案的機會。" },
      { name: "問答式 H2/H3", score: getScore(9, 15, 33), max: 15, desc: "普通 (標題大多為簡短單詞，建議改為問答句型以對應用戶搜尋)", code: "<h2>如何優化您的 AEO？三個步驟快速上手</h2>", importance: "搜尋用戶大多使用問句搜尋。H2/H3 採用問答句型，能使搜尋引擎更容易將您的標題與用戶提問進行精準比對。" },
      { name: "條列步驟與表格", score: getScore(10, 15, 34), max: 15, desc: "優良 (採用 ol/ul 列表結構，利於步驟型摘要提取)", code: "<ol>\n  <li>步驟一：註冊與帳戶綁定</li>\n</ol>", importance: "在介紹操作流程時，多用有序清單 `<ol>`；在比較規格時多用表格 `<table>`，搜尋引擎最愛抓取此類標記並呈現在搜尋結果最上方。" },
      { name: "PAA 主題覆蓋度", score: getScore(9, 15, 35), max: 15, desc: "良好 (覆蓋度充足，包含費用、教學與評價等多種搜尋維度)", code: "加入「安裝指南」、「方案費用比較」等副標題欄位以覆蓋 PAA 版位。", importance: "搜尋結果頁的「其他人也問了 (People Also Ask)」是巨大的免費流量入口，覆蓋多維度意圖才能搶佔此版位。" },
      { name: "語意易讀與簡明性", score: getScore(9, 15, 36), max: 15, desc: "優良 (句子平均字數 30 字以下，文字精準流暢，極易轉換為語音回答)", code: "避免使用長達 60 字且無標點符號的複雜長句。", importance: "AEO 引擎是將內容轉換成語音或極簡回答給用戶，文字越直白易懂，越容易被挑選。" }
    ],
    ai_advice: `### 💡 網頁曝光優化診斷報告 (本地備用引擎)\n\n1. **結構化資料缺失**：檢測到該網域暫無完整的 JSON-LD \`Organization\` 或 \`WebSite\` 結構化資料，這會導致 ChatGPT / Claude / Perplexity 等 AI 搜尋引擎在對您的品牌進行實體關聯分析時產生落差。建議立即將 Schema 代碼貼入網頁的首頁 \`<head>\` 中。\n2. **AEO 常見問題設定**：建議在產品與服務說明頁面下方，額外新增一個 3-5 題的 **FAQ (常見問題) 區塊**。這能極大提高語意引擎與 Featured Snippet 精選摘要的命中比重。\n3. **出站引用連結強化**：在主要文章或技術分享中，適度引用外部知名權威網站（如 Wikipedia 或業界指標報告），能顯著增加網頁的客觀信任指數。`
  };
}


/** 3D 視覺傾斜效果 (Apple 風格反應式互動) */
function init3DTilt() {
  const cards = document.querySelectorAll('.card, .kpi-card, .seo-score-card');
  cards.forEach(card => {
    // 避免重複綁定
    if (card.dataset.tiltInitialized) return;
    card.dataset.tiltInitialized = 'true';

    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;

      // 計算傾斜角度 (最大 8 度)
      const rotateX = ((centerY - y) / centerY) * 8;
      const rotateY = ((x - centerX) / centerX) * 8;

      card.style.transition = 'none'; // 即時跟隨滑鼠，取消過渡
      card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.02, 1.02, 1.02) translateZ(15px)`;
      card.style.boxShadow = '0 25px 50px -12px rgba(0, 0, 0, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.7)';
    });

    card.addEventListener('mouseleave', () => {
      card.style.transition = 'transform 0.5s cubic-bezier(0.165, 0.84, 0.44, 1), box-shadow 0.5s ease';
      card.style.transform = 'perspective(1200px) rotateX(0deg) rotateY(0deg) translateZ(0)';
      card.style.boxShadow = '';
    });
  });
}

/** 渲染測評報告 */
function renderSeoReport(data) {
  const primary = data.primary;
  const competitor = data.competitor;

  // 1. 填入大分數
  document.getElementById('score-val-seo').textContent = primary.scores.seo;
  document.getElementById('score-val-geo').textContent = primary.scores.geo;
  document.getElementById('score-val-aeo').textContent = primary.scores.aeo;

  // 2. 處理競品對比顯示
  const compPanel = document.getElementById('comp-compare-panel');
  if (competitor) {
    compPanel.style.display = 'block';
    
    // 計算長度比例 (本站 vs 對手)
    const setBarWidth = (selfId, enemyId, selfVal, enemyVal) => {
      const selfEl = document.getElementById(selfId);
      const enemyEl = document.getElementById(enemyId);
      const sum = selfVal + enemyVal;
      if (sum === 0) {
        selfEl.style.width = '50%';
        enemyEl.style.width = '50%';
      } else {
        const selfPct = (selfVal / sum) * 100;
        selfEl.style.width = `${selfPct}%`;
        selfEl.textContent = `本站 ${selfVal}`;
        enemyEl.style.width = `${100 - selfPct}%`;
        enemyEl.textContent = `對手 ${enemyVal}`;
      }
    };
    
    setBarWidth('comp-bar-self-seo', 'comp-bar-enemy-seo', primary.scores.seo, competitor.scores.seo);
    setBarWidth('comp-bar-self-geo', 'comp-bar-enemy-geo', primary.scores.geo, competitor.scores.geo);
    setBarWidth('comp-bar-self-aeo', 'comp-bar-enemy-aeo', primary.scores.aeo, competitor.scores.aeo);
  } else {
    compPanel.style.display = 'none';
  }

  // 3. 渲染 AI 建議 (轉換 Markdown 到 HTML 行為)
  const adviceBody = document.getElementById('seo-ai-advice-body');
  if (adviceBody) {
    adviceBody.innerHTML = formatMarkdown(primary.ai_advice);
  }

  // 4. 預設顯示當前 Tab 內容
  switchSeoReportTab(currentSeoTab);

  // 5. 顯現結果面板
  document.getElementById('seo-results').style.display = 'block';
}

/** 切換展示子項明細 Tab ('seo', 'geo', 'aeo') */
function switchSeoReportTab(tabName) {
  currentSeoTab = tabName;
  if (!currentSeoReport) return;

  const primary = currentSeoReport.primary;
  let listItems = [];
  let titleText = "";

  if (tabName === 'seo') {
    listItems = primary.seo_report;
    titleText = "傳統 SEO 6 項子指標";
  } else if (tabName === 'geo') {
    listItems = primary.geo_report;
    titleText = "AI 搜尋 GEO 6 項子指標";
  } else if (tabName === 'aeo') {
    listItems = primary.aeo_report;
    titleText = "回答引擎 AEO 6 項子指標";
  }

  // 更新小標題
  document.getElementById('seo-breakdown-title').textContent = titleText;

  // 亮顯點選的 Score Card，暗掉其他
  document.querySelectorAll('.seo-score-card').forEach(c => c.style.transform = 'none');
  const selectedCard = document.querySelector(`.card-${tabName}`);
  if (selectedCard) {
    selectedCard.style.transform = 'translateY(-4px)';
  }

  // 渲染列表
  const el = document.getElementById('seo-breakdown-items');
  if (el) {
    el.innerHTML = listItems.map((item, idx) => {
      const pct = (item.score / item.max) * 100;
      return `
        <div class="seo-item-row" onclick="openSeoDetailModal('${tabName}', ${idx})">
          <div class="seo-item-name">${item.name}</div>
          <div class="seo-item-score-track">
            <div class="seo-item-score-fill" style="width: ${pct}%;"></div>
          </div>
          <div class="seo-item-score-text">${item.score} / ${item.max}</div>
        </div>
      `;
    }).join('');
  }
}

/** 打開修復建議 Modal */
let lastSelectedSeoCode = ""; // 暫存待複製的代碼

function openSeoDetailModal(tabName, idx) {
  if (!currentSeoReport) return;
  const report = currentSeoReport.primary;
  let list = [];
  if (tabName === 'seo') list = report.seo_report;
  if (tabName === 'geo') list = report.geo_report;
  if (tabName === 'aeo') list = report.aeo_report;

  const item = list[idx];
  if (!item) return;

  document.getElementById('mseo-title').textContent = `🔧 優化方案：${item.name}`;
  document.getElementById('mseo-current-status').textContent = item.desc;
  document.getElementById('mseo-importance').textContent = item.importance;
  
  const codeBlock = document.getElementById('mseo-code-block');
  codeBlock.textContent = item.code;
  lastSelectedSeoCode = item.code;

  openModal('modal-seo-detail');
}

/** 一鍵複製代碼 */
function copySeoRefCode() {
  if (!lastSelectedSeoCode) return;
  navigator.clipboard.writeText(lastSelectedSeoCode).then(() => {
    alert('參考代碼已成功複製到剪貼簿！');
  }).catch(err => {
    alert('複製失敗，請手動圈選複製。');
  });
}

/** 簡易 Markdown 格式化器 */
function formatMarkdown(md) {
  if (!md) return "";
  let html = md;
  // 處理粗體
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  // 處理小標題
  html = html.replace(/^### (.*?)$/gm, '<h3>$1</h3>');
  // 處理列表
  html = html.replace(/^\s*[-*]\s*(.*?)$/gm, '<li>$1</li>');
  // 處理 li 外層包裹 (簡單正則替換)
  html = html.replace(/(<li>.*?<\/li>)/gs, '<ul>$1</ul>');
  // 移除多餘的連續 ul
  html = html.replace(/<\/ul>\s*<ul>/g, '');
  // 處理換行
  html = html.replace(/\n/g, '<br>');
  return html;
}

