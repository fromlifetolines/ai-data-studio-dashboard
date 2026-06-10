"""
AI Data Studio — backend/main.py
FastAPI 後端 API 進入點

啟動方式：
  cd backend
  uvicorn main:app --reload --port 8000

API 文件：
  http://localhost:8000/docs
"""

import os
import json
import asyncio
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ── 本地模組 ──────────────────────────────────────────
from ga4_client import GA4Client, GA4Config
from ai_insight_engine import generate_insight

# ── App 初始化 ────────────────────────────────────────
app = FastAPI(
    title="AI Data Studio API",
    description="全渠道數據分析後端，串接 GA4 / Search Console / Google Ads / Meta Ads",
    version="1.0.0"
)

# ── CORS（允許前端 GitHub Pages 呼叫）────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 設定檔路徑 ────────────────────────────────────────
SETTINGS_PATH = Path(__file__).parent.parent / "credentials" / "settings.json"
CREDENTIALS_DIR = Path(__file__).parent.parent / "credentials"
CREDENTIALS_DIR.mkdir(exist_ok=True)

# ══════════════════════════════════════════════════════
# Request / Response 資料模型
# ══════════════════════════════════════════════════════

class GA4Settings(BaseModel):
    property_id: str           # 例：properties/123456789
    credentials_json: str      # Service Account JSON 內容（字串）

class SaveSettingsRequest(BaseModel):
    ga4: Optional[GA4Settings] = None
    openai_key: Optional[str] = None

class ValidateRequest(BaseModel):
    property_id: str
    credentials_json: str

# ══════════════════════════════════════════════════════
# 工具函式
# ══════════════════════════════════════════════════════

def load_settings() -> dict:
    """讀取本地設定檔"""
    if SETTINGS_PATH.exists():
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_settings(data: dict):
    """儲存設定到本地檔案"""
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_credentials_path() -> Optional[Path]:
    """取得 Service Account JSON 檔案路徑"""
    path = CREDENTIALS_DIR / "service-account.json"
    return path if path.exists() else None

# ══════════════════════════════════════════════════════
# API 路由
# ══════════════════════════════════════════════════════

# ── 健康檢查 ──────────────────────────────────────────
@app.get("/api/health")
async def health_check():
    """健康檢查 + 設定狀態"""
    settings = load_settings()
    cred_path = get_credentials_path()

    return {
        "status": "ok",
        "version": "1.0.0",
        "config": {
            "ga4_configured":         bool(settings.get("ga4_property_id")) and cred_path is not None,
            "ga4_property_id":        settings.get("ga4_property_id", ""),
            "openai_configured":      bool(settings.get("openai_key") or os.getenv("OPENAI_API_KEY")),
            "credentials_file_exists": cred_path is not None,
            "demo_mode":              not (bool(settings.get("ga4_property_id")) and cred_path is not None),
        }
    }

