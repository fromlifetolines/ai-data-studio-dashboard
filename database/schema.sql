-- 競品分析專案
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    industry TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 競品清單
CREATE TABLE IF NOT EXISTS competitors (
    id TEXT PRIMARY KEY,
    project_id TEXT,
    name TEXT NOT NULL,
    domain TEXT NOT NULL,
    type TEXT CHECK(type IN ('direct','indirect','benchmark')),
    is_own_company BOOLEAN DEFAULT 0,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- 流量快照
CREATE TABLE IF NOT EXISTS traffic_snapshots (
    id TEXT PRIMARY KEY,
    competitor_id TEXT,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    monthly_visits INTEGER,
    bounce_rate REAL,
    avg_visit_duration INTEGER,
    traffic_sources TEXT,  -- JSON string: {organic, paid, social, direct, referral}
    FOREIGN KEY(competitor_id) REFERENCES competitors(id) ON DELETE CASCADE
);

-- SEO 數據
CREATE TABLE IF NOT EXISTS seo_snapshots (
    id TEXT PRIMARY KEY,
    competitor_id TEXT,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    organic_keywords INTEGER,
    organic_traffic_value INTEGER,
    top_keywords TEXT,       -- JSON string: [{keyword, position, volume}]
    paid_keywords TEXT,       -- JSON string: [{keyword, ad_copy}]
    FOREIGN KEY(competitor_id) REFERENCES competitors(id) ON DELETE CASCADE
);

-- 社群輿情
CREATE TABLE IF NOT EXISTS social_snapshots (
    id TEXT PRIMARY KEY,
    competitor_id TEXT,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    platform TEXT,           -- PTT, Dcard, IG
    post_count INTEGER,
    positive_ratio REAL,
    negative_ratio REAL,
    word_cloud TEXT,        -- JSON string: [{word, count}]
    top_posts TEXT,         -- JSON string
    FOREIGN KEY(competitor_id) REFERENCES competitors(id) ON DELETE CASCADE
);

-- AI 分析結果（緩存）
CREATE TABLE IF NOT EXISTS ai_analyses (
    id TEXT PRIMARY KEY,
    project_id TEXT,
    analysis_type TEXT,      -- swot, porter, insights
    content TEXT,            -- JSON string
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- 線下實地數據
CREATE TABLE IF NOT EXISTS field_surveys (
    id TEXT PRIMARY KEY,
    competitor_id TEXT,
    surveyor TEXT,
    location TEXT,
    survey_date DATE,
    foot_traffic_score INTEGER,  -- 1-5 主觀評分
    product_display_notes TEXT,
    photos TEXT,            -- JSON string: [base64 or URL]
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(competitor_id) REFERENCES competitors(id) ON DELETE CASCADE
);