# ── 儲存設定 ──────────────────────────────────────────
@app.post("/api/settings/save")
async def save_api_settings(req: SaveSettingsRequest):
    """
    儲存 GA4 Property ID、Service Account JSON、OpenAI Key
    這是用戶在「設定頁面」填完表單後呼叫的端點
    """
    settings = load_settings()

    if req.ga4:
        # 標準化 Property ID 格式
        prop_id = req.ga4.property_id.strip()
        if not prop_id.startswith("properties/"):
            prop_id = f"properties/{prop_id}"
        settings["ga4_property_id"] = prop_id

        # 儲存 Service Account JSON 到 credentials/ 目錄
        cred_path = CREDENTIALS_DIR / "service-account.json"
        try:
            parsed = json.loads(req.ga4.credentials_json)
            with open(cred_path, "w", encoding="utf-8") as f:
                json.dump(parsed, f, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Service Account JSON 格式錯誤，請確認內容是完整的 JSON 格式。")

    if req.openai_key:
        settings["openai_key"] = req.openai_key.strip()

    save_settings(settings)
    return {"success": True, "message": "設定已儲存"}

# ── 驗證 GA4 連線 ─────────────────────────────────────
@app.post("/api/settings/validate-ga4")
async def validate_ga4(req: ValidateRequest):
    """
    驗證 GA4 Property ID + Service Account 是否能成功連線
    用戶點擊「驗證」按鈕時呼叫
    """
    try:
        # 暫時寫入 credentials 測試
        temp_path = CREDENTIALS_DIR / "service-account.json"
        parsed = json.loads(req.credentials_json)
        with open(temp_path, "w") as f:
            json.dump(parsed, f)

        prop_id = req.property_id
        if not prop_id.startswith("properties/"):
            prop_id = f"properties/{prop_id}"

        config = GA4Config(
            property_id=prop_id,
            credentials_path=str(temp_path)
        )
        client = GA4Client(config)
        result = client.test_connection()

        return {"success": True, "message": "GA4 連線成功！", "property_name": result.get("name", "")}

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Service Account JSON 格式錯誤")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"連線失敗：{str(e)}")

# ── 讀取目前設定 ──────────────────────────────────────
@app.get("/api/settings")
async def get_settings():
    """讀取目前的設定狀態（不回傳敏感資訊）"""
    settings = load_settings()
    cred_path = get_credentials_path()

    return {
        "ga4_property_id":         settings.get("ga4_property_id", ""),
        "ga4_configured":          bool(settings.get("ga4_property_id")) and cred_path is not None,
        "openai_configured":       bool(settings.get("openai_key") or os.getenv("OPENAI_API_KEY")),
        "credentials_file_exists": cred_path is not None,
    }

# ── 完整 Dashboard 數據 ───────────────────────────────
@app.get("/api/dashboard")
async def get_dashboard(
    start_date: str = "30daysAgo",
    end_date:   str = "today"
):
    """
    主要 API：回傳完整 Dashboard 所需的所有數據
    前端 dashboard.js 呼叫這個端點

    Query params:
      start_date: 例 "7daysAgo", "30daysAgo", "2025-01-01"
      end_date:   例 "today", "2025-06-08"
    """
    settings = load_settings()
    cred_path = get_credentials_path()

    # ── Demo Mode：沒有設定 credentials 時返回假數據 ──
    if not settings.get("ga4_property_id") or not cred_path:
        return JSONResponse(content={
            "mode": "demo",
            "message": "目前為 Demo 模式。請至「設定」頁面輸入 GA4 Property ID 與 Service Account 金鑰以顯示真實數據。",
            "data": _get_demo_data()
        })

    # ── 真實模式：呼叫 GA4 API ────────────────────────
    try:
        config = GA4Config(
            property_id=settings["ga4_property_id"],
            credentials_path=str(cred_path)
        )
        client = GA4Client(config)

        # 並行撈取多組數據，加速回應
        results = await asyncio.gather(
            asyncio.to_thread(client.get_overview,         start_date, end_date),
            asyncio.to_thread(client.get_sessions_trend,   start_date, end_date),
            asyncio.to_thread(client.get_traffic_sources,  start_date, end_date),
            asyncio.to_thread(client.get_top_pages,        start_date, end_date),
            asyncio.to_thread(client.get_device_breakdown, start_date, end_date),
            return_exceptions=True
        )

        overview, sessions_trend, traffic_sources, top_pages, device = results

        # 處理部分失敗
        for r in results:
            if isinstance(r, Exception):
                print(f"[WARN] 部分數據撈取失敗：{r}")

        # 將 GA4 真實數據映射為前端期待的格式
        overview_dict = overview if not isinstance(overview, Exception) else {}
        sessions_delta = overview_dict.get("sessions_delta", "—")
        users_delta = overview_dict.get("users_delta", "—")

        # 1. KPIs
        kpis = {
            "sessions": {
                "value": f"{overview_dict.get('sessions', 0):,}" if "sessions" in overview_dict else "—",
                "delta": sessions_delta,
                "trend": "up" if "+" in sessions_delta else "down" if "-" in sessions_delta else "flat"
            },
            "users": {
                "value": f"{overview_dict.get('users', 0):,}" if "users" in overview_dict else "—",
                "delta": users_delta,
                "trend": "up" if "+" in users_delta else "down" if "-" in users_delta else "flat"
            },
            "impressions": {"value": "—", "delta": "—", "trend": "flat"},
            "roas":        {"value": "—", "delta": "—", "trend": "flat"},
        }

        # 2. 每日趨勢
        trend_dict = sessions_trend if not isinstance(sessions_trend, Exception) else {}
        s_trend = trend_dict.get("sessions_trend", [])
        u_trend = trend_dict.get("users_trend", [])
        nu_trend = trend_dict.get("new_users_trend", [])

        # 3. 流量來源與裝置類型
        t_sources = traffic_sources if not isinstance(traffic_sources, Exception) else []
        dev_data = device if not isinstance(device, Exception) else []

        # 4. 熱門網頁
        pages_data = top_pages if not isinstance(top_pages, Exception) else []

        # 生成 AI 洞察
        openai_key = settings.get("openai_key") or os.getenv("OPENAI_API_KEY", "")
        ai_summary = ""
        if openai_key and overview_dict:
            try:
                # 將 ga4_data 包裝為原 format 以相容 generate_insight 函式
                temp_ga4_data = {
                    "overview": overview_dict,
                    "sessions_trend": trend_dict,
                    "traffic_sources": t_sources,
                    "top_pages": pages_data,
                    "device": dev_data,
                }
                ai_summary = await asyncio.to_thread(
                    generate_insight, temp_ga4_data, openai_key
                )
            except Exception as e:
                print(f"[WARN] AI 洞察生成失敗：{e}")
                ai_summary = "AI 分析暫時無法使用，請稍後再試。"

        # 取得 Demo 數據當作其他填寫項目的預設值 (避免 Search Console & Ads 面板在 live 模式下因沒資料而破版/報錯)
        demo = _get_demo_data()

        data_payload = {
            "ai_summary": ai_summary or f"已成功串接 GA4 真實數據！工作階段共 {overview_dict.get('sessions', 0):,} 次，不重複用戶 {overview_dict.get('users', 0):,} 位，跳出率 {overview_dict.get('bounce_rate', '—')}。",
            "kpis": kpis,
            "sessions_trend": s_trend,
            "users_trend": u_trend,
            "new_users_trend": nu_trend,
            "traffic_source": t_sources,
            "device": dev_data,
            "pages": pages_data,
            "keywords": demo.get("keywords", []),
            "ssc_imp": demo.get("ssc_imp", []),
            "ssc_click": demo.get("ssc_click", []),
            "search_type": demo.get("search_type", []),
            "channels": demo.get("channels", []),
            "ad_revenue": demo.get("ad_revenue", []),
            "ad_spend": demo.get("ad_spend", []),
            "budget": demo.get("budget", []),
        }

        return JSONResponse(content={
            "mode": "live",
            "data": data_payload
        })

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"數據撈取失敗：{str(e)}。請確認 GA4 Property ID 與 Service Account 金鑰是否正確。"
        )

# ── 單獨 GA4 端點 ─────────────────────────────────────
@app.get("/api/ga4")
async def get_ga4_data(
    metric:     str = "sessions",
    start_date: str = "30daysAgo",
    end_date:   str = "today"
):
    """取得特定 GA4 指標數據"""
    settings = load_settings()
    cred_path = get_credentials_path()

    if not settings.get("ga4_property_id") or not cred_path:
        raise HTTPException(status_code=400, detail="尚未設定 GA4，請先完成串接設定。")

    config = GA4Config(
        property_id=settings["ga4_property_id"],
        credentials_path=str(cred_path)
    )
    client = GA4Client(config)

    try:
        data = client.get_metric(metric, start_date, end_date)
        return {"metric": metric, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── AI 洞察端點 ───────────────────────────────────────
@app.get("/api/ai-insight")
async def get_ai_insight():
    """取得最新 AI 洞察文字"""
    settings = load_settings()
    openai_key = settings.get("openai_key") or os.getenv("OPENAI_API_KEY", "")

    if not openai_key:
        return {"insight": "請設定 OpenAI API Key 以啟用 AI 洞察功能。", "mode": "no_key"}

    # 這裡可以從快取讀取，避免每次都重新呼叫 AI
    return {"insight": "AI 洞察功能已啟用。請呼叫 /api/dashboard 取得完整分析。", "mode": "ready"}

# ══════════════════════════════════════════════════════
# Demo 數據（沒有 credentials 時使用）
# ══════════════════════════════════════════════════════

def _get_demo_data() -> dict:
    """回傳 Demo 模式假數據，與前端 MOCK 對應"""
    return {
        "ai_summary": "這是 <strong>Demo 模式</strong>，目前顯示的是示範數據。請前往「設定」頁面串接你的 GA4 帳號，即可看到真實數據與 AI 分析。",
        "kpis": {
            "sessions":    {"value": "38,241", "delta": "+9.4%", "trend": "up"},
            "users":       {"value": "28,109", "delta": "+5.2%", "trend": "up"},
            "impressions": {"value": "182K",   "delta": "+12%",  "trend": "up"},
            "roas":        {"value": "3.61×",  "delta": "—",     "trend": "flat"},
        },
        "sessions_trend":  [2400,2800,2600,3100,3300,3800,3600,3200,3700,4000,4300,4100,4500,4700],
        "users_trend":     [1800,2100,1950,2300,2450,2800,2650,2400,2800,3000,3200,3100,3400,3500],
        "new_users_trend": [1100,1300,1200,1500,1600,1900,1750,1500,1750,1900,2000,1950,2100,2200],
        "traffic_source": [
            {"label": "自然搜尋", "value": 61, "color": "#2563EB"},
            {"label": "直接流量", "value": 18, "color": "#6b7280"},
            {"label": "社群媒體", "value": 12, "color": "#93c5fd"},
            {"label": "其他",     "value":  9, "color": "#e5e7eb"},
        ],
        "device": [
            {"label": "手機", "value": 58, "color": "#2563EB"},
            {"label": "桌機", "value": 34, "color": "#6b7280"},
            {"label": "平板", "value":  8, "color": "#d1d5db"},
        ],
        "pages": [
            {"path": "/",               "views": 12401, "unique": 9820,  "time": "3:12", "bounce": "38%", "conv": "4.2%", "status": "good"},
            {"path": "/pricing",        "views": 7832,  "unique": 6140,  "time": "1:05", "bounce": "78%", "conv": "1.8%", "status": "bad"},
            {"path": "/blog/ga4-guide", "views": 5210,  "unique": 4890,  "time": "4:28", "bounce": "41%", "conv": "2.9%", "status": "good"},
            {"path": "/features",       "views": 3980,  "unique": 3200,  "time": "2:50", "bounce": "45%", "conv": "3.1%", "status": "warn"},
            {"path": "/docs",           "views": 2140,  "unique": 1980,  "time": "5:10", "bounce": "33%", "conv": "6.4%", "status": "good"},
        ],
        "keywords": [
            {"kw": "數據分析工具",          "imp": 28400, "click": 1477, "ctr": "5.2%", "rank": "#4.0", "trend": "+2", "opp": "進入首頁", "opp_type": "good"},
            {"kw": "GA4 教學",              "imp": 19200, "click": 1306, "ctr": "6.8%", "rank": "#3.2", "trend": "+3", "opp": "搶 Top3",  "opp_type": "good"},
            {"kw": "網站流量分析",          "imp": 15800, "click":  616, "ctr": "3.9%", "rank": "#6.1", "trend": "−1", "opp": "加強內容", "opp_type": "warn"},
            {"kw": "google analytics 設定", "imp": 11400, "click":  240, "ctr": "2.1%", "rank": "#12",  "trend": "+5", "opp": "有潛力",   "opp_type": "warn"},
            {"kw": "SEO 工具推薦",          "imp":  9600, "click":  173, "ctr": "1.8%", "rank": "#18",  "trend": "—",  "opp": "待衝刺",   "opp_type": "bad"},
        ],
        "ssc_imp":    [11000,12500,12000,13800,14200,15000,14500,13200,14800,16000,17000,16500,18000,18200],
        "ssc_click":  [420,490,460,530,550,590,570,510,570,620,660,640,690,692],
        "search_type": [
            {"label": "網頁", "value": 83, "color": "#2563EB"},
            {"label": "圖片", "value": 10, "color": "#6b7280"},
            {"label": "影片", "value":  7, "color": "#d1d5db"},
        ],
        "channels": [
            {"name": "Google Ads",  "icon": "ti-brand-google",   "icon_bg": "#EFF6FF", "icon_color": "#1d4ed8", "spend": "$68,200", "imp": "520K",  "click": "18,400", "conv": "1,140", "cpa": "$59.8",  "roas": "4.2×", "status": "good"},
            {"name": "Meta Ads",    "icon": "ti-brand-facebook", "icon_bg": "#F5F3FF", "icon_color": "#6d28d9", "spend": "$42,300", "imp": "890K",  "click": "11,200", "conv": "580",   "cpa": "$72.9",  "roas": "2.8×", "status": "warn"},
            {"name": "YouTube Ads", "icon": "ti-brand-youtube",  "icon_bg": "#FFF7ED", "icon_color": "#c2410c", "spend": "$14,000", "imp": "1.2M",  "click": "4,800",  "conv": "122",   "cpa": "$114.8", "roas": "1.9×", "status": "bad"},
        ],
        "ad_revenue": [29,33,31,36,39,44,42,38,43,47,50,49,53,56],
        "ad_spend":   [7.5,8,8,9,10,11,9.5,8.8,10,12,13,12,13,14],
        "budget": [
            {"label": "Google",  "value": 55, "color": "#2563EB"},
            {"label": "Meta",    "value": 34, "color": "#6b7280"},
            {"label": "YouTube", "value": 11, "color": "#d1d5db"},
        ],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
